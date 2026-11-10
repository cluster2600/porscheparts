"""The independent witness check rejects incorrectly scaled or positioned domains."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import trimesh

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "linux_witness_check", ROOT / "twins/962-cylinder-head-f0/source/linux_runtime/check_witness.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class LinuxWitnessCheckTests(unittest.TestCase):
    def test_dimensioned_boxes_and_nonempty_lattice_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, x in (("metal_domain", 0), ("coolant_domain", 40), ("dry_domain", 80), ("lattice", 0)):
                mesh = trimesh.creation.box(extents=[10, 20, 30])
                mesh.apply_translation([x, 0, 15])
                mesh.export(root / (name + ".stl"))
            result = checker.check(root)
            self.assertTrue(result["passed"])
            self.assertFalse(result["physical_qualification"])
            self.assertEqual(len(result["mesh_sha256"]), 4)
            # Volume alone cannot detect a misplaced domain.
            path = root / "coolant_domain.stl"
            mesh = trimesh.load(path, force="mesh")
            mesh.apply_translation([1, 0, 0])
            mesh.export(path)
            result = checker.check(root)
            self.assertFalse(result["passed"])
            self.assertFalse(result["checks"]["coolant_domain"]["passed"])


if __name__ == "__main__":
    unittest.main()
