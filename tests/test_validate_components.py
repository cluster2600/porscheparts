import json
import unittest
from copy import deepcopy

from scripts.validate_components import ROOT, validate_assembly, validate_component


class ComponentValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.front = json.loads(
            (ROOT / "catalog" / "components" / "comp-fuchs-37024.013.json").read_text(encoding="utf-8")
        )
        cls.rear = json.loads(
            (ROOT / "catalog" / "components" / "comp-fuchs-37026.013.json").read_text(encoding="utf-8")
        )

    def test_complete_components_are_valid(self) -> None:
        self.assertEqual(validate_component(self.front), [])
        self.assertEqual(validate_component(self.rear), [])

    def test_schemas_are_valid_json(self) -> None:
        for name in ("component.schema.json", "assembly.schema.json"):
            schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_unknown_mass_source_is_rejected(self) -> None:
        record = deepcopy(self.front)
        record["physical"]["mass"]["source_id"] = "UNKNOWN"
        self.assertTrue(any("mass.source_id" in error for error in validate_component(record)))

    def test_spatial_check_requires_accuracy(self) -> None:
        record = deepcopy(self.front)
        record["eligibility"]["spatial_check"] = True
        self.assertTrue(any("requires known interface accuracy" in error for error in validate_component(record)))

    def test_positioned_assembly_requires_transforms(self) -> None:
        assembly = json.loads(
            (ROOT / "catalog" / "assemblies" / "asm-993-fuchs-17-wheel-set.json").read_text(encoding="utf-8")
        )
        assembly["status"] = "positioned"
        known = {self.front["component_id"]: self.front, self.rear["component_id"]: self.rear}
        self.assertTrue(any("required for positioned" in error for error in validate_assembly(assembly, known)))

    def test_assembly_mass_must_match_component_sum(self) -> None:
        assembly = json.loads(
            (ROOT / "catalog" / "assemblies" / "asm-993-fuchs-17-wheel-set.json").read_text(encoding="utf-8")
        )
        assembly["physical_summary"]["mass_g"] = 1
        known = {self.front["component_id"]: self.front, self.rear["component_id"]: self.rear}
        self.assertTrue(any("does not match component sum" in error for error in validate_assembly(assembly, known)))


if __name__ == "__main__":
    unittest.main()
