#!/usr/bin/env python3
"""Auteur fail-closed du premier layout CAO mesure du moteur 917 (F30).

Le script ne reconstruit aucun solide et n'applique aucune cote documentaire.
Il ne peut produire qu'un STEP filaire de construction, apres validation d'un
paquet F27 complet et d'une decision de binding CAO separee.
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime
import errno
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_REL = Path(
    "twins/reference-917-engine/parametric-layout-authoring-f30.template.json"
)
F27_VALIDATOR_REL = Path(
    "twins/reference-917-engine/source/validate_physical_metrology_campaign_f27.py"
)
SCAN_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"
CAD_IMAGE_REFERENCE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@"
    "sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
)
# Aucune cle publique de reviewer n'est encore approuvee dans le depot. Tant
# que cette ancre reste absente, le chemin CLI d'authoring reel echoue ferme.
# Une future revue doit ajouter uniquement le SHA-256 de la cle publique
# approuvee; la cle privee ne doit jamais entrer dans le depot.
TRUSTED_F30_REVIEWER_PUBLIC_KEY_SHA256: str | None = None
F30_SIGNATURE_ALGORITHM = "ed25519-openssl-pkeyutl"
VARIANT_TARGET_MAP = {
    "917_5_0_na": "type_912_5_0_na",
}
UPSTREAMS = (
    (
        "f21_scale_orientation",
        Path("twins/reference-917-engine/scan-scale-orientation-acquisition-f21.json"),
        "scale_orientation_acquisition_contract_only",
        "e958bc9188fb05dbe02e131cdc12f3e466eaa93aa2772e930bf91f733f2d924b",
    ),
    (
        "f22_parametric_assembly",
        Path("twins/reference-917-engine/parametric-cad-assembly-contract-f22.json"),
        "null_parameter_and_interface_registry_only",
        "87529899d643dd437f357c79fa4dd4fa5ac5ed95929c4fdf82c4985222fd6baa",
    ),
    (
        "f24_dual_variant_readiness",
        Path("twins/reference-917-engine/dual-variant-functional-readiness-f24.json"),
        "variant_and_solver_input_boundaries_only",
        "87a2a22a79146d590d99ab1d3277a2c2c92d069c8275e580b675a5b5dcf23630",
    ),
    (
        "f27_physical_metrology_template",
        Path("twins/reference-917-engine/physical-metrology-campaign-f27.template.json"),
        "blank_campaign_schema_only",
        "73aa225c2b8baa3f74aa288f5ee570bafda8a6099c44fc2a4b8dde528eb12ee4",
    ),
    (
        "f27_observation_template",
        Path("twins/reference-917-engine/physical-metrology-observations-f27.template.csv"),
        "blank_observation_schema_only",
        "af1ab7c3a171ac69c7c25073c32007bb6902d064aa49e6dfbee2d3d1d5700ba2",
    ),
    (
        "f27_validator",
        Path("twins/reference-917-engine/source/validate_physical_metrology_campaign_f27.py"),
        "executed_fail_closed_validator",
        "7eda0cd1f6b7470b16b582c994a0c98b1f64b49a75c131500fe612da5333f1d4",
    ),
    (
        "f28_dual_variant_cad_contract",
        Path("twins/reference-917-engine/dual-variant-parametric-cad-contract-f28.json"),
        "component_family_and_branch_semantics_only",
        "920b8c022676a9941c8764fb1f0f178da47220798dd6fa7e96ba6d410aee5abb",
    ),
    (
        "f28_cad_author_image_lock",
        Path("containers/cad-author-f28.lock.json"),
        "immutable_cpu_cad_toolchain_only",
        "d221f6b6a2bd88361051809f2e06fa22dbe53948636fd18387f78c8111d50d8d",
    ),
)
AUTHORIZED_SCOPE = (
    "engine_coordinate_frame",
    "crankshaft_axis",
    "crankcase_split_plane",
    "bank_deck_planes",
    "twelve_cylinder_axes",
    "physically_confirmed_main_bearing_stations",
)
RELEASE_GATE_IDS = (
    "solid_geometry_authorized",
    "functional_component_cad_authorized",
    "classical_solver_authorized",
    "physicsnemo_dataset_authorized",
    "physicsnemo_training_authorized",
    "omniverse_simready_authorized",
    "manufacturing_authorized",
    "polymer_print_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
)
F27_RELEASE_GATE_IDS = (
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
CANONICAL_FRAME_TOLERANCE = 1e-9
GEOMETRIC_RELATION_TOLERANCE = 1e-6
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
STRICT_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)
F30_EVIDENCE_KINDS = {
    "engine_coordinate_frame_fit",
    "crankshaft_axis_fit",
    "crankcase_split_plane_fit",
    "bank_deck_plane_fit",
    "cylinder_axis_fit",
    "main_bearing_station_fit",
    "main_bearing_count_report",
}


class DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_nonfinite_constant(token: str) -> None:
    raise ValueError(f"non-finite JSON constant: {token}")


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_template(root: Path) -> dict[str, Any]:
    manifest = []
    for upstream_id, relative_path, role, approved_sha256 in UPSTREAMS:
        observed_sha256 = sha256_file(root / relative_path)
        if observed_sha256 != approved_sha256:
            raise ValueError(f"approved_upstream_sha256_mismatch:{upstream_id}")
        manifest.append(
            {
                "id": upstream_id,
                "path": relative_path.as_posix(),
                "sha256": approved_sha256,
                "role": role,
            }
        )
    return {
        "$comment": (
            "F30 definit l'auteur du premier layout CAO mesure. Le formulaire suivi "
            "ne contient aucune mesure ni geometrie et tous les gates physiques, "
            "solveurs, PhysicsNeMo, Omniverse et fabrication restent fermes."
        ),
        "schema_version": "1.0.0",
        "phase": "F30",
        "status": "layout_authoring_contract_ready_no_measurements_no_geometry",
        "upstream_manifest": manifest,
        "source_binding": {
            "canonical_scan_sha256": SCAN_SHA256,
            "raw_scan_or_derivative_tracked": False,
            "filled_f27_packet_must_remain_under_work": True,
            "documentary_dimensions_may_drive_layout": False,
            "closest_documentary_variant_may_select_identity": False,
            "f27_to_f28_variant_target_map": VARIANT_TARGET_MAP,
            "f27_type_912_4_5_na_target": "blocked_no_f28_authoring_branch",
            "f27_917_30_turbo_5374_target": (
                "blocked_generic_f27_identity_does_not_distinguish_f28_1973_branch"
            ),
        },
        "cad_runtime": {
            "immutable_image": CAD_IMAGE_REFERENCE,
            "platform": "linux/amd64",
            "gpu_required": False,
            "network_required": False,
            "runtime_user": "9178:9178",
            "authoring_library": "build123d 0.11.1",
            "kernel": "OCCT 7.9.3",
        },
        "reviewer_authentication": {
            "signature_algorithm": F30_SIGNATURE_ALGORITHM,
            "signature_scope": "exact_canonical_binding_json_bytes",
            "trusted_reviewer_public_key_sha256": (
                TRUSTED_F30_REVIEWER_PUBLIC_KEY_SHA256
            ),
            "authoring_blocked_until_trust_anchor_configured": (
                TRUSTED_F30_REVIEWER_PUBLIC_KEY_SHA256 is None
            ),
            "private_key_tracked_or_transferred": False,
        },
        "required_authority_chain": [
            "F27 campaign structurally ready for independent binding review",
            "two F27 independent reviews accepted",
            "separate F30 CAD binding decision authenticated by a distinct reviewer",
            "reviewer public key SHA-256 matches the tracked trust anchor",
            "detached Ed25519 signature verifies the exact canonical binding JSON",
            "layout parameters bound by SHA-256 to the decision",
            "all parameters carry unit, uncertainty, datum and evidence reference",
        ],
        "authorized_layout_entities": list(AUTHORIZED_SCOPE),
        "required_counts": {
            "engine_coordinate_frames": 1,
            "crankshaft_axes": 1,
            "crankcase_split_planes": 1,
            "bank_deck_planes": 2,
            "cylinder_axes": 12,
            "main_bearing_station_count": "physically_confirmed_value_only",
        },
        "authoring_policy": {
            "output_kind": "wireframe_construction_layout_only",
            "solid_count": 0,
            "face_count": 0,
            "documentary_candidates_applied": False,
            "step_digest_reproducibility_claim": False,
            "normalized_geometry_signature_required": True,
            "occt_roundtrip_required": True,
            "atomic_no_overwrite_output_required": True,
            "publication_complete_marker_required": True,
            "allowed_output_root": "work/917-engine/cad/f30",
            "construction_witness_conventions_mm": {
                "engine_frame_axis_length": 25.0,
                "main_bearing_marker_half_length": 5.0,
            },
        },
        "local_input_contract": {
            "f27_record": "filled JSON under work; never tracked",
            "f27_observations": "filled CSV under work; never tracked",
            "f27_evidence_root": "sealed evidence directory under work; never tracked",
            "working_scan": "exact canonical OBJ under work; never tracked",
            "binding_decision": {
                "decision": "accepted_for_parametric_layout_only",
                "required_bindings": [
                    "campaign_id",
                    "f27_final_review_envelope_sha256",
                    "f27_scan_to_engine_transform_sha256",
                    "scan_sha256",
                    "f27_variant_id",
                    "f28_variant_id",
                    "layout_parameters_sha256",
                    "review_report_sha256",
                    "reviewer_public_key_sha256",
                ],
                "reviewer_must_be_distinct_from_f27_reviewers": True,
                "authorized_scope": list(AUTHORIZED_SCOPE),
            },
            "layout_parameters": {
                "units": "mm",
                "right_handed": True,
                "canonical_crankshaft_axis": [1.0, 0.0, 0.0],
                "canonical_split_plane_normal": [0.0, 0.0, 1.0],
                "handedness_token": "bank_positive_on_positive_engine_y",
                "cylinder_axis_count": 12,
                "documentary_candidates_applied": False,
                "variant_mapping": VARIANT_TARGET_MAP,
            },
            "binding_review_report": (
                "separate human review report under work, bound by SHA-256; never tracked"
            ),
            "binding_detached_signature": (
                "Ed25519 signature over the exact canonical binding JSON; never tracked"
            ),
            "reviewer_public_key": (
                "public key under work whose SHA-256 must match the tracked trust anchor; never tracked"
            ),
            "layout_evidence_root": (
                "F30 measurement and fit evidence under work, verified by index; never tracked"
            ),
        },
        "local_outputs": [
            "layout-parameters.json",
            "engine-layout.step",
            "geometry-report.json",
            "provenance-manifest.json",
            "publication-complete.json",
        ],
        "prohibited_outputs": [
            "solid CAD",
            "STL or 3MF",
            "USD or SimReady asset",
            "solver deck or result",
            "PhysicsNeMo sample or model weight",
            "manufacturing drawing or release",
        ],
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def validate_template(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        expected = build_template(root)
        observed = load_json(root / TEMPLATE_REL)
    except (OSError, ValueError, DuplicateKeyError) as exc:
        return [f"template_unreadable:{type(exc).__name__}"]
    if observed != expected:
        errors.append("tracked_template_is_not_current")
    if any(observed.get("release_gates", {}).values()):
        errors.append("tracked_template_release_gate_open")
    if observed.get("authoring_policy", {}).get("solid_count") != 0:
        errors.append("tracked_template_must_author_zero_solids")
    return errors


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _is_identifier(value: Any) -> bool:
    return isinstance(value, str) and IDENTIFIER_RE.fullmatch(value) is not None


def _parse_strict_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or STRICT_UTC_RE.fullmatch(value) is None:
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _vector(value: Any, label: str, errors: list[str]) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3 or not all(_finite(item) for item in value):
        errors.append(f"finite_vector3_required:{label}")
        return None
    return [float(item) for item in value]


def _unit_vector(value: Any, label: str, errors: list[str]) -> list[float] | None:
    vector = _vector(value, label, errors)
    if vector is None:
        return None
    norm = math.sqrt(sum(component * component for component in vector))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-6):
        errors.append(f"unit_vector_required:{label}")
    return vector


def _positive(value: Any, label: str, errors: list[str]) -> None:
    if not _finite(value) or float(value) <= 0.0:
        errors.append(f"positive_number_required:{label}")


def _dot(first: list[float], second: list[float]) -> float:
    return sum(first[index] * second[index] for index in range(3))


def _subtract(first: list[float], second: list[float]) -> list[float]:
    return [first[index] - second[index] for index in range(3)]


def _evidence_ref(
    value: Any,
    label: str,
    evidence_kinds: dict[str, str],
    expected_kind: str,
    used_evidence_ids: set[str],
    errors: list[str],
) -> None:
    if not _is_identifier(value):
        errors.append(f"canonical_evidence_ref_required:{label}")
    elif value not in evidence_kinds:
        errors.append(f"unresolved_f30_evidence_ref:{label}")
    else:
        used_evidence_ids.add(value)
        if evidence_kinds[value] != expected_kind:
            errors.append(f"f30_evidence_kind_mismatch:{label}")


def _layout_evidence_kinds(index: Any, errors: list[str]) -> dict[str, str]:
    if not isinstance(index, list) or not index:
        errors.append("nonempty_layout_evidence_index_required")
        return {}
    result: dict[str, str] = {}
    relative_paths: set[str] = set()
    for ordinal, entry in enumerate(index):
        label = f"evidence_index[{ordinal}]"
        if not isinstance(entry, dict) or set(entry) != {
            "evidence_id",
            "kind",
            "relative_path",
            "sha256",
            "contains_proprietary_or_sensitive_data",
            "commit_allowed",
        }:
            errors.append(f"layout_evidence_entry_shape_invalid:{ordinal}")
            continue
        evidence_id = entry.get("evidence_id")
        kind = entry.get("kind")
        relative_path = entry.get("relative_path")
        if not _is_identifier(evidence_id) or evidence_id in result:
            errors.append(f"layout_evidence_id_invalid_or_duplicate:{ordinal}")
            continue
        if kind not in F30_EVIDENCE_KINDS:
            errors.append(f"layout_evidence_kind_invalid:{ordinal}")
        if not isinstance(relative_path, str):
            errors.append(f"layout_evidence_relative_path_invalid:{ordinal}")
        else:
            pure_path = PurePosixPath(relative_path)
            if (
                pure_path.is_absolute()
                or not pure_path.parts
                or any(part in {"", ".", ".."} for part in pure_path.parts)
                or relative_path in relative_paths
            ):
                errors.append(f"layout_evidence_relative_path_invalid:{ordinal}")
            relative_paths.add(relative_path)
        if not _is_sha256(entry.get("sha256")):
            errors.append(f"layout_evidence_sha256_invalid:{ordinal}")
        if not isinstance(entry.get("contains_proprietary_or_sensitive_data"), bool):
            errors.append(f"layout_evidence_sensitivity_flag_invalid:{ordinal}")
        if entry.get("commit_allowed") is not False:
            errors.append(f"layout_evidence_commit_must_be_forbidden:{ordinal}")
        if isinstance(kind, str):
            result[evidence_id] = kind
    return result


def validate_layout_parameters(parameters: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence_kinds = _layout_evidence_kinds(parameters.get("evidence_index"), errors)
    used_evidence_ids: set[str] = set()
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "campaign_id",
        "f27_final_review_envelope_sha256",
        "f27_scan_to_engine_transform_sha256",
        "scan_sha256",
        "f27_variant_id",
        "f28_variant_id",
        "units",
        "documentary_candidates_applied",
        "evidence_index",
        "engine_frame",
        "crankshaft_axis",
        "crankcase_split_plane",
        "bank_deck_planes",
        "cylinder_axes",
        "main_bearing_stations",
        "release_gates",
    }
    if set(parameters) != expected_keys:
        errors.append("layout_parameter_key_set_mismatch")
    if parameters.get("schema_version") != "1.0.0" or parameters.get("phase") != "F30":
        errors.append("layout_parameter_identity_mismatch")
    if parameters.get("status") != "measured_layout_input_candidate":
        errors.append("layout_parameter_status_not_measured_candidate")
    if parameters.get("scan_sha256") != SCAN_SHA256:
        errors.append("layout_parameter_scan_sha256_mismatch")
    f27_variant_id = parameters.get("f27_variant_id")
    f28_variant_id = parameters.get("f28_variant_id")
    if f27_variant_id not in VARIANT_TARGET_MAP:
        errors.append("layout_parameter_f27_variant_has_no_f28_authoring_branch")
    elif f28_variant_id != VARIANT_TARGET_MAP[f27_variant_id]:
        errors.append("layout_parameter_f27_to_f28_variant_mapping_mismatch")
    if parameters.get("units") != "mm":
        errors.append("layout_parameter_units_must_be_mm")
    if parameters.get("documentary_candidates_applied") is not False:
        errors.append("documentary_candidates_must_not_drive_layout")
    if not _is_identifier(parameters.get("campaign_id")):
        errors.append("layout_campaign_id_required")
    if not _is_sha256(parameters.get("f27_final_review_envelope_sha256")):
        errors.append("layout_f27_envelope_sha256_required")
    if not _is_sha256(parameters.get("f27_scan_to_engine_transform_sha256")):
        errors.append("layout_f27_transform_sha256_required")

    frame_origin: list[float] | None = None
    frame = parameters.get("engine_frame")
    if not isinstance(frame, dict) or set(frame) != {
        "id",
        "origin_mm",
        "right_handed",
        "handedness_token",
        "evidence_ref",
        "position_standard_uncertainty_mm",
    }:
        errors.append("engine_frame_shape_invalid")
    else:
        if frame.get("id") != "ENGINE-FRAME-F30":
            errors.append("engine_frame_id_mismatch")
        frame_origin = _vector(frame.get("origin_mm"), "engine_frame.origin_mm", errors)
        if frame_origin is not None and any(
            not math.isclose(
                coordinate,
                0.0,
                rel_tol=0.0,
                abs_tol=CANONICAL_FRAME_TOLERANCE,
            )
            for coordinate in frame_origin
        ):
            errors.append("engine_frame_origin_must_be_canonical_zero")
        if frame.get("right_handed") is not True:
            errors.append("engine_frame_must_be_right_handed")
        if frame.get("handedness_token") != "bank_positive_on_positive_engine_y":
            errors.append("engine_frame_handedness_mismatch")
        _positive(
            frame.get("position_standard_uncertainty_mm"),
            "engine_frame.position_standard_uncertainty_mm",
            errors,
        )
        _evidence_ref(
            frame.get("evidence_ref"),
            "engine_frame.evidence_ref",
            evidence_kinds,
            "engine_coordinate_frame_fit",
            used_evidence_ids,
            errors,
        )

    crank_origin: list[float] | None = None
    crank_direction: list[float] | None = None
    crank_span: list[float] | None = None
    crank = parameters.get("crankshaft_axis")
    if not isinstance(crank, dict) or set(crank) != {
        "id",
        "datum_ref",
        "origin_mm",
        "direction",
        "span_mm",
        "position_standard_uncertainty_mm",
        "angular_standard_uncertainty_deg",
        "evidence_ref",
    }:
        errors.append("crankshaft_axis_shape_invalid")
    else:
        if crank.get("id") != "CRANKSHAFT-AXIS-F30":
            errors.append("crankshaft_axis_id_mismatch")
        if crank.get("datum_ref") != "ENGINE-FRAME-F30":
            errors.append("crankshaft_axis_datum_ref_mismatch")
        crank_origin = _vector(crank.get("origin_mm"), "crankshaft_axis.origin_mm", errors)
        crank_direction = _unit_vector(crank.get("direction"), "crankshaft_axis.direction", errors)
        if crank_direction is not None and any(
            not math.isclose(crank_direction[index], expected, rel_tol=0.0, abs_tol=CANONICAL_FRAME_TOLERANCE)
            for index, expected in enumerate((1.0, 0.0, 0.0))
        ):
            errors.append("crankshaft_axis_not_canonical_x")
        span = crank.get("span_mm")
        if not isinstance(span, list) or len(span) != 2 or not all(_finite(item) for item in span):
            errors.append("crankshaft_axis_span_invalid")
        elif float(span[0]) >= float(span[1]):
            errors.append("crankshaft_axis_span_not_increasing")
        else:
            crank_span = [float(span[0]), float(span[1])]
        _positive(crank.get("position_standard_uncertainty_mm"), "crankshaft_axis.position_standard_uncertainty_mm", errors)
        _positive(crank.get("angular_standard_uncertainty_deg"), "crankshaft_axis.angular_standard_uncertainty_deg", errors)
        _evidence_ref(
            crank.get("evidence_ref"),
            "crankshaft_axis.evidence_ref",
            evidence_kinds,
            "crankshaft_axis_fit",
            used_evidence_ids,
            errors,
        )

    if frame_origin is not None and crank_origin is not None and any(
        not math.isclose(
            frame_origin[index],
            crank_origin[index],
            rel_tol=0.0,
            abs_tol=GEOMETRIC_RELATION_TOLERANCE,
        )
        for index in range(3)
    ):
        errors.append("engine_frame_origin_must_equal_crankshaft_axis_origin")

    split = parameters.get("crankcase_split_plane")
    _validate_plane(
        split,
        "crankcase_split_plane",
        evidence_kinds,
        "crankcase_split_plane_fit",
        used_evidence_ids,
        errors,
        expected_normal=(0.0, 0.0, 1.0),
    )
    if isinstance(split, dict) and frame_origin is not None:
        split_origin = _vector(
            split.get("origin_mm"), "crankcase_split_plane.origin_relation", errors
        )
        if split_origin is not None and any(
            not math.isclose(
                split_origin[index],
                frame_origin[index],
                rel_tol=0.0,
                abs_tol=GEOMETRIC_RELATION_TOLERANCE,
            )
            for index in range(3)
        ):
            errors.append("crankcase_split_plane_must_contain_engine_origin")

    decks = parameters.get("bank_deck_planes")
    deck_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(decks, list) or len(decks) != 2:
        errors.append("exactly_two_bank_deck_planes_required")
    else:
        ids = {item.get("id") for item in decks if isinstance(item, dict)}
        if ids != {"BANK-POSITIVE-DECK", "BANK-NEGATIVE-DECK"}:
            errors.append("bank_deck_plane_ids_invalid")
        for index, plane in enumerate(decks):
            _validate_plane(
                plane,
                f"bank_deck_planes[{index}]",
                evidence_kinds,
                "bank_deck_plane_fit",
                used_evidence_ids,
                errors,
            )
            if isinstance(plane, dict) and isinstance(plane.get("id"), str):
                deck_by_id[plane["id"]] = plane
        for deck_id, expected_y_sign in (
            ("BANK-POSITIVE-DECK", 1.0),
            ("BANK-NEGATIVE-DECK", -1.0),
        ):
            plane = deck_by_id.get(deck_id)
            if plane is None:
                continue
            origin = _vector(plane.get("origin_mm"), f"{deck_id}.origin_relation", errors)
            normal = _unit_vector(plane.get("normal"), f"{deck_id}.normal_relation", errors)
            if origin is not None and frame_origin is not None:
                signed_y = origin[1] - frame_origin[1]
                if expected_y_sign * signed_y <= GEOMETRIC_RELATION_TOLERANCE:
                    errors.append(f"bank_deck_origin_wrong_engine_y_side:{deck_id}")
            if normal is not None:
                if expected_y_sign * normal[1] <= GEOMETRIC_RELATION_TOLERANCE:
                    errors.append(f"bank_deck_normal_wrong_engine_y_direction:{deck_id}")
                if crank_direction is not None and not math.isclose(
                    _dot(normal, crank_direction),
                    0.0,
                    rel_tol=0.0,
                    abs_tol=GEOMETRIC_RELATION_TOLERANCE,
                ):
                    errors.append(f"bank_deck_normal_not_orthogonal_to_crankshaft:{deck_id}")

    axes = parameters.get("cylinder_axes")
    expected_axis_ids = {
        *(f"CYL-P-{index:02d}" for index in range(1, 7)),
        *(f"CYL-N-{index:02d}" for index in range(1, 7)),
    }
    if not isinstance(axes, list) or len(axes) != 12:
        errors.append("exactly_twelve_cylinder_axes_required")
    else:
        ids = {item.get("id") for item in axes if isinstance(item, dict)}
        if ids != expected_axis_ids:
            errors.append("cylinder_axis_ids_invalid")
        seen_origins: set[tuple[float, float, float]] = set()
        bank_axis_positions: dict[str, list[tuple[str, float]]] = {
            "positive": [],
            "negative": [],
        }
        for index, axis in enumerate(axes):
            label = f"cylinder_axes[{index}]"
            if not isinstance(axis, dict) or set(axis) != {
                "id",
                "bank",
                "datum_ref",
                "origin_mm",
                "direction",
                "witness_length_mm",
                "position_standard_uncertainty_mm",
                "angular_standard_uncertainty_deg",
                "evidence_ref",
            }:
                errors.append(f"cylinder_axis_shape_invalid:{index}")
                continue
            expected_bank = "positive" if str(axis.get("id", "")).startswith("CYL-P-") else "negative"
            if axis.get("bank") != expected_bank:
                errors.append(f"cylinder_axis_bank_mismatch:{index}")
            if axis.get("datum_ref") != "ENGINE-FRAME-F30":
                errors.append(f"cylinder_axis_datum_ref_mismatch:{index}")
            origin = _vector(axis.get("origin_mm"), f"{label}.origin_mm", errors)
            direction = _unit_vector(axis.get("direction"), f"{label}.direction", errors)
            _positive(axis.get("witness_length_mm"), f"{label}.witness_length_mm", errors)
            _positive(axis.get("position_standard_uncertainty_mm"), f"{label}.position_standard_uncertainty_mm", errors)
            _positive(axis.get("angular_standard_uncertainty_deg"), f"{label}.angular_standard_uncertainty_deg", errors)
            _evidence_ref(
                axis.get("evidence_ref"),
                f"{label}.evidence_ref",
                evidence_kinds,
                "cylinder_axis_fit",
                used_evidence_ids,
                errors,
            )
            if origin is not None:
                origin_key = tuple(round(item, 9) for item in origin)
                if origin_key in seen_origins:
                    errors.append("duplicate_cylinder_axis_origin")
                seen_origins.add(origin_key)
                if axis.get("bank") in bank_axis_positions and isinstance(
                    axis.get("id"), str
                ):
                    bank_axis_positions[axis["bank"]].append(
                        (axis["id"], origin[0])
                    )
            deck_id = (
                "BANK-POSITIVE-DECK"
                if axis.get("bank") == "positive"
                else "BANK-NEGATIVE-DECK"
            )
            deck = deck_by_id.get(deck_id)
            if origin is not None and direction is not None and deck is not None:
                deck_origin = _vector(
                    deck.get("origin_mm"), f"{label}.deck_origin_relation", errors
                )
                deck_normal = _unit_vector(
                    deck.get("normal"), f"{label}.deck_normal_relation", errors
                )
                if deck_origin is not None and deck_normal is not None:
                    signed_distance = _dot(
                        _subtract(origin, deck_origin), deck_normal
                    )
                    if _finite(axis.get("position_standard_uncertainty_mm")) and _finite(
                        deck.get("position_standard_uncertainty_mm")
                    ):
                        position_allowance = float(
                            axis["position_standard_uncertainty_mm"]
                        ) + float(deck["position_standard_uncertainty_mm"])
                        if abs(signed_distance) > position_allowance:
                            errors.append(
                                f"cylinder_axis_origin_not_on_bank_deck:{axis.get('id')}"
                            )
                    alignment = _dot(direction, deck_normal)
                    if _finite(axis.get("angular_standard_uncertainty_deg")) and _finite(
                        deck.get("angular_standard_uncertainty_deg")
                    ):
                        angular_allowance = math.radians(
                            float(axis["angular_standard_uncertainty_deg"])
                            + float(deck["angular_standard_uncertainty_deg"])
                        )
                        minimum_alignment = math.cos(min(angular_allowance, math.pi))
                        if alignment < minimum_alignment:
                            errors.append(
                                f"cylinder_axis_not_aligned_with_bank_deck:{axis.get('id')}"
                            )
                if (
                    crank_direction is not None
                    and _finite(axis.get("angular_standard_uncertainty_deg"))
                    and not math.isclose(
                        _dot(direction, crank_direction),
                        0.0,
                        rel_tol=0.0,
                        abs_tol=math.sin(
                            min(
                                math.radians(
                                    float(axis["angular_standard_uncertainty_deg"])
                                ),
                                math.pi / 2.0,
                            )
                        )
                        + GEOMETRIC_RELATION_TOLERANCE,
                    )
                ):
                    errors.append(
                        f"cylinder_axis_not_orthogonal_to_crankshaft:{axis.get('id')}"
                    )
        for bank, positions_by_id in bank_axis_positions.items():
            ordered_x = [
                position
                for _axis_id, position in sorted(positions_by_id)
            ]
            if len(ordered_x) == 6 and any(
                ordered_x[index] >= ordered_x[index + 1]
                for index in range(len(ordered_x) - 1)
            ):
                errors.append(f"cylinder_axis_order_not_increasing_engine_x:{bank}")

    bearings = parameters.get("main_bearing_stations")
    if not isinstance(bearings, dict) or set(bearings) != {
        "physically_confirmed_count",
        "stations",
        "count_evidence_ref",
    }:
        errors.append("main_bearing_station_shape_invalid")
    else:
        count = bearings.get("physically_confirmed_count")
        stations = bearings.get("stations")
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 16:
            errors.append("main_bearing_confirmed_count_invalid")
        if not isinstance(stations, list) or not isinstance(count, int) or len(stations) != count:
            errors.append("main_bearing_station_count_mismatch")
        else:
            expected_ids = {f"MAIN-{index:02d}" for index in range(1, count + 1)}
            observed_ids = {item.get("id") for item in stations if isinstance(item, dict)}
            if observed_ids != expected_ids:
                errors.append("main_bearing_station_ids_invalid")
            positions: list[float] = []
            for index, station in enumerate(stations):
                label = f"main_bearing_stations.stations[{index}]"
                if not isinstance(station, dict) or set(station) != {
                    "id",
                    "datum_ref",
                    "position_x_mm",
                    "position_standard_uncertainty_mm",
                    "evidence_ref",
                }:
                    errors.append(f"main_bearing_station_entry_invalid:{index}")
                    continue
                if station.get("datum_ref") != "ENGINE-FRAME-F30":
                    errors.append(f"main_bearing_station_datum_ref_mismatch:{index}")
                if _finite(station.get("position_x_mm")):
                    positions.append(float(station["position_x_mm"]))
                else:
                    errors.append(f"finite_number_required:{label}.position_x_mm")
                _positive(station.get("position_standard_uncertainty_mm"), f"{label}.position_standard_uncertainty_mm", errors)
                _evidence_ref(
                    station.get("evidence_ref"),
                    f"{label}.evidence_ref",
                    evidence_kinds,
                    "main_bearing_station_fit",
                    used_evidence_ids,
                    errors,
                )
            if len(positions) == len(stations) and positions != sorted(positions):
                errors.append("main_bearing_stations_must_be_sorted")
            if len(set(round(item, 9) for item in positions)) != len(positions):
                errors.append("duplicate_main_bearing_station_position")
            if crank_span is not None and any(
                item < crank_span[0] - GEOMETRIC_RELATION_TOLERANCE
                or item > crank_span[1] + GEOMETRIC_RELATION_TOLERANCE
                for item in positions
            ):
                errors.append("main_bearing_station_outside_crankshaft_span")
        _evidence_ref(
            bearings.get("count_evidence_ref"),
            "main_bearing_stations.count_evidence_ref",
            evidence_kinds,
            "main_bearing_count_report",
            used_evidence_ids,
            errors,
        )

    gates = parameters.get("release_gates")
    if gates != {gate_id: False for gate_id in RELEASE_GATE_IDS}:
        errors.append("layout_parameter_release_gates_must_all_be_false")
    orphan_evidence = sorted(set(evidence_kinds) - used_evidence_ids)
    if orphan_evidence:
        errors.append("orphan_layout_evidence_entries:" + ",".join(orphan_evidence))
    return sorted(set(errors))


def _validate_plane(
    plane: Any,
    label: str,
    evidence_kinds: dict[str, str],
    expected_evidence_kind: str,
    used_evidence_ids: set[str],
    errors: list[str],
    expected_normal: tuple[float, float, float] | None = None,
) -> None:
    expected_keys = {
        "id",
        "datum_ref",
        "origin_mm",
        "normal",
        "u_direction",
        "extent_u_mm",
        "extent_v_mm",
        "position_standard_uncertainty_mm",
        "angular_standard_uncertainty_deg",
        "evidence_ref",
    }
    if not isinstance(plane, dict) or set(plane) != expected_keys:
        errors.append(f"plane_shape_invalid:{label}")
        return
    if not _is_identifier(plane.get("id")):
        errors.append(f"plane_id_invalid:{label}")
    if plane.get("datum_ref") != "ENGINE-FRAME-F30":
        errors.append(f"plane_datum_ref_mismatch:{label}")
    _vector(plane.get("origin_mm"), f"{label}.origin_mm", errors)
    normal = _unit_vector(plane.get("normal"), f"{label}.normal", errors)
    u_direction = _unit_vector(plane.get("u_direction"), f"{label}.u_direction", errors)
    if normal is not None and expected_normal is not None and any(
        not math.isclose(normal[index], value, rel_tol=0.0, abs_tol=CANONICAL_FRAME_TOLERANCE)
        for index, value in enumerate(expected_normal)
    ):
        errors.append(f"plane_normal_not_canonical:{label}")
    if normal is not None and u_direction is not None:
        dot = sum(normal[index] * u_direction[index] for index in range(3))
        if not math.isclose(dot, 0.0, rel_tol=0.0, abs_tol=1e-6):
            errors.append(f"plane_u_direction_not_orthogonal:{label}")
    _positive(plane.get("extent_u_mm"), f"{label}.extent_u_mm", errors)
    _positive(plane.get("extent_v_mm"), f"{label}.extent_v_mm", errors)
    _positive(plane.get("position_standard_uncertainty_mm"), f"{label}.position_standard_uncertainty_mm", errors)
    _positive(plane.get("angular_standard_uncertainty_deg"), f"{label}.angular_standard_uncertainty_deg", errors)
    _evidence_ref(
        plane.get("evidence_ref"),
        f"{label}.evidence_ref",
        evidence_kinds,
        expected_evidence_kind,
        used_evidence_ids,
        errors,
    )


def validate_binding(
    binding: dict[str, Any],
    record: dict[str, Any],
    layout_parameters_sha256: str,
    review_report_sha256: str,
    reviewer_public_key_sha256: str,
    trusted_reviewer_public_key_sha256: str | None,
) -> list[str]:
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "phase",
        "decision_id",
        "decision",
        "campaign_id",
        "f27_final_review_envelope_sha256",
        "f27_scan_to_engine_transform_sha256",
        "scan_sha256",
        "f27_variant_id",
        "f28_variant_id",
        "layout_parameters_sha256",
        "reviewer_id",
        "signed_at_utc",
        "review_report_evidence_ref",
        "review_report_sha256",
        "reviewer_public_key_sha256",
        "signature_algorithm",
        "signature_scope",
        "authorized_scope",
        "release_gates",
    }
    if set(binding) != expected_keys:
        errors.append("binding_key_set_mismatch")
    if binding.get("schema_version") != "1.0.0" or binding.get("phase") != "F30":
        errors.append("binding_identity_mismatch")
    if binding.get("decision") != "accepted_for_parametric_layout_only":
        errors.append("binding_decision_not_accepted_for_layout_only")
    if not _is_identifier(binding.get("decision_id")) or not _is_identifier(binding.get("reviewer_id")):
        errors.append("binding_canonical_identifiers_required")
    campaign = record.get("campaign", {})
    source = record.get("source_binding", {})
    variant = record.get("variant_identification", {})
    envelope = record.get("independent_reviews", {}).get("final_envelope", {})
    expected_bindings = {
        "campaign_id": campaign.get("campaign_id"),
        "f27_final_review_envelope_sha256": envelope.get("sha256"),
        "f27_scan_to_engine_transform_sha256": sha256_bytes(
            canonical_json_bytes(
                record.get("orientation_protocol", {}).get(
                    "scan_to_engine_transform", {}
                )
            )
        ),
        "scan_sha256": source.get("working_scan_sha256"),
        "f27_variant_id": variant.get("selected_candidate_variant_id"),
        "f28_variant_id": VARIANT_TARGET_MAP.get(
            variant.get("selected_candidate_variant_id")
        ),
        "layout_parameters_sha256": layout_parameters_sha256,
        "review_report_sha256": review_report_sha256,
        "reviewer_public_key_sha256": reviewer_public_key_sha256,
    }
    for key, expected in expected_bindings.items():
        if binding.get(key) != expected:
            errors.append(f"binding_value_mismatch:{key}")
    if binding.get("authorized_scope") != list(AUTHORIZED_SCOPE):
        errors.append("binding_authorized_scope_mismatch")
    f27_reviewer_ids = {
        review.get("reviewer_id")
        for key, review in record.get("independent_reviews", {}).items()
        if key in {"metrology", "variant_engineering"} and isinstance(review, dict)
    }
    if binding.get("reviewer_id") in f27_reviewer_ids:
        errors.append("binding_reviewer_must_be_distinct_from_f27_reviewers")
    if not _is_identifier(binding.get("review_report_evidence_ref")):
        errors.append("binding_review_report_evidence_ref_required")
    if not _is_sha256(binding.get("review_report_sha256")):
        errors.append("binding_review_report_sha256_required")
    if binding.get("signature_algorithm") != F30_SIGNATURE_ALGORITHM:
        errors.append("binding_signature_algorithm_mismatch")
    if binding.get("signature_scope") != "exact_canonical_binding_json_bytes":
        errors.append("binding_signature_scope_mismatch")
    if trusted_reviewer_public_key_sha256 is None:
        errors.append("binding_reviewer_trust_anchor_not_configured")
    elif reviewer_public_key_sha256 != trusted_reviewer_public_key_sha256:
        errors.append("binding_reviewer_public_key_not_trusted")
    binding_signed_at = _parse_strict_utc(binding.get("signed_at_utc"))
    if binding_signed_at is None:
        errors.append("binding_signed_at_utc_required")
    prior_review_times = [
        _parse_strict_utc(
            record.get("independent_reviews", {}).get(review_id, {}).get(
                "signed_at_utc" if review_id != "final_envelope" else "generated_at_utc"
            )
        )
        for review_id in ("metrology", "variant_engineering", "final_envelope")
    ]
    if (
        binding_signed_at is not None
        and all(item is not None for item in prior_review_times)
        and binding_signed_at <= max(item for item in prior_review_times if item is not None)
    ):
        errors.append("binding_signature_must_follow_f27_reviews_and_final_envelope")
    if binding.get("release_gates") != {gate_id: False for gate_id in RELEASE_GATE_IDS}:
        errors.append("binding_release_gates_must_all_be_false")
    return sorted(set(errors))


def _verify_binding_detached_signature(
    binding_path: Path,
    reviewer_public_key_path: Path,
    detached_signature_path: Path,
) -> bool:
    """Verifie une signature Ed25519 sans jamais charger de cle privee."""

    command = [
        "/usr/bin/openssl",
        "pkeyutl",
        "-verify",
        "-pubin",
        "-inkey",
        str(reviewer_public_key_path),
        "-rawin",
        "-in",
        str(binding_path),
        "-sigfile",
        str(detached_signature_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def layout_signature(parameters: dict[str, Any]) -> dict[str, Any]:
    axes = sorted(parameters["cylinder_axes"], key=lambda item: item["id"])
    stations = parameters["main_bearing_stations"]["stations"]
    return {
        "schema_version": "1.0.0",
        "phase": "F30",
        "units": "mm",
        "f27_variant_id": parameters["f27_variant_id"],
        "f28_variant_id": parameters["f28_variant_id"],
        "entity_counts": {
            "engine_coordinate_frame": 1,
            "crankshaft_axis": 1,
            "crankcase_split_plane": 1,
            "bank_deck_planes": 2,
            "cylinder_axes": len(axes),
            "main_bearing_stations": len(stations),
        },
        "engine_frame": {
            "origin_mm": parameters["engine_frame"]["origin_mm"],
            "right_handed": parameters["engine_frame"]["right_handed"],
            "handedness_token": parameters["engine_frame"]["handedness_token"],
        },
        "crankshaft_axis": {
            "origin_mm": parameters["crankshaft_axis"]["origin_mm"],
            "direction": parameters["crankshaft_axis"]["direction"],
            "span_mm": parameters["crankshaft_axis"]["span_mm"],
        },
        "bank_deck_planes": [
            {
                "id": item["id"],
                "origin_mm": item["origin_mm"],
                "normal": item["normal"],
                "u_direction": item["u_direction"],
                "extent_u_mm": item["extent_u_mm"],
                "extent_v_mm": item["extent_v_mm"],
            }
            for item in sorted(parameters["bank_deck_planes"], key=lambda item: item["id"])
        ],
        "crankcase_split_plane": {
            "origin_mm": parameters["crankcase_split_plane"]["origin_mm"],
            "normal": parameters["crankcase_split_plane"]["normal"],
            "u_direction": parameters["crankcase_split_plane"]["u_direction"],
            "extent_u_mm": parameters["crankcase_split_plane"]["extent_u_mm"],
            "extent_v_mm": parameters["crankcase_split_plane"]["extent_v_mm"],
        },
        "cylinder_axes": [
            {
                "id": item["id"],
                "origin_mm": item["origin_mm"],
                "direction": item["direction"],
                "witness_length_mm": item["witness_length_mm"],
            }
            for item in axes
        ],
        "main_bearing_stations_x_mm": [item["position_x_mm"] for item in stations],
        "construction_witness_conventions_mm": {
            "engine_frame_axis_length": 25.0,
            "main_bearing_marker_half_length": 5.0,
        },
        "construction_segments": _construction_segments(parameters),
        "solid_count": 0,
        "face_count": 0,
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def _add(first: list[float], second: list[float]) -> list[float]:
    return [first[index] + second[index] for index in range(3)]


def _scale(vector: list[float], factor: float) -> list[float]:
    return [component * factor for component in vector]


def _cross(first: list[float], second: list[float]) -> list[float]:
    return [
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    ]


def _construction_segments(parameters: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []

    def add_segment(segment_id: str, start: list[float], end: list[float]) -> None:
        segments.append(
            {
                "id": segment_id,
                "start_mm": [float(item) for item in start],
                "end_mm": [float(item) for item in end],
            }
        )

    frame_origin = [float(item) for item in parameters["engine_frame"]["origin_mm"]]
    frame_witness_length = 25.0
    for axis_name, direction in (
        ("X", [1.0, 0.0, 0.0]),
        ("Y", [0.0, 1.0, 0.0]),
        ("Z", [0.0, 0.0, 1.0]),
    ):
        add_segment(
            f"ENGINE-FRAME-{axis_name}",
            frame_origin,
            _add(frame_origin, _scale(direction, frame_witness_length)),
        )

    crank = parameters["crankshaft_axis"]
    crank_origin = [float(item) for item in crank["origin_mm"]]
    crank_direction = [float(item) for item in crank["direction"]]
    add_segment(
        "CRANKSHAFT-AXIS",
        _add(crank_origin, _scale(crank_direction, float(crank["span_mm"][0]))),
        _add(crank_origin, _scale(crank_direction, float(crank["span_mm"][1]))),
    )

    for plane in [parameters["crankcase_split_plane"], *parameters["bank_deck_planes"]]:
        origin = [float(item) for item in plane["origin_mm"]]
        u = [float(item) for item in plane["u_direction"]]
        normal = [float(item) for item in plane["normal"]]
        v = _cross(normal, u)
        half_u = float(plane["extent_u_mm"]) / 2.0
        half_v = float(plane["extent_v_mm"]) / 2.0
        corners = [
            _add(_add(origin, _scale(u, sign_u * half_u)), _scale(v, sign_v * half_v))
            for sign_u, sign_v in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        for index in range(4):
            add_segment(
                f"{plane['id']}-EDGE-{index + 1:02d}",
                corners[index],
                corners[(index + 1) % 4],
            )

    for axis in parameters["cylinder_axes"]:
        origin = [float(item) for item in axis["origin_mm"]]
        direction = [float(item) for item in axis["direction"]]
        half = float(axis["witness_length_mm"]) / 2.0
        add_segment(
            f"{axis['id']}-AXIS",
            _add(origin, _scale(direction, -half)),
            _add(origin, _scale(direction, half)),
        )

    bearing_marker_half_length = 5.0
    for station in parameters["main_bearing_stations"]["stations"]:
        center = [float(station["position_x_mm"]), 0.0, 0.0]
        add_segment(
            f"{station['id']}-MARKER-Y",
            _add(center, [0.0, -bearing_marker_half_length, 0.0]),
            _add(center, [0.0, bearing_marker_half_length, 0.0]),
        )
        add_segment(
            f"{station['id']}-MARKER-Z",
            _add(center, [0.0, 0.0, -bearing_marker_half_length]),
            _add(center, [0.0, 0.0, bearing_marker_half_length]),
        )
    return sorted(segments, key=lambda item: item["id"])


STEP_COORDINATE_DECIMALS = 9


def _canonical_segment_coordinates(
    start: list[float] | tuple[float, float, float],
    end: list[float] | tuple[float, float, float],
) -> list[list[float]]:
    """Normalise l'orientation d'un segment pour comparer un round-trip STEP."""

    endpoints = sorted(
        [
            tuple(round(float(value), STEP_COORDINATE_DECIMALS) for value in point)
            for point in (start, end)
        ]
    )
    return [list(endpoint) for endpoint in endpoints]


def _coordinate_multiset_signature(segments: list[dict[str, Any]]) -> str:
    normalized = sorted(
        _canonical_segment_coordinates(segment["start_mm"], segment["end_mm"])
        for segment in segments
    )
    return sha256_bytes(
        canonical_json_bytes(
            {
                "units": "mm",
                "coordinate_rounding_decimals": STEP_COORDINATE_DECIMALS,
                "segments": normalized,
            }
        )
    )


def _verified_roundtrip_coordinate_signatures(
    expected_segments: list[dict[str, Any]],
    reopened_segments: list[dict[str, Any]],
) -> tuple[str, str]:
    expected_geometry_sha256 = _coordinate_multiset_signature(expected_segments)
    reopened_geometry_sha256 = _coordinate_multiset_signature(reopened_segments)
    if reopened_geometry_sha256 != expected_geometry_sha256:
        raise RuntimeError("F30 construction STEP roundtrip changed segment coordinates")
    return expected_geometry_sha256, reopened_geometry_sha256


def _build_step(parameters: dict[str, Any], step_path: Path) -> dict[str, Any]:
    from build123d import Compound, Edge, Vector, export_step, import_step

    expected_segments = _construction_segments(parameters)
    edges: list[Any] = [
        Edge.make_line(Vector(*segment["start_mm"]), Vector(*segment["end_mm"]))
        for segment in expected_segments
    ]

    compound = Compound(children=edges)
    export_step(compound, step_path)
    reopened = import_step(step_path)
    validity_probe = reopened.is_valid
    reopened_valid = bool(validity_probe() if callable(validity_probe) else validity_probe)
    if not reopened_valid:
        raise RuntimeError("F30 construction STEP failed OCCT validity check")
    if len(reopened.solids()) != 0 or len(reopened.faces()) != 0:
        raise RuntimeError("F30 construction STEP must contain no solid or face")
    if len(reopened.edges()) != len(edges):
        raise RuntimeError("F30 construction STEP roundtrip changed edge count")
    reopened_segments: list[dict[str, Any]] = []
    for edge in reopened.edges():
        if getattr(edge.geom_type, "name", None) != "LINE":
            raise RuntimeError("F30 construction STEP roundtrip introduced non-line edge")
        vertices = edge.vertices()
        if len(vertices) != 2:
            raise RuntimeError("F30 construction STEP roundtrip edge has invalid vertices")
        reopened_segments.append(
            {
                "start_mm": [float(vertices[0].X), float(vertices[0].Y), float(vertices[0].Z)],
                "end_mm": [float(vertices[1].X), float(vertices[1].Y), float(vertices[1].Z)],
            }
        )
    expected_geometry_sha256, reopened_geometry_sha256 = (
        _verified_roundtrip_coordinate_signatures(
            expected_segments,
            reopened_segments,
        )
    )
    return {
        "authored_edge_count": len(edges),
        "reopened_edge_count": len(reopened.edges()),
        "reopened_linear_edge_count": len(reopened_segments),
        "reopened_face_count": len(reopened.faces()),
        "reopened_solid_count": len(reopened.solids()),
        "reopened_valid": reopened_valid,
        "coordinate_rounding_decimals": STEP_COORDINATE_DECIMALS,
        "expected_geometry_sha256": expected_geometry_sha256,
        "reopened_geometry_sha256": reopened_geometry_sha256,
        "reopened_geometry_matches_expected": True,
        "step_bytes": step_path.stat().st_size,
        "step_sha256_recorded_not_reproducibility_claim": sha256_file(step_path),
    }


def _private_path(root: Path, path: Path, label: str) -> list[str]:
    errors: list[str] = []
    try:
        resolved = path.resolve(strict=True)
        work_root = (root / "work").resolve(strict=True)
    except OSError:
        return [f"private_path_unavailable:{label}"]
    if not resolved.is_relative_to(work_root):
        errors.append(f"private_path_must_be_under_work:{label}")
    return errors


def validate_layout_evidence_files(
    parameters: dict[str, Any], evidence_root: Path
) -> tuple[list[str], list[dict[str, str]]]:
    errors: list[str] = []
    observed_manifest: list[dict[str, str]] = []
    try:
        if evidence_root.is_symlink() or not evidence_root.is_dir():
            return ["layout_evidence_root_must_be_real_directory"], []
        root_resolved = evidence_root.resolve(strict=True)
    except OSError:
        return ["layout_evidence_root_unavailable"], []

    index = parameters.get("evidence_index")
    if not isinstance(index, list):
        return ["layout_evidence_index_unavailable"], []
    indexed_paths: set[str] = set()
    for ordinal, entry in enumerate(index):
        if not isinstance(entry, dict) or not isinstance(entry.get("relative_path"), str):
            continue
        relative_path = entry["relative_path"]
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or any(
            part in {"", ".", ".."} for part in pure_path.parts
        ):
            continue
        candidate = evidence_root.joinpath(*pure_path.parts)
        current = evidence_root
        symlink_found = False
        for component in pure_path.parts:
            current = current / component
            if current.is_symlink():
                symlink_found = True
                break
        if symlink_found:
            errors.append(f"layout_evidence_symlink_forbidden:{ordinal}")
            continue
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            errors.append(f"layout_evidence_file_unavailable:{ordinal}")
            continue
        if not resolved.is_relative_to(root_resolved) or not candidate.is_file():
            errors.append(f"layout_evidence_regular_file_required:{ordinal}")
            continue
        observed_sha256 = sha256_file(candidate)
        if observed_sha256 != entry.get("sha256"):
            errors.append(f"layout_evidence_sha256_mismatch:{ordinal}")
        indexed_paths.add(relative_path)
        observed_manifest.append(
            {
                "evidence_id": str(entry.get("evidence_id")),
                "kind": str(entry.get("kind")),
                "sha256": observed_sha256,
            }
        )

    discovered_paths: set[str] = set()
    for directory, directory_names, file_names in os.walk(
        evidence_root, topdown=True, followlinks=False
    ):
        directory_path = Path(directory)
        for name in list(directory_names):
            child = directory_path / name
            if child.is_symlink():
                errors.append("layout_evidence_symlink_forbidden:directory")
                directory_names.remove(name)
        for name in file_names:
            child = directory_path / name
            if child.is_symlink():
                errors.append("layout_evidence_symlink_forbidden:file")
                continue
            discovered_paths.add(child.relative_to(evidence_root).as_posix())
    if discovered_paths != indexed_paths:
        errors.append("layout_evidence_directory_and_index_file_sets_mismatch")
    return sorted(set(errors)), sorted(
        observed_manifest, key=lambda item: item["evidence_id"]
    )


def _copy_regular_file_no_symlink(source: Path, destination: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    source_fd = os.open(source, flags)
    try:
        observed = os.fstat(source_fd)
        if not stat.S_ISREG(observed.st_mode):
            raise ValueError(f"regular_file_required:{source.name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(os.dup(source_fd), "rb") as input_stream, destination.open(
            "xb"
        ) as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
    finally:
        os.close(source_fd)


def _copy_evidence_tree_no_symlinks(source_root: Path, destination_root: Path) -> None:
    if source_root.is_symlink() or not source_root.is_dir():
        raise ValueError("real_evidence_directory_required")
    destination_root.mkdir(parents=True, exist_ok=False)
    for directory, directory_names, file_names in os.walk(
        source_root, topdown=True, followlinks=False
    ):
        source_directory = Path(directory)
        relative_directory = source_directory.relative_to(source_root)
        destination_directory = destination_root / relative_directory
        destination_directory.mkdir(parents=True, exist_ok=True)
        for name in directory_names:
            child = source_directory / name
            if child.is_symlink():
                raise ValueError("evidence_directory_symlink_forbidden")
        for name in file_names:
            child = source_directory / name
            if child.is_symlink():
                raise ValueError("evidence_file_symlink_forbidden")
            _copy_regular_file_no_symlink(child, destination_directory / name)


def _regular_tree_sha256s(root: Path) -> set[str]:
    hashes: set[str] = set()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("real_evidence_directory_required")
    for directory, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        directory_path = Path(directory)
        for name in directory_names:
            if (directory_path / name).is_symlink():
                raise ValueError("evidence_directory_symlink_forbidden")
        for name in file_names:
            path = directory_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("evidence_regular_file_required")
            hashes.add(sha256_file(path))
    return hashes


def _run_f27_validator(
    validator_path: Path,
    root: Path,
    record: Path,
    observations: Path,
    evidence_root: Path,
    working_scan: Path,
) -> dict[str, Any]:
    approved_validator_sha256 = next(
        approved_sha256
        for upstream_id, _path, _role, approved_sha256 in UPSTREAMS
        if upstream_id == "f27_validator"
    )
    validator_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        validator_flags |= os.O_NOFOLLOW
    try:
        validator_fd = os.open(validator_path, validator_flags)
    except OSError as exc:
        return {
            "report_status": "failed_closed",
            "errors": [f"f27_validator_open_failed:{type(exc).__name__}"],
        }
    validator_digest = hashlib.sha256()
    try:
        if not stat.S_ISREG(os.fstat(validator_fd).st_mode):
            os.close(validator_fd)
            return {
                "report_status": "failed_closed",
                "errors": ["f27_validator_regular_file_required"],
            }
        with os.fdopen(os.dup(validator_fd), "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                validator_digest.update(chunk)
        os.lseek(validator_fd, 0, os.SEEK_SET)
    except OSError as exc:
        os.close(validator_fd)
        return {
            "report_status": "failed_closed",
            "errors": [f"f27_validator_read_failed:{type(exc).__name__}"],
        }
    if validator_digest.hexdigest() != approved_validator_sha256:
        os.close(validator_fd)
        return {
            "report_status": "failed_closed",
            "errors": ["f27_validator_sha256_mismatch"],
        }
    validator_fd_path = (
        f"/proc/self/fd/{validator_fd}"
        if sys.platform.startswith("linux")
        else f"/dev/fd/{validator_fd}"
    )
    command = [
        sys.executable,
        validator_fd_path,
        "--root",
        str(root),
        "--record",
        str(record),
        "--observations",
        str(observations),
        "--evidence-root",
        str(evidence_root),
        "--working-scan",
        str(working_scan),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=root,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
            },
            stdin=subprocess.DEVNULL,
            timeout=180,
            pass_fds=(validator_fd,),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        os.close(validator_fd)
        return {
            "report_status": "failed_closed",
            "errors": [f"f27_validator_execution_failed:{type(exc).__name__}"],
        }
    os.close(validator_fd)
    try:
        report = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        return {
            "report_status": "failed_closed",
            "errors": ["f27_validator_output_unreadable"],
        }
    if completed.returncode != 0 and not report.get("errors"):
        report["errors"] = ["f27_validator_failed_without_errors"]
    return report


def validate_f27_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != "1.0.0" or report.get("phase") != "F27":
        errors.append("f27_validator_report_identity_mismatch")
    if report.get("report_status") != "ready_for_independent_binding_review_gates_closed":
        errors.append("f27_campaign_not_ready_for_binding")
    if report.get("errors") != []:
        errors.append("f27_campaign_contains_errors")
    expected_claims = {
        "campaign_packet_structurally_complete": True,
        "scan_variant_bound": False,
        "cad_input_authorized": False,
        "solver_authorized": False,
        "physicsnemo_authorized": False,
        "fabrication_authorized": False,
    }
    if report.get("claims") != expected_claims:
        errors.append("f27_validator_claims_mismatch")
    expected_gates = {gate_id: False for gate_id in F27_RELEASE_GATE_IDS}
    observed_gates = report.get("release_gates")
    if (
        not isinstance(observed_gates, dict)
        or set(observed_gates) != set(expected_gates)
        or any(value is not False for value in observed_gates.values())
    ):
        errors.append("f27_validator_release_gate_registry_mismatch")
    return errors


def failed_author_report(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "phase": "F30",
        "status": "failed_closed_no_output",
        "errors": sorted(set(errors)),
        "output_created": False,
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _open_directory_no_symlinks(path: Path) -> int:
    candidate = path.absolute()
    components = candidate.parts[1:]
    current_fd = os.open(os.path.sep, _directory_open_flags())
    try:
        for component in components:
            next_fd = os.open(component, _directory_open_flags(), dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        if not stat.S_ISDIR(os.fstat(current_fd).st_mode):
            raise ValueError("real_directory_required")
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _sha256_regular_file_at(directory_fd: int, name: str) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("temporary_output_must_contain_regular_files_only")
        digest = hashlib.sha256()
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        os.fsync(descriptor)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _rename_directory_noreplace(
    parent_fd: int, source_name: str, destination_name: str
) -> None:
    if any("/" in name or name in {"", ".", ".."} for name in (source_name, destination_name)):
        raise ValueError("publication_directory_name_invalid")
    libc = ctypes.CDLL(None, use_errno=True)
    source = os.fsencode(source_name)
    destination = os.fsencode(destination_name)
    if hasattr(libc, "renameat2"):
        rename = libc.renameat2
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(parent_fd, source, parent_fd, destination, 1)
    elif hasattr(libc, "renameatx_np"):
        rename = libc.renameatx_np
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(parent_fd, source, parent_fd, destination, 0x00000004)
    else:
        raise OSError(errno.ENOSYS, "atomic no-replace directory rename unavailable")
    if result != 0:
        observed_errno = ctypes.get_errno()
        raise OSError(observed_errno, os.strerror(observed_errno), destination_name)


def _create_staging_directory(parent_fd: int, output_name: str) -> str:
    for _attempt in range(32):
        name = f".{output_name}.tmp-{secrets.token_hex(16)}"
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        return name
    raise FileExistsError("unable_to_allocate_unique_staging_directory")


def _cleanup_staging_directory(parent_fd: int, staging_name: str) -> None:
    try:
        staging_fd = os.open(staging_name, _directory_open_flags(), dir_fd=parent_fd)
    except FileNotFoundError:
        return
    try:
        for name in os.listdir(staging_fd):
            try:
                os.unlink(name, dir_fd=staging_fd)
            except IsADirectoryError:
                raise ValueError("staging_subdirectory_forbidden")
    finally:
        os.close(staging_fd)
    os.rmdir(staging_name, dir_fd=parent_fd)


def _publish_with_completion_marker(
    parent_fd: int, staging_name: str, output_name: str
) -> tuple[dict[str, str], list[str]]:
    staging_fd = os.open(staging_name, _directory_open_flags(), dir_fd=parent_fd)
    try:
        source_names = sorted(os.listdir(staging_fd))
        if not source_names or "publication-complete.json" in source_names:
            raise ValueError("temporary_output_file_set_invalid")
        published_hashes = {
            name: _sha256_regular_file_at(staging_fd, name) for name in source_names
        }
        marker = {
            "schema_version": "1.0.0",
            "phase": "F30",
            "status": "publication_complete_release_gates_closed",
            "published_sha256": published_hashes,
            "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        }
        marker_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            marker_flags |= os.O_NOFOLLOW
        marker_fd = os.open(
            "publication-complete.json",
            marker_flags,
            0o600,
            dir_fd=staging_fd,
        )
        try:
            payload = canonical_json_bytes(marker)
            with os.fdopen(os.dup(marker_fd), "wb") as stream:
                stream.write(payload)
                stream.flush()
            os.fsync(marker_fd)
        finally:
            os.close(marker_fd)
        os.fsync(staging_fd)
        _rename_directory_noreplace(parent_fd, staging_name, output_name)
        os.fsync(parent_fd)
        return published_hashes, [*source_names, "publication-complete.json"]
    finally:
        os.close(staging_fd)


def author_layout(
    root: Path,
    record_path: Path,
    observations_path: Path,
    evidence_root: Path,
    working_scan_path: Path,
    binding_path: Path,
    binding_report_path: Path,
    binding_signature_path: Path,
    reviewer_public_key_path: Path,
    layout_evidence_root: Path,
    parameters_path: Path,
    output_dir: Path,
    *,
    step_builder: Callable[[dict[str, Any], Path], dict[str, Any]] = _build_step,
    trusted_reviewer_public_key_sha256: str | None = (
        TRUSTED_F30_REVIEWER_PUBLIC_KEY_SHA256
    ),
    binding_signature_verifier: Callable[[Path, Path, Path], bool] = (
        _verify_binding_detached_signature
    ),
) -> dict[str, Any]:
    errors = validate_template(root)
    for label, path in (
        ("record", record_path),
        ("observations", observations_path),
        ("evidence_root", evidence_root),
        ("working_scan", working_scan_path),
        ("binding", binding_path),
        ("binding_review_report", binding_report_path),
        ("binding_detached_signature", binding_signature_path),
        ("reviewer_public_key", reviewer_public_key_path),
        ("layout_evidence_root", layout_evidence_root),
        ("parameters", parameters_path),
    ):
        errors.extend(_private_path(root, path, label))
    allowed_output_root = (root / "work/917-engine/cad/f30").absolute()
    lexical_output = output_dir.absolute()
    if lexical_output.parent != allowed_output_root:
        errors.append("output_dir_outside_f30_work_root")
    if not _is_identifier(output_dir.name):
        errors.append("output_dir_name_must_be_canonical_identifier")
    current_output_parent = root
    for component in Path("work/917-engine/cad/f30").parts:
        current_output_parent = current_output_parent / component
        if current_output_parent.exists() and current_output_parent.is_symlink():
            errors.append("f30_output_root_symlink_forbidden")
            break
    if output_dir.exists():
        errors.append("output_dir_already_exists_no_overwrite")
    if not allowed_output_root.is_dir() or allowed_output_root.is_symlink():
        errors.append("f30_output_root_must_preexist_as_real_directory")
    try:
        if os.path.samefile(evidence_root, layout_evidence_root):
            errors.append("f27_and_f30_evidence_roots_must_be_distinct")
    except OSError:
        pass
    if errors:
        return failed_author_report(errors)

    work_root = root / "work"
    if not work_root.is_dir() or work_root.is_symlink():
        return failed_author_report(["real_work_root_required"])
    snapshot_context = tempfile.TemporaryDirectory(
        prefix=".f30-input-snapshot-", dir=work_root
    )
    snapshot_root = Path(snapshot_context.name)
    try:
        snapshot_paths = {
            "record": snapshot_root / "f27-record.json",
            "observations": snapshot_root / "f27-observations.csv",
            "working_scan": snapshot_root / "working-scan.obj",
            "binding": snapshot_root / "binding.json",
            "binding_report": snapshot_root / "binding-report.bin",
            "binding_signature": snapshot_root / "binding-signature.bin",
            "reviewer_public_key": snapshot_root / "reviewer-public-key.pem",
            "parameters": snapshot_root / "layout-parameters.json",
            "f27_validator": snapshot_root / "f27-validator.py",
            "f27_evidence": snapshot_root / "f27-evidence",
            "layout_evidence": snapshot_root / "layout-evidence",
        }
        for source, destination in (
            (record_path, snapshot_paths["record"]),
            (observations_path, snapshot_paths["observations"]),
            (working_scan_path, snapshot_paths["working_scan"]),
            (binding_path, snapshot_paths["binding"]),
            (binding_report_path, snapshot_paths["binding_report"]),
            (binding_signature_path, snapshot_paths["binding_signature"]),
            (reviewer_public_key_path, snapshot_paths["reviewer_public_key"]),
            (parameters_path, snapshot_paths["parameters"]),
            (root / F27_VALIDATOR_REL, snapshot_paths["f27_validator"]),
        ):
            _copy_regular_file_no_symlink(source, destination)
        _copy_evidence_tree_no_symlinks(
            evidence_root, snapshot_paths["f27_evidence"]
        )
        _copy_evidence_tree_no_symlinks(
            layout_evidence_root, snapshot_paths["layout_evidence"]
        )
    except (OSError, ValueError) as exc:
        snapshot_context.cleanup()
        return failed_author_report(
            [f"authoring_input_snapshot_failed:{type(exc).__name__}"]
        )

    record_path = snapshot_paths["record"]
    observations_path = snapshot_paths["observations"]
    working_scan_path = snapshot_paths["working_scan"]
    binding_path = snapshot_paths["binding"]
    binding_report_path = snapshot_paths["binding_report"]
    binding_signature_path = snapshot_paths["binding_signature"]
    reviewer_public_key_path = snapshot_paths["reviewer_public_key"]
    parameters_path = snapshot_paths["parameters"]
    evidence_root = snapshot_paths["f27_evidence"]
    layout_evidence_root = snapshot_paths["layout_evidence"]

    try:
        if _regular_tree_sha256s(evidence_root) & _regular_tree_sha256s(
            layout_evidence_root
        ):
            errors.append("f27_and_f30_evidence_payload_sha256_overlap")
    except (OSError, ValueError) as exc:
        errors.append(f"evidence_separation_check_failed:{type(exc).__name__}")

    f27_report = _run_f27_validator(
        snapshot_paths["f27_validator"],
        root,
        record_path,
        observations_path,
        evidence_root,
        working_scan_path,
    )
    errors.extend(validate_f27_report(f27_report))

    try:
        record = load_json(record_path)
        binding = load_json(binding_path)
        parameters = load_json(parameters_path)
    except (OSError, ValueError, DuplicateKeyError) as exc:
        errors.append(f"authoring_input_unreadable:{type(exc).__name__}")
        record = {}
        binding = {}
        parameters = {}

    binding_canonical_bytes = canonical_json_bytes(binding) if binding else b""
    if binding and binding_path.read_bytes() != binding_canonical_bytes:
        errors.append("binding_decision_must_be_canonical_json")
    parameters_canonical_bytes = canonical_json_bytes(parameters) if parameters else b""
    if parameters:
        errors.extend(validate_layout_parameters(parameters))
        if parameters_path.read_bytes() != parameters_canonical_bytes:
            errors.append("layout_parameters_must_be_canonical_json")
    layout_evidence_errors, layout_evidence_manifest = (
        validate_layout_evidence_files(parameters, layout_evidence_root)
        if parameters
        else (["layout_evidence_not_validated"], [])
    )
    errors.extend(layout_evidence_errors)
    parameters_sha256 = (
        sha256_bytes(parameters_canonical_bytes) if parameters_canonical_bytes else ""
    )
    binding_report_sha256 = (
        sha256_file(binding_report_path) if binding_report_path.is_file() else ""
    )
    binding_signature_sha256 = (
        sha256_file(binding_signature_path)
        if binding_signature_path.is_file()
        else ""
    )
    reviewer_public_key_sha256 = (
        sha256_file(reviewer_public_key_path)
        if reviewer_public_key_path.is_file()
        else ""
    )
    working_scan_sha256 = (
        sha256_file(working_scan_path) if working_scan_path.is_file() else ""
    )
    if working_scan_sha256 != SCAN_SHA256:
        errors.append("working_scan_sha256_mismatch_after_snapshot")
    if binding and record:
        errors.extend(
            validate_binding(
                binding,
                record,
                parameters_sha256,
                binding_report_sha256,
                reviewer_public_key_sha256,
                trusted_reviewer_public_key_sha256,
            )
        )
        if (
            trusted_reviewer_public_key_sha256 is not None
            and reviewer_public_key_sha256 == trusted_reviewer_public_key_sha256
            and not binding_signature_verifier(
                binding_path,
                reviewer_public_key_path,
                binding_signature_path,
            )
        ):
            errors.append("binding_detached_signature_invalid")
    if parameters and record:
        if parameters.get("campaign_id") != record.get("campaign", {}).get("campaign_id"):
            errors.append("parameters_campaign_id_mismatch")
        selected_f27_variant = record.get("variant_identification", {}).get(
            "selected_candidate_variant_id"
        )
        if parameters.get("f27_variant_id") != selected_f27_variant:
            errors.append("parameters_f27_variant_id_mismatch")
        if parameters.get("f28_variant_id") != VARIANT_TARGET_MAP.get(
            selected_f27_variant
        ):
            errors.append("parameters_f28_variant_id_mismatch")
        if parameters.get("f27_final_review_envelope_sha256") != record.get("independent_reviews", {}).get("final_envelope", {}).get("sha256"):
            errors.append("parameters_f27_envelope_mismatch")
        f27_transform_sha256 = sha256_bytes(
            canonical_json_bytes(
                record.get("orientation_protocol", {}).get(
                    "scan_to_engine_transform", {}
                )
            )
        )
        if (
            parameters.get("f27_scan_to_engine_transform_sha256")
            != f27_transform_sha256
        ):
            errors.append("parameters_f27_transform_sha256_mismatch")

    input_sha256 = {
        "f27_record": sha256_file(record_path),
        "f27_observations": sha256_file(observations_path),
        "working_scan": working_scan_sha256,
        "binding_decision": sha256_file(binding_path),
        "binding_review_report": binding_report_sha256,
        "binding_detached_signature": binding_signature_sha256,
        "reviewer_public_key": reviewer_public_key_sha256,
        "layout_parameters": parameters_sha256,
    }

    unique_errors = sorted(set(errors))
    if unique_errors:
        snapshot_context.cleanup()
        return failed_author_report(unique_errors)

    try:
        output_parent_fd = _open_directory_no_symlinks(allowed_output_root)
    except (OSError, ValueError) as exc:
        snapshot_context.cleanup()
        return failed_author_report(
            [f"f30_output_root_open_failed:{type(exc).__name__}"]
        )
    try:
        os.stat(output_dir.name, dir_fd=output_parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        os.close(output_parent_fd)
        snapshot_context.cleanup()
        return failed_author_report(["output_dir_already_exists_no_overwrite"])
    try:
        staging_name = _create_staging_directory(output_parent_fd, output_dir.name)
    except (OSError, ValueError) as exc:
        os.close(output_parent_fd)
        snapshot_context.cleanup()
        return failed_author_report(
            [f"f30_staging_directory_failed:{type(exc).__name__}"]
        )
    temporary = allowed_output_root / staging_name
    published_output_files: list[str] = []
    try:
        (temporary / "layout-parameters.json").write_bytes(parameters_canonical_bytes)
        step_metrics = step_builder(parameters, temporary / "engine-layout.step")
        step_path = temporary / "engine-layout.step"
        required_step_metrics = {
            "authored_edge_count",
            "reopened_edge_count",
            "reopened_linear_edge_count",
            "reopened_face_count",
            "reopened_solid_count",
            "reopened_valid",
            "coordinate_rounding_decimals",
            "expected_geometry_sha256",
            "reopened_geometry_sha256",
            "reopened_geometry_matches_expected",
            "step_bytes",
            "step_sha256_recorded_not_reproducibility_claim",
        }
        if set(step_metrics) != required_step_metrics:
            raise ValueError("step_roundtrip_metric_set_mismatch")
        if (
            not step_path.is_file()
            or step_path.is_symlink()
            or step_path.stat().st_size <= 0
            or step_metrics["authored_edge_count"] <= 0
            or step_metrics["reopened_edge_count"]
            != step_metrics["authored_edge_count"]
            or step_metrics["reopened_linear_edge_count"]
            != step_metrics["authored_edge_count"]
            or step_metrics["reopened_face_count"] != 0
            or step_metrics["reopened_solid_count"] != 0
            or step_metrics["reopened_valid"] is not True
            or step_metrics["coordinate_rounding_decimals"]
            != STEP_COORDINATE_DECIMALS
            or not _is_sha256(step_metrics["expected_geometry_sha256"])
            or step_metrics["reopened_geometry_sha256"]
            != step_metrics["expected_geometry_sha256"]
            or step_metrics["reopened_geometry_matches_expected"] is not True
            or step_metrics["step_bytes"] != step_path.stat().st_size
            or step_metrics["step_sha256_recorded_not_reproducibility_claim"]
            != sha256_file(step_path)
        ):
            raise ValueError("step_roundtrip_gate_failed")
        signature = layout_signature(parameters)
        geometry_report = {
            "schema_version": "1.0.0",
            "phase": "F30",
            "status": "construction_layout_authored_release_gates_closed",
            "geometry_signature": signature,
            "step_roundtrip": step_metrics,
            "claims": {
                "measured_layout_authored": True,
                "solid_geometry_authored": False,
                "functional_engine_cad_authored": False,
                "manufacturing_geometry_authored": False,
            },
            "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        }
        (temporary / "geometry-report.json").write_bytes(canonical_json_bytes(geometry_report))
        provenance = {
            "schema_version": "1.0.0",
            "phase": "F30",
            "status": "local_private_construction_layout_only",
            "runtime_image_policy": {
                "required_image_reference": CAD_IMAGE_REFERENCE,
                "exact_image_identity_verified_in_process": False,
                "controller_runtime_attestation_required": True,
                "claim": (
                    "Le processus dans le conteneur ne peut pas attester son propre "
                    "digest OCI; cette provenance n'affirme donc pas que l'image "
                    "requise a ete utilisee."
                ),
            },
            "input_sha256": input_sha256,
            "layout_evidence_manifest": layout_evidence_manifest,
            "output_sha256": {
                name: sha256_file(temporary / name)
                for name in (
                    "layout-parameters.json",
                    "engine-layout.step",
                    "geometry-report.json",
                )
            },
            "raw_scan_copied_to_output": False,
            "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        }
        (temporary / "provenance-manifest.json").write_bytes(canonical_json_bytes(provenance))
        _published_hashes, published_output_files = _publish_with_completion_marker(
            output_parent_fd,
            staging_name,
            output_dir.name,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        try:
            _cleanup_staging_directory(output_parent_fd, staging_name)
        except (OSError, ValueError):
            pass
        os.close(output_parent_fd)
        snapshot_context.cleanup()
        return failed_author_report([f"authoring_failed:{type(exc).__name__}"])
    finally:
        try:
            _cleanup_staging_directory(output_parent_fd, staging_name)
        except (OSError, ValueError):
            pass
    os.close(output_parent_fd)
    result = {
        "schema_version": "1.0.0",
        "phase": "F30",
        "status": "construction_layout_authored_release_gates_closed",
        "errors": [],
        "output_created": True,
        "output_files": sorted(published_output_files),
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }
    snapshot_context.cleanup()
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-template", action="store_true")
    mode.add_argument("--check-template", action="store_true")
    mode.add_argument("--author", action="store_true")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--working-scan", type=Path)
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--binding-report", type=Path)
    parser.add_argument("--binding-signature", type=Path)
    parser.add_argument("--reviewer-public-key", type=Path)
    parser.add_argument("--layout-evidence-root", type=Path)
    parser.add_argument("--parameters", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    template_path = root / TEMPLATE_REL
    if args.write_template:
        try:
            template_path.write_bytes(canonical_json_bytes(build_template(root)))
        except (OSError, ValueError) as exc:
            print(
                json.dumps(
                    failed_author_report(
                        [f"template_write_failed:{type(exc).__name__}"]
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 1
        print(template_path.relative_to(root))
        return 0
    if args.check_template:
        errors = validate_template(root)
        report = {
            "schema_version": "1.0.0",
            "phase": "F30",
            "status": "passed_fail_closed" if not errors else "failed_closed",
            "errors": errors,
            "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0 if not errors else 1
    required = {
        "record": args.record,
        "observations": args.observations,
        "evidence_root": args.evidence_root,
        "working_scan": args.working_scan,
        "binding": args.binding,
        "binding_report": args.binding_report,
        "binding_signature": args.binding_signature,
        "reviewer_public_key": args.reviewer_public_key,
        "layout_evidence_root": args.layout_evidence_root,
        "parameters": args.parameters,
        "output_dir": args.output_dir,
    }
    missing = sorted(key for key, value in required.items() if value is None)
    if missing:
        print(
            json.dumps(
                failed_author_report(
                    [f"missing_argument:{key}" for key in missing]
                ),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    report = author_layout(
        root,
        args.record,
        args.observations,
        args.evidence_root,
        args.working_scan,
        args.binding,
        args.binding_report,
        args.binding_signature,
        args.reviewer_public_key,
        args.layout_evidence_root,
        args.parameters,
        args.output_dir,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "construction_layout_authored_release_gates_closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
