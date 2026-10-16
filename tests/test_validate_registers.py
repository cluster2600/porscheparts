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

    def test_pet_range_must_span_the_skeleton_family(self) -> None:
        payload = deepcopy(self.classification)
        family = next(item for item in payload["families"] if item["family_id"] == "8xx")
        entry = next(item for item in family["qualified_sources"] if "pet_illustrations" in item)
        self.assertEqual(entry["pet_illustrations"]["last"], self.skeleton["8xx"]["illustrations"][-1])
        # An inner illustration is a member of the family but not its end.
        entry["pet_illustrations"]["last"] = "807-02"
        entry["location"] = entry["location"].replace("to 898-00R", "to 807-02")
        errors = self.classify(payload)
        self.assertTrue(any("807-02 is not the last illustration of 8xx" in error for error in errors))

    def test_stated_range_and_counts_must_match_the_skeleton(self) -> None:
        payload = deepcopy(self.classification)
        family = next(item for item in payload["families"] if item["family_id"] == "8xx")
        entry = next(item for item in family["qualified_sources"] if "pet_illustrations" in item)
        location = entry["location"]
        entry["location"] = location.replace("(85 illustrations", "(40 illustrations")
        errors = self.classify(payload)
        self.assertTrue(any("states 40 illustrations; the skeleton has 85" in error for error in errors))
        entry["location"] = location.replace("4553 references", "4552 references")
        errors = self.classify(payload)
        self.assertTrue(any("states 4552 references; the skeleton has 4553" in error for error in errors))
        entry["location"] = location.replace("to 898-00R", "to 807-02")
        errors = self.classify(payload)
        self.assertTrue(any("states illustrations 801-00 to 807-02" in error for error in errors))

    def test_record_observation_needs_a_date_the_record_states(self) -> None:
        payload = deepcopy(self.classification)
        entry = next(item for item in payload["sources"] if item["source_id"] == "SRC-CELETTE-MZX-964-993-JIGS")
        observation = next(item for item in entry["availability"] if item["basis"] == "record_text")
        self.assertEqual(self.classify(payload), [])
        observation["observed_on"] = "2026-08-30"
        errors = self.classify(payload)
        self.assertTrue(any("2026-08-30 is neither in the quote nor the access date" in error for error in errors))

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
