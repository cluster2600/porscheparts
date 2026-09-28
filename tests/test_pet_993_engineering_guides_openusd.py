import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_pet_993_engineering_guides_openusd.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_pet_993_engineering_guides_openusd", MODULE_PATH
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class Pet993EngineeringGuideOpenUsdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.build_report()

    def test_eight_engineering_stages_pass_strict_openusd(self) -> None:
        self.assertEqual(self.report["scope"]["validated_stage_count"], 8)
        self.assertEqual(self.report["scope"]["validated_F1_surrogate_variants"], 176)
        self.assertEqual(self.report["scope"]["guide_primitive_count"], 97)
        self.assertEqual(self.report["scope"]["pet_linked_part_master_count"], 171)
        self.assertTrue(
            all(item["result"] == "passed" for item in self.report["validated_stages"])
        )

    def test_validation_remains_distinct_from_simready_and_engineering_proof(self) -> None:
        self.assertEqual(
            self.report["status"],
            "passed_openusd_strict_not_nvidia_asset_validator_or_simready",
        )
        self.assertEqual(
            self.report["results"]["nvidia_asset_validator"],
            "not_run_preflight_blocked",
        )
        self.assertFalse(self.report["results"]["simready_validated"])
        self.assertFalse(any(self.report["claim_boundary"].values()))
        for field in (
            "analysis_geometry_count",
            "physics_schema_count",
            "qualified_material_assignment_count",
            "simready_asset_count",
        ):
            self.assertEqual(self.report["scope"][field], 0)

    def test_stage_evidence_is_digest_bound_to_source_reports(self) -> None:
        for stage in self.report["validated_stages"]:
            self.assertEqual(len(stage["source_report_sha256"]), 64)
            self.assertEqual(len(stage["stage_sha256"]), 64)
            self.assertTrue((ROOT / stage["stage"]).is_file())

    def test_checked_in_report_is_current(self) -> None:
        self.assertEqual(validator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
