#!/usr/bin/env python3
"""Promote exactly two fingerprint-matched Node Android CI binary archives."""
import argparse
import hashlib
import json
import re
import struct
import tarfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_elf_pages import check_bytes

ABIS = {"armeabi-v7a": (1, 40), "arm64-v8a": (2, 183)}
REPO = "Khronos31/node-android"
FILES = ("bin/node", "LICENSE", "BUILD-METADATA.json")
# Python tarfile normalizes directory names, stripping trailing slashes.
MEMBERS = {".", "./bin", "./bin/node", "./LICENSE",
           "./BUILD-METADATA.json", "./SHA256SUMS"}
SHA = re.compile(r"[0-9a-f]{40}\Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def must(ok, message):
    if not ok:
        raise ValueError(message)


def validate_elf(blob, abi):
    cls, machine = ABIS[abi]
    must(len(blob) >= 20 and blob[:4] == b"\x7fELF", f"{abi}: bad ELF")
    must(blob[4] == cls and blob[5] == 1, f"{abi}: class/endian mismatch")
    must(struct.unpack_from("<H", blob, 16)[0] == 3, f"{abi}: not PIE ET_DYN")
    must(struct.unpack_from("<H", blob, 18)[0] == machine,
         f"{abi}: incorrect ELF architecture")


def validate_run(run, run_id):
    must(run.get("id") == run_id, "CI run ID mismatch")
    must(run.get("status") == "completed" and run.get("conclusion") == "success",
         "CI run did not succeed")
    must(run.get("name") == "Build Node.js for Android", "Wrong workflow")
    must((run.get("repository") or {}).get("full_name") == REPO,
         "Wrong CI repository")
    head = run.get("head_sha", "")
    must(SHA.fullmatch(head) is not None, "Missing CI source head")
    return head


def validate_archive(file, abi, lock, patch_hashes):
    must(file.is_file(), f"Missing {file}")
    with tarfile.open(file, "r:xz") as tf:
        members = tf.getmembers()
        names = [m.name for m in members]
        must(set(names) == MEMBERS and len(names) == len(MEMBERS),
             f"{abi}: unexpected/duplicate archive entries: {names}")
        blobs = {}
        for path in FILES + ("SHA256SUMS",):
            m = tf.getmember("./" + path)
            must(m.isfile() and not m.issym() and not m.islnk(),
                 f"{abi}: non-regular or linked member: {path}")
            blobs[path] = tf.extractfile(m).read()
        must(tf.getmember("./bin/node").mode & 0o111,
             f"{abi}: binary lacks execute permission")
    lines = blobs["SHA256SUMS"].decode("ascii").splitlines()
    checks = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9/_.-]+)", line)
        must(match is not None, f"{abi}: bad SHA256SUMS line")
        hashed, path = match.groups()
        must(path in FILES and path not in checks,
             f"{abi}: unexpected or duplicate checksum entry: {path}")
        checks[path] = hashed
    must(set(checks) == set(FILES), f"{abi}: incomplete SHA256SUMS")
    for path in FILES:
        must(checks[path] == digest(blobs[path]),
             f"{abi}: checksum failed: {path}")
    validate_elf(blobs["bin/node"], abi)
    check_bytes(blobs["bin/node"], f"{abi}/bin/node")
    meta = json.loads(blobs["BUILD-METADATA.json"])
    expected = {
        "node_version": lock["version"],
        "source_url": lock["source_url"],
        "source_sha256": lock["sha256"],
        "ndk_version": lock["ndk_version"],
        "android_api": lock["android_api"],
        "android_abi": abi,
        "source_repo": REPO,
        "host": "linux-x86_64",
        "binary_sha256": digest(blobs["bin/node"]),
        "patch_sha256": patch_hashes,
    }
    for field, value in expected.items():
        must(meta.get(field) == value,
             f"{abi}: build metadata drift: {field}")
    must(SHA.fullmatch(meta.get("source_commit", "")) is not None,
         f"{abi}: missing recorded CI checkout")
    must(len(blobs["LICENSE"]) > 1000, f"{abi}: missing Node LICENSE")
    return {
        "name": file.name,
        "size_bytes": file.stat().st_size,
        "sha256": digest(file.read_bytes()),
        "binary_sha256": meta["binary_sha256"],
        "ci_checkout_sha": meta["source_commit"],
    }


def promote(repo, assets, run, run_id, tag, commit, tool_commit):
    lock = json.loads((repo / "versions/node-24.json").read_text())
    must(re.fullmatch(rf"v{re.escape(lock['version'])}-android\.[1-9][0-9]*",
                      tag) is not None, "Invalid pinned Node Android tag")
    must(SHA.fullmatch(commit) is not None, "Invalid release tag commit")
    must(SHA.fullmatch(tool_commit) is not None,
         "Invalid promotion workflow checkout commit")
    head = validate_run(run, run_id)
    patches = {p.name: digest(p.read_bytes())
               for p in sorted((repo / "patches/node-24").glob("*.patch"))}
    must(patches, "Missing patch set")
    archives = {}
    for abi in ABIS:
        filename = f"node-v{lock['version']}-android-{abi}.tar.xz"
        archives[abi] = validate_archive(assets / filename, abi, lock, patches)
        print("ARCHIVE_VERIFIED", abi, archives[abi]["sha256"])
    must(sorted(x.name for x in assets.glob("*.tar.xz")) ==
         sorted(x["name"] for x in archives.values()),
         "Unexpected binary release archive")
    must(len({a["ci_checkout_sha"] for a in archives.values()}) == 1,
         "Binary archives were built against different CI checkouts")
    provenance = {
        "release_tag": tag, "release_commit": commit,
        "promotion_workflow_commit": tool_commit,
        "node_version": lock["version"],
        "android_api_min": lock["android_api"],
        "ndk_version": lock["ndk_version"],
        "source_sha256": lock["sha256"], "source_url": lock["source_url"],
        "build_run_id": run_id,
        "build_run_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
        "build_head_sha": head,
        "ci_checkout_sha": next(iter(archives.values()))["ci_checkout_sha"],
        "patch_sha256": patches,
        "archives": archives,
        "device_test_note": (
            "An earlier source/patch-matched build (run 39220534794) passed "
            "real-device testing on both Android ABIs. These promoted -j4 "
            "archives have not themselves been retested byte-for-byte."
        ),
    }
    (assets / "RELEASE-METADATA.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    (assets / "SHA256SUMS").write_text("".join(
        f"{archives[abi]['sha256']}  {archives[abi]['name']}\n"
        for abi in sorted(ABIS)))
    print("RELEASE_PAYLOAD_VERIFIED", tag, run_id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True, type=Path)
    ap.add_argument("--assets", required=True, type=Path)
    ap.add_argument("--run-json", required=True, type=Path)
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--release-commit", required=True)
    ap.add_argument("--tool-commit", required=True)
    a = ap.parse_args()
    promote(a.repo_root, a.assets, json.loads(a.run_json.read_text()),
            a.run_id, a.tag, a.release_commit, a.tool_commit)


if __name__ == "__main__":
    main()
