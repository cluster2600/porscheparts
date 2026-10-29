"""Native RTX exposed clipping that the local preview did not reproduce."""
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "twins/964-chassis/monocoque/omniverse"
AVAILABLE = all(importlib.util.find_spec(n) for n in ("pxr", "numpy", "pyvista")) and shutil.which("usdchecker")


@unittest.skipUnless(AVAILABLE, "Native OpenUSD, VTK and usdchecker required")
class ReviewFramingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HERE))
        try:
            import prepare_framed_review
            cls.module = prepare_framed_review
        finally:
            sys.path.pop(0)
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / "framed"
        cls.source_hashes = {p.name: cls.module.digest(p) for p in (HERE / "bundle-001").iterdir()}
        cls.report = cls.module.prepare(HERE / "bundle-001", cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_original_and_geometry_are_unchanged(self):
        for name, expected in self.source_hashes.items():
            self.assertEqual(self.module.digest(HERE / "bundle-001" / name), expected)
        for name in self.source_hashes.keys() - {"validation.json", "monocoque.usda", "interior.usda"}:
            self.assertEqual(self.module.digest(self.output / name), self.source_hashes[name])
        self.assertFalse(self.report["rtx_execution_verified"])
        self.assertFalse(self.report["native_framing_verified"])
        self.assertFalse(self.report["manufacturing_authorized"])

    def test_every_vertex_fits_all_123_camera_samples_with_margin(self):
        import numpy as np
        from pxr import Usd, UsdGeom
        stage = Usd.Stage.Open(str(self.output / "monocoque.usda"))
        points = np.concatenate([np.asarray(UsdGeom.Mesh(p).GetPointsAttr().Get(), dtype=float)
                                 for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)])
        world = np.column_stack((points, np.ones(len(points))))
        for name in ("Front", "Rear", "Interior", "Orbit"):
            camera = UsdGeom.Camera(stage.GetPrimAtPath("/Monocoque/Presentation/" + name))
            for frame in range(120) if name == "Orbit" else (0,):
                with self.subTest(camera=name, frame=frame):
                    eye = world @ np.asarray(camera.ComputeLocalToWorldTransform(frame).GetInverse())
                    depth = -eye[:, 2]
                    near, far = camera.GetClippingRangeAttr().Get()
                    self.assertGreater(float(depth.min()), near)
                    self.assertLess(float(depth.max()), far)
                    focal = camera.GetFocalLengthAttr().Get()
                    half_aperture = np.array([camera.GetHorizontalApertureAttr().Get(),
                                              camera.GetVerticalApertureAttr().Get()]) / 2
                    ndc = np.abs(eye[:, :2] / depth[:, None] * focal / half_aperture)
                    self.assertLessEqual(float(ndc.max()), .9)

    def test_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            self.module.prepare(HERE / "bundle-001", self.output)


if __name__ == "__main__":
    unittest.main()
