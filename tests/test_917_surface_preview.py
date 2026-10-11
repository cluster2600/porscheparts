import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "models/917-engine-reconstruction/assembly"
SPEC = importlib.util.spec_from_file_location("engine_surface_preview", HERE / "render_surfaces.py")
RENDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDER)
try:
    import numpy as np
    import trimesh
    import vtk
    from PIL import Image
    RUNTIME = True
except ImportError:
    RUNTIME = False


class SurfacePreviewTests(unittest.TestCase):
    @unittest.skipUnless(RUNTIME, "VTK, NumPy, Trimesh and Pillow required")
    def test_real_surfaces_keep_triangles_and_instance_transforms(self):
        scene = trimesh.Scene()
        rows = []
        for i, name in enumerate(("crankcase_positive", "crankshaft", "individual_head")):
            matrix = np.eye(4)
            matrix[0, 3] = i * .2
            node = f"part_{i:04d}"
            scene.add_geometry(trimesh.creation.box(extents=(.1, .1, .1)),
                               geom_name=name, node_name=node, transform=matrix)
            mm = matrix.copy(); mm[:3, 3] *= 1000
            rows.append({"instance_id": node, "family": name, "matrix_mm": mm.tolist()})
        with tempfile.TemporaryDirectory() as temporary:
            glb = Path(temporary) / "fixture.glb"
            image = Path(temporary) / "surface.png"
            scene.export(glb)
            before = RENDER.sha256(glb)
            report = RENDER.render_scene(glb, rows, image)
            self.assertEqual(RENDER.sha256(glb), before)
            self.assertEqual(report["prototype_triangles"], 36)
            self.assertEqual((report["prototypes"], report["instances"]), (3, 3))
            self.assertLess(report["max_actor_transform_error_m"], 1e-6)
            self.assertEqual(report["opacity"], 1)
            self.assertFalse(report["point_sampling"])
            self.assertFalse(report["decimation"])
            pixels = np.asarray(Image.open(image))
            self.assertEqual(pixels.shape, (2000, 3200, 3))
            self.assertGreater(np.std(pixels[:1000, :1600]), 15)
            rows[0]["matrix_mm"][0][3] += 10
            with self.assertRaisesRegex(ValueError, "placement"):
                RENDER.render_scene(glb, rows, Path(temporary) / "wrong.png")

    def test_published_render_receipt_binds_sources_without_physical_release(self):
        report = json.loads((HERE / "surface-preview-20261011.json").read_text())
        for name, expected in report["source_sha256"].items():
            self.assertEqual(RENDER.sha256(ROOT / name), expected)
        geometry = json.loads((HERE / "execution-20261011.json").read_text())
        self.assertEqual(report["glb_sha256_before_and_after"], geometry["glb_roundtrip"]["sha256"])
        self.assertEqual((report["prototypes"], report["instances"]), (119, 1129))
        self.assertFalse(report["point_sampling"])
        self.assertFalse(report["decimation"])
        for key in ("manufacturing_authorized", "physical_fit_verified", "material_qualification"):
            self.assertFalse(report[key])


if __name__ == "__main__":
    unittest.main()
