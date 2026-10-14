import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scan917", ROOT / "models/917-engine-reconstruction/source/reconstruct.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReconstructionTests(unittest.TestCase):
    def test_execution_evidence_matches_sources_without_engine_release(self):
        receipt = json.loads((ROOT / "models/917-engine-reconstruction/execution-20261010.json").read_text())
        for name, expected in receipt["toolchain"]["source_sha256"].items():
            self.assertEqual(MODULE.sha256(ROOT / "models/917-engine-reconstruction/source" / name), expected)
        self.assertFalse(any(receipt["release_gates"].values()))
        self.assertIsNone(receipt["physical_units"])
        self.assertEqual(len(receipt["accepted_geometry_runs"]), 2)
        self.assertEqual(len(receipt["rejected_runs"]), 1)

    def test_resolution_requires_distinct_finite_positive_levels(self):
        self.assertEqual(MODULE.check_voxels([1.5, 3]), [3, 1.5])
        for values in ([1], [1, 1], [0, 1], [-1, 1], [float("nan"), 1], [float("inf"), 1]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                MODULE.check_voxels(values)

    def test_outputs_cannot_publish_geometry_or_overwrite_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            original = MODULE.ROOT
            MODULE.ROOT = Path(directory).resolve()
            try:
                for path in (MODULE.ROOT, MODULE.ROOT / "work", MODULE.ROOT / "models/out", MODULE.ROOT / "work/../out"):
                    with self.subTest(path=path), self.assertRaises(ValueError):
                        MODULE.check_output(path)
                valid = MODULE.ROOT / "work/new"
                self.assertEqual(MODULE.check_output(valid), valid)
                valid.mkdir(parents=True)
                with self.assertRaises(ValueError):
                    MODULE.check_output(valid)
            finally:
                MODULE.ROOT = original

    def test_independent_audit_rejects_open_mesh_and_measures_closed_mesh(self):
        try:
            import trimesh
            import rtree  # required by closest_point
            import scipy.spatial
        except ImportError:
            self.skipTest("trimesh/rtree/scipy absent")
        cube = trimesh.creation.box()
        audit = MODULE.audit(cube, cube, samples=40)
        self.assertTrue(audit["watertight"])
        self.assertAlmostEqual(audit["source_to_shell_distance_source_units"]["max_sampled"], 0)
        self.assertEqual(audit["connected_surface_components"], 1)
        cube.update_faces(list(range(len(cube.faces) - 1)))
        with self.assertRaises(ValueError):
            MODULE.audit(cube, cube, samples=40)

    def test_wrong_source_hash_stops_before_build_or_output_creation(self):
        try:
            import trimesh
        except ImportError:
            self.skipTest("trimesh absent")
        with tempfile.TemporaryDirectory() as directory:
            original = MODULE.ROOT
            MODULE.ROOT = Path(directory).resolve()
            try:
                source = MODULE.ROOT / "wrong.obj"
                source.write_text("v 0 0 0\n")
                output = MODULE.ROOT / "work/new"
                with self.assertRaisesRegex(ValueError, "source scan hash mismatch"):
                    MODULE.run(source, output, "must-never-run-dotnet", [3, 1.5])
                self.assertFalse(output.exists())
            finally:
                MODULE.ROOT = original


if __name__ == "__main__":
    unittest.main()
