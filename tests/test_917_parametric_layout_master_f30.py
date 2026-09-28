import copy
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/build_parametric_layout_master_f30.py"
)
TEMPLATE = (
    ROOT
    / "twins/reference-917-engine/parametric-layout-authoring-f30.template.json"
)
F27_JSON_TEMPLATE = (
    ROOT
    / "twins/reference-917-engine/physical-metrology-campaign-f27.template.json"
)
F27_CSV_TEMPLATE = (
    ROOT
    / "twins/reference-917-engine/physical-metrology-observations-f27.template.csv"
)


def load_module():
    spec = importlib.util.spec_from_file_location("parametric_layout_917_f30", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ParametricLayoutMaster917F30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        (ROOT / "work").mkdir(exist_ok=True)
        cls.allowed_output_root = ROOT / "work/917-engine/cad/f30"
        cls.allowed_output_root.mkdir(parents=True, exist_ok=True)

    def _ready_f27_report(self):
        return {
            "schema_version": "1.0.0",
            "phase": "F27",
            "report_status": "ready_for_independent_binding_review_gates_closed",
            "errors": [],
            "claims": {
                "campaign_packet_structurally_complete": True,
                "scan_variant_bound": False,
                "cad_input_authorized": False,
                "solver_authorized": False,
                "physicsnemo_authorized": False,
                "fabrication_authorized": False,
            },
            "release_gates": {
                gate_id: False for gate_id in self.module.F27_RELEASE_GATE_IDS
            },
        }

    def _plane(self, identifier, origin, normal, evidence_ref):
        return {
            "id": identifier,
            "datum_ref": "ENGINE-FRAME-F30",
            "origin_mm": origin,
            "normal": normal,
            "u_direction": [1.0, 0.0, 0.0],
            "extent_u_mm": 700.0,
            "extent_v_mm": 300.0,
            "position_standard_uncertainty_mm": 0.1,
            "angular_standard_uncertainty_deg": 0.1,
            "evidence_ref": evidence_ref,
        }

    def _fixture(self, base):
        base = Path(base)
        f27_evidence_root = base / "f27-evidence"
        layout_evidence_root = base / "layout-evidence"
        f27_evidence_root.mkdir()
        layout_evidence_root.mkdir()
        (f27_evidence_root / "placeholder.txt").write_text(
            "synthetic F27 evidence\n", encoding="utf-8"
        )

        evidence_specs = (
            ("EV-FRAME", "engine_coordinate_frame_fit"),
            ("EV-CRANK", "crankshaft_axis_fit"),
            ("EV-SPLIT", "crankcase_split_plane_fit"),
            ("EV-DECK", "bank_deck_plane_fit"),
            ("EV-CYL", "cylinder_axis_fit"),
            ("EV-BEARING", "main_bearing_station_fit"),
            ("EV-BEARING-COUNT", "main_bearing_count_report"),
        )
        evidence_index = []
        for evidence_id, kind in evidence_specs:
            relative_path = f"{evidence_id}.txt"
            payload = f"synthetic {kind}\n".encode("utf-8")
            (layout_evidence_root / relative_path).write_bytes(payload)
            evidence_index.append(
                {
                    "evidence_id": evidence_id,
                    "kind": kind,
                    "relative_path": relative_path,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "contains_proprietary_or_sensitive_data": False,
                    "commit_allowed": False,
                }
            )

        transform = {
            "scale_mm_per_obj_unit": 1.0,
            "rotation_matrix_3x3": [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            "translation_mm": [0.0, 0.0, 0.0],
            "status": "reviewed_complete",
        }
        record = {
            "campaign": {"campaign_id": "SYNTHETIC-F30-CAMPAIGN"},
            "source_binding": {
                "working_scan_sha256": self.module.SCAN_SHA256,
            },
            "variant_identification": {
                "selected_candidate_variant_id": "917_5_0_na",
            },
            "orientation_protocol": {
                "scan_to_engine_transform": transform,
            },
            "independent_reviews": {
                "metrology": {
                    "reviewer_id": "F27-METROLOGY-REVIEWER",
                    "signed_at_utc": "2026-01-01T13:00:00Z",
                },
                "variant_engineering": {
                    "reviewer_id": "F27-VARIANT-REVIEWER",
                    "signed_at_utc": "2026-01-01T13:05:00Z",
                },
                "final_envelope": {
                    "sha256": "a" * 64,
                    "generated_at_utc": "2026-01-01T13:10:00Z",
                },
            },
        }

        cylinder_axes = []
        positions_x = [-300.0, -180.0, -60.0, 60.0, 180.0, 300.0]
        for bank_token, bank, y, direction in (
            ("P", "positive", 100.0, [0.0, 1.0, 0.0]),
            ("N", "negative", -100.0, [0.0, -1.0, 0.0]),
        ):
            for ordinal, position_x in enumerate(positions_x, start=1):
                cylinder_axes.append(
                    {
                        "id": f"CYL-{bank_token}-{ordinal:02d}",
                        "bank": bank,
                        "datum_ref": "ENGINE-FRAME-F30",
                        "origin_mm": [position_x, y, 0.0],
                        "direction": direction,
                        "witness_length_mm": 160.0,
                        "position_standard_uncertainty_mm": 0.1,
                        "angular_standard_uncertainty_deg": 0.1,
                        "evidence_ref": "EV-CYL",
                    }
                )

        bearing_positions = [-350.0, -250.0, -150.0, -50.0, 50.0, 150.0, 250.0, 350.0]
        parameters = {
            "schema_version": "1.0.0",
            "phase": "F30",
            "status": "measured_layout_input_candidate",
            "campaign_id": "SYNTHETIC-F30-CAMPAIGN",
            "f27_final_review_envelope_sha256": "a" * 64,
            "f27_scan_to_engine_transform_sha256": hashlib.sha256(
                self.module.canonical_json_bytes(transform)
            ).hexdigest(),
            "scan_sha256": self.module.SCAN_SHA256,
            "f27_variant_id": "917_5_0_na",
            "f28_variant_id": "type_912_5_0_na",
            "units": "mm",
            "documentary_candidates_applied": False,
            "evidence_index": evidence_index,
            "engine_frame": {
                "id": "ENGINE-FRAME-F30",
                "origin_mm": [0.0, 0.0, 0.0],
                "right_handed": True,
                "handedness_token": "bank_positive_on_positive_engine_y",
                "position_standard_uncertainty_mm": 0.1,
                "evidence_ref": "EV-FRAME",
            },
            "crankshaft_axis": {
                "id": "CRANKSHAFT-AXIS-F30",
                "datum_ref": "ENGINE-FRAME-F30",
                "origin_mm": [0.0, 0.0, 0.0],
                "direction": [1.0, 0.0, 0.0],
                "span_mm": [-400.0, 400.0],
                "position_standard_uncertainty_mm": 0.1,
                "angular_standard_uncertainty_deg": 0.1,
                "evidence_ref": "EV-CRANK",
            },
            "crankcase_split_plane": self._plane(
                "CRANKCASE-SPLIT-PLANE", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], "EV-SPLIT"
            ),
            "bank_deck_planes": [
                self._plane(
                    "BANK-POSITIVE-DECK", [0.0, 100.0, 0.0], [0.0, 1.0, 0.0], "EV-DECK"
                ),
                self._plane(
                    "BANK-NEGATIVE-DECK", [0.0, -100.0, 0.0], [0.0, -1.0, 0.0], "EV-DECK"
                ),
            ],
            "cylinder_axes": cylinder_axes,
            "main_bearing_stations": {
                "physically_confirmed_count": 8,
                "stations": [
                    {
                        "id": f"MAIN-{ordinal:02d}",
                        "datum_ref": "ENGINE-FRAME-F30",
                        "position_x_mm": position_x,
                        "position_standard_uncertainty_mm": 0.1,
                        "evidence_ref": "EV-BEARING",
                    }
                    for ordinal, position_x in enumerate(bearing_positions, start=1)
                ],
                "count_evidence_ref": "EV-BEARING-COUNT",
            },
            "release_gates": {
                gate_id: False for gate_id in self.module.RELEASE_GATE_IDS
            },
        }

        binding_report = base / "binding-review-report.txt"
        binding_report.write_text(
            "synthetic F30 human review report\n", encoding="utf-8"
        )
        reviewer_public_key = base / "reviewer-public-key.pem"
        reviewer_public_key.write_text(
            "synthetic public key fixture; not a real trust anchor\n",
            encoding="utf-8",
        )
        binding_signature = base / "binding-signature.bin"
        binding_signature.write_bytes(b"synthetic detached signature fixture\n")
        parameters_path = base / "layout-parameters.json"
        parameters_path.write_bytes(self.module.canonical_json_bytes(parameters))
        binding = {
            "schema_version": "1.0.0",
            "phase": "F30",
            "decision_id": "F30-SYNTHETIC-DECISION",
            "decision": "accepted_for_parametric_layout_only",
            "campaign_id": "SYNTHETIC-F30-CAMPAIGN",
            "f27_final_review_envelope_sha256": "a" * 64,
            "f27_scan_to_engine_transform_sha256": parameters[
                "f27_scan_to_engine_transform_sha256"
            ],
            "scan_sha256": self.module.SCAN_SHA256,
            "f27_variant_id": "917_5_0_na",
            "f28_variant_id": "type_912_5_0_na",
            "layout_parameters_sha256": hashlib.sha256(
                self.module.canonical_json_bytes(parameters)
            ).hexdigest(),
            "reviewer_id": "F30-INDEPENDENT-REVIEWER",
            "signed_at_utc": "2026-01-01T13:20:00Z",
            "review_report_evidence_ref": "F30-REVIEW-REPORT",
            "review_report_sha256": hashlib.sha256(
                binding_report.read_bytes()
            ).hexdigest(),
            "reviewer_public_key_sha256": hashlib.sha256(
                reviewer_public_key.read_bytes()
            ).hexdigest(),
            "signature_algorithm": self.module.F30_SIGNATURE_ALGORITHM,
            "signature_scope": "exact_canonical_binding_json_bytes",
            "authorized_scope": list(self.module.AUTHORIZED_SCOPE),
            "release_gates": {
                gate_id: False for gate_id in self.module.RELEASE_GATE_IDS
            },
        }

        paths = {
            "record": base / "record.json",
            "observations": base / "observations.csv",
            "working_scan": base / "working-scan-source.obj",
            "binding": base / "binding.json",
            "binding_report": binding_report,
            "binding_signature": binding_signature,
            "reviewer_public_key": reviewer_public_key,
            "parameters": parameters_path,
            "f27_evidence": f27_evidence_root,
            "layout_evidence": layout_evidence_root,
        }
        paths["record"].write_bytes(self.module.canonical_json_bytes(record))
        paths["observations"].write_text("synthetic observations\n", encoding="utf-8")
        paths["working_scan"].write_bytes(b"synthetic scan placeholder\n")
        paths["binding"].write_bytes(self.module.canonical_json_bytes(binding))
        return record, parameters, binding, paths

    def _write_parameter_and_binding(self, parameters, binding, paths):
        parameter_bytes = self.module.canonical_json_bytes(parameters)
        paths["parameters"].write_bytes(parameter_bytes)
        binding["layout_parameters_sha256"] = hashlib.sha256(parameter_bytes).hexdigest()
        paths["binding"].write_bytes(self.module.canonical_json_bytes(binding))

    def _selective_sha256(self, real_sha256):
        def calculate(path):
            candidate = Path(path)
            if candidate.name == "working-scan.obj":
                return self.module.SCAN_SHA256
            return real_sha256(candidate)

        return calculate

    def _fake_step_builder(self, real_sha256):
        def build(parameters, step_path):
            step_path.write_bytes(b"ISO-10303-21; synthetic F30 wireframe; END-ISO-10303-21;\n")
            segments = self.module._construction_segments(parameters)
            edge_count = len(segments)
            geometry_sha256 = self.module._coordinate_multiset_signature(segments)
            return {
                "authored_edge_count": edge_count,
                "reopened_edge_count": edge_count,
                "reopened_linear_edge_count": edge_count,
                "reopened_face_count": 0,
                "reopened_solid_count": 0,
                "reopened_valid": True,
                "coordinate_rounding_decimals": self.module.STEP_COORDINATE_DECIMALS,
                "expected_geometry_sha256": geometry_sha256,
                "reopened_geometry_sha256": geometry_sha256,
                "reopened_geometry_matches_expected": True,
                "step_bytes": step_path.stat().st_size,
                "step_sha256_recorded_not_reproducibility_claim": real_sha256(
                    step_path
                ),
            }

        return build

    def _author(
        self,
        paths,
        output_dir,
        *,
        trusted_public_key_sha256="fixture",
        signature_valid=True,
    ):
        real_sha256 = self.module.sha256_file
        if trusted_public_key_sha256 == "fixture":
            trusted_public_key_sha256 = real_sha256(paths["reviewer_public_key"])
        with mock.patch.object(
            self.module,
            "_run_f27_validator",
            return_value=self._ready_f27_report(),
        ), mock.patch.object(
            self.module,
            "sha256_file",
            side_effect=self._selective_sha256(real_sha256),
        ):
            return self.module.author_layout(
                ROOT,
                paths["record"],
                paths["observations"],
                paths["f27_evidence"],
                paths["working_scan"],
                paths["binding"],
                paths["binding_report"],
                paths["binding_signature"],
                paths["reviewer_public_key"],
                paths["layout_evidence"],
                paths["parameters"],
                output_dir,
                step_builder=self._fake_step_builder(real_sha256),
                trusted_reviewer_public_key_sha256=trusted_public_key_sha256,
                binding_signature_verifier=lambda *_args: signature_valid,
            )

    def test_tracked_template_is_exact_and_fail_closed(self):
        observed = self.module.load_json(TEMPLATE)
        self.assertEqual(observed, self.module.build_template(ROOT))
        self.assertTrue(all(value is False for value in observed["release_gates"].values()))
        self.assertEqual(
            observed["source_binding"]["f27_to_f28_variant_target_map"],
            {"917_5_0_na": "type_912_5_0_na"},
        )

    def test_upstream_drift_cannot_be_rebased_by_template_generator(self):
        with mock.patch.object(self.module, "sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "approved_upstream_sha256_mismatch"):
                self.module.build_template(ROOT)

    def test_parameter_validation_accepts_coherent_synthetic_layout(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, _paths = self._fixture(temporary)
            self.assertEqual(self.module.validate_layout_parameters(parameters), [])

    def test_generic_turbo_variant_is_blocked_without_exact_f28_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, _paths = self._fixture(temporary)
            parameters["f27_variant_id"] = "917_30_turbo_5374"
            parameters["f28_variant_id"] = "917_30_1973_turbo_5374"
            errors = self.module.validate_layout_parameters(parameters)
            self.assertIn(
                "layout_parameter_f27_variant_has_no_f28_authoring_branch",
                errors,
            )

    def test_wrong_evidence_role_and_orphan_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, _paths = self._fixture(temporary)
            parameters["engine_frame"]["evidence_ref"] = "EV-CYL"
            errors = self.module.validate_layout_parameters(parameters)
            self.assertIn("f30_evidence_kind_mismatch:engine_frame.evidence_ref", errors)
            self.assertTrue(
                any(error.startswith("orphan_layout_evidence_entries:") for error in errors)
            )

    def test_incoherent_cylinder_axis_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, _paths = self._fixture(temporary)
            parameters["cylinder_axes"][0]["direction"] = [1.0, 0.0, 0.0]
            errors = self.module.validate_layout_parameters(parameters)
            self.assertTrue(
                any(
                    error.startswith("cylinder_axis_not_aligned_with_bank_deck:")
                    for error in errors
                )
            )
            self.assertTrue(
                any(
                    error.startswith("cylinder_axis_not_orthogonal_to_crankshaft:")
                    for error in errors
                )
            )

    def test_binding_must_follow_f27_final_envelope(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            record, parameters, binding, paths = self._fixture(temporary)
            binding["signed_at_utc"] = "2026-01-01T13:09:59Z"
            errors = self.module.validate_binding(
                binding,
                record,
                hashlib.sha256(
                    self.module.canonical_json_bytes(parameters)
                ).hexdigest(),
                hashlib.sha256(paths["binding_report"].read_bytes()).hexdigest(),
                hashlib.sha256(paths["reviewer_public_key"].read_bytes()).hexdigest(),
                hashlib.sha256(paths["reviewer_public_key"].read_bytes()).hexdigest(),
            )
            self.assertIn(
                "binding_signature_must_follow_f27_reviews_and_final_envelope",
                errors,
            )

    def test_layout_evidence_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, paths = self._fixture(temporary)
            target = Path(temporary) / "outside-evidence.txt"
            target.write_text("outside\n", encoding="utf-8")
            linked = paths["layout_evidence"] / "EV-FRAME.txt"
            linked.unlink()
            linked.symlink_to(target)
            errors, _manifest = self.module.validate_layout_evidence_files(
                parameters, paths["layout_evidence"]
            )
            self.assertTrue(
                any(error.startswith("layout_evidence_symlink_forbidden:") for error in errors)
            )

    def test_modified_binding_report_fails_without_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, _parameters, _binding, paths = self._fixture(temporary)
            paths["binding_report"].write_text(
                "modified after binding\n", encoding="utf-8"
            )
            output_dir = self.allowed_output_root / f"BAD-REPORT-{Path(temporary).name}"
            report = self._author(paths, output_dir)
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn(
                "binding_value_mismatch:review_report_sha256", report["errors"]
            )
            self.assertFalse(output_dir.exists())

    def test_authoring_is_blocked_without_trusted_reviewer_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, _parameters, _binding, paths = self._fixture(temporary)
            output_dir = self.allowed_output_root / f"NO-TRUST-{Path(temporary).name}"
            report = self._author(
                paths,
                output_dir,
                trusted_public_key_sha256=None,
            )
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn(
                "binding_reviewer_trust_anchor_not_configured",
                report["errors"],
            )
            self.assertFalse(output_dir.exists())

    def test_invalid_detached_binding_signature_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, _parameters, _binding, paths = self._fixture(temporary)
            output_dir = self.allowed_output_root / f"BAD-SIGNATURE-{Path(temporary).name}"
            report = self._author(paths, output_dir, signature_valid=False)
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn("binding_detached_signature_invalid", report["errors"])
            self.assertFalse(output_dir.exists())

    def test_f27_and_f30_evidence_payloads_must_be_distinct(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, binding, paths = self._fixture(temporary)
            reused_payload = (paths["f27_evidence"] / "placeholder.txt").read_bytes()
            reused_path = paths["layout_evidence"] / "EV-FRAME.txt"
            reused_path.write_bytes(reused_payload)
            frame_entry = next(
                item
                for item in parameters["evidence_index"]
                if item["evidence_id"] == "EV-FRAME"
            )
            frame_entry["sha256"] = hashlib.sha256(reused_payload).hexdigest()
            self._write_parameter_and_binding(parameters, binding, paths)
            output_dir = self.allowed_output_root / f"REUSED-EVIDENCE-{Path(temporary).name}"
            report = self._author(paths, output_dir)
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn(
                "f27_and_f30_evidence_payload_sha256_overlap",
                report["errors"],
            )
            self.assertFalse(output_dir.exists())

    def test_f27_gate_must_be_literal_false(self):
        report = self._ready_f27_report()
        report["release_gates"][self.module.F27_RELEASE_GATE_IDS[0]] = 0
        self.assertIn(
            "f27_validator_release_gate_registry_mismatch",
            self.module.validate_f27_report(report),
        )

    def test_f27_gate_registry_cannot_be_truncated(self):
        report = self._ready_f27_report()
        report["release_gates"].pop(self.module.F27_RELEASE_GATE_IDS[-1])
        self.assertIn(
            "f27_validator_release_gate_registry_mismatch",
            self.module.validate_f27_report(report),
        )

    def test_each_step_geometry_change_changes_construction_signature(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, _paths = self._fixture(temporary)
            original = self.module.layout_signature(parameters)["construction_segments"]
            modified = copy.deepcopy(parameters)
            modified["cylinder_axes"][0]["witness_length_mm"] += 1.0
            changed_axis = self.module.layout_signature(modified)["construction_segments"]
            self.assertNotEqual(original, changed_axis)
            modified = copy.deepcopy(parameters)
            modified["bank_deck_planes"][0]["extent_v_mm"] += 1.0
            changed_plane = self.module.layout_signature(modified)["construction_segments"]
            self.assertNotEqual(original, changed_plane)

    def test_translated_reopened_step_coordinates_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, _binding, _paths = self._fixture(temporary)
            expected = self.module._construction_segments(parameters)
            translated = copy.deepcopy(expected)
            translated[0]["start_mm"][0] += 1.0
            translated[0]["end_mm"][0] += 1.0
            with self.assertRaisesRegex(RuntimeError, "changed segment coordinates"):
                self.module._verified_roundtrip_coordinate_signatures(
                    expected,
                    translated,
                )

    def test_authoring_publishes_only_wireframe_contract_with_completion_marker(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, _parameters, _binding, paths = self._fixture(temporary)
            output_dir = self.allowed_output_root / f"SYNTHETIC-{Path(temporary).name}"
            self.addCleanup(shutil.rmtree, output_dir, True)
            report = self._author(paths, output_dir)
            self.assertEqual(
                report["status"],
                "construction_layout_authored_release_gates_closed",
            )
            self.assertTrue(output_dir.is_dir())
            self.assertEqual(
                set(report["output_files"]),
                {
                    "layout-parameters.json",
                    "engine-layout.step",
                    "geometry-report.json",
                    "provenance-manifest.json",
                    "publication-complete.json",
                },
            )
            geometry = self.module.load_json(output_dir / "geometry-report.json")
            self.assertEqual(geometry["step_roundtrip"]["reopened_face_count"], 0)
            self.assertEqual(geometry["step_roundtrip"]["reopened_solid_count"], 0)
            self.assertTrue(
                geometry["step_roundtrip"]["reopened_geometry_matches_expected"]
            )
            self.assertEqual(
                geometry["step_roundtrip"]["expected_geometry_sha256"],
                geometry["step_roundtrip"]["reopened_geometry_sha256"],
            )
            self.assertFalse(geometry["claims"]["functional_engine_cad_authored"])
            self.assertTrue(all(value is False for value in geometry["release_gates"].values()))
            provenance = self.module.load_json(output_dir / "provenance-manifest.json")
            self.assertNotIn("runtime_image", provenance)
            self.assertFalse(
                provenance["runtime_image_policy"][
                    "exact_image_identity_verified_in_process"
                ]
            )
            self.assertTrue(
                provenance["runtime_image_policy"][
                    "controller_runtime_attestation_required"
                ]
            )

    def test_authoring_rejects_claimed_step_coordinate_mismatch(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, _parameters, _binding, paths = self._fixture(temporary)
            output_dir = self.allowed_output_root / f"STEP-MISMATCH-{Path(temporary).name}"
            real_sha256 = self.module.sha256_file
            base_builder = self._fake_step_builder(real_sha256)

            def mismatched_builder(parameters, step_path):
                metrics = base_builder(parameters, step_path)
                metrics["reopened_geometry_sha256"] = "0" * 64
                return metrics

            with mock.patch.object(
                self.module,
                "_run_f27_validator",
                return_value=self._ready_f27_report(),
            ), mock.patch.object(
                self.module,
                "sha256_file",
                side_effect=self._selective_sha256(real_sha256),
            ):
                report = self.module.author_layout(
                    ROOT,
                    paths["record"],
                    paths["observations"],
                    paths["f27_evidence"],
                    paths["working_scan"],
                    paths["binding"],
                    paths["binding_report"],
                    paths["binding_signature"],
                    paths["reviewer_public_key"],
                    paths["layout_evidence"],
                    paths["parameters"],
                    output_dir,
                    step_builder=mismatched_builder,
                    trusted_reviewer_public_key_sha256=real_sha256(
                        paths["reviewer_public_key"]
                    ),
                    binding_signature_verifier=lambda *_args: True,
                )
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn("authoring_failed:ValueError", report["errors"])
            self.assertFalse(output_dir.exists())

    def test_noncanonical_parameter_bytes_fail_without_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, parameters, binding, paths = self._fixture(temporary)
            raw = json.dumps(parameters, separators=(",", ":")).encode("utf-8")
            paths["parameters"].write_bytes(raw)
            binding["layout_parameters_sha256"] = hashlib.sha256(
                self.module.canonical_json_bytes(parameters)
            ).hexdigest()
            paths["binding"].write_bytes(self.module.canonical_json_bytes(binding))
            output_dir = self.allowed_output_root / f"NONCANONICAL-{Path(temporary).name}"
            report = self._author(paths, output_dir)
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn("layout_parameters_must_be_canonical_json", report["errors"])
            self.assertFalse(output_dir.exists())

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            _record, _parameters, _binding, paths = self._fixture(temporary)
            output_dir = self.allowed_output_root / f"EXISTING-{Path(temporary).name}"
            self.addCleanup(shutil.rmtree, output_dir, True)
            output_dir.mkdir()
            sentinel = output_dir / "sentinel.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            report = self._author(paths, output_dir)
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn("output_dir_already_exists_no_overwrite", report["errors"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_interrupted_publication_never_exposes_partial_final_directory(self):
        parent_fd = self.module._open_directory_no_symlinks(
            self.allowed_output_root
        )
        output_name = f"INTERRUPTED-{self._testMethodName}"
        staging_name = self.module._create_staging_directory(parent_fd, output_name)
        staging_path = self.allowed_output_root / staging_name
        (staging_path / "payload.json").write_text("{}\n", encoding="utf-8")
        try:
            with mock.patch.object(
                self.module,
                "_rename_directory_noreplace",
                side_effect=OSError("synthetic interruption before rename"),
            ):
                with self.assertRaises(OSError):
                    self.module._publish_with_completion_marker(
                        parent_fd,
                        staging_name,
                        output_name,
                    )
            self.assertFalse((self.allowed_output_root / output_name).exists())
            self.assertTrue(staging_path.is_dir())
            self.assertTrue((staging_path / "publication-complete.json").is_file())
        finally:
            self.module._cleanup_staging_directory(parent_fd, staging_name)
            os.close(parent_fd)

    def test_blank_real_f27_packet_cannot_create_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temporary:
            base = Path(temporary)
            f27_evidence = base / "f27-evidence"
            layout_evidence = base / "layout-evidence"
            f27_evidence.mkdir()
            layout_evidence.mkdir()
            paths = {
                "record": base / "record.json",
                "observations": base / "observations.csv",
                "working_scan": base / "working-scan-source.obj",
                "binding": base / "binding.json",
                "binding_report": base / "binding-report.txt",
                "binding_signature": base / "binding-signature.bin",
                "reviewer_public_key": base / "reviewer-public-key.pem",
                "parameters": base / "parameters.json",
                "f27_evidence": f27_evidence,
                "layout_evidence": layout_evidence,
            }
            shutil.copyfile(F27_JSON_TEMPLATE, paths["record"])
            shutil.copyfile(F27_CSV_TEMPLATE, paths["observations"])
            paths["working_scan"].write_bytes(b"not the canonical scan\n")
            paths["binding"].write_text("{}\n", encoding="utf-8")
            paths["binding_report"].write_text("blank\n", encoding="utf-8")
            paths["binding_signature"].write_bytes(b"blank signature\n")
            paths["reviewer_public_key"].write_text("blank key\n", encoding="utf-8")
            paths["parameters"].write_text("{}\n", encoding="utf-8")
            output_dir = self.allowed_output_root / f"BLANK-F27-{Path(temporary).name}"
            report = self.module.author_layout(
                ROOT,
                paths["record"],
                paths["observations"],
                paths["f27_evidence"],
                paths["working_scan"],
                paths["binding"],
                paths["binding_report"],
                paths["binding_signature"],
                paths["reviewer_public_key"],
                paths["layout_evidence"],
                paths["parameters"],
                output_dir,
            )
            self.assertEqual(report["status"], "failed_closed_no_output")
            self.assertIn("f27_campaign_not_ready_for_binding", report["errors"])
            self.assertFalse(output_dir.exists())


if __name__ == "__main__":
    unittest.main()
