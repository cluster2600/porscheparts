import json
import unittest

from scripts.model_turbo_dyno_0d import DEFAULT_DATA, DEFAULT_OUTPUT, build_output, validate_data
from scripts.generate_turbo_variants import EXPECTED_VARIANTS, MANIFEST, validate_manifest


class TurboVariantValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_valid(self) -> None:
        self.assertEqual(validate_manifest(self.payload), [])

    def test_manifest_contains_the_three_comparison_variants(self) -> None:
        ids = {variant["variant_id"] for variant in self.payload["variants"]}
        self.assertEqual(ids, EXPECTED_VARIANTS)

    def test_variants_keep_the_same_mass_flow(self) -> None:
        flows = {variant["flow"]["mass_flow_per_case_kg_s"] for variant in self.payload["variants"]}
        self.assertEqual(flows, {self.payload["comparison"]["mass_flow_per_case_kg_s"]})


class TurboDynoValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(DEFAULT_DATA.read_text(encoding="utf-8"))
        cls.derived = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_dyno_reference_data_is_valid(self) -> None:
        self.assertEqual(validate_data(self.payload), [])

    def test_derived_output_is_reproducible(self) -> None:
        self.assertEqual(build_output(self.payload, DEFAULT_DATA), self.derived)

    def test_powerhaus_same_rpm_point_is_consistent(self) -> None:
        run = next(item for item in self.derived["runs"] if item["run_id"].startswith("POWERHAUS"))
        self.assertTrue(run["consistency_checks"])
        self.assertTrue(all(item["status"] == "within_5_percent" for item in run["consistency_checks"]))

    def test_ap_report_is_flagged_when_power_and_torque_do_not_match(self) -> None:
        run = next(item for item in self.derived["runs"] if item["run_id"].startswith("AP-CAR"))
        self.assertEqual(run["consistency_checks"][0]["status"], "inconsistent_over_5_percent")


if __name__ == "__main__":
    unittest.main()
