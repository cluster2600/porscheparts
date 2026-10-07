import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001"
SCRIPT = PART / "source/flat_fan_sizing_f2.py"
REPORT = PART / "evidence/flat-fan-sizing-f2.json"
SPEC = importlib.util.spec_from_file_location("flat_fan_sizing_f2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FlatFanSizingF2Tests(unittest.TestCase):
    def test_configure_reproduces_the_f1_geometry_at_248_mm(self) -> None:
        m = MODULE.load_rotor_module()
        reference = MODULE.load_rotor_module()
        MODULE.configure(m, 248.0, 10_000.0, reference.DESIGN_FLOW_GAIN, MODULE.DUTY_CASES[0])

        self.assertAlmostEqual(m.blade_tip_radius_mm(), reference.blade_tip_radius_mm())
        self.assertAlmostEqual(m.HUB_OUTER_DIAMETER_MM, reference.HUB_OUTER_DIAMETER_MM)
        self.assertAlmostEqual(m.HOUSING_SYNTHETIC_THROAT_MM, reference.HOUSING_SYNTHETIC_THROAT_MM)
        self.assertEqual(m.design_f1_rotor(), reference.design_f1_rotor())

    def test_overrides_stay_private_to_the_study(self) -> None:
        m = MODULE.load_rotor_module()
        MODULE.configure(m, 360.0, 6000.0, 1.2, MODULE.DUTY_CASES[4])
        fresh = MODULE.load_rotor_module()
        self.assertEqual(fresh.OUTER_DIAMETER_MM, 248.0)
        self.assertEqual(fresh.SYNTHETIC_PRESSURE_RISE_PA, 800.0)
        self.assertEqual(fresh.SYNTHETIC_AIRFLOW_M3_S, 1.01)

    def test_small_grid_meets_target_under_tip_speed_cap(self) -> None:
        report = MODULE.study(cases=MODULE.DUTY_CASES[:1], diameters=(240, 320),
                              speeds=(7000, 8500, 10000), gains=(1.15, 1.25))
        case = report["cases"][0]
        cap = report["sweep"]["tip_speed_cap_m_s"]
        for row in case["rows"]:
            best = row["best"]
            if best:
                self.assertGreaterEqual(best["flow_m3_s"], case["target_flow_m3_s"])
                self.assertLessEqual(best["tip_speed_m_s"], cap + 1e-9)
                self.assertGreaterEqual(best["min_de_haller"], MODULE.MINIMUM_DE_HALLER)

    def test_study_operating_point_matches_the_f1_bisection(self) -> None:
        m = MODULE.load_rotor_module()
        design = m.design_f1_rotor()
        mine = MODULE.operating_point(m, design, 10_000.0)
        theirs = m.operating_point(design, 10_000.0, **MODULE.CONFIG)
        self.assertAlmostEqual(mine["flow_m3_s"], theirs["flow_m3_s"], places=6)

    def test_committed_study_findings(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        optimum = report["results"]["optimum_diameter_mm_by_case"]

        self.assertFalse(report["results"]["bigger_is_better_at_synthetic_duty"])
        self.assertGreater(optimum["four times the air"], optimum["synthetic F0 duty"])
        self.assertGreaterEqual(optimum["twice the air"], optimum["synthetic F0 duty"])
        self.assertEqual(report["measured_context"]["fan_power_hp"], {"4000_fan_rpm": 1.5, "12000_fan_rpm": 32.0})
        self.assertFalse(report["manufacturing_authorized"])


if __name__ == "__main__":
    unittest.main()
