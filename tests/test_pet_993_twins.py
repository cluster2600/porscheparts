import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_twins.py"
SPEC = importlib.util.spec_from_file_location("generate_pet_993_twins", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993TwinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads(generator.TRACKED_INDEX.read_text(encoding="utf-8"))
        cls.crosswalk = json.loads(generator.TRACKED_CROSSWALK.read_text(encoding="utf-8"))

    def test_index_covers_the_complete_documentary_union(self) -> None:
        scope = self.index["scope"]
        self.assertEqual(scope["listed_documentary_twins"], 12864)
        self.assertEqual(scope["read_documentary_twins"], 15)
        self.assertEqual(scope["total_documentary_twins"], 12879)
        self.assertEqual(scope["unique_oem_references"], 6013)
        self.assertEqual(scope["part_master_twins"], 6013)
        self.assertEqual(scope["illustration_count"], 239)
        self.assertEqual(scope["system_count"], 10)
        self.assertEqual(scope["configured_vehicle_bom_count"], 0)

    def test_shards_close_and_have_digests(self) -> None:
        shards = self.index["output"]["shards"]
        self.assertEqual([item["system_id"] for item in shards], [
            "0xx", "1xx", "2xx", "3xx", "4xx", "5xx", "6xx", "7xx", "8xx", "9xx"
        ])
        self.assertEqual(sum(item["record_count"] for item in shards), 12879)
        for item in shards:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(item["path"].startswith("work/pet-993/twins/"))

        master_shards = self.index["output"]["part_master_shards"]
        self.assertEqual([item["shard_id"] for item in master_shards], list("0123456789abcdef"))
        self.assertEqual(sum(item["record_count"] for item in master_shards), 6013)
        for item in master_shards:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(item["path"].startswith("work/pet-993/part-masters/"))

    def test_source_boundary_keeps_raw_pet_out_of_the_repository(self) -> None:
        boundary = self.index["source_boundary"]
        self.assertFalse(boundary["raw_pet_pdf_copied"])
        self.assertFalse(boundary["pet_illustrations_copied"])
        self.assertRegex(boundary["oem_listed_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(boundary["oem_parts_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(len(boundary["pet_sources"]), 2)
        for source in boundary["pet_sources"]:
            self.assertNotIn("confirmedBy", source["rights"])

    def test_all_engineering_claims_fail_closed(self) -> None:
        readiness = self.index["engineering_readiness"]
        self.assertFalse(readiness["functioning_vehicle_claim"])
        for key, value in readiness.items():
            if key != "functioning_vehicle_claim":
                self.assertEqual(value, 0, key)
        self.assertIn(
            "documentary_twin_authorizes_manufacturing_or_road_use",
            self.index["prohibited_claims"],
        )

    def test_variant_proof_is_not_inferred_from_catalogue_appearance(self) -> None:
        quality = self.index["quality"]
        self.assertEqual(quality["records_with_proven_variants"], 13)
        self.assertEqual(quality["records_without_proven_variants"], 12866)
        self.assertEqual(
            quality["applicability_status_counts"]["unresolved_catalogue_appearance_only"],
            12864,
        )

    def test_declared_engineering_observations_are_coverage_not_decisions(self) -> None:
        coverage = self.index["quality"]["part_master_evidence_coverage"]
        self.assertEqual(coverage["masters_with_declared_bounding_box"], 9)
        self.assertEqual(coverage["masters_with_non_placeholder_declared_material"], 1)
        self.assertEqual(
            coverage["masters_with_declared_bounding_box_and_non_placeholder_material"],
            1,
        )
        self.assertEqual(coverage["qualified_material_decisions"], 0)

    def test_documentary_twin_schema_separates_source_and_engineering(self) -> None:
        row = {
            "oemReference": "993 000 000 00",
            "revision": None,
            "description": "test part",
            "position": 1,
            "petIllustration": "101-00",
            "petGroup": "test group",
            "petPage": 1,
            "petSourceId": "test-source",
            "generationId": "993",
            "depth": "listed",
            "sightings": 1,
        }
        twin = generator.documentary_twin(
            row,
            depth="listed",
            illustration_context={"system_id": "1xx", "system_name": "Moteur"},
            simulation_domains=["structural"],
        )
        self.assertEqual(twin["engineering_state"]["fidelity"], "F0_reference")
        self.assertEqual(twin["vehicle_configuration"]["applicability_status"], "unresolved_catalogue_appearance_only")
        self.assertIsNone(twin["engineering_state"]["material_decision"])
        self.assertEqual(twin["engineering_state"]["reference_solver"], "not_run")
        self.assertFalse(twin["manufacturing"]["functional_release"])

    def test_catalog_crosswalk_is_identity_only_and_closes(self) -> None:
        summary = self.crosswalk["summary"]
        parts = self.crosswalk["parts"]
        self.assertEqual(summary["catalog_part_records"], len(parts))
        self.assertEqual(summary["pet_occurrence_links"], 13)
        self.assertEqual(summary["unmatched_oem_references"], 2)
        self.assertEqual(
            sum(len(part["pet_occurrence_matches"]) for part in parts),
            summary["pet_occurrence_links"],
        )
        self.assertEqual(
            self.index["output"]["catalog_crosswalk"]["sha256"],
            generator.sha256_text(generator.render_json(self.crosswalk)),
        )
        for part in parts:
            self.assertEqual(
                part["claims"]["identity_crosswalk"],
                bool(part["pet_occurrence_matches"]),
            )
            self.assertFalse(part["claims"]["variant_fitment"])
            self.assertFalse(part["claims"]["geometry_fit"])
            self.assertFalse(part["claims"]["manufacturing_release"])

    def test_known_engine_carrier_link_keeps_pet_depth(self) -> None:
        carrier = next(
            part for part in self.crosswalk["parts"] if part["part_id"] == "993-ENG-CARRIER-0001"
        )
        self.assertEqual(carrier["status"], "matched_documentary_identity_only")
        self.assertEqual(len(carrier["pet_occurrence_matches"]), 1)
        match = carrier["pet_occurrence_matches"][0]
        self.assertEqual(match["pet_illustration"], "109-00")
        self.assertEqual(match["record_depth"], "read")
        self.assertEqual(match["part_master_twin_id"], generator.part_master_twin_id("99311502153"))

    def test_engine_carrier_part_master_keeps_evidence_separate_from_decisions(self) -> None:
        occurrence = generator.documentary_twin(
            {
                "oemReference": "993 115 021 53",
                "englishName": "Engine carrier",
                "petIllustration": "109-00",
                "petGroup": "Engine suspension",
                "petIllustrationPage": 42,
                "petPosition": 17,
                "petSourceId": "test-source",
                "generationId": "993",
                "fitsVehicles": ["993-turbo"],
                "oemMaterial": "unknown",
                "safetyLevel": 7,
                "quantityPerCar": 1,
                "petVerified": True,
            },
            depth="read",
            illustration_context={"system_id": "1xx", "system_name": "Moteur"},
            simulation_domains=["structural"],
        )
        carrier = generator.build_part_master_twins(
            [occurrence],
            [
                {
                    "entry_id": "993-ENGINE-CARRIER-TURBO",
                    "oem_reference": "993 115 021 53",
                    "source_id": "TEST-SOURCE",
                    "confidence": "declared",
                    "dimensions_mm": [600.0, 50.0, 50.0],
                    "mass_kg": 1.96,
                    "material": "acier",
                }
            ],
        )[0]
        self.assertEqual(carrier["twin_kind"], "documentary_part_identity_master")
        self.assertEqual(carrier["documentary_graph"]["occurrence_count"], 1)
        self.assertEqual(
            carrier["documentary_graph"]["proven_variant_contexts"][0]["proven_variants"],
            ["993-turbo"],
        )
        self.assertEqual(
            carrier["documentary_graph"]["source_material_observations"][0]["source_material"],
            "unknown",
        )
        declared = carrier["documentary_graph"]["declared_engineering_observations"][0]
        self.assertEqual(declared["bounding_box_mm"], [600.0, 50.0, 50.0])
        self.assertEqual(declared["material"], "acier")
        self.assertEqual(
            declared["observation_status"],
            "declared_not_independently_measured_or_qualified",
        )
        self.assertIsNone(carrier["engineering_state"]["selected_material"])
        self.assertEqual(carrier["engineering_state"]["reference_solver"], "not_run")
        self.assertFalse(carrier["manufacturing"]["functional_release"])

    def test_tracked_index_validator_accepts_committed_state(self) -> None:
        generator.validate_tracked_index(self.index)


if __name__ == "__main__":
    unittest.main()
