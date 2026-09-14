import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-exh-oval-tip-in625-f0-0001/source/oval_exhaust_tip.py"
RECORD = ROOT / "catalog/parts/993-exh-oval-tip-in625-f0-0001.json"
REPORT = ROOT / "parts/993-exh-oval-tip-in625-f0-0001/evidence/engineering-screen.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-exhaust-tips-dimensions.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-in625-exhaust-register.json"
SPEC = importlib.util.spec_from_file_location("oval_exhaust_tip", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class OvalExhaustTipIn625F0Tests(unittest.TestCase):
    def test_published_outlet_and_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        authority = report["geometry_authority"]
        self.assertEqual(authority["published"], ["commercial outlet envelope 120 x 85 mm"])
        self.assertEqual(authority["catalogue_identity"], ["FVD11199300"])
        self.assertGreaterEqual(len(authority["hypotheses"]), 6)
        self.assertIn("No Porsche or FVD interface", authority["not_claimed"])
        self.assertFalse(report["release_authorized"])

    def test_flow_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        cold_q = 3.8 / 1000.0 * 6500.0 / (2.0 * 60.0) * 0.95 / 2.0
        hot_q = cold_q * 850.0 / 300.0
        inlet_area = math.pi * (28.7 / 1000.0) ** 2
        outlet_area = math.pi * (54.7 / 1000.0) * (37.2 / 1000.0)
        inlet_velocity = hot_q / inlet_area
        density = 1.18 * 300.0 / 850.0
        loss_coefficient = (1.0 - inlet_area / outlet_area) ** 2
        pressure_loss = loss_coefficient * 0.5 * density * inlet_velocity**2

        self.assertAlmostEqual(results["cold_volume_flow_each_m3_s"], cold_q)
        self.assertAlmostEqual(results["hot_volume_flow_each_m3_s"], hot_q)
        self.assertAlmostEqual(results["inlet_velocity_m_s"], inlet_velocity)
        self.assertAlmostEqual(results["borda_carnot_loss_coefficient"], loss_coefficient)
        self.assertAlmostEqual(results["borda_carnot_pressure_loss_pa"], pressure_loss)
        self.assertAlmostEqual(results["screening_flow_power_w"], pressure_loss * hot_q)
        self.assertGreater(results["inlet_reynolds"], 4000.0)

    def test_thermal_pressure_and_modal_screens_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        self.assertAlmostEqual(
            results["thin_wall_hoop_stress_mpa"],
            30_000.0 * 0.033 / 0.0008 / 1_000_000.0,
        )
        self.assertAlmostEqual(
            results["free_thermal_expansion_mm"],
            13.7e-6 * 120.0 * (700.0 - 293.0),
        )
        self.assertGreater(
            results["fully_constrained_elastic_thermal_stress_mpa"], 640.0
        )
        self.assertGreater(results["cantilever_strip_first_mode_hz"], 0.0)
        self.assertGreater(results["outward_radiative_power_w"], 0.0)

    def test_committed_artifacts_keep_route_and_release_open(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        fvd = json.loads(FVD_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertIn("sheet_metal", record["manufacturing"]["candidate_processes"])
        self.assertIn("LPBF", record["manufacturing"]["candidate_processes"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["envelope_mm"], [120.0, 85.0, 120.0])
        self.assertAlmostEqual(
            report["results"]["cad_volume_mm3"],
            report["step_roundtrip"]["volume_mm3"],
        )
        self.assertAlmostEqual(report["results"]["screening_mass_g"], 406.38045021929724)
        self.assertEqual(fvd["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertGreaterEqual(len(report["release_blockers"]), 9)
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
