#!/usr/bin/env python3
"""Stage both ABIs' real EPGStation native addon outputs into APK jniLibs."""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from check_pages import check_16k

if len(sys.argv) != 5:
    raise SystemExit("usage: stage-android-apk.py artifacts jniLibs licenses assets")
src, jni, licenses, assets = [Path(p) for p in sys.argv[1:]]
pairs = {"better-sqlite3--better_sqlite3.node": "libepg3_better_sqlite3.so",
         "fs-ext--fs_ext.node": "libepg3_fs_ext.so"}
expected = {"armeabi-v7a": ("ELF32", "ARM"),
            "arm64-v8a": ("ELF64", "AArch64")}
for abi, (cls, machine) in expected.items():
    # C++ addons may reference the Android NDK shared C++ runtime, which is
    # not a system library. Ship the exact same pinned NDK libc++ for this ABI.
    ndk = Path(os.environ["ANDROID_NDK_HOME"])
    triple = "arm-linux-androideabi" if abi == "armeabi-v7a" else "aarch64-linux-android"
    libcxx = ndk / "toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib" / triple / "libc++_shared.so"
    if not libcxx.is_file():
        raise SystemExit(f"Pinned NDK C++ shared runtime missing: {libcxx}")
    cpp_dst = jni / abi / "libc++_shared.so"
    cpp_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(libcxx, cpp_dst)
    # Android 16 KiB page devices use 64-bit ABIs. NDK r27 bundles a
    # 16 KiB-aligned arm64 libc++, but the 32-bit armv7 libc++ uses 4 KiB.
    if abi == "arm64-v8a":
        check_16k(cpp_dst)
    print("EPG3_STAGE_CPP_RUNTIME_OK", abi, cpp_dst.stat().st_size)
    for pattern, name in pairs.items():
        matches = list(src.rglob(f"{abi}/{pattern}"))
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one {abi}/{pattern}, found {len(matches)}")
        dest = jni / abi / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(matches[0], dest)
        check_16k(dest)
        header = subprocess.check_output(["readelf", "-h", str(dest)], text=True)
        if cls not in header or machine not in header:
            raise SystemExit(f"Wrong ELF type in staged module: {dest}")
        print("EPG3_STAGE_OK", abi, name, dest.stat().st_size)
licenses.mkdir(parents=True, exist_ok=True)
for module in ("better-sqlite3", "fs-ext"):
    files = list(src.rglob(f"{module}.LICENSE"))
    if not files:
        raise SystemExit(f"Missing license for {module}")
    shutil.copyfile(files[0], licenses / f"EPG3-{module}-LICENSE")

# Stage source-package JS wrappers byte-identically from both ABI build jobs.
# Production JS must not differ between armv7a and arm64.
relpaths = [
    "better-sqlite3/lib/index.js",
    "better-sqlite3/lib/database.js",
    "better-sqlite3/lib/util.js",
    "better-sqlite3/lib/sqlite-error.js",
    "fs-ext/fs-ext.js",
    "node_modules/aribts/index.js",
    "node_modules/diskusage-ng/index.js",
    "node_modules/crc/package.json",
    "node_modules/eventemitter3/package.json",
    "node_modules/iconv-lite/package.json",
    "node_modules/safer-buffer/package.json",
]
for abi in expected:
    roots = list(src.rglob(f"{abi}/js"))
    if len(roots) != 1:
        raise SystemExit(f"Expected one {abi}/js root, got {len(roots)}")
    root = roots[0]
    for rel in relpaths:
        if not (root / rel).is_file():
            raise SystemExit(f"Missing production JS file: {abi}/{rel}")
    if abi == "armeabi-v7a":
        first_root = root
    else:
        first_files = {p.relative_to(first_root): p.read_bytes()
                       for p in first_root.rglob("*") if p.is_file()}
        second_files = {p.relative_to(root): p.read_bytes()
                        for p in root.rglob("*") if p.is_file()}
        if first_files != second_files:
            raise SystemExit("Native job production JS wrappers differ between ABIs")

out = assets / "epg3-modules"
shutil.copytree(first_root, out, dirs_exist_ok=True)
print("EPG3_PRODUCTION_JS_STAGED", len(first_files), "files")
