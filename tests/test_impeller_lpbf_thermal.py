"""Physical energy checks and fail-closed admission for the WE43 thermal study."""
from _deps import require_modules
require_modules("numpy", "scipy", "trimesh", "matplotlib")

import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001/source/simulate_lpbf_thermal.py"))
np, sparse = MODULE["np"], MODULE["sparse"]


class ImpellerThermalTests(unittest.TestCase):
    def test_voxelization_covers_translated_whole_solid(self):
        box = MODULE["trimesh"].creation.box(extents=[4, 6, 8])
        before = box.vertices.copy()
        body = MODULE["voxel_body"](box, 1.)
        self.assertEqual(int(body.sum()), 192)
        np.testing.assert_array_equal(box.vertices, before)
        box.apply_translation([73., -126., 21.])
        np.testing.assert_array_equal(MODULE["voxel_body"](box, 1.), body)

    def test_heat_injection_and_cooling_match_analytic_energy(self):
        step = MODULE["SOLVER"]["implicit_step"]
        t, error, stored, rejected, absorbed = step(np.array([300.]), np.array([2.]),
            sparse.csr_matrix((1, 1)), np.zeros(1), np.zeros(1), np.array([200.]), .005)
        self.assertAlmostEqual(t[0], 300.5)
        self.assertAlmostEqual(stored, 1.)
        self.assertAlmostEqual(absorbed, 1.)
        self.assertEqual(rejected, 0.)
        self.assertLess(error, 1e-10)
        cooled, error, stored, rejected, absorbed = step(t, np.array([2.]),
            sparse.csr_matrix((1, 1)), np.array([4.]), np.array([1200.]), np.zeros(1), .5)
        self.assertAlmostEqual(cooled[0], 300.25)
        self.assertAlmostEqual(stored + rejected - absorbed, 0.)
        self.assertLess(error, 1e-10)

    def test_unphysical_inputs_and_release_claims_are_rejected(self):
        card = json.loads(MODULE["CARD"].read_text())
        MODULE["validate"](card, 2., .35, 4)
        for path, value in [(('material', 'rho_kg_m3'), 0.),
                            (('material', 'conductivity_w_m_k'), float('nan')),
                            (('assumptions', 'support_solid_fraction'), 1.1),
                            (('process', 'supplier_calibrated'), True)]:
            altered = copy.deepcopy(card)
            altered[path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE["validate"](altered, 2., .35, 4)
        for absorption in (0., 1.1, float('nan')):
            with self.assertRaises(ValueError):
                MODULE["validate"](card, 2., absorption, 4)

    def test_invalid_resolution_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-created"
            with self.assertRaises(ValueError):
                MODULE["run"](output, 3., .35, 4)
            self.assertFalse(output.exists())

    def test_conduction_preserves_energy_and_matches_two_cell_solution(self):
        step = MODULE["SOLVER"]["implicit_step"]
        t, error, stored, rejected, absorbed = step(np.array([310., 300.]), np.ones(2),
            sparse.csr_matrix([[2., -2.], [-2., 2.]]), np.zeros(2), np.zeros(2), np.zeros(2), .25)
        np.testing.assert_allclose(t, [307.5, 302.5], atol=1e-10)
        self.assertAlmostEqual(stored, 0.)
        self.assertEqual(rejected, 0.)
        self.assertEqual(absorbed, 0.)
        self.assertLess(error, 1e-10)

    def test_grid_volume_loss_is_rejected(self):
        box = MODULE["trimesh"].creation.box(extents=[4, 4, 4])
        with patch.dict(MODULE["SOLVER"], interior_voxels=lambda mesh, pitch: np.ones((2, 2, 2))):
            with self.assertRaisesRegex(ValueError, "volume"):
                MODULE["voxel_body"](box, 1.)

    def test_renderer_rejects_tampered_results_before_creating_output(self):
        renderer = runpy.run_path(str(MODULE["CARD"].with_name("render_lpbf_thermal.py")))
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory)
            (case / "summary.json").write_text(json.dumps({
                "hashes": {"surface": "same", "card": "same"},
                "status": "transient_3d_bulk_thermal_solve_completed", "manufacturing_authorized": False,
                "output_hashes": {"thermal-fields.npz": "wrong", "history.json": "wrong"}}))
            (case / "thermal-fields.npz").write_bytes(b"tampered")
            output = case / "not-created"
            with self.assertRaisesRegex(ValueError, "digest"):
                renderer["render"]([case], output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
