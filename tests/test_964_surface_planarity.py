import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("surface_planarity", ROOT /
    "twins/964-chassis/dimensional-correction-20261106/audit_surface_planarity.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class WholeSurfacePlanarityTests(unittest.TestCase):
    def grid(self, tilted=False):
        return [[100*i/3, 80*j/3, -65 + (2*i/3 if tilted else 0)]
                for i in range(4) for j in range(4)]

    def test_flat_and_tilted_planes_are_planar_but_level_is_distinct(self):
        flat = AUDIT.plane_certificate(self.grid())
        tilted = AUDIT.plane_certificate(self.grid(True))
        self.assertTrue(flat["passed"])
        self.assertTrue(flat["horizontal_level"])
        self.assertTrue(tilted["passed"])
        self.assertFalse(tilted["horizontal_level"])

    def test_bowed_middle_fails_despite_all_level_boundary_poles(self):
        poles = self.grid()
        for i, j in [(1, 1), (1, 2), (2, 1), (2, 2)]:
            poles[4*i+j][2] -= 4
        boundary = [poles[4*i+j] for i in range(4) for j in range(4) if i in (0, 3) or j in (0, 3)]
        self.assertTrue(AUDIT.plane_certificate(boundary)["passed"])
        self.assertFalse(AUDIT.plane_certificate(poles)["passed"])

    def test_degenerate_line_is_not_an_admitted_plane(self):
        self.assertFalse(AUDIT.plane_certificate([[i, 2*i, 3*i] for i in range(16)])["passed"])

    def test_independent_tensor_algebra_preserves_an_affine_tilted_plane(self):
        rows = [[[x, y, 7 + .02*x - .03*y] for y in (-200, 0, 60, 200)]
                for x in (0, 100, 300, 600)]
        poles, count = AUDIT.tensor_poles({"sections_mm": rows, "closed_profile": False})
        self.assertEqual(count, 9)
        self.assertTrue(all(abs(p[2] - (7 + .02*p[0] - .03*p[1])) < 1e-10 for p in poles))
        result = AUDIT.plane_certificate(poles)
        self.assertTrue(result["passed"])
        self.assertFalse(result["horizontal_level"])

    def test_actual_f2_level_landmarks_do_not_make_the_surface_planar(self):
        model = json.loads((ROOT / "twins/964-chassis/sculpted-cell-f2-20261106/canonical-model.json").read_text())
        sill = next(c for c in model["components"] if c["name"] == "sill_left")
        self.assertTrue(all(row[15][2] == row[16][2] == -65 for row in sill["sections_mm"]))
        poles, count = AUDIT.tensor_poles(sill, [15, 16])
        self.assertEqual(count, len(sill["sections_mm"])-1)
        self.assertFalse(AUDIT.plane_certificate(poles)["passed"])
        results = AUDIT.audit(model)
        self.assertEqual(len(results["regions"]), 5)
        self.assertTrue(all(not r["passed"] for r in results["regions"]))


if __name__ == "__main__":
    unittest.main()
