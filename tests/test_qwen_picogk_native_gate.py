"""Check the plan trust boundary without requiring the private native runtime."""
from pathlib import Path
import subprocess
import sys
import unittest


class PicoGKNativeGateTest(unittest.TestCase):
    def test_boundary(self):
        script = Path(__file__).resolve().parents[1] / 'training/qwen-picogk-native-gate/gate.py'
        result = subprocess.run([sys.executable, str(script), '--self-check'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
