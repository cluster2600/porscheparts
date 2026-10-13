"""Check the registered synthetic course without loading model weights."""
from pathlib import Path
import subprocess
import sys
import unittest


class PicoGKRobustnessTest(unittest.TestCase):
    def test_course_contract(self):
        script = Path(__file__).resolve().parents[1]/'training/qwen-picogk-robustness-20261013/run.py'
        result = subprocess.run([sys.executable, str(script), 'self-check'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_paired_correction_contract(self):
        script = Path(__file__).resolve().parents[1]/'training/qwen-picogk-robustness-20261013/correction.py'
        result = subprocess.run([sys.executable, str(script), 'self-check'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
