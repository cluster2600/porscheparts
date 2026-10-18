"""The envelope must be actual geometry, while fit and engineering remain unqualified."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"


class EnclosedHeadTests(unittest.TestCase):
    def test_actual_envelope_and_images_retain_provenance_without_release(self):
        r = json.loads((FAMILY / "derived/enclosed-report.json").read_text())
        for key in ("manufacturing_authorized", "is_fitment_validated", "wall_thickness_qualified",
                    "hydraulic_performance_validated", "thermal_improvement_validated", "strength_validated",
                    "interface_conformity_validated"):
            self.assertIs(r[key], False)
        for path, digest in r["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        parent = json.loads((FAMILY / "derived/refinement-report.json").read_text())
        self.assertGreater(r["mesh"]["volume_mm3"], 2 * parent["mesh_metrics"]["solid"]["volume_mm3"])
        self.assertTrue(r["mesh"]["watertight"] and r["mesh"]["consistent_winding"])
        self.assertEqual(r["mesh"]["connected_components"], 1)
        self.assertTrue(all(d < 0 for d in r["material_probe_signed_distances_mm"]))
        self.assertEqual(len(r["dry_opening_probes_mm"]), 6)
        for n, item in r["images"].items():
            data = (FAMILY / "derived/enclosed-views" / (n + ".png")).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            self.assertEqual(struct.unpack(">II", data[16:24]), (1600, 1200))

    def test_enclosure_does_not_change_the_passage_parameters(self):
        original = json.loads((FAMILY / "source/solid.json").read_text())
        enclosed = json.loads((FAMILY / "source/enclosed-solid.json").read_text())
        self.assertEqual(original["parameters"], enclosed["parameters"])
        self.assertEqual(enclosed["density_g_cm3"], 0)
        self.assertEqual(enclosed["safety_class"], "prohibited_pending_engineering")

    @unittest.skipUnless(importlib.util.find_spec("vtk"), "optional VTK unavailable")
    def test_virtual_closed_cut_matches_analytic_cube_volume(self):
        import vtk
        p = FAMILY / "source/enclosed/render_enclosed.py"
        s = importlib.util.spec_from_file_location("enclosed_views", p)
        module = importlib.util.module_from_spec(s); s.loader.exec_module(module)
        cube = vtk.vtkCubeSource(); cube.Update()
        clean = vtk.vtkCleanPolyData(); clean.SetInputConnection(cube.GetOutputPort()); clean.Update()
        result = module.cut_left(clean.GetOutput())
        triangulate = vtk.vtkTriangleFilter(); triangulate.SetInputData(result); triangulate.Update()
        properties = vtk.vtkMassProperties(); properties.SetInputConnection(triangulate.GetOutputPort()); properties.Update()
        self.assertAlmostEqual(properties.GetVolume(), .75)


if __name__ == "__main__":
    unittest.main()
