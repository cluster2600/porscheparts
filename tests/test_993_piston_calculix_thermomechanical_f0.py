import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "twins/993-m64-60-piston-gallery-f0/source/run_calculix_thermomechanical_screen.py"
)
VERIFIER = (
    ROOT
    / "twins/993-m64-60-piston-gallery-f0/source/verify_calculix_thermomechanical_report.py"
)
REPORT = (
    ROOT
    / "twins/993-m64-60-piston-gallery-f0/evidence/calculix-f0/calculix-thermomechanical-screen.json"
)
RECORD = ROOT / "catalog/parts/993-eng-piston-cp1-gallery-f0-0001.json"
TWIN = ROOT / "catalog/twins/twin-993-m64-60-piston-gallery-f0.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RUNNER = load_module("piston_calculix_runner", SOURCE)
CHECK = load_module("piston_calculix_verifier", VERIFIER)


class PistonCalculixThermomechanicalF0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_synthetic_force_chain_is_reproducible(self) -> None:
        loads = RUNNER.synthetic_loads()
        gas = 12.0 * math.pi * 100.0**2 / 4.0
        omega = 2.0 * math.pi * 6720.0 / 60.0
        acceleration = 0.0764 / 2.0 * omega**2 * (1.0 + (0.0764 / 2.0) / 0.127)
        inertia = (681.32 + 140.0) / 1000.0 * acceleration
        self.assertAlmostEqual(loads["gas_force_n"], gas)
        self.assertAlmostEqual(loads["tdc_acceleration_m_s2"], acceleration)
        self.assertAlmostEqual(loads["inertia_force_n"], inertia)
        self.assertAlmostEqual(loads["conservative_axial_force_n"], gas + inertia)

    def test_real_six_case_calculix_receipts_and_three_meshes(self) -> None:
        self.assertEqual(self.report["solver"]["execution_count"], 6)
        self.assertIn("Version 2.21", self.report["solver"]["calculix_version_output"])
        self.assertEqual(self.report["solver"]["gmsh_version"], "4.12.1")
        self.assertEqual(
            [case["mesh"]["mesh_size_mm"] for case in self.report["cases"]],
            [5.0, 3.5, 2.5],
        )
        for case in self.report["cases"]:
            self.assertEqual(case["cold_linear_static"]["return_code"], 0)
            self.assertEqual(
                case["hot_sequential_thermomechanical"]["return_code"], 0
            )

    def test_finest_mesh_is_numerically_converged_but_hot_screen_fails(self) -> None:
        finest = self.report["cases"][-1]
        hot = finest["hot_sequential_thermomechanical"]
        self.assertGreater(finest["mesh"]["nodes"], 100_000)
        self.assertGreater(finest["mesh"]["quadratic_tetrahedra"], 50_000)
        self.assertGreater(hot["von_mises_mpa"]["p95"], 297.0)
        self.assertGreater(hot["temperature_c"]["maximum"], 160.0)
        self.assertLess(hot["temperature_c"]["maximum"], 250.0)
        self.assertTrue(all(self.report["numerical_gates"].values()))
        self.assertLess(
            self.report["ambient_reference_strength_ratios"][
                "hot_p95_yield_to_stress"
            ],
            1.0,
        )

    def test_fatigue_life_and_release_remain_fail_closed(self) -> None:
        fatigue = self.report["fatigue_proxy"]
        self.assertEqual(fatigue["shaft_revolutions_at_100h"], 40_320_000.0)
        self.assertEqual(
            fatigue["combustion_events_per_cylinder_at_100h"], 20_160_000.0
        )
        self.assertFalse(fatigue["cp1_hot_sn_curve_available"])
        self.assertIsNone(fatigue["predicted_life_cycles"])
        self.assertTrue(all(not value for value in self.report["engineering_gates"].values()))
        self.assertIsNone(self.report["selected_variant"])
        self.assertFalse(self.report["manufacturing_authorized"])
        self.assertFalse(self.report["engine_operation_authorized"])
        self.assertFalse(self.report["release_authorized"])

    def test_report_hashes_and_calculations_are_independently_verified(self) -> None:
        checked = CHECK.verify(ROOT, REPORT)
        self.assertEqual(checked["status"], "PASS")
        self.assertEqual(checked["solver_executions"], 6)
        self.assertFalse(checked["release_authorized"])

    def test_catalogue_and_twin_reference_the_solver_evidence(self) -> None:
        evidence = (
            "twins/993-m64-60-piston-gallery-f0/evidence/calculix-f0/"
            "calculix-thermomechanical-screen.json"
        )
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        twin = json.loads(TWIN.read_text(encoding="utf-8"))
        self.assertIn(evidence, record["validation"]["evidence"])
        self.assertIn(evidence, twin["validation"]["evidence"])


if __name__ == "__main__":
    unittest.main()
