"""Check the 935 CFD admissibility verdict and the validator that holds it to its evidence."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_935_admissibility.py"
RECORD = ROOT / "twins" / "935-horizontal-cooling-system-f0" / "admissibility.json"

sys.path.insert(0, str(ROOT / "scripts"))
from validate_935_admissibility import validate  # noqa: E402


class AdmissibilityRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))

    def test_repository_record_passes_the_validator(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_rotor_wall_is_currently_blocked_for_parameter_studies(self):
        self.assertEqual(self.record["verdict"], "inadmissible_for_cfd_parameter_studies")

    def test_every_cited_report_exists_and_carries_its_digest(self):
        for finding in self.record["basis"]:
            report = ROOT / finding["report"]
            self.assertTrue(report.is_file(), finding["report"])
            self.assertIn(finding["evidence_sha256"], report.read_text(encoding="utf-8"))

    def test_the_trials_already_spent_are_recorded_against_the_verdict(self):
        """The eight rejected trials of 2026-10-28 are why this record exists."""
        spent = [trial for family in self.record["blocks"]
                 for trial in family["recorded_rejections"]]
        self.assertGreaterEqual(len(spent), 6)
        for trial in spent:
            self.assertTrue((ROOT / trial["report"]).is_file(), trial["report"])
            self.assertTrue(trial["pull_requests"])

    def test_diagnostics_and_reacquisition_stay_open(self):
        """A blocking verdict that stops every kind of work would just be ignored."""
        self.assertTrue(self.record["does_not_block"])
        self.assertTrue(self.record["clears_when"])
        joined = " ".join(self.record["does_not_block"]).lower()
        self.assertIn("audit", joined)

    def test_record_claims_no_result_or_permission(self):
        joined = " ".join(self.record["limitations"]).lower()
        self.assertIn("no permission to manufacture", joined)


class ValidatorRejectionTests(unittest.TestCase):
    """The validator has to fail on a bad record, not only pass on the good one."""

    def setUp(self):
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))

    def mutate(self, change):
        record = copy.deepcopy(self.record)
        change(record)
        return validate(record)

    def test_unknown_verdict_refused(self):
        errors = self.mutate(lambda r: r.update(verdict="looks_fine"))
        self.assertTrue(any("not one of" in e for e in errors), errors)

    def test_drifted_digest_refused(self):
        errors = self.mutate(lambda r: r["basis"][0].update(evidence_sha256="0" * 64))
        self.assertTrue(any("drifted from its evidence" in e for e in errors), errors)

    def test_missing_report_refused(self):
        errors = self.mutate(lambda r: r["basis"][0].update(report="docs/nope.md"))
        self.assertTrue(any("not a file in this repository" in e for e in errors), errors)

    def test_blocking_without_recorded_rejections_refused(self):
        errors = self.mutate(lambda r: r["blocks"][0].update(recorded_rejections=[]))
        self.assertTrue(any("already spent" in e for e in errors), errors)

    def test_blocking_without_clearing_conditions_refused(self):
        errors = self.mutate(lambda r: r.update(clears_when=[]))
        self.assertTrue(any("clears_when" in e for e in errors), errors)

    def test_unnamed_varied_setting_refused(self):
        errors = self.mutate(lambda r: r["blocks"][0]["recorded_rejections"][0].update(change=" "))
        self.assertTrue(any("single setting that was varied" in e for e in errors), errors)

    def test_clean_record_has_no_errors(self):
        self.assertEqual(validate(self.record), [])


if __name__ == "__main__":
    unittest.main()
