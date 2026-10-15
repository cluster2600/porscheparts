"""Recovery must reject changed weights and receipts before model loading."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1] / 'training/qwen-picogk-20261012'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PicoGKRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.run = self.root / 'run-001'
        (self.run / 'adapter').mkdir(parents=True)
        self.adapter = self.run / 'adapter/adapters.safetensors'
        self.adapter.write_bytes(b'retained-adapter')
        self.base = self.root / 'model/model.safetensors'
        self.base.parent.mkdir()
        self.base.write_bytes(b'pinned-base')
        self.manifest = self.run / 'FROZEN-RUN.json'
        self.manifest.write_text(json.dumps({'files': [
            {'path': 'adapter/adapters.safetensors', 'sha256': digest(self.adapter)}]}))
        self.profile = self.root / 'profile.json'
        self.write_profile()

    def write_profile(self):
        self.profile.write_text(json.dumps({
            'selected_run_manifest_sha256': digest(self.manifest),
            'selected_adapter_sha256': digest(self.adapter),
            'model_files_sha256': {'model.safetensors': digest(self.base)}}))

    def check_recovery(self):
        # Separate imports from the other training packages' curriculum modules.
        code = ('import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); '
                'import ask; ask.RECOVERY_PROFILE = Path(sys.argv[2]); '
                'print(ask.recovered_base(Path(sys.argv[3]), Path(sys.argv[3])))')
        return subprocess.run([sys.executable, '-c', code, str(HERE), str(self.profile), str(self.root)],
                              capture_output=True, text=True, timeout=30)

    def test_relocation_preserves_identity(self):
        result = self.check_recovery()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(self.base.parent.resolve()))

    def test_changed_base_rejected(self):
        self.base.write_bytes(b'different-base')
        result = self.check_recovery()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('base model file changed', result.stderr)

    def test_changed_adapter_rejected(self):
        self.adapter.write_bytes(b'different-adapter')
        result = self.check_recovery()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Retained run file changed', result.stderr)

    def test_changed_manifest_rejected(self):
        self.manifest.write_text('{"files": []}')
        result = self.check_recovery()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manifest changed', result.stderr)

    def test_escaping_path_rejected(self):
        self.manifest.write_text(json.dumps({'files': [
            {'path': '../model/model.safetensors', 'sha256': digest(self.base)}]}))
        self.write_profile()
        result = self.check_recovery()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('escaped its directory', result.stderr)
