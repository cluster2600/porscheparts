"""DT-01 fit checker: worst-case static margins, H04 corner rule and fail-closed inputs.

Every number in this file and in tests/fixtures/dt01-switch-fit/ is synthetic.
None is a dimension of the switch blank or of a 993 dashboard, and no test here
changes the physical-fit status of the twin or of the part.
"""
import copy
import importlib.util
import itertools
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "993-cabin-dashboard-switch-0001"
MODULE_PATH = TWIN / "source" / "check_fit.py"
CONTRACT_PATH = TWIN / "interface-contract.json"
TWIN_RECORD = ROOT / "catalog" / "twins" / "twin-993-cabin-dashboard-switch-0001.json"
FIXTURES = ROOT / "tests" / "fixtures" / "dt01-switch-fit"
SPEC = importlib.util.spec_from_file_location("check_fit", MODULE_PATH)
check_fit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_fit)


def reading(value, uncertainty=0.1):
    return {"value": value, "uncertainty": uncertainty, "unit": "mm"}


def base_values(**overrides):
    values = {
        "D01": reading(30), "D02": reading(20), "D05": reading(8),
        "D08": reading(27), "D09": reading(17), "D10": reading(2.0, 0.25),
        "H01": reading(28), "H02": reading(18), "H03": reading(3),
        "H04": reading(2.0, 0.25), "H05": reading(12),
    }
    values.update(overrides)
    return values


def rounded_rectangle_sdf(x, y, width, height, radius):
    """Signed distance to a centred rounded rectangle, negative inside."""
    qx = abs(x) - (width / 2 - radius)
    qy = abs(y) - (height / 2 - radius)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    return outside + min(max(qx, qy), 0.0) - radius


def sampled_margin(container, contained, steps=2000):
    """Independent check: minimum inward distance of the body outline to the opening."""
    width, height, radius = container
    inner_width, inner_height, inner_radius = contained
    a = inner_width / 2 - inner_radius
    b = inner_height / 2 - inner_radius
    points = []
    for index in range(steps + 1):
        t = index / steps
        theta = t * math.pi / 2
        points.append((a + inner_radius * math.cos(theta), b + inner_radius * math.sin(theta)))
        points.append((t * a, b + inner_radius))
        points.append((a + inner_radius, t * b))
    return min(-rounded_rectangle_sdf(x, y, width, height, radius) for x, y in points)


class LinearMarginTests(unittest.TestCase):
    def test_positive_worst_case_margins_pass(self) -> None:
        report = check_fit.calculate(base_values())
        self.assertTrue(report["passed"])
        self.assertAlmostEqual(report["metrics"]["horizontal_clearance"]["worst_case_margin_mm"], 0.8)

    def test_uncertainty_can_fail_nominal_clearance(self) -> None:
        report = check_fit.calculate(base_values(D08=reading(27.9, 0.1), H01=reading(28, 0.1)))
        self.assertFalse(report["passed"])
        self.assertLess(report["metrics"]["horizontal_clearance"]["worst_case_margin_mm"], 0)

    def test_zero_worst_case_margin_is_not_a_pass(self) -> None:
        # Binary-exact values: worst case 28.25 - 28.25 is exactly zero.
        report = check_fit.calculate(base_values(D08=reading(28.0, 0.25), H01=reading(28.5, 0.25)))
        metric = report["metrics"]["horizontal_clearance"]
        self.assertEqual(metric["worst_case_margin_mm"], 0.0)
        self.assertFalse(metric["passed"])
        self.assertFalse(report["passed"])


class CornerRuleTests(unittest.TestCase):
    def test_closed_form_matches_independent_distance_sampling(self) -> None:
        generator = random.Random(505)
        for _ in range(150):
            width = generator.uniform(10, 40)
            height = generator.uniform(10, 40)
            radius = generator.uniform(0, min(width, height) / 2)
            inner_width = width - generator.uniform(-1, 3)
            inner_height = height - generator.uniform(-1, 3)
            inner_radius = generator.uniform(0, min(inner_width, inner_height) / 2)
            container = (width, height, radius)
            contained = (inner_width, inner_height, inner_radius)
            margin, _ = check_fit.rounded_rectangle_margin(container, contained)
            self.assertAlmostEqual(margin, sampled_margin(container, contained), delta=1e-4)

    def test_sharp_body_in_rounded_opening_interferes_although_sides_clear(self) -> None:
        margin, governs = check_fit.rounded_rectangle_margin((30, 20, 3), (29, 19, 0))
        self.assertEqual(governs, "corner")
        self.assertAlmostEqual(margin, 3 - math.sqrt(2) * 2.5)
        self.assertLess(margin, 0)
        report = check_fit.calculate(base_values(
            H01=reading(30, 0.01), H02=reading(20, 0.01), H04=reading(3, 0.01),
            D08=reading(29, 0.01), D09=reading(19, 0.01), D10=reading(0.1, 0.01),
        ))
        self.assertTrue(report["metrics"]["horizontal_clearance"]["passed"])
        self.assertTrue(report["metrics"]["vertical_clearance"]["passed"])
        self.assertFalse(report["metrics"]["corner_insertion_clearance"]["passed"])
        self.assertFalse(report["passed"])

    def test_body_corner_at_least_as_round_as_opening_is_side_governed(self) -> None:
        margin, governs = check_fit.rounded_rectangle_margin((30, 20, 2), (29, 19, 2))
        self.assertEqual(governs, "side")
        self.assertAlmostEqual(margin, 0.5)

    def test_tangent_corner_boundary(self) -> None:
        # Worst case: c = 0.5, D10 = 0.75; the corner gap is zero at
        # H04 = 0.75 + 0.5 * (2 + sqrt 2). Step either side of the root.
        root = 0.75 + 0.5 * (2 + math.sqrt(2)) - 0.25
        for offset, expected in ((-1e-6, True), (1e-6, False)):
            report = check_fit.calculate(base_values(
                H01=reading(28.25, 0.125), H02=reading(18.25, 0.125), H04=reading(root + offset, 0.25),
                D08=reading(27.0, 0.125), D09=reading(17.0, 0.125), D10=reading(1.0, 0.25),
            ))
            metric = report["metrics"]["corner_insertion_clearance"]
            self.assertEqual(metric["worst_case_governed_by"], "corner")
            self.assertEqual(metric["passed"], expected, offset)

    def test_uncertainty_alone_can_fail_the_corner(self) -> None:
        values = base_values(
            H01=reading(40, 0.02), H02=reading(24, 0.02), H04=reading(3.0, 0.5),
            D08=reading(39, 0.02), D09=reading(23, 0.02), D10=reading(2.0, 0.5),
        )
        metric = check_fit.calculate(values)["metrics"]["corner_insertion_clearance"]
        self.assertGreater(metric["nominal_margin_mm"], 0)
        self.assertLess(metric["worst_case_margin_mm"], 0)
        self.assertFalse(metric["passed"])

    def test_worst_case_is_the_minimum_over_the_uncertainty_box(self) -> None:
        values = base_values(
            H01=reading(40, 0.1), H02=reading(24, 0.1), H04=reading(3.0, 0.25),
            D08=reading(39, 0.1), D09=reading(23, 0.1), D10=reading(2.0, 0.25),
        )
        reported = check_fit.calculate(values)["metrics"]["corner_insertion_clearance"]["worst_case_margin_mm"]
        keys = ("H01", "H02", "H04", "D08", "D09", "D10")
        lowest = math.inf
        for signs in itertools.product((-1, 0, 1), repeat=len(keys)):
            shifted = {key: values[key]["value"] + sign * values[key]["uncertainty"] for key, sign in zip(keys, signs)}
            margin, _ = check_fit.rounded_rectangle_margin(
                (shifted["H01"], shifted["H02"], shifted["H04"]), (shifted["D08"], shifted["D09"], shifted["D10"]))
            lowest = min(lowest, margin)
        self.assertAlmostEqual(reported, lowest, places=6)

    def test_physical_bounds_are_applied_and_recorded(self) -> None:
        values = base_values(D10=reading(0.1, 0.25), H04=reading(9.0, 0.5), H01=reading(28, 0.1), H02=reading(18, 0.1))
        metric = check_fit.calculate(values)["metrics"]["corner_insertion_clearance"]
        self.assertEqual(metric["worst_case_inputs_mm"]["D10"], 0.0)
        self.assertEqual(metric["worst_case_inputs_mm"]["H04"], 8.95)
        self.assertEqual(len(metric["bounds_applied"]), 2)


class FailClosedValueTests(unittest.TestCase):
    def assertRefused(self, values, fragment):
        with self.assertRaises(SystemExit) as raised:
            check_fit.calculate(values)
        self.assertIn(fragment, str(raised.exception.code))

    def test_absent_corner_inputs_are_refused(self) -> None:
        for key in ("D10", "H04"):
            values = base_values()
            del values[key]
            self.assertRefused(values, key)

    def test_unit_mismatch_is_refused(self) -> None:
        for unit in ("in", "deg", None):
            values = base_values()
            values["H04"] = dict(values["H04"], unit=unit)
            self.assertRefused(values, "expected mm")

    def test_non_finite_and_non_numeric_values_are_refused(self) -> None:
        for bad in (math.nan, math.inf, -math.inf, "2.0", True, None):
            values = base_values(H04=dict(reading(2.0), value=bad))
            self.assertRefused(values, "H04.value")
            values = base_values(D10=dict(reading(2.0), uncertainty=bad))
            self.assertRefused(values, "D10.uncertainty")

    def test_zero_uncertainty_is_refused(self) -> None:
        self.assertRefused(base_values(H04=reading(2.0, 0)), "greater than zero")

    def test_nonphysical_values_are_refused(self) -> None:
        self.assertRefused(base_values(D10=reading(-0.5, 0.25)), "negative corner radius")
        self.assertRefused(base_values(H04=reading(9.5, 0.25)), "exceeds half")
        self.assertRefused(base_values(D10=reading(8.6, 0.25)), "exceeds half")
        self.assertRefused(base_values(H01=reading(0.1, 0.1)), "nonphysical length")


def fixture_record():
    return json.loads((FIXTURES / "corner-pass-measurements.json").read_text(encoding="utf-8"))


class FailClosedRecordTests(unittest.TestCase):
    def assertRecordRefused(self, record, fragment, raw=None):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            path.write_text(raw if raw is not None else json.dumps(record), encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                check_fit.load_readings(path)
        self.assertIn(fragment, str(raised.exception.code))

    def edit(self, dimension, **fields):
        record = fixture_record()
        for item in record["readings"]:
            if item["dimension_id"] == dimension:
                item.update(fields)
        return record

    def test_fixture_record_is_accepted(self) -> None:
        readings = check_fit.load_readings(FIXTURES / "corner-pass-measurements.json")
        self.assertEqual(set(readings), set(check_fit.REQUIRED))

    def test_missing_h04_reading_is_refused(self) -> None:
        record = fixture_record()
        record["readings"] = [item for item in record["readings"] if item["dimension_id"] != "H04"]
        self.assertRecordRefused(record, "H04")

    def test_duplicate_reading_is_refused(self) -> None:
        record = fixture_record()
        duplicate = copy.deepcopy(next(item for item in record["readings"] if item["dimension_id"] == "H04"))
        duplicate.update(samples=[3.5, 3.5, 3.5], value=3.5)
        record["readings"].append(duplicate)
        self.assertRecordRefused(record, "duplicate")

    def test_nan_and_infinity_literals_are_refused(self) -> None:
        text = (FIXTURES / "corner-pass-measurements.json").read_text(encoding="utf-8")
        for literal in ("NaN", "Infinity", "-Infinity"):
            raw = text.replace('"value": 3.0', f'"value": {literal}', 1)
            self.assertNotEqual(raw, text)
            self.assertRecordRefused(None, "non-finite", raw=raw)
        # 1e400 parses as infinity without a NaN literal; it must still be refused.
        raw = text.replace('"value": 3.0', '"value": 1e400', 1)
        self.assertRecordRefused(None, "validate_measurements", raw=raw)

    def test_unit_outside_schema_is_refused(self) -> None:
        self.assertRecordRefused(self.edit("H04", unit="in"), "validate_measurements")

    def test_unit_inside_schema_but_not_mm_is_refused(self) -> None:
        self.assertRecordRefused(self.edit("H04", unit="deg"), "expected mm")

    def test_derived_host_reading_is_refused(self) -> None:
        self.assertRecordRefused(self.edit("H01", method="derived"), "empty opening")
        self.assertRecordRefused(self.edit("H04", method="derived"), "empty opening")

    def test_unsupported_radius_method_is_refused(self) -> None:
        for method in ("direct", "scan", "photogrammetry", "indirect"):
            self.assertRecordRefused(self.edit("H04", method=method), "not supported")
            self.assertRecordRefused(self.edit("D10", method=method), "not supported")

    def test_fewer_than_three_samples_is_refused(self) -> None:
        self.assertRecordRefused(self.edit("D10", samples=[2.0, 2.0]), "at least 3 samples")

    def test_value_contradicting_its_samples_is_refused(self) -> None:
        self.assertRecordRefused(self.edit("H04", samples=[2.0, 2.0, 2.0]), "validate_measurements")

    def test_undeclared_instrument_is_refused(self) -> None:
        self.assertRecordRefused(self.edit("H04", instrument_id="NOT-DECLARED"), "validate_measurements")

    def test_record_for_another_part_is_refused(self) -> None:
        record = fixture_record()
        record["subject"]["part_id"] = "993-INT-OTHER-PART-0001"
        self.assertRecordRefused(record, "subject.part_id")
        record["subject"]["part_id"] = None
        self.assertRecordRefused(record, "subject.part_id")

    def test_documented_specification_is_refused(self) -> None:
        record = fixture_record()
        record["record_kind"] = "documented_specification"
        self.assertRecordRefused(record, "declared values do not feed a fit check")


class ReportTests(unittest.TestCase):
    def run_checker(self, name):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "report.json"
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--measurements", str(FIXTURES / f"{name}-measurements.json"),
                 "--out", str(out)],
                capture_output=True, text=True, check=False,
            )
            return result.returncode, out.read_text(encoding="utf-8") if out.exists() else None

    def test_fixture_reports_are_reproduced_exactly(self) -> None:
        for name, code in (("corner-pass", 0), ("corner-interference", 2)):
            returncode, produced = self.run_checker(name)
            self.assertEqual(returncode, code, name)
            self.assertEqual(produced, (FIXTURES / f"{name}-report.json").read_text(encoding="utf-8"), name)

    def test_interference_fixture_fails_on_the_corner_only(self) -> None:
        report = json.loads((FIXTURES / "corner-interference-report.json").read_text(encoding="utf-8"))
        failed = [name for name, metric in report["metrics"].items() if not metric["passed"]]
        self.assertEqual(failed, ["corner_insertion_clearance"])

    def test_a_pass_never_claims_clip_force_or_fit(self) -> None:
        report = json.loads((FIXTURES / "corner-pass-report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual(report["physical_fit_status"], "not_established")
        self.assertIn("clip_insertion_force", report["not_evaluated"])
        self.assertIn("clip_retention_force", report["not_evaluated"])
        self.assertFalse(any("force" in name for name in report["metrics"]))
        for name, metric in report["metrics"].items():
            self.assertTrue(metric["limitations"], name)
        self.assertNotIn("H04 is not yet computed", json.dumps(report))

    def test_invalid_record_writes_no_report(self) -> None:
        record = fixture_record()
        record["readings"] = [item for item in record["readings"] if item["dimension_id"] != "D10"]
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "record.json"
            source.write_text(json.dumps(record), encoding="utf-8")
            out = Path(folder) / "report.json"
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--measurements", str(source), "--out", str(out)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("D10", result.stderr)
            self.assertFalse(out.exists())


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_checker_inputs_match_the_independent_contract(self) -> None:
        dimensions = self.contract["dimensions"]
        self.assertEqual(set(dimensions), set(check_fit.REQUIRED))
        for key, spec in dimensions.items():
            self.assertEqual(set(spec["methods"]), check_fit.METHODS[key], key)
            if spec["kind"] == "radius":
                self.assertEqual(tuple(spec["bounded_by"]), check_fit.RADII[key], key)
        self.assertEqual({key for key, spec in dimensions.items() if spec["kind"] == "radius"}, set(check_fit.RADII))
        self.assertEqual(self.contract["input_record"]["min_samples"], check_fit.MIN_SAMPLES)
        self.assertEqual(self.contract["contract_id"], check_fit.CONTRACT_ID)

    def test_checker_metrics_match_the_independent_contract(self) -> None:
        metrics = self.contract["metrics"]
        linear = {name: (spec["positive"], spec["negative"]) for name, spec in metrics.items()
                  if spec["rule"] == "linear_difference"}
        self.assertEqual(linear, check_fit.METRICS)
        corner = metrics[check_fit.CORNER_METRIC]
        self.assertEqual(corner["container"], check_fit.CORNER_INPUTS["container"])
        self.assertEqual(corner["contained"], check_fit.CORNER_INPUTS["contained"])

    def test_clip_force_stays_outside_the_contract_metrics(self) -> None:
        self.assertIn("clip_insertion_force", self.contract["not_evaluated"])
        self.assertEqual(set(self.contract["not_evaluated"]), set(check_fit.NOT_EVALUATED))
        self.assertFalse(any("force" in name for name in self.contract["metrics"]))

    def test_twin_record_declares_the_corner_interface_without_a_status_change(self) -> None:
        record = json.loads(TWIN_RECORD.read_text(encoding="utf-8"))
        interfaces = {item["interface_id"]: item for item in record["interfaces"]}
        corner = interfaces["IF_CORNER_INSERTION"]
        spec = self.contract["metrics"][check_fit.CORNER_METRIC]
        expected = set(spec["container"].values()) | set(spec["contained"].values())
        self.assertEqual(set(corner["required_measurements"]), expected)
        for interface_id, interface in interfaces.items():
            for key in interface["required_measurements"]:
                self.assertIn(key, check_fit.REQUIRED, interface_id)

    def test_no_status_moves_without_a_physical_session(self) -> None:
        # Software tests and synthetic fixtures never move the twin: while the
        # register holds no physical session for the part, every interface
        # stays missing_data and the twin stays a concept.
        sessions = []
        for path in sorted((ROOT / "catalog" / "measurements").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if (record.get("subject") or {}).get("part_id") == check_fit.CANDIDATE_PART_ID and \
                    record.get("record_kind", "physical_measurement") == "physical_measurement":
                sessions.append(path.name)
        if sessions:
            self.skipTest(f"physical sessions present: {sessions}")
        record = json.loads(TWIN_RECORD.read_text(encoding="utf-8"))
        self.assertEqual({item["status"] for item in record["interfaces"]}, {"missing_data"})
        self.assertEqual(record["validation"]["status"], "concept")

if __name__ == "__main__":
    unittest.main()
