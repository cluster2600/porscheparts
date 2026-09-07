import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/propose_thermal_face_groups.py"
SPEC = importlib.util.spec_from_file_location("m64_proposals", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ThermalFaceProposalTests(unittest.TestCase):
    feature = {"start": [0., 0., 0.], "end": [0., 0., 2.], "radius": 1.}

    def test_finite_side(self):
        self.assertEqual(MODULE.finite_cylinder_support_matches([[1., 0., .5], [0., 1., 1.5]], self.feature), ["cylindrical_side"])

    def test_infinite_extension_is_not_side(self):
        self.assertEqual(MODULE.finite_cylinder_support_matches([[1., 0., 3.]], self.feature), [])

    def test_cap_interior(self):
        self.assertEqual(MODULE.finite_cylinder_support_matches([[.5, 0., 2.], [0., 0., 2.]], self.feature), ["end_cap"])

    def test_plane_outside_disk_is_not_cap(self):
        self.assertEqual(MODULE.finite_cylinder_support_matches([[2., 0., 2.]], self.feature), [])

    def test_all_samples_must_match(self):
        self.assertEqual(MODULE.finite_cylinder_support_matches([[1., 0., .5], [.8, 0., 1.5]], self.feature), [])

    def test_shared_cylinder_rim_remains_ambiguous(self):
        self.assertEqual(MODULE.finite_cylinder_support_matches([[1., 0., 0.]], self.feature), ["cylindrical_side", "start_cap"])

    def test_invalid_input_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_finite"):
            MODULE.finite_cylinder_support_matches([[float("nan"), 0., 0.]], self.feature)

    def test_signature_requires_area_and_center_not_just_bbox(self):
        source = {"face_id": 4, "surface_type": "Plane", "bbox_scan_units": [0, 0, 0, 1, 1, 0],
                  "centroid_scan_units": [.5, .5, 0], "area_scan_units_squared": 1.}
        self.assertEqual(MODULE.signature_candidates(source, [source]), [4])
        changed = dict(source, area_scan_units_squared=.8)
        self.assertEqual(MODULE.signature_candidates(changed, [source]), [])


if __name__ == "__main__":
    unittest.main()
