#!/usr/bin/env python3
"""Check Android shared-library LOAD segments for 16 KiB ELF page alignment."""
import re
import subprocess
import sys
from pathlib import Path

MIN_PAGE_SIZE = 16384


def check_16k(path: Path) -> int:
    # readelf -W keeps all program-header columns on one line, including
    # executable armv7 and arm64 headers. Flags may use one or two columns.
    output = subprocess.check_output(["readelf", "-W", "-l", str(path)], text=True)
    count = 0
    for line in output.splitlines():
        cols = line.split()
        if not cols or cols[0] != "LOAD":
            continue
        if len(cols) < 8:
            raise ValueError(f"{path}: malformed LOAD header: {line}")
        off, virt, align = int(cols[1], 16), int(cols[2], 16), int(cols[-1], 16)
        count += 1
        if align < MIN_PAGE_SIZE or align & (align - 1):
            raise ValueError(f"{path}: LOAD[{count}] invalid p_align=0x{align:x}")
        if off % MIN_PAGE_SIZE != virt % MIN_PAGE_SIZE:
            raise ValueError(f"{path}: LOAD[{count}] offset/vaddr not 16K congruent")
    if not count:
        raise ValueError(f"{path}: no LOAD segments")
    print(f"EPG3_16K_ELF_PASS {path} LOAD={count}")
    return count


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        check_16k(Path(arg))
