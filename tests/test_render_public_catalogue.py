"""Public catalogue: only gate-passed records are published, deterministically."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_public_catalogue as cat  # noqa: E402

BRACKET = ROOT / "catalog/parts/993-eng-bracket-0001.json"


def passing(record: dict) -> dict:
    r = copy.deepcopy(record)
    r["validation"].update(status="released", reviewed_by="Reviewer", reviewed_on="2026-11-05")
    return r


class PublicCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(BRACKET.read_text(encoding="utf-8"))

    def test_concept_record_is_refused(self):
        self.assertTrue(any("concept" in r for r in cat.gate_failures(self.record)))

    def test_every_lower_status_is_refused(self):
        for status in ["concept", "dimensionally_reviewed", "prototype_fitted",
                       "functionally_tested", "engineering_reviewed"]:
            r = passing(self.record)
            r["validation"]["status"] = status
            self.assertTrue(cat.gate_failures(r), status)

    def test_released_record_with_review_and_images_passes(self):
        self.assertEqual(cat.gate_failures(passing(self.record)), [])

    def test_released_without_evidence_or_reviewer_is_refused(self):
        r = passing(self.record)
        r["validation"]["evidence"] = []
        r["validation"]["reviewed_by"] = ""
        self.assertEqual(len(cat.gate_failures(r)), 2)

    def test_released_without_images_is_refused(self):
        r = passing(self.record)
        r["part_id"] = "993-NO-SUCH-PART-0001"
        self.assertIn("no public preview images", cat.gate_failures(r))

    def test_published_page_lists_only_passing_records_with_versions(self):
        fiches = [(BRACKET, passing(self.record)), (BRACKET, self.record)]
        page = cat.catalogue(fiches)
        self.assertEqual(page.count("993-ENG-BRACKET-0001]"), 1)
        self.assertIn("1 of 2 records published", page)
        self.assertIn("preview.png", page)

    def test_status_page_leads_every_entry_with_not_ready_to_print(self):
        page = cat.statut(cat.charger())
        rows = [l for l in page.splitlines() if l.startswith("| [")]
        self.assertTrue(rows)
        self.assertTrue(all("**Not ready to print.**" in l for l in rows))

    def test_current_records_publish_nothing_and_output_is_deterministic(self):
        first, second = cat.attendues(), cat.attendues()
        self.assertEqual(first, second)
        self.assertIn("No part has passed the publication gate", first[cat.OUT / "README.md"])


if __name__ == "__main__":
    unittest.main()
