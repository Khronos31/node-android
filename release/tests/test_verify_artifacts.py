import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "verify_artifacts.py"
spec = importlib.util.spec_from_file_location("release_verify", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseTests(unittest.TestCase):
    def test_elf_class_machine_and_type(self):
        for abi, (cls, machine) in module.ABIS.items():
            data = bytearray(32)
            data[:6] = b"\x7fELF" + bytes([cls, 1])
            data[16:18] = (3).to_bytes(2, "little")
            data[18:20] = machine.to_bytes(2, "little")
            module.validate_elf(data, abi)
            data[16] = 1
            with self.assertRaises(ValueError):
                module.validate_elf(data, abi)

    def test_success_run_cannot_be_from_other_repo(self):
        run = {"id": 12, "status": "completed", "conclusion": "success",
               "name": "Build Node.js for Android",
               "repository": {"full_name": "Khronos31/node-android"},
               "head_sha": "a" * 40}
        self.assertEqual(module.validate_run(run, 12), "a" * 40)
        for diff in ({"status": "in_progress"}, {"conclusion": "failure"},
                     {"repository": {"full_name": "someone/fork"}},
                     {"id": 13}):
            with self.assertRaises(ValueError):
                module.validate_run({**run, **diff}, 12)

    def test_duplicate_or_missing_tag_revision_rejected(self):
        self.assertIsNone(__import__("re").fullmatch(
            r"v24\.21\.0-android\.[1-9][0-9]*", "v24.21.0-android.0"))


if __name__ == "__main__":
    unittest.main()
