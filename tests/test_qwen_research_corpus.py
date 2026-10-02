"""Exercise the existing curation and registered-selection self-checks in CI."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ResearchCorpusTest(unittest.TestCase):
    def test_curation_and_selection(self):
        for script in ('prepare.py', 'run.py', 'continue.py'):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, str(ROOT / 'training/qwen-research-corpus' / script), 'self-check'],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
