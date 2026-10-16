import json
import unittest
from copy import deepcopy

from scripts.validate_components import ROOT, validate_assembly, validate_component


def _load(*parts: str) -> dict:
    return json.loads((ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


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
            schema = json.loads((ROOT / "catalog" / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_unknown_mass_source_is_rejected(self) -> None:
        record = deepcopy(self.front)
        record["physical"]["mass"]["source_id"] = "UNKNOWN"
        self.assertTrue(any("mass.source_id" in error for error in validate_component(record)))

    def test_registry_link_must_resolve_to_the_same_document(self) -> None:
        record = deepcopy(self.front)
        record["sources"][0]["registry_source_id"] = "SRC-DOES-NOT-EXIST"
        self.assertTrue(any("is not a registered source" in error for error in validate_component(record)))
        record["sources"][0]["registry_source_id"] = "SRC-FUCHS-993-APPLICATION-LEAFLET-2020"
        self.assertTrue(any("different URL" in error for error in validate_component(record)))

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


class MountingRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.known = {}
        for path in sorted((ROOT / "catalog" / "components").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            cls.known[record["component_id"]] = record
        cls.wheels_17 = _load("catalog", "assemblies", "asm-993-fuchs-17-wheel-set.json")

    def _errors(self, assembly: dict, **registries) -> list[str]:
        return validate_assembly(assembly, self.known, **registries)

    def test_all_component_and_assembly_records_are_valid(self) -> None:
        for component_id, record in self.known.items():
            self.assertEqual(validate_component(record), [], component_id)
        for path in sorted((ROOT / "catalog" / "assemblies").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(self._errors(record), [], path.name)

    def test_wheel_sets_record_the_sourced_hub_fastening(self) -> None:
        for name in ("asm-993-fuchs-17-wheel-set.json", "asm-993-fuchs-18-wheel-set.json"):
            relations = _load("catalog", "assemblies", name)["mounting_relations"]
            self.assertEqual({item["instance_ids"][0] for item in relations}, {"FRONT_WHEELS", "REAR_WHEELS"})
            for relation in relations:
                self.assertEqual(relation["fastener"]["thread"], "M14x1.5")
                self.assertEqual(relation["fastener"]["count_per_unit"], 5)
                self.assertEqual(relation["tightening_torque"]["value"], 130)
                self.assertEqual(relation["tightening_torque"]["source_id"], "SRC-PORSCHE-WORKSHOP-MANUAL-993")

    def test_relation_instance_must_exist(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["instance_ids"] = ["SPARE_WHEEL"]
        self.assertTrue(any("unknown instance SPARE_WHEEL" in error for error in self._errors(assembly)))

    def test_fastener_count_must_equal_the_sourced_component_parameter(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["fastener"]["count_per_unit"] = 4
        self.assertTrue(any("is not the BOLT_COUNT count" in error for error in self._errors(assembly)))

    def test_fastener_count_needs_a_parameter(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["fastener"]["count_parameter_id"] = None
        self.assertTrue(any("must name the component parameter" in error for error in self._errors(assembly)))

    def test_unknown_count_and_torque_stay_null(self) -> None:
        assembly = deepcopy(self.wheels_17)
        relation = assembly["mounting_relations"][0]
        relation["fastener"]["count_per_unit"] = None
        relation["fastener"]["count_parameter_id"] = None
        relation["tightening_torque"] = None
        self.assertEqual(self._errors(assembly), [])

    def test_torque_must_match_the_cited_manual_value(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["tightening_torque"]["value"] = 120
        self.assertTrue(any("does not state 120 Nm" in error for error in self._errors(assembly)))

    def test_torque_thread_must_match_the_cited_manual_value(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["fastener"]["thread"] = "M12x1.5"
        self.assertTrue(any("is for thread" in error for error in self._errors(assembly)))

    def test_torque_rejects_unknown_manual_value(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["tightening_torque"]["measurement_refs"][0]["value_id"] = "MNL-TORQUE-9999"
        self.assertTrue(any("not in MEAS-MANUAL-993-ALL" in error for error in self._errors(assembly)))

    def test_torque_rejects_unreviewed_ocr(self) -> None:
        measurements = {
            "MEAS-FAKE": {
                "V1": {
                    "record_type": "torque_spec",
                    "unit": "Nm",
                    "numeric_values": [130.0],
                    "extraction_status": "ocr_unreviewed",
                    "source_id": "SRC-PORSCHE-WORKSHOP-MANUAL-993",
                    "details": {"thread": "M 14x 1.5"},
                }
            }
        }
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["tightening_torque"]["measurement_refs"] = [
            {"measurement_id": "MEAS-FAKE", "value_id": "V1"}
        ]
        errors = self._errors(assembly, measurements=measurements)
        self.assertTrue(any("ocr_unreviewed is not admissible" in error for error in errors))

    def test_relation_sources_must_be_cited_and_registered(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["fastener"]["source_id"] = "FUCHS-37026-APPROVAL"
        self.assertTrue(any("not cited in source_ids" in error for error in self._errors(assembly)))
        assembly = deepcopy(self.wheels_17)
        assembly["relationship_sources"][-1]["url"] = "https://example.org/manual"
        self.assertTrue(any("URL differs from the catalog/sources record" in error for error in self._errors(assembly)))
        self.assertTrue(any("is not a record in catalog/sources" in error for error in self._errors(assembly, sources={})))

    def test_twin_interface_link_must_resolve(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["counterpart"]["twin_interfaces"][0]["interface_id"] = "IF_NOWHERE"
        self.assertTrue(any("IF_NOWHERE is not an interface" in error for error in self._errors(assembly)))

    def test_component_counterpart_must_exist(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["counterpart"] = {"kind": "component", "ref": "COMP-UNKNOWN"}
        self.assertTrue(any("counterpart.ref: unknown component" in error for error in self._errors(assembly)))

    def test_torque_without_a_measurement_value_is_rejected(self) -> None:
        # A typed torque with no cited measurement value must not pass, whatever its value or source.
        for value, source_id in ((999, "SRC-PORSCHE-WORKSHOP-MANUAL-993"), (50, "FUCHS-37024-APPROVAL")):
            assembly = deepcopy(self.wheels_17)
            torque = assembly["mounting_relations"][0]["tightening_torque"]
            torque.update({"value": value, "source_id": source_id, "measurement_refs": [], "corroborated_by": []})
            with self.subTest(value=value, source_id=source_id):
                self.assertTrue(
                    any("must cite at least one measurement value" in error for error in self._errors(assembly))
                )

    def test_torque_schema_requires_a_measurement_value(self) -> None:
        schema = _load("catalog", "schemas", "assembly.schema.json")
        relation = schema["properties"]["mounting_relations"]["items"]["properties"]
        self.assertEqual(relation["tightening_torque"]["properties"]["measurement_refs"]["minItems"], 1)
        self.assertTrue(relation["instance_ids"]["uniqueItems"])

    def test_twin_interface_link_must_match_the_axle_and_size(self) -> None:
        for interface_id in ("IF_REAR_18_HUB", "IF_REAR_17_HUB", "IF_FRONT_18_HUB"):
            assembly = deepcopy(self.wheels_17)
            assembly["mounting_relations"][0]["counterpart"]["twin_interfaces"][0]["interface_id"] = interface_id
            with self.subTest(interface_id=interface_id):
                self.assertTrue(
                    any(
                        f"{interface_id} does not involve the geometry of COMP-FUCHS-37024.013" in error
                        for error in self._errors(assembly)
                    )
                )

    def test_twin_interface_link_must_be_a_fastener_interface(self) -> None:
        twins = {
            "TWIN-993-WHEEL-HUB-INTERFACES-0001": {
                "IF_FRONT_17_HUB": {
                    "kind": "contact",
                    "geometry_files": {"components/wheels/fuchs/derived/37024.013-interface-proxy.step"},
                },
                "IF_REAR_17_HUB": {
                    "kind": "fastener",
                    "geometry_files": {"components/wheels/fuchs/derived/37026.013-interface-proxy.step"},
                },
            }
        }
        errors = self._errors(deepcopy(self.wheels_17), twins=twins)
        self.assertEqual(
            errors,
            ["mounting_relations[0].counterpart.twin_interfaces: IF_FRONT_17_HUB is a contact interface, not a fastener interface"],
        )

    def test_duplicate_instance_in_a_relation_is_rejected(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relations"][0]["instance_ids"] = ["FRONT_WHEELS", "FRONT_WHEELS"]
        self.assertIn("mounting_relations[0].instance_ids: duplicate instance FRONT_WHEELS", self._errors(assembly))

    def test_unhashable_ids_are_reported_not_raised(self) -> None:
        mutations = {
            "instance_ids": lambda record: record["mounting_relations"][0].update(instance_ids=[["FRONT_WHEELS"]]),
            "source_ids": lambda record: record["mounting_relations"][0]["source_ids"].append({"id": "X"}),
            "counterpart": lambda record: record["mounting_relations"][0].update(
                counterpart={"kind": "component", "ref": ["COMP-FUCHS-37024.013"]}
            ),
            "twin_id": lambda record: record["mounting_relations"][0]["counterpart"]["twin_interfaces"][0].update(
                twin_id=["TWIN-993-WHEEL-HUB-INTERFACES-0001"]
            ),
            "interface_id": lambda record: record["mounting_relations"][0]["counterpart"]["twin_interfaces"][0].update(
                interface_id={"id": "IF_FRONT_17_HUB"}
            ),
            "measurement_id": lambda record: record["mounting_relations"][0]["tightening_torque"]["measurement_refs"][0].update(
                measurement_id=["MEAS-MANUAL-993-ALL"]
            ),
            "value_id": lambda record: record["mounting_relations"][0]["tightening_torque"]["measurement_refs"][0].update(
                value_id=["MNL-TORQUE-0134"]
            ),
            "component_id": lambda record: record["instances"][0].update(component_id=["COMP-FUCHS-37024.013"]),
            "relationship_source_id": lambda record: record["instances"][0].update(relationship_source_id=["X"]),
            "relationship_sources": lambda record: record["relationship_sources"][0].update(source_id=["X"]),
            "status": lambda record: record.update(status=["logical"]),
        }
        for name, mutate in mutations.items():
            assembly = deepcopy(self.wheels_17)
            mutate(assembly)
            with self.subTest(field=name):
                self.assertTrue(self._errors(assembly))
        component = deepcopy(self.known["COMP-FUCHS-37024.013"])
        component["physical"]["mass"]["source_id"] = ["FUCHS-PRODUCT"]
        component["kind"] = ["aftermarket"]
        errors = validate_component(component)
        self.assertIn("physical.mass.source_id: unknown source", errors)
        self.assertIn("kind: unknown", errors)

    def test_record_local_source_url_must_match_the_component_source(self) -> None:
        assembly = deepcopy(self.wheels_17)
        index = next(
            position
            for position, source in enumerate(assembly["relationship_sources"])
            if source["source_id"] == "FUCHS-37024-APPROVAL"
        )
        assembly["relationship_sources"][index]["url"] = "https://www.fuchsfelge.com/other.pdf"
        self.assertIn(
            f"relationship_sources[{index}].source_id: URL differs from the FUCHS-37024-APPROVAL source of COMP-FUCHS-37024.013",
            self._errors(assembly),
        )

    def test_unknown_assembly_field_is_rejected(self) -> None:
        assembly = deepcopy(self.wheels_17)
        assembly["mounting_relation"] = []
        self.assertTrue(any("unknown fields: mounting_relation" in error for error in self._errors(assembly)))


class ConnectingRodInventoryTests(unittest.TestCase):
    def test_rod_is_inventory_only_with_its_process_gap_recorded(self) -> None:
        rod = _load("catalog", "components", "comp-pauter-993-230-580-1270f.json")
        self.assertEqual(validate_component(rod), [])
        self.assertEqual(rod["geometry"]["master_format"], "none")
        self.assertEqual(rod["geometry"]["derived_files"], [])
        self.assertFalse(rod["eligibility"]["spatial_check"])
        self.assertIsNone(rod["physical"]["mass"]["tolerance_g"])
        self.assertIn("not declared", rod["physical"]["material"]["process"])
        self.assertTrue(any("MEZGER-P010" in item for item in rod["geometry"]["limitations"]))
        # Position numbers are a record convention, not the Porsche cylinder numbering.
        self.assertEqual(rod["vehicle"]["positions"], [f"position_{index}" for index in range(1, 7)])

    def test_rod_set_has_six_instances_and_no_unsourced_relation(self) -> None:
        rod = _load("catalog", "components", "comp-pauter-993-230-580-1270f.json")
        assembly = _load("catalog", "assemblies", "asm-993-pauter-rod-set.json")
        self.assertEqual(validate_assembly(assembly, {rod["component_id"]: rod}), [])
        self.assertEqual(sum(item["quantity"] for item in assembly["instances"]), 6)
        self.assertEqual(assembly["physical_summary"]["mass_g"], 6 * 535)
        self.assertNotIn("mounting_relations", assembly)

    def test_registry_source_id_must_resolve(self) -> None:
        rod = _load("catalog", "components", "comp-pauter-993-230-580-1270f.json")
        self.assertTrue(any("is not a record in catalog/sources" in error for error in validate_component(rod, sources={})))


if __name__ == "__main__":
    unittest.main()
