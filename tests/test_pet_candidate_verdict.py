"""Verdict on the factory catalogue designations.

The central test is the last one: the verdict written in the judgments file
must follow from its own inputs. That is the guard the earlier screenings
lacked, where a verdict could survive a change in its reasons.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
JUDGEMENTS = ROOT / "catalog/manufacturing/pet-candidate-judgements.json"
TRIAGE = ROOT / "twins/993-exhaust-tip-ti-f0/evidence/selection/pet-part-titanium-triage.json"
VERDICT = ROOT / "twins/993-exhaust-tip-ti-f0/evidence/selection/pet-candidate-verdict.json"
SCRIPT = ROOT / "scripts/screen_pet_candidates.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PetCandidateVerdictTests(unittest.TestCase):
    def test_every_retained_designation_is_judged(self) -> None:
        retained = {item["description"] for item in load(TRIAGE)["shortlist"]}
        judged = set(load(JUDGEMENTS)["parts"])
        self.assertEqual(retained - judged, set())

    def test_the_verdict_covers_everything_judged_not_only_the_triage(self) -> None:
        """The verdict covered the 70 designations the vocabulary recognised.
        It now covers everything judged by hand; otherwise a part that was
        judged but absent from the vocabulary — `muffler` — stayed invisible."""
        report = load(VERDICT)
        judged = set(load(JUDGEMENTS)["parts"])
        retained = {item["description"] for item in load(TRIAGE)["shortlist"]}
        self.assertGreater(report["designations_judged"], len(retained))
        self.assertLessEqual(report["designations_judged"], len(judged))

    def test_opening_a_fiche_requires_all_three_conditions(self) -> None:
        for row in load(VERDICT)["backlog"]:
            with self.subTest(designation=row["description"]):
                self.assertTrue(row["titanium_improves_on_it"])
                self.assertNotIn(
                    row["presumed_safety_class"],
                    ("prohibited_pending_engineering", "safety_critical"),
                )
                self.assertTrue(row["additive_families"])
                self.assertEqual(row["blockers"], [])

    def test_every_rejection_carries_a_reason(self) -> None:
        for row in load(VERDICT)["ranking"]:
            if row["verdict"] == "reject":
                with self.subTest(designation=row["description"]):
                    self.assertTrue(row["blockers"])
                    self.assertTrue(row["reason"].strip())

    def test_the_selected_part_is_in_the_backlog(self) -> None:
        backlog = {row["description"] for row in load(VERDICT)["backlog"]}
        self.assertIn("tail pipe", backlog)

    def test_a_verdict_that_no_longer_follows_its_reasons_is_refused(self) -> None:
        judgements = load(JUDGEMENTS)
        # Flip an input without touching its written verdict.
        judgements["parts"]["hot-air manifold"]["titanium_improves_on_it"] = False
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "judgements.json"
            tampered.write_text(json.dumps(judgements, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--judgements",
                    str(tampered),
                    "--output",
                    str(Path(tmp) / "out.json"),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incoherent", result.stderr)


if __name__ == "__main__":
    unittest.main()
