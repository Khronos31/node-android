"""ELF program header size/alignment regression tests without Android toolchain."""
import sys
import unittest
import struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_elf_pages import check_bytes


def fake(elf_class, align=16384, offset=0x4000, vaddr=0x8000):
    # Tiny intentionally synthetic ELF: enough program headers for layout gate.
    head = bytearray(128)
    head[0:6] = b"\x7fELF" + bytes([elf_class, 1])
    if elf_class == 1:
        struct.pack_into("<I", head, 28, 64)
        struct.pack_into("<HH", head, 42, 32, 1)
        struct.pack_into("<IIIIIIII", head, 64,
                         1, offset, vaddr, 0, 1, 1, 5, align)
    else:
        struct.pack_into("<Q", head, 32, 64)
        struct.pack_into("<HH", head, 54, 56, 1)
        struct.pack_into("<IIQQQQQQ", head, 64,
                         1, 5, offset, vaddr, 0, 1, 1, align)
    return bytes(head)


class PageAlignmentTests(unittest.TestCase):
    def test_16k_loads_for_both_abis(self):
        for cls in (1, 2):
            with self.subTest(cls=cls):
                self.assertEqual(check_bytes(fake(cls)), 1)

    def test_4k_load_rejected(self):
        for cls in (1, 2):
            with self.subTest(cls=cls), self.assertRaisesRegex(
                    ValueError, "alignment"):
                check_bytes(fake(cls, align=4096))

    def test_incongruent_offsets_rejected(self):
        for cls in (1, 2):
            with self.subTest(cls=cls), self.assertRaisesRegex(
                    ValueError, "congruent"):
                check_bytes(fake(cls, offset=0x1000, vaddr=0x2000))

    def test_no_program_header_rejected(self):
        with self.assertRaises(ValueError):
            check_bytes(b"\x7fELF\x02\x01" + b"\x00" * 120)


if __name__ == "__main__":
    unittest.main()
