import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_metal_am_geometry_screen.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_metal_am_geometry_screen", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MetalAmGeometryScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_rectangular_machine_fit_uses_independent_axes(self) -> None:
        card = {
            "manufacturer": "EOS",
            "model": "M 290",
            "build_width_mm": 250.0,
            "build_depth_mm": 250.0,
            "build_height_mm": 325.0,
            "source": "https://example.invalid/eos",
        }
        self.module.validate_machine(card)
        result = self.module.machine_fit(card, self.module.np.asarray([120.0, 85.0, 120.0]))
        self.assertEqual(result["build_envelope_type"], "rectangular_prism")
        self.assertEqual(result["width_margin_mm"], 130.0)
        self.assertEqual(result["depth_margin_mm"], 165.0)
        self.assertEqual(result["height_margin_mm"], 205.0)
        self.assertTrue(result["bare_part_nominal_fit"])

    def test_rectangular_machine_rejects_axis_overflow(self) -> None:
        card = {
            "manufacturer": "EOS",
            "model": "M 290",
            "build_width_mm": 250.0,
            "build_depth_mm": 250.0,
            "build_height_mm": 325.0,
            "source": "https://example.invalid/eos",
        }
        result = self.module.machine_fit(card, self.module.np.asarray([251.0, 80.0, 100.0]))
        self.assertFalse(result["bare_part_nominal_fit"])

    def test_circular_machine_keeps_conservative_diameter(self) -> None:
        card = {
            "manufacturer": "Velo3D",
            "model": "Sapphire",
            "build_cylinder_diameter_mm": 315.0,
            "build_height_mm": 400.0,
            "source": "https://example.invalid/velo3d",
        }
        self.module.validate_machine(card)
        result = self.module.machine_fit(card, self.module.np.asarray([120.0, 90.0, 100.0]))
        self.assertEqual(result["build_envelope_type"], "circular_cylinder")
        self.assertEqual(result["conservative_required_diameter_mm"], 150.0)
        self.assertEqual(result["diametral_margin_mm"], 165.0)
        self.assertTrue(result["bare_part_nominal_fit"])

    def test_machine_card_cannot_mix_envelope_types(self) -> None:
        card = {
            "manufacturer": "invalid",
            "model": "mixed",
            "build_cylinder_diameter_mm": 250.0,
            "build_width_mm": 250.0,
            "build_depth_mm": 250.0,
            "build_height_mm": 325.0,
            "source": "https://example.invalid/mixed",
        }
        with self.assertRaises(self.module.ScreenError):
            self.module.validate_machine(card)

    def test_generic_chart_does_not_name_cp1(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("PROCEDE THERMIQUE CP1", source)
        self.assertIn("PROCEDE THERMIQUE CIBLE", source)


if __name__ == "__main__":
    unittest.main()
