#!/usr/bin/env python3
"""Tests du rendu de reproductibilite AdditiveFOAM F42.2."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/render_additivefoam_f42_comparison.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_additivefoam_f42_comparison", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report() -> dict:
    case_ids = [
        f"P{power}-V{speed}-H{hatch}"
        for power in (360, 380, 400)
        for speed in (1200, 1300, 1500)
        for hatch in (130, 150, 160)
    ]
    rows = []
    for index, case_id in enumerate(case_ids):
        metrics = {
            name: {
                "left": 300.0 + index,
                "right": 300.0 + index,
                "relative_difference": 0.0,
                "passes": True,
            }
            for name in (
                "temperature_max_k",
                "temperature_p99_k",
                "molten_volume_mm3",
                "melt_pool_length_mm",
                "melt_pool_width_mm",
                "melt_pool_depth_mm",
                "maximum_courant_number",
            )
        }
        rows.append(
            {
                "case_id": case_id,
                "resolution": "nominal",
                "present_on_both_hosts": True,
                "metrics": metrics,
                "passes": True,
            }
        )
    for case_id in case_ids[:3]:
        for resolution in ("coarse", "fine"):
            duplicate = dict(rows[case_ids.index(case_id)])
            duplicate["resolution"] = resolution
            duplicate["metrics"] = {
                name: dict(value) for name, value in duplicate["metrics"].items()
            }
            rows.append(duplicate)
    return {
        "phase": "F42.2",
        "hosts": {"left": "hote-a", "right": "hote-b"},
        "case_set_identical": True,
        "comparisons": rows,
        "gates": {"all_33_runs_reproduced_within_tolerance": True},
    }


class F42LpbfComparisonRenderTests(unittest.TestCase):
    def test_valid_report_renders_png(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "comparison.png"
            module.render(report(), output)
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertGreater(output.stat().st_size, 20_000)

    def test_missing_case_fails_closed(self) -> None:
        module = load_module()
        payload = report()
        payload["comparisons"].pop()
        with self.assertRaisesRegex(ValueError, "33_comparaisons_requises"):
            module.validate(payload)

    def test_missing_metric_fails_closed(self) -> None:
        module = load_module()
        payload = report()
        del payload["comparisons"][0]["metrics"]["temperature_p99_k"]
        with self.assertRaisesRegex(ValueError, "jeu_de_metriques_invalide"):
            module.validate(payload)


if __name__ == "__main__":
    unittest.main()
