#!/usr/bin/env python3
"""Construit les formulaires F27 et valide une campagne metrologique locale.

Les formulaires suivis sont volontairement vierges. Une campagne remplie doit
rester sous ``work/`` avec ses preuves. Le validateur peut declarer un paquet
pret pour revue independante, mais n'ouvre jamais un gate d'ingenierie.
"""

from __future__ import annotations

import argparse
import copy
import csv
import errno
import hashlib
import io
import json
import math
import os
import re
import stat
import statistics
import subprocess
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any


JSON_TEMPLATE_REL = Path(
    "twins/reference-917-engine/physical-metrology-campaign-f27.template.json"
)
CSV_TEMPLATE_REL = Path(
    "twins/reference-917-engine/physical-metrology-observations-f27.template.csv"
)
UPSTREAMS = {
    "f13_scan_metrology": Path(
        "twins/reference-917-engine/scan-metrology-f13.json"
    ),
    "f16_kinematic_interfaces": Path(
        "twins/reference-917-engine/kinematic-interface-readiness-f16.json"
    ),
    "f21_scale_orientation": Path(
        "twins/reference-917-engine/scan-scale-orientation-acquisition-f21.json"
    ),
}
UPSTREAM_ROLES = {
    "f13_scan_metrology": "candidate_variants_and_minimum_physical_controls_only",
    "f16_kinematic_interfaces": "named_datums_and_measurement_targets_only",
    "f21_scale_orientation": "exact_scan_binding_and_empty_acquisition_slots_only",
}
APPROVED_UPSTREAM_SHA256 = {
    "f13_scan_metrology": "578b4ffcf49be04c701b3a86ba0b04d9cd11fd9f39f11b757c2220a698731a5d",
    "f16_kinematic_interfaces": "ec5e56cdd750071462e00dcec978182916ee4c266435bfea0720dea2fda2f2e2",
    "f21_scale_orientation": "fca7306a0afda5e4b4a0af9210dd00189e27f54f32b547e90d02aa9ab18e1808",
}
SCAN_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"
SCALE_CONTROL_IDS = ("SC-01", "SC-02", "SC-03")
CANDIDATE_VARIANT_IDS = (
    "type_912_4_5_na",
    "917_5_0_na",
    "917_30_turbo_5374",
)
DATUM_DEFINITIONS = (
    ("OR-PRIMARY-AXIS", "crankshaft_axis", "axis"),
    ("OR-SECONDARY-PLANE", "crankcase_split_plane", "plane"),
    ("OR-HANDEDNESS", "bank_positive_deck_plane", "handedness_witness"),
)
DATUM_DIRECTION_RULES = {
    "OR-PRIMARY-AXIS": "positive_engine_x_follows_declared_crankshaft_reference_end",
    "OR-SECONDARY-PLANE": "positive_engine_z_follows_declared_crankcase_split_plane_normal",
    "OR-HANDEDNESS": "bank_positive_lies_on_positive_engine_y",
}
HANDEDNESS_TOKEN = "bank_positive_on_positive_engine_y"
NUMERICAL_CONSISTENCY_ABS_TOL = 1e-6
SCALE_CONSISTENCY_REL_TOL = 1e-9
SCALE_CONSISTENCY_ABS_TOL = 1e-12
METHOD_IDS = ("CMM", "CT", "PHOTOGRAMMETRY", "MESH_INSPECTION")
PHYSICAL_METHOD_IDS = {"CMM", "CT", "PHOTOGRAMMETRY"}
REPEAT_COUNT = 3
MAX_RELATIVE_SCALE_SPREAD = 0.005
SHA256_LENGTH = 64
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_CSV_BYTES = 2 * 1024 * 1024
UNCERTAINTY_CORRELATION_MODEL = (
    "unknown_correlations_bounded_by_one_use_worst_case_linear_sum"
)
PACKET_SEAL_DOMAIN = b"porsche-917-f27-packet-seal-v1\0"
FINAL_REVIEW_ENVELOPE_DOMAIN = b"porsche-917-f27-final-review-envelope-v1\0"
LOCAL_CAMPAIGN_REL = Path("work/917-engine/metrology/f27")
STRICT_UTC_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)

RELEASE_GATE_IDS = (
    "scan_identity_verified",
    "three_independent_scale_controls_verified",
    "same_feature_physical_correspondence_verified",
    "traceable_provenance_verified",
    "uncertainty_budget_accepted",
    "scan_scale_verified",
    "orientation_primary_axis_verified",
    "orientation_secondary_plane_verified",
    "orientation_handedness_verified",
    "scan_orientation_verified",
    "f11_source_identity_and_scale_adapter_ready",
    "scan_variant_binding_authorized",
    "cad_reconstruction_authorized",
    "classical_solver_authorized",
    "physicsnemo_dataset_authorized",
    "physicsnemo_training_authorized",
    "omniverse_simready_authorized",
    "fabrication_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
)

CSV_FIELDS = (
    "observation_id",
    "control_id",
    "measurement_side",
    "repetition_index",
    "feature_id",
    "scan_region_token",
    "setup_id",
    "method_id",
    "quantity",
    "unit",
    "value",
    "standard_uncertainty",
    "temperature_c",
    "timestamp_utc",
    "instrument_or_software_id",
    "calibration_or_validation_evidence_ref",
    "raw_evidence_ref",
    "operator_or_lab",
    "review_status",
)

METHOD_SPECIFIC_FIELDS = {
    "CMM": (
        "probe_qualification_evidence_ref",
        "datum_alignment_procedure_evidence_ref",
    ),
    "CT": (
        "scale_artifact_evidence_ref",
        "voxel_size_report_evidence_ref",
        "reconstruction_recipe_evidence_ref",
        "segmentation_recipe_evidence_ref",
    ),
    "PHOTOGRAMMETRY": (
        "camera_calibration_evidence_ref",
        "scale_bar_certificate_evidence_ref",
        "bundle_adjustment_report_evidence_ref",
        "target_layout_evidence_ref",
    ),
    "MESH_INSPECTION": (
        "software_validation_evidence_ref",
        "measurement_script_evidence_ref",
    ),
}


class DuplicateKeyError(ValueError):
    """Raised when JSON contains duplicate keys."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(token: str) -> None:
    raise ValueError(f"non_finite_json_number_forbidden:{token}")


def _parse_json_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise ValueError(f"non_finite_json_number_forbidden:{token}")
    return value


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _regular_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _component_is_symlink(parent_fd: int, component: str) -> bool:
    try:
        observed = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISLNK(observed.st_mode)


def _open_absolute_directory_components(components: tuple[str, ...]) -> int:
    current_fd = os.open(os.path.sep, _directory_open_flags())
    try:
        for component in components:
            next_fd = os.open(component, _directory_open_flags(), dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _open_path_no_symlinks(
    path: Path,
    *,
    expect_directory: bool,
    error_label: str,
) -> int:
    """Open every path component relative to an already-open directory.

    No component is resolved in advance. Each directory and the final object is
    opened with ``O_NOFOLLOW`` then checked using ``fstat``. This prevents a
    permissive ``Path.resolve()`` from laundering a symlink before validation.
    """

    raw_path = os.fspath(path)
    if not raw_path:
        raise ValueError(f"empty_{error_label}_path_forbidden")
    candidate = Path(raw_path)
    if candidate.is_absolute():
        components = candidate.parts[1:]
        # macOS publie /var et /tmp comme alias systeme immuables vers /private.
        # Cette seule normalisation d'ancrage est explicite ; aucun composant
        # fourni sous l'ancre n'est resolu ou suivi.
        if sys.platform == "darwin" and components[:1] == ("var",):
            current_fd = _open_absolute_directory_components(("private", "var"))
            components = components[1:]
        elif sys.platform == "darwin" and components[:1] == ("tmp",):
            current_fd = _open_absolute_directory_components(("private", "tmp"))
            components = components[1:]
        else:
            current_fd = os.open(os.path.sep, _directory_open_flags())
    else:
        current_fd = os.open(".", _directory_open_flags())
        components = candidate.parts
    if not components:
        if expect_directory:
            return current_fd
        os.close(current_fd)
        raise ValueError(f"regular_file_required:{path}")
    try:
        for index, component in enumerate(components):
            if component in {"", "."}:
                continue
            final = index == len(components) - 1
            flags = (
                _directory_open_flags()
                if not final or expect_directory
                else _regular_open_flags()
            )
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                if exc.errno == errno.ELOOP or _component_is_symlink(
                    current_fd, component
                ):
                    raise ValueError(
                        f"symlink_{error_label}_forbidden:{path}"
                    ) from exc
                raise
            os.close(current_fd)
            current_fd = next_fd
        observed = os.fstat(current_fd)
        required = stat.S_ISDIR(observed.st_mode) if expect_directory else stat.S_ISREG(observed.st_mode)
        if not required:
            kind = "directory" if expect_directory else "regular_file"
            raise ValueError(f"{kind}_required:{path}")
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _open_relative_regular_file_no_symlinks(
    root_fd: int, relative: PurePosixPath, evidence_id: str
) -> int:
    current_fd = os.dup(root_fd)
    try:
        for index, component in enumerate(relative.parts):
            final = index == len(relative.parts) - 1
            flags = _regular_open_flags() if final else _directory_open_flags()
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                if exc.errno == errno.ELOOP or _component_is_symlink(
                    current_fd, component
                ):
                    raise ValueError(
                        f"evidence_symlink_component_forbidden:{evidence_id}"
                    ) from exc
                raise
            os.close(current_fd)
            current_fd = next_fd
        observed = os.fstat(current_fd)
        if not stat.S_ISREG(observed.st_mode):
            raise ValueError(f"evidence_regular_file_required:{evidence_id}")
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _read_regular_file(path: Path, maximum_bytes: int) -> bytes:
    try:
        descriptor = _open_path_no_symlinks(
            path, expect_directory=False, error_label="input"
        )
    except ValueError:
        raise
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"regular_file_required:{path}")
        if before.st_size > maximum_bytes:
            raise ValueError(f"input_too_large:{path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(maximum_bytes + 1)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if identity_before != identity_after:
            raise ValueError(f"input_changed_during_read:{path}")
        if len(data) > maximum_bytes or len(data) != before.st_size:
            raise ValueError(f"input_size_changed_or_too_large:{path}")
        return data
    finally:
        os.close(descriptor)


def _decode_json_strict(raw: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite_constant,
        parse_float=_parse_json_float,
    )
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def load_json_strict(path: Path) -> dict[str, Any]:
    raw = _read_regular_file(path, MAX_JSON_BYTES)
    return _decode_json_strict(raw, path)


def load_json_strict_with_sha256(path: Path) -> tuple[dict[str, Any], str]:
    raw = _read_regular_file(path, MAX_JSON_BYTES)
    return _decode_json_strict(raw, path), hashlib.sha256(raw).hexdigest()


def load_csv_strict(path: Path) -> list[dict[str, str]]:
    raw = _read_regular_file(path, MAX_CSV_BYTES)
    if len(raw) > MAX_CSV_BYTES:
        raise ValueError(f"input_too_large:{path}")
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != list(CSV_FIELDS):
        raise ValueError("csv_header_mismatch")
    rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError("csv_extra_column_value")
    return rows


def sha256_file(path: Path) -> str:
    try:
        descriptor = _open_path_no_symlinks(
            path, expect_directory=False, error_label="hash_input"
        )
    except ValueError:
        raise
    return _sha256_open_descriptor(descriptor, f"{path}")


def _sha256_open_descriptor(descriptor: int, label: str) -> str:
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"regular_hash_input_required:{label}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError(f"hash_input_changed_during_read:{label}")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _upstream_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": source_id,
            "path": str(relative),
            "sha256": APPROVED_UPSTREAM_SHA256[source_id],
            "role": UPSTREAM_ROLES[source_id],
        }
        for source_id, relative in UPSTREAMS.items()
    ]


def _evidence_slot(kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "independent_source_id": None,
        "evidence_ref": None,
        "review_status": "missing",
    }


def _review_slot(role: str) -> dict[str, Any]:
    return {
        "role": role,
        "reviewer_id": None,
        "decision": None,
        "reviewed_acquisition_packet_sha256": None,
        "signed_report_evidence_ref": None,
        "signed_at_utc": None,
    }


def _method_slot(method_id: str) -> dict[str, Any]:
    common = {
        "method_id": method_id,
        "selected": None,
        "selection_justification": None,
        "instrument_or_software_id": None,
        "software_name_version": None,
        "procedure_evidence_ref": None,
        "calibration_or_validation_evidence_ref": None,
        "operator_or_lab": None,
        "measurement_start_utc": None,
        "measurement_end_utc": None,
    }
    common["method_specific"] = {
        field: None for field in METHOD_SPECIFIC_FIELDS[method_id]
    }
    return common


def _scale_control_slot(control_id: str) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "f21_slot_ref": control_id,
        "physical_feature_id": None,
        "scan_region_token": None,
        "feature_endpoint_definition": None,
        "physical_method_id": None,
        "scan_method_id": None,
        "same_feature_correspondence_evidence_ref": None,
        "uncertainty_budget_id": f"UB-{control_id}",
        "minimum_physical_repetitions": REPEAT_COUNT,
        "minimum_scan_repetitions": REPEAT_COUNT,
        "independent_from_other_controls": None,
        "status": "missing",
    }


def _datum_slot(slot_id: str, datum_ref: str, kind: str) -> dict[str, Any]:
    return {
        "datum_id": slot_id,
        "f21_slot_ref": slot_id,
        "f16_datum_ref": datum_ref,
        "kind": kind,
        "physical_feature_id": None,
        "scan_region_token": None,
        "physical_method_id": None,
        "scan_method_id": None,
        "semantic_direction_rule": None,
        "physical_fit_evidence_ref": None,
        "scan_fit_evidence_ref": None,
        "registration_evidence_ref": None,
        "fit_result": {
            "origin_obj_units": None,
            "direction_or_normal": None,
            "handedness_token": None,
            "fit_residual_obj_units": None,
            "registration_residual_mm": None,
            "angular_standard_uncertainty_deg": None,
        },
        "status": "missing",
    }


def _orientation_relation_contract() -> dict[str, Any]:
    return {
        "contract_role": "candidate_coordinate_consistency_only_not_release_authority",
        "primary_axis_must_lie_in_secondary_plane": True,
        "transform_row_0_must_equal_primary_axis_direction": True,
        "transform_row_2_must_equal_secondary_plane_normal": True,
        "transform_row_1_must_equal_row_2_cross_row_0": True,
        "translation_must_map_primary_axis_origin_to_engine_origin": True,
        "handedness_witness_must_transform_to_positive_engine_y": True,
        "required_handedness_token": HANDEDNESS_TOKEN,
        "numeric_consistency_absolute_tolerance": NUMERICAL_CONSISTENCY_ABS_TOL,
    }


def _uncertainty_slot(control_id: str) -> dict[str, Any]:
    return {
        "budget_id": f"UB-{control_id}",
        "control_id": control_id,
        "measurement_model": None,
        "contributors_evidence_ref": None,
        "correlation_assumptions": None,
        "maximum_relative_standard_uncertainty": None,
        "maximum_relative_repeatability_range": None,
        "predeclared_before_acquisition": None,
        "approved_protocol_evidence_ref": None,
        "status": "missing",
    }


def _custody_event(sequence: int, event_type: str) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_type": event_type,
        "timestamp_utc": None,
        "actor_id": None,
        "location_or_system_id": None,
        "input_identifier_or_sha256": None,
        "output_identifier_or_sha256": None,
        "evidence_ref": None,
        "witness_or_review_status": "missing",
    }


def _candidate_variant_ids(root: Path) -> list[str]:
    del root
    return list(CANDIDATE_VARIANT_IDS)


def build_json_template(root: Path) -> dict[str, Any]:
    candidates = _candidate_variant_ids(root)
    return {
        "$comment": (
            "F27 est un formulaire vierge a copier sous work/. Il ne contient "
            "aucune mesure et ne libere ni variante, ni CAO, ni simulation, ni fabrication."
        ),
        "schema_version": "1.0.0",
        "phase": "F27",
        "record_status": "blank_template_not_executed",
        "upstream_manifest": _upstream_manifest(root),
        "authority_boundary": {
            "documentary_dimensions_may_calibrate_scan": False,
            "numerical_closest_candidate_may_select_variant": False,
            "scan_render_or_filename_may_define_orientation": False,
            "validator_may_open_engineering_release_gates": False,
            "local_measurements_and_evidence_must_remain_outside_git": True,
        },
        "campaign": {
            "campaign_id": None,
            "record_revision": None,
            "campaign_owner": None,
            "metrology_lab": None,
            "planned_start_utc": None,
            "protocol_frozen_at_utc": None,
            "preacquisition_approval_evidence_ref": None,
        },
        "source_binding": {
            "expected_scan_sha256": SCAN_SHA256,
            "working_scan_sha256": None,
            "physical_asset_or_part_set_id": None,
            "physical_asset_serial_or_marking_evidence_ref": None,
            "identity_status": "missing",
        },
        "chain_of_custody": {
            "custody_id": None,
            "events": [
                _custody_event(1, "physical_asset_intake"),
                _custody_event(2, "scan_working_copy_creation"),
                _custody_event(3, "instrument_calibration_verification"),
                _custody_event(4, "acquisition_open"),
                _custody_event(5, "acquisition_close"),
                _custody_event(6, "evidence_manifest_seal"),
            ],
        },
        "environment": {
            "stabilization_procedure_evidence_ref": None,
            "temperature_instrument_id": None,
            "temperature_calibration_evidence_ref": None,
            "temperature_c": None,
            "relative_humidity_percent": None,
            "environment_log_evidence_ref": None,
        },
        "methods": [_method_slot(method_id) for method_id in METHOD_IDS],
        "scale_protocol": {
            "required_control_count": len(SCALE_CONTROL_IDS),
            "maximum_relative_scale_spread": MAX_RELATIVE_SCALE_SPREAD,
            "same_feature_scan_to_physical_required": True,
            "distinct_feature_and_scan_region_per_control_required": True,
            "reposition_or_independent_refit_between_repetition_groups_required": True,
            "controls": [
                _scale_control_slot(control_id)
                for control_id in SCALE_CONTROL_IDS
            ],
        },
        "uncertainty_budgets": [
            _uncertainty_slot(control_id) for control_id in SCALE_CONTROL_IDS
        ],
        "orientation_protocol": {
            "datum_count": len(DATUM_DEFINITIONS),
            "relation_contract": _orientation_relation_contract(),
            "datums": [_datum_slot(*definition) for definition in DATUM_DEFINITIONS],
            "scan_to_engine_transform": {
                "scale_mm_per_obj_unit": None,
                "rotation_matrix_3x3": None,
                "translation_mm": None,
                "transform_uncertainty_evidence_ref": None,
                "status": "missing",
            },
        },
        "variant_identification": {
            "candidate_registry_source": str(UPSTREAMS["f13_scan_metrology"]),
            "allowed_candidate_variant_ids": candidates,
            "selected_candidate_variant_id": None,
            "f16_branch_crosswalk_evidence_ref": None,
            "identity_evidence": [
                _evidence_slot("direct_marking_or_part_identity"),
                _evidence_slot("part_number_or_configuration_crosswalk"),
                _evidence_slot("teardown_or_architecture_discriminant"),
                _evidence_slot("calibrated_metrology_comparison"),
            ],
            "conflicting_evidence_log_evidence_ref": None,
            "adjudication_status": "missing",
        },
        "evidence_index": [],
        "independent_reviews": {
            "metrology": _review_slot("qualified_metrology_reviewer"),
            "variant_engineering": _review_slot("independent_engineering_reviewer"),
            "final_envelope": {
                "sha256": None,
                "generated_at_utc": None,
            },
        },
        "current_readiness": {
            "campaign_executed": False,
            "evidence_packet_complete": False,
            "scale_candidate_ready_for_review": False,
            "orientation_candidate_ready_for_review": False,
            "variant_candidate_ready_for_review": False,
            "binding_adapter_implemented": False,
        },
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        "repository_content_boundary": {
            "tracked_template_contains_raw_scan": False,
            "tracked_template_contains_proprietary_geometry": False,
            "tracked_template_contains_physical_measurements": False,
            "tracked_template_contains_physical_asset_identifier": False,
            "tracked_template_contains_operator_personal_data": False,
            "filled_record_and_evidence_must_remain_outside_git": True,
        },
    }


def build_csv_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for control_id in SCALE_CONTROL_IDS:
        for side, unit in (("physical", "mm"), ("scan", "OBJ_unit")):
            for repetition in range(1, REPEAT_COUNT + 1):
                row = {field: "" for field in CSV_FIELDS}
                row.update(
                    {
                        "observation_id": (
                            f"{control_id}-{side.upper()}-{repetition:02d}"
                        ),
                        "control_id": control_id,
                        "measurement_side": side,
                        "repetition_index": str(repetition),
                        "quantity": "same_feature_distance",
                        "unit": unit,
                        "review_status": "missing",
                    }
                )
                rows.append(row)
    return rows


def render_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def validate_upstreams(root: Path) -> list[str]:
    errors: list[str] = []
    loaded: dict[str, dict[str, Any]] = {}
    for source_id, relative in UPSTREAMS.items():
        source_path = root / relative
        try:
            source, observed_sha256 = load_json_strict_with_sha256(source_path)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(
                f"approved_upstream_unreadable:{source_id}:{type(exc).__name__}"
            )
            continue
        if observed_sha256 != APPROVED_UPSTREAM_SHA256[source_id]:
            errors.append(f"approved_upstream_sha256_mismatch:{source_id}")
        loaded[source_id] = source
    if set(loaded) != set(UPSTREAMS):
        return sorted(set(errors))

    f13 = loaded["f13_scan_metrology"]
    f16 = loaded["f16_kinematic_interfaces"]
    f21 = loaded["f21_scale_orientation"]

    if (
        f13.get("schema_version") != "1.0.0"
        or f13.get("phase") != "F13"
        or f13.get("status") != "hypothesis_only_physical_calibration_missing"
    ):
        errors.append("f13_identity_invariant_mismatch")
    if (
        f16.get("schema_version") != "1.0.0"
        or f16.get("phase") != "F16-001"
        or f16.get("status")
        != "kinematic_interface_contract_ready_all_geometry_and_motion_blocked"
    ):
        errors.append("f16_identity_invariant_mismatch")
    if (
        f21.get("schema_version") != "1.0.0"
        or f21.get("phase") != "F21"
        or f21.get("status")
        != "acquisition_sheet_ready_scale_and_orientation_unverified"
    ):
        errors.append("f21_identity_invariant_mismatch")

    if f21.get("asset", {}).get("source_scan_sha256") != SCAN_SHA256:
        errors.append("f21_scan_sha256_mismatch")
    acquisition_policy = f21.get("acquisition_record_policy", {})
    for field in (
        "working_record_must_remain_outside_git",
        "exact_scan_hash_required",
        "exact_physical_asset_identity_required",
        "three_distinct_physical_features_required",
        "three_distinct_scan_regions_required",
        "same_feature_scan_to_physical_correspondence_required",
        "traceable_instrument_and_calibration_required",
        "uncertainty_required_per_control",
    ):
        if acquisition_policy.get(field) is not True:
            errors.append(f"f21_acquisition_policy_invariant_mismatch:{field}")
    for field in (
        "tracked_contract_may_contain_coordinates",
        "tracked_contract_may_contain_measurements",
    ):
        if acquisition_policy.get(field) is not False:
            errors.append(f"f21_acquisition_policy_invariant_mismatch:{field}")
    if [item.get("id") for item in f21.get("scale_control_slots", [])] != list(
        SCALE_CONTROL_IDS
    ):
        errors.append("f21_scale_slots_incompatible")
    if f21.get("f11_compatibility", {}).get("maximum_relative_spread") != MAX_RELATIVE_SCALE_SPREAD:
        errors.append("f21_scale_spread_policy_mismatch")
    if [
        (item.get("id"), item.get("f16_datum_ref"))
        for item in f21.get("orientation_datum_slots", [])
    ] != [(item[0], item[1]) for item in DATUM_DEFINITIONS]:
        errors.append("f21_orientation_slots_incompatible")
    if any(f21.get("release_gates", {}).values()):
        errors.append("f21_release_gate_open")
    if any(
        value not in (False, 0)
        for key, value in f21.get("current_readiness", {}).items()
        if key.endswith("_ready") or key.startswith("completed_")
    ):
        errors.append("f21_current_readiness_open")
    documentary = f21.get("documentary_dimension_exclusion", {})
    if (
        documentary.get("documentary_source_has_scan_scale_authority") is not False
        or documentary.get("documentary_source_has_scan_orientation_authority")
        is not False
        or documentary.get("exception_without_physical_metrology") is not False
    ):
        errors.append("f21_documentary_authority_boundary_open")

    controls = f13.get("required_physical_controls", [])
    if len(controls) != 3 or any(
        not isinstance(item, dict)
        or item.get("minimum_measurements") != REPEAT_COUNT
        or item.get("status") != "missing"
        for item in controls
    ):
        errors.append("f13_minimum_repeat_policy_incompatible")
    candidate_records = f13.get("public_facts", {}).get("candidate_bores", [])
    candidates = [
        item.get("variant_id") for item in candidate_records if isinstance(item, dict)
    ]
    if candidates != list(CANDIDATE_VARIANT_IDS):
        errors.append("f13_candidate_registry_incompatible")
    if f13.get("derivation_policy", {}).get("selection_allowed") is not False:
        errors.append("f13_numerical_selection_must_remain_forbidden")
    if any(
        value is not False
        for key, value in f13.get("release_authority", {}).items()
        if key.endswith("_enabled")
    ):
        errors.append("f13_release_authority_open")

    fixed_datum_records = f16.get("datum_registry_contract", {}).get(
        "fixed_datums", []
    )
    fixed_datums = {
        item.get("id"): item
        for item in fixed_datum_records
        if isinstance(item, dict)
    }
    if any(
        item[1] not in fixed_datums
        or fixed_datums[item[1]].get("status") != "unknown_unverified"
        or fixed_datums[item[1]].get("origin_mm") is not None
        for item in DATUM_DEFINITIONS
    ):
        errors.append("f16_required_datum_missing")
    work_branch = f16.get("work_branch", {})
    if (
        work_branch.get("scan_binding") is not False
        or work_branch.get("scan_asset_id") is not None
        or work_branch.get("scan_scale_mm_per_unit") is not None
        or work_branch.get("variant_identity_proven") is not False
        or work_branch.get("manufacturing_identity_proven") is not False
    ):
        errors.append("f16_scan_binding_must_remain_false")
    if any(f16.get("release_gates", {}).values()):
        errors.append("f16_release_gate_open")
    return sorted(set(errors))


def validate_templates(root: Path) -> list[str]:
    errors = validate_upstreams(root)
    expected_json = build_json_template(root)
    observed_json = load_json_strict(root / JSON_TEMPLATE_REL)
    if observed_json != expected_json:
        errors.append("canonical_f27_json_template_mismatch")
    expected_csv = render_csv(build_csv_rows()).encode("utf-8")
    observed_csv = _read_regular_file(root / CSV_TEMPLATE_REL, MAX_CSV_BYTES)
    if observed_csv != expected_csv:
        errors.append("canonical_f27_csv_template_mismatch")
    if any(expected_json["release_gates"].values()):
        errors.append("template_release_gate_open")
    return sorted(set(errors))


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_canonical_identifier(value: Any) -> bool:
    return (
        _is_nonempty_string(value)
        and value == value.strip()
        and unicodedata.normalize("NFC", value) == value
    )


def _require_canonical_identifier(
    value: Any, label: str, errors: list[str]
) -> None:
    if not _is_canonical_identifier(value):
        errors.append(f"canonical_identifier_required:{label}")


def _parse_positive(value: str, label: str, errors: list[str]) -> float | None:
    if isinstance(value, bool):
        errors.append(f"boolean_numeric_value_forbidden:{label}")
        return None
    try:
        parsed = float(value)
    except (OverflowError, TypeError, ValueError):
        errors.append(f"invalid_numeric_value:{label}")
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        errors.append(f"positive_finite_value_required:{label}")
        return None
    return parsed


def _parse_finite(value: Any, label: str, errors: list[str]) -> float | None:
    if isinstance(value, bool):
        errors.append(f"boolean_numeric_value_forbidden:{label}")
        return None
    try:
        parsed = float(value)
    except (OverflowError, TypeError, ValueError):
        errors.append(f"invalid_numeric_value:{label}")
        return None
    if not math.isfinite(parsed):
        errors.append(f"finite_value_required:{label}")
        return None
    return parsed


def _parse_utc(value: Any, label: str, errors: list[str]) -> datetime | None:
    if not _is_nonempty_string(value) or STRICT_UTC_PATTERN.fullmatch(value) is None:
        errors.append(f"utc_timestamp_required:{label}")
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"invalid_utc_timestamp:{label}")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        errors.append(f"utc_timezone_aware_timestamp_required:{label}")
        return None
    return parsed


def _require_fields(
    mapping: Any, fields: tuple[str, ...] | list[str], prefix: str, errors: list[str]
) -> None:
    if not isinstance(mapping, dict):
        errors.append(f"object_required:{prefix}")
        return
    for field in fields:
        if not _is_nonempty_string(mapping.get(field)):
            errors.append(f"missing_required_field:{prefix}.{field}")


def _evidence_map(record: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    entries = record.get("evidence_index")
    if not isinstance(entries, list):
        errors.append("evidence_index_list_required")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(entries):
        prefix = f"evidence_index[{index}]"
        if not isinstance(item, dict):
            errors.append(f"object_required:{prefix}")
            continue
        expected_keys = {
            "evidence_id",
            "kind",
            "relative_path",
            "sha256",
            "contains_proprietary_or_sensitive_data",
            "commit_allowed",
        }
        if set(item) != expected_keys:
            errors.append(f"evidence_entry_keys_mismatch:{prefix}")
        evidence_id = item.get("evidence_id")
        if not _is_nonempty_string(evidence_id):
            errors.append(f"missing_required_field:{prefix}.evidence_id")
            continue
        if not _is_canonical_identifier(evidence_id):
            errors.append(f"canonical_identifier_required:{prefix}.evidence_id")
        if evidence_id in result:
            errors.append(f"duplicate_evidence_id:{evidence_id}")
            continue
        if not _is_nonempty_string(item.get("kind")):
            errors.append(f"missing_required_field:{prefix}.kind")
        relative = item.get("relative_path")
        if not _is_nonempty_string(relative):
            errors.append(f"missing_required_field:{prefix}.relative_path")
        else:
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts or str(pure) != relative:
                errors.append(f"unsafe_evidence_relative_path:{evidence_id}")
        if not _is_sha256(item.get("sha256")):
            errors.append(f"invalid_evidence_sha256:{evidence_id}")
        if not isinstance(item.get("contains_proprietary_or_sensitive_data"), bool):
            errors.append(f"evidence_sensitivity_boolean_required:{evidence_id}")
        if item.get("commit_allowed") is not False:
            errors.append(f"evidence_commit_must_be_false:{evidence_id}")
        result[evidence_id] = item
    return result


def _collect_evidence_refs(value: Any, path: str = "") -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if (key.endswith("_evidence_ref") or key == "evidence_ref") and child is not None:
                refs.append((child_path, child))
            elif key != "evidence_index":
                refs.extend(_collect_evidence_refs(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_collect_evidence_refs(child, f"{path}[{index}]"))
    return refs


def _expected_evidence_kind(record: dict[str, Any], path: str) -> str:
    if path.startswith("variant_identification.identity_evidence["):
        try:
            index = int(path.split("[", 1)[1].split("]", 1)[0])
            identity_kind = record["variant_identification"]["identity_evidence"][
                index
            ]["kind"]
        except (IndexError, KeyError, TypeError, ValueError):
            return "invalid_variant_identity_role"
        return f"variant_identity:{identity_kind}"
    if path.startswith("chain_of_custody.events["):
        try:
            index = int(path.split("[", 1)[1].split("]", 1)[0])
            event_type = record["chain_of_custody"]["events"][index]["event_type"]
        except (IndexError, KeyError, TypeError, ValueError):
            return "invalid_custody_role"
        return f"chain_of_custody:{event_type}"
    field = path.rsplit(".", 1)[-1]
    fixed_roles = {
        "preacquisition_approval_evidence_ref": "preacquisition_protocol_approval",
        "physical_asset_serial_or_marking_evidence_ref": "physical_asset_identity",
        "stabilization_procedure_evidence_ref": "environment_stabilization_procedure",
        "temperature_calibration_evidence_ref": "temperature_calibration",
        "environment_log_evidence_ref": "environment_log",
        "procedure_evidence_ref": "measurement_method_procedure",
        "calibration_or_validation_evidence_ref": "calibration_or_validation",
        "same_feature_correspondence_evidence_ref": "same_feature_correspondence",
        "contributors_evidence_ref": "uncertainty_contributors",
        "approved_protocol_evidence_ref": "uncertainty_protocol_approval",
        "physical_fit_evidence_ref": "physical_datum_fit",
        "scan_fit_evidence_ref": "scan_datum_fit",
        "registration_evidence_ref": "datum_registration",
        "transform_uncertainty_evidence_ref": "transform_uncertainty",
        "f16_branch_crosswalk_evidence_ref": "variant_branch_crosswalk",
        "conflicting_evidence_log_evidence_ref": "variant_conflicting_evidence_log",
        "signed_report_evidence_ref": "signed_independent_review_report",
    }
    if field in fixed_roles:
        return fixed_roles[field]
    if field.endswith("_evidence_ref"):
        return field[: -len("_evidence_ref")]
    if field == "evidence_ref":
        return "generic_evidence_role_forbidden"
    return "unknown_evidence_role"


def _bind_evidence_roles(
    record: dict[str, Any],
    rows: list[dict[str, str]],
    evidence: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    bindings: dict[str, set[str]] = {}
    for path, evidence_id in _collect_evidence_refs(record):
        if not _is_nonempty_string(evidence_id) or evidence_id not in evidence:
            errors.append(f"unresolved_evidence_ref:{path}")
            continue
        expected_kind = _expected_evidence_kind(record, path)
        bindings.setdefault(evidence_id, set()).add(expected_kind)
        if evidence[evidence_id].get("kind") != expected_kind:
            errors.append(f"evidence_kind_role_mismatch:{path}")
    for index, row in enumerate(rows):
        observation_id = row.get("observation_id") or str(index)
        for field, expected_kind in (
            ("calibration_or_validation_evidence_ref", "calibration_or_validation"),
            ("raw_evidence_ref", "raw_measurement_data"),
        ):
            evidence_id = row.get(field)
            if not _is_nonempty_string(evidence_id) or evidence_id not in evidence:
                errors.append(f"unresolved_csv_evidence_ref:{index}.{field}")
                continue
            bindings.setdefault(evidence_id, set()).add(expected_kind)
            if evidence[evidence_id].get("kind") != expected_kind:
                errors.append(
                    f"evidence_kind_role_mismatch:csv.{observation_id}.{field}"
                )
    for evidence_id, kinds in bindings.items():
        if len(kinds) != 1:
            errors.append(f"evidence_id_reused_across_incompatible_roles:{evidence_id}")
    digest_kinds: dict[str, set[str]] = {}
    for evidence_id, kinds in bindings.items():
        item = evidence.get(evidence_id)
        if item is None or not _is_sha256(item.get("sha256")):
            continue
        digest_kinds.setdefault(item["sha256"], set()).update(kinds)
    for digest, kinds in digest_kinds.items():
        if len(kinds) > 1:
            errors.append(
                f"evidence_digest_reused_across_incompatible_roles:{digest}"
            )
    unreferenced = set(evidence) - set(bindings)
    for evidence_id in sorted(unreferenced):
        errors.append(f"unreferenced_evidence_entry:{evidence_id}")

    identity_refs = record.get("variant_identification", {}).get(
        "identity_evidence", []
    )
    if isinstance(identity_refs, list):
        identifiers = [
            item.get("evidence_ref") for item in identity_refs if isinstance(item, dict)
        ]
        if (
            len(identifiers) != 4
            or any(not _is_nonempty_string(identifier) for identifier in identifiers)
            or len(set(identifiers)) != 4
        ):
            errors.append("variant_identity_evidence_files_must_be_distinct")
        elif any(identifier not in evidence for identifier in identifiers):
            errors.append("variant_identity_evidence_digests_must_be_distinct")
        else:
            identity_digests = [
                evidence[identifier].get("sha256") for identifier in identifiers
            ]
            if any(not _is_sha256(digest) for digest in identity_digests) or len(
                set(identity_digests)
            ) != 4:
                errors.append("variant_identity_evidence_digests_must_be_distinct")
    reviews = record.get("independent_reviews", {})
    if isinstance(reviews, dict):
        review_refs = [
            reviews[key].get("signed_report_evidence_ref")
            for key in ("metrology", "variant_engineering")
            if isinstance(reviews.get(key), dict)
        ]
        if (
            len(review_refs) != 2
            or any(not _is_nonempty_string(identifier) for identifier in review_refs)
            or len(set(review_refs)) != 2
        ):
            errors.append("independent_review_reports_must_be_distinct")
        elif any(identifier not in evidence for identifier in review_refs):
            errors.append("independent_review_report_digests_must_be_distinct")
        else:
            review_digests = [
                evidence[identifier].get("sha256") for identifier in review_refs
            ]
            if any(not _is_sha256(digest) for digest in review_digests) or len(
                set(review_digests)
            ) != 2:
                errors.append("independent_review_report_digests_must_be_distinct")


def _verify_evidence_files(
    evidence: dict[str, dict[str, Any]],
    root: Path,
    errors: list[str],
    packet_input_identities: set[tuple[int, int]] | None = None,
) -> None:
    try:
        root_fd = _open_path_no_symlinks(
            root, expect_directory=True, error_label="evidence_root"
        )
    except (OSError, ValueError):
        errors.append("evidence_root_directory_required_without_symlink")
        return
    opened_identities: dict[tuple[int, int], str] = {}
    observed_paths: dict[str, str] = {}
    try:
        for evidence_id, item in evidence.items():
            relative = item.get("relative_path")
            if not _is_nonempty_string(relative):
                continue
            pure_relative = PurePosixPath(relative)
            if (
                pure_relative.is_absolute()
                or ".." in pure_relative.parts
                or str(pure_relative) != relative
            ):
                # _evidence_map a deja inscrit l'erreur de schema. Ne jamais
                # tenter d'ouvrir un chemin unsafe, meme dans un paquet voue a
                # l'echec ferme.
                continue
            if relative in observed_paths:
                errors.append(
                    f"evidence_relative_path_reused:{observed_paths[relative]}:{evidence_id}"
                )
                continue
            observed_paths[relative] = evidence_id
            try:
                descriptor = _open_relative_regular_file_no_symlinks(
                    root_fd, pure_relative, evidence_id
                )
            except FileNotFoundError:
                errors.append(f"evidence_file_missing:{evidence_id}")
                continue
            except (OSError, ValueError) as exc:
                message = str(exc)
                if message.startswith("evidence_symlink_component_forbidden:"):
                    errors.append(message)
                else:
                    errors.append(f"evidence_regular_file_required:{evidence_id}")
                continue
            observed = os.fstat(descriptor)
            if observed.st_size == 0:
                errors.append(f"evidence_file_empty:{evidence_id}")
                os.close(descriptor)
                continue
            identity = (observed.st_dev, observed.st_ino)
            if identity in (packet_input_identities or set()):
                errors.append(f"evidence_file_aliases_packet_input:{evidence_id}")
            previous_id = opened_identities.get(identity)
            if previous_id is not None:
                errors.append(f"evidence_file_identity_reused:{previous_id}:{evidence_id}")
            else:
                opened_identities[identity] = evidence_id
            if _sha256_open_descriptor(descriptor, evidence_id) != item.get("sha256"):
                errors.append(f"evidence_sha256_mismatch:{evidence_id}")
    finally:
        os.close(root_fd)


def _validate_record_key_shape(
    value: Any,
    template: Any,
    path: str,
    errors: list[str],
) -> None:
    if path == "evidence_index":
        return
    if isinstance(template, dict):
        if not isinstance(value, dict):
            errors.append(f"record_object_required:{path or '<root>'}")
            return
        if set(value) != set(template):
            errors.append(f"record_keys_mismatch:{path or '<root>'}")
            return
        for key in template:
            child_path = f"{path}.{key}" if path else key
            _validate_record_key_shape(value[key], template[key], child_path, errors)
    elif isinstance(template, list):
        if not isinstance(value, list):
            errors.append(f"record_list_required:{path}")
            return
        if len(value) != len(template):
            errors.append(f"record_fixed_list_length_mismatch:{path}")
            return
        for index, child_template in enumerate(template):
            _validate_record_key_shape(
                value[index], child_template, f"{path}[{index}]", errors
            )


def _validate_shape(record: dict[str, Any], root: Path, errors: list[str]) -> None:
    template = build_json_template(root)
    _validate_record_key_shape(record, template, "", errors)
    if set(record) != set(template):
        errors.append("record_top_level_keys_mismatch")
    if record.get("schema_version") != "1.0.0" or record.get("phase") != "F27":
        errors.append("record_schema_or_phase_mismatch")
    if record.get("upstream_manifest") != template["upstream_manifest"]:
        errors.append("upstream_manifest_mismatch")
    if record.get("authority_boundary") != template["authority_boundary"]:
        errors.append("authority_boundary_mismatch")
    if record.get("repository_content_boundary") != template["repository_content_boundary"]:
        errors.append("repository_content_boundary_mismatch")
    if record.get("record_status") != "campaign_execution_complete_pending_binding_review":
        errors.append("campaign_record_status_incomplete")
    gates = record.get("release_gates")
    if not isinstance(gates, dict) or set(gates) != set(RELEASE_GATE_IDS):
        errors.append("release_gate_set_mismatch")
    elif any(value is not False for value in gates.values()):
        errors.append("all_release_gates_must_remain_false")
    readiness = record.get("current_readiness")
    if not isinstance(readiness, dict) or any(value is not False for value in readiness.values()):
        errors.append("record_readiness_flags_must_remain_false")


def _validate_methods(
    record: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    methods = record.get("methods")
    if (
        not isinstance(methods, list)
        or len(methods) != len(METHOD_IDS)
        or any(not isinstance(item, dict) for item in methods)
        or [item.get("method_id") for item in methods] != list(METHOD_IDS)
    ):
        errors.append("method_registry_mismatch")
        return {}
    selected: dict[str, dict[str, Any]] = {}
    for item in methods:
        method_id = item["method_id"]
        if not isinstance(item.get("selected"), bool):
            errors.append(f"method_selection_boolean_required:{method_id}")
            continue
        if item["selected"] is False:
            continue
        selected[method_id] = item
        _require_fields(
            item,
            [
                "selection_justification",
                "instrument_or_software_id",
                "software_name_version",
                "procedure_evidence_ref",
                "calibration_or_validation_evidence_ref",
                "operator_or_lab",
                "measurement_start_utc",
                "measurement_end_utc",
            ],
            f"methods.{method_id}",
            errors,
        )
        started = _parse_utc(item.get("measurement_start_utc"), f"methods.{method_id}.measurement_start_utc", errors)
        ended = _parse_utc(item.get("measurement_end_utc"), f"methods.{method_id}.measurement_end_utc", errors)
        if started is not None and ended is not None and started > ended:
            errors.append(f"method_time_window_reversed:{method_id}")
        specific = item.get("method_specific")
        if not isinstance(specific, dict) or set(specific) != set(METHOD_SPECIFIC_FIELDS[method_id]):
            errors.append(f"method_specific_keys_mismatch:{method_id}")
        else:
            _require_fields(
                specific,
                list(METHOD_SPECIFIC_FIELDS[method_id]),
                f"methods.{method_id}.method_specific",
                errors,
            )
    if "MESH_INSPECTION" not in selected:
        errors.append("mesh_inspection_method_required")
    if not (set(selected) & PHYSICAL_METHOD_IDS):
        errors.append("physical_metrology_method_required")
    return selected


def _validate_scale_controls(
    record: dict[str, Any], selected_methods: dict[str, dict[str, Any]], errors: list[str]
) -> dict[str, dict[str, Any]]:
    protocol = record.get("scale_protocol")
    if not isinstance(protocol, dict):
        errors.append("scale_protocol_object_required")
        return {}
    if protocol.get("required_control_count") != 3:
        errors.append("exactly_three_scale_controls_required")
    if protocol.get("maximum_relative_scale_spread") != MAX_RELATIVE_SCALE_SPREAD:
        errors.append("scale_spread_policy_mismatch")
    for flag in (
        "same_feature_scan_to_physical_required",
        "distinct_feature_and_scan_region_per_control_required",
        "reposition_or_independent_refit_between_repetition_groups_required",
    ):
        if protocol.get(flag) is not True:
            errors.append(f"scale_protocol_flag_required:{flag}")
    controls = protocol.get("controls")
    if (
        not isinstance(controls, list)
        or len(controls) != len(SCALE_CONTROL_IDS)
        or any(not isinstance(item, dict) for item in controls)
        or [item.get("control_id") for item in controls] != list(SCALE_CONTROL_IDS)
    ):
        errors.append("scale_control_registry_mismatch")
        return {}
    result: dict[str, dict[str, Any]] = {}
    features: list[str] = []
    regions: list[str] = []
    for item in controls:
        control_id = item["control_id"]
        result[control_id] = item
        if item.get("f21_slot_ref") != control_id:
            errors.append(f"f21_scale_slot_ref_mismatch:{control_id}")
        if item.get("uncertainty_budget_id") != f"UB-{control_id}":
            errors.append(f"scale_uncertainty_budget_link_mismatch:{control_id}")
        _require_fields(
            item,
            [
                "physical_feature_id",
                "scan_region_token",
                "feature_endpoint_definition",
                "physical_method_id",
                "scan_method_id",
                "same_feature_correspondence_evidence_ref",
                "uncertainty_budget_id",
            ],
            f"scale_protocol.controls.{control_id}",
            errors,
        )
        feature = item.get("physical_feature_id")
        region = item.get("scan_region_token")
        if _is_nonempty_string(feature):
            _require_canonical_identifier(
                feature,
                f"scale_protocol.controls.{control_id}.physical_feature_id",
                errors,
            )
            features.append(unicodedata.normalize("NFC", feature.strip()))
        if _is_nonempty_string(region):
            _require_canonical_identifier(
                region,
                f"scale_protocol.controls.{control_id}.scan_region_token",
                errors,
            )
            regions.append(unicodedata.normalize("NFC", region.strip()))
        physical_method_id = item.get("physical_method_id")
        scan_method_id = item.get("scan_method_id")
        if (
            not isinstance(physical_method_id, str)
            or physical_method_id not in PHYSICAL_METHOD_IDS
        ):
            errors.append(f"physical_method_invalid:{control_id}")
        if (
            not isinstance(physical_method_id, str)
            or physical_method_id not in selected_methods
        ):
            errors.append(f"physical_method_not_selected:{control_id}")
        if scan_method_id != "MESH_INSPECTION":
            errors.append(f"scan_method_must_be_mesh_inspection:{control_id}")
        if not isinstance(scan_method_id, str) or scan_method_id not in selected_methods:
            errors.append(f"scan_method_not_selected:{control_id}")
        if item.get("minimum_physical_repetitions") != REPEAT_COUNT or item.get("minimum_scan_repetitions") != REPEAT_COUNT:
            errors.append(f"scale_repeat_count_mismatch:{control_id}")
        if item.get("independent_from_other_controls") is not True:
            errors.append(f"control_independence_not_confirmed:{control_id}")
        if item.get("status") != "reviewed_complete":
            errors.append(f"scale_control_not_reviewed_complete:{control_id}")
    if len(features) != 3 or len(set(features)) != 3:
        errors.append("three_distinct_physical_features_required")
    if len(regions) != 3 or len(set(regions)) != 3:
        errors.append("three_distinct_scan_regions_required")
    return result


def _validate_uncertainty_budgets(
    record: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    budgets = record.get("uncertainty_budgets")
    if (
        not isinstance(budgets, list)
        or len(budgets) != len(SCALE_CONTROL_IDS)
        or any(not isinstance(item, dict) for item in budgets)
        or [item.get("control_id") for item in budgets] != list(SCALE_CONTROL_IDS)
    ):
        errors.append("uncertainty_budget_registry_mismatch")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in budgets:
        control_id = item["control_id"]
        result[control_id] = item
        if item.get("budget_id") != f"UB-{control_id}":
            errors.append(f"uncertainty_budget_id_mismatch:{control_id}")
        _require_fields(
            item,
            [
                "measurement_model",
                "contributors_evidence_ref",
                "correlation_assumptions",
                "approved_protocol_evidence_ref",
            ],
            f"uncertainty_budgets.{control_id}",
            errors,
        )
        if item.get("correlation_assumptions") != UNCERTAINTY_CORRELATION_MODEL:
            errors.append(f"unsupported_uncertainty_correlation_model:{control_id}")
        for field in (
            "maximum_relative_standard_uncertainty",
            "maximum_relative_repeatability_range",
        ):
            raw_value = item.get(field)
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                errors.append(f"json_numeric_required:uncertainty_budgets.{control_id}.{field}")
            _parse_positive(
                raw_value, f"uncertainty_budgets.{control_id}.{field}", errors
            )
        if item.get("predeclared_before_acquisition") is not True:
            errors.append(f"uncertainty_budget_not_predeclared:{control_id}")
        if item.get("status") != "approved_before_acquisition":
            errors.append(f"uncertainty_budget_not_approved:{control_id}")
    return result


def _validate_csv_observations(
    rows: list[dict[str, str]],
    controls: dict[str, dict[str, Any]],
    budgets: dict[str, dict[str, Any]],
    selected_methods: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, Any], list[datetime]]:
    expected_metadata = {
        row["observation_id"]: row for row in build_csv_rows()
    }
    if len(rows) != len(expected_metadata):
        errors.append("csv_observation_count_mismatch")
    if len({row.get("observation_id") for row in rows}) != len(rows):
        errors.append("duplicate_csv_observation_id")
    grouped: dict[str, dict[str, list[tuple[float, float]]]] = {
        control_id: {"physical": [], "scan": []}
        for control_id in SCALE_CONTROL_IDS
    }
    timestamps: list[datetime] = []
    setup_ids: dict[str, dict[str, list[str]]] = {
        control_id: {"physical": [], "scan": []}
        for control_id in SCALE_CONTROL_IDS
    }
    for row in rows:
        observation_id = row.get("observation_id", "")
        expected = expected_metadata.get(observation_id)
        if expected is None:
            errors.append(f"unexpected_csv_observation:{observation_id}")
            continue
        for field in (
            "observation_id",
            "control_id",
            "measurement_side",
            "repetition_index",
            "quantity",
            "unit",
        ):
            if row.get(field) != expected[field]:
                errors.append(f"csv_fixed_field_mismatch:{observation_id}.{field}")
        control_id = row["control_id"]
        if control_id not in grouped:
            errors.append(f"unexpected_csv_control_id:{observation_id}")
            continue
        measurement_side = row.get("measurement_side")
        if measurement_side not in {"physical", "scan"}:
            errors.append(f"unexpected_csv_measurement_side:{observation_id}")
            continue
        control = controls.get(control_id, {})
        for field in (
            "feature_id",
            "scan_region_token",
            "setup_id",
            "method_id",
            "value",
            "standard_uncertainty",
            "temperature_c",
            "timestamp_utc",
            "instrument_or_software_id",
            "calibration_or_validation_evidence_ref",
            "raw_evidence_ref",
            "operator_or_lab",
        ):
            if not _is_nonempty_string(row.get(field)):
                errors.append(f"missing_csv_field:{observation_id}.{field}")
        if row.get("review_status") != "accepted":
            errors.append(f"csv_observation_not_accepted:{observation_id}")
        if row.get("feature_id") != control.get("physical_feature_id"):
            errors.append(f"csv_same_feature_mismatch:{observation_id}")
        if row.get("scan_region_token") != control.get("scan_region_token"):
            errors.append(f"csv_scan_region_mismatch:{observation_id}")
        expected_method = (
            control.get("physical_method_id")
            if measurement_side == "physical"
            else control.get("scan_method_id")
        )
        if row.get("method_id") != expected_method:
            errors.append(f"csv_method_mismatch:{observation_id}")
        method = selected_methods.get(row.get("method_id", ""), {})
        if row.get("instrument_or_software_id") != method.get("instrument_or_software_id"):
            errors.append(f"csv_instrument_or_software_mismatch:{observation_id}")
        value = _parse_positive(row.get("value"), f"csv.{observation_id}.value", errors)
        uncertainty = _parse_positive(
            row.get("standard_uncertainty"),
            f"csv.{observation_id}.standard_uncertainty",
            errors,
        )
        _parse_finite(row.get("temperature_c"), f"csv.{observation_id}.temperature_c", errors)
        timestamp = _parse_utc(row.get("timestamp_utc"), f"csv.{observation_id}.timestamp_utc", errors)
        if timestamp is not None:
            timestamps.append(timestamp)
            method_start = _parse_utc(
                method.get("measurement_start_utc"),
                f"csv.{observation_id}.method_start",
                [],
            )
            method_end = _parse_utc(
                method.get("measurement_end_utc"),
                f"csv.{observation_id}.method_end",
                [],
            )
            if method_start is not None and method_end is not None and not (
                method_start <= timestamp <= method_end
            ):
                errors.append(f"observation_outside_method_time_window:{observation_id}")
        if _is_nonempty_string(row.get("setup_id")):
            _require_canonical_identifier(
                row["setup_id"], f"csv.{observation_id}.setup_id", errors
            )
            setup_ids[control_id][measurement_side].append(
                unicodedata.normalize("NFC", row["setup_id"].strip())
            )
        if _is_nonempty_string(row.get("operator_or_lab")):
            _require_canonical_identifier(
                row["operator_or_lab"],
                f"csv.{observation_id}.operator_or_lab",
                errors,
            )
        if value is not None and uncertainty is not None:
            grouped[control_id][measurement_side].append((value, uncertainty))

    metrics: dict[str, Any] = {"controls": {}, "relative_scale_spread": None}
    scale_factors: list[float] = []
    for control_id in SCALE_CONTROL_IDS:
        physical = grouped[control_id]["physical"]
        scan = grouped[control_id]["scan"]
        if len(physical) != REPEAT_COUNT or len(scan) != REPEAT_COUNT:
            errors.append(f"complete_repeat_sets_required:{control_id}")
            continue
        for side in ("physical", "scan"):
            if len(set(setup_ids[control_id][side])) != REPEAT_COUNT:
                errors.append(f"independent_repeat_setups_required:{control_id}.{side}")
        physical_values = [item[0] for item in physical]
        scan_values = [item[0] for item in scan]
        physical_mean = statistics.fmean(physical_values)
        scan_mean = statistics.fmean(scan_values)
        scale = physical_mean / scan_mean
        scale_factors.append(scale)
        physical_repeat_range = (max(physical_values) - min(physical_values)) / physical_mean
        scan_repeat_range = (max(scan_values) - min(scan_values)) / scan_mean
        # F27 ne dispose d'aucune matrice de covariance qualifiee. Il borne
        # donc toutes les correlations par |rho| <= 1 et utilise la somme
        # lineaire conservative : moyenne arithmetique des u au sein de chaque
        # cote, puis somme des contributions relatives entre les deux cotes.
        mean_physical_u = statistics.fmean(item[1] for item in physical)
        mean_scan_u = statistics.fmean(item[1] for item in scan)
        relative_u = (
            mean_physical_u / physical_mean + mean_scan_u / scan_mean
        )
        budget = budgets.get(control_id, {})
        max_relative_u = budget.get("maximum_relative_standard_uncertainty")
        max_repeatability = budget.get("maximum_relative_repeatability_range")
        if isinstance(max_relative_u, (int, float)) and relative_u > max_relative_u:
            errors.append(f"relative_uncertainty_exceeds_predeclared_limit:{control_id}")
        if isinstance(max_repeatability, (int, float)) and max(
            physical_repeat_range, scan_repeat_range
        ) > max_repeatability:
            errors.append(f"repeatability_exceeds_predeclared_limit:{control_id}")
        metrics["controls"][control_id] = {
            "scale_mm_per_obj_unit": scale,
            "relative_standard_uncertainty": relative_u,
            "physical_relative_range": physical_repeat_range,
            "scan_relative_range": scan_repeat_range,
        }
    if len(scale_factors) == 3:
        relative_spread = (max(scale_factors) - min(scale_factors)) / statistics.fmean(scale_factors)
        metrics["relative_scale_spread"] = relative_spread
        if relative_spread > MAX_RELATIVE_SCALE_SPREAD:
            errors.append("f21_relative_scale_spread_exceeded")
    return metrics, timestamps


def _validate_orientation(
    record: dict[str, Any], selected_methods: dict[str, dict[str, Any]], errors: list[str]
) -> float | None:
    protocol = record.get("orientation_protocol")
    if not isinstance(protocol, dict):
        errors.append("orientation_protocol_object_required")
        return None
    if protocol.get("datum_count") != 3:
        errors.append("orientation_datum_count_mismatch")
    if protocol.get("relation_contract") != _orientation_relation_contract():
        errors.append("orientation_relation_contract_mismatch")
    datums = protocol.get("datums")
    expected = [(item[0], item[1], item[2]) for item in DATUM_DEFINITIONS]
    observed = (
        [
            (item.get("datum_id"), item.get("f16_datum_ref"), item.get("kind"))
            for item in datums
        ]
        if isinstance(datums, list)
        and len(datums) == len(DATUM_DEFINITIONS)
        and all(isinstance(item, dict) for item in datums)
        else []
    )
    if observed != expected:
        errors.append("orientation_datum_registry_mismatch")
        return None
    datum_results: dict[str, dict[str, Any]] = {}
    for item in datums:
        datum_id = item["datum_id"]
        if item.get("f21_slot_ref") != datum_id:
            errors.append(f"f21_orientation_slot_ref_mismatch:{datum_id}")
        _require_fields(
            item,
            [
                "physical_feature_id",
                "scan_region_token",
                "physical_method_id",
                "scan_method_id",
                "semantic_direction_rule",
                "physical_fit_evidence_ref",
                "scan_fit_evidence_ref",
                "registration_evidence_ref",
            ],
            f"orientation_protocol.datums.{datum_id}",
            errors,
        )
        if item.get("semantic_direction_rule") != DATUM_DIRECTION_RULES[datum_id]:
            errors.append(f"orientation_semantic_direction_rule_mismatch:{datum_id}")
        physical_method_id = item.get("physical_method_id")
        scan_method_id = item.get("scan_method_id")
        if (
            not isinstance(physical_method_id, str)
            or physical_method_id not in PHYSICAL_METHOD_IDS
            or physical_method_id not in selected_methods
        ):
            errors.append(f"orientation_physical_method_invalid_or_unselected:{datum_id}")
        if (
            scan_method_id != "MESH_INSPECTION"
            or not isinstance(scan_method_id, str)
            or scan_method_id not in selected_methods
        ):
            errors.append(f"orientation_scan_method_invalid_or_unselected:{datum_id}")
        result = item.get("fit_result")
        if not isinstance(result, dict):
            errors.append(f"orientation_fit_result_object_required:{datum_id}")
            continue
        datum_results[datum_id] = result
        if item["kind"] in ("axis", "plane"):
            origin = result.get("origin_obj_units")
            direction = result.get("direction_or_normal")
            if not isinstance(origin, list) or len(origin) != 3 or any(
                not isinstance(v, (int, float))
                or isinstance(v, bool)
                or not math.isfinite(v)
                for v in origin
            ):
                errors.append(f"orientation_origin_vector_required:{datum_id}")
            if not isinstance(direction, list) or len(direction) != 3 or any(
                not isinstance(v, (int, float))
                or isinstance(v, bool)
                or not math.isfinite(v)
                for v in direction
            ):
                errors.append(f"orientation_direction_vector_required:{datum_id}")
            elif not math.isclose(
                math.sqrt(sum(v * v for v in direction)),
                1.0,
                rel_tol=0.0,
                abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
            ):
                errors.append(f"orientation_direction_must_be_unit_vector:{datum_id}")
        else:
            if result.get("handedness_token") != HANDEDNESS_TOKEN:
                errors.append(f"orientation_handedness_token_mismatch:{datum_id}")
            witness = result.get("origin_obj_units")
            if not (
                isinstance(witness, list)
                and len(witness) == 3
                and all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    for value in witness
                )
            ):
                errors.append(f"orientation_handedness_witness_point_required:{datum_id}")
        for field in (
            "fit_residual_obj_units",
            "registration_residual_mm",
            "angular_standard_uncertainty_deg",
        ):
            _parse_positive(result.get(field), f"orientation.{datum_id}.{field}", errors)
        if item.get("status") != "reviewed_complete":
            errors.append(f"orientation_datum_not_reviewed_complete:{datum_id}")
    transform = protocol.get("scan_to_engine_transform")
    if not isinstance(transform, dict):
        errors.append("scan_to_engine_transform_object_required")
        return None
    scale = _parse_positive(transform.get("scale_mm_per_obj_unit"), "orientation.transform.scale", errors)
    matrix = transform.get("rotation_matrix_3x3")
    matrix_valid = (
        isinstance(matrix, list)
        and len(matrix) == 3
        and all(
            isinstance(row, list)
            and len(row) == 3
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in row
            )
            for row in matrix
        )
    )
    if not matrix_valid:
        errors.append("rotation_matrix_3x3_required")
    else:
        for index, row in enumerate(matrix):
            norm = math.sqrt(sum(value * value for value in row))
            if not math.isclose(
                norm,
                1.0,
                rel_tol=0.0,
                abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
            ):
                errors.append(f"rotation_matrix_row_not_unit:{index}")
        for left, right in ((0, 1), (0, 2), (1, 2)):
            dot = sum(matrix[left][index] * matrix[right][index] for index in range(3))
            if not math.isclose(
                dot,
                0.0,
                rel_tol=0.0,
                abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
            ):
                errors.append(f"rotation_matrix_rows_not_orthogonal:{left}.{right}")
        determinant = (
            matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
            - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
            + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
        )
        if not math.isclose(
            determinant,
            1.0,
            rel_tol=0.0,
            abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
        ):
            errors.append("rotation_matrix_must_be_right_handed")
    translation = transform.get("translation_mm")
    translation_valid = (
        isinstance(translation, list)
        and len(translation) == 3
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in translation
        )
    )
    if not translation_valid:
        errors.append("translation_vector_mm_required")
    primary = datum_results.get("OR-PRIMARY-AXIS", {})
    secondary = datum_results.get("OR-SECONDARY-PLANE", {})
    primary_origin = primary.get("origin_obj_units")
    primary_direction = primary.get("direction_or_normal")
    secondary_origin = secondary.get("origin_obj_units")
    secondary_normal = secondary.get("direction_or_normal")
    geometric_vectors_valid = all(
        isinstance(vector, list)
        and len(vector) == 3
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in vector
        )
        for vector in (
            primary_origin,
            primary_direction,
            secondary_origin,
            secondary_normal,
        )
    )
    if geometric_vectors_valid:
        axis_plane_dot = sum(
            primary_direction[index] * secondary_normal[index]
            for index in range(3)
        )
        if not math.isclose(
            axis_plane_dot,
            0.0,
            rel_tol=0.0,
            abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
        ):
            errors.append("primary_axis_secondary_plane_relation_degenerate")
        origin_offset = [
            primary_origin[index] - secondary_origin[index] for index in range(3)
        ]
        origin_plane_distance = sum(
            origin_offset[index] * secondary_normal[index] for index in range(3)
        )
        if not math.isclose(
            origin_plane_distance,
            0.0,
            rel_tol=0.0,
            abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
        ):
            errors.append("primary_axis_origin_not_in_secondary_plane")
        if matrix_valid:
            for row_index, expected_vector, label in (
                (0, primary_direction, "primary_axis"),
                (2, secondary_normal, "secondary_plane"),
            ):
                if any(
                    not math.isclose(
                        matrix[row_index][index],
                        expected_vector[index],
                        rel_tol=0.0,
                        abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
                    )
                    for index in range(3)
                ):
                    errors.append(f"transform_{label}_row_mismatch")
            expected_row_1 = [
                secondary_normal[1] * primary_direction[2]
                - secondary_normal[2] * primary_direction[1],
                secondary_normal[2] * primary_direction[0]
                - secondary_normal[0] * primary_direction[2],
                secondary_normal[0] * primary_direction[1]
                - secondary_normal[1] * primary_direction[0],
            ]
            if any(
                not math.isclose(
                    matrix[1][index],
                    expected_row_1[index],
                    rel_tol=0.0,
                    abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
                )
                for index in range(3)
            ):
                errors.append("transform_handedness_row_mismatch")
            if scale is not None and translation_valid:
                expected_translation = [
                    -scale
                    * sum(
                        matrix[row_index][index] * primary_origin[index]
                        for index in range(3)
                    )
                    for row_index in range(3)
                ]
                if any(
                    not math.isclose(
                        translation[index],
                        expected_translation[index],
                        rel_tol=0.0,
                        abs_tol=NUMERICAL_CONSISTENCY_ABS_TOL,
                    )
                    for index in range(3)
                ):
                    errors.append("transform_translation_origin_mapping_mismatch")
                handedness_witness = datum_results.get("OR-HANDEDNESS", {}).get(
                    "origin_obj_units"
                )
                if (
                    isinstance(handedness_witness, list)
                    and len(handedness_witness) == 3
                    and all(
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                        for value in handedness_witness
                    )
                ):
                    witness_engine_y = scale * sum(
                        matrix[1][index] * handedness_witness[index]
                        for index in range(3)
                    ) + translation[1]
                    if witness_engine_y <= NUMERICAL_CONSISTENCY_ABS_TOL:
                        errors.append(
                            "handedness_witness_not_on_positive_engine_y"
                        )
    if not _is_nonempty_string(transform.get("transform_uncertainty_evidence_ref")):
        errors.append("transform_uncertainty_evidence_required")
    if transform.get("status") != "reviewed_complete":
        errors.append("scan_to_engine_transform_not_reviewed_complete")
    return scale


def _validate_identity_and_variant(record: dict[str, Any], root: Path, errors: list[str]) -> None:
    source = record.get("source_binding")
    if not isinstance(source, dict):
        errors.append("source_binding_object_required")
        return
    if source.get("expected_scan_sha256") != SCAN_SHA256 or source.get("working_scan_sha256") != SCAN_SHA256:
        errors.append("exact_working_scan_sha256_required")
    _require_fields(
        source,
        ["physical_asset_or_part_set_id", "physical_asset_serial_or_marking_evidence_ref"],
        "source_binding",
        errors,
    )
    if source.get("identity_status") != "reviewed_complete":
        errors.append("physical_asset_identity_not_reviewed_complete")

    variant = record.get("variant_identification")
    if not isinstance(variant, dict):
        errors.append("variant_identification_object_required")
        return
    candidates = _candidate_variant_ids(root)
    if variant.get("candidate_registry_source") != str(
        UPSTREAMS["f13_scan_metrology"]
    ):
        errors.append("variant_candidate_registry_source_mismatch")
    if variant.get("allowed_candidate_variant_ids") != candidates:
        errors.append("variant_candidate_registry_mismatch")
    selected = variant.get("selected_candidate_variant_id")
    if selected not in candidates:
        errors.append("selected_variant_not_in_f13_candidate_registry")
    if not _is_nonempty_string(variant.get("f16_branch_crosswalk_evidence_ref")):
        errors.append("f16_branch_crosswalk_evidence_required")
    evidence = variant.get("identity_evidence")
    expected_kinds = [
        "direct_marking_or_part_identity",
        "part_number_or_configuration_crosswalk",
        "teardown_or_architecture_discriminant",
        "calibrated_metrology_comparison",
    ]
    if (
        not isinstance(evidence, list)
        or len(evidence) != len(expected_kinds)
        or any(not isinstance(item, dict) for item in evidence)
        or [item.get("kind") for item in evidence] != expected_kinds
    ):
        errors.append("variant_identity_evidence_registry_mismatch")
    else:
        sources: list[str] = []
        for index, item in enumerate(evidence):
            prefix = f"variant_identification.identity_evidence[{index}]"
            _require_fields(item, ["independent_source_id", "evidence_ref"], prefix, errors)
            if _is_nonempty_string(item.get("independent_source_id")):
                _require_canonical_identifier(
                    item["independent_source_id"],
                    f"{prefix}.independent_source_id",
                    errors,
                )
                sources.append(
                    unicodedata.normalize("NFC", item["independent_source_id"].strip())
                )
            if item.get("review_status") != "accepted":
                errors.append(f"identity_evidence_not_accepted:{item.get('kind')}")
        if len(sources) != len(set(sources)):
            errors.append("variant_identity_sources_must_be_independent")
    if not _is_nonempty_string(variant.get("conflicting_evidence_log_evidence_ref")):
        errors.append("conflicting_evidence_log_required")
    if variant.get("adjudication_status") != "accepted_by_independent_review":
        errors.append("variant_adjudication_not_accepted")


def _validate_campaign_custody_environment_and_reviews(
    record: dict[str, Any],
    rows: list[dict[str, str]],
    observation_times: list[datetime],
    errors: list[str],
) -> None:
    campaign = record.get("campaign")
    _require_fields(
        campaign,
        [
            "campaign_id",
            "record_revision",
            "campaign_owner",
            "metrology_lab",
            "planned_start_utc",
            "protocol_frozen_at_utc",
            "preacquisition_approval_evidence_ref",
        ],
        "campaign",
        errors,
    )
    if isinstance(campaign, dict):
        for field in ("campaign_owner", "metrology_lab"):
            _require_canonical_identifier(
                campaign.get(field), f"campaign.{field}", errors
            )
    frozen = _parse_utc(campaign.get("protocol_frozen_at_utc") if isinstance(campaign, dict) else None, "campaign.protocol_frozen_at_utc", errors)
    _parse_utc(campaign.get("planned_start_utc") if isinstance(campaign, dict) else None, "campaign.planned_start_utc", errors)
    if frozen is not None and observation_times and frozen >= min(observation_times):
        errors.append("protocol_must_be_frozen_before_first_observation")

    custody = record.get("chain_of_custody")
    if not isinstance(custody, dict) or not _is_nonempty_string(custody.get("custody_id")):
        errors.append("custody_id_required")
    events = custody.get("events") if isinstance(custody, dict) else None
    expected_events = [
        "physical_asset_intake",
        "scan_working_copy_creation",
        "instrument_calibration_verification",
        "acquisition_open",
        "acquisition_close",
        "evidence_manifest_seal",
    ]
    seal_time: datetime | None = None
    if (
        not isinstance(events, list)
        or len(events) != len(expected_events)
        or any(not isinstance(item, dict) for item in events)
        or [item.get("event_type") for item in events] != expected_events
    ):
        errors.append("custody_event_registry_mismatch")
    else:
        event_times: list[datetime] = []
        for index, event in enumerate(events, start=1):
            if event.get("sequence") != index:
                errors.append(f"custody_sequence_mismatch:{index}")
            _require_fields(
                event,
                [
                    "actor_id",
                    "location_or_system_id",
                    "input_identifier_or_sha256",
                    "output_identifier_or_sha256",
                    "evidence_ref",
                ],
                f"chain_of_custody.events[{index - 1}]",
                errors,
            )
            _require_canonical_identifier(
                event.get("actor_id"),
                f"chain_of_custody.events[{index - 1}].actor_id",
                errors,
            )
            timestamp = _parse_utc(event.get("timestamp_utc"), f"chain_of_custody.events[{index - 1}].timestamp_utc", errors)
            if timestamp is not None:
                event_times.append(timestamp)
            if event.get("witness_or_review_status") != "accepted":
                errors.append(f"custody_event_not_accepted:{index}")
        if event_times != sorted(event_times):
            errors.append("custody_timestamps_not_monotonic")
        if len(event_times) == len(expected_events):
            seal_time = event_times[5]
        if events[1].get("output_identifier_or_sha256") != SCAN_SHA256:
            errors.append("custody_working_scan_sha256_mismatch")
        if len(event_times) == len(expected_events) and observation_times:
            acquisition_open = event_times[3]
            acquisition_close = event_times[4]
            if any(
                timestamp < acquisition_open or timestamp > acquisition_close
                for timestamp in observation_times
            ):
                errors.append("observation_outside_custody_acquisition_window")

    environment = record.get("environment")
    _require_fields(
        environment,
        [
            "stabilization_procedure_evidence_ref",
            "temperature_instrument_id",
            "temperature_calibration_evidence_ref",
            "environment_log_evidence_ref",
        ],
        "environment",
        errors,
    )
    if isinstance(environment, dict):
        _parse_finite(environment.get("temperature_c"), "environment.temperature_c", errors)
        humidity = _parse_finite(environment.get("relative_humidity_percent"), "environment.relative_humidity_percent", errors)
        if humidity is not None and not 0 <= humidity <= 100:
            errors.append("relative_humidity_out_of_range")

    reviews = record.get("independent_reviews")
    expected_review_keys = {"metrology", "variant_engineering", "final_envelope"}
    if (
        not isinstance(reviews, dict)
        or set(reviews) != expected_review_keys
        or any(not isinstance(review, dict) for review in reviews.values())
    ):
        errors.append("independent_review_registry_mismatch")
    else:
        reviewer_ids: list[str] = []
        forbidden_candidates: list[Any] = (
            [campaign.get("campaign_owner"), campaign.get("metrology_lab")]
            if isinstance(campaign, dict)
            else [None, None]
        )
        methods = record.get("methods")
        if isinstance(methods, list):
            forbidden_candidates.extend(
                item.get("operator_or_lab")
                for item in methods
                if isinstance(item, dict)
            )
            for item in methods:
                if isinstance(item, dict) and _is_nonempty_string(
                    item.get("operator_or_lab")
                ):
                    _require_canonical_identifier(
                        item["operator_or_lab"],
                        f"methods.{item.get('method_id')}.operator_or_lab",
                        errors,
                    )
        forbidden_candidates.extend(
            row.get("operator_or_lab") for row in rows if isinstance(row, dict)
        )
        if isinstance(events, list):
            forbidden_candidates.extend(
                item.get("actor_id") for item in events if isinstance(item, dict)
            )
        forbidden_reviewer_ids = {
            unicodedata.normalize("NFC", value.strip())
            for value in forbidden_candidates
            if _is_nonempty_string(value)
        }
        signed_times: list[datetime] = []
        acquisition_seal_sha256 = None
        if (
            isinstance(events, list)
            and len(events) == 6
            and isinstance(events[5], dict)
        ):
            acquisition_seal_sha256 = events[5].get(
                "output_identifier_or_sha256"
            )
        for key in ("metrology", "variant_engineering"):
            review = reviews[key]
            expected_role = (
                "qualified_metrology_reviewer"
                if key == "metrology"
                else "independent_engineering_reviewer"
            )
            if review.get("role") != expected_role:
                errors.append(f"independent_review_role_mismatch:{key}")
            _require_fields(
                review,
                [
                    "reviewer_id",
                    "reviewed_acquisition_packet_sha256",
                    "signed_report_evidence_ref",
                    "signed_at_utc",
                ],
                f"independent_reviews.{key}",
                errors,
            )
            if (
                not _is_sha256(review.get("reviewed_acquisition_packet_sha256"))
                or review.get("reviewed_acquisition_packet_sha256")
                != acquisition_seal_sha256
            ):
                errors.append(f"review_acquisition_seal_binding_mismatch:{key}")
            if _is_nonempty_string(review.get("reviewer_id")):
                _require_canonical_identifier(
                    review["reviewer_id"],
                    f"independent_reviews.{key}.reviewer_id",
                    errors,
                )
                normalized_reviewer_id = unicodedata.normalize(
                    "NFC", review["reviewer_id"].strip()
                )
                reviewer_ids.append(normalized_reviewer_id)
                if normalized_reviewer_id in forbidden_reviewer_ids:
                    errors.append(f"independent_reviewer_role_conflict:{key}")
            if review.get("decision") != "accepted":
                errors.append(f"independent_review_not_accepted:{key}")
            signed_at = _parse_utc(
                review.get("signed_at_utc"),
                f"independent_reviews.{key}.signed_at_utc",
                errors,
            )
            if (
                signed_at is not None
                and seal_time is not None
                and signed_at <= seal_time
            ):
                errors.append(f"independent_review_must_follow_packet_seal:{key}")
            if signed_at is not None:
                signed_times.append(signed_at)
        if len(reviewer_ids) == 2 and len(set(reviewer_ids)) != 2:
            errors.append("independent_reviewers_must_be_distinct")
        final_envelope = reviews["final_envelope"]
        _require_fields(
            final_envelope,
            ["sha256", "generated_at_utc"],
            "independent_reviews.final_envelope",
            errors,
        )
        generated_at = _parse_utc(
            final_envelope.get("generated_at_utc"),
            "independent_reviews.final_envelope.generated_at_utc",
            errors,
        )
        if generated_at is not None and signed_times and generated_at <= max(signed_times):
            errors.append("final_review_envelope_must_follow_both_reviews")
        if (
            not _is_sha256(final_envelope.get("sha256"))
            or final_envelope.get("sha256")
            != final_review_envelope_sha256(record, rows)
        ):
            errors.append("final_review_envelope_sha256_mismatch")


def packet_seal_sha256(
    record: dict[str, Any], rows: list[dict[str, str]]
) -> str:
    """Digest canonique d'acquisition, avant les deux revues futures."""

    normalized = copy.deepcopy(record)
    reviews = normalized.get("independent_reviews", {})
    review_evidence_ids = {
        review.get("signed_report_evidence_ref")
        for key, review in reviews.items()
        if key in {"metrology", "variant_engineering"}
        and isinstance(review, dict)
        and _is_nonempty_string(review.get("signed_report_evidence_ref"))
    } if isinstance(reviews, dict) else set()
    normalized["independent_reviews"] = {
        "excluded_from_acquisition_seal_pending_post_seal_reviews": True
    }
    events = normalized.get("chain_of_custody", {}).get("events", [])
    seal_evidence_id = None
    if isinstance(events, list) and len(events) >= 6 and isinstance(events[5], dict):
        seal_evidence_id = events[5].get("evidence_ref")
        events[5]["output_identifier_or_sha256"] = None
    entries = normalized.get("evidence_index", [])
    if isinstance(entries, list):
        entries[:] = [
            item
            for item in entries
            if not (
                isinstance(item, dict)
                and item.get("evidence_id") in review_evidence_ids
            )
        ]
        for item in entries:
            if isinstance(item, dict) and item.get("evidence_id") == seal_evidence_id:
                # L'identite, le role et le chemin du rapport de sceau restent
                # lies ; son propre hash est neutralise pour eviter un digest
                # circulaire. Le fichier est tout de meme verifie separement.
                item["sha256"] = None
    return _canonical_packet_digest(PACKET_SEAL_DOMAIN, normalized, rows)


def final_review_envelope_sha256(
    record: dict[str, Any], rows: list[dict[str, str]]
) -> str:
    normalized = copy.deepcopy(record)
    reviews = normalized.get("independent_reviews")
    if isinstance(reviews, dict):
        envelope = reviews.get("final_envelope")
        if isinstance(envelope, dict):
            envelope["sha256"] = None
    return _canonical_packet_digest(FINAL_REVIEW_ENVELOPE_DOMAIN, normalized, rows)


def _canonical_packet_digest(
    domain: bytes, record: dict[str, Any], rows: list[dict[str, str]]
) -> str:
    record_bytes = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    csv_bytes = render_csv(rows).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(domain)
    for payload in (record_bytes, csv_bytes):
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_packet_storage_paths(
    root: Path,
    record: dict[str, Any],
    rows: list[dict[str, str]],
    record_path: Path | None,
    observations_path: Path | None,
    evidence_root: Path | None,
    working_scan_path: Path | None,
    errors: list[str],
) -> set[tuple[int, int]]:
    packet_input_identities: set[tuple[int, int]] = set()
    if record_path is None:
        errors.append("campaign_record_path_required_for_git_boundary_proof")
    if observations_path is None:
        errors.append("observations_path_required_for_git_boundary_proof")
    if evidence_root is None:
        errors.append("evidence_root_required_for_git_boundary_proof")
    if working_scan_path is None:
        errors.append("working_scan_path_required_for_git_boundary_proof")
    if (
        record_path is None
        or observations_path is None
        or evidence_root is None
        or working_scan_path is None
    ):
        return packet_input_identities

    opened: list[tuple[str, int, bool]] = []
    try:
        for path, expect_directory, label in (
            (record_path, False, "campaign_record"),
            (observations_path, False, "observations"),
            (evidence_root, True, "evidence_root"),
            (working_scan_path, False, "working_scan"),
        ):
            try:
                opened.append(
                    (
                        label,
                        _open_path_no_symlinks(
                        path,
                        expect_directory=expect_directory,
                        error_label=label,
                        ),
                        expect_directory,
                    )
                )
            except (OSError, ValueError) as exc:
                errors.append(f"unsafe_packet_path:{label}:{type(exc).__name__}")
        if len(opened) != 4:
            return packet_input_identities
        identity_labels: dict[tuple[int, int], str] = {}
        for label, descriptor, expect_directory in opened:
            if expect_directory:
                continue
            observed = os.fstat(descriptor)
            identity = (observed.st_dev, observed.st_ino)
            previous_label = identity_labels.get(identity)
            if previous_label is not None:
                errors.append(
                    f"packet_input_file_identity_reused:{previous_label}:{label}"
                )
            else:
                identity_labels[identity] = label
            packet_input_identities.add(identity)
    finally:
        for _, descriptor, _ in opened:
            os.close(descriptor)

    try:
        if load_json_strict(record_path) != record:
            errors.append("campaign_record_memory_file_mismatch")
        if load_csv_strict(observations_path) != rows:
            errors.append("observations_memory_file_mismatch")
    except (
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        csv.Error,
        json.JSONDecodeError,
    ) as exc:
        errors.append(f"packet_source_reread_failed:{type(exc).__name__}")

    record_abs = _lexical_absolute(record_path)
    observations_abs = _lexical_absolute(observations_path)
    evidence_abs = _lexical_absolute(evidence_root)
    working_scan_abs = _lexical_absolute(working_scan_path)
    root_abs = _lexical_absolute(root)
    if record_abs.parent != observations_abs.parent:
        errors.append("campaign_record_and_observations_must_share_directory")
    if evidence_abs != record_abs.parent / "evidence":
        errors.append("evidence_root_must_be_campaign_evidence_child")
    if working_scan_abs.parent != record_abs.parent:
        errors.append("working_scan_must_be_campaign_sibling")

    allowed_local_root = root_abs / LOCAL_CAMPAIGN_REL
    for label, path in (
        ("campaign_record", record_abs),
        ("observations", observations_abs),
        ("evidence_root", evidence_abs),
        ("working_scan", working_scan_abs),
    ):
        if not _is_within(path, root_abs):
            continue
        if not _is_within(path, allowed_local_root):
            errors.append(f"packet_path_inside_repository_outside_work:{label}")
            continue
        relative = path.relative_to(root_abs)
        git_check = subprocess.run(
            [
                "git",
                "-C",
                str(root_abs),
                "ls-files",
                "--error-unmatch",
                "--",
                relative.as_posix(),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if git_check.returncode == 0:
            errors.append(f"packet_path_is_git_tracked:{label}")
    return packet_input_identities


def _verify_working_scan_file(path: Path | None, errors: list[str]) -> None:
    if path is None:
        errors.append("working_scan_file_required")
        return
    try:
        observed_sha256 = sha256_file(path)
    except (OSError, ValueError) as exc:
        errors.append(f"working_scan_file_unreadable:{type(exc).__name__}")
        return
    if observed_sha256 != SCAN_SHA256:
        errors.append("working_scan_file_sha256_mismatch")


def evaluate_record(
    root: Path,
    record: dict[str, Any],
    rows: list[dict[str, str]],
    evidence_root: Path | None,
    *,
    record_path: Path | None = None,
    observations_path: Path | None = None,
    working_scan_path: Path | None = None,
) -> dict[str, Any]:
    errors = validate_upstreams(root)
    packet_input_identities = _validate_packet_storage_paths(
        root,
        record,
        rows,
        record_path,
        observations_path,
        evidence_root,
        working_scan_path,
        errors,
    )
    _verify_working_scan_file(working_scan_path, errors)
    _validate_shape(record, root, errors)
    selected_methods = _validate_methods(record, errors)
    controls = _validate_scale_controls(record, selected_methods, errors)
    budgets = _validate_uncertainty_budgets(record, errors)
    metrics, observation_times = _validate_csv_observations(
        rows, controls, budgets, selected_methods, errors
    )
    transform_scale = _validate_orientation(record, selected_methods, errors)
    control_metrics = metrics.get("controls", {})
    if transform_scale is not None and len(control_metrics) == 3:
        derived_scale = statistics.fmean(
            item["scale_mm_per_obj_unit"] for item in control_metrics.values()
        )
        if not math.isclose(
            transform_scale,
            derived_scale,
            rel_tol=SCALE_CONSISTENCY_REL_TOL,
            abs_tol=SCALE_CONSISTENCY_ABS_TOL,
        ):
            errors.append("transform_scale_must_equal_mean_of_three_controls")
    _validate_identity_and_variant(record, root, errors)
    _validate_campaign_custody_environment_and_reviews(
        record, rows, observation_times, errors
    )

    evidence = _evidence_map(record, errors)
    _bind_evidence_roles(record, rows, evidence, errors)
    custody = record.get("chain_of_custody")
    custody_events = custody.get("events", []) if isinstance(custody, dict) else []
    if (
        isinstance(custody_events, list)
        and len(custody_events) == 6
        and isinstance(custody_events[5], dict)
    ):
        seal_event = custody_events[5]
        try:
            expected_seal = packet_seal_sha256(record, rows)
        except (TypeError, ValueError):
            errors.append("custody_packet_seal_payload_invalid")
        else:
            if seal_event.get("output_identifier_or_sha256") != expected_seal:
                errors.append("custody_packet_seal_sha256_mismatch")
    if evidence_root is None:
        errors.append("evidence_root_required_for_complete_campaign")
    else:
        _verify_evidence_files(
            evidence,
            evidence_root,
            errors,
            packet_input_identities,
        )

    unique_errors = sorted(set(errors))
    return {
        "schema_version": "1.0.0",
        "phase": "F27",
        "report_status": (
            "ready_for_independent_binding_review_gates_closed"
            if not unique_errors
            else "failed_closed"
        ),
        "errors": unique_errors,
        "derived_screening_metrics_not_release_authority": metrics,
        "claims": {
            "campaign_packet_structurally_complete": not unique_errors,
            "scan_variant_bound": False,
            "cad_input_authorized": False,
            "solver_authorized": False,
            "physicsnemo_authorized": False,
            "fabrication_authorized": False,
        },
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def check_templates_report(root: Path) -> dict[str, Any]:
    errors = validate_templates(root)
    return {
        "schema_version": "1.0.0",
        "phase": "F27",
        "report_status": "passed_fail_closed" if not errors else "failed_closed",
        "errors": errors,
        "template_contains_measurements": False,
        "template_contains_proprietary_geometry": False,
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def write_templates(root: Path) -> None:
    json_bytes = (
        json.dumps(build_json_template(root), indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    csv_bytes = render_csv(build_csv_rows()).encode("utf-8")
    _write_new(root / JSON_TEMPLATE_REL, json_bytes)
    _write_new(root / CSV_TEMPLATE_REL, csv_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--write-templates", action="store_true")
    parser.add_argument("--check-templates", action="store_true")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--working-scan", type=Path)
    args = parser.parse_args()

    root = _lexical_absolute(args.root)
    try:
        if args.write_templates:
            write_templates(root)
        if args.record or args.observations or args.evidence_root or args.working_scan:
            if not (
                args.record
                and args.observations
                and args.evidence_root
                and args.working_scan
            ):
                parser.error(
                    "--record, --observations, --evidence-root and --working-scan are required together"
                )
            record = load_json_strict(args.record)
            rows = load_csv_strict(args.observations)
            report = evaluate_record(
                root,
                record,
                rows,
                args.evidence_root,
                record_path=args.record,
                observations_path=args.observations,
                working_scan_path=args.working_scan,
            )
        else:
            report = check_templates_report(root)
    except (
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        csv.Error,
        json.JSONDecodeError,
    ) as exc:
        report = {
            "schema_version": "1.0.0",
            "phase": "F27",
            "report_status": "failed_closed",
            "errors": [f"unsafe_or_invalid_input:{type(exc).__name__}"],
            "claims": {
                "campaign_packet_structurally_complete": False,
                "scan_variant_bound": False,
                "cad_input_authorized": False,
                "solver_authorized": False,
                "physicsnemo_authorized": False,
                "fabrication_authorized": False,
            },
            "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["report_status"] in {
        "passed_fail_closed",
        "ready_for_independent_binding_review_gates_closed",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
