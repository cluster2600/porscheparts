from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f39"
REPORT = EVIDENCE / "intel-native-run-ddc7703.json"
METADATA = EVIDENCE / "execution-metadata.json"
CONTRACT = ROOT / "twins/reference-917-engine/unsteady-network-f39.json"
RUNNER = ROOT / "twins/reference-917-engine/source/run_unsteady_network_f39.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class F39ExecutionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = load(REPORT)
        cls.metadata = load(METADATA)

    def test_evidence_is_hash_bound_to_code_contract_and_image(self) -> None:
        self.assertEqual(sha256(CONTRACT), self.metadata["contract"]["sha256"])
        self.assertEqual(sha256(RUNNER), self.metadata["runner"]["sha256"])
        self.assertEqual(sha256(REPORT), self.metadata["canonical_report"]["sha256"])
        self.assertEqual(REPORT.stat().st_size, self.metadata["canonical_report"]["byte_count"])
        self.assertIn("@sha256:", self.metadata["container"]["reference"])

    def test_two_native_runs_are_recorded_byte_identical(self) -> None:
        hashes = {item["report_sha256"] for item in self.metadata["runs"]}
        self.assertEqual(len(self.metadata["runs"]), 2)
        self.assertEqual(hashes, {sha256(REPORT)})
        self.assertIs(self.metadata["observations"]["two_runs_byte_identical"], True)
        self.assertEqual(self.metadata["container"]["architecture"], "amd64")

    def test_only_numerical_execution_gates_are_open(self) -> None:
        self.assertTrue(self.report["numerical_gates"])
        self.assertTrue(all(self.report["numerical_gates"].values()))
        self.assertTrue(self.report["physical_release_gates"])
        self.assertTrue(all(value is False for value in self.report["physical_release_gates"].values()))
        execution = self.report["execution"]
        self.assertEqual(execution["backend_version"], "0.3.3")
        self.assertAlmostEqual(execution["crank_degrees_advanced"], 720.0)
        self.assertEqual(execution["pipe_diagnostic_count"], 27)
        self.assertEqual(execution["component_diagnostic_count"], 15)
        self.assertIs(execution["exact_runtime_coverage"], True)
        self.assertIs(execution["finite_fields"], True)
        self.assertIs(execution["positive_state"], True)

    def test_evidence_does_not_claim_power_or_release(self) -> None:
        self.assertIn("1600_hp", self.metadata["not_proven"])
        self.assertIn("combustion", self.metadata["not_proven"])
        self.assertIn("manufacturing", self.metadata["not_proven"])
        self.assertIs(self.metadata["observations"]["physical_release_gates_all_false"], True)


if __name__ == "__main__":
    unittest.main()
