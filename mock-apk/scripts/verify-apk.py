#!/usr/bin/env python3
"""Static verification of unsigned internals in a debug-signed mock APK."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("apk", type=Path)
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / ".generated/assets/runtime-origin.json").read_text())
required = {
    "classes.dex", "assets/basic-smoke.js", "assets/native-addon-smoke.js",
    "assets/runtime-origin.json", "assets/licenses/Node-LICENSE"
}
for abi in ("armeabi-v7a", "arm64-v8a"):
    required.update([f"lib/{abi}/libnode_exec.so", f"lib/{abi}/libnapi_smoke.so"])
with zipfile.ZipFile(args.apk) as apk:
    if apk.testzip() is not None:
        raise RuntimeError("APK ZIP CRC failure")
    missing = required - set(apk.namelist())
    if missing:
        raise RuntimeError(f"Missing APK payload: {sorted(missing)}")
    for abi in ("armeabi-v7a", "arm64-v8a"):
        binary = apk.read(f"lib/{abi}/libnode_exec.so")
        h = hashlib.sha256(binary).hexdigest()
        if h != manifest["abis"][abi]["binary_sha256"]:
            raise RuntimeError("Node binary differs from pinned staged runtime: " + abi)
        addon = apk.read(f"lib/{abi}/libnapi_smoke.so")
        if not addon.startswith(b"\x7fELF"):
            raise RuntimeError("N-API addon is not ELF: " + abi)
        print("APK_OK", abi, "node_sha256=" + h, "addon_bytes=" + str(len(addon)))
    origin = json.loads(apk.read("assets/runtime-origin.json"))
    if origin != manifest:
        raise RuntimeError("Runtime provenance in APK differs from staging manifest")
print("APK verification succeeded:", args.apk, args.apk.stat().st_size)
