#!/usr/bin/env python3
"""Tests du rendu des mesures AdditiveFOAM F42.2."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "twins/reference-917-engine/source/render_additivefoam_f42_results.py"
SPEC = importlib.util.spec_from_file_location("render_additivefoam_f42_results", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def fixture() -> dict:
    measurements = []
    for power in (360, 380, 400):
        for speed in (1200, 1300, 1500):
            for hatch in (130, 150, 160):
                measurements.append(
                    {
                        "case_id": f"P{power}-V{speed}-H{hatch}",
                        "resolution": "nominal",
                        "temperature_max_k": 2200.0,
                        "temperature_p99_k": 1200.0 + power - 360,
                        "melt_pool_length_mm": 0.50,
                        "melt_pool_width_mm": 0.18,
                        "melt_pool_depth_mm": 0.10,
                    }
                )
    return {
        "phase": "F42",
        "measurements": measurements,
        "temperature_limit_policy": {"cap_hit_count": 0},
        "convergence": {},
        "gates": {
            "doe_response_ranking_permitted": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }


class F42LpbfResultsRenderTests(unittest.TestCase):
    def test_valid_3x3x3_report_renders_png(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.png"
            MODULE.render(fixture(), output, "fixture")
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_missing_nominal_case_fails_closed(self) -> None:
        report = fixture()
        report["measurements"].pop()
        with self.assertRaisesRegex(ValueError, "27_mesures_nominales_requises"):
            MODULE.validate_results(report)

    def test_invalid_case_identifier_is_rejected(self) -> None:
        report = fixture()
        report["measurements"][0]["case_id"] = "bad"
        with self.assertRaisesRegex(ValueError, "identifiant_cas_invalide"):
            MODULE.validate_results(report)


if __name__ == "__main__":
    unittest.main()
