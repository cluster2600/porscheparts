from _deps import require_modules
require_modules('trimesh')

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import trimesh

ROOT = Path(__file__).resolve().parents[1]


class ReferenceFanPrintScreenTests(unittest.TestCase):
    def test_open_rotor_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            trimesh.Trimesh(vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                            faces=[[0, 1, 2]]).export(path / 'rotor-mm.stl')
            result = subprocess.run([
                sys.executable, str(ROOT / 'twins/993-engine-cooling-fan-system-f0/source/run_reference_print_screen.py'),
                str(path), str(path / 'output'),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('closed single solid', result.stderr)
            self.assertFalse((path / 'output').exists())
