"""Check the large-file ratchet: its register, and that it refuses what it should."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_file_sizes.py"
REGISTER = ROOT / "catalog" / "registers" / "large-files.json"


def run_gate(script):
    """Run a specific copy of the gate; it resolves the repository from its own path."""
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True)


class LargeFileRegisterTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(REGISTER.read_text(encoding="utf-8"))

    def test_register_shape(self):
        self.assertEqual(self.doc["schema_version"], 1)
        self.assertEqual(self.doc["threshold_bytes"], 1048576)
        self.assertTrue(self.doc["rationale"].strip())

    def test_every_entry_carries_a_path_and_a_reason(self):
        paths = set()
        for entry in self.doc["entries"]:
            self.assertTrue(entry["path"].strip(), entry)
            self.assertTrue(entry["reason"].strip(), entry["path"])
            self.assertGreaterEqual(entry["bytes"], self.doc["threshold_bytes"], entry["path"])
            self.assertNotIn(entry["path"], paths, "duplicate register entry")
            paths.add(entry["path"])

    def test_register_sorted_so_diffs_stay_readable(self):
        paths = [entry["path"] for entry in self.doc["entries"]]
        self.assertEqual(paths, sorted(paths))


class LargeFileGateTests(unittest.TestCase):
    def test_repository_passes_its_own_gate(self):
        result = run_gate(SCRIPT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gate_refuses_an_unadmitted_payload(self):
        """A throwaway repository with one oversized blob must fail, not pass."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
            subprocess.run(["git", "-C", str(work), "config", "user.email", "t@example.com"], check=True)
            subprocess.run(["git", "-C", str(work), "config", "user.name", "t"], check=True)
            register = work / "catalog" / "registers"
            register.mkdir(parents=True)
            (register / "large-files.json").write_text(json.dumps({
                "schema_version": 1, "threshold_bytes": 1048576,
                "recorded_on": "2026-10-29", "rationale": "test", "entries": [],
            }), encoding="utf-8")
            scripts = work / "scripts"
            scripts.mkdir()
            (scripts / "validate_file_sizes.py").write_bytes(SCRIPT.read_bytes())
            (work / "payload.npz").write_bytes(b"\0" * (2 * 1048576))
            subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(work), "commit", "-qm", "seed"], check=True)

            result = run_gate(scripts / "validate_file_sizes.py")
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("payload.npz", result.stdout)
            self.assertIn("1 path(s) refused", result.stdout)


if __name__ == "__main__":
    unittest.main()
