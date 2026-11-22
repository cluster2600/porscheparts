"""The carrier's gyroid cell at constant solid fraction, finished on a GPU: the solver on a closed form, then the
committed results against CalculiX's tensors and the contract written before the GPU runs."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "parts/993-eng-carrier-0001/source/design-20261016/constant-fraction-gpu-20261122"
CCX = STUDY.parent / "constant-fraction-20261026" / "results" / "single-thread"
RESULTS = STUDY / "results" / "a100-20261122"


def has(*names: str) -> bool:
    return all(importlib.util.find_spec(n) is not None for n in names)


@unittest.skipUnless(has("numpy", "scipy"), "numpy or scipy absent")
class CarrierCellGpuTests(unittest.TestCase):
    def setUp(self):
        import numpy as np

        sys.path.insert(0, str(STUDY))
        import rve_c3d8

        self.np, self.rve = np, rve_c3d8
        self.contract = json.loads((STUDY / "contract.json").read_text())

    def tensor(self, path: Path):
        return self.np.array(json.loads(path.read_text())["effective_C_MPa"])

    def test_a_cell_without_void_returns_the_isotropic_tensor(self):
        np, r = self.np, self.rve
        cell = r.Cell(8, 1.0, 0.4000097)                      # void as stiff as the solid
        K, F = cell.assemble(), cell.rhs()
        W, info = r.solve(K, F, "scipy")
        C = np.array(cell.recover(W, K, F)["effective_C_MPa"])
        D = r.elasticity(r.E_MPA, r.NU)
        self.assertLess(np.abs(C - D).max() / np.abs(D).max(), 1e-10)
        # the same element and material as the CalculiX decks
        self.assertEqual((r.E_MPA, r.NU, r.AMPLITUDE), (107000.0, 0.31, 0.001))

    def test_the_gpu_backend_was_qualified_against_calculix_before_any_new_resolution(self):
        np = self.np
        limit = self.contract["qualification_before_use"]["limit"]
        q = json.loads((RESULTS / "qualification.json").read_text())
        self.assertTrue(q["admitted"])
        self.assertEqual(q["limit"], limit)
        self.assertEqual({(c["resolution"], c["void_floor"]) for c in q["cases"]},
                         {(n, f) for n in (16, 24, 32) for f in ("1e-4", "1e-6")})
        for c in q["cases"]:
            mine = self.tensor(RESULTS / f"n{c['resolution']}-floor{c['void_floor']}" / "assessment.json")
            theirs = self.tensor(CCX / f"n{c['resolution']}-floor{c['void_floor']}" / "assessment.json")
            diff = float(np.linalg.norm(mine - theirs) / np.linalg.norm(theirs))
            self.assertAlmostEqual(diff, c["relative_difference_to_calculix"], places=15)
            self.assertLessEqual(diff, limit)

    def test_every_case_passes_the_checks_of_the_earlier_study(self):
        for path in sorted(RESULTS.glob("n*-floor*/assessment.json")):
            a = json.loads(path.read_text())
            self.assertTrue(a["status"].endswith("six_strain_energy_checks_passed"), path)
            self.assertEqual(a["solid_periodic_components"], 1, path)
            self.assertLessEqual(max(c["relative_energy_residual"] for c in a["cases"]), 1e-4, path)
            self.assertLessEqual(a["relative_antisymmetry"], 1e-4, path)
            eig = a["normalized_stiffness_eigenvalues"]
            self.assertGreater(min(eig), 0.0, path)
            self.assertLessEqual(max(eig), a["voigt_upper_ratio"] + 1e-4, path)
            self.assertLess(abs(a["solid_fraction"] - 0.4000097) / 0.4000097, 0.005, path)
            self.assertFalse(a["carrier_convergence_demonstrated"])

    def test_the_verdicts_follow_from_the_tensors_and_the_contract(self):
        np = self.np
        resolutions = (self.contract["resolutions"]["completion_of_the_declared_study"]
                       + self.contract["resolutions"]["extension_declared_now"])
        self.assertEqual(resolutions, [16, 24, 32, 48, 64, 80])
        terminal = json.loads((RESULTS / "terminal.json").read_text())
        rows = {r["resolution"]: r for r in terminal["comparisons"]}
        self.assertEqual(sorted(rows), resolutions)
        hard = {n: self.tensor(RESULTS / f"n{n}-floor1e-6" / "assessment.json") for n in resolutions}
        for previous, n in zip(resolutions, resolutions[1:]):
            change = float(np.linalg.norm(hard[previous] - hard[n]) / np.linalg.norm(hard[n]))
            self.assertAlmostEqual(rows[n]["relative_tensor_resolution_change"], change, places=12)
            self.assertEqual(rows[n]["resolution_change_passed"], change <= 0.02)
        for n in resolutions:
            soft = self.tensor(RESULTS / f"n{n}-floor1e-4" / "assessment.json")
            floor = float(np.linalg.norm(soft - hard[n]) / np.linalg.norm(hard[n]))
            self.assertEqual(rows[n]["void_floor_test_passed"], floor <= 0.01)
        passes = lambda *ns: all(rows[k]["resolution_change_passed"] and rows[k]["void_floor_test_passed"] for k in ns)
        self.assertEqual(terminal["declared_study_converged"], passes(32, 48))
        self.assertEqual(terminal["extended_series_converged"], passes(64, 80))
        self.assertFalse(terminal["carrier_convergence_demonstrated"])
        # the steps from 32 to 48 and from 24 to 32 match the earlier CalculiX comparison where both exist
        earlier = {r["resolution"]: r for r in json.loads((CCX / "comparison-progress.json").read_text())}
        for n in (24, 32):
            self.assertAlmostEqual(rows[n]["relative_tensor_resolution_change"], earlier[n]["relative_tensor_resolution_change"], places=6)

    def test_a_cached_case_is_reused_only_for_the_same_case_and_backend_family(self):
        import contextlib
        import io
        import shutil
        import tempfile

        import study

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copytree(RESULTS / "n16-floor1e-6", tmp / "n16-floor1e-6")
            with contextlib.redirect_stdout(io.StringIO()):
                report = study.case(tmp, 16, 1e-6, "1e-6", 0.4000097, "cudss")
            self.assertTrue(report["solver"]["backend"].startswith("NVIDIA cuDSS"))
            for args in [(16, 1e-6, "1e-6", 0.4000097, "scipy"),      # another backend
                         (16, 1e-4, "1e-6", 0.4000097, "cudss"),      # another void floor in that folder
                         (16, 1e-6, "1e-6", 0.41, "cudss")]:          # another target
                with self.assertRaises(SystemExit):
                    study.case(tmp, *args)

    def test_the_n80_refusal_is_kept_and_the_retry_changed_only_memory_placement(self):
        refusal = json.loads((RESULTS / "refusal-n80-cudss-alloc-failed.json").read_text())
        self.assertIn("ALLOC_FAILED", refusal["detail"])
        addendum = json.loads((STUDY / "n80-execution-addendum.json").read_text())
        self.assertIn("before any N=80 tensor existed", addendum["written"])
        for floor in ("1e-4", "1e-6"):
            a = json.loads((RESULTS / f"n80-floor{floor}" / "assessment.json").read_text())
            self.assertTrue(a["solver"]["hybrid_memory_mode"])
        for n in (16, 24, 32, 48, 64):
            a = json.loads((RESULTS / f"n{n}-floor1e-6" / "assessment.json").read_text())
            self.assertFalse(a["solver"].get("hybrid_memory_mode", False))
        readme = " ".join((STUDY / "README.md").read_text().split())
        self.assertIn("ALLOC_FAILED", readme)
        self.assertIn("No carrier convergence", readme)


if __name__ == "__main__":
    unittest.main()
