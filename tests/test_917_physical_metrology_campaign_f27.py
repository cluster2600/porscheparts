import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/validate_physical_metrology_campaign_f27.py"
)
JSON_TEMPLATE = (
    ROOT
    / "twins/reference-917-engine/physical-metrology-campaign-f27.template.json"
)
CSV_TEMPLATE = (
    ROOT
    / "twins/reference-917-engine/physical-metrology-observations-f27.template.csv"
)


def load_module():
    spec = importlib.util.spec_from_file_location("metrology_campaign_917_f27", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def all_false(mapping):
    return all(value is False for value in mapping.values())


def rows_from_text(module, text):
    return list(csv.DictReader(io.StringIO(text), fieldnames=None))


class PhysicalMetrologyCampaign917F27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.template = cls.module.load_json_strict(JSON_TEMPLATE)
        cls.csv_rows = cls.module.load_csv_strict(CSV_TEMPLATE)

    def _complete_synthetic_packet(self, directory):
        record = copy.deepcopy(self.template)
        record["record_status"] = "campaign_execution_complete_pending_binding_review"
        record["campaign"].update(
            {
                "campaign_id": "SYNTHETIC-TEST-CAMPAIGN",
                "record_revision": "test-revision",
                "campaign_owner": "synthetic-owner",
                "metrology_lab": "synthetic-lab",
                "planned_start_utc": "2026-01-01T09:00:00Z",
                "protocol_frozen_at_utc": "2026-01-01T08:00:00Z",
            }
        )
        record["source_binding"].update(
            {
                "working_scan_sha256": self.module.SCAN_SHA256,
                "physical_asset_or_part_set_id": "SYNTHETIC-ASSET",
                "identity_status": "reviewed_complete",
            }
        )
        record["chain_of_custody"]["custody_id"] = "SYNTHETIC-CUSTODY"
        custody_times = (
            "2026-01-01T09:00:00Z",
            "2026-01-01T09:05:00Z",
            "2026-01-01T09:10:00Z",
            "2026-01-01T10:00:00Z",
            "2026-01-01T12:00:00Z",
            "2026-01-01T12:10:00Z",
        )
        for index, event in enumerate(record["chain_of_custody"]["events"]):
            event.update(
                {
                    "timestamp_utc": custody_times[index],
                    "actor_id": f"synthetic-actor-{index + 1}",
                    "location_or_system_id": "synthetic-location",
                    "input_identifier_or_sha256": f"synthetic-input-{index + 1}",
                    "output_identifier_or_sha256": f"synthetic-output-{index + 1}",
                    "witness_or_review_status": "accepted",
                }
            )
        record["chain_of_custody"]["events"][1][
            "output_identifier_or_sha256"
        ] = self.module.SCAN_SHA256
        record["environment"].update(
            {
                "temperature_instrument_id": "SYNTHETIC-THERMOMETER",
                "temperature_c": 20.0,
                "relative_humidity_percent": 50.0,
            }
        )
        for method in record["methods"]:
            selected = method["method_id"] in {"CMM", "MESH_INSPECTION"}
            method["selected"] = selected
            if selected:
                method.update(
                    {
                        "selection_justification": "synthetic validator fixture",
                        "instrument_or_software_id": (
                            "SYNTHETIC-CMM" if method["method_id"] == "CMM" else "SYNTHETIC-MESH"
                        ),
                        "software_name_version": "synthetic-version",
                        "operator_or_lab": "synthetic-lab",
                        "measurement_start_utc": "2026-01-01T10:00:00Z",
                        "measurement_end_utc": "2026-01-01T12:00:00Z",
                    }
                )

        for ordinal, control in enumerate(
            record["scale_protocol"]["controls"], start=1
        ):
            control.update(
                {
                    "physical_feature_id": f"synthetic-feature-{ordinal}",
                    "scan_region_token": f"synthetic-region-{ordinal}",
                    "feature_endpoint_definition": "synthetic matching endpoints",
                    "physical_method_id": "CMM",
                    "scan_method_id": "MESH_INSPECTION",
                    "independent_from_other_controls": True,
                    "status": "reviewed_complete",
                }
            )
        for budget in record["uncertainty_budgets"]:
            budget.update(
                {
                    "measurement_model": "synthetic ratio model",
                    "correlation_assumptions": self.module.UNCERTAINTY_CORRELATION_MODEL,
                    "maximum_relative_standard_uncertainty": 0.01,
                    "maximum_relative_repeatability_range": 0.01,
                    "predeclared_before_acquisition": True,
                    "status": "approved_before_acquisition",
                }
            )

        for ordinal, datum in enumerate(
            record["orientation_protocol"]["datums"], start=1
        ):
            datum.update(
                {
                    "physical_feature_id": f"synthetic-datum-feature-{ordinal}",
                    "scan_region_token": f"synthetic-datum-region-{ordinal}",
                    "physical_method_id": "CMM",
                    "scan_method_id": "MESH_INSPECTION",
                    "semantic_direction_rule": self.module.DATUM_DIRECTION_RULES[
                        datum["datum_id"]
                    ],
                    "status": "reviewed_complete",
                }
            )
            datum["fit_result"].update(
                {
                    "fit_residual_obj_units": 0.001,
                    "registration_residual_mm": 0.001,
                    "angular_standard_uncertainty_deg": 0.001,
                }
            )
            if datum["kind"] in {"axis", "plane"}:
                datum["fit_result"]["origin_obj_units"] = [0.0, 0.0, 0.0]
                datum["fit_result"]["direction_or_normal"] = (
                    [1.0, 0.0, 0.0] if datum["kind"] == "axis" else [0.0, 0.0, 1.0]
                )
            else:
                datum["fit_result"]["handedness_token"] = self.module.HANDEDNESS_TOKEN
                datum["fit_result"]["origin_obj_units"] = [0.0, 1.0, 0.0]
        record["orientation_protocol"]["scan_to_engine_transform"].update(
            {
                "scale_mm_per_obj_unit": 1.0,
                "rotation_matrix_3x3": [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                ],
                "translation_mm": [0.0, 0.0, 0.0],
                "status": "reviewed_complete",
            }
        )

        variant = record["variant_identification"]
        variant["selected_candidate_variant_id"] = variant[
            "allowed_candidate_variant_ids"
        ][0]
        variant["adjudication_status"] = "accepted_by_independent_review"
        for ordinal, evidence in enumerate(variant["identity_evidence"], start=1):
            evidence["independent_source_id"] = f"synthetic-source-{ordinal}"
            evidence["review_status"] = "accepted"
        reviews = record["independent_reviews"]
        reviews["metrology"].update(
            {
                "reviewer_id": "synthetic-metrology-reviewer",
                "decision": "accepted",
                "signed_at_utc": "2026-01-01T13:00:00Z",
            }
        )
        reviews["variant_engineering"].update(
            {
                "reviewer_id": "synthetic-engineering-reviewer",
                "decision": "accepted",
                "signed_at_utc": "2026-01-01T13:05:00Z",
            }
        )

        rows = copy.deepcopy(self.csv_rows)
        controls = {
            item["control_id"]: item
            for item in record["scale_protocol"]["controls"]
        }
        for row in rows:
            control = controls[row["control_id"]]
            row.update(
                {
                    "feature_id": control["physical_feature_id"],
                    "scan_region_token": control["scan_region_token"],
                    "setup_id": f"synthetic-{row['measurement_side']}-setup-{row['repetition_index']}",
                    "method_id": (
                        "CMM" if row["measurement_side"] == "physical" else "MESH_INSPECTION"
                    ),
                    "value": "100.0",
                    "standard_uncertainty": "0.01",
                    "temperature_c": "20.0",
                    "timestamp_utc": "2026-01-01T10:30:00Z",
                    "instrument_or_software_id": (
                        "SYNTHETIC-CMM"
                        if row["measurement_side"] == "physical"
                        else "SYNTHETIC-MESH"
                    ),
                    "operator_or_lab": "synthetic-lab",
                    "review_status": "accepted",
                }
            )

        evidence_ids = {}

        def evidence_id(path):
            if path not in evidence_ids:
                evidence_ids[path] = f"EV-{len(evidence_ids) + 1:03d}"
            return evidence_ids[path]

        def fill_refs(value, path=""):
            if isinstance(value, dict):
                for key, child in value.items():
                    child_path = f"{path}.{key}" if path else key
                    if key == "evidence_index":
                        continue
                    if key.endswith("_evidence_ref") or key == "evidence_ref":
                        if child is None:
                            value[key] = evidence_id(child_path)
                    else:
                        fill_refs(child, child_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    fill_refs(child, f"{path}[{index}]")

        fill_refs(record)
        for index, row in enumerate(rows):
            for field in (
                "calibration_or_validation_evidence_ref",
                "raw_evidence_ref",
            ):
                row[field] = evidence_id(f"csv[{index}].{field}")

        evidence_root = Path(directory) / "evidence"
        evidence_root.mkdir()
        entries = []
        for path, identifier in sorted(evidence_ids.items(), key=lambda item: item[1]):
            relative = f"{identifier}.txt"
            content = f"synthetic evidence for {path}\n".encode("utf-8")
            (evidence_root / relative).write_bytes(content)
            if path.startswith("csv["):
                field = path.rsplit(".", 1)[-1]
                kind = (
                    "calibration_or_validation"
                    if field == "calibration_or_validation_evidence_ref"
                    else "raw_measurement_data"
                )
            else:
                kind = self.module._expected_evidence_kind(record, path)
            entries.append(
                {
                    "evidence_id": identifier,
                    "kind": kind,
                    "relative_path": relative,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "contains_proprietary_or_sensitive_data": False,
                    "commit_allowed": False,
                }
            )
        record["evidence_index"] = entries
        seal_event = record["chain_of_custody"]["events"][5]
        seal_event["output_identifier_or_sha256"] = self.module.packet_seal_sha256(
            record, rows
        )
        for key in ("metrology", "variant_engineering"):
            record["independent_reviews"][key][
                "reviewed_acquisition_packet_sha256"
            ] = seal_event["output_identifier_or_sha256"]
        record["independent_reviews"]["final_envelope"][
            "generated_at_utc"
        ] = "2026-01-01T13:10:00Z"
        record["independent_reviews"]["final_envelope"][
            "sha256"
        ] = self.module.final_review_envelope_sha256(record, rows)
        return record, rows, evidence_root

    def _evaluate_packet(
        self, directory, record, rows, evidence_root, *, root=ROOT
    ):
        record_path = Path(directory) / "campaign-target.json"
        observations_path = Path(directory) / "observations-target.csv"
        record_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        observations_path.write_text(
            self.module.render_csv(rows), encoding="utf-8", newline=""
        )
        working_scan_path = Path(directory) / "working-scan.obj"
        if not working_scan_path.exists():
            working_scan_path.write_bytes(b"synthetic non-canonical scan fixture\n")
        # Une preimage synthetique du hash du scan reel n'existe pas. Les tests
        # de paquet isolent donc ce seul gate; le test dedie ci-dessous exerce
        # le lecteur/hash production et ses echecs.
        with mock.patch.object(
            self.module, "_verify_working_scan_file", return_value=None
        ):
            return self.module.evaluate_record(
                root,
                record,
                rows,
                evidence_root,
                record_path=record_path,
                observations_path=observations_path,
                working_scan_path=working_scan_path,
            )

    def test_canonical_templates_are_deterministic_empty_and_fail_closed(self):
        self.assertEqual(self.module.build_json_template(ROOT), self.template)
        self.assertEqual(self.module.build_csv_rows(), self.csv_rows)
        report = self.module.check_templates_report(ROOT)
        self.assertEqual(report["report_status"], "passed_fail_closed")
        self.assertEqual(report["errors"], [])
        self.assertFalse(report["template_contains_measurements"])
        self.assertFalse(report["template_contains_proprietary_geometry"])
        self.assertTrue(all_false(report["release_gates"]))

    def test_upstream_audit_preserves_f13_f16_f21_authority_boundaries(self):
        self.assertEqual(self.module.validate_upstreams(ROOT), [])
        self.assertEqual(
            [item["id"] for item in self.template["upstream_manifest"]],
            ["f13_scan_metrology", "f16_kinematic_interfaces", "f21_scale_orientation"],
        )
        self.assertFalse(
            self.template["authority_boundary"][
                "documentary_dimensions_may_calibrate_scan"
            ]
        )
        self.assertFalse(
            self.template["authority_boundary"][
                "numerical_closest_candidate_may_select_variant"
            ]
        )
        self.assertFalse(
            self.template["authority_boundary"][
                "validator_may_open_engineering_release_gates"
            ]
        )
        self.assertTrue(
            self.template["repository_content_boundary"][
                "filled_record_and_evidence_must_remain_outside_git"
            ]
        )

    def test_csv_has_three_independent_paired_controls_and_no_values(self):
        self.assertEqual(len(self.csv_rows), 18)
        for control_id in self.module.SCALE_CONTROL_IDS:
            selected = [row for row in self.csv_rows if row["control_id"] == control_id]
            self.assertEqual(len(selected), 6)
            self.assertEqual(
                {row["measurement_side"] for row in selected}, {"physical", "scan"}
            )
            for side in ("physical", "scan"):
                self.assertEqual(
                    {row["repetition_index"] for row in selected if row["measurement_side"] == side},
                    {"1", "2", "3"},
                )
        for row in self.csv_rows:
            self.assertEqual(row["value"], "")
            self.assertEqual(row["standard_uncertainty"], "")
            self.assertEqual(row["feature_id"], "")

    def test_blank_templates_cannot_be_accepted_as_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary) / "evidence"
            evidence_root.mkdir()
            report = self._evaluate_packet(
                temporary, self.template, self.csv_rows, evidence_root
            )
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn("campaign_record_status_incomplete", report["errors"])
        self.assertIn("exact_working_scan_sha256_required", report["errors"])
        self.assertIn("three_distinct_physical_features_required", report["errors"])
        self.assertTrue(all_false(report["release_gates"]))
        self.assertFalse(report["claims"]["scan_variant_bound"])

    def test_synthetic_complete_packet_is_only_ready_for_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertEqual(report["errors"], [])
        self.assertEqual(
            report["report_status"],
            "ready_for_independent_binding_review_gates_closed",
        )
        self.assertTrue(report["claims"]["campaign_packet_structurally_complete"])
        self.assertFalse(report["claims"]["scan_variant_bound"])
        self.assertFalse(report["claims"]["cad_input_authorized"])
        self.assertFalse(report["claims"]["physicsnemo_authorized"])
        self.assertTrue(all_false(report["release_gates"]))
        metrics = report["derived_screening_metrics_not_release_authority"]
        self.assertEqual(metrics["relative_scale_spread"], 0.0)
        self.assertEqual(
            {item["scale_mm_per_obj_unit"] for item in metrics["controls"].values()},
            {1.0},
        )

    def test_duplicate_feature_region_or_setup_fails_independence(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            controls = record["scale_protocol"]["controls"]
            controls[1]["physical_feature_id"] = controls[0]["physical_feature_id"]
            controls[1]["scan_region_token"] = controls[0]["scan_region_token"]
            for row in rows:
                if row["control_id"] == "SC-02":
                    row["feature_id"] = controls[1]["physical_feature_id"]
                    row["scan_region_token"] = controls[1]["scan_region_token"]
            rows[1]["setup_id"] = rows[0]["setup_id"]
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn("three_distinct_physical_features_required", report["errors"])
        self.assertIn("three_distinct_scan_regions_required", report["errors"])
        self.assertIn("independent_repeat_setups_required:SC-01.physical", report["errors"])
        self.assertTrue(all_false(report["release_gates"]))

    def test_scale_spread_and_uncertainty_limits_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            for row in rows:
                if row["control_id"] == "SC-03" and row["measurement_side"] == "physical":
                    row["value"] = "102.0"
            record["uncertainty_budgets"][0][
                "maximum_relative_standard_uncertainty"
            ] = 0.000001
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn("f21_relative_scale_spread_exceeded", report["errors"])
        self.assertIn(
            "relative_uncertainty_exceeds_predeclared_limit:SC-01",
            report["errors"],
        )
        self.assertIn("transform_scale_must_equal_mean_of_three_controls", report["errors"])
        self.assertTrue(all_false(report["release_gates"]))

    def test_variant_custody_review_and_orientation_are_not_automatic(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["variant_identification"]["selected_candidate_variant_id"] = "invented_variant"
            record["variant_identification"]["f16_branch_crosswalk_evidence_ref"] = None
            record["independent_reviews"]["variant_engineering"]["reviewer_id"] = (
                record["independent_reviews"]["metrology"]["reviewer_id"]
            )
            record["orientation_protocol"]["scan_to_engine_transform"][
                "rotation_matrix_3x3"
            ][2][2] = -1.0
            record["campaign"]["protocol_frozen_at_utc"] = "2026-01-01T11:00:00Z"
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn("selected_variant_not_in_f13_candidate_registry", report["errors"])
        self.assertIn("f16_branch_crosswalk_evidence_required", report["errors"])
        self.assertIn("independent_reviewers_must_be_distinct", report["errors"])
        self.assertIn("rotation_matrix_must_be_right_handed", report["errors"])
        self.assertIn("protocol_must_be_frozen_before_first_observation", report["errors"])
        self.assertTrue(all_false(report["release_gates"]))

    def test_evidence_digest_path_and_release_injection_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["evidence_index"][0]["sha256"] = "0" * 64
            record["evidence_index"][1]["relative_path"] = "../escape"
            record["release_gates"]["physicsnemo_training_authorized"] = True
            record["current_readiness"]["campaign_executed"] = True
            record["campaign"]["invented_authority"] = True
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertTrue(
            any(error.startswith("evidence_sha256_mismatch:") for error in report["errors"])
        )
        self.assertTrue(
            any(error.startswith("unsafe_evidence_relative_path:") for error in report["errors"])
        )
        self.assertIn("all_release_gates_must_remain_false", report["errors"])
        self.assertIn("record_readiness_flags_must_remain_false", report["errors"])
        self.assertIn("record_keys_mismatch:campaign", report["errors"])
        self.assertTrue(all_false(report["release_gates"]))

    def test_duplicate_json_key_and_csv_header_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            duplicate = Path(temporary) / "duplicate.json"
            duplicate.write_text('{"phase":"F27","phase":"F28"}\n', encoding="utf-8")
            with self.assertRaises(self.module.DuplicateKeyError):
                self.module.load_json_strict(duplicate)
            bad_csv = Path(temporary) / "bad.csv"
            bad_csv.write_text("unexpected\nvalue\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "csv_header_mismatch"):
                self.module.load_csv_strict(bad_csv)

    def test_nonfinite_json_symlink_and_nonregular_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"value":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non_finite_json_number_forbidden"):
                self.module.load_json_strict(nonfinite)
            overflow = root / "overflow.json"
            overflow.write_text('{"value":1e400}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non_finite_json_number_forbidden"):
                self.module.load_json_strict(overflow)

            target = root / "target.json"
            target.write_text('{"value":null}\n', encoding="utf-8")
            symlink = root / "symlink.json"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlink_input_forbidden"):
                self.module.load_json_strict(symlink)
            with self.assertRaisesRegex(ValueError, "symlink_hash_input_forbidden"):
                self.module.sha256_file(symlink)

            with self.assertRaisesRegex(ValueError, "regular_file_required"):
                self.module._read_regular_file(root, 1024)

    def test_working_scan_requires_a_real_exact_regular_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "working-scan.obj"
            scan.write_bytes(b"not the canonical scan\n")
            errors = []
            self.module._verify_working_scan_file(scan, errors)
            self.assertEqual(errors, ["working_scan_file_sha256_mismatch"])

            scan_link = root / "working-scan-link.obj"
            scan_link.symlink_to(scan)
            errors = []
            self.module._verify_working_scan_file(scan_link, errors)
            self.assertEqual(errors, ["working_scan_file_unreadable:ValueError"])

            errors = []
            with mock.patch.object(
                self.module,
                "sha256_file",
                return_value=self.module.SCAN_SHA256,
            ):
                self.module._verify_working_scan_file(scan, errors)
            self.assertEqual(errors, [])

    def test_descriptor_change_during_read_or_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.json"
            source.write_text('{"value":null}\n', encoding="utf-8")
            real_fstat = self.module.os.fstat

            def changing_fstat_factory():
                calls = 0

                def changing_fstat(descriptor):
                    nonlocal calls
                    calls += 1
                    observed = real_fstat(descriptor)
                    if calls == 2:
                        return types.SimpleNamespace(
                            st_mode=observed.st_mode,
                            st_size=observed.st_size,
                            st_dev=observed.st_dev,
                            st_ino=observed.st_ino,
                            st_mtime_ns=observed.st_mtime_ns + 1,
                        )
                    return observed

                return changing_fstat

            with mock.patch.object(
                self.module.os, "fstat", side_effect=changing_fstat_factory()
            ):
                with self.assertRaisesRegex(ValueError, "input_changed_during_read"):
                    self.module._read_regular_file(source, 1024)

            with mock.patch.object(
                self.module.os, "fstat", side_effect=changing_fstat_factory()
            ):
                with self.assertRaisesRegex(ValueError, "hash_input_changed_during_read"):
                    self.module.sha256_file(source)

    def test_approved_upstream_hashes_cannot_be_rebased_by_packet(self):
        with tempfile.TemporaryDirectory() as upstream_temporary, tempfile.TemporaryDirectory() as packet_temporary:
            upstream_root = Path(upstream_temporary)
            for relative in self.module.UPSTREAMS.values():
                destination = upstream_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            f21_path = upstream_root / self.module.UPSTREAMS["f21_scale_orientation"]
            f21 = json.loads(f21_path.read_text(encoding="utf-8"))
            f21["acquisition_record_policy"][
                "same_feature_scan_to_physical_correspondence_required"
            ] = False
            f21_path.write_text(
                json.dumps(f21, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            upstream_errors = self.module.validate_upstreams(upstream_root)
            self.assertIn(
                "approved_upstream_sha256_mismatch:f21_scale_orientation",
                upstream_errors,
            )
            self.assertIn(
                "f21_acquisition_policy_invariant_mismatch:same_feature_scan_to_physical_correspondence_required",
                upstream_errors,
            )

            record, rows, evidence_root = self._complete_synthetic_packet(
                packet_temporary
            )
            record["upstream_manifest"] = self.module._upstream_manifest(upstream_root)
            report = self._evaluate_packet(
                packet_temporary,
                record,
                rows,
                evidence_root,
                root=upstream_root,
            )
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn(
            "approved_upstream_sha256_mismatch:f21_scale_orientation",
            report["errors"],
        )

    def test_each_upstream_is_hash_bound_and_parsed_from_one_descriptor_read(self):
        real_reader = self.module._read_regular_file
        with mock.patch.object(
            self.module,
            "_read_regular_file",
            wraps=real_reader,
        ) as reader, mock.patch.object(
            self.module,
            "sha256_file",
            side_effect=AssertionError("second pathname open forbidden"),
        ):
            self.assertEqual(self.module.validate_upstreams(ROOT), [])
        self.assertEqual(reader.call_count, len(self.module.UPSTREAMS))

    def test_reviews_must_follow_seal_and_be_independent_from_campaign(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["independent_reviews"]["metrology"].update(
                {
                    "reviewer_id": record["campaign"]["campaign_owner"],
                    "signed_at_utc": "2025-01-01T00:00:00Z",
                }
            )
            record["independent_reviews"]["variant_engineering"].update(
                {
                    "reviewer_id": "synthetic-lab",
                    "signed_at_utc": "2025-01-01T00:00:01Z",
                }
            )
            for method in record["methods"]:
                if method["selected"]:
                    method["operator_or_lab"] = "synthetic-technician"
            for row in rows:
                row["operator_or_lab"] = "synthetic-technician"
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = self.module.packet_seal_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn(
            "independent_review_must_follow_packet_seal:metrology", report["errors"]
        )
        self.assertIn(
            "independent_review_must_follow_packet_seal:variant_engineering",
            report["errors"],
        )
        self.assertIn("independent_reviewer_role_conflict:metrology", report["errors"])
        self.assertIn(
            "independent_reviewer_role_conflict:variant_engineering", report["errors"]
        )

    def test_unknown_correlation_uses_conservative_uncertainty_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            for budget in record["uncertainty_budgets"]:
                budget["maximum_relative_standard_uncertainty"] = 0.005
            for row in rows:
                row["standard_uncertainty"] = "0.6"
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = self.module.packet_seal_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        for control_id in self.module.SCALE_CONTROL_IDS:
            self.assertIn(
                f"relative_uncertainty_exceeds_predeclared_limit:{control_id}",
                report["errors"],
            )
            self.assertAlmostEqual(
                report["derived_screening_metrics_not_release_authority"]["controls"][
                    control_id
                ]["relative_standard_uncertainty"],
                0.012,
            )

    def test_evidence_roles_and_packet_seal_reject_one_file_collapse(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            reused_id = record["evidence_index"][0]["evidence_id"]

            def collapse_refs(value):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key == "evidence_index":
                            continue
                        if key.endswith("_evidence_ref") or key == "evidence_ref":
                            if child is not None:
                                value[key] = reused_id
                        else:
                            collapse_refs(child)
                elif isinstance(value, list):
                    for child in value:
                        collapse_refs(child)

            collapse_refs(record)
            for row in rows:
                row["calibration_or_validation_evidence_ref"] = reused_id
                row["raw_evidence_ref"] = reused_id
            record["evidence_index"] = [record["evidence_index"][0]]
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = self.module.packet_seal_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertTrue(
            any(
                error.startswith("evidence_kind_role_mismatch:")
                for error in report["errors"]
            )
        )
        self.assertIn(
            f"evidence_id_reused_across_incompatible_roles:{reused_id}",
            report["errors"],
        )
        self.assertIn(
            "variant_identity_evidence_files_must_be_distinct", report["errors"]
        )
        self.assertIn("independent_review_reports_must_be_distinct", report["errors"])

    def test_zero_byte_evidence_cannot_satisfy_any_role(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            empty_sha256 = hashlib.sha256(b"").hexdigest()
            for item in record["evidence_index"]:
                (evidence_root / item["relative_path"]).write_bytes(b"")
                item["sha256"] = empty_sha256
            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertEqual(
            len(
                [
                    error
                    for error in report["errors"]
                    if error.startswith("evidence_file_empty:")
                ]
            ),
            len(record["evidence_index"]),
        )

    def test_identity_and_review_artifacts_require_distinct_content_digests(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            identity_ids = {
                item["evidence_ref"]
                for item in record["variant_identification"]["identity_evidence"]
            }
            review_ids = {
                record["independent_reviews"][key]["signed_report_evidence_ref"]
                for key in ("metrology", "variant_engineering")
            }
            entries = {
                item["evidence_id"]: item for item in record["evidence_index"]
            }
            for identifiers, content in (
                (identity_ids, b"same identity artifact\n"),
                (review_ids, b"same signed review artifact\n"),
            ):
                digest = hashlib.sha256(content).hexdigest()
                for evidence_id in identifiers:
                    item = entries[evidence_id]
                    (evidence_root / item["relative_path"]).write_bytes(content)
                    item["sha256"] = digest
            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn(
            "variant_identity_evidence_digests_must_be_distinct", report["errors"]
        )
        self.assertIn(
            "independent_review_report_digests_must_be_distinct", report["errors"]
        )

    def test_same_digest_cannot_be_laundered_across_evidence_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            evidence_ids = (
                record["campaign"]["preacquisition_approval_evidence_ref"],
                record["source_binding"][
                    "physical_asset_serial_or_marking_evidence_ref"
                ],
            )
            entries = {
                item["evidence_id"]: item for item in record["evidence_index"]
            }
            content = b"same bytes copied across incompatible roles\n"
            digest = hashlib.sha256(content).hexdigest()
            for evidence_id in evidence_ids:
                item = entries[evidence_id]
                (evidence_root / item["relative_path"]).write_bytes(content)
                item["sha256"] = digest
            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn(
            f"evidence_digest_reused_across_incompatible_roles:{digest}",
            report["errors"],
        )

    def test_packet_seal_binds_record_csv_and_evidence_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            rows[0]["value"] = "100.1"
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn("custody_packet_seal_sha256_mismatch", report["errors"])
        self.assertIn("final_review_envelope_sha256_mismatch", report["errors"])

    def test_acquisition_seal_is_constructible_before_post_seal_reviews(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, _ = self._complete_synthetic_packet(temporary)
            acquisition_digest = record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ]
            pre_review_record = copy.deepcopy(record)
            review_evidence_ids = {
                pre_review_record["independent_reviews"][key][
                    "signed_report_evidence_ref"
                ]
                for key in ("metrology", "variant_engineering")
            }
            pre_review_record["independent_reviews"] = copy.deepcopy(
                self.template["independent_reviews"]
            )
            pre_review_record["evidence_index"] = [
                item
                for item in pre_review_record["evidence_index"]
                if item["evidence_id"] not in review_evidence_ids
            ]
            pre_review_record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = None
            self.assertEqual(
                self.module.packet_seal_sha256(pre_review_record, rows),
                acquisition_digest,
            )
            for key in ("metrology", "variant_engineering"):
                self.assertEqual(
                    record["independent_reviews"][key][
                        "reviewed_acquisition_packet_sha256"
                    ],
                    acquisition_digest,
                )
            self.assertEqual(
                record["independent_reviews"]["final_envelope"]["sha256"],
                self.module.final_review_envelope_sha256(record, rows),
            )

    def test_datum_relationships_handedness_and_transform_are_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            datums = record["orientation_protocol"]["datums"]
            datums[1]["fit_result"]["direction_or_normal"] = [1.0, 0.0, 0.0]
            datums[2]["fit_result"]["handedness_token"] = "arbitrary"
            datums[2]["fit_result"]["origin_obj_units"] = [0.0, -1.0, 0.0]
            datums[0]["fit_result"]["origin_obj_units"] = [1.0, 0.0, 0.0]
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = self.module.packet_seal_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn(
            "primary_axis_secondary_plane_relation_degenerate", report["errors"]
        )
        self.assertIn(
            "orientation_handedness_token_mismatch:OR-HANDEDNESS", report["errors"]
        )
        self.assertIn("transform_secondary_plane_row_mismatch", report["errors"])
        self.assertIn("transform_translation_origin_mapping_mismatch", report["errors"])
        self.assertIn("handedness_witness_not_on_positive_engine_y", report["errors"])

    def test_static_slot_budget_registry_and_review_roles_are_immutable(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            for control in record["scale_protocol"]["controls"]:
                control["f21_slot_ref"] = "BOGUS"
                control["uncertainty_budget_id"] = "BOGUS"
            for budget in record["uncertainty_budgets"]:
                budget["budget_id"] = "OTHER"
            for datum in record["orientation_protocol"]["datums"]:
                datum["f21_slot_ref"] = "BOGUS"
            record["variant_identification"]["candidate_registry_source"] = (
                "invented.json"
            )
            record["independent_reviews"]["metrology"]["role"] = "invented"
            record["independent_reviews"]["variant_engineering"]["role"] = (
                "invented"
            )
            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        for control_id in self.module.SCALE_CONTROL_IDS:
            self.assertIn(f"f21_scale_slot_ref_mismatch:{control_id}", report["errors"])
            self.assertIn(
                f"scale_uncertainty_budget_link_mismatch:{control_id}", report["errors"]
            )
            self.assertIn(
                f"uncertainty_budget_id_mismatch:{control_id}", report["errors"]
            )
        for datum_id, _, _ in self.module.DATUM_DEFINITIONS:
            self.assertIn(
                f"f21_orientation_slot_ref_mismatch:{datum_id}", report["errors"]
            )
        self.assertIn("variant_candidate_registry_source_mismatch", report["errors"])
        self.assertIn("independent_review_role_mismatch:metrology", report["errors"])
        self.assertIn(
            "independent_review_role_mismatch:variant_engineering", report["errors"]
        )

    def test_independence_identifiers_reject_whitespace_and_unicode_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            aliases = ["same", " same", "same "]
            for control, alias in zip(record["scale_protocol"]["controls"], aliases):
                control["physical_feature_id"] = alias
                control["scan_region_token"] = alias
            controls = {
                item["control_id"]: item
                for item in record["scale_protocol"]["controls"]
            }
            for row in rows:
                control = controls[row["control_id"]]
                row["feature_id"] = control["physical_feature_id"]
                row["scan_region_token"] = control["scan_region_token"]
                repetition = int(row["repetition_index"])
                row["setup_id"] = aliases[repetition - 1]
            for item, alias in zip(
                record["variant_identification"]["identity_evidence"],
                ["source", " source", "source ", "\u0065\u0301"],
            ):
                item["independent_source_id"] = alias
            record["independent_reviews"]["metrology"]["reviewer_id"] = (
                " synthetic-owner"
            )
            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn("three_distinct_physical_features_required", report["errors"])
        self.assertIn("three_distinct_scan_regions_required", report["errors"])
        self.assertTrue(
            any(
                error.startswith("canonical_identifier_required:")
                for error in report["errors"]
            )
        )
        self.assertIn(
            "independent_repeat_setups_required:SC-01.physical", report["errors"]
        )
        self.assertIn("variant_identity_sources_must_be_independent", report["errors"])
        self.assertIn("independent_reviewer_role_conflict:metrology", report["errors"])

    def test_malformed_nested_records_and_strict_utc_fail_without_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["methods"].append(None)
            record["variant_identification"]["identity_evidence"].append(None)
            record["independent_reviews"]["metrology"] = None
            record["orientation_protocol"]["scan_to_engine_transform"][
                "translation_mm"
            ] = ["bad", 0.0, 0.0]
            record["scale_protocol"]["controls"][0]["physical_method_id"] = []
            record["scale_protocol"]["controls"][0]["scan_method_id"] = []
            record["orientation_protocol"]["datums"][0][
                "physical_method_id"
            ] = []
            rows[0]["control_id"] = "UNKNOWN"
            rows[1]["measurement_side"] = "BOGUS"
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn("record_fixed_list_length_mismatch:methods", report["errors"])
        self.assertIn("method_registry_mismatch", report["errors"])
        self.assertIn(
            "variant_identity_evidence_registry_mismatch", report["errors"]
        )
        self.assertIn("independent_review_registry_mismatch", report["errors"])
        self.assertIn("translation_vector_mm_required", report["errors"])
        self.assertIn("physical_method_invalid:SC-01", report["errors"])
        self.assertIn(
            "orientation_physical_method_invalid_or_unselected:OR-PRIMARY-AXIS",
            report["errors"],
        )
        self.assertIn(
            "unexpected_csv_control_id:SC-01-PHYSICAL-01", report["errors"]
        )
        self.assertIn(
            "unexpected_csv_measurement_side:SC-01-PHYSICAL-02", report["errors"]
        )

    def test_non_string_nested_evidence_refs_fail_without_type_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["variant_identification"]["identity_evidence"][0][
                "evidence_ref"
            ] = []
            record["independent_reviews"]["metrology"][
                "signed_report_evidence_ref"
            ] = []
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn(
            "variant_identity_evidence_files_must_be_distinct", report["errors"]
        )
        self.assertIn("independent_review_reports_must_be_distinct", report["errors"])

    def test_non_string_nested_evidence_digests_fail_without_type_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            identity_ref = record["variant_identification"]["identity_evidence"][0][
                "evidence_ref"
            ]
            review_ref = record["independent_reviews"]["metrology"][
                "signed_report_evidence_ref"
            ]
            evidence = {
                item["evidence_id"]: item for item in record["evidence_index"]
            }
            evidence[identity_ref]["sha256"] = []
            evidence[review_ref]["sha256"] = []
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn("variant_identity_evidence_digests_must_be_distinct", report["errors"])
        self.assertIn("independent_review_report_digests_must_be_distinct", report["errors"])

    def test_evidence_hardlink_to_packet_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record_path = directory / "campaign-target.json"
            observations_path = directory / "observations-target.csv"
            observations_path.write_text(
                self.module.render_csv(rows), encoding="utf-8", newline=""
            )
            working_scan_path = directory / "working-scan.obj"
            working_scan_path.write_bytes(b"synthetic non-canonical scan fixture\n")

            approval_ref = record["campaign"][
                "preacquisition_approval_evidence_ref"
            ]
            evidence_entry = next(
                item
                for item in record["evidence_index"]
                if item["evidence_id"] == approval_ref
            )
            approval_path = evidence_root / evidence_entry["relative_path"]
            approval_path.unlink()
            os.link(observations_path, approval_path)
            evidence_entry["sha256"] = self.module.sha256_file(observations_path)

            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            record_path.write_text(
                json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                self.module, "_verify_working_scan_file", return_value=None
            ):
                report = self.module.evaluate_record(
                    ROOT,
                    record,
                    rows,
                    evidence_root,
                    record_path=record_path,
                    observations_path=observations_path,
                    working_scan_path=working_scan_path,
                )
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn(
            f"evidence_file_aliases_packet_input:{approval_ref}", report["errors"]
        )

    def test_protocol_freeze_equal_to_first_observation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["campaign"]["protocol_frozen_at_utc"] = rows[0]["timestamp_utc"]
            acquisition_digest = self.module.packet_seal_sha256(record, rows)
            record["chain_of_custody"]["events"][5][
                "output_identifier_or_sha256"
            ] = acquisition_digest
            for key in ("metrology", "variant_engineering"):
                record["independent_reviews"][key][
                    "reviewed_acquisition_packet_sha256"
                ] = acquisition_digest
            record["independent_reviews"]["final_envelope"][
                "sha256"
            ] = self.module.final_review_envelope_sha256(record, rows)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn(
            "protocol_must_be_frozen_before_first_observation", report["errors"]
        )

    def test_strict_utc_rejects_date_only_without_comparison_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            record["independent_reviews"]["metrology"]["signed_at_utc"] = (
                "2026-01-01Z"
            )
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn(
            "utc_timestamp_required:independent_reviews.metrology.signed_at_utc",
            report["errors"],
        )

    def test_real_packet_paths_must_be_outside_git_or_under_work(self):
        docs_root = ROOT / "docs"
        with tempfile.TemporaryDirectory(dir=docs_root) as temporary:
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            report = self._evaluate_packet(temporary, record, rows, evidence_root)
        self.assertIn(
            "packet_path_inside_repository_outside_work:campaign_record",
            report["errors"],
        )
        self.assertIn(
            "packet_path_inside_repository_outside_work:observations", report["errors"]
        )
        self.assertIn(
            "packet_path_inside_repository_outside_work:evidence_root", report["errors"]
        )

    def test_cli_rejects_record_and_evidence_root_symlink_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record, rows, evidence_root = self._complete_synthetic_packet(temporary)
            baseline = self._evaluate_packet(temporary, record, rows, evidence_root)
            self.assertEqual(
                baseline["report_status"],
                "ready_for_independent_binding_review_gates_closed",
            )
            record_path = root / "campaign-target.json"
            observations_path = root / "observations-target.csv"
            record_link = root / "campaign-link.json"
            evidence_link = root / "evidence-link"
            record_link.symlink_to(record_path)
            evidence_link.symlink_to(evidence_root, target_is_directory=True)
            for selected_record, selected_evidence in (
                (record_link, evidence_root),
                (record_path, evidence_link),
            ):
                checked = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--root",
                        str(ROOT),
                        "--record",
                        str(selected_record),
                        "--observations",
                        str(observations_path),
                        "--evidence-root",
                        str(selected_evidence),
                        "--working-scan",
                        str(root / "working-scan.obj"),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(checked.returncode, 0)
                self.assertEqual(json.loads(checked.stdout)["report_status"], "failed_closed")

    def test_cli_converts_csv_parser_limits_to_failed_closed_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observations = root / "oversized-field.csv"
            header = CSV_TEMPLATE.read_text(encoding="utf-8").splitlines()[0]
            observations.write_text(
                header + "\n" + ("x" * 200_000) + "\n", encoding="utf-8"
            )
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            working_scan = root / "working-scan.obj"
            working_scan.write_bytes(b"not the canonical scan\n")
            checked = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(ROOT),
                    "--record",
                    str(JSON_TEMPLATE),
                    "--observations",
                    str(observations),
                    "--evidence-root",
                    str(evidence_root),
                    "--working-scan",
                    str(working_scan),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(checked.returncode, 0)
        report = json.loads(checked.stdout)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertIn("unsafe_or_invalid_input:Error", report["errors"])

    def test_cli_checks_templates_and_blank_record_exits_nonzero(self):
        checked = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(ROOT), "--check-templates"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["report_status"], "passed_fail_closed")

        with tempfile.TemporaryDirectory() as temporary:
            working_scan = Path(temporary) / "working-scan.obj"
            working_scan.write_bytes(b"not the canonical scan\n")
            blank = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(ROOT),
                    "--record",
                    str(JSON_TEMPLATE),
                    "--observations",
                    str(CSV_TEMPLATE),
                    "--evidence-root",
                    temporary,
                    "--working-scan",
                    str(working_scan),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(blank.returncode, 0)
        report = json.loads(blank.stdout)
        self.assertEqual(report["report_status"], "failed_closed")
        self.assertTrue(all_false(report["release_gates"]))


if __name__ == "__main__":
    unittest.main()
