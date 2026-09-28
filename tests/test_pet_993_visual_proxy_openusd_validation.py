import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_pet_993_visual_proxy_openusd.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_pet_993_visual_proxy_openusd", MODULE_PATH
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class Pet993VisualProxyOpenUsdValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.build_report()
        cls.manifest = json.loads(validator.ATLAS_MANIFEST.read_text(encoding="utf-8"))

    def test_strict_validator_resolves_all_three_root_stages(self) -> None:
        self.assertEqual(
            self.report["status"], "passed_openusd_strict_not_simready"
        )
        self.assertEqual(self.report["validator"]["command"], "usdchecker --strict")
        self.assertIn("Apple USD Tools", self.report["validator"]["tool_suite"])
        self.assertEqual(self.report["scope"]["validated_root_stages"], 3)
        self.assertEqual(
            self.report["scope"]["visual_proxy_instances_resolved_through_atlas"],
            6013,
        )
        self.assertTrue(
            self.report["scope"][
                "documentary_visual_and_functional_layers_composed"
            ]
        )
        self.assertTrue(
            all(item["result"] == "passed" for item in self.report["validated_stages"])
        )

    def test_validation_is_digest_bound_to_the_generated_stages(self) -> None:
        expected = {
            self.manifest["output"]["prototype_stage"]: self.manifest["output"][
                "prototype_stage_sha256"
            ],
            self.manifest["output"]["root_stage"]: self.manifest["output"][
                "root_stage_sha256"
            ],
            self.manifest["output"]["composed_catalogue_digital_twin_stage"]: self.manifest[
                "output"
            ]["composed_catalogue_digital_twin_stage_sha256"],
        }
        actual = {
            item["path"]: item["sha256"] for item in self.report["validated_stages"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            self.report["source"]["atlas_manifest_sha256"],
            validator.sha256_file(validator.ATLAS_MANIFEST),
        )

    def test_openusd_pass_is_not_promoted_to_simready_or_engineering_proof(self) -> None:
        self.assertEqual(
            self.report["results"]["strict_openusd_validation"], "passed"
        )
        self.assertEqual(
            self.report["results"]["composition_resolution"], "passed"
        )
        self.assertEqual(
            self.report["results"]["nvidia_asset_validator"], "not_run"
        )
        self.assertFalse(self.report["results"]["simready_validated"])
        self.assertTrue(
            all(value is False for value in self.report["claim_boundary"].values())
        )

    def test_checked_in_report_is_current(self) -> None:
        self.assertEqual(validator.main(["--check-index"]), 0)
        self.assertEqual(validator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
