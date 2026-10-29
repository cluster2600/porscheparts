"""Native CAD fixtures remain synthetic; no private head geometry is required."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec("OCP"), "native CAD controls require optional OCCT")
class ScanFeatureCADTests(unittest.TestCase):
    def test_reversed_solid_does_not_supply_outward_orientation_evidence(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from scripts.scan_feature_cad import inspect_shape
        shape = BRepPrimAPI_MakeBox(30., 30., 10.).Shape().Reversed()
        report = inspect_shape(shape)
        self.assertLess(report["oriented_volume_mm3"], 0)
        self.assertFalse(report["solid_hole_classification_admitted"])

    def test_wrong_private_source_does_not_create_output(self):
        from scripts.study_935_paper_features import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.obj"
            source.write_text("different source")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                run(source, root / "arrays.npz", root / "baseline", root / "out")
            self.assertFalse((root / "out").exists())

    def test_straight_holes_boss_and_unsupported_step(self):
        from scripts.scan_feature_cad import synthetic_controls
        controls = synthetic_controls()
        self.assertEqual(len(controls), 6)
        self.assertTrue(all(c["passed"] for c in controls))
        self.assertTrue(all(c["independent_analytic_fixture_volume_check"] for c in controls))

    def test_partial_face_abstains_without_silently_closing_a_hole(self):
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
        from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
        from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE
        from scripts.scan_feature_cad import inspect_shape, shapes
        body = BRepAlgoAPI_Cut(BRepPrimAPI_MakeBox(30., 30., 10.).Shape(),
                              BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(15, 15, -1), gp_Dir(0, 0, 1)), 4., 12.).Shape()).Shape()
        face = next(f for f in shapes(body, TopAbs_FACE) if len(shapes(f, TopAbs_WIRE)) == 2)
        report = inspect_shape(face)
        self.assertFalse(report["solid_hole_classification_admitted"])
        self.assertIsNone(report["oriented_volume_mm3"])
        self.assertEqual(len(report["rims"]), 1)
        self.assertEqual(report["rims"][0]["state"], "abstain_partial_or_nonmanifold_CAD")
        self.assertEqual(report["rims"][0]["through_or_blind"], "unresolved")


if __name__ == "__main__":
    unittest.main()
