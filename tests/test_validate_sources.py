import json
import unittest
from copy import deepcopy

try:
    import jsonschema
except ImportError:  # the CI venv does not install it; the test below is skipped there
    jsonschema = None

from scripts import validate_sources
from scripts.validate_sources import ROOT, load_and_validate, validate_source


class SourceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "catalog" / "templates" / "source-record.json"
        cls.template = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_source(self.template), [])

    def test_source_schema_is_valid_json(self) -> None:
        path = ROOT / "catalog" / "schemas" / "source.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "porscheparts source record")

    def test_available_source_must_have_been_accessed(self) -> None:
        record = deepcopy(self.template)
        record["access"]["status"] = "available"

        errors = validate_source(record)

        self.assertIn("access.method: available requires an observed access method", errors)

    def test_browser_read_requires_date(self) -> None:
        record = deepcopy(self.template)
        record["access"]["status"] = "available"
        record["access"]["method"] = "browser_page_read"

        errors = validate_source(record)

        self.assertIn("access.accessed_on: required when the source was accessed", errors)

    def test_attribution_requirement_needs_text(self) -> None:
        record = deepcopy(self.template)
        record["rights"]["redistribution"] = "attribution_required"

        errors = validate_source(record)

        self.assertIn("rights.attribution: required when attribution is required", errors)

    def _archive_verified(self) -> dict:
        record = deepcopy(self.template)
        record["rights"] = {
            "license": "archive-verified-CC-BY-SA-3.0",
            "redistribution": "attribution_required",
            "attribution": "stagsimon",
            "archive_capture": {
                "status": "archive_verified",
                "capture_url": "https://web.archive.org/web/20170424143508/http://www.thingiverse.com:80/thing:2006970",
                "capture_timestamp": "20170424143508",
                "read_on": "2026-11-05",
                "license_as_read": "Creative Commons - Attribution - Share Alike",
                "author": "stagsimon",
            },
        }
        return record

    def test_archive_verified_record_is_valid(self) -> None:
        self.assertEqual(validate_source(self._archive_verified()), [])

    def test_archive_verified_licence_requires_a_capture(self) -> None:
        record = self._archive_verified()
        del record["rights"]["archive_capture"]
        self.assertIn("rights.archive_capture: required when the licence is archive-verified", validate_source(record))

    def test_capture_requires_archive_verified_licence(self) -> None:
        record = self._archive_verified()
        record["rights"]["license"] = "CC-BY-SA-3.0"
        self.assertIn("rights.license: an archive capture requires an 'archive-verified-' licence", validate_source(record))

    def test_capture_timestamp_must_match_url(self) -> None:
        record = self._archive_verified()
        record["rights"]["archive_capture"]["capture_timestamp"] = "20170424143509"
        self.assertIn("rights.archive_capture.capture_timestamp: must match the capture URL", validate_source(record))

    def test_capture_must_be_a_wayback_url(self) -> None:
        record = self._archive_verified()
        record["rights"]["archive_capture"]["capture_url"] = "https://www.thingiverse.com/thing:2006970"
        self.assertTrue(any(e.startswith("rights.archive_capture.capture_url") for e in validate_source(record)))

    def test_template_file_loads_and_validates(self) -> None:
        self.assertEqual(load_and_validate(self.path), [])

    def test_schema_enumerations_match_the_validator(self) -> None:
        """The validator is the enforced contract; the schema must not lag behind it."""
        schema = json.loads((ROOT / "catalog" / "schemas" / "source.schema.json").read_text(encoding="utf-8"))
        properties = schema["properties"]
        pairs = {
            "source_type": (properties["source_type"]["enum"], validate_sources.SOURCE_TYPES),
            "content_types": (properties["content_types"]["items"]["enum"], validate_sources.CONTENT_TYPES),
            "coverage.generation": (
                properties["coverage"]["properties"]["generation"]["enum"],
                validate_sources.GENERATIONS,
            ),
            "access.status": (properties["access"]["properties"]["status"]["enum"], validate_sources.ACCESS_STATUSES),
            "access.method": (properties["access"]["properties"]["method"]["enum"], validate_sources.ACCESS_METHODS),
            "rights.redistribution": (
                properties["rights"]["properties"]["redistribution"]["enum"],
                validate_sources.REDISTRIBUTION,
            ),
            "quality.dimensional_accuracy": (
                properties["quality"]["properties"]["dimensional_accuracy"]["enum"],
                validate_sources.DIMENSIONAL_ACCURACY,
            ),
            "quality.evidence_level": (
                properties["quality"]["properties"]["evidence_level"]["enum"],
                validate_sources.EVIDENCE_LEVELS,
            ),
        }
        for field, (schema_values, validator_values) in pairs.items():
            self.assertEqual(set(schema_values), set(validator_values), field)
        self.assertEqual(set(schema["required"]), validate_sources.REQUIRED_KEYS)
        offline = schema["allOf"][0]["then"]["properties"]["access"]["properties"]["method"]["enum"]
        self.assertEqual(set(offline), validate_sources.OFFLINE_METHODS)

    @unittest.skipIf(jsonschema is None, "jsonschema is not installed")
    def test_every_source_record_validates_against_the_schema(self) -> None:
        schema = json.loads((ROOT / "catalog" / "schemas" / "source.schema.json").read_text(encoding="utf-8"))
        validator_class = jsonschema.validators.validator_for(schema)
        validator_class.check_schema(schema)
        validator = validator_class(schema)
        paths = sorted((ROOT / "catalog" / "sources").glob("*.json"))
        self.assertTrue(paths)
        for path in [*paths, self.path]:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors = [f"{list(error.absolute_path)}: {error.message}" for error in validator.iter_errors(record)]
            self.assertEqual(errors, [], path.name)

    def test_every_coverage_key_in_use_is_declared_in_the_schema(self) -> None:
        schema = json.loads((ROOT / "catalog" / "schemas" / "source.schema.json").read_text(encoding="utf-8"))
        declared = set(schema["properties"]["coverage"]["properties"])
        for path in sorted((ROOT / "catalog" / "sources").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertLessEqual(set(record["coverage"]), declared, path.name)


if __name__ == "__main__":
    unittest.main()
