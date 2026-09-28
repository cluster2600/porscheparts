import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_porschefanatics_crosswalk.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_porschefanatics_crosswalk", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993PorscheFanaticsCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, _ = generator.build(generator.DEFAULT_SOURCE_ROOT)
        cls.links = [
            json.loads(line)
            for line in generator.WORK_OUTPUT.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_only_explicit_replaces_oem_claims_create_links(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(scope["porschefanatics_part_records"], 109316)
        self.assertEqual(scope["direct_993_fitment_records"], 29400)
        self.assertEqual(scope["records_with_replaces_oem"], 6)
        self.assertEqual(scope["exact_pet_replacement_links"], 6)
        self.assertEqual(scope["linked_pet_part_masters"], 2)
        self.assertEqual(scope["linked_normalized_oem_references"], 2)
        self.assertEqual(len(self.links), 6)
        self.assertTrue(
            all(item["link_method"] == "exact_normalized_replacesOem" for item in self.links)
        )
        self.assertIn(
            "generation_fitment_without_oem_reference",
            self.manifest["source_boundary"]["prohibited_link_methods"],
        )

    def test_commercial_materials_remain_unqualified_alternative_evidence(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(scope["links_with_qualified_material_basis"], 0)
        self.assertEqual(scope["links_with_unqualified_material_labels"], 6)
        for link in self.links:
            record = link["porschefanatics_record"]
            self.assertEqual(record["material_ids_with_qualified_basis"], [])
            self.assertTrue(record["material_ids_without_qualified_basis"])
            self.assertIsNone(record["material_basis"])

    def test_replacement_claim_never_promotes_oem_or_functional_proof(self) -> None:
        self.assertEqual(
            self.manifest["scope"][
                "promoted_oem_geometry_material_process_or_validation_claims"
            ],
            0,
        )
        for link in self.links:
            evidence = link["evidence_boundary"]
            self.assertTrue(
                evidence["commercial_record_is_exact_oem_replacement_claim"]
            )
            for key, value in evidence.items():
                if key != "commercial_record_is_exact_oem_replacement_claim":
                    self.assertFalse(value)
        self.assertTrue(
            all(value is False for value in self.manifest["claim_boundary"].values())
        )

    def test_tracked_manifest_keeps_commercial_payload_in_work_only(self) -> None:
        rendered = json.dumps(self.manifest, ensure_ascii=False)
        self.assertNotIn("99337504905", rendered)
        self.assertNotIn("99311502190", rendered)
        self.assertNotIn("porschefanatics_record", rendered)
        self.assertNotIn("https://www.", rendered)
        self.assertFalse(self.manifest["output"]["tracked"])
        self.assertEqual(self.manifest["output"]["record_count"], 6)
        self.assertTrue(
            all(
                value is False
                for key, value in self.manifest["rights_boundary"].items()
                if key.startswith("tracked_manifest_contains")
            )
        )

    def test_checked_in_manifest_and_work_crosswalk_are_current(self) -> None:
        self.assertEqual(generator.main(["--check-index"]), 0)
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
