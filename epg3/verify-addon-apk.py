#!/usr/bin/env python3
"""Ensure APK retains byte-identical cross-compiled Android addons."""
import hashlib
import sys
import zipfile
from pathlib import Path

apk, staged = Path(sys.argv[1]), Path(sys.argv[2])
with zipfile.ZipFile(apk) as package:
    for abi in ("armeabi-v7a", "arm64-v8a"):
        for name in ("libepg3_better_sqlite3.so", "libepg3_fs_ext.so", "libc++_shared.so"):
            key = f"lib/{abi}/{name}"
            raw = package.read(key)
            disk = (staged / abi / name).read_bytes()
            if raw != disk or raw[:4] != b"\x7fELF":
                raise SystemExit(f"Bad staged native addon {key}")
            print("EPG3_APK_MODULE_OK", key, hashlib.sha256(raw).hexdigest())
    for name in ("better-sqlite3", "fs-ext"):
        lic = f"assets/licenses/EPG3-{name}-LICENSE"
        if not package.read(lic):
            raise SystemExit("License missing in APK: " + lic)
print("EPG3_LEGACY_ADDON_APK_STATIC_PASS", apk.stat().st_size)
