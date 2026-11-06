import json
import unittest
from copy import deepcopy

try:
    import jsonschema
except ImportError:  # the CI venv does not install it; the cross-check below is skipped there
    jsonschema = None

from scripts import validate_twins
from scripts.validate_twins import ROOT, load_and_validate, schema_errors, validate_twin

REGISTRY = ROOT / "catalog" / "twins"
SCHEMA = ROOT / "catalog" / "schemas" / "twin.schema.json"
IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def _load(name: str) -> dict:
    return json.loads((REGISTRY / name).read_text(encoding="utf-8"))


def invalid_cases() -> list[tuple[str, dict, str]]:
    """Mutations of real records that the contract must refuse, with the expected error text."""
    template = json.loads((ROOT / "catalog" / "templates" / "twin-record.json").read_text(encoding="utf-8"))
    hub = _load("twin-993-wheel-hub-interfaces-0001.json")
    fan = _load("twin-993-engine-cooling-fan-system-f0.json")
    floor = _load("twin-964-chassis-floor-0001.json")
    cases: list[tuple[str, dict, str]] = []

    def case(name: str, base: dict, edit, expected: str) -> None:
        record = deepcopy(base)
        edit(record)
        cases.append((name, record, expected))

    # 993 records.
    case("993 model year before 1993", hub, lambda r: r["vehicle"]["model_years"].update({"from": 1992}),
         "vehicle.model_years.from: expected at least 1993")
    case("generation outside the contract", hub, lambda r: r["vehicle"].update({"generation": "911"}),
         "vehicle.generation: expected one of")
    case("retired schema version", hub, lambda r: r.update({"schema_version": "1.0.0"}), "is retired")
    # Each F2 case withholds exactly one requirement from an otherwise complete upgrade.
    upgraded = upgraded_hub()
    case("993 fidelity raised to F2 without evidence", upgraded, lambda r: r["validation"].update({"evidence": []}),
         "validation.evidence: expected at least 1 items [rule: F2_interface or above")
    case("993 fidelity raised to F2 with an interface still missing data", upgraded,
         lambda r: r["interfaces"][2].update({"status": "missing_data"}), "interfaces[2].status: must not be \"missing_data\"")
    case("993 fidelity raised to F2 with unknown accuracy", upgraded,
         lambda r: r["components"][3].update({"accuracy_mm": None}), "components[3].accuracy_mm: expected number")
    case("993 fidelity raised to F2 with no vehicle transform", upgraded,
         lambda r: r["coordinate_system"].update({"vehicle_transform": None}),
         "coordinate_system.vehicle_transform: expected array")
    case("993 interface passed without evidence", template,
         lambda r: r["interfaces"][0].update({"status": "passed"}),
         "validation.evidence: expected at least 1 items [rule: an interface status other than missing_data")
    case("993 failed interface stripped of its evidence", fan,
         lambda r: r["validation"].update({"evidence": []}), "validation.evidence: expected at least 1 items")
    case("993 digitally checked at F1", template,
         lambda r: r["validation"].update({"status": "digitally_checked", "evidence": ["catalog/schemas/twin.schema.json"]}),
         "at least F2_interface")
    case("993 geometry ready with unknown accuracy", hub,
         lambda r: r["validation"].update({"status": "geometry_ready"}), "components[0].accuracy_mm: expected number")
    case("993 F4 without physical correlation", hub, lambda r: r.update({"fidelity": "F4_correlated"}),
         "validation.status: expected \"physically_correlated\"")
    case("zero accuracy instead of unknown", hub, lambda r: r["components"][0].update({"accuracy_mm": 0}),
         "components[0].accuracy_mm: expected more than 0")
    case("part_id omitted instead of null", hub, lambda r: r["components"][0].pop("part_id"),
         "components[0]: missing fields: part_id")
    case("contact interface joining three components", template,
         lambda r: (r["components"].append({"component_id": "THIRD", "role": "context", "part_id": None,
                                            "geometry_file": "", "accuracy_mm": None}),
                    r["interfaces"][0].update({"components": ["HOST", "CANDIDATE", "THIRD"]})),
         "interfaces[0].components: expected at most 2 items")
    case("interface referencing an unknown component", template,
         lambda r: r["interfaces"][0]["components"].__setitem__(1, "UNKNOWN"), "unknown component")
    case("duplicate interface id", hub, lambda r: r["interfaces"][1].update({"interface_id": r["interfaces"][0]["interface_id"]}),
         "duplicate")
    case("evidence path with the wrong letter case", hub,
         lambda r: r["validation"]["evidence"].__setitem__(0, r["validation"]["evidence"][0].replace("comp-fuchs-", "COMP-FUCHS-")),
         "referenced file does not exist")
    case("unknown coordinate-system field", hub, lambda r: r["coordinate_system"].update({"datum_guess": "x"}),
         "coordinate_system: unknown fields: datum_guess")
    case("build123d master that is not Python", hub, lambda r: r["geometry"].update({"master_file": "catalog/schemas/twin.schema.json"}),
         "geometry.master_file: does not match")

    # 964 record.
    case("964 with 993 model years", floor, lambda r: r["vehicle"]["model_years"].update({"to": 1995}),
         "vehicle.model_years.to: expected at most 1994")
    case("964 record relabelled 993", floor, lambda r: r["vehicle"].update({"generation": "993"}),
         "vehicle.model_years.from: expected at least 1993")
    case("964 twin id on a 993 vehicle", floor,
         lambda r: r["vehicle"].update({"generation": "993", "model_years": {"from": 1994, "to": 1994}}),
         "twin_id: names generation 964")
    case("964 model years reversed", floor, lambda r: r["vehicle"].update({"model_years": {"from": 1994, "to": 1989}}),
         "from must be <= to")
    case("964 partial interface promoted to passed without evidence", floor,
         lambda r: (r["interfaces"][0].update({"status": "passed"}), r["validation"].update({"evidence": [], "checks_passed": []})),
         "validation.evidence: expected at least 1 items")
    case("964 fidelity raised to F2 with unknown accuracy", floor, lambda r: r.update({"fidelity": "F2_interface"}),
         "components[0].accuracy_mm: expected number")
    case("964 digitally checked with partial interfaces", floor,
         lambda r: r["validation"].update({"status": "digitally_checked"}), "interfaces[0].status: expected one of")
    case("964 vehicle transform without provenance", floor, lambda r: r["coordinate_system"].pop("vehicle_transform_provenance"),
         "coordinate_system: missing fields: vehicle_transform_provenance")
    case("964 checks passed without evidence", floor,
         lambda r: (r["interfaces"][0].update({"status": "missing_data"}), r["interfaces"][1].update({"status": "missing_data"}),
                    r["validation"].update({"evidence": []})),
         "[rule: a recorded passed check needs evidence]")
    case("964 materials without a source", floor, lambda r: r["materials"].pop("source"), "materials: missing fields: source")
    case("964 materials with an undeclared field", floor, lambda r: r["materials"].update({"yield_mpa": 300}),
         "materials: unknown fields: yield_mpa")
    case("964 datum interface with one component", floor, lambda r: r["interfaces"][0].update({"components": ["FLOOR_PAN"]}),
         "interfaces[0].components: expected at least 2 items")
    case("964 interface kind outside the contract", floor, lambda r: r["interfaces"][1].update({"kind": "weld"}),
         "interfaces[1].kind: expected one of")
    return cases


def upgraded_hub() -> dict:
    """The wheel-hub record with synthetic values meeting every F2_interface requirement (test data only)."""
    record = _load("twin-993-wheel-hub-interfaces-0001.json")
    record["fidelity"] = "F2_interface"
    record["coordinate_system"].update({"vehicle_transform": IDENTITY, "vehicle_transform_provenance": "synthetic test value"})
    for component in record["components"]:
        component["accuracy_mm"] = 0.5
    for interface in record["interfaces"]:
        interface["status"] = "ready"
    return record


def checked_record() -> dict:
    """A synthetic record that meets every upgrade requirement, so the rules are not blanket bans."""
    record = json.loads((ROOT / "catalog" / "templates" / "twin-record.json").read_text(encoding="utf-8"))
    record["fidelity"] = "F2_interface"
    record["coordinate_system"].update({"vehicle_transform": IDENTITY, "vehicle_transform_provenance": "synthetic test value"})
    for component in record["components"]:
        component["accuracy_mm"] = 0.1
    record["interfaces"][0]["status"] = "passed"
    record["geometry"].update({"master_format": "build123d", "master_file": "scripts/validate_twins.py"})
    record["validation"].update({"status": "digitally_checked", "evidence": ["catalog/schemas/twin.schema.json"]})
    return record


class TwinValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads((ROOT / "catalog" / "templates" / "twin-record.json").read_text(encoding="utf-8"))
        cls.records = sorted(REGISTRY.glob("*.json"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_twin(self.template), [])

    def test_every_registry_record_meets_the_contract(self) -> None:
        self.assertGreaterEqual(len(self.records), 10)
        generations = set()
        for path in self.records:
            with self.subTest(record=path.name):
                self.assertEqual(load_and_validate(path), [])
                generations.add(json.loads(path.read_text(encoding="utf-8"))["vehicle"]["generation"])
        self.assertEqual(generations, {"993", "964"})

    def test_schema_uses_only_keywords_the_validator_executes(self) -> None:
        validate_twins.load_schema.cache_clear()
        schema = validate_twins.load_schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["schema_version"], {"const": "1.1.0"})
        with self.assertRaises(ValueError):
            validate_twins._check_keywords({"properties": {"x": {"oneOf": [{"type": "string"}]}}})
        with self.assertRaises(ValueError):
            validate_twins._check_keywords({"additionalProperties": {"type": "string"}})

    def test_invalid_records_are_refused_with_the_expected_reason(self) -> None:
        for name, record, expected in invalid_cases():
            with self.subTest(case=name):
                errors = validate_twin(record)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_a_fully_evidenced_upgrade_is_accepted(self) -> None:
        self.assertEqual(validate_twin(checked_record()), [])
        self.assertEqual(validate_twin(upgraded_hub()), [])

    def test_unknown_values_stay_unknown(self) -> None:
        record = deepcopy(self.template)
        for component in record["components"]:
            self.assertIsNone(component["accuracy_mm"])
            self.assertIsNone(component["part_id"])
        self.assertIsNone(record["coordinate_system"]["vehicle_transform"])
        floor = _load("twin-964-chassis-floor-0001.json")
        self.assertIsNone(floor["materials"]["grade"])
        self.assertEqual(validate_twin(record), [])

    def test_wheel_hub_twin_loads_and_references_four_step_proxies(self) -> None:
        path = REGISTRY / "twin-993-wheel-hub-interfaces-0001.json"
        self.assertEqual(load_and_validate(path), [])
        record = json.loads(path.read_text(encoding="utf-8"))
        step_files = record["geometry"]["derived_files"]
        self.assertEqual(len(step_files), 4)
        self.assertTrue(all((ROOT / item).is_file() for item in step_files))

    @unittest.skipIf(jsonschema is None, "jsonschema is not installed")
    def test_reference_implementation_agrees_with_the_stdlib_evaluator(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        validator_class = jsonschema.Draft202012Validator
        validator_class.check_schema(schema)
        validator = validator_class(schema)
        samples = [(path.name, json.loads(path.read_text(encoding="utf-8"))) for path in self.records]
        samples += [("template", self.template), ("checked", checked_record()), ("upgraded hub", upgraded_hub())]
        samples += [(name, record) for name, record, _ in invalid_cases()]
        for name, record in samples:
            with self.subTest(sample=name):
                reference = [error.message for error in validator.iter_errors(record)]
                self.assertEqual(bool(reference), bool(schema_errors(record)), reference)


if __name__ == "__main__":
    unittest.main()
