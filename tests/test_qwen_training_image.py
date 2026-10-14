"""L'image d'entraînement doit refuser ses entrées invalides avant MLX."""
from pathlib import Path
import subprocess
import sys
import unittest


class QwenTrainingImageTest(unittest.TestCase):
    @unittest.skipIf(sys.version_info < (3, 12), 'The training image requires Python >= 3.12.')
    def test_cpu_trust_boundaries(self):
        script = Path(__file__).resolve().parents[1]/'containers/qwen-picogk-training-vast/image_smoke.py'
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"training_started": false', result.stdout)


if __name__ == '__main__':
    unittest.main()
