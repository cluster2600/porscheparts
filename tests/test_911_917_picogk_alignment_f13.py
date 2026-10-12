import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "twins/vehicle-911-917/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("alignment_f13", SOURCE / "prepare_picogk_alignment_f13.py")
alignment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alignment)
from annotate_picogk_mechanical_f13 import validate_report


class ScanAlignmentTests(unittest.TestCase):
    def test_staggered_banks_do_not_rotate_engine(self):
        angle = np.deg2rad(31)
        rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                             [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
        registry = []
        for name, sign in (("positive", 1), ("negative", -1)):
            for index, x in enumerate((0, 118, 236, 409, 527, 645), 1):
                p = np.array([x + sign * 35, sign * 250, 0]) @ rotation.T + [14, -25, 80]
                registry.append({"bank": name, "geometric_index": index,
                                 "center_scan_coordinates_obj_units": p.tolist()})
        frame = alignment.bank_frame(registry)
        np.testing.assert_allclose(frame[0], rotation[:, 0], atol=1e-12)
        np.testing.assert_allclose(frame @ frame.T, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(frame), 1.0)
        points = np.array([v["center_scan_coordinates_obj_units"] for v in registry[:6]]) @ frame.T
        np.testing.assert_allclose(points[:, 1], points[0, 1], atol=1e-10)

    def test_missing_bank_is_rejected(self):
        with self.assertRaises(ValueError):
            alignment.bank_frame([])

    def test_annotator_refuses_physical_release_claim(self):
        report = {"phase": "F13", "release_gates": {"physical_fit_verified": True}}
        with self.assertRaises(ValueError):
            validate_report(report)

    def test_local_geometry_and_interfaces_when_available(self):
        output = SOURCE.parents[2] / "work/911-917-picogk-f13"
        path = output / "picogk-mechanical-report-f13.json"
        if not path.exists():
            self.skipTest("résultats privés PicoGK absents")
        report = json.loads(path.read_text())
        validate_report(report)
        np.testing.assert_allclose(report["alignment"]["fitted_longitudinal_axis_in_vehicle"], [1, 0, 0], atol=1e-7)
        refs = report["kinematic_references"]
        self.assertEqual(refs["differential_x_mm"], refs["rear_axle_x_mm"])
        np.testing.assert_allclose(refs["rear_hub_centres_mm"], refs["halfshaft_outer_joint_centres_mm"])
        for key in ("engine_scan", "transaxle_schematic", "turbo_left", "turbo_right", "rear_halfshafts_and_CV_joints"):
            layer = report["layers"][key]
            self.assertGreater(layer["properties"]["volume_mm3"], 0)
            self.assertTrue((output / layer["vdb"]).is_file())
        # L'interférence héritée ne doit pas disparaître silencieusement du diagnostic.
        self.assertTrue(report["checks"]["halfshafts_vs_structure"]["collision"])


if __name__ == "__main__":
    unittest.main()
