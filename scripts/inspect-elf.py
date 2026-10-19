#!/usr/bin/env python3
"""Check that a Node ELF binary can be shipped as an Android app native lib."""
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: inspect-elf.py <node-binary> <armeabi-v7a|arm64-v8a>")
binary = Path(sys.argv[1])
abi = sys.argv[2]
expected = {
    "armeabi-v7a": ("ELF32", "ARM", "/system/bin/linker"),
    "arm64-v8a": ("ELF64", "AArch64", "/system/bin/linker64"),
}
if abi not in expected:
    raise SystemExit("Unsupported Android ABI: " + abi)
cls, machine, linker = expected[abi]

def run(*args):
    return subprocess.check_output(("readelf", *args, str(binary)), text=True)

header = run("-h")
program = run("-l")
dynamic = run("-d")
if not re.search(r"Class:\s+" + cls, header):
    raise SystemExit(f"Wrong ELF class for {abi}")
if not re.search(r"Machine:\s+" + machine + r"\b", header):
    raise SystemExit(f"Wrong ELF architecture for {abi}")
if not re.search(r"Type:\s+DYN\b", header):
    raise SystemExit("Android Node binary must be PIE (ELF DYN)")
if f"[Requesting program interpreter: {linker}]" not in program:
    raise SystemExit("Wrong Android PIE program interpreter: " + linker)

needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
# Android platform libs only: no Termux-installed ICU/OpenSSL/zlib/libc++.
allowed = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libz.so"}
extra = set(needed) - allowed
if extra:
    raise SystemExit(f"Unexpected unbundled shared dependencies: {sorted(extra)}")
if not needed:
    raise SystemExit("No Android Bionic dependencies found; suspicious runtime ELF")
print(f"OK: {abi}, PIE, {linker}, NEEDED={needed}")
