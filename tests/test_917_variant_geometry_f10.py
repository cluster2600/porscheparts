import copy
import importlib.util
import json
import math
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "twins/reference-917-engine/variant-configurations-f10.json"
PREPARE = ROOT / "twins/reference-917-engine/source/prepare_variant_configs_f10.py"
DETAIL_BUILDER = ROOT / "twins/reference-917-engine/source/build_detail_expansion_f3.py"
KINEMATICS_MATH = ROOT / "twins/reference-917-engine/source/kinematics_f2_math.py"
RUNNER = ROOT / "twins/reference-917-engine/run_variant_geometry_f10.sh"
F1 = ROOT / "twins/reference-917-engine/complete-engine-f1.json"
F9 = ROOT / "twins/reference-917-engine/performance-target-f9.json"

SPEC = importlib.util.spec_from_file_location("engine_917_variant_f10", PREPARE)
assert SPEC is not None and SPEC.loader is not None
F10 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F10)

DETAIL_SPEC = importlib.util.spec_from_file_location("engine_917_detail_builder", DETAIL_BUILDER)
assert DETAIL_SPEC is not None and DETAIL_SPEC.loader is not None
DETAIL = importlib.util.module_from_spec(DETAIL_SPEC)
DETAIL_SPEC.loader.exec_module(DETAIL)

MATH_SPEC = importlib.util.spec_from_file_location("engine_917_kinematics_math", KINEMATICS_MATH)
assert MATH_SPEC is not None and MATH_SPEC.loader is not None
KINEMATICS = importlib.util.module_from_spec(MATH_SPEC)
MATH_SPEC.loader.exec_module(KINEMATICS)


class Engine917VariantGeometryF10Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.variants = {item["variant_id"]: item for item in cls.manifest["variants"]}

    def test_contract_is_fail_closed_and_valid(self):
        self.assertEqual(F10.validate_contract(self.manifest, ROOT), [])
        gates = self.manifest["release_gates"]
        for gate in F10.PHYSICAL_RELEASE_GATES:
            self.assertIs(gates[gate], False)
        self.assertIn("manufacturing_release", self.manifest["prohibited_use"])

    def test_two_variants_have_distinct_sourced_geometry(self):
        self.assertEqual(set(self.variants), {"type_912_4_5_na", "917_30_turbo_5374"})
        na = self.variants["type_912_4_5_na"]["geometry"]
        turbo = self.variants["917_30_turbo_5374"]["geometry"]
        self.assertEqual((na["bore_mm"], na["stroke_mm"]), (85.0, 66.0))
        self.assertEqual((turbo["bore_mm"], turbo["stroke_mm"]), (90.0, 70.4))
        self.assertAlmostEqual(
            F10.calculated_displacement_cm3(12, na["bore_mm"], na["stroke_mm"]),
            4494.205370592878,
        )
        self.assertAlmostEqual(
            F10.calculated_displacement_cm3(12, turbo["bore_mm"], turbo["stroke_mm"]),
            5374.3853843491315,
        )
        for geometry in (na, turbo):
            self.assertEqual(set(geometry["field_evidence"]), F10.REQUIRED_EVIDENCE_FIELDS)
            self.assertTrue(all(geometry["field_evidence"].values()))

    def test_f1_and_f9_are_the_geometry_cross_checks(self):
        f1 = json.loads(F1.read_text(encoding="utf-8"))
        f9 = json.loads(F9.read_text(encoding="utf-8"))
        na = self.variants["type_912_4_5_na"]["geometry"]
        turbo = self.variants["917_30_turbo_5374"]["geometry"]
        self.assertEqual(
            (na["bore_mm"], na["stroke_mm"]),
            (f1["declared_dimensions"]["bore_mm"], f1["declared_dimensions"]["stroke_mm"]),
        )
        self.assertEqual(
            (turbo["bore_mm"], turbo["stroke_mm"]),
            (f9["geometry"]["bore_mm"], f9["geometry"]["stroke_mm"]),
        )

    def test_stage_provenance_payload_preserves_documented_value_and_exact_field_map(self):
        for variant_id, variant in self.variants.items():
            geometry = variant["geometry"]
            payload = F10.stage_provenance_payload(
                variant_id,
                geometry["documented_displacement_cm3"],
                geometry["field_evidence"],
            )
            self.assertEqual(payload["variant_id"], variant_id)
            self.assertEqual(
                payload["documented_displacement_cm3"], geometry["documented_displacement_cm3"]
            )
            self.assertEqual(
                payload["field_evidence"],
                {field: sorted(source_ids) for field, source_ids in sorted(geometry["field_evidence"].items())},
            )

    def test_stage_provenance_evaluation_rejects_metadata_mutations(self):
        variant_id = "917_30_turbo_5374"
        expected_geometry = F10.EXPECTED_VARIANT_GEOMETRY[variant_id]
        expected = F10.stage_provenance_payload(
            variant_id,
            expected_geometry["values"]["documented_displacement_cm3"],
            expected_geometry["field_evidence"],
        )
        calculated = F10.calculated_displacement_cm3(
            expected_geometry["values"]["cylinder_count"],
            expected_geometry["values"]["bore_mm"],
            expected_geometry["values"]["stroke_mm"],
        )

        valid = F10.evaluate_stage_provenance(
            expected,
            documented_displacement_cm3=5374.0,
            calculated_displacement_cm3=calculated,
            field_evidence_json=json.dumps(expected["field_evidence"]),
            expected_calculated_displacement_cm3=calculated,
        )
        self.assertTrue(all(result["passed"] for result in valid.values()))

        mutations = (
            {"documented_displacement_cm3": 5378.0},
            {"calculated_displacement_cm3": True},
            {
                "field_evidence_json": json.dumps(
                    {
                        **expected["field_evidence"],
                        "bore_mm": ["SRC-KFZ-TECH-917-TYPE912-ENGINE"],
                    }
                )
            },
            {"field_evidence_json": "{invalid-json"},
        )
        defaults = {
            "documented_displacement_cm3": 5374.0,
            "calculated_displacement_cm3": calculated,
            "field_evidence_json": json.dumps(expected["field_evidence"]),
            "expected_calculated_displacement_cm3": calculated,
        }
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = F10.evaluate_stage_provenance(expected, **(defaults | mutation))
                self.assertFalse(all(item["passed"] for item in result.values()))

    def test_stages_are_separate_instead_of_a_visibility_variant(self):
        self.assertEqual(
            self.manifest["stage_policy"]["mode"],
            "one_geometry_and_kinematic_stage_per_variant",
        )
        self.assertIs(self.manifest["stage_policy"]["engine_variant_set_allowed"], False)
        paths = [
            path
            for variant in self.manifest["variants"]
            for path in variant["outputs"].values()
        ]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(path.startswith(f"{variant['output_slug']}/stages/") for variant in self.manifest["variants"] for path in variant["outputs"].values()))

    def test_turbo_families_are_filtered_out_of_the_na_branch(self):
        na = self.variants["type_912_4_5_na"]["assembly_filter"]
        turbo = self.variants["917_30_turbo_5374"]["assembly_filter"]
        self.assertEqual(na["f1_variant_tags"], ["base"])
        self.assertEqual(na["f3_variant_tags"], ["all"])
        self.assertEqual((na["turbocharger_expected_count"], na["charge_plenum_expected_count"]), (0, 0))
        self.assertEqual(set(turbo["f1_variant_tags"]), {"base", "917_30_only"})
        self.assertEqual(set(turbo["f3_variant_tags"]), {"all", "917_30_only"})
        self.assertEqual((turbo["turbocharger_expected_count"], turbo["charge_plenum_expected_count"]), (2, 2))

    def test_four_stroke_valve_cycle_keeps_twelve_unique_firing_phases(self):
        config = json.loads((ROOT / "twins/reference-917-engine/kinematics-f2.json").read_text(encoding="utf-8"))
        order = config["firing_order"]["sequence"]
        phases = [KINEMATICS.cylinder_cycle_deg(0.0, cylinder, order) for cylinder in range(1, 13)]
        self.assertEqual(len(set(phases)), 12)
        for offset in range(6):
            first = order[offset]
            second = order[offset + 6]
            self.assertEqual(
                (KINEMATICS.cylinder_cycle_deg(0.0, second, order) - KINEMATICS.cylinder_cycle_deg(0.0, first, order)) % 720.0,
                360.0,
            )

    def test_crankshaft_and_rod_geometry_remain_explicit_visual_hypotheses(self):
        scope = self.manifest["variant_change_scope"]
        self.assertIn(
            "crankshaft_body_throw_and_counterweight_proxy_geometry",
            scope["intentionally_unchanged_visual_hypotheses"],
        )
        self.assertIn("ne reconstruit pas un vilebrequin 917/30", scope["explicit_limit"])
        for variant in self.manifest["variants"]:
            status = variant["kinematics"]["connecting_rod_status"]
            self.assertIn("hypothesis", status)
            self.assertIn("not_sourced", status)
            self.assertFalse(variant["kinematics"]["physical_kinematics_ready"])

    def test_generated_configs_preserve_provenance_and_filter_families(self):
        original_f1 = json.loads(F1.read_text(encoding="utf-8"))
        original_sources = set(original_f1["source_ids"])
        na_f1, na_f2, na_f3 = F10.generated_configs(
            self.manifest, ROOT, self.variants["type_912_4_5_na"]
        )
        turbo_f1, turbo_f2, turbo_f3 = F10.generated_configs(
            self.manifest, ROOT, self.variants["917_30_turbo_5374"]
        )
        self.assertTrue(original_sources <= set(na_f1["source_ids"]))
        self.assertTrue(original_sources <= set(turbo_f1["source_ids"]))
        self.assertNotIn("turbocharger", {item["id"] for item in na_f1["component_families"]})
        self.assertNotIn("charge_plenum", {item["id"] for item in na_f1["component_families"]})
        self.assertIn("turbocharger", {item["id"] for item in turbo_f1["component_families"]})
        self.assertEqual((na_f2["f10_variant"]["bore_mm"], na_f2["crank_slider"]["stroke_mm"]), (85.0, 66.0))
        self.assertEqual((turbo_f2["f10_variant"]["bore_mm"], turbo_f2["crank_slider"]["stroke_mm"]), (90.0, 70.4))
        self.assertEqual((na_f3["acceptance"]["added_family_count"], na_f3["acceptance"]["added_instance_count"]), (8, 20))
        self.assertEqual((turbo_f3["acceptance"]["added_family_count"], turbo_f3["acceptance"]["added_instance_count"]), (13, 30))

    def test_detail_generator_respects_each_variant_family_filter(self):
        turbo_only = {
            "turbo_turbine_wheel",
            "turbo_compressor_wheel",
            "turbo_shaft",
            "wastegate",
            "wastegate_bypass_pipe",
        }
        available_placements = DETAIL.placements()
        available_shapes = {
            family: object()
            for family in {item["family"] for item in available_placements}
        }
        selected = {}
        for variant_id in ("type_912_4_5_na", "917_30_turbo_5374"):
            _, _, detail_config = F10.generated_configs(
                self.manifest, ROOT, self.variants[variant_id]
            )
            shapes, layout = DETAIL.select_configured_geometry(
                detail_config, available_shapes, available_placements
            )
            requested = {item["id"] for item in detail_config["families"]}
            self.assertEqual(set(shapes), requested)
            self.assertEqual({item["family"] for item in layout}, requested)
            self.assertEqual(len(shapes), detail_config["acceptance"]["added_family_count"])
            self.assertEqual(len(layout), detail_config["acceptance"]["added_instance_count"])
            selected[variant_id] = set(shapes)

        self.assertTrue(turbo_only.isdisjoint(selected["type_912_4_5_na"]))
        self.assertTrue(turbo_only <= selected["917_30_turbo_5374"])

    def test_contract_rejects_shared_stage_or_physical_release(self):
        shared = copy.deepcopy(self.manifest)
        shared["variants"][1]["outputs"]["geometry_stage"] = shared["variants"][0]["outputs"]["geometry_stage"]
        errors = F10.validate_contract(shared, ROOT)
        self.assertIn("variants.outputs: every stage path must be unique", errors)
        released = copy.deepcopy(self.manifest)
        released["release_gates"]["manufacturing_geometry_ready"] = True
        errors = F10.validate_contract(released, ROOT)
        self.assertIn("release_gates.manufacturing_geometry_ready: must remain false in F10", errors)

        renamed = copy.deepcopy(self.manifest)
        renamed["variants"][0]["outputs"]["geometry_stage"] = (
            "type-912-4-5-na/stages/arbitrary-name.usda"
        )
        errors = F10.validate_contract(renamed, ROOT)
        self.assertIn(
            "variants.type_912_4_5_na.outputs.geometry_stage: expected "
            "type-912-4-5-na/stages/type-912-4-5-na-geometry-f10.usda",
            errors,
        )

    def test_contract_rejects_unsourced_turbo_geometry(self):
        mutated = copy.deepcopy(self.manifest)
        turbo = next(item for item in mutated["variants"] if item["variant_id"] == "917_30_turbo_5374")
        turbo["geometry"]["field_evidence"]["bore_mm"] = []
        errors = F10.validate_contract(mutated, ROOT)
        self.assertIn(
            "variants.917_30_turbo_5374.geometry.field_evidence.bore_mm: at least one source is required",
            errors,
        )

    def test_contract_rejects_duplicate_or_escaping_slugs(self):
        duplicate = copy.deepcopy(self.manifest)
        duplicate["variants"][1]["output_slug"] = duplicate["variants"][0]["output_slug"]
        errors = F10.validate_contract(duplicate, ROOT)
        self.assertIn("variants.output_slug: every variant slug must be unique", errors)

        traversal = copy.deepcopy(self.manifest)
        turbo = next(item for item in traversal["variants"] if item["variant_id"] == "917_30_turbo_5374")
        turbo["output_slug"] = "../../outside"
        turbo["outputs"] = {
            key: f"../../outside/stages/{Path(value).name}" for key, value in turbo["outputs"].items()
        }
        errors = F10.validate_contract(traversal, ROOT)
        self.assertIn(
            "variants.917_30_turbo_5374.output_slug: must be a safe lowercase slug",
            errors,
        )
        self.assertTrue(any("outputs.geometry_stage" in error for error in errors))

    def test_contract_rejects_non_twelve_cylinder_geometry(self):
        mutated = copy.deepcopy(self.manifest)
        turbo = next(item for item in mutated["variants"] if item["variant_id"] == "917_30_turbo_5374")
        turbo["geometry"]["cylinder_count"] = 13
        turbo["geometry"]["documented_displacement_cm3"] = F10.calculated_displacement_cm3(
            13, turbo["geometry"]["bore_mm"], turbo["geometry"]["stroke_mm"]
        )
        errors = F10.validate_contract(mutated, ROOT)
        self.assertIn("variants.917_30_turbo_5374.geometry.cylinder_count: must be 12", errors)

    def test_contract_rejects_a_source_that_does_not_support_the_field(self):
        mutated = copy.deepcopy(self.manifest)
        turbo = next(item for item in mutated["variants"] if item["variant_id"] == "917_30_turbo_5374")
        turbo["geometry"]["field_evidence"]["bore_mm"] = ["SRC-PORSCHE-NEWSROOM-91730-TURBO"]
        errors = F10.validate_contract(mutated, ROOT)
        self.assertIn(
            "variants.917_30_turbo_5374.geometry.field_evidence.bore_mm: "
            "sources do not support this field ['SRC-PORSCHE-NEWSROOM-91730-TURBO']",
            errors,
        )

    def test_contract_rejects_cross_variant_or_wrong_definition_evidence(self):
        mutations = [
            ("917_30_turbo_5374", "bore_mm", ["SRC-KFZ-TECH-917-TYPE912-ENGINE"]),
            ("type_912_4_5_na", "cylinder_count", ["SRC-PORSCHE-NEWSROOM-91730-TURBO"]),
            ("type_912_4_5_na", "documented_displacement_cm3", ["SRC-PORSCHE-NEWSROOM-91730-TURBO"]),
            ("917_30_turbo_5374", "stroke_mm", ["SRC-STUTTCARS-917-TECHNICAL-DETAILS"]),
        ]
        for variant_id, field, source_ids in mutations:
            with self.subTest(variant_id=variant_id, field=field):
                mutated = copy.deepcopy(self.manifest)
                variant = next(item for item in mutated["variants"] if item["variant_id"] == variant_id)
                variant["geometry"]["field_evidence"][field] = source_ids
                errors = F10.validate_contract(mutated, ROOT)
                self.assertTrue(
                    any(f"variants.{variant_id}.geometry.field_evidence.{field}:" in error for error in errors),
                    errors,
                )

    def test_contract_rejects_nearby_but_not_documented_displacements(self):
        for variant_id, value in (("type_912_4_5_na", 4498.0), ("917_30_turbo_5374", 5378.0)):
            with self.subTest(variant_id=variant_id):
                mutated = copy.deepcopy(self.manifest)
                variant = next(item for item in mutated["variants"] if item["variant_id"] == variant_id)
                variant["geometry"]["documented_displacement_cm3"] = value
                errors = F10.validate_contract(mutated, ROOT)
                expected = F10.EXPECTED_VARIANT_GEOMETRY[variant_id]["values"]["documented_displacement_cm3"]
                self.assertIn(
                    f"variants.{variant_id}.geometry.documented_displacement_cm3: "
                    f"expected documented value {expected}",
                    errors,
                )

    def test_contract_rejects_physical_status_unknown_gates_and_removed_power_limits(self):
        status = copy.deepcopy(self.manifest)
        status["status"] = "physically_validated"
        errors = F10.validate_contract(status, ROOT)
        self.assertIn(f"status: expected {F10.EXPECTED_STATUS}", errors)

        gate = copy.deepcopy(self.manifest)
        gate["release_gates"]["fea_proof_ready"] = True
        errors = F10.validate_contract(gate, ROOT)
        self.assertTrue(any(error.startswith("release_gates: expected exactly") for error in errors))

        prohibited = copy.deepcopy(self.manifest)
        prohibited["prohibited_use"].remove("claim_that_F10_proves_1600_hp")
        prohibited["prohibited_use"].remove("combustion_power_torque_or_durability_claim")
        errors = F10.validate_contract(prohibited, ROOT)
        self.assertTrue(any("claim_that_F10_proves_1600_hp" in error for error in errors))
        self.assertTrue(any("combustion_power_torque_or_durability_claim" in error for error in errors))

    def test_cli_materializes_two_config_trees_under_work_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "f10"
            completed = subprocess.run(
                [
                    "python3",
                    str(PREPARE),
                    "--manifest",
                    str(MANIFEST),
                    "--project-root",
                    str(ROOT),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads((output / "variant-config-generation-report.json").read_text(encoding="utf-8"))
            self.assertEqual(json.loads(completed.stdout), report)
            self.assertEqual(report["variant_count"], 2)
            for variant in self.manifest["variants"]:
                config_root = output / variant["output_slug"] / "configs"
                self.assertTrue((config_root / "complete-engine-f10.json").is_file())
                self.assertTrue((config_root / "kinematics-f10.json").is_file())
                self.assertTrue((config_root / "detail-expansion-f10.json").is_file())

    def test_cli_check_remains_read_only_even_if_output_is_supplied(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "must-not-exist"
            completed = subprocess.run(
                [
                    "python3",
                    str(PREPARE),
                    "--manifest",
                    str(MANIFEST),
                    "--project-root",
                    str(ROOT),
                    "--output",
                    str(output),
                    "--check",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(completed.stdout)
            self.assertFalse(report["write_performed"])
            self.assertFalse(output.exists())

    def test_runner_rejects_output_override_that_escapes_work(self):
        completed = subprocess.run(
            ["bash", str(RUNNER)],
            cwd=ROOT,
            env={**os.environ, "F10_OUTPUT_REL": "work/../../f10-escape-must-not-write"},
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("doit se resoudre dans un sous-repertoire de work/", completed.stderr)

    def test_runner_refuses_an_existing_output_before_starting_docker(self):
        work_root = ROOT / "work"
        work_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_root) as temp_dir:
            relative = Path(temp_dir).resolve().relative_to(ROOT)
            completed = subprocess.run(
                ["bash", str(RUNNER)],
                cwd=ROOT,
                env={**os.environ, "F10_OUTPUT_REL": str(relative)},
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("le repertoire de sortie existe deja", completed.stderr)

    def test_runner_creates_work_parent_before_acquiring_lock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            clean_root = Path(temp_dir)
            clean_runner = clean_root / "twins/reference-917-engine/run_variant_geometry_f10.sh"
            clean_runner.parent.mkdir(parents=True)
            shutil.copy2(RUNNER, clean_runner)
            self.assertFalse((clean_root / "work").exists())
            completed = subprocess.run(
                ["bash", str(clean_runner)],
                cwd=clean_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertTrue((clean_root / "work").is_dir())
            self.assertFalse((clean_root / "work/.917-variant-geometry-f10.lock").exists())
            self.assertNotIn("une autre generation detient", completed.stderr)


if __name__ == "__main__":
    unittest.main()
