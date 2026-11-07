"""Supplement the hash-pinned field test with exact rejection diagnostics."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.environ.get("FIELD_LATTICE_DLL") and os.environ.get("DOTNET"),
                     "native field runtime not selected")
class FieldPreflightTests(unittest.TestCase):
    def test_rejections_are_validation_errors_not_runtime_failures(self):
        payload = {"schema_version": 1, "voxel_mm": .5,
                   "frame": "F0_GLOBAL_X_forward_Y_left_Z_up", "value_unit": "MPa",
                   "rows": [[0, 0, 0, 1, 1, 1]]}
        cases = [({**payload, "value_unit": "Pa"}, "Unsupported field contract"),
                 ({**payload, "rows": payload["rows"] * 2}, "Duplicate sparse positions"),
                 ({**payload, "rows": [[.1, 0, 0, 1, 1, 1]]}, "Invalid sparse samples"),
                 (payload, "Output already exists")]
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "samples.json", Path(folder) / "output"
            for data, message in cases:
                with self.subTest(message=message):
                    if message == "Output already exists":
                        output.mkdir()
                        (output / "keep").write_text("unchanged")
                    source.write_text(json.dumps(data))
                    result = subprocess.run(
                        [os.environ["DOTNET"], os.environ["FIELD_LATTICE_DLL"], str(source), str(output)],
                        capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)
                    if message == "Output already exists":
                        self.assertEqual((output / "keep").read_text(), "unchanged")
                    else:
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
