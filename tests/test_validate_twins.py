import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.validate_twins import ROOT, load_and_validate, validate_twin


class TwinValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads((ROOT / "templates" / "twin-record.json").read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_twin(self.template), [])

    def test_schema_is_valid_json(self) -> None:
        schema = json.loads((ROOT / "schemas" / "twin.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_checked_twin_requires_interface_fidelity(self) -> None:
        record = deepcopy(self.template)
        record["validation"]["status"] = "digitally_checked"
        record["validation"]["evidence"] = ["report.json"]
        errors = validate_twin(record)
        self.assertTrue(any("at least F2_interface" in error for error in errors))

    def test_interface_cannot_reference_unknown_component(self) -> None:
        record = deepcopy(self.template)
        record["interfaces"][0]["components"][1] = "UNKNOWN"
        errors = validate_twin(record)
        self.assertTrue(any("unknown component" in error for error in errors))

    def test_registry_record_loads(self) -> None:
        path = ROOT / "catalog" / "twins" / "twin-993-cabin-dashboard-switch-0001.json"
        self.assertEqual(load_and_validate(path), [])


if __name__ == "__main__":
    unittest.main()

