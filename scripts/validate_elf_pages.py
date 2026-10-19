#!/usr/bin/env python3
"""Reject Android native ELF binaries with PT_LOAD alignment below 16 KiB.

This is an ELF *layout* gate, not a substitute for runtime tests on a
real 16 KiB-page Android device. Handles both 32- and 64-bit little-endian ELFs.
"""
import argparse
import struct
from pathlib import Path

PAGE_SIZE = 16 * 1024
PT_LOAD = 1


def check_bytes(raw: bytes, source: str = "<memory>") -> int:
    if len(raw) < 64 or raw[:4] != b"\x7fELF":
        raise ValueError(f"{source}: missing/truncated ELF header")
    elf_class, endian = raw[4:6]
    if elf_class not in (1, 2) or endian != 1:
        raise ValueError(f"{source}: expected 32/64-bit little-endian ELF")
    if elf_class == 1:
        header_offset, count_offset, entry_fmt = 28, 42, "<IIIIIIII"
    else:
        header_offset, count_offset, entry_fmt = 32, 54, "<IIQQQQQQ"
    phoff = struct.unpack_from("<I" if elf_class == 1 else "<Q",
                               raw, header_offset)[0]
    phentsize, phnum = struct.unpack_from("<HH", raw, count_offset)
    entry_size = struct.calcsize(entry_fmt)
    if phnum == 0 or phnum == 0xFFFF or phentsize < entry_size:
        raise ValueError(f"{source}: missing/unsupported program headers")
    if phoff + phentsize * phnum > len(raw):
        raise ValueError(f"{source}: truncated program header table")
    checked = 0
    for n in range(phnum):
        items = struct.unpack_from(entry_fmt, raw, phoff + n * phentsize)
        if items[0] != PT_LOAD:
            continue
        if elf_class == 1:
            _, offset, vaddr, _, _, _, _, align = items
        else:
            _, _, offset, vaddr, _, _, _, align = items
        checked += 1
        if align < PAGE_SIZE or align & (align - 1):
            raise ValueError(
                f"{source}: LOAD[{n}] alignment 0x{align:x} "
                f"is not at least 0x{PAGE_SIZE:x}")
        if offset % PAGE_SIZE != vaddr % PAGE_SIZE:
            raise ValueError(
                f"{source}: LOAD[{n}] p_offset/p_vaddr not 16 KiB congruent")
    if not checked:
        raise ValueError(f"{source}: no PT_LOAD segments")
    return checked


def check_file(path: Path) -> int:
    count = check_bytes(path.read_bytes(), str(path))
    print(f"16K_ELF_PASS {path} LOAD={count}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", nargs="+", type=Path)
    args = parser.parse_args()
    for elf in args.elf:
        check_file(elf)
