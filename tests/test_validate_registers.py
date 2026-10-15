import json
import unittest
from copy import deepcopy
from datetime import date

from scripts.validate_registers import (
    CLASSIFICATION,
    CONTRADICTIONS,
    load_manual_values,
    load_skeleton,
    load_sources,
    validate_classification,
    validate_contradictions,
)


class RegisterValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = load_sources()
        cls.manual = load_manual_values()
        cls.skeleton = load_skeleton()
        cls.contradictions = json.loads(CONTRADICTIONS.read_text(encoding="utf-8"))
        cls.classification = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))

    def classify(self, payload: dict) -> list[str]:
        return validate_classification(
            payload, self.sources, self.manual, self.skeleton, today=date(2026, 10, 15)
        )

    def test_shipped_registers_are_valid(self) -> None:
        self.assertEqual(validate_contradictions(self.contradictions, self.sources), [])
        self.assertEqual(self.classify(self.classification), [])

    def test_unregistered_source_in_a_contradiction_is_rejected(self) -> None:
        payload = deepcopy(self.contradictions)
        payload["entries"][0]["values"][0]["source_id"] = "SRC-DOES-NOT-EXIST"
        errors = validate_contradictions(payload, self.sources)
        self.assertTrue(any("is not a registered source" in error for error in errors))

    def test_open_contradiction_needs_a_next_step(self) -> None:
        payload = deepcopy(self.contradictions)
        entry = next(item for item in payload["entries"] if item["status"] == "open")
        entry.pop("next_step")
        errors = validate_contradictions(payload, self.sources)
        self.assertTrue(any("next_step" in error for error in errors))

    def test_unsourced_value_must_point_to_a_file(self) -> None:
        payload = deepcopy(self.contradictions)
        value = payload["entries"][0]["values"][0]
        value["source_id"] = None
        value.pop("repository_path", None)
        errors = validate_contradictions(payload, self.sources)
        self.assertTrue(any("repository_path" in error for error in errors))

    def test_every_skeleton_family_needs_a_qualified_source(self) -> None:
        payload = deepcopy(self.classification)
        payload["families"] = [item for item in payload["families"] if item["family_id"] != "7xx"]
        errors = self.classify(payload)
        self.assertIn("families: system 7xx of the assembly skeleton has no qualified source", errors)

    def test_community_source_does_not_qualify_a_family(self) -> None:
        payload = deepcopy(self.classification)
        family = next(item for item in payload["families"] if item["family_id"] == "7xx")
        family["qualified_sources"] = [
            {
                "source_id": "SRC-PFF-993-BRAKE-LIGHT-SWITCH-TRAVEL",
                "role": "service_specification",
                "location": "forum reply",
            }
        ]
        errors = self.classify(payload)
        self.assertTrue(any("not official or manufacturer" in error for error in errors))

    def test_manual_value_must_belong_to_the_cited_source(self) -> None:
        payload = deepcopy(self.classification)
        family = next(item for item in payload["families"] if item["family_id"] == "3xx")
        family["qualified_sources"][1]["value_ids"].append("MNL-964BC-0020")
        errors = self.classify(payload)
        self.assertTrue(any("MNL-964BC-0020 is not in MEAS-MANUAL-993-ALL" in error for error in errors))

    def test_model_year_quote_must_be_verbatim(self) -> None:
        payload = deepcopy(self.classification)
        entry = next(item for item in payload["sources"] if "model_years" in item)
        entry["model_years"]["quote"] = "1990-2001"
        errors = self.classify(payload)
        self.assertTrue(any("not found verbatim" in error for error in errors))

    def test_absence_is_never_a_discontinuation(self) -> None:
        payload = deepcopy(self.classification)
        entry = next(item for item in payload["sources"] if "availability" in item)
        entry["availability"][0]["status"] = "discontinued_per_publisher"
        errors = self.classify(payload)
        self.assertTrue(any("publisher's own statement" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
