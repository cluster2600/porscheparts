"""Exercise the installed-wrapper overlay without modifying the pinned source."""
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MeshOfferRefreshPatchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("patch"), "POSIX patch is required")
    def test_refresh_preserves_listing_scope_and_frozen_source(self):
        source = ROOT / "deploy/openbao/openbao-vastai"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "openbao-vastai"
            shutil.copyfile(source, target)
            result = subprocess.run(
                ["patch", "--batch", str(target),
                 str(ROOT / "deploy/openbao/mesh-offer-refresh-scope.patch")],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            loader = SourceFileLoader("mesh_offer_overlay", str(target))
            spec = importlib.util.spec_from_loader(loader.name, loader)
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
            self.assertEqual(module.mesh_offer_query(45828237), module.mesh_offer_query())
            self.assertEqual(module.mesh_offer_query()["limit"], 50)
            self.assertEqual(module.mesh_offer_query()["num_gpus"], {"eq": 1})
            self.assertEqual(module.mesh_offer_query()["cpu_ram"], {"gte": 60000})
            self.assertEqual(module.mesh_offer_query()["verified"], {"eq": True})
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
