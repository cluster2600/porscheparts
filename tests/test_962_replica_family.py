"""Displacement options remain arithmetic until measured engine interfaces exist."""
import copy
import csv
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/962-cylinder-head-f0/source/displacement_family.py"
spec = importlib.util.spec_from_file_location("displacement_family", SCRIPT)
family = importlib.util.module_from_spec(spec)
spec.loader.exec_module(family)


class ReplicaFamilyTests(unittest.TestCase):
    def test_default_targets_retain_unknown_dimensions_and_no_qualification(self):
        result = family.report()
        self.assertEqual([v["target_displacement_cm3"] for v in result["variants"]],
                         [2994, 3164, 3400, 3600, 3800, 4000])
        self.assertFalse(any(result["qualification"].values()))
        for variant in result["variants"]:
            self.assertIsNone(variant["bore_mm"])
            self.assertIsNone(variant["stroke_mm"])
            calculated = variant["calculation"]
            self.assertIsNone(calculated["bore_mm"])
            self.assertIsNone(calculated["stroke_mm"])
            self.assertEqual(calculated["input_assumptions"], {})
            self.assertIsNone(calculated["dimension_basis"])
            self.assertFalse(calculated["fitment_validated"])
            self.assertFalse(calculated["geometry_generated"])

    def test_endpoint_arithmetic_and_both_algebra_routes_roundtrip(self):
        for target in (2994, 3164, 3400, 3600, 3800, 4000):
            point = family.calculate(target, bore_mm=102)
            self.assertAlmostEqual(point["swept_volume_per_cylinder_cm3"], target / 6)
            self.assertAlmostEqual(math.pi / 4 * 102 ** 2 * point["stroke_mm"] * 6 / 1000, target)
            other = family.calculate(target, stroke_mm=point["stroke_mm"])
            self.assertAlmostEqual(other["bore_mm"], 102)
            self.assertEqual(point["input_assumptions"], {"bore_mm": 102})
            self.assertEqual(point["dimension_basis"], "algebra_from_assumed_dimension")
            self.assertFalse(point["manufacturing_authorized"])

    def test_invalid_numbers_limits_and_two_assumptions_are_rejected(self):
        bad_numbers = (None, True, False, "4000", float("nan"), float("inf"),
                       -float("inf"), 0, -1, 1e-320, 10 ** 400)
        for number in (*bad_numbers, 2993.999, 4000.0001, 4000.65990807686):
            with self.subTest(target=repr(number)), self.assertRaises(ValueError):
                family.calculate(number)
        for name in ("bore_mm", "stroke_mm"):
            for number in bad_numbers:
                if number is None:
                    continue
                with self.subTest(dimension=name, value=repr(number)), self.assertRaises(ValueError):
                    family.calculate(4000, **{name: number})
            for number in (1e-307, 1e308):
                with self.subTest(dimension=name, extreme=number), self.assertRaises(ValueError):
                    family.calculate(4000, **{name: number})
        with self.assertRaises(ValueError):
            family.calculate(4000, bore_mm=102, stroke_mm=81.6)

    def test_config_cannot_invent_dimensions_history_or_qualification(self):
        config = json.loads(family.CONFIG.read_text())
        for mutation in (
            lambda c: c["reference"].update(published_displacement_cm3=4000),
            lambda c: c.update(status="replica_ready"),
            lambda c: c["reference"].update(bore_mm=95),
            lambda c: c["reference"].update(stroke_mm=70.4),
            lambda c: c["reference"].update(spark_plugs_per_cylinder=1),
            lambda c: c["envelope"].update(max_cm3=4100),
            lambda c: c["design_policy"].update(uniform_head_scaling_allowed=True),
            lambda c: c["design_policy"].update(historical_master_available=True),
            lambda c: c["required_measured_inputs"].update(fastener_pattern_and_load_path=[100, 40]),
            lambda c: c["qualification"].update(manufacturing_authorized=True),
            lambda c: c["variants"][0].update(bore_mm=95),
            lambda c: c["variants"][-1].update(basis="published"),
            lambda c: c["variants"][-1].update(target_displacement_cm3=4000.66),
            lambda c: c["variants"][-1].update(id=c["variants"][0]["id"]),
        ):
            candidate = copy.deepcopy(config)
            mutation(candidate)
            with self.assertRaises(ValueError):
                family.report(candidate)

    def test_cli_preserves_existing_output_and_requires_explicit_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            output.write_text("previous evidence")
            result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "previous evidence")
        result = subprocess.run([sys.executable, str(SCRIPT), "--bore-mm", "102"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --target-cm3", result.stderr)

    def test_retained_report_matches_live_config_and_calculator(self):
        self.assertEqual(json.loads(family.RETAINED_REPORT.read_text()), family.report())

    def test_measurement_template_has_no_results_or_evidence(self):
        with (family.FAMILY / "replica-measurements.template.csv").open(newline="") as source:
            reader = csv.DictReader(source)
            rows = list(reader)
            self.assertEqual(len(reader.fieldnames), len(set(reader.fieldnames)))
        self.assertEqual([row["control_id"] for row in rows],
                         [f"RP-{i:02d}" for i in range(1, 22)])
        for row in rows:
            self.assertNotIn(None, row)
            self.assertNotIn(None, row.values())
            self.assertEqual(row["review_status"], "missing")
            for field in ("result", "standard_uncertainty", "evidence_ref", "sha256",
                          "instrument_id", "calibration_ref", "specimen_id"):
                self.assertEqual(row[field], "")

    def test_program_links_to_current_family(self):
        program = json.loads((family.FAMILY / "kit-program.json").read_text())
        active = program["active_development"]
        self.assertEqual(active["reference_family"], str(family.CONFIG.relative_to(ROOT)))
        for field in ("reference_family", "document"):
            self.assertTrue((ROOT / active[field]).is_file())


if __name__ == "__main__":
    unittest.main()
