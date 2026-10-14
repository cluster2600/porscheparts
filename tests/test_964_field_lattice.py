import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/964-chassis/monocoque/field-lattice"
if np is not None:
    spec = importlib.util.spec_from_file_location("field_lattice_prepare", SOURCE / "prepare.py")
    field = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(field)


@unittest.skipIf(np is None, "numpy not installed")
class FieldLatticeTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("FIELD_LATTICE_DLL") and os.environ.get("DOTNET"), "native Mac runtime not selected")
    def test_native_rejects_wrong_units_duplicate_points_and_existing_output(self):
        payload = {"schema_version": 1, "voxel_mm": .5,
                   "frame": "F0_GLOBAL_X_forward_Y_left_Z_up", "value_unit": "MPa",
                   "rows": [[0, 0, 0, 1, 1, 1]]}
        with tempfile.TemporaryDirectory() as tmp:
            sample, output = Path(tmp)/"sample.json", Path(tmp)/"output"
            variants = [{**payload, "value_unit": "Pa"},
                        {**payload, "rows": payload["rows"]*2},
                        {**payload, "rows": [[.1, 0, 0, 1, 1, 1]]}]
            for bad in variants:
                sample.write_text(json.dumps(bad))
                result = subprocess.run([os.environ["DOTNET"], os.environ["FIELD_LATTICE_DLL"], str(sample), str(output)],
                                        capture_output=True, timeout=20)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("unchanged")
            sample.write_text(json.dumps(payload))
            result = subprocess.run([os.environ["DOTNET"], os.environ["FIELD_LATTICE_DLL"], str(sample), str(output)],
                                    capture_output=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), "unchanged")

    def test_tensor_order_and_zero_are_not_failure_criteria(self):
        np.testing.assert_allclose(field.von_mises([[10, 0, 0, 0, 0, 0],
                                                  [9, 9, 9, 0, 0, 0],
                                                  [0, 0, 0, 0, 2, 0]]), [10, 0, np.sqrt(12)])

    def test_bin_maxima_not_averages_signed_frame_count_and_zero(self):
        xyz = [[-1.1, 2.1, -3.1], [-.9, 1.9, -2.9], [4, -5, 6]]
        rows, error = field.aggregate(xyz, [[2, 8], [9, 1], [0, 0]])
        np.testing.assert_array_equal(rows, [[-1, 2, -3, 9, 8, 2], [4, -5, 6, 0, 0, 1]])
        self.assertLessEqual(error, np.sqrt(3)*.25)
        self.assertEqual(rows[:, 5].sum(), 3)

    def test_half_grid_tie_rule_and_deterministic_order(self):
        rows, _ = field.aggregate([[-.25, 0, 0], [.25, 0, 0]], [[1, 2], [3, 4]])
        np.testing.assert_array_equal(rows[:, 0], [0, .5])
        backwards, _ = field.aggregate([[.25, 0, 0], [-.25, 0, 0]], [[3, 4], [1, 2]])
        np.testing.assert_array_equal(rows, backwards)

    def test_rejects_invalid_arrays_and_unverified_solver_output(self):
        for xyz, values in (([], []), ([[float("nan"), 0, 0]], [[1, 2]]),
                            ([[0, 0, 0]], [[-1, 2]]), ([[0, 0, 0]], [[1]]),
                            ([[5001, 0, 0]], [[1, 2]]), ([[0, 0, 0]], [[1, float("inf")]])):
            with self.assertRaises(ValueError):
                field.aggregate(xyz, values)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "torsion_+1"
            path.mkdir()
            (path / "shell.dat").write_text("changed solver data")
            output = Path(tmp) / "output"
            with self.assertRaisesRegex(ValueError, "Unverified solver output"):
                field.prepare(tmp, output)
            self.assertFalse(output.exists())

    def test_retained_receipt_binds_sources_and_outputs_without_approval(self):
        evidence = SOURCE / "evidence"
        receipt = json.loads((evidence / "execution.json").read_text())
        for name, digest in receipt["files_sha256"].items():
            self.assertEqual(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest(), digest, name)
        report = json.loads((evidence / "report.json").read_text())
        mapping = json.loads((evidence / "mapping.json").read_text())
        self.assertEqual(report["samples_sha256"], mapping["samples_sha256"])
        self.assertEqual(report["active_bins_per_field"], mapping["active_sample_bins"])
        self.assertTrue(report["all_sample_values_bitwise_equal"])
        self.assertTrue(report["zero_signed_coordinate_witness_passed"])
        self.assertTrue(report["geometry_vdb_equal"])
        self.assertFalse(report["product_strength_validated"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["structural_optimization"])
        self.assertLessEqual(mapping["position_error_max_mm"], mapping["position_error_bound_mm"])
        self.assertEqual(report["input_integration_points_per_case"], 179216)
        topology = json.loads((evidence / "topology.json").read_text())
        self.assertTrue(topology["uniform_probe"]["closed_oriented_combinatorial_surface_screen_pass"])
        self.assertFalse(topology["graded_probe"]["closed_oriented_combinatorial_surface_screen_pass"])
        self.assertEqual(topology["graded_probe"]["exact_zero_area_faces"], 32)
        self.assertTrue(all(v["faces_removed"] == 0 for v in topology.values()))


if __name__ == "__main__":
    unittest.main()
