import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.validate_catalog import ROOT, load_and_validate, validate_record


class CatalogueValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template_path = ROOT / "templates" / "part-record.json"
        cls.template = json.loads(template_path.read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_record(self.template), [])

    def test_schema_is_valid_json(self) -> None:
        schema_path = ROOT / "schemas" / "part.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_titanium_requires_process_controls(self) -> None:
        record = deepcopy(self.template)
        record["titanium"]["applicable"] = True
        record["titanium"]["hip_required"] = "to_be_determined"
        record["manufacturing"]["preferred_process"] = "LPBF"

        errors = validate_record(record)

        self.assertTrue(any("titanium.alloy" in error for error in errors))
        self.assertTrue(any("titanium.inspection" in error for error in errors))
        self.assertTrue(any("supplier_requirements" in error for error in errors))

    def test_prohibited_part_cannot_be_released(self) -> None:
        record = deepcopy(self.template)
        record["validation"]["status"] = "released"
        record["validation"]["reviewed_by"] = "reviewer"
        record["validation"]["evidence"] = ["parts/example/evidence/report.pdf"]
        record["manufacturing"]["supplier_requirements"] = ["Traceable material"]

        errors = validate_record(record)

        self.assertIn("validation.status: a prohibited part cannot be released", errors)

    def test_missing_master_file_is_rejected(self) -> None:
        record = deepcopy(self.template)
        record["geometry"]["master_format"] = "STEP"
        record["geometry"]["master_file"] = "parts/missing/source/part.step"

        errors = validate_record(record)

        self.assertTrue(any("referenced file does not exist" in error for error in errors))

    def test_template_file_loads_and_validates(self) -> None:
        path = Path(ROOT / "templates" / "part-record.json")
        self.assertEqual(load_and_validate(path), [])


if __name__ == "__main__":
    unittest.main()
