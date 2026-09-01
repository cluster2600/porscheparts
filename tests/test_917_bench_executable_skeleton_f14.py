import copy
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN_ROOT = ROOT / "twins/reference-917-engine"
CONFIG = TWIN_ROOT / "bench-executable-skeleton-f14.json"
BUILDER = TWIN_ROOT / "source/build_bench_executable_skeleton_f14.py"
MECHANICAL = TWIN_ROOT / "mechanical-connections-f8.json"
DUCTS = TWIN_ROOT / "ducts-f8.json"
NA = "type_912_4_5_na"
TURBO = "917_30_turbo_5374"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def applies(item, variant_id):
    tags = {
        NA: {"all", "type_912_4_5_na"},
        TURBO: {"all", "917_30_only"},
    }
    return item["variant"] in tags[variant_id]


class Engine917BenchExecutableSkeletonF14Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load(CONFIG)
        cls.mechanical = load(MECHANICAL)
        cls.ducts = load(DUCTS)

    def test_contract_has_two_explicit_f10_compositions(self):
        variants = {item["variant_id"]: item for item in self.config["variants"]}
        self.assertEqual(set(variants), {NA, TURBO})
        self.assertEqual(
            variants[NA]["input_stage"],
            "work/917-variant-geometry-f10/type-912-4-5-na/stages/type-912-4-5-na-detail-f10.usda",
        )
        self.assertEqual(
            variants[TURBO]["input_stage"],
            "work/917-variant-geometry-f10/917-30-turbo-5374/stages/917-30-turbo-5374-detail-f10.usda",
        )
        self.assertNotEqual(variants[NA]["input_stage"], variants[TURBO]["input_stage"])

    def test_equipment_and_sensor_counts_are_real_contract_sums(self):
        equipment = self.config["bench_equipment"]
        sensors = self.config["instrumentation"]
        self.assertEqual(len(equipment), 12)
        self.assertEqual(sum(item["count"] for item in equipment), 16)
        self.assertEqual(
            sum(item["count"] for item in equipment if item["f4_authoring_status"] == "missing"),
            5,
        )
        self.assertEqual(
            {item["id"] for item in equipment if item["f4_authoring_status"] == "missing"},
            {"starter_motor", "cooling_air_supply", "exhaust_extraction", "fire_suppression"},
        )
        self.assertEqual(len(sensors), 10)
        self.assertEqual(sum(item["count"] for item in sensors), 49)

    def test_source_graph_counts_are_deduced_per_variant(self):
        mechanical = self.mechanical["mechanical_connections"]
        ducts = self.ducts["ducts"]
        graph = self.config["semantic_graph"]
        self.assertEqual(len(mechanical), 18)
        self.assertEqual(sum(item["count"] for item in mechanical), 119)
        self.assertEqual(sum(item["count"] for item in mechanical if applies(item, NA)), 117)
        self.assertEqual(sum(item["count"] for item in mechanical if applies(item, TURBO)), 119)
        self.assertEqual(len(ducts), 21)
        self.assertEqual(sum(item["count"] for item in ducts), 106)
        self.assertEqual(sum(item["count"] for item in ducts if item["variant"] == "all"), 68)
        self.assertEqual(sum(item["count"] for item in ducts if item["variant"] == "type_912_4_5_na"), 14)
        self.assertEqual(sum(item["count"] for item in ducts if item["variant"] == "917_30_only"), 24)
        self.assertEqual(sum(item["count"] for item in ducts if applies(item, NA)), 82)
        self.assertEqual(sum(item["count"] for item in ducts if applies(item, TURBO)), 92)
        self.assertEqual(graph["mechanical_connections"]["union_instance_count"], 119)
        self.assertEqual(graph["ducts"]["union_instance_count"], 106)

    def run_builder(self, temp: Path, config_path: Path = CONFIG):
        na_stage = temp / "inputs/na-f10.usda"
        turbo_stage = temp / "inputs/turbo-f10.usda"
        na_stage.parent.mkdir(parents=True, exist_ok=True)
        minimal_stage = '#usda 1.0\n(defaultPrim = "World")\ndef Xform "World" {}\n'
        na_stage.write_text(minimal_stage, encoding="utf-8")
        turbo_stage.write_text(minimal_stage, encoding="utf-8")
        checker = temp / "usdchecker-fake"
        checker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        checker.chmod(checker.stat().st_mode | 0o111)
        output = temp / "output"
        result = subprocess.run(
            [
                "python3",
                str(BUILDER),
                "--project-root",
                str(ROOT),
                "--config",
                str(config_path),
                "--output",
                str(output),
                "--na-input-stage",
                str(na_stage),
                "--turbo-input-stage",
                str(turbo_stage),
                "--usdchecker",
                str(checker),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report_path = output / "state-machine-report.json"
        report = load(report_path) if report_path.is_file() else None
        return result, output, report

    def test_builder_authors_two_fail_closed_ascii_overlays(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result, output, report = self.run_builder(Path(temp_dir))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(report["status"], "software_runtime_passed_engine_physics_blocked")
            self.assertTrue(report["software_runtime_passed"])
            self.assertFalse(report["engine_physics_validated"])
            self.assertFalse(report["fluid_simulation_ready"])
            self.assertFalse(report["fired_run_executed"])
            self.assertEqual(report["engine_physics_joint_count"], 0)
            self.assertEqual(report["engine_articulation_root_count"], 0)
            self.assertEqual(report["cfd_volume_count"], 0)
            stages = {item["variant_id"]: item for item in report["variant_stages"]}
            self.assertEqual(stages[NA]["mechanical_connection_instances"], 117)
            self.assertEqual(stages[TURBO]["mechanical_connection_instances"], 119)
            self.assertEqual(stages[NA]["duct_instances"], 82)
            self.assertEqual(stages[TURBO]["duct_instances"], 92)
            for variant_id, slug in ((NA, "type-912-4-5-na"), (TURBO, "917-30-turbo-5374")):
                stage_path = output / slug / "917-engine-bench-executable-skeleton-f14.usda"
                text = stage_path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("#usda 1.0"))
                self.assertIn(f"benchExecutableVariantId = \"{variant_id}\"", text)
                self.assertEqual(text.count("equipmentInstanceIndex ="), 16)
                self.assertEqual(text.count("sensorInstanceIndex ="), 49)
                self.assertNotIn("PhysicsJoint", text)
                self.assertNotIn("PhysicsRigidBodyAPI", text)
                self.assertNotIn("PhysicsCollisionAPI", text)
                self.assertNotIn("PhysicsArticulationRootAPI", text)
                self.assertNotIn("def Mesh", text)
                self.assertNotIn("def Volume", text)
                self.assertEqual(stages[variant_id]["orphan_semantic_endpoint_count"], 0)
                self.assertEqual(stages[variant_id]["new_physics_schema_tokens"], [])
                self.assertEqual(
                    stages[variant_id]["ascii_dependency_joint_scan"]["ascii_joint_token_findings"],
                    [],
                )

    def test_every_graph_relationship_targets_an_authored_semantic_port(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result, output, _ = self.run_builder(Path(temp_dir))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            for path in output.glob("*/917-engine-bench-executable-skeleton-f14.usda"):
                text = path.read_text(encoding="utf-8")
                targets = re.findall(
                    r"custom rel (?:body_a|body_b|source|target) = <(/World/BenchExecutableF14/Ports/([^/]+)/([^>]+))>",
                    text,
                )
                self.assertTrue(targets)
                for _, scope, endpoint_id in targets:
                    self.assertIn(f'def Scope "{scope}"', text)
                    self.assertIn(f'def Xform "{endpoint_id}"', text)

    def test_state_machine_pass_is_explicitly_not_engine_proof(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result, _, report = self.run_builder(Path(temp_dir))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            gates = {item["id"]: item["status"] for item in report["state_machine"]}
            self.assertEqual(gates["usd_overlay_validation"], "passed")
            self.assertEqual(gates["measured_interface_frames"], "blocked")
            self.assertEqual(gates["closed_internal_fluid_volumes"], "blocked")
            self.assertEqual(gates["reference_solver_and_test_correlation"], "blocked")
            self.assertEqual(gates["instrumented_start_authorization"], "blocked")
            self.assertIn("not_engine_physics", report["software_runtime_scope"].replace(" ", "_"))

    def test_count_tampering_blocks_before_overlay_authoring(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            tampered = copy.deepcopy(self.config)
            tampered["semantic_graph"]["ducts"]["union_instance_count"] = 105
            config_path = temp / "tampered-f14.json"
            config_path.write_text(json.dumps(tampered), encoding="utf-8")
            result, output, report = self.run_builder(temp, config_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(report["status"], "blocked_before_authoring")
            self.assertFalse(report["software_runtime_passed"])
            self.assertFalse(report["engine_physics_validated"])
            self.assertTrue(any("duct_union_instances" in error for error in report["errors"]))
            self.assertEqual(list(output.glob("*/917-engine-bench-executable-skeleton-f14.usda")), [])


if __name__ == "__main__":
    unittest.main()
