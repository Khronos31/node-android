import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from importlib import import_module
module = import_module("verify-upstream")

class TestPinnedManifest(unittest.TestCase):
    def setUp(self):
        self.ok = {"version": "3.0.0-beta2", "engines": {"node": ">=24"},
                   "dependencies": {"better-sqlite3": "12.11.1",
                                    "fs-ext": "2.1.1", "diskusage-ng": "1.0.4"}}
    def test_pinned(self):
        self.assertTrue(module.verify(self.ok, {"dependencies": self.ok["dependencies"]}))
    def test_dependency_drift(self):
        wrong = dict(self.ok["dependencies"], **{"better-sqlite3": "13.0.3"})
        with self.assertRaises(RuntimeError):
            module.verify(self.ok, {"dependencies": wrong})
    def test_engine_requirement(self):
        upstream = dict(self.ok, engines={"node": ">=22"})
        with self.assertRaises(RuntimeError):
            module.verify(upstream, {"dependencies": self.ok["dependencies"]})

if __name__ == "__main__":
    unittest.main()
