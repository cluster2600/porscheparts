import json
import unittest
from copy import deepcopy

from scripts.validate_specifications import ROOT, load_and_validate, validate_specification_set


class DocumentarySpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.technical_path = ROOT / "catalog" / "specifications" / "porschefanatics-993-technical-data.json"
        cls.torque_path = ROOT / "catalog" / "specifications" / "porschefanatics-993-torques.json"

    def test_schema_is_valid_json(self) -> None:
        schema = json.loads((ROOT / "schemas" / "documentary-specification.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "3dprinting993 documentary specification set")

    def test_complete_porschefanatics_snapshot_is_present(self) -> None:
        technical = json.loads(self.technical_path.read_text(encoding="utf-8"))
        torques = json.loads(self.torque_path.read_text(encoding="utf-8"))
        self.assertEqual(len(technical["records"]), 111)
        self.assertEqual(len(torques["records"]), 195)
        self.assertEqual(load_and_validate(self.technical_path), [])
        self.assertEqual(load_and_validate(self.torque_path), [])

    def test_ocr_record_cannot_be_promoted_automatically(self) -> None:
        record_set = json.loads(self.technical_path.read_text(encoding="utf-8"))
        changed = deepcopy(record_set)
        changed["records"][0]["verification_status"] = "verified"
        errors = validate_specification_set(changed)
        self.assertTrue(any("cannot be promoted automatically" in error for error in errors))

    def test_torque_requires_torque_or_angle(self) -> None:
        record_set = json.loads(self.torque_path.read_text(encoding="utf-8"))
        changed = deepcopy(record_set)
        changed["records"][0]["torque_nm"] = None
        changed["records"][0]["angle_degrees"] = None
        errors = validate_specification_set(changed)
        self.assertTrue(any("expected a torque or an angle" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

