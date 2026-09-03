#!/usr/bin/env python3
"""Valide l'autorite documentaire bi-variante F43 sans dependance externe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


CONTRACT_RELATIVE_PATH = Path("twins/reference-917-engine/variant-authority-f43.json")
EXPECTED_BINDINGS = {
    "ams_917_engine_technical_analysis": (
        "catalog/sources/src-ams-917-engine-technical-analysis.json",
        "87669cfbda481b816acb880f54c37e3cc73dffd6e753fd8b695248c9c9765a37",
    ),
    "porsche_newsroom_91730_turbo": (
        "catalog/sources/src-porsche-newsroom-91730-turbo.json",
        "beffabf935be3baec242bb134a50b6a112c038564c8664f803778cae5f219e55",
    ),
    "classical_solver_facts_f13": (
        "twins/reference-917-engine/classical-solver-cases-f13.json",
        "1ec8a0c49e95f8f2c8185d4c0f4074d1ed4b36477996ba590cc9f92eccf42a97",
    ),
    "dimensional_skeleton_f14": (
        "twins/reference-917-engine/dimensional-skeleton-f14.json",
        "2824eb0aeb9bfa5f16d7720ade0ba05236d2e4319ef6cbb97b11ff2e0e28b00e",
    ),
    "dual_variant_parametric_contract_f28": (
        "twins/reference-917-engine/dual-variant-parametric-cad-contract-f28.json",
        "920b8c022676a9941c8764fb1f0f178da47220798dd6fa7e96ba6d410aee5abb",
    ),
    "clean_sheet_turbo_screening_f32": (
        "twins/reference-917-engine/clean-sheet-2026-f32.json",
        "485a381b26f4d02da82d66b277e9e4ab16dbeaf7f72b5eb341b02304355ddfb4",
    ),
}
EXPECTED_VARIANTS = {
    "917_2026_flat12_na_candidate": {
        "configuration": "naturally_aspirated",
        "source_fact_variant_id": "type_912_5_0_na",
        "cylinder_count": 12,
        "bore_mm": 86.8,
        "stroke_mm": 70.4,
        "documented_displacement_cm3": 4999.0,
        "turbocharger_count": 0,
    },
    "917_2026_flat12_twin_turbo_1600hp_target": {
        "configuration": "twin_turbo",
        "source_fact_variant_id": "917_30_1973_turbo_5374",
        "cylinder_count": 12,
        "bore_mm": 90.0,
        "stroke_mm": 70.4,
        "documented_displacement_cm3": 5374.0,
        "turbocharger_count": 2,
    },
}
EXPECTED_VARIANT_KEYS = {
    "variant_id",
    "product_label",
    "configuration",
    "source_fact_variant_id",
    "cylinder_count",
    "bore_mm",
    "stroke_mm",
    "documented_displacement_cm3",
    "calculated_displacement_cm3",
    "turbocharger_count",
    "requested_power",
    "parameter_classification",
    "historical_hardware_identity_equivalent",
    "geometry_released",
    "solver_results_released",
}
EXPECTED_CONFLICT_BINDINGS = {
    "f33_na_uses_turbo_bore": (
        "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json",
        "6bbd5a5373660641c50e85dce6b45ac23222751d77f9f86783d82bd72530e73b",
    ),
    "f37_na_bench_uses_legacy_4_5_identity": (
        "twins/reference-917-engine/integrated-bench-assembly-f37.json",
        "44241ab4b756f0308ab811e91e8b5c2f5bf5aca20eec8871221c3e6348ea6f4f",
    ),
    "f38_na_bench_lineage_uses_legacy_4_5_identity": (
        "twins/reference-917-engine/gas-path-network-f38.json",
        "e52c7e7910f0263578e4197276a2abbafc36e83460f9bd55346af4a497c51c1d",
    ),
    "f39_na_uses_turbo_bore": (
        "twins/reference-917-engine/unsteady-network-f39.json",
        "c62d1dffcd57a13dce569eb1af05e61c84b893b27613f77c01b0878831743432",
    ),
}
EXPECTED_F13_FACTS = {
    "FACT-CYLINDER-COUNT": ("type_912_5_0_na", 12, "count"),
    "FACT-50-BORE": ("type_912_5_0_na", 86.8, "mm"),
    "FACT-50-STROKE": ("type_912_5_0_na", 70.4, "mm"),
    "FACT-50-DISPLACEMENT": ("type_912_5_0_na", 4999.0, "cm3"),
    "FACT-CYLINDER-COUNT-91730-1973": ("917_30_1973_turbo_5374", 12, "count"),
    "FACT-5374-BORE": ("917_30_turbo_5374", 90.0, "mm"),
    "FACT-5374-STROKE": ("917_30_turbo_5374", 70.4, "mm"),
    "FACT-5374-DISPLACEMENT": ("917_30_turbo_5374", 5374.0, "cm3"),
}
EXPECTED_TOP_LEVEL_KEYS = {
    "$comment",
    "schema_version",
    "phase",
    "status",
    "asset_id",
    "authority_scope",
    "source_bindings",
    "product_variants",
    "legacy_branch_exclusions",
    "downstream_conflict_register",
    "migration_policy",
    "release_gates",
    "required_next_evidence",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_tracked_file(project_root: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError(f"invalid project-relative path: {relative_path!r}")
    root = project_root.resolve()
    candidate = project_root / relative_path
    if candidate.is_symlink():
        raise ValueError(f"symlink is not accepted: {relative_path}")
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    if not resolved.is_file():
        raise ValueError(f"not a regular file: {relative_path}")
    return resolved


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _index(records: list[dict[str, Any]], key: str, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        value = record.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{label}: missing non-empty {key}")
            continue
        if value in result:
            errors.append(f"{label}: duplicate {key} {value}")
            continue
        result[value] = record
    return result


def _validate_binding_set(
    project_root: Path,
    records: list[dict[str, Any]],
    expected: dict[str, tuple[str, str]],
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    indexed = _index(records, "id", label, errors)
    if set(indexed) != set(expected):
        errors.append(f"{label}: expected ids {sorted(expected)}, got {sorted(indexed)}")
    loaded: dict[str, Any] = {}
    for record_id, (relative_path, digest) in expected.items():
        record = indexed.get(record_id)
        if record is None:
            continue
        if record.get("path") != relative_path:
            errors.append(f"{label}/{record_id}: path mismatch")
        if record.get("sha256") != digest:
            errors.append(f"{label}/{record_id}: declared sha256 mismatch")
        try:
            path = _resolve_tracked_file(project_root, relative_path)
        except (OSError, ValueError) as exc:
            errors.append(f"{label}/{record_id}: {exc}")
            continue
        actual = _sha256(path)
        if actual != digest:
            errors.append(f"{label}/{record_id}: file sha256 mismatch: {actual}")
            continue
        try:
            loaded[record_id] = _load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{label}/{record_id}: invalid JSON: {exc}")
    return loaded


def _facts_by_id(variant: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["fact_id"]: record for record in variant["facts"]}


def _validate_source_crosswalk(loaded: dict[str, Any], errors: list[str]) -> None:
    f13 = loaded.get("classical_solver_facts_f13")
    if f13 is not None:
        facts = {record["id"]: record for record in f13.get("fact_registry", [])}
        for fact_id, (variant, value, unit) in EXPECTED_F13_FACTS.items():
            record = facts.get(fact_id)
            if record is None:
                errors.append(f"F13: missing fact {fact_id}")
                continue
            candidate = record.get("candidate", {})
            if (record.get("variant"), candidate.get("value"), candidate.get("unit")) != (variant, value, unit):
                errors.append(f"F13: fact {fact_id} no longer matches F43")
            if record.get("design_lock") is not False:
                errors.append(f"F13: fact {fact_id} must remain unlocked")

    f14 = loaded.get("dimensional_skeleton_f14")
    if f14 is not None:
        variants = {record["variant_id"]: record for record in f14.get("variants", [])}
        expected = {
            "917_5_0_na_4999": (12, 86.8, 70.4, 4999.0),
            "917_30_turbo_5374": (12, 90.0, 70.4, 5374.0),
        }
        for variant_id, values in expected.items():
            record = variants.get(variant_id)
            if record is None:
                errors.append(f"F14: missing variant {variant_id}")
                continue
            facts = _facts_by_id(record)
            actual = tuple(
                facts[fact_id]["value"]
                for fact_id in ("cylinder_count", "bore_diameter_mm", "stroke_mm", "documented_displacement_cm3")
            )
            if actual != values:
                errors.append(f"F14: variant {variant_id} no longer matches F43")

    f28 = loaded.get("dual_variant_parametric_contract_f28")
    if f28 is not None:
        guides = {record["variant_id"]: record for record in f28.get("documentary_design_guides", [])}
        expected = {
            "type_912_5_0_na": (86.8, 70.4),
            "917_30_1973_turbo_5374": (90.0, 70.4),
        }
        for variant_id, values in expected.items():
            guide = guides.get(variant_id)
            if guide is None:
                errors.append(f"F28: missing guide {variant_id}")
                continue
            if (guide.get("bore", {}).get("value"), guide.get("stroke", {}).get("value")) != values:
                errors.append(f"F28: guide {variant_id} no longer matches F43")
            if guide.get("design_lock") is not False or guide.get("cad_parameter_applied") is not False:
                errors.append(f"F28: guide {variant_id} must remain documentary")

    f32 = loaded.get("clean_sheet_turbo_screening_f32")
    if f32 is not None:
        target = f32.get("program", {}).get("target_power", {})
        if (target.get("value"), target.get("unit"), target.get("proven")) != (1600.0, "mechanical_hp", False):
            errors.append("F32: the 1600 mechanical_hp requirement lineage changed")


def _validate_variants(contract: dict[str, Any], errors: list[str]) -> None:
    variants = _index(contract.get("product_variants", []), "variant_id", "product_variants", errors)
    if set(variants) != set(EXPECTED_VARIANTS):
        errors.append(f"product_variants: expected {sorted(EXPECTED_VARIANTS)}, got {sorted(variants)}")
    for variant_id, expected in EXPECTED_VARIANTS.items():
        record = variants.get(variant_id)
        if record is None:
            continue
        if set(record) != EXPECTED_VARIANT_KEYS:
            errors.append(f"{variant_id}: unexpected variant keys {sorted(set(record) ^ EXPECTED_VARIANT_KEYS)}")
        for key, value in expected.items():
            if record.get(key) != value:
                errors.append(f"{variant_id}: {key} must be {value!r}")
        calculated = math.pi / 4.0 * (record["bore_mm"] / 10.0) ** 2 * (record["stroke_mm"] / 10.0) * record["cylinder_count"]
        if not math.isclose(record.get("calculated_displacement_cm3", -1.0), calculated, rel_tol=0.0, abs_tol=1e-9):
            errors.append(f"{variant_id}: calculated_displacement_cm3 is not derived from bore/stroke/count")
        if abs(calculated - record["documented_displacement_cm3"]) > 0.5:
            errors.append(f"{variant_id}: documented and calculated displacement differ by more than 0.5 cm3")
        for field in ("historical_hardware_identity_equivalent", "geometry_released", "solver_results_released"):
            if record.get(field) is not False:
                errors.append(f"{variant_id}: {field} must remain false")

    na = variants.get("917_2026_flat12_na_candidate", {})
    if na.get("requested_power", "missing") is not None:
        errors.append("NA product: requested_power must remain null")
    turbo = variants.get("917_2026_flat12_twin_turbo_1600hp_target", {})
    power = turbo.get("requested_power", {})
    expected_power = {
        "value": 1600.0,
        "unit": "mechanical_hp",
        "origin": "user_design_requirement_carried_by_f32",
        "measured": False,
        "simulated": False,
        "proven": False,
    }
    if power != expected_power:
        errors.append("turbo product: requested_power must remain the exact unproven user requirement")


def _validate_legacy_and_conflicts(
    project_root: Path,
    contract: dict[str, Any],
    errors: list[str],
) -> None:
    legacy = contract.get("legacy_branch_exclusions", {})
    expected_legacy = {
        "f10_path": "twins/reference-917-engine/variant-configurations-f10.json",
        "f10_sha256": "dfb6ee25f367c934b11ff020e34d9d77296d2b5a535030a73221696af7c7a640",
        "excluded_na_variant_id": "type_912_4_5_na",
        "excluded_na_bore_mm": 85.0,
        "excluded_na_stroke_mm": 66.0,
        "excluded_na_documented_displacement_cm3": 4494.0,
        "silent_na_inheritance_allowed": False,
        "historical_turbo_hardware_identity_transfer_allowed": False,
    }
    for key, value in expected_legacy.items():
        if legacy.get(key) != value:
            errors.append(f"legacy_branch_exclusions: {key} must be {value!r}")
    try:
        f10_path = _resolve_tracked_file(project_root, legacy.get("f10_path", ""))
        if _sha256(f10_path) != legacy.get("f10_sha256"):
            errors.append("legacy_branch_exclusions: F10 file sha256 mismatch")
        f10 = _load_json(f10_path)
        variants = {record["variant_id"]: record for record in f10.get("variants", [])}
        old = variants.get("type_912_4_5_na", {}).get("geometry", {})
        if (old.get("bore_mm"), old.get("stroke_mm"), old.get("documented_displacement_cm3")) != (85.0, 66.0, 4494.0):
            errors.append("F10: excluded 4.5 L branch snapshot changed")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"legacy_branch_exclusions: {exc}")

    conflicts = contract.get("downstream_conflict_register", [])
    loaded = _validate_binding_set(project_root, conflicts, EXPECTED_CONFLICT_BINDINGS, "downstream_conflict_register", errors)
    for record in conflicts:
        if record.get("conforms_to_f43") is not False or record.get("results_reusable_as_f43_product_evidence") is not False:
            errors.append(f"{record.get('id')}: conflict must remain fail closed")

    f33 = loaded.get("f33_na_uses_turbo_bore")
    if f33 is not None:
        variants = {record["id"]: record for record in f33.get("engine_variants", [])}
        candidate = variants.get("917_2026_flat12_na_candidate", {}).get("forward_solver_input", {})
        if (candidate.get("bore_mm"), candidate.get("stroke_mm")) != (90.0, 70.4):
            errors.append("F33: registered NA conflict snapshot changed")
    f37 = loaded.get("f37_na_bench_uses_legacy_4_5_identity")
    if f37 is not None:
        variants = {record["variant_id"]: record for record in f37.get("variants", [])}
        candidate = variants.get("type_912_4_5_na", {})
        if (candidate.get("f28_variant_id"), candidate.get("f28_identity_match")) != ("type_912_5_0_na", False):
            errors.append("F37: registered legacy NA identity conflict snapshot changed")
    f38 = loaded.get("f38_na_bench_lineage_uses_legacy_4_5_identity")
    if f38 is not None:
        variants = {record["variant_id"]: record for record in f38.get("variants", [])}
        candidate = variants.get("917_2026_flat12_na_candidate", {})
        if (candidate.get("bench_variant_id"), candidate.get("bench_geometry_identity_match")) != ("type_912_4_5_na", False):
            errors.append("F38: registered legacy NA lineage conflict snapshot changed")
    f39 = loaded.get("f39_na_uses_turbo_bore")
    if f39 is not None:
        candidate = f39.get("variant", {})
        if (candidate.get("variant_id"), candidate.get("bore_mm"), candidate.get("stroke_mm")) != (
            "917_2026_flat12_na_candidate",
            90.0,
            70.4,
        ):
            errors.append("F39: registered NA conflict snapshot changed")


def validate(project_root: Path, contract_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    root = project_root.resolve()
    path = contract_path or root / CONTRACT_RELATIVE_PATH
    try:
        contract = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"contract: {exc}"]

    if set(contract) != EXPECTED_TOP_LEVEL_KEYS:
        errors.append(f"contract: unexpected top-level keys {sorted(set(contract) ^ EXPECTED_TOP_LEVEL_KEYS)}")
    if contract.get("schema_version") != "1.0.0" or contract.get("phase") != "F43":
        errors.append("contract: schema_version/phase mismatch")
    if contract.get("status") != "source_bound_2026_variant_authority_only_all_geometry_solver_and_release_gates_blocked":
        errors.append("contract: status mismatch")

    scope = contract.get("authority_scope", {})
    if scope.get("variant_parameter_authority") is not True:
        errors.append("authority_scope: variant_parameter_authority must be true")
    for key in (
        "historical_replica",
        "geometry_authority",
        "performance_authority",
        "manufacturing_authority",
        "consumer_migration_complete",
    ):
        if scope.get(key) is not False:
            errors.append(f"authority_scope: {key} must be false")

    loaded = _validate_binding_set(root, contract.get("source_bindings", []), EXPECTED_BINDINGS, "source_bindings", errors)
    for record in contract.get("source_bindings", []):
        if record.get("geometry_transfer_authorized") is not False:
            errors.append(f"source_bindings/{record.get('id')}: geometry transfer must remain false")
    _validate_source_crosswalk(loaded, errors)
    _validate_variants(contract, errors)
    _validate_legacy_and_conflicts(root, contract, errors)

    migration = contract.get("migration_policy", {})
    expected_migration = {
        "f43_product_variant_ids_are_authoritative_for_future_2026_work": True,
        "existing_f33_f37_f38_f39_results_are_grandfathered_as_product_evidence": False,
        "consumer_must_bind_this_contract_by_path_and_sha256": True,
        "consumer_must_regenerate_after_parameter_change": True,
        "cross_variant_geometry_or_solver_result_reuse_allowed": False,
        "unmeasured_dimensions_may_be_filled_from_other_variants": False,
    }
    if migration != expected_migration:
        errors.append("migration_policy: exact fail-closed policy required")
    gates = contract.get("release_gates", {})
    if not gates or any(value is not False for value in gates.values()):
        errors.append("release_gates: every gate must be explicitly false")
    if len(contract.get("required_next_evidence", [])) != 5:
        errors.append("required_next_evidence: exact five-item migration/evidence list required")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args(argv)
    contract_path = args.contract
    if contract_path is not None and not contract_path.is_absolute():
        contract_path = args.project_root / contract_path
    errors = validate(args.project_root, contract_path)
    if errors:
        for error in errors:
            print(f"F43 ERROR: {error}", file=sys.stderr)
        return 1
    print("F43 variant authority validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
