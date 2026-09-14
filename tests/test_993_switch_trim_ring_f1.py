import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-int-switch-trim-ring-f1-0001/source/switch_trim_ring.py"
SPEC = importlib.util.spec_from_file_location("switch_trim_ring", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SwitchTrimRingF1Tests(unittest.TestCase):
    def test_geometry_screen_recomputes_published_dimensions(self) -> None:
        report = MODULE.geometry_screen()
        self.assertEqual(report["status"], "geometry_math_screen_only")
        self.assertAlmostEqual(report["results"]["front_radial_wall_mm"], 3.75)
        self.assertAlmostEqual(report["results"]["rear_radial_wall_mm"], 1.25)

        r_outer, r_front, r_rear, depth = 15.25, 11.5, 14.0, 10.5
        expected = math.pi * r_outer**2 * depth - math.pi * depth * (
            r_front**2 + r_front * r_rear + r_rear**2
        ) / 3.0
        self.assertAlmostEqual(report["results"]["analytic_volume_mm3"], expected)

    def test_release_is_explicitly_blocked(self) -> None:
        report = MODULE.geometry_screen()
        blockers = " ".join(report["release_blockers"])
        self.assertGreaterEqual(len(report["release_blockers"]), 5)
        self.assertIn("Tolérances", blockers)
        self.assertIn("OEM", blockers)
        self.assertEqual(
            report["manufacturing_decision"]["decision"],
            "undecided_pending_sample_and_cost_comparison",
        )


if __name__ == "__main__":
    unittest.main()
