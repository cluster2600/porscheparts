"""Released openbao-vastai delta (issue #422): pinned patch and variant hashes.

The repository wrapper stays frozen at its F46-pinned hash; the release is the
delta below, applied to a disposable copy. No network or secrets.
"""
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "42fe39ebcf7fc81e8f6c4a85e38fa9da03fd4637bb93a37b3a422c315e8a5aa4"
PATCH_SHA256 = "079a005b2bbeeba5db7b06663948a2a32e266efd9b45e4225111f11eae58ee15"
# Pinned source + this delta.
VARIANT_SHA256 = "f4a0e09f768d10c7d2975547d9b10fb17d77d5bc35094e40f37d2809ac559a20"
# Pinned source + wrapper-fea512.patch + this delta.
FEA512_STACK_SHA256 = "d25f7ceed075e4bcb6ff15cfcc785425d5cf575187c180949c7572211a018fd3"


class MeshOfferRefreshPatchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("patch"), "POSIX patch is required")
    def test_refresh_preserves_listing_scope_and_frozen_source(self):
        source = ROOT / "deploy/openbao/openbao-vastai"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(before, SOURCE_SHA256)
        patch_file = ROOT / "deploy/openbao/mesh-offer-refresh-scope.patch"
        self.assertEqual(hashlib.sha256(patch_file.read_bytes()).hexdigest(), PATCH_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "openbao-vastai"
            shutil.copyfile(source, target)
            result = subprocess.run(
                ["patch", "--batch", str(target),
                 str(ROOT / "deploy/openbao/mesh-offer-refresh-scope.patch")],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), VARIANT_SHA256)
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

    @unittest.skipUnless(shutil.which("patch"), "POSIX patch is required")
    def test_delta_stacks_on_fea512_variant(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "openbao-vastai"
            shutil.copyfile(ROOT / "deploy/openbao/openbao-vastai", target)
            for delta in ("deploy/vast/m64-fea512/wrapper-fea512.patch",
                          "deploy/openbao/mesh-offer-refresh-scope.patch"):
                result = subprocess.run(["patch", "--batch", str(target), str(ROOT / delta)],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), FEA512_STACK_SHA256)
