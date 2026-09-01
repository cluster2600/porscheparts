import json
import unittest
from copy import deepcopy
from datetime import date, timedelta

from scripts.validate_measurements import ROOT, load_and_validate, validate_measurement


class MeasurementValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "templates" / "measurement-record.json"
        cls.template = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_measurement(self.template), [])

    def test_measurement_schema_is_valid_json(self) -> None:
        path = ROOT / "schemas" / "measurement.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "3dprinting993 measurement record")

    def test_value_must_match_its_samples(self) -> None:
        record = deepcopy(self.template)
        record["readings"][0]["value"] = 11.5

        errors = validate_measurement(record)

        self.assertTrue(any("does not match the mean of its samples" in error for error in errors))

    def test_uncertainty_cannot_beat_instrument_resolution(self) -> None:
        record = deepcopy(self.template)
        record["readings"][0]["uncertainty"] = 0.001

        errors = validate_measurement(record)

        self.assertTrue(any("finer than half the instrument resolution" in error for error in errors))

    def test_streamed_reading_requires_a_timestamp(self) -> None:
        record = deepcopy(self.template)
        record["instruments"][0]["interface"] = "serial"
        record["readings"][0]["capture_mode"] = "instrument_stream"

        errors = validate_measurement(record)

        self.assertIn(
            "readings[0].captured_at: required when capture_mode is instrument_stream",
            errors,
        )

    def test_manual_instrument_cannot_stream(self) -> None:
        record = deepcopy(self.template)
        record["readings"][0]["capture_mode"] = "instrument_stream"
        record["readings"][0]["captured_at"] = "2026-08-28T10:00:00"

        errors = validate_measurement(record)

        self.assertIn(
            "readings[0].capture_mode: instrument CAL-01 has a manual interface",
            errors,
        )

    def test_reading_must_reference_a_declared_instrument(self) -> None:
        record = deepcopy(self.template)
        record["readings"][0]["instrument_id"] = "MISSING"

        errors = validate_measurement(record)

        self.assertTrue(any("no instrument declares" in error for error in errors))

    def test_evidence_level_a_requires_repeats_and_calibration(self) -> None:
        record = deepcopy(self.template)
        record["evidence"]["level"] = "A"
        record["readings"][0]["samples"] = [10.02, 10.02]
        record["readings"][0]["value"] = 10.02

        errors = validate_measurement(record)

        self.assertTrue(any("requires at least three samples" in error for error in errors))
        self.assertTrue(any("requires a known calibration state" in error for error in errors))

    def test_calibrated_instrument_needs_a_check_date(self) -> None:
        record = deepcopy(self.template)
        record["instruments"][0]["calibration"]["status"] = "calibrated"

        errors = validate_measurement(record)

        self.assertIn(
            "instruments[0].calibration.checked_on: required when the instrument is declared calibrated",
            errors,
        )

    def test_session_cannot_be_dated_in_the_future(self) -> None:
        record = deepcopy(self.template)
        record["session"]["performed_on"] = (date.today() + timedelta(days=1)).isoformat()

        errors = validate_measurement(record)

        self.assertIn("session.performed_on: date is in the future", errors)

    def test_duplicate_dimension_identifiers_are_rejected(self) -> None:
        record = deepcopy(self.template)
        record["readings"].append(deepcopy(record["readings"][0]))

        errors = validate_measurement(record)

        self.assertTrue(any("duplicate identifier D01" in error for error in errors))

    def test_template_file_loads_from_disk(self) -> None:
        self.assertEqual(load_and_validate(self.path), [])

    def test_manual_specification_record_is_valid(self) -> None:
        path = ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json"
        record = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(record["record_kind"], "documented_specification")
        self.assertEqual(len(record["declared_values"]), 2496)
        self.assertEqual(load_and_validate(path), [])


if __name__ == "__main__":
    unittest.main()
