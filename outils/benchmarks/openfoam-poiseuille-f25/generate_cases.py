#!/usr/bin/env python3
"""Génère trois cas OpenFOAM synthétiques depuis le contrat F25."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import stat
from pathlib import Path
from typing import Any


EXPECTED_BENCHMARK_ID = "openfoam-planar-poiseuille-tool-verification-f25"
EXPECTED_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-mesh-cfd@"
    "sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f"
)
EXPECTED_MESHES = (("coarse", 8), ("medium", 16), ("fine", 32))
EXPECTED_EXCLUDED_WORKFLOWS = [
    "porsche-917-classical-solver-cases-f13",
    "porsche-917-physicsnemo-dataset-f14",
]
EXPECTED_DECK_FILES = [
    "0/U",
    "0/p",
    "constant/fvModels",
    "constant/momentumTransport",
    "constant/physicalProperties",
    "system/blockMeshDict",
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
]
EXPECTED_ACCEPTANCE = {
    "mesh_check_required": True,
    "solver_completion_required": True,
    "ux_linear_solver_final_residual_max": 1e-8,
    "p_linear_solver_final_residual_max": 1e-12,
    "cyclic_pair_antisymmetry_relative_max": 1e-10,
    "continuity_local_sum_max": 1e-12,
    "fine_mass_flow_relative_error_max": 0.002,
    "fine_l2_relative_max": 0.002,
    "fine_linf_relative_max": 0.002,
    "transverse_velocity_abs_max_m_s": 1e-12,
    "observed_order_min": 1.8,
    "observed_order_max": 2.2,
    "repeatability_canonical_metrics_identical_required": True,
}
PLACEHOLDER_RE = re.compile(r"@@[A-Z0-9_]+@@")


class ContractError(ValueError):
    """Le contrat ne décrit pas le benchmark F25 fermé attendu."""


def load_contract(path: Path) -> dict[str, Any]:
    def reject_non_finite(value: str) -> None:
        raise ContractError(f"non_finite_json_constant:{value}")

    contract = json.loads(
        path.read_text(encoding="utf-8"), parse_constant=reject_non_finite
    )
    validate_contract(contract, path.parent)
    return contract


def validate_contract(contract: dict[str, Any], contract_dir: Path) -> None:
    errors: list[str] = []

    if contract.get("benchmark_id") != EXPECTED_BENCHMARK_ID:
        errors.append("unexpected_benchmark_id")
    if contract.get("milestone") != "F25":
        errors.append("milestone_must_be_f25")

    scope = contract.get("scope", {})
    if scope.get("kind") != "synthetic_tool_solver_verification":
        errors.append("scope_must_be_synthetic_tool_solver_verification")
    if scope.get("source_data") != "synthetic_only":
        errors.append("source_data_must_be_synthetic_only")
    if scope.get("geometry") != "parallel_plate_channel":
        errors.append("geometry_must_be_parallel_plate_channel")
    if scope.get("porsche_asset") is not None:
        errors.append("porsche_asset_must_be_null")
    if scope.get("engine_variant") is not None:
        errors.append("engine_variant_must_be_null")
    if scope.get("excluded_workflows") != EXPECTED_EXCLUDED_WORKFLOWS:
        errors.append("excluded_workflows_must_remain_locked")

    container = contract.get("container", {})
    if container.get("image") != EXPECTED_IMAGE:
        errors.append("container_digest_must_remain_pinned")
    if container.get("platform") != "linux/amd64":
        errors.append("container_platform_must_be_linux_amd64")
    if container.get("network") != "none":
        errors.append("container_network_must_be_none")
    if container.get("requested_command") != "simpleFoam":
        errors.append("requested_command_must_be_simpleFoam")
    if container.get("openfoam_major") != 13:
        errors.append("openfoam_major_must_be_13")
    expected_confinement = {
        "read_only_root_filesystem": True,
        "case_mount_scope": "single_case_read_write",
        "run_as_host_uid_gid": True,
        "home": "/tmp",
        "tmpfs": "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "pids_limit": 128,
        "capabilities_dropped": "ALL",
        "no_new_privileges": True,
    }
    if container.get("confinement") != expected_confinement:
        errors.append("container_confinement_must_remain_closed")

    physics = contract.get("physics", {})
    for key in (
        "channel_length_m",
        "channel_height_m",
        "channel_depth_m",
        "kinematic_viscosity_m2_s",
        "body_force_x_m_s2",
        "density_reference_kg_m3",
    ):
        value = physics.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value <= 0
        ):
            errors.append(f"positive_physics_value_required:{key}")

    meshes = contract.get("meshes", [])
    actual_meshes = tuple((mesh.get("id"), mesh.get("cells_y")) for mesh in meshes)
    if actual_meshes != EXPECTED_MESHES:
        errors.append("meshes_must_be_coarse_8_medium_16_fine_32")
    for mesh in meshes:
        if mesh.get("cells_x") != 1 or mesh.get("cells_z") != 1:
            errors.append(f"single_periodic_column_required:{mesh.get('id')}")

    if contract.get("repetitions") != 2:
        errors.append("exactly_two_repetitions_required")

    acceptance = contract.get("acceptance", {})
    if set(acceptance) != set(EXPECTED_ACCEPTANCE):
        errors.append("acceptance_keys_must_remain_locked")
    for key, expected in EXPECTED_ACCEPTANCE.items():
        actual = acceptance.get(key)
        if isinstance(expected, bool):
            valid = actual is expected
        else:
            valid = (
                not isinstance(actual, bool)
                and isinstance(actual, (int, float))
                and math.isfinite(float(actual))
                and float(actual) == float(expected)
            )
        if not valid:
            errors.append(f"acceptance_value_must_remain_locked:{key}")
    if (
        isinstance(acceptance.get("observed_order_min"), (int, float))
        and isinstance(acceptance.get("observed_order_max"), (int, float))
        and not isinstance(acceptance.get("observed_order_min"), bool)
        and not isinstance(acceptance.get("observed_order_max"), bool)
        and acceptance["observed_order_min"] > acceptance["observed_order_max"]
    ):
        errors.append("observed_order_bounds_inverted")

    gates = contract.get("gates", {})
    required_closed_gates = {
        "f13_case_promotion_authorized",
        "physicsnemo_sample_authorized",
        "engine_simulation_claim_authorized",
        "engine_design_lock_authorized",
        "fabrication_authorized",
        "vehicle_use_authorized",
    }
    for gate in sorted(required_closed_gates):
        if gates.get(gate) is not False:
            errors.append(f"gate_must_remain_closed:{gate}")

    decks = contract.get("decks", {})
    if decks.get("root") != "decks":
        errors.append("deck_root_must_be_decks")
    if decks.get("files") != EXPECTED_DECK_FILES:
        errors.append("deck_files_must_remain_locked")
    resolved_contract_dir = contract_dir.resolve()
    deck_root = contract_dir / "decks"
    resolved_deck_root: Path | None = None
    try:
        resolved_deck_root = deck_root.resolve(strict=True)
        if deck_root.is_symlink():
            errors.append("deck_root_symlink_forbidden")
        if not resolved_deck_root.is_relative_to(resolved_contract_dir):
            errors.append("resolved_deck_root_outside_contract")
        if resolved_deck_root != resolved_contract_dir / "decks":
            errors.append("resolved_deck_root_mismatch")
        if not stat.S_ISDIR(deck_root.lstat().st_mode):
            errors.append("deck_root_not_directory")
    except (FileNotFoundError, OSError):
        errors.append("deck_root_unresolvable")
    for relative in decks.get("files", []):
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append(f"unsafe_deck_path:{relative}")
            continue
        deck_path = deck_root / relative
        try:
            resolved_deck = deck_path.resolve(strict=True)
            current = deck_root
            for part in Path(relative).parts:
                current = current / part
                if current.is_symlink():
                    errors.append(f"deck_symlink_forbidden:{relative}")
                    break
            if resolved_deck_root is None or not resolved_deck.is_relative_to(
                resolved_deck_root
            ):
                errors.append(f"resolved_deck_outside_root:{relative}")
            if not stat.S_ISREG(deck_path.lstat().st_mode):
                errors.append(f"deck_not_regular_file:{relative}")
        except (FileNotFoundError, OSError):
            errors.append(f"missing_deck:{relative}")

    if errors:
        raise ContractError(";".join(errors))


def format_scalar(value: float | int) -> str:
    return format(float(value), ".17g")


def render_deck(text: str, replacements: dict[str, str], relative: str) -> str:
    rendered = text
    for token, value in replacements.items():
        rendered = rendered.replace(f"@@{token}@@", value)
    unresolved = sorted(set(PLACEHOLDER_RE.findall(rendered)))
    if unresolved:
        raise ContractError(
            f"unresolved_placeholders:{relative}:{','.join(unresolved)}"
        )
    return rendered


def generate_cases(contract_path: Path, output_dir: Path) -> list[Path]:
    contract_path = contract_path.resolve()
    output_dir = output_dir.resolve()
    contract = load_contract(contract_path)
    if output_dir.exists():
        raise FileExistsError(f"output_already_exists:{output_dir}")

    decks = contract["decks"]
    deck_root = contract_path.parent / decks["root"]
    physics = contract["physics"]
    generated: list[Path] = []

    output_dir.mkdir(parents=True)
    for mesh in contract["meshes"]:
        case_dir = output_dir / mesh["id"]
        replacements = {
            "CHANNEL_LENGTH": format_scalar(physics["channel_length_m"]),
            "HALF_HEIGHT": format_scalar(physics["channel_height_m"] / 2.0),
            "CHANNEL_DEPTH": format_scalar(physics["channel_depth_m"]),
            "KINEMATIC_VISCOSITY": format_scalar(
                physics["kinematic_viscosity_m2_s"]
            ),
            "BODY_FORCE_X": format_scalar(physics["body_force_x_m_s2"]),
            "CELLS_X": str(mesh["cells_x"]),
            "CELLS_Y": str(mesh["cells_y"]),
            "CELLS_Z": str(mesh["cells_z"]),
        }
        for relative in decks["files"]:
            source = deck_root / relative
            destination = case_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                render_deck(source.read_text(encoding="utf-8"), replacements, relative),
                encoding="utf-8",
            )

        manifest = {
            "schema_version": "1.0",
            "benchmark_id": contract["benchmark_id"],
            "case_id": mesh["id"],
            "mesh": mesh,
            "synthetic_physics": physics,
            "container_image": contract["container"]["image"],
            "gates": contract["gates"],
        }
        (case_dir / "case-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        generated.append(case_dir)

    shutil.copy2(contract_path, output_dir / "benchmark-contract-f25.json")
    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated = generate_cases(args.contract, args.output)
    print(
        json.dumps(
            {
                "status": "generated",
                "case_count": len(generated),
                "case_ids": [path.name for path in generated],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
