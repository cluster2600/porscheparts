"""The study bundle must retain coordinates, portability and unreleased status."""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/964-chassis/monocoque/omniverse/build_twin.py"
AVAILABLE = all(importlib.util.find_spec(name) for name in ("numpy", "pxr", "pyvista")) and shutil.which("usdchecker")


@unittest.skipUnless(AVAILABLE, "Native OpenUSD, VTK and usdchecker required")
class MonocoqueBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("monocoque_twin", SOURCE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.temp = tempfile.TemporaryDirectory()
        cls.bundle = Path(cls.temp.name) / "original"
        cls.report = cls.module.build(cls.bundle)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_source_triangles_preserved(self):
        self.assertEqual(sum(x["triangles"] for x in self.report["groups"].values()), 422816)
        self.assertEqual(set(self.report["groups"]), set(self.module.GROUPS))
        self.assertFalse(self.report["physical_validation"])
        self.assertFalse(self.report["rtx_execution_verified"])

    def test_coordinates_preserved_per_group(self):
        import numpy as np
        import pyvista as pv
        from pxr import Usd, UsdGeom
        original = pv.read(self.module.MONOCOQUE / "derived/zesad-monocoque.vtp")
        faces = original.faces.reshape(-1, 4)[:, 1:]
        stage = Usd.Stage.Open(str(self.bundle / "monocoque.usda"))
        for index, name in enumerate(self.module.GROUPS):
            selected = faces[original.cell_data["group"] == index]
            mesh = UsdGeom.Mesh.Get(stage, f"/Monocoque/Geometry/{name}")
            p = np.asarray(mesh.GetPointsAttr().Get())
            f = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
            np.testing.assert_array_equal(p[f], original.points[selected])

    def test_relocation_without_source_files(self):
        target = Path(self.temp.name) / "relocated"
        shutil.copytree(self.bundle, target)
        self.assertEqual(self.module.validate(target)["groups"], self.report["groups"])

    def test_refuses_output_overwrite(self):
        with self.assertRaises(FileExistsError):
            self.module.build(self.bundle)

    def test_rejects_corrupt_arrays(self):
        import numpy as np
        for points, faces in (([[float("nan"), 0, 0]], [[0, 0, 0]]),
                              ([[0, 0, 0]], [[0, -1, 0]]),
                              ([[0, 0, 0]], [[0, 1, 0]])):
            with self.assertRaises(ValueError):
                self.module.checked_arrays(np.asarray(points), np.asarray(faces))

    def test_rejects_unit_and_authorization_changes(self):
        from pxr import Usd, UsdGeom
        for name in ("units", "authorization"):
            target = Path(self.temp.name) / name
            shutil.copytree(self.bundle, target)
            stage = Usd.Stage.Open(str(target / "monocoque.usda"))
            if name == "units":
                UsdGeom.SetStageMetersPerUnit(stage, 1.)
            else:
                stage.GetDefaultPrim().SetCustomDataByKey("manufacturingAuthorized", True)
            stage.GetRootLayer().Save()
            with self.assertRaises(ValueError):
                self.module.validate(target)


if __name__ == "__main__":
    unittest.main()
