import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_configuration_part_links.py"
SPEC = importlib.util.spec_from_file_location("generate_993_configuration_part_links", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class ConfigurationPartLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))

    def test_single_dimension_constraint_counts_close(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["eligible_single_dimension_constraint_occurrences"], 694)
        self.assertEqual(scope["resolved_constraint_occurrences"], 682)
        self.assertEqual(scope["unresolved_constraint_occurrences"], 12)
        self.assertEqual(scope["configuration_candidate_links"], 24063)

    def test_eligible_and_resolved_counts_are_partitioned_by_kind(self) -> None:
        coverage = self.contract["coverage"]
        self.assertEqual(
            coverage["eligible_occurrences_by_constraint_kind"],
            {
                "body_style": 192,
                "direct_variant": 173,
                "engine_code": 238,
                "transmission_code": 91,
            },
        )
        self.assertEqual(
            coverage["resolved_occurrences_by_constraint_kind"],
            {
                "body_style": 192,
                "direct_variant": 162,
                "engine_code": 238,
                "transmission_code": 90,
            },
        )

    def test_unresolved_constraints_expose_missing_roster_dimensions(self) -> None:
        unresolved = self.contract["unresolved_constraint_links"]
        kinds = Counter(item["constraint_kind"] for item in unresolved)
        self.assertEqual(kinds, {"direct_variant": 11, "transmission_code": 1})
        values = {value for item in unresolved for value in item["constraint_values"]}
        self.assertEqual(
            values,
            {"993-carrera-s", "993-carrera-4s", "993-turbo-s", "A50.07"},
        )

    def test_all_configuration_candidates_receive_constraints_but_no_bom(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["linked_configuration_candidates"], 149)
        self.assertEqual(scope["unlinked_configuration_candidates"], 0)
        counts = [
            item["single_dimension_constraint_occurrence_count"]
            for item in self.contract["coverage"]["per_configuration_candidate"]
        ]
        self.assertEqual(min(counts), 69)
        self.assertEqual(max(counts), 315)
        self.assertTrue(
            all(
                item["complete_vehicle_bom"] is False
                for item in self.contract["coverage"]["per_configuration_candidate"]
            )
        )

    def test_links_remain_unreviewed_and_unpromoted(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["human_reviewed_constraint_occurrences"], 0)
        self.assertEqual(scope["promoted_vehicle_bom_entries"], 0)
        self.assertEqual(scope["complete_configuration_boms"], 0)
        for link in self.contract["resolved_constraint_links"]:
            self.assertFalse(link["promoted_to_vehicle_bom"])
            self.assertFalse(link["geometry_fit"])
            self.assertFalse(link["manufacturing_release"])

    def test_tracked_contract_validates(self) -> None:
        generator.validate_contract(self.contract)


if __name__ == "__main__":
    unittest.main()
