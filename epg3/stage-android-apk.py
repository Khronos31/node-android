#!/usr/bin/env python3
"""Stage both ABIs' real EPGStation native addon outputs into APK jniLibs."""
import shutil
import subprocess
import sys
from pathlib import Path

src, jni, licenses = [Path(p) for p in sys.argv[1:]]
pairs = {"better-sqlite3--better_sqlite3.node": "libepg3_better_sqlite3.so",
         "fs-ext--fs_ext.node": "libepg3_fs_ext.so"}
expected = {"armeabi-v7a": ("ELF32", "ARM"),
            "arm64-v8a": ("ELF64", "AArch64")}
for abi, (cls, machine) in expected.items():
    for pattern, name in pairs.items():
        matches = list(src.rglob(f"{abi}/{pattern}"))
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one {abi}/{pattern}, found {len(matches)}")
        dest = jni / abi / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(matches[0], dest)
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
