import importlib.util
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "twins/964-chassis/model-year-review-20261029/run.py"


@unittest.skipIf(importlib.util.find_spec("numpy") is None, "numpy required")
class ModelYearReviewTests(unittest.TestCase):
    def setUp(self):
        self.path_before = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), self.path_before))
        self.module = runpy.run_path(str(RUN))

    def test_frame_axes_offsets_and_rotations_without_changing_source(self):
        import numpy as np
        convert = self.module["registered_vertices"]
        source = np.array([[11., 102., 3.]])
        np.testing.assert_array_equal(convert(source, [0, 10, 0, 100, -2]), [[2, -1, 5]])
        np.testing.assert_array_equal(source, [[11, 102, 3]])
        np.testing.assert_allclose(convert([[1, 0, 0]], [np.pi/2, 0, 0, 0, 0]),
                                   [[-1, 0, 0]], atol=1e-7)
        np.testing.assert_allclose(convert([[1, 0, 0]], [0, 0, np.pi/2, 0, 0]),
                                   [[0, 0, 1]], atol=1e-7)
        for vertices, params in [([], [0]*5), ([[0, 1]], [0]*5),
                                 ([[0, float("nan"), 0]], [0]*5),
                                 ([[0, 0, 0]], [0]*4),
                                 ([[0, 0, 0]], [0, 0, 0, 0, float("inf")])]:
            with self.assertRaises(ValueError):
                convert(vertices, params)

    def test_crop_preserves_indices_and_drops_crossing_triangles(self):
        import numpy as np
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [2, 0, 0]])
        faces = np.array([[0, 1, 2], [1, 2, 3]])
        selected, count = self.module["crop_faces"](vertices, faces, [0, 1, 0, 1, 0, 1])
        np.testing.assert_array_equal(selected, [[0, 1, 2]])
        self.assertEqual(count, 3)

    def test_unknown_scan_and_existing_output_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "unknown.obj"
            scan.write_text("v 0 0 0\n")
            output = root / "review"
            arguments = [str(RUN), "--scan", str(scan), "--output", str(output)]
            with patch.object(sys, "argv", arguments), self.assertRaisesRegex(ValueError, "digest"):
                self.module["main"]()
            self.assertFalse(output.exists())
            output.mkdir()
            marker = output / "keep"
            marker.write_bytes(b"preserve")
            with patch.object(sys, "argv", arguments), self.assertRaises(FileExistsError):
                self.module["main"]()
            self.assertEqual(marker.read_bytes(), b"preserve")

    def test_retained_receipts_match_inputs_and_withhold_year_identification(self):
        import hashlib
        import json
        folder = RUN.parent
        report = json.loads((folder / "run.json").read_text())
        for path, digest in report["input_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)
        self.assertEqual(hashlib.sha256((folder / "interface-review.json").read_bytes()).hexdigest(),
                         report["interface_review_sha256"])
        registration = json.loads((ROOT / "twins/964-chassis/derived/scan-recalage-20260925.json").read_text())
        self.assertEqual(report["source_sha256"], registration["source_sha256"])
        for name, digest in report["array_sha256"].items():
            self.assertEqual(digest, registration["outputs"][name])
        self.assertEqual(len(report["crops"]), 4)
        self.assertTrue(all(0 < c["source_triangles"] <= report["original_triangles"]
                            for c in report["crops"].values()))
        for key in ("model_year", "model_year_group", "p14_measured_span_mm"):
            self.assertIsNone(report[key])
        self.assertFalse(any(report["release_flags"].values()))
        manual = json.loads((folder / "manual-review.json").read_text())
        self.assertFalse(manual["p13_discriminates_model_year_group"])
        self.assertIsNone(manual["donor_model_year"])
        ledger = json.loads((ROOT / "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json").read_text())
        values = {v["value_id"]: v for v in ledger["declared_values"]}
        for observation in manual["observations"]:
            value = values[observation["value_id"]]
            self.assertEqual(value["numeric_values"],
                             [observation["nominal_mm"], observation["tolerance_mm"]])
