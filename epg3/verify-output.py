#!/usr/bin/env python3
"""Check build outputs are real Android ELFs; do not claim device runtime success."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from check_pages import check_16k

folder = Path(sys.argv[1])
abi = sys.argv[2]
specs = {"armeabi-v7a": ("ELF32", "ARM"), "arm64-v8a": ("ELF64", "AArch64")}
expected = specs[abi]
modules = ("better-sqlite3", "fs-ext", "diskusage-ng")
files = []
for module in modules:
    addons = list(folder.glob(module + "--*.node"))
    no_gyp = folder / (module + ".NO_BINDING_GYP")
    if not addons and not no_gyp.is_file():
        raise SystemExit("Missing result for " + module)
    for file in addons:
        info = subprocess.check_output(["readelf", "-h", str(file)], text=True)
        cls, mach = expected
        if not re.search(r"Class:\s+" + cls, info) or not re.search(r"Machine:\s+" + mach + r"\b", info):
            raise SystemExit("ELF architecture check failed: " + str(file))
        if not re.search(r"Type:\s+DYN", info):
            raise SystemExit("Native addon must be shared ELF: " + str(file))
        check_16k(file)
        files.append({
            "name": file.name, "bytes": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        })
print("EPG3_NATIVE_ELF_STATIC_PASS", abi, "addons=" + str(len(files)))
(folder / "build-manifest.json").write_text(
    json.dumps({"abi": abi, "node_version": "24.21.0", "epgstation": "3.0.0-beta2",
                "source_commit": "1793ab74088be8791d191c9621ab881e50741119",
                "files": files}, indent=2) + "\n"
)
