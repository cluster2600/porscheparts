#!/usr/bin/env python3
"""Valide le contrat F45 des deux culasses turbo sans ouvrir de gate physique."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


CONTRACT = Path("twins/reference-917-engine/head-architecture-authority-f45.json")
EXPECTED_VARIANTS = {
    "917_30_turbo_5374_2v_f45": (2, 1, 1),
    "917_30_turbo_5374_4v_f45": (4, 2, 2),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    contract = load(root / CONTRACT)
    if contract.get("phase") != "F45":
        errors.append("phase_must_be_F45")

    engine = contract.get("engine_authority", {})
    engine_path = root / engine.get("path", "")
    if not engine_path.is_file() or sha256(engine_path) != engine.get("sha256"):
        errors.append("engine_authority_hash_mismatch")
    if engine.get("variant_id") != "917_2026_flat12_twin_turbo_1600hp_target":
        errors.append("wrong_turbo_variant")
    if engine.get("requested_power_proven") is not False:
        errors.append("1600_hp_must_remain_unproven")

    morphology = contract.get("morphology_authority", {})
    source_path = root / morphology.get("source_record_path", "")
    if not source_path.is_file() or sha256(source_path) != morphology.get("source_record_sha256"):
        errors.append("morphology_source_hash_mismatch")
    required_false = (
        "absolute_scale_certified",
        "global_anisotropic_scaling_allowed",
        "global_ellipse_or_oval_envelope_allowed",
        "ellipse_extrusion_allowed_for_head_body_or_fins",
        "f39_ellipse_volume_lineage_accepted",
    )
    for key in required_false:
        if morphology.get(key) is not False:
            errors.append(f"morphology/{key}_must_be_false")
    if morphology.get("preserve_external_scan_morphology") is not True:
        errors.append("scan_morphology_must_be_preserved")

    variants = {item.get("variant_id"): item for item in contract.get("head_variants", [])}
    if set(variants) != set(EXPECTED_VARIANTS):
        errors.append("exact_2v_4v_variant_set_required")
    for variant_id, counts in EXPECTED_VARIANTS.items():
        item = variants.get(variant_id, {})
        observed = (
            item.get("valve_count_per_cylinder"),
            item.get("intake_valve_count"),
            item.get("exhaust_valve_count"),
        )
        if observed != counts:
            errors.append(f"{variant_id}/valve_counts_invalid")
        for gate in ("geometry_released", "solver_results_released", "metal_print_authorized"):
            if item.get(gate) is not False:
                errors.append(f"{variant_id}/{gate}_must_be_false")

    cooling = contract.get("additive_air_cooling", {})
    if cooling.get("engine_core_coolant") != "forced_air_and_engine_oil_only":
        errors.append("air_oil_core_required")
    for key in ("liquid_water_jacket_allowed", "closed_powder_trap_allowed"):
        if cooling.get(key) is not False:
            errors.append(f"additive_air_cooling/{key}_must_be_false")
    for key in (
        "all_internal_air_channels_must_be_through_open",
        "all_internal_air_channels_must_be_powder_removable",
        "all_internal_air_channels_must_be_ct_inspectable",
    ):
        if cooling.get(key) is not True:
            errors.append(f"additive_air_cooling/{key}_must_be_true")

    oil = contract.get("secondary_oil_circuit", {})
    for key in (
        "dry_sump_return_required",
        "pressurized_gallery_required",
        "metered_jets_required",
        "gravity_and_scavenge_returns_required",
        "printed_passages_must_be_through_open_flushable_and_ct_inspectable",
        "machining_and_cleanout_access_required",
    ):
        if oil.get(key) is not True:
            errors.append(f"secondary_oil_circuit/{key}_must_be_true")
    for key in ("closed_oil_cooling_jacket_allowed", "hardware_ranges_and_oil_grade_locked"):
        if oil.get(key) is not False:
            errors.append(f"secondary_oil_circuit/{key}_must_be_false")

    limits = contract.get("required_solver_matrix", {})
    if limits.get("minimum_mesh_levels") != 3:
        errors.append("three_mesh_levels_required")
    for key, expected in (
        ("mass_and_energy_balance_limit_fraction", 0.01),
        ("mesh_convergence_limit_fraction", 0.05),
        ("cross_method_difference_limit_fraction", 0.05),
    ):
        if limits.get(key) != expected:
            errors.append(f"{key}_must_equal_{expected}")

    gates = contract.get("release_gates", {})
    if not gates or any(value is not False for value in gates.values()):
        errors.append("all_release_gates_must_start_false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate(args.project_root.resolve())
    payload = {"phase": "F45", "status": "passed" if not errors else "failed", "errors": errors}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
