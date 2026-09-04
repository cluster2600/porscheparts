import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source"
CONTRACT = ROOT / "twins/reference-917-engine/connecting-rod-cad-f44.json"
VALIDATOR = SOURCE / "validate_connecting_rod_cad_f44.py"
BUILDER = SOURCE / "build_connecting_rod_cad_f44.py"
SMOKE = SOURCE / "smoke_connecting_rod_cad_f44.py"


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class ConnectingRodCadF44Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module("validate_connecting_rod_cad_f44", VALIDATOR)
        cls.builder = load_module("build_connecting_rod_cad_f44", BUILDER)
        cls.smoke = load_module("smoke_connecting_rod_cad_f44", SMOKE)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def temporary_contract(self, payload):
        directory = tempfile.TemporaryDirectory(prefix="f44-connecting-rod-")
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_tracked_contract_passes(self):
        self.assertEqual(self.validator.validate(ROOT, CONTRACT), [])

    def test_only_allowed_parameter_classifications_are_used(self):
        self.assertEqual(
            set(self.contract["classification_vocabulary"]),
            {"design_hypothesis", "unknown_requires_traceable_measurement"},
        )
        self.assertTrue(
            all(record["classification"] == "design_hypothesis" for record in self.contract["parameter_register"].values())
        )
        for name, expected in {
            "rod_bolt_boss_radial_margin_mm": 2.0,
            "rod_bolt_seat_radial_clearance_mm": 0.5,
            "rod_bolt_spotface_depth_mm": 1.5,
        }.items():
            record = self.contract["parameter_register"][name]
            self.assertEqual(record["value"], expected)
            self.assertEqual(record["unit"], "mm")
            self.assertEqual(record["classification"], "design_hypothesis")
            self.assertEqual(record["source_refs"], [])
        self.assertTrue(
            all(
                record["value"] is None
                and record["classification"] == "unknown_requires_traceable_measurement"
                for record in self.contract["unknown_required_inputs"]
            )
        )

    def test_requested_detailed_features_are_explicit_and_separate(self):
        features = {record["id"]: record["count"] for record in self.contract["required_features"]}
        self.assertEqual(
            features,
            {
                "connecting_rod_body": 1,
                "connecting_rod_cap": 1,
                "cap_joint_plane": 1,
                "rod_bolt_through_hole": 2,
                "rod_bolt": 2,
                "big_end_half_bearing": 2,
                "small_end_bushing": 1,
                "internal_oil_channel": 1,
            },
        )
        specification = self.builder.describe(self.contract)
        self.assertEqual(specification["semantic_component_counts"]["connecting_rod_cap"], 1)
        self.assertEqual(specification["semantic_component_counts"]["rod_bolt"], 2)
        self.assertEqual(specification["semantic_component_counts"]["big_end_half_bearing"], 2)
        self.assertEqual(specification["semantic_component_counts"]["small_end_bushing"], 1)
        self.assertEqual(specification["subtractive_feature_counts"]["rod_bolt_through_hole"], 2)
        self.assertEqual(specification["subtractive_feature_counts"]["internal_oil_channel"], 1)

    def test_smoke_requires_exactly_nine_step_nine_stl_and_one_report(self):
        expected = self.smoke.expected_relative_files(self.contract)
        self.assertEqual(len(expected), 19)
        self.assertEqual(sum(path.suffix == ".step" for path in expected), 9)
        self.assertEqual(sum(path.suffix == ".stl" for path in expected), 9)
        self.assertIn(Path("geometry-report.json"), expected)

    def test_pair_topology_mismatch_is_computed_and_blocks_export(self):
        audit = self.builder.describe(self.contract)["pair_topology_audit"]
        self.assertAlmostEqual(audit["clearance_mm"], 1.32)
        self.assertAlmostEqual(audit["center_separation_mm"], 23.32)
        self.assertAlmostEqual(audit["required_span_mm"], 45.32)
        self.assertAlmostEqual(audit["available_crankpin_width_mm"], 26.0)
        self.assertAlmostEqual(audit["deficit_mm"], 19.32)
        self.assertAlmostEqual(audit["maximum_equal_rod_width_if_side_by_side_mm"], 26.0 / 2.06)
        self.assertFalse(self.contract["scope"]["paired_rod_assembly_allowed"])
        self.assertFalse(self.contract["output_policy"]["paired_assembly_export_allowed"])
        self.assertFalse(self.contract["pair_topology_audit"]["automatic_resize_allowed"])

    def test_validator_rejects_silent_pair_enablement_or_dimension_change(self):
        mutated = copy.deepcopy(self.contract)
        mutated["scope"]["paired_rod_assembly_allowed"] = True
        mutated["parameter_register"]["rod_width_mm"]["value"] = 12.0
        errors = self.validator.validate(ROOT, self.temporary_contract(mutated))
        self.assertTrue(any("paired_rod_assembly_allowed" in error for error in errors), errors)
        self.assertTrue(any("rod_width_mm" in error for error in errors), errors)

    def test_source_hash_and_geometry_transfer_are_fail_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["source_bindings"][0]["sha256"] = "0" * 64
        mutated["source_bindings"][1]["geometry_transfer_authorized"] = True
        errors = self.validator.validate(ROOT, self.temporary_contract(mutated))
        self.assertTrue(any("declared sha256 mismatch" in error for error in errors), errors)
        self.assertTrue(any("geometry transfer must remain false" in error for error in errors), errors)

    def test_duplicate_source_and_extra_top_level_key_fail_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["source_bindings"].append(copy.deepcopy(mutated["source_bindings"][0]))
        mutated["unreviewed_escape_hatch"] = True
        errors = self.validator.validate(ROOT, self.temporary_contract(mutated))
        self.assertTrue(any("duplicate id" in error for error in errors), errors)
        self.assertTrue(any("top-level keys mismatch" in error for error in errors), errors)

    def test_all_release_gates_and_physics_metadata_remain_closed(self):
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        metadata = self.builder.describe(self.contract)["metadata"]
        self.assertTrue(metadata["display_only"])
        self.assertFalse(metadata["physical_joint_enabled"])
        self.assertFalse(metadata["physics_enabled"])
        self.assertFalse(metadata["simulation_result"])
        self.assertFalse(metadata["manufacturing_geometry"])
        self.assertFalse(metadata["power_evidence"])

    def test_validator_rejects_open_gate_or_filled_unknown(self):
        mutated = copy.deepcopy(self.contract)
        mutated["release_gates"]["manufacturing_authorized"] = True
        mutated["unknown_required_inputs"][0]["value"] = 45.32
        errors = self.validator.validate(ROOT, self.temporary_contract(mutated))
        self.assertTrue(any("every release gate" in error for error in errors), errors)
        self.assertTrue(any("value must remain null" in error for error in errors), errors)

    def test_validator_rejects_each_reviewed_fail_open_mutation(self):
        mutations = []

        manufacturing = copy.deepcopy(self.contract)
        manufacturing["release_gates"]["manufacturing_authorized"] = True
        mutations.append(("manufacturing_authorized", manufacturing, "release gate"))

        feature = copy.deepcopy(self.contract)
        next(
            record
            for record in feature["required_features"]
            if record["id"] == "rod_bolt_through_hole"
        )["representation"] = "positive_solid"
        mutations.append(("rod_bolt_through_hole", feature, "representation mismatch"))

        source_refs = copy.deepcopy(self.contract)
        del source_refs["parameter_register"]["beam_height_mm"]["source_refs"]
        mutations.append(("missing_source_refs", source_refs, "source_refs"))

        pair_formula = copy.deepcopy(self.contract)
        pair_formula["pair_topology_audit"]["formula"] = "required_span_mm = rod_width_mm"
        mutations.append(("pair_formula", pair_formula, "formula mismatch"))

        for name, payload, expected_fragment in mutations:
            with self.subTest(name=name):
                errors = self.validator.validate(ROOT, self.temporary_contract(payload))
                self.assertTrue(any(expected_fragment in error for error in errors), errors)

    def test_validator_closes_nested_schemas_and_non_snapshot_values(self):
        mutations = []
        for section, mutate, expected_fragment in (
            (
                "source_binding",
                lambda payload: payload["source_bindings"][0].update({"escape": True}),
                "exact binding keys",
            ),
            (
                "scope",
                lambda payload: payload["scope"].update({"escape": True}),
                "exact closed F44 schema",
            ),
            (
                "parameter_record",
                lambda payload: payload["parameter_register"]["beam_height_mm"].update({"escape": True}),
                "exact value/unit/classification/source_refs/note keys",
            ),
            (
                "unknown_record",
                lambda payload: payload["unknown_required_inputs"][0].update({"escape": True}),
                "exact id/value/classification keys",
            ),
            (
                "feature_record",
                lambda payload: payload["required_features"][0].update({"escape": True}),
                "exact id/count/representation keys",
            ),
            (
                "pair_audit",
                lambda payload: payload["pair_topology_audit"].update({"escape": True}),
                "exact closed F44 schema",
            ),
            (
                "output_policy",
                lambda payload: payload["output_policy"].update({"escape": True}),
                "exact fail-closed F44 policy",
            ),
        ):
            payload = copy.deepcopy(self.contract)
            mutate(payload)
            mutations.append((section, payload, expected_fragment))

        changed_value = copy.deepcopy(self.contract)
        changed_value["parameter_register"]["beam_height_mm"]["value"] = 29.0
        mutations.append(("non_snapshot_value", changed_value, "beam_height_mm: value changed"))

        changed_unit = copy.deepcopy(self.contract)
        changed_unit["parameter_register"]["beam_height_mm"]["unit"] = "cm"
        mutations.append(("parameter_unit", changed_unit, "unit must remain mm"))

        for name, payload, expected_fragment in mutations:
            with self.subTest(name=name):
                errors = self.validator.validate(ROOT, self.temporary_contract(payload))
                self.assertTrue(any(expected_fragment in error for error in errors), errors)

    def test_validator_rejects_measured_or_manufacturing_claims_in_comment_and_notes(self):
        comment = copy.deepcopy(self.contract)
        comment["$comment"] = "Dimensions mesurées et pièce autorisée pour fabrication."
        errors = self.validator.validate(ROOT, self.temporary_contract(comment))
        self.assertTrue(any("$comment" in error for error in errors), errors)

        note = copy.deepcopy(self.contract)
        note["parameter_register"]["beam_height_mm"]["note"] = (
            "Dimension mesurée; fabrication métallique autorisée."
        )
        errors = self.validator.validate(ROOT, self.temporary_contract(note))
        self.assertTrue(any("notes differ" in error for error in errors), errors)

    def test_geometry_report_checks_require_positive_ligaments_and_cutter_intersections(self):
        valid_checks = {
            "minimum_ligament_mm": 1.0,
            "bolt_hole_cutter_body_intersection_mm3": 2.0,
            "bolt_hole_cutter_cap_intersection_mm3": 3.0,
            "oil_channel_cutter_body_intersection_mm3": 4.0,
            "unintended_fastener_interference_mm3": 0.0,
            "spotface_cutter_minimum_intersection_mm3": 5.0,
            "spotface_cutter_maximum_depth_delta_mm": 0.0,
            "spotface_post_subtraction_maximum_residual_mm3": 0.0,
            "oil_channel_cutter_bearing_upper_intersection_mm3": 1.0,
            "oil_channel_cutter_bearing_lower_intersection_mm3": 1.0,
            "oil_channel_cutter_bushing_intersection_mm3": 1.0,
            "oil_channel_big_end_bore_opening_mm3": 1.0,
            "oil_channel_small_end_bore_opening_mm3": 1.0,
            "oil_channel_big_end_outer_exit_probe_mm3": 1.0,
            "oil_channel_big_end_outer_exit_depth_delta_mm": 0.0,
            "oil_channel_connected_component_count": 1,
            "oil_channel_post_subtraction_maximum_residual_mm3": 0.0,
            "bearing_cap_split_gap_delta_mm": 0.0,
        }
        self.smoke.verify_geometry_checks({"geometry_checks": valid_checks})
        for key in (
            "minimum_ligament_mm",
            "bolt_hole_cutter_body_intersection_mm3",
            "bolt_hole_cutter_cap_intersection_mm3",
            "oil_channel_cutter_body_intersection_mm3",
            "spotface_cutter_minimum_intersection_mm3",
            "oil_channel_cutter_bearing_upper_intersection_mm3",
            "oil_channel_cutter_bearing_lower_intersection_mm3",
            "oil_channel_cutter_bushing_intersection_mm3",
            "oil_channel_big_end_bore_opening_mm3",
            "oil_channel_small_end_bore_opening_mm3",
            "oil_channel_big_end_outer_exit_probe_mm3",
        ):
            with self.subTest(key=key):
                mutated = copy.deepcopy(valid_checks)
                mutated[key] = 0.0
                with self.assertRaisesRegex(RuntimeError, "geometry_check_not_positive"):
                    self.smoke.verify_geometry_checks({"geometry_checks": mutated})
        interference = copy.deepcopy(valid_checks)
        interference["unintended_fastener_interference_mm3"] = 0.001
        with self.assertRaisesRegex(RuntimeError, "geometry_check_residual_nonzero"):
            self.smoke.verify_geometry_checks({"geometry_checks": interference})
        disconnected = copy.deepcopy(valid_checks)
        disconnected["oil_channel_connected_component_count"] = 2
        with self.assertRaisesRegex(RuntimeError, "oil_channel_must_be_one_connected_component"):
            self.smoke.verify_geometry_checks({"geometry_checks": disconnected})
        incomplete = copy.deepcopy(valid_checks)
        del incomplete["minimum_ligament_mm"]
        with self.assertRaisesRegex(RuntimeError, "geometry_checks_schema_mismatch"):
            self.smoke.verify_geometry_checks({"geometry_checks": incomplete})

    def test_oil_channel_starts_beyond_big_end_bearing_outer_radius(self):
        source = BUILDER.read_text(encoding="utf-8")
        oil_tool = source.split("def oil_channel_tool", 1)[1].split(
            "def intersection_volume_mm3", 1
        )[0]
        self.assertIn(
            'bearing_outer = big_inner + parameter(contract, "big_end_bearing_shell_thickness_mm")',
            oil_tool,
        )
        self.assertIn("start = -bearing_outer - overlap", oil_tool)
        self.assertNotIn("start = -big_inner - overlap", oil_tool)

    def test_smoke_metric_comparison_is_fail_closed(self):
        baseline = {
            "valid": True,
            "solid_count": 1,
            "all_solids_positive_volume": True,
            "volume_mm3": 100.0,
            "bounds_min_mm": [-1.0, -2.0, -3.0],
            "bounds_max_mm": [1.0, 2.0, 3.0],
        }
        self.smoke.compare_metrics(
            copy.deepcopy(baseline),
            baseline,
            label="unit",
            volume_rel_tolerance=1e-8,
            volume_abs_tolerance_mm3=1e-4,
            bounds_abs_tolerance_mm=1e-6,
        )
        for field, value, message in (
            ("solid_count", 2, "solid_count_mismatch"),
            ("volume_mm3", 110.0, "volume_mismatch"),
            ("bounds_max_mm", [1.0, 2.0, 3.1], "bounds_mismatch"),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(baseline)
                mutated[field] = value
                with self.assertRaisesRegex(RuntimeError, message):
                    self.smoke.compare_metrics(
                        mutated,
                        baseline,
                        label="unit",
                        volume_rel_tolerance=1e-8,
                        volume_abs_tolerance_mm3=1e-4,
                        bounds_abs_tolerance_mm=1e-6,
                    )

    def test_stl_parser_proves_manifold_closure_and_opposite_edge_orientation(self):
        vertices = {
            "a": (0.0, 0.0, 0.0),
            "b": (1.0, 0.0, 0.0),
            "c": (0.0, 1.0, 0.0),
            "d": (0.0, 0.0, 1.0),
        }
        closed_faces = [
            (vertices["a"], vertices["c"], vertices["b"]),
            (vertices["a"], vertices["b"], vertices["d"]),
            (vertices["a"], vertices["d"], vertices["c"]),
            (vertices["b"], vertices["c"], vertices["d"]),
        ]
        metrics = self.smoke.triangle_mesh_metrics(closed_faces, label="closed-tetrahedron")
        self.assertTrue(metrics["valid"])
        self.assertTrue(metrics["manifold_closed"])
        self.assertTrue(metrics["consistently_oriented"])
        self.assertTrue(metrics["outward_oriented"])
        self.assertEqual(metrics["solid_count"], 1)

        with tempfile.TemporaryDirectory(prefix="f44-open-stl-") as directory:
            path = Path(directory) / "open-tetrahedron.stl"
            lines = ["solid open"]
            for triangle in closed_faces[:-1]:
                lines.extend(("facet normal 0 0 0", "outer loop"))
                lines.extend(f"vertex {x} {y} {z}" for x, y, z in triangle)
                lines.extend(("endloop", "endfacet"))
            lines.append("endsolid open")
            path.write_text("\n".join(lines) + "\n", encoding="ascii")
            parsed = self.smoke._stl_triangles(path)
            with self.assertRaisesRegex(RuntimeError, "stl_non_manifold_edge"):
                self.smoke.triangle_mesh_metrics(parsed, label=path.name)

        inconsistent = copy.deepcopy(closed_faces)
        inconsistent[-1] = tuple(reversed(inconsistent[-1]))
        with self.assertRaisesRegex(RuntimeError, "stl_inconsistent_edge_orientation"):
            self.smoke.triangle_mesh_metrics(inconsistent, label="inconsistent-tetrahedron")

    def test_stl_parser_rejects_global_inversion_without_breaking_multiple_solids(self):
        a = (0.0, 0.0, 0.0)
        b = (1.0, 0.0, 0.0)
        c = (0.0, 1.0, 0.0)
        d = (0.0, 0.0, 1.0)
        outward = [(a, c, b), (a, b, d), (a, d, c), (b, c, d)]
        inverted = [tuple(reversed(triangle)) for triangle in outward]
        with self.assertRaisesRegex(RuntimeError, "stl_inward_oriented_component"):
            self.smoke.triangle_mesh_metrics(inverted, label="inverted-closed-tetrahedron")

        translated = [
            tuple((x + 3.0, y, z) for x, y, z in triangle)
            for triangle in outward
        ]
        multi_metrics = self.smoke.triangle_mesh_metrics(
            outward + translated,
            label="two-outward-tetrahedra",
        )
        self.assertTrue(multi_metrics["valid"])
        self.assertTrue(multi_metrics["outward_oriented"])
        self.assertEqual(multi_metrics["solid_count"], 2)

    def test_smoke_reopens_both_neutral_and_mesh_exports_and_checks_provenance(self):
        source = SMOKE.read_text(encoding="utf-8")
        self.assertIn("shape_metrics(import_step(step))", source)
        self.assertIn("reopened_stl = stl_metrics(stl)", source)
        self.assertIn('authored = record.get("authored_metrics"', source)
        self.assertIn('canonical = record.get("canonical_metrics"', source)
        self.assertIn("report_contract_sha256_mismatch", source)
        self.assertIn("report_cad_runtime_provenance_mismatch", source)
        self.assertIn("report_source_provenance_mismatch", source)
        self.assertIn("step_sha256_mismatch", source)
        self.assertIn("stl_sha256_mismatch", source)

    def test_builder_keeps_build123d_lazy_and_models_subtractive_features(self):
        source = BUILDER.read_text(encoding="utf-8")
        prefix = source.split("def cylinder_x", maxsplit=1)[0]
        self.assertNotIn("import build123d", prefix)
        self.assertIn("outer = outer - hole", source)
        self.assertIn("outer = outer - channel", source)
        self.assertIn("bearing_before_channel = tube_x", source)
        self.assertIn("bushing_before_channel = tube_x", source)
        self.assertIn("clean_export_shape", source)

    def test_builder_audits_authored_shape_before_cleaning(self):
        source = BUILDER.read_text(encoding="utf-8")
        export_body = source.split("def export_shape(", 1)[1].split("def generate(", 1)[0]
        authored = "authored = shape_metrics(shape)"
        cleaned = "exportable = clean_export_shape(shape)"
        self.assertIn(authored, export_body)
        self.assertIn(cleaned, export_body)
        self.assertLess(export_body.index(authored), export_body.index(cleaned))
        self.assertIn('"authored_metrics": authored', export_body)
        self.assertIn('"created_metrics": created', export_body)
        self.assertIn('"clean_export_audit"', export_body)

    def test_make_target_runs_real_docker_smoke_with_separate_writable_work_mount(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        immutable_image = (
            "ghcr.io/cluster2600/3dprinting993-cad-author-f28@"
            "sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
        )
        self.assertIn(f"override F44_CAD_IMAGE := {immutable_image}", makefile)
        self.assertIn("override F44_OUTPUT := work/917-connecting-rod-cad-f44", makefile)
        target = makefile.split("917-connecting-rod-cad-f44: 917-connecting-rod-cad-f44-check", 1)[1]
        target = target.split("917-wave-action-f39-image-test:", 1)[0]
        self.assertIn("smoke_connecting_rod_cad_f44.py", target)
        self.assertIn('-e HOME=/tmp', target)
        self.assertIn('src="$(CURDIR)/twins",dst=/workspace/twins,readonly', target)
        self.assertIn('src="$(CURDIR)/work",dst=/workspace/work', target)
        self.assertIn('--output "/workspace/$(F44_OUTPUT)"', target)
        self.assertIn("test ! -L work", target)
        self.assertLess(target.index("test ! -L work"), target.index("docker run"))

        hostile_output = "work/f44;touch-F44_OUTPUT_INJECTION"
        hostile_image = "alpine;touch-F44_IMAGE_INJECTION"
        dry_run = subprocess.run(
            [
                "make",
                "-n",
                "917-connecting-rod-cad-f44",
                f"F44_OUTPUT={hostile_output}",
                f"F44_CAD_IMAGE={hostile_image}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        rendered = dry_run.stdout + dry_run.stderr
        self.assertNotIn("F44_OUTPUT_INJECTION", rendered)
        self.assertNotIn("F44_IMAGE_INJECTION", rendered)
        self.assertIn(immutable_image, rendered)
        self.assertIn('/workspace/work/917-connecting-rod-cad-f44', rendered)

    def test_generator_rejects_output_outside_project_work_before_loading_cad(self):
        with tempfile.TemporaryDirectory(prefix="f44-outside-") as directory:
            output = Path(directory) / "917-connecting-rod-cad-f44"
            with self.assertRaisesRegex(RuntimeError, "output_must_be_direct_child_of_work"):
                self.builder.generate(ROOT, CONTRACT, self.contract, output)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="f44-existing-output-") as directory:
            fake_root = Path(directory)
            output = fake_root / "work/917-connecting-rod-cad-f44"
            output.mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "output_already_exists"):
                self.builder.generate(fake_root, CONTRACT, self.contract, output)

    def test_output_symlink_is_rejected_before_loading_cad(self):
        with tempfile.TemporaryDirectory(prefix="f44-symlink-root-") as root_directory:
            with tempfile.TemporaryDirectory(prefix="f44-symlink-target-") as target_directory:
                fake_root = Path(root_directory)
                work = fake_root / "work"
                work.mkdir()
                output = work / "917-connecting-rod-cad-f44"
                output.symlink_to(target_directory, target_is_directory=True)
                with self.assertRaisesRegex(RuntimeError, "output_symlink_not_allowed"):
                    self.builder.generate(fake_root, CONTRACT, self.contract, output)

    def test_cli_validation_and_description_pass_without_cad_runtime(self):
        validation = subprocess.run(
            ["python3", str(VALIDATOR), "--project-root", str(ROOT), "--contract", str(CONTRACT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(validation.returncode, 0, validation.stderr)
        self.assertIn("validation passed", validation.stdout)
        description = subprocess.run(
            [
                "python3", str(BUILDER), "--project-root", str(ROOT), "--contract", str(CONTRACT),
                "--describe-only",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(description.returncode, 0, description.stderr)
        self.assertTrue(json.loads(description.stdout)["metadata"]["display_only"])


if __name__ == "__main__":
    unittest.main()
