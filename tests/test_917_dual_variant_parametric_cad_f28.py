import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_dual_variant_parametric_cad_contract_f28.py"
CONTRACT = ROOT / "twins/reference-917-engine/dual-variant-parametric-cad-contract-f28.json"

# Litteraux de test independants des constantes du generateur. Ils rendent une
# rebasis silencieuse visible dans la revue de code.
EXPECTED_UPSTREAM_SHA256 = {
    "classical_solver_facts_f13": "add18d3c64ad481d20052fd6b6a3b0db773bb67ad534831b23dd11c996d0a08b",
    "kinematic_interfaces_f16": "ec5e56cdd750071462e00dcec978182916ee4c266435bfea0720dea2fda2f2e2",
    "manufacturing_routing_f19": "f9fc00c4f51840bb5781ffc21078f7e30febecd6bef202e32e882f0da3130d6f",
    "dual_variant_functional_readiness_f24": "27fd052a45e051f75836e4116255a655f760b1d36c600a14778eb69fed0a7d5b",
    "physical_metrology_campaign_f27": "9d2157383f50a0e3b4db76c49b9ef8ad9ab2aec56ff60e95efe388ea4d90a822",
    "variant_visualization_f10": "dfb6ee25f367c934b11ff020e34d9d77296d2b5a535030a73221696af7c7a640",
    "valvetrain_flow_f20": "4f5e1eee41711d9012f703211fa44de053dd0f266fc7f41ee001b2273c12136c",
    "parametric_cad_f22": "5086429d0514d7206083bda450bd271b74406f249b58f60aa365c16f1f6b2144",
}
EXPECTED_F19_ROUTES = {
    "crankcase_half": "conventional_candidate",
    "main_bearing": "purchased_non_printable",
    "crankshaft": "conventional_candidate",
    "central_output_gear": "conventional_candidate",
    "output_shaft": "unresolved",
    "connecting_rod": "conventional_candidate",
    "piston": "unresolved",
    "piston_pin": "purchased_non_printable",
    "piston_ring": "purchased_non_printable",
    "individual_cylinder": "conventional_candidate",
    "individual_head": "metal_additive_candidate",
    "intake_valve": "purchased_non_printable",
    "exhaust_valve": "purchased_non_printable",
    "valve_spring": "purchased_non_printable",
    "bucket_tappet": "purchased_non_printable",
    "camshaft": "unresolved",
    "cam_carrier": "conventional_candidate",
    "cam_drive_gear": "conventional_candidate",
    "cooling_blower": "conventional_candidate",
    "blower_shroud": "metal_additive_candidate",
    "intake_trumpet": "metal_additive_candidate",
    "injector": "purchased_non_printable",
    "spark_plug": "purchased_non_printable",
    "distributor": "purchased_non_printable",
    "pressure_oil_pump": "purchased_non_printable",
    "scavenge_oil_pump": "purchased_non_printable",
    "exhaust_primary": "conventional_candidate",
    "exhaust_collector": "conventional_candidate",
    "alternator": "purchased_non_printable",
    "turbocharger": "purchased_non_printable",
    "charge_plenum": "metal_additive_candidate",
}
EXPECTED_RESTORED_FAMILIES = {
    "output_shaft",
    "distributor",
    "pressure_oil_pump",
    "scavenge_oil_pump",
    "alternator",
    "turbocharger",
}
EXPECTED_F16_GRAPH = {
    "crankcase_supports_crankshaft": ("crankcase_half", "main_bearing", "crankshaft", 8, "revolute_bearing_candidate"),
    "crankshaft_to_connecting_rod": ("crankshaft", None, "connecting_rod", 12, "revolute_candidate"),
    "connecting_rod_to_piston_pin": ("connecting_rod", None, "piston_pin", 12, "revolute_candidate"),
    "piston_pin_to_piston": ("piston_pin", None, "piston", 12, "fit_definition_unknown"),
    "piston_to_cylinder": ("piston", None, "individual_cylinder", 12, "prismatic_candidate"),
    "cylinder_to_crankcase": ("individual_cylinder", None, "crankcase_half", 12, "fixed_interface_candidate"),
}
EXPECTED_TURBO_RELATIONS = {
    # source family, source boundary, via, target, cardinality, type, upstream ref
    "turbocharger_to_chra_via_compressor_housing": ("turbocharger", None, "turbo_compressor_housing", "turbo_chra", 2, "assembly_decomposition_only", "family_route_registry/turbocharger"),
    "turbocharger_to_chra_via_turbine_housing": ("turbocharger", None, "turbo_turbine_housing", "turbo_chra", 2, "assembly_decomposition_only", "family_route_registry/turbocharger"),
    "collector_to_turbine_inlet_duct": ("exhaust_collector", None, None, "turbine_inlet_duct_assembly", 2, "compressible_exhaust", "f8_interface_route_registry/ducts/collector_to_turbo_hot_side"),
    "turbine_inlet_duct_to_turbine_housing": ("turbine_inlet_duct_assembly", None, "duct_body", "turbo_turbine_housing", 2, "compressible_exhaust", "f8_interface_route_registry/ducts/collector_to_turbo_hot_side"),
    "turbine_housing_to_chra": ("turbo_turbine_housing", None, None, "turbo_chra", 2, "turbo_rotor_support", "f8_interface_route_registry/mechanical_connections/turbo_rotor_support"),
    "chra_to_compressor_housing": ("turbo_chra", None, None, "turbo_compressor_housing", 2, "turbo_rotor_support", "f8_interface_route_registry/mechanical_connections/turbo_rotor_support"),
    "ambient_to_two_compressor_inlets": (None, "bench_intake_ambient", "compressor_duct_assembly", "turbo_compressor_housing", 2, "compressible_intake", "f8_interface_route_registry/ducts/ambient_to_turbo_compressor_inlet"),
    "compressor_housing_to_compressor_duct": ("turbo_compressor_housing", None, "duct_body", "compressor_duct_assembly", 2, "compressible_intake", "f8_interface_route_registry/ducts/turbo_to_charge_plenum"),
    "compressor_duct_to_charge_plenum": ("compressor_duct_assembly", None, None, "charge_plenum", 2, "compressible_intake", "f8_interface_route_registry/ducts/turbo_to_charge_plenum"),
    "charge_plenum_to_intake_distribution": ("charge_plenum", None, None, "intake_duct_assembly", 12, "compressible_intake", "f8_interface_route_registry/ducts/charge_plenum_to_intake_trumpets"),
    "turbine_housing_to_exhaust_duct": ("turbo_turbine_housing", None, None, "exhaust_duct_assembly", 2, "compressible_exhaust", "f8_interface_route_registry/ducts/turbo_turbine_outlet_to_bench_extraction"),
    "wastegate_inlet_bypass": ("turbine_inlet_duct_assembly", None, None, "wastegate", 2, "exhaust_bypass_control_unknown", "family_route_registry/turbocharger"),
    "wastegate_outlet_bypass": ("wastegate", None, None, "exhaust_duct_assembly", 2, "exhaust_bypass_control_unknown", "family_route_registry/turbocharger"),
    "turbo_pressure_oil_feed": ("lubrication_duct_assembly", None, None, "turbo_chra", 2, "oil_line", "f8_interface_route_registry/ducts/turbo_pressure_oil_feed"),
    "turbo_scavenge_oil_drain": ("turbo_chra", None, None, "lubrication_duct_assembly", 2, "oil_line", "f8_interface_route_registry/ducts/turbo_scavenge_oil_drain"),
}
EXPECTED_CONTRACT_SHA256 = "0949753839ff018d95b9daa220ee906525978f429b9adcd4da15b6960bb99556"


def load_module():
    specification = importlib.util.spec_from_file_location("build_f28", SCRIPT)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_false_tree(value):
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return bool(value) and all(strict_false_tree(item) for item in value.values())
    if isinstance(value, list):
        return bool(value) and all(strict_false_tree(item) for item in value)
    return False


class DualVariantParametricCadF28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _loaded_upstreams(self):
        return {
            record["id"]: json.loads((ROOT / record["path"]).read_text(encoding="utf-8"))
            for record in self.contract["upstream_contracts"]
        }

    def _copy_upstreams(self, root):
        for record in self.contract["upstream_contracts"]:
            source = ROOT / record["path"]
            target = root / record["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_tracked_contract_is_deterministic_zero_geometry_and_digest_locked(self):
        self.assertEqual(self.module.build_contract(ROOT), self.contract)
        report = self.module.evaluate(ROOT, self.contract)
        self.assertEqual(report["report_status"], "passed", report["contract_errors"])
        self.assertEqual(report["variant_count"], 2)
        self.assertEqual(report["family_count"], 54)
        self.assertEqual(report["f19_source_family_count"], 31)
        self.assertEqual(report["turbo_semantic_instance_count"], 2)
        self.assertEqual(report["geometry_artifact_count"], 0)
        self.assertTrue(strict_false_tree(report["release"]))
        self.assertEqual(file_sha256(CONTRACT), EXPECTED_CONTRACT_SHA256)

    def test_canonical_upstream_digests_are_literal_and_view_is_immutable(self):
        records = {item["id"]: item for item in self.contract["upstream_contracts"]}
        self.assertEqual(set(records), set(EXPECTED_UPSTREAM_SHA256))
        for source_id, digest in EXPECTED_UPSTREAM_SHA256.items():
            self.assertEqual(records[source_id]["sha256"], digest)
            self.assertEqual(file_sha256(ROOT / records[source_id]["path"]), digest)
            self.assertFalse(records[source_id]["geometry_payload_transfer_authorized"])
            self.assertFalse(records[source_id]["manufacturing_authority"])
        with self.assertRaises(TypeError):
            self.module.UPSTREAMS["manufacturing_routing_f19"]["sha256"] = "0" * 64

    def test_f19_all_31_families_routes_and_extensions_are_traceable(self):
        coverage = self.contract["f19_coverage"]
        self.assertEqual(coverage["source_family_count"], 31)
        self.assertEqual(coverage["missing_source_family_refs"], [])
        self.assertEqual(set(coverage["covered_source_family_refs"]), set(EXPECTED_F19_ROUTES))
        records = {item["id"]: item for item in self.contract["component_family_registry"]}
        self.assertTrue(EXPECTED_RESTORED_FAMILIES <= set(records))
        for family_id, route in EXPECTED_F19_ROUTES.items():
            self.assertEqual(records[family_id]["route_class"], route)
            crosswalk = records[family_id]["source_crosswalk"]
            self.assertEqual(crosswalk["registry"], "family_route_registry")
            self.assertEqual(crosswalk["source_ids"], [family_id])
            self.assertEqual(crosswalk["relationship"], "exact_f19_family")
        for item in records.values():
            crosswalk = item["source_crosswalk"]
            self.assertTrue(crosswalk["registry"])
            self.assertTrue(crosswalk["source_ids"])
            self.assertNotIn("or_f19_taxonomy_extension", json.dumps(crosswalk))
        self.assertEqual(records["intake_trumpet"]["variant_scope"], "common")

    def test_variant_sets_are_exact_and_intake_trumpet_is_in_both(self):
        by_id = {item["variant_id"]: item for item in self.contract["variant_contracts"]}
        self.assertEqual(set(by_id), {"type_912_5_0_na", "917_30_1973_turbo_5374"})
        for record in by_id.values():
            self.assertIn("intake_trumpet", record["family_refs"])
            self.assertTrue(record["semantic_bom_scope_frozen"])
            self.assertFalse(record["real_bom_complete"])
            for field in ("variant_geometry", "variant_placement", "variant_material_set", "variant_tolerance_set", "provenance_ref", "review_status", "datum_ref"):
                self.assertIsNone(record[field])
        self.assertNotIn("turbocharger", by_id["type_912_5_0_na"]["family_refs"])
        self.assertIn("turbocharger", by_id["917_30_1973_turbo_5374"]["family_refs"])

    def test_f13_facts_are_directly_bound_and_power_variants_are_distinct(self):
        guides = {item["variant_id"]: item for item in self.contract["documentary_design_guides"]}
        self.assertEqual((guides["type_912_5_0_na"]["bore"]["value"], guides["type_912_5_0_na"]["stroke"]["value"]), (86.8, 70.4))
        self.assertEqual((guides["917_30_1973_turbo_5374"]["bore"]["value"], guides["917_30_1973_turbo_5374"]["stroke"]["value"]), (90.0, 70.4))
        self.assertEqual(guides["type_912_5_0_na"]["source_contract"], "classical_solver_facts_f13")
        self.assertEqual(guides["917_30_1973_turbo_5374"]["source_contract"], "classical_solver_facts_f13")
        for guide in guides.values():
            self.assertFalse(guide["design_lock"])
            self.assertFalse(guide["cad_parameter_applied"])
            self.assertFalse(guide["boundary_condition"])
        power = self.contract["reported_power_boundary"]
        self.assertEqual(power["fact_ref"], "FACT-TURBO-POWER-1600-REPORTED")
        self.assertEqual(power["source_fact_variant_id"], "917_30_1600_hp_reported_qualifying_target")
        self.assertEqual(power["related_design_branch_id"], "917_30_1973_turbo_5374")
        self.assertNotEqual(power["source_fact_variant_id"], power["related_design_branch_id"])
        self.assertEqual(power["reported_value"], 1600.0)
        self.assertEqual(power["role"], "documentary_only_not_boundary_condition")

    def test_f16_minimal_graph_is_preserved_with_intermediates_cardinality_and_types(self):
        relations = {item["id"]: item for item in self.contract["common_topology_requirements"]}
        for relation_id, expected in EXPECTED_F16_GRAPH.items():
            item = relations[relation_id]
            actual = (item["source_family"], item["via_family"], item["target_family"], item["cardinality"], item["planned_interface_type"])
            self.assertEqual(actual, expected)
            self.assertEqual(item["upstream_contract"], "kinematic_interfaces_f16")
        required = {
            "head_to_cylinder",
            "camshaft_to_cam_carrier",
            "cam_carrier_to_head",
            "camshaft_to_bucket_tappet",
            "bucket_tappet_to_intake_valve",
            "bucket_tappet_to_exhaust_valve",
            "intake_valve_spring_stack",
            "exhaust_valve_spring_stack",
        }
        self.assertTrue(required <= set(relations))

    def test_turbo_crosswalk_and_complete_semantic_flow_lube_topology(self):
        turbo = self.contract["turbo_topology_requirement"]
        self.assertEqual(turbo["f19_source_family_ref"], "turbocharger")
        self.assertEqual(turbo["required_instance_count"], 2)
        self.assertEqual([item["id"] for item in turbo["instances"]], ["turbo_semantic_01", "turbo_semantic_02"])
        expected_components = {"chra": "turbo_chra", "compressor_housing": "turbo_compressor_housing", "turbine_housing": "turbo_turbine_housing", "wastegate": "wastegate"}
        for item in turbo["instances"]:
            self.assertEqual(item["family_ref"], "turbocharger")
            self.assertEqual(item["component_family_refs"], expected_components)
            self.assertFalse(item["released"])
        relations = {item["id"]: item for item in turbo["planned_relations"]}
        self.assertEqual(set(relations), set(EXPECTED_TURBO_RELATIONS))
        for relation_id, expected in EXPECTED_TURBO_RELATIONS.items():
            relation = relations[relation_id]
            actual = (
                relation["source_family"],
                relation["source_boundary_ref"],
                relation["via_family"],
                relation["target_family"],
                relation["cardinality"],
                relation["planned_interface_type"],
                relation["upstream_relation_ref"],
            )
            self.assertEqual(actual, expected, relation_id)
        self.assertEqual(relations["ambient_to_two_compressor_inlets"]["source_boundary_ref"], "bench_intake_ambient")
        for key in ("topology_bound_to_geometry", "maps_selected", "flow_network_released", "lubrication_network_released"):
            self.assertFalse(turbo[key])

    def test_na_exhaust_bypass_is_not_inherited_by_turbo_common_trunk(self):
        common = self.contract["common_topology_requirements"]
        na = self.contract["na_topology_requirements"]
        turbo = self.contract["turbo_topology_requirement"]["planned_relations"]
        self.assertTrue(all("na_" not in item["id"] and "na_" not in item["upstream_relation_ref"] for item in common))
        self.assertIn("na_exhaust_collector_to_bench_extraction", {item["id"] for item in na})
        self.assertNotIn("na_exhaust_collector_to_bench_extraction", {item["id"] for item in turbo})

    def test_no_declared_family_is_semantically_isolated(self):
        variants = {item["variant_id"]: set(item["family_refs"]) for item in self.contract["variant_contracts"]}
        common_relations = self.contract["common_topology_requirements"]
        for variant_id, extra in (("type_912_5_0_na", self.contract["na_topology_requirements"]), ("917_30_1973_turbo_5374", self.contract["turbo_topology_requirement"]["planned_relations"])):
            connected = set()
            for relation in common_relations + extra:
                connected.update(value for value in (relation["source_family"], relation["via_family"], relation["target_family"]) if value is not None)
            self.assertEqual(variants[variant_id] - connected, set())

    def test_all_engineering_and_topology_inputs_remain_null(self):
        for item in self.contract["component_family_registry"]:
            self.assertIsNone(item["real_bom_quantity"])
            self.assertFalse(item["route_selected"])
            self.assertFalse(item["released"])
            self.assertEqual(set(item["engineering_unknowns"]), {"dimension_set", "interface_definition", "material_specification", "placement_transform", "tolerance_set", "provenance_ref", "review_status", "datum_ref"})
            self.assertTrue(all(value is None for value in item["engineering_unknowns"].values()))
        relations = self.contract["common_topology_requirements"] + self.contract["na_topology_requirements"] + self.contract["turbo_topology_requirement"]["planned_relations"]
        for relation in relations:
            for field in ("interface_definition", "placement_transform", "tolerance_set", "provenance_ref", "review_status", "datum_ref"):
                self.assertIsNone(relation[field])
            self.assertFalse(relation["joint_created"])
            self.assertFalse(relation["active"])

    def test_non_boolean_false_like_gate_values_fail_closed(self):
        for fake in ("true", "false", 0, 1, None, [], {}):
            contract = copy.deepcopy(self.contract)
            contract["release_gates"]["fabrication_authorized"] = fake
            report = self.module.evaluate(ROOT, contract)
            self.assertEqual(report["report_status"], "failed")
            self.assertIn("release_gates_must_be_exact_booleans_false", report["contract_errors"])
        loaded = self._loaded_upstreams()
        f19 = loaded["manufacturing_routing_f19"]
        f19["release_gates"]["vehicle_use_authorized"] = "true"
        with self.assertRaisesRegex(self.module.ContractError, "f19_release_gates_must_remain_false"):
            self.module.validate_upstream_invariants(loaded)

    def test_upstream_gate_key_deletion_fails_independent_invariants(self):
        cases = (
            ("kinematic_interfaces_f16", "scan_identity_verified", "f16_release_gates_must_remain_false"),
            ("manufacturing_routing_f19", "vehicle_use_authorized", "f19_release_gates_must_remain_false"),
            ("dual_variant_functional_readiness_f24", "manufacturing_authorized", "f24_release_gates_must_remain_false"),
            ("physical_metrology_campaign_f27", "engine_start_authorized", "f27_release_gates_must_remain_false"),
            ("variant_visualization_f10", "performance_claim_authorized", "f10_excluded_source_mismatch"),
            ("valvetrain_flow_f20", "physicsnemo_ready", "f20_excluded_source_mismatch"),
            ("parametric_cad_f22", "functional_engine_authorized", "f22_excluded_source_mismatch"),
        )
        for source_id, gate_id, error in cases:
            with self.subTest(source_id=source_id, gate_id=gate_id):
                loaded = self._loaded_upstreams()
                del loaded[source_id]["release_gates"][gate_id]
                with self.assertRaisesRegex(self.module.ContractError, error):
                    self.module.validate_upstream_invariants(loaded)

    def test_independent_invariants_reject_reviewed_rebase_bypasses(self):
        mutations = []
        loaded = self._loaded_upstreams()
        next(item for item in loaded["manufacturing_routing_f19"]["family_route_registry"] if item["id"] == "piston")["functional_disposition"]["route_class"] = "metal_additive_candidate"
        mutations.append((loaded, "f19_route_mismatch:piston"))
        loaded = self._loaded_upstreams()
        loaded["kinematic_interfaces_f16"]["component_instance_contract"] = []
        mutations.append((loaded, "f16_component_instance_contract_mismatch"))
        loaded = self._loaded_upstreams()
        loaded["dual_variant_functional_readiness_f24"]["variant_crosswalk"][1]["reported_1600_hp_fact_ref"] = "FACT-INVENTED"
        mutations.append((loaded, "f24_reported_power_scope_mismatch"))
        loaded = self._loaded_upstreams()
        fact = next(item for item in loaded["classical_solver_facts_f13"]["fact_registry"] if item["id"] == "FACT-TURBO-POWER-1600-REPORTED")
        fact["variant"] = "917_30_1973_turbo_5374"
        mutations.append((loaded, "f13_fact_invariant_mismatch:FACT-TURBO-POWER-1600-REPORTED"))
        loaded = self._loaded_upstreams()
        external = loaded["manufacturing_routing_f19"]["f8_interface_route_registry"]["external_interfaces"]
        external[:] = [item for item in external if item["id"] != "bench_intake_ambient"]
        mutations.append((loaded, "f19_bench_intake_ambient_boundary_mismatch"))
        for mutated, message in mutations:
            with self.assertRaisesRegex(self.module.ContractError, message):
                self.module.validate_upstream_invariants(mutated)

    def test_modified_upstream_cannot_be_rebound_by_upstreams_view(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            self._copy_upstreams(temp_root)
            path = temp_root / "twins/reference-917-engine/manufacturing-routing-f19.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            next(item for item in data["family_route_registry"] if item["id"] == "piston")["functional_disposition"]["route_class"] = "metal_additive_candidate"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(TypeError):
                self.module.UPSTREAMS["manufacturing_routing_f19"]["sha256"] = file_sha256(path)
            with self.assertRaisesRegex(self.module.ContractError, "upstream_sha256_mismatch:manufacturing_routing_f19"):
                self.module.build_contract(temp_root)

    def test_adversarial_injections_fail_closed(self):
        contract = copy.deepcopy(self.contract)
        record = next(item for item in contract["component_family_registry"] if item["id"] == "piston_ring")
        record["route_class"] = "metal_additive_candidate"
        record["engineering_unknowns"]["dimension_set"] = {"invented": 1}
        contract["asset"]["scan_bound"] = True
        contract["authority_boundary"]["cad_master_generated"] = True
        contract["turbo_topology_requirement"]["instances"][0]["commercial_model"] = "invented"
        report = self.module.evaluate(ROOT, contract)
        self.assertEqual(report["report_status"], "failed")
        self.assertIn("route_laundering_forbidden:piston_ring", report["contract_errors"])
        self.assertIn("engineering_unknown_must_be_null:piston_ring:dimension_set", report["contract_errors"])
        self.assertIn("scan_binding_forbidden", report["contract_errors"])
        self.assertIn("authority_gate_open_or_not_boolean", report["contract_errors"])
        self.assertIn("turbo_input_must_be_null:turbo_semantic_01:commercial_model", report["contract_errors"])
        self.assertTrue(strict_false_tree(report["release"]))

    def test_generator_modes_are_mutually_exclusive_and_check_is_read_only(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "f28.json"
            output.write_text(json.dumps(self.contract, indent=2) + "\n", encoding="utf-8")
            before = output.read_bytes()
            both = subprocess.run(["python3", str(SCRIPT), "--root", str(ROOT), "--output", str(output), "--check", "--write"], capture_output=True, text=True, env=environment, check=False)
            self.assertEqual(both.returncode, 2)
            self.assertEqual(output.read_bytes(), before)
            checked = subprocess.run(["python3", str(SCRIPT), "--root", str(ROOT), "--output", str(output), "--check"], capture_output=True, text=True, env=environment, check=False)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(output.read_bytes(), before)

    def test_generator_rejects_non_json_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bad = Path(temp_dir) / "forbidden.step"
            with self.assertRaisesRegex(self.module.ContractError, "output_must_be_json"):
                self.module.write_contract(bad, self.contract)
            self.assertFalse(bad.exists())


if __name__ == "__main__":
    unittest.main()
