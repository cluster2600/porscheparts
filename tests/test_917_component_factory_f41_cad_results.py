#!/usr/bin/env python3
"""Adversarial tests for the local F41 CAD result archive validator."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    ROOT
    / "twins/reference-917-engine/source/validate_component_factory_f41_cad_results.py"
)


def load_validator():
    spec = importlib.util.spec_from_file_location("f41_cad_results_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load F41 CAD result validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ComponentFactoryF41CadResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_validator()
        cls.job_id = "f41-cad-test-0123456789ab"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="f41-cad-results-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def encoded_json(value: object) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def evidence(path: str, payload: bytes) -> dict[str, object]:
        return {
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }

    def valid_payloads(self) -> dict[str, bytes]:
        source_hashes = {
            field: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for field, relative in self.validator.SOURCE_PATHS.items()
        }
        payloads: dict[str, bytes] = {}
        family_reports = []
        for family in self.validator.FAMILIES:
            outputs = {}
            for output_format in self.validator.FORMATS:
                path = self.validator.artifact_relative_path(family, output_format)
                content = f"synthetic-test:{family}:{output_format}\n".encode("ascii")
                payloads[path] = content
                outputs[output_format] = self.evidence(path, content)
            family_report = {
                "checks": {
                    "3mf_roundtrip_shape_count": 1,
                    "3mf_roundtrip_solid_count": 1,
                    "step_roundtrip": {
                        "all_solids_positive_volume": True,
                        "bounds_size_mm": [1.0, 2.0, 3.0],
                        "manifold": True,
                        "solid_count": 1,
                        "valid": True,
                        "volume_mm3": 6.0,
                    },
                },
                "family_id": family,
                "manufacturing_released": False,
                "outputs": outputs,
                "runtime_image_ref": self.validator.EXPECTED_RUNTIME_IMAGE,
                "simulation_validated": False,
                "source_contract_sha256": source_hashes["source_contract_sha256"],
                "source_generator_sha256": source_hashes["source_generator_sha256"],
                "source_math_sha256": source_hashes["source_math_sha256"],
                "source_seed": "F35_rotating_917_30_turbo_5374",
                "state": "generated_research_seed_not_released",
            }
            family_reports.append(family_report)
            payloads[f"artifacts/{family}/cad-family-report.json"] = self.encoded_json(
                family_report
            )

        log_payload = b"synthetic F35 CAD seed log\n"
        payloads["logs/f35-cad-seed.log"] = log_payload
        payloads["preflight/cad.json"] = self.encoded_json(
            {
                "checks": {
                    "F35_hash_bound_inputs": [
                        {
                            "path": self.validator.SOURCE_PATHS[
                                "source_contract_sha256"
                            ],
                            "role": "contract",
                            "sha256": source_hashes["source_contract_sha256"],
                        },
                        {
                            "path": self.validator.SOURCE_PATHS[
                                "source_generator_sha256"
                            ],
                            "role": "generator",
                            "sha256": source_hashes["source_generator_sha256"],
                        },
                        {
                            "path": self.validator.SOURCE_PATHS[
                                "source_math_sha256"
                            ],
                            "role": "math_module",
                            "sha256": source_hashes["source_math_sha256"],
                        },
                    ],
                    "build123d_version": "0.11.1",
                    "expected_image_ref": self.validator.EXPECTED_RUNTIME_IMAGE,
                    "lib3mf_available": True,
                    "network_required_during_job": False,
                    "platform": "linux/amd64",
                    "reported_runtime_image_ref": self.validator.EXPECTED_RUNTIME_IMAGE,
                },
                "errors": [],
                "geometry_generated": False,
                "paid_instance_launched": False,
                "phase": "F41",
                "runtime_phase": "cad",
                "schema_version": "1.0.0",
                "status": "passed",
            }
        )
        payloads["cad-execution-report.json"] = self.encoded_json(
            {
                "blocked_family_count": 132,
                "family_reports": family_reports,
                "generateable_family_count": 6,
                "generated_family_count": 6,
                "generated_format_counts": dict(self.validator.EXPECTED_FORMAT_COUNTS),
                "paid_instance_launched": False,
                "phase": "F41",
                "planned_family_count": 138,
                "release_gates": {
                    key: False for key in sorted(self.validator.RELEASE_GATE_KEYS)
                },
                "runtime_phase": "cad",
                "schema_version": "1.0.0",
                "source_generation_log": self.evidence(
                    "logs/f35-cad-seed.log", log_payload
                ),
                "status": self.validator.EXPECTED_STATUS,
                "target_variant": "917_30_turbo_5374",
            }
        )
        return payloads

    def write_archive(
        self,
        payloads: dict[str, bytes],
        *,
        extra_members: list[tuple[tarfile.TarInfo, bytes | None]] | None = None,
    ) -> Path:
        archive = self.root / "results.tar.gz"
        prefixed_files = {
            f"{self.job_id}/{relative}": payload for relative, payload in payloads.items()
        }
        directories = {self.job_id}
        for name in prefixed_files:
            parts = name.split("/")
            for depth in range(1, len(parts)):
                directories.add("/".join(parts[:depth]))
        with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as handle:
            for name in sorted(directories, key=lambda item: (item.count("/"), item)):
                member = tarfile.TarInfo(f"{name}/")
                member.type = tarfile.DIRTYPE
                member.mode = 0o750
                member.mtime = 0
                handle.addfile(member)
            for name, payload in sorted(prefixed_files.items()):
                member = tarfile.TarInfo(name)
                member.size = len(payload)
                member.mode = 0o640
                member.mtime = 0
                handle.addfile(member, io.BytesIO(payload))
            for member, payload in extra_members or []:
                handle.addfile(member, None if payload is None else io.BytesIO(payload))
        return archive

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def validate(self, archive: Path, output_name: str = "extracted"):
        return self.validator.validate_and_extract(
            archive,
            self.digest(archive),
            self.job_id,
            self.root / output_name,
        )

    def mutate_main_report(self, payloads: dict[str, bytes], mutate) -> None:
        report = json.loads(payloads["cad-execution-report.json"])
        mutate(report)
        payloads["cad-execution-report.json"] = self.encoded_json(report)

    def test_valid_archive_extracts_and_verifies_exact_evidence(self):
        archive = self.write_archive(self.valid_payloads())
        result = self.validate(archive)
        self.assertEqual(
            result["status"],
            "passed_cad_results_archive_integrity_verified_not_released",
        )
        self.assertEqual(result["verified_artifact_count"], 18)
        self.assertEqual(result["generated_format_counts"], {"STEP": 6, "STL": 6, "3MF": 6, "USD": 0})
        self.assertFalse(result["geometry_semantics_validated"])
        self.assertFalse(result["physical_validation_complete"])
        self.assertFalse(result["simulation_validated"])
        self.assertFalse(result["manufacturing_released"])
        self.assertTrue((self.root / "extracted" / self.job_id / "cad-execution-report.json").is_file())
        self.assertFalse(any(".f41-staging-" in item.name for item in self.root.iterdir()))

    def test_archive_sha256_must_match_before_output_creation(self):
        archive = self.write_archive(self.valid_payloads())
        output = self.root / "bad-hash-output"
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_sha256_mismatch"):
            self.validator.validate_and_extract(archive, "0" * 64, self.job_id, output)
        self.assertFalse(output.exists())

    def test_symlink_archive_is_rejected_by_o_nofollow(self):
        archive = self.write_archive(self.valid_payloads())
        link = self.root / "linked-results.tar.gz"
        link.symlink_to(archive)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_absent_or_unsafe"):
            self.validator.validate_and_extract(link, self.digest(archive), self.job_id, self.root / "symlink-output")

    def test_existing_output_is_rejected_without_changes(self):
        archive = self.write_archive(self.valid_payloads())
        output = self.root / "existing"
        output.mkdir()
        marker = output / "keep"
        marker.write_text("keep", encoding="ascii")
        with self.assertRaisesRegex(self.validator.ResultValidationError, "extraction_output_must_be_new"):
            self.validator.validate_and_extract(archive, self.digest(archive), self.job_id, output)
        self.assertEqual(marker.read_text(encoding="ascii"), "keep")

    def test_parent_traversal_member_is_rejected(self):
        member = tarfile.TarInfo(f"{self.job_id}/../escape")
        member.size = 1
        archive = self.write_archive(self.valid_payloads(), extra_members=[(member, b"x")])
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_member_ambiguous_component"):
            self.validate(archive)

    def test_backslash_member_is_rejected(self):
        member = tarfile.TarInfo(f"{self.job_id}\\escape")
        member.size = 1
        archive = self.write_archive(self.valid_payloads(), extra_members=[(member, b"x")])
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_member_backslash"):
            self.validate(archive)

    def test_special_member_is_rejected(self):
        member = tarfile.TarInfo(f"{self.job_id}/unsafe-link")
        member.type = tarfile.SYMTYPE
        member.linkname = "cad-execution-report.json"
        archive = self.write_archive(self.valid_payloads(), extra_members=[(member, None)])
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_member_special_type"):
            self.validate(archive)

    def test_duplicate_member_is_rejected(self):
        duplicate_name = f"{self.job_id}/cad-execution-report.json"
        member = tarfile.TarInfo(duplicate_name)
        member.size = 1
        archive = self.write_archive(self.valid_payloads(), extra_members=[(member, b"x")])
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_member_duplicate"):
            self.validate(archive)

    def test_casefold_collision_in_implicit_directory_is_rejected(self):
        member = tarfile.TarInfo(f"{self.job_id}/artifacts/Piston/unexpected.bin")
        member.size = 1
        archive = self.write_archive(self.valid_payloads(), extra_members=[(member, b"x")])
        with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_member_casefold_collision"):
            self.validate(archive)

    def test_per_member_limit_is_checked_before_extraction(self):
        archive = self.write_archive(self.valid_payloads())
        previous = self.validator.MAX_MEMBER_BYTES
        self.validator.MAX_MEMBER_BYTES = 8
        try:
            with self.assertRaisesRegex(self.validator.ResultValidationError, "archive_member_size_limit"):
                self.validate(archive)
        finally:
            self.validator.MAX_MEMBER_BYTES = previous
        self.assertFalse((self.root / "extracted").exists())

    def test_global_gzip_decompressed_stream_limit_precedes_tar_parsing(self):
        archive = self.write_archive(self.valid_payloads())
        previous = self.validator.MAX_DECOMPRESSED_TAR_BYTES
        self.validator.MAX_DECOMPRESSED_TAR_BYTES = 1024
        try:
            with self.assertRaisesRegex(
                self.validator.ResultValidationError,
                "gzip_decompressed_stream_limit_exceeded",
            ):
                self.validate(archive)
        finally:
            self.validator.MAX_DECOMPRESSED_TAR_BYTES = previous
        self.assertFalse((self.root / "extracted").exists())
        self.assertFalse(any(".f41-staging-" in item.name for item in self.root.iterdir()))

    def test_runtime_workspace_is_excluded_from_exact_layout(self):
        member = tarfile.TarInfo(f"{self.job_id}/.runtime/home/unexpected")
        member.size = 1
        archive = self.write_archive(self.valid_payloads(), extra_members=[(member, b"x")])
        with self.assertRaisesRegex(
            self.validator.ResultValidationError, "archive_regular_file_set_mismatch"
        ):
            self.validate(archive)
        self.assertFalse((self.root / "extracted").exists())

    def test_exact_counts_and_format_counts_are_required(self):
        payloads = self.valid_payloads()
        self.mutate_main_report(payloads, lambda report: report.__setitem__("generated_family_count", 5))
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "cad_report_generated_count_mismatch"):
            self.validate(archive)

        payloads = self.valid_payloads()
        self.mutate_main_report(
            payloads,
            lambda report: report["generated_format_counts"].__setitem__("USD", False),
        )
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "cad_report_format_counts_mismatch"):
            self.validate(archive, "bad-format-output")

    def test_release_gate_cannot_be_opened(self):
        payloads = self.valid_payloads()

        def mutate(report):
            report["release_gates"]["metal_print_authorized"] = True

        self.mutate_main_report(payloads, mutate)
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "policy_flag_must_remain_false"):
            self.validate(archive)

    def test_family_manufacturing_or_simulation_claim_cannot_be_opened(self):
        for field in ("manufacturing_released", "simulation_validated"):
            with self.subTest(field=field):
                payloads = self.valid_payloads()
                report = json.loads(payloads["cad-execution-report.json"])
                report["family_reports"][0][field] = True
                payloads["cad-execution-report.json"] = self.encoded_json(report)
                archive = self.write_archive(payloads)
                with self.assertRaisesRegex(self.validator.ResultValidationError, "policy_flag_must_remain_false"):
                    self.validate(archive, f"output-{field}")

    def test_nested_physical_claim_cannot_be_hidden_in_checks(self):
        payloads = self.valid_payloads()
        report = json.loads(payloads["cad-execution-report.json"])
        report["family_reports"][0]["checks"]["physical_validation_complete"] = True
        payloads["cad-execution-report.json"] = self.encoded_json(report)
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "policy_flag_must_remain_false"):
            self.validate(archive)

    def test_preflight_checks_are_exact_and_dependencies_are_pinned(self):
        payloads = self.valid_payloads()
        preflight = json.loads(payloads["preflight/cad.json"])
        preflight["checks"]["build123d_version"] = "0.11.2"
        payloads["preflight/cad.json"] = self.encoded_json(preflight)
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(
            self.validator.ResultValidationError,
            "cad_preflight_build123d_version_mismatch",
        ):
            self.validate(archive)
        self.assertFalse((self.root / "extracted").exists())

        payloads = self.valid_payloads()
        preflight = json.loads(payloads["preflight/cad.json"])
        preflight["checks"]["unexpected"] = "value"
        payloads["preflight/cad.json"] = self.encoded_json(preflight)
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(
            self.validator.ResultValidationError,
            "cad_preflight_check_schema_mismatch",
        ):
            self.validate(archive, "extra-preflight-check")
        self.assertFalse((self.root / "extra-preflight-check").exists())

    def test_source_generation_log_must_be_nonempty(self):
        payloads = self.valid_payloads()
        payloads["logs/f35-cad-seed.log"] = b""
        self.mutate_main_report(
            payloads,
            lambda report: report.__setitem__(
                "source_generation_log",
                self.evidence("logs/f35-cad-seed.log", b""),
            ),
        )
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(
            self.validator.ResultValidationError,
            "artifact_size_invalid:logs/f35-cad-seed.log",
        ):
            self.validate(archive)
        self.assertFalse((self.root / "extracted").exists())

    def test_unexpected_policy_key_is_rejected_even_when_string_or_false(self):
        cases = (
            ("physical_note", "reference only"),
            ("fatigue_claim", False),
            ("dyno_status", "not run"),
        )
        for index, (key, value) in enumerate(cases):
            with self.subTest(key=key):
                payloads = self.valid_payloads()
                report = json.loads(payloads["cad-execution-report.json"])
                report["family_reports"][0]["checks"][key] = value
                payloads["cad-execution-report.json"] = self.encoded_json(report)
                archive = self.write_archive(payloads)
                with self.assertRaisesRegex(
                    self.validator.ResultValidationError,
                    "cad_family_check_schema_mismatch",
                ):
                    self.validate(archive, f"unexpected-policy-{index}")
                self.assertFalse((self.root / f"unexpected-policy-{index}").exists())

    def test_family_metric_types_must_be_finite_and_positive(self):
        mutations = (
            ("3mf_roundtrip_shape_count", True, "cad_family_3mf_shape_count_invalid"),
            ("step_roundtrip.volume_mm3", float("nan"), "cad_family_step_volume_invalid"),
            ("step_roundtrip.bounds_size_mm", [1.0, 0.0, 3.0], "cad_family_step_bounds_invalid"),
        )
        for index, (field, value, error) in enumerate(mutations):
            with self.subTest(field=field):
                payloads = self.valid_payloads()
                report = json.loads(payloads["cad-execution-report.json"])
                checks = report["family_reports"][0]["checks"]
                if "." in field:
                    parent, child = field.split(".", 1)
                    checks[parent][child] = value
                else:
                    checks[field] = value
                payloads["cad-execution-report.json"] = self.encoded_json(report)
                archive = self.write_archive(payloads)
                with self.assertRaisesRegex(self.validator.ResultValidationError, error):
                    self.validate(archive, f"invalid-metric-{index}")
                self.assertFalse((self.root / f"invalid-metric-{index}").exists())

    def test_artifact_content_must_match_declared_hash_and_size(self):
        payloads = self.valid_payloads()
        path = self.validator.artifact_relative_path("piston", "STEP")
        payloads[path] += b"tampered"
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "artifact_size_mismatch"):
            self.validate(archive)

    def test_family_sidecar_must_equal_the_main_report_entry(self):
        payloads = self.valid_payloads()
        path = "artifacts/piston/cad-family-report.json"
        sidecar = json.loads(payloads[path])
        sidecar["state"] = "tampered"
        payloads[path] = self.encoded_json(sidecar)
        archive = self.write_archive(payloads)
        with self.assertRaisesRegex(self.validator.ResultValidationError, "cad_family_sidecar_mismatch"):
            self.validate(archive)


if __name__ == "__main__":
    unittest.main()
