import json
import unittest
from copy import deepcopy

from scripts.validate_sources import ROOT, load_and_validate, validate_source


class SourceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "templates" / "source-record.json"
        cls.template = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_source(self.template), [])

    def test_source_schema_is_valid_json(self) -> None:
        path = ROOT / "schemas" / "source.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "3dprinting993 source record")

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

    def test_template_file_loads_and_validates(self) -> None:
        self.assertEqual(load_and_validate(self.path), [])


if __name__ == "__main__":
    unittest.main()
