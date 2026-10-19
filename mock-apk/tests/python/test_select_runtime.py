"""Offline regression tests for PR-based Node runtime selection."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from select_runtime import validate


class TestSelection(unittest.TestCase):
    def test_reference(self):
        self.assertEqual(validate({"source": "reference", "runtime_run_id": None}),
                         ("reference", ""))

    def test_custom_node_ci(self):
        self.assertEqual(
            validate({"source": "run-artifacts", "runtime_run_id": 39220534794}),
            ("run-artifacts", "39220534794"))

    def test_rejects_missing_id(self):
        for bad_id in (None, "", "1234", 0, -1, True):
            with self.subTest(run_id=bad_id):
                with self.assertRaises(ValueError):
                    validate({"source": "run-artifacts", "runtime_run_id": bad_id})

    def test_rejects_ambiguous_reference(self):
        with self.assertRaises(ValueError):
            validate({"source": "reference", "runtime_run_id": 123})

    def test_rejects_extra_or_unknown_fields(self):
        for data in (
            {"source": "reference"},
            {"source": "reference", "runtime_run_id": None, "unexpected": 1},
            {"source": "untrusted", "runtime_run_id": 123},
            {},
            [],
        ):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    validate(data)


if __name__ == "__main__":
    unittest.main()
