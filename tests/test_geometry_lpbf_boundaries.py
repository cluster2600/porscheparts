"""Dependency-free refusal checks for optional native software witnesses."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WitnessBoundaries(unittest.TestCase):
    def test_usd_brep_refuses_existing_receipt_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt"
            output.mkdir()
            receipt = output / "report.json"
            receipt.write_text("preserve prior receipt")
            result = subprocess.run(
                [sys.executable, str(ROOT / "containers/examples/usd_brep_smoke.py"),
                 "--output", str(output)], capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FileExistsError", result.stderr)
            self.assertEqual(receipt.read_text(), "preserve prior receipt")

    def test_go_melt_rejects_changed_source_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "go_melt").mkdir()
            (root / "go_melt/computeFunctions.py").write_text("raise RuntimeError('must not execute')")
            output = root / "receipt"
            result = subprocess.run(
                [sys.executable, str(ROOT / "benchmarks/go-melt/smoke.py"),
                 "--source", str(root), "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unreviewed GO-MELT kernel revision", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
