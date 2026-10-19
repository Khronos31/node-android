#!/usr/bin/env python3
"""Stage pinned Android PIE Node binaries into an APK without building Node.

Modes:
  reference: checksum-verified 3rd-party Node 24.21.0 prebuilts, for CI only.
  run-artifacts: use BOTH native archives produced by the node-android CI run.
No untrusted tar paths are extracted to the filesystem.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

VERSION = "24.21.0"
SOURCE_SHA = "a6f54defb6fd7c84f41dba13d61e78e9b4e0961712cf61f29715c05f5ced94fc"
REFERENCE = {
    "armeabi-v7a": {
        "arch": "arm",
        "sha256": "137825866407cae9a10e8947a58ceb8b8fbea52867d6bd4ba53d836584b967c9",
        "elf_class": "ELF32",
        "machine": "ARM",
        "interpreter": "/system/bin/linker",
    },
    "arm64-v8a": {
        "arch": "arm64",
        "sha256": "08ec25a88585932ce7f5ffe6ccc0d27606027f130de6d9318f3ea08d4654990e",
        "elf_class": "ELF64",
        "machine": "AArch64",
        "interpreter": "/system/bin/linker64",
    },
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url, target, expected):
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".part")
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Khronos31-node-android-mock/0.2"})
            with urllib.request.urlopen(request, timeout=90) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst)
            if sha256(tmp) != expected:
                raise RuntimeError("Downloaded archive SHA-256 mismatch: " + url)
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
    if sha256(target) != expected:
        raise RuntimeError("Cached archive SHA-256 mismatch: " + str(target))
    return target

def member_contents(tar, required):
    for member in tar.getmembers():
        path = member.name.lstrip("./")
        if path == required and member.isfile():
            if member.size > 200 * 1024 * 1024:
                raise RuntimeError("Unreasonable tar member size: " + path)
            handle = tar.extractfile(member)
            if handle is None:
                break
            return handle.read()
    raise RuntimeError("Missing expected file from tar: " + required)

def inspect(binary, abi):
    spec = REFERENCE[abi]
    header = subprocess.check_output(
        ["readelf", "-h", str(binary)], text=True)
    program = subprocess.check_output(
        ["readelf", "-l", str(binary)], text=True)
    dynamic = subprocess.check_output(
        ["readelf", "-d", str(binary)], text=True)
    if not re.search(r"Class:\s+" + spec["elf_class"], header):
        raise RuntimeError("ELF class mismatch: " + abi)
    if not re.search(r"Machine:\s+" + spec["machine"] + r"\b", header):
        raise RuntimeError("ELF machine mismatch: " + abi)
    if not re.search(r"Type:\s+DYN\b", header):
        raise RuntimeError("Node executable must be PIE/DYN: " + abi)
    if "[Requesting program interpreter: " + spec["interpreter"] + "]" not in program:
        raise RuntimeError("Android linker/interpreter mismatch: " + abi)
    needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
    unexpected = set(needed) - {"libc.so", "libm.so", "libdl.so", "liblog.so", "libz.so"}
    if unexpected or not needed:
        raise RuntimeError("Node requires unbundled shared libraries: " + repr(needed))
    exported = subprocess.check_output(
        ["readelf", "-W", "--dyn-syms", str(binary)], text=True)
    if "napi_create_function" not in exported:
        print("WARNING: Node PIE does not export napi_create_function; "
              "Node-API addon may fail to load.", file=sys.stderr)
    return needed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, choices=["reference", "run-artifacts"])
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    generated = root / ".generated"
    (generated / "assets").mkdir(parents=True, exist_ok=True)
    manifest = {"node_version": VERSION, "source": args.source,
                "run_id": args.run_id or None, "abis": {}}

    for abi, spec in REFERENCE.items():
        if args.source == "reference":
            arch = spec["arch"]
            filename = f"node-android-{arch}-{VERSION}.tar.xz"
            tag = f"node-android-{arch}-24"
            url = ("https://github.com/Delusions6515/node-android-build/"
                   f"releases/download/{tag}/{filename}")
            archive = download(url, generated / "download-cache" / filename,
                               spec["sha256"])
            node_path = f"nodejs-v{VERSION}-android-{arch}/bin/node"
        else:
            if not args.run_id.isdigit() or int(args.run_id) < 1:
                raise RuntimeError("--run-id is required for run-artifacts")
            name = f"node-v{VERSION}-android-{abi}"
            archive = generated / "run-artifacts" / name / (name + ".tar.xz")
            if not archive.is_file():
                raise RuntimeError(f"Missing GitHub Actions artifact: {archive}")
            node_path = "bin/node"

        with tarfile.open(archive, "r:xz") as tf:
            binary = member_contents(tf, node_path)
            if args.source == "run-artifacts":
                meta = json.loads(member_contents(tf, "BUILD-METADATA.json"))
                checks = member_contents(tf, "SHA256SUMS").decode()
                if meta.get("node_version") != VERSION or meta.get("android_abi") != abi:
                    raise RuntimeError("Unexpected runtime metadata: " + abi)
                if meta.get("source_sha256") != SOURCE_SHA:
                    raise RuntimeError("Unpinned Node official source in CI artifact")
                digest = hashlib.sha256(binary).hexdigest()
                if digest != meta.get("binary_sha256"):
                    raise RuntimeError("Runtime SHA-256 disagrees with build metadata")
                if (digest + "  bin/node") not in checks:
                    raise RuntimeError("Binary not attested in SHA256SUMS: " + abi)

        path = generated / "jniLibs" / abi / "libnode_exec.so"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(binary)
        path.chmod(0o755)
        needed = inspect(path, abi)
        manifest["abis"][abi] = {
            "binary_sha256": sha256(path),
            "archive_sha256": sha256(archive),
            "node_needed_libraries": needed,
        }
        print(f"STAGED {abi}: {path.stat().st_size} bytes, SHA-256 {sha256(path)}")

    (generated / "assets" / "runtime-origin.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("Both Android Node runtimes staged successfully")

if __name__ == "__main__":
    main()
