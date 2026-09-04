from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f40"
METADATA = EVIDENCE / "execution-metadata.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class UnsteadyConvergenceF40EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metadata = load(METADATA)
        cls.report_path = ROOT / cls.metadata["canonical_report"]["path"]
        cls.report = load(cls.report_path)

    def test_hashes_bind_the_exact_contract_runner_and_report(self) -> None:
        for key in ("contract", "runner"):
            item = self.metadata[key]
            self.assertEqual(sha256(ROOT / item["path"]), item["sha256"])
        canonical = self.metadata["canonical_report"]
        self.assertEqual(sha256(self.report_path), canonical["sha256"])
        self.assertEqual(self.report_path.stat().st_size, canonical["byte_count"])
        self.assertEqual(
            {item["report_sha256"] for item in self.metadata["runs"]},
            {canonical["sha256"]},
        )

    def test_report_is_a_twelve_cylinder_six_case_campaign(self) -> None:
        cases = self.report["campaign"]["case_reports"]
        self.assertEqual(len(cases), 6)
        for case in cases:
            self.assertEqual(case["case_summary"]["cylinder_spec_count"], 12)
            self.assertEqual(case["crank_validation"]["runtime_cylinder_count"], 12)
            self.assertEqual(case["case_summary"]["valve_port_count"], 24)
            self.assertEqual(len(case["cycle_boundaries"]), 4)
            self.assertIs(case["four_cycles_completed"], True)

    def test_nonconvergence_blocks_sensitivity_and_all_physical_claims(self) -> None:
        gates = self.report["numerical_gates"]
        self.assertIs(gates["all_cases_executed_four_cycles"], True)
        self.assertIs(gates["all_runtime_fields_finite"], True)
        self.assertIs(gates["all_runtime_states_positive"], True)
        self.assertIs(
            gates["aggregate_cycle_boundary_convergence_all_cases_demonstrated"],
            False,
        )
        for family in ("mesh", "temporal", "initial_state"):
            self.assertIs(self.report["sensitivity"][family]["evaluated"], False)
            self.assertIs(self.report["sensitivity"][family]["within_tolerance"], False)
        self.assertTrue(all(value is False for value in self.report["physical_release_gates"].values()))

    def test_last_aggregate_deltas_exceed_the_locked_threshold(self) -> None:
        deltas = [
            case["cycle_convergence"]["relative_deltas"][-1]["maximum_relative_delta"]
            for case in self.report["campaign"]["case_reports"]
        ]
        self.assertGreater(min(deltas), 0.041)
        self.assertLess(max(deltas), 0.045)
        self.assertTrue(all(value > 0.001 for value in deltas))


if __name__ == "__main__":
    unittest.main()
