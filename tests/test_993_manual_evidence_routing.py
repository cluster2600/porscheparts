import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_manual_evidence_routing.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_993_manual_evidence_routing", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class ManualEvidenceRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))

    def test_complete_manual_ledger_is_partitioned(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["manual_records"], 2496)
        self.assertEqual(scope["technical_data_records"], 111)
        self.assertEqual(scope["torque_spec_records"], 195)
        self.assertEqual(scope["measurement_occurrence_records"], 2190)
        self.assertEqual(scope["system_routed_records"], 2442)
        self.assertEqual(scope["unresolved_system_records"], 54)
        self.assertEqual(
            scope["system_routed_records"] + scope["unresolved_system_records"],
            scope["manual_records"],
        )

    def test_all_ten_vehicle_systems_receive_evidence_routes(self) -> None:
        coverage = self.contract["coverage"]["records_by_system"]
        self.assertEqual(set(coverage), {f"{value}xx" for value in range(10)})
        self.assertEqual(sum(coverage.values()), 2442)
        self.assertTrue(all(value > 0 for value in coverage.values()))
        self.assertEqual(
            self.contract["coverage"]["unresolved_records_by_collection"],
            {"measurement_occurrences": 54},
        )

    def test_lexical_part_candidates_remain_review_only(self) -> None:
        scope = self.contract["scope"]
        candidates = self.contract["part_review_candidates"]
        self.assertEqual(scope["part_review_candidate_records"], 158)
        self.assertEqual(scope["part_review_candidate_links"], 1569)
        self.assertEqual(scope["part_master_twins_with_candidates"], 417)
        self.assertEqual(scope["lexically_unambiguous_candidate_records"], 10)
        self.assertEqual(scope["promoted_part_measurements_or_torques"], 0)
        self.assertTrue(any(item["candidate_part_master_count"] > 1 for item in candidates))
        for item in candidates:
            self.assertEqual(
                item["review_status"],
                "manual_review_required_exact_lexical_match_only",
            )
            self.assertFalse(any(item["claims"].values()))

    def test_routing_records_reference_source_rows_without_copying_pdf(self) -> None:
        records = self.contract["routing_records"]
        self.assertEqual(len(records), 2496)
        self.assertEqual(
            len({item["manual_evidence_id"] for item in records}),
            2496,
        )
        self.assertFalse(self.contract["source_boundary"]["manual_pdf_copied"])
        self.assertTrue(self.contract["source_boundary"]["source_master_shards_verified"])

    def test_checked_in_contract_is_current(self) -> None:
        self.assertEqual(generator.run(write=False), 0)
        self.assertEqual(generator.run(write=False, check_index=True), 0)


if __name__ == "__main__":
    unittest.main()
