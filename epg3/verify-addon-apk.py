#!/usr/bin/env python3
"""Ensure APK retains byte-identical cross-compiled Android addons."""
import hashlib
import tempfile
from check_pages import check_16k
import sys
import zipfile
from pathlib import Path
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
    # Check ALL native libraries shipped to arm64, including the Node PIE
    # and N-API smoke addon. This is the key missing check in previous APKs.
    # The NDK r27 armeabi-v7a libc++ has 4 KiB pages; skip only this 32-bit
    # system prebuilt, never skip custom armv7 binaries.
    with tempfile.TemporaryDirectory(prefix="epg3-check-pages-") as tmp:
        for abi in ("armeabi-v7a", "arm64-v8a"):
            names = [item for item in package.namelist()
                     if item.startswith(f"lib/{abi}/") and item.endswith(".so")]
            if not names:
                raise SystemExit(f"Missing native libs for {abi}")
            for name in names:
                if abi == "armeabi-v7a" and name.endswith("/libc++_shared.so"):
                    print("ARM32_NDK_LIBCXX_4K_EXCEPTION", name)
                    continue
                dest = Path(tmp) / abi / Path(name).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(package.read(name))
                check_16k(dest)
                print("APK_16K_LOAD_PASS", name)

    for name in ("better-sqlite3", "fs-ext"):
        lic = f"assets/licenses/EPG3-{name}-LICENSE"
        if not package.read(lic):
            raise SystemExit("License missing in APK: " + lic)
    for required in (
        "assets/epg3-modules/better-sqlite3/lib/index.js",
        "assets/epg3-modules/better-sqlite3/lib/database.js",
        "assets/epg3-modules/better-sqlite3/lib/methods/wrappers.js",
        "assets/epg3-modules/fs-ext/fs-ext.js",
        "assets/epg3-functional-smoke.js",
        "assets/epg3-js-deps-smoke.js",
        "assets/epg3-modules/node_modules/aribts/index.js",
        "assets/epg3-modules/node_modules/diskusage-ng/index.js",
    ):
        if not package.read(required):
            raise SystemExit("Missing production JS/functional test: " + required)
print("EPG3_LEGACY_ADDON_APK_STATIC_PASS", apk.stat().st_size)
