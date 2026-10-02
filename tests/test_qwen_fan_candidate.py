import json
from pathlib import Path
import runpy
import unittest

HERE = Path(__file__).resolve().parents[1] / "twins/993-engine-cooling-fan-system-f0/source"
accept = runpy.run_path(str(HERE / "accept_qwen_fan_candidate.py"))["accept"]


class CandidateTest(unittest.TestCase):
    def test_bounded_single_factor_and_rejections(self):
        base = json.loads((HERE / "picogk-reference/organic-e.json").read_text())
        values = {k: base[k] for k in ("blade_pitch_deg", "tip_twist_deg", "camber_mm",
                                     "sweep_mm", "blade_tip_chord_mm")}
        values["blade_pitch_deg"] = 42
        candidate = accept("root = " + json.dumps(values), base)
        self.assertEqual(candidate["blade_pitch_deg"], 42)
        for key in set(base) - set(values) - {"parameter_evidence"}:
            self.assertEqual(candidate[key], base[key])
        for bad in [json.dumps([values]), json.dumps(values | {"sweep_mm": 16}),
                    json.dumps(values | {"blade_pitch_deg": True}),
                    json.dumps(values | {"blade_pitch_deg": 99}),
                    json.dumps(values | {"blade_pitch_deg": float("nan")}),
                    json.dumps(values)[:-1] + ', "sweep_mm": 8}',
                    "import os; " + json.dumps(values)]:
            with self.assertRaises(ValueError):
                accept(bad, base)
