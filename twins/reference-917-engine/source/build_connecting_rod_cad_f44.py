#!/usr/bin/env python3
"""Génère la bielle détaillée F44, exclusivement comme étude visuelle.

Le chemin de validation et ``--describe-only`` ne nécessitent aucune dépendance
CAO. build123d/OCCT n'est importé que pour la génération STEP/STL explicite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from validate_connecting_rod_cad_f44 import pair_topology_audit, validate  # noqa: E402


CAD_RUNTIME_IMAGE_ENV = "F44_CAD_RUNTIME_IMAGE_REF"
CAD_RUNTIME_IMAGE_REPOSITORY = "ghcr.io/cluster2600/3dprinting993-cad-author-f28"
CAD_RUNTIME_IMAGE_DIGEST = "sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
SEMANTIC_COMPONENT_COUNTS = {
    "connecting_rod_body": 1,
    "connecting_rod_cap": 1,
    "rod_bolt": 2,
    "big_end_half_bearing": 2,
    "small_end_bushing": 1,
}
DISPLAY_MIN_RADIAL_LIGAMENT_MM = 1.0
BOOLEAN_VOLUME_TOLERANCE_MM3 = 1.0e-6
INTERFERENCE_VOLUME_TOLERANCE_MM3 = 1.0e-9
SPOTFACE_LOCATION_TOLERANCE_MM = 1.0e-6
CLEAN_EXPORT_VOLUME_RELATIVE_TOLERANCE = 1.0e-9
CLEAN_EXPORT_BOUNDS_TOLERANCE_MM = 1.0e-6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(payload, dict), "contract_must_be_a_json_object")
    return payload


def parameter(contract: dict[str, Any], name: str) -> float:
    record = contract["parameter_register"][name]
    value = record["value"]
    require(record["classification"] == "design_hypothesis", f"parameter_not_design_hypothesis:{name}")
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"numeric_parameter_required:{name}")
    require(math.isfinite(float(value)), f"finite_parameter_required:{name}")
    return float(value)


def describe(contract: dict[str, Any]) -> dict[str, Any]:
    """Retourne le manifeste sémantique testable sans runtime CAO."""

    audit = pair_topology_audit(contract["parameter_register"])
    require(audit["deficit_mm"] > 0.0, "pair_topology_must_remain_blocked")
    require(contract["scope"]["paired_rod_assembly_allowed"] is False, "paired_rod_export_forbidden")
    return {
        "schema_version": "1.0.0",
        "phase": "F44",
        "asset_id": contract["asset_id"],
        "status": "display_only_single_connecting_rod_specification_pair_topology_blocked",
        "metadata": {
            "display_only": True,
            "engineering_study_only": True,
            "physical_joint_enabled": False,
            "physics_enabled": False,
            "simulation_result": False,
            "manufacturing_geometry": False,
            "power_evidence": False,
        },
        "future_occurrence_count": 12,
        "semantic_component_counts": dict(SEMANTIC_COMPONENT_COUNTS),
        "subtractive_feature_counts": {
            "rod_bolt_through_hole": 2,
            "internal_oil_channel": 1,
        },
        "datum_feature_counts": {"cap_joint_plane": 1},
        "pair_topology_audit": audit,
        "fastener_design_audit": fastener_design_audit(contract),
        "split_gap_audit": split_gap_audit(contract),
        "paired_rod_assembly_exported": False,
        "release_gates": contract["release_gates"],
    }


def split_gap_audit(contract: dict[str, Any]) -> dict[str, Any]:
    """Interdit un écart graphique qui pourrait suggérer un crush implicite."""

    cap_gap = parameter(contract, "cap_joint_visual_gap_mm")
    bearing_gap = parameter(contract, "bearing_split_visual_gap_mm")
    gap_delta = abs(bearing_gap - cap_gap)
    require(gap_delta == 0.0, "bearing_split_visual_gap_must_equal_cap_joint_visual_gap")
    return {
        "status": "display_only_split_gaps_exactly_aligned",
        "cap_joint_visual_gap_mm": cap_gap,
        "bearing_split_visual_gap_mm": bearing_gap,
        "bearing_cap_split_gap_delta_mm": gap_delta,
        "bearing_crush_evidence": False,
    }


def fastener_design_audit(contract: dict[str, Any]) -> dict[str, Any]:
    """Vérifie les dégagements analytiques de la fixation display-only.

    Ces relations empêchent les perçages de déboucher dans le logement du
    coussinet et dimensionnent des oreilles avec une portée plane autour de
    chaque tête. Elles ne constituent ni un calcul de serrage ni une cote de
    fabrication.
    """

    bearing_inner = (
        parameter(contract, "crankpin_nominal_diameter_mm") / 2.0
        + parameter(contract, "big_end_bearing_running_clearance_radial_mm")
    )
    bearing_outer = bearing_inner + parameter(contract, "big_end_bearing_shell_thickness_mm")
    housing_radius = bearing_outer + parameter(contract, "bearing_housing_visual_clearance_radial_mm")
    hole_radius = parameter(contract, "rod_bolt_clearance_diameter_mm") / 2.0
    shank_radius = parameter(contract, "rod_bolt_shank_diameter_mm") / 2.0
    head_radius = parameter(contract, "rod_bolt_head_diameter_mm") / 2.0
    head_height = parameter(contract, "rod_bolt_head_height_mm")
    bolt_offset = parameter(contract, "rod_bolt_axis_offset_z_mm")
    seat_half_span = parameter(contract, "rod_bolt_length_mm") / 2.0
    boss_margin = parameter(contract, "rod_bolt_boss_radial_margin_mm")
    boss_radius = head_radius + boss_margin
    seat_clearance = parameter(contract, "rod_bolt_seat_radial_clearance_mm")
    spotface_radius = head_radius + seat_clearance
    spotface_depth = parameter(contract, "rod_bolt_spotface_depth_mm")
    boss_half_span = seat_half_span + spotface_depth
    radial_ligament = bolt_offset - hole_radius - housing_radius
    hole_to_boss_wall = boss_radius - hole_radius
    head_to_boss_margin = boss_radius - head_radius
    shank_to_hole_clearance = hole_radius - shank_radius

    require(
        radial_ligament >= DISPLAY_MIN_RADIAL_LIGAMENT_MM,
        "rod_bolt_hole_breaches_big_end_housing_ligament",
    )
    require(hole_to_boss_wall > 0.0, "rod_bolt_hole_exceeds_boss_radius")
    require(head_to_boss_margin > 0.0, "rod_bolt_head_exceeds_boss_radius")
    require(spotface_radius < boss_radius, "rod_bolt_spotface_exceeds_boss_radius")
    require(spotface_depth > 0.0, "rod_bolt_spotface_depth_must_be_positive")
    require(shank_to_hole_clearance > 0.0, "rod_bolt_shank_has_no_visual_clearance")
    require(seat_half_span > head_height, "rod_bolt_seat_span_too_short")
    return {
        "status": "display_only_analytic_fastener_clearances_passed",
        "big_end_housing_radius_mm": round(housing_radius, 6),
        "bolt_hole_radius_mm": round(hole_radius, 6),
        "bolt_axis_offset_z_mm": round(bolt_offset, 6),
        "minimum_radial_ligament_to_housing_mm": round(radial_ligament, 6),
        "required_minimum_radial_ligament_mm": DISPLAY_MIN_RADIAL_LIGAMENT_MM,
        "boss_radial_margin_mm": round(boss_margin, 6),
        "boss_radius_mm": round(boss_radius, 6),
        "seat_radial_clearance_mm": round(seat_clearance, 6),
        "spotface_radius_mm": round(spotface_radius, 6),
        "spotface_depth_mm": round(spotface_depth, 6),
        "seat_half_span_y_mm": round(seat_half_span, 6),
        "boss_half_span_y_mm": round(boss_half_span, 6),
        "hole_to_boss_wall_mm": round(hole_to_boss_wall, 6),
        "head_to_boss_radial_margin_mm": round(head_to_boss_margin, 6),
        "shank_to_hole_radial_clearance_mm": round(shank_to_hole_clearance, 6),
        "head_inner_face_to_seat_gap_mm": 0.0,
        "classification": "design_hypothesis",
        "physical_preload_evidence": False,
    }


def cad_runtime_provenance() -> dict[str, str]:
    image_ref = os.environ.get(CAD_RUNTIME_IMAGE_ENV, "")
    expected = f"{CAD_RUNTIME_IMAGE_REPOSITORY}@{CAD_RUNTIME_IMAGE_DIGEST}"
    require(image_ref == expected, f"immutable_cad_runtime_image_required:{CAD_RUNTIME_IMAGE_ENV}")
    require(re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", image_ref) is not None, "invalid_cad_runtime_image")
    return {"image_ref": image_ref, "digest": CAD_RUNTIME_IMAGE_DIGEST}


def source_provenance(project_root: Path, contract_path: Path) -> dict[str, Any]:
    """Lie les dérivés aux sources exactes; le commit reste nul sans métadonnées Git."""

    root = project_root.resolve()
    candidates = {
        "contract": contract_path.resolve(),
        "builder": Path(__file__).resolve(),
        "validator": SOURCE_DIR / "validate_connecting_rod_cad_f44.py",
        "smoke": SOURCE_DIR / "smoke_connecting_rod_cad_f44.py",
    }
    files: list[dict[str, str]] = []
    combined = hashlib.sha256()
    for role, candidate in candidates.items():
        resolved = candidate.resolve(strict=True)
        require(resolved.is_file() and not candidate.is_symlink(), f"invalid_source_provenance_file:{role}")
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"source_provenance_outside_project:{role}") from exc
        digest = sha256(resolved)
        files.append({"role": role, "path": str(relative), "sha256": digest})
        combined.update(role.encode("utf-8"))
        combined.update(b"\0")
        combined.update(str(relative).encode("utf-8"))
        combined.update(b"\0")
        combined.update(digest.encode("ascii"))
        combined.update(b"\n")

    commit: str | None = None
    source_tree_clean: bool | None = None
    git_status = "unavailable_in_cad_container"
    if (root / ".git").exists():
        try:
            revision = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            require(re.fullmatch(r"[0-9a-f]{40}", revision) is not None, "invalid_git_commit_provenance")
            commit = revision
            relative_paths = [record["path"] for record in files]
            status = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain", "--", *relative_paths],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout
            source_tree_clean = not bool(status.strip())
            git_status = "available"
        except (OSError, subprocess.SubprocessError, RuntimeError):
            commit = None
            source_tree_clean = None
            git_status = "unavailable_or_invalid"
    return {
        "files": files,
        "combined_source_sha256": combined.hexdigest(),
        "git_commit": commit,
        "git_source_tree_clean": source_tree_clean,
        "git_status": git_status,
    }


def cylinder_x(radius: float, length: float, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(x, y, z) * Rot(0.0, 90.0, 0.0) * Cylinder(
        radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )


def cylinder_y(radius: float, length: float, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(x, y, z) * Rot(90.0, 0.0, 0.0) * Cylinder(
        radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )


def tube_x(
    outer_radius: float,
    inner_radius: float,
    length: float,
    *,
    boolean_overshoot: float,
    y: float = 0.0,
) -> Any:
    require(outer_radius > inner_radius > 0.0, "invalid_tube_radii")
    return cylinder_x(outer_radius, length, y=y) - cylinder_x(
        inner_radius, length + 2.0 * boolean_overshoot, y=y
    )


def split_half(shape: Any, contract: dict[str, Any], *, upper: bool, gap_name: str) -> Any:
    from build123d import Align, Box, Pos

    center_distance = parameter(contract, "rod_center_distance_mm")
    big_outer = parameter(contract, "big_end_outer_diameter_mm")
    small_outer = parameter(contract, "small_end_outer_diameter_mm")
    width = parameter(contract, "rod_width_mm")
    overshoot = parameter(contract, "boolean_overshoot_mm")
    gap = parameter(contract, gap_name)
    extent_y = center_distance + 2.0 * big_outer
    extent_z = big_outer + small_outer + 2.0 * overshoot
    sign = 1.0 if upper else -1.0
    cutter = Pos(0.0, sign * (gap / 2.0 + extent_y / 2.0), 0.0) * Box(
        width + 2.0 * overshoot,
        extent_y,
        extent_z,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    return shape & cutter


def oil_channel_tool(contract: dict[str, Any]) -> Any:
    big_inner = (
        parameter(contract, "crankpin_nominal_diameter_mm") / 2.0
        + parameter(contract, "big_end_bearing_running_clearance_radial_mm")
    )
    bearing_outer = big_inner + parameter(contract, "big_end_bearing_shell_thickness_mm")
    end = parameter(contract, "rod_center_distance_mm")
    overlap = parameter(contract, "oil_channel_boolean_overlap_mm")
    # Le canal de démonstration part au-delà du rayon extérieur du coussinet
    # inférieur. Il traverse donc réellement les deux demi-coussinets et le
    # volume d'alésage de tête avant de rejoindre le volume d'alésage de pied.
    start = -bearing_outer - overlap
    length = end - start + overlap
    return cylinder_y(
        parameter(contract, "oil_channel_visual_diameter_mm") / 2.0,
        length,
        y=start + length / 2.0,
    )


def intersection_volume_mm3(first: Any, second: Any) -> float:
    common = first & second
    if common is None:
        return 0.0
    return float(sum(solid.volume for solid in common.solids()))


def build_shapes_with_audit(contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Construit les composants et audite réellement les fixations en BRep."""

    from build123d import Align, Box, Compound, Pos

    center_distance = parameter(contract, "rod_center_distance_mm")
    width = parameter(contract, "rod_width_mm")
    big_outer = parameter(contract, "big_end_outer_diameter_mm")
    small_outer = parameter(contract, "small_end_outer_diameter_mm")
    beam_height = parameter(contract, "beam_height_mm")
    overlap = parameter(contract, "beam_end_overlap_mm")
    overshoot = parameter(contract, "boolean_overshoot_mm")

    beam_length = center_distance - big_outer / 2.0 - small_outer / 2.0 + 2.0 * overlap
    beam_center_y = (big_outer / 2.0 - overlap + center_distance - small_outer / 2.0 + overlap) / 2.0
    outer = cylinder_x(big_outer / 2.0, width)
    outer = outer + cylinder_x(small_outer / 2.0, width, y=center_distance)
    outer = outer + Pos(0.0, beam_center_y, 0.0) * Box(
        width, beam_length, beam_height, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )

    bearing_inner = (
        parameter(contract, "crankpin_nominal_diameter_mm") / 2.0
        + parameter(contract, "big_end_bearing_running_clearance_radial_mm")
    )
    bearing_outer = bearing_inner + parameter(contract, "big_end_bearing_shell_thickness_mm")
    big_housing_radius = bearing_outer + parameter(contract, "bearing_housing_visual_clearance_radial_mm")
    bushing_inner = (
        parameter(contract, "small_end_nominal_bore_mm") / 2.0
        + parameter(contract, "small_end_bushing_inner_clearance_radial_mm")
    )
    bushing_outer = bushing_inner + parameter(contract, "small_end_bushing_thickness_mm")
    small_housing_radius = bushing_outer + parameter(contract, "small_end_housing_visual_clearance_radial_mm")
    fastener_design = fastener_design_audit(contract)
    split_design = split_gap_audit(contract)
    bolt_offset = parameter(contract, "rod_bolt_axis_offset_z_mm")
    boss_radius = float(fastener_design["boss_radius_mm"])
    spotface_radius = float(fastener_design["spotface_radius_mm"])
    spotface_depth = float(fastener_design["spotface_depth_mm"])
    seat_half_span = float(fastener_design["seat_half_span_y_mm"])
    boss_half_span = float(fastener_design["boss_half_span_y_mm"])
    boss_length = 2.0 * boss_half_span
    for sign in (-1.0, 1.0):
        outer = outer + cylinder_y(boss_radius, boss_length, z=sign * bolt_offset)
    outer = outer - cylinder_x(big_housing_radius, width + 2.0 * overshoot)
    outer = outer - cylinder_x(small_housing_radius, width + 2.0 * overshoot, y=center_distance)

    outer_before_spotfaces = outer
    spotface_length = spotface_depth + overshoot
    spotface_tools: list[tuple[str, float, Any, Any]] = []
    for z_sign in (-1.0, 1.0):
        for y_sign in (-1.0, 1.0):
            spotface_center_y = y_sign * (seat_half_span + spotface_length / 2.0)
            spotface = cylinder_y(
                spotface_radius,
                spotface_length,
                y=spotface_center_y,
                z=z_sign * bolt_offset,
            )
            spotface_id = (
                f"rod_bolt_{1 if z_sign < 0.0 else 2:02d}_"
                f"{'negative' if y_sign < 0.0 else 'positive'}_y_spotface"
            )
            nominal_spotface = cylinder_y(
                spotface_radius,
                spotface_depth,
                y=y_sign * (seat_half_span + spotface_depth / 2.0),
                z=z_sign * bolt_offset,
            )
            spotface_tools.append((spotface_id, y_sign, spotface, nominal_spotface))
            outer = outer - spotface
    outer_after_spotfaces = outer

    outer_before_bolt_holes = outer
    hole_length = max(big_outer + 2.0 * overshoot, boss_length + 2.0 * overshoot)
    hole_radius = parameter(contract, "rod_bolt_clearance_diameter_mm") / 2.0
    bolt_holes = [cylinder_y(hole_radius, hole_length, z=sign * bolt_offset) for sign in (-1.0, 1.0)]
    for hole in bolt_holes:
        outer = outer - hole
    outer_before_oil_channel = outer
    channel = oil_channel_tool(contract)
    outer = outer - channel

    body = split_half(outer, contract, upper=True, gap_name="cap_joint_visual_gap_mm")
    cap = split_half(outer, contract, upper=False, gap_name="cap_joint_visual_gap_mm")
    body.label = "F44 connecting rod body display-only"
    cap.label = "F44 connecting rod cap display-only"

    bolt_length = parameter(contract, "rod_bolt_length_mm")
    bolt_radius = parameter(contract, "rod_bolt_shank_diameter_mm") / 2.0
    head_radius = parameter(contract, "rod_bolt_head_diameter_mm") / 2.0
    head_height = parameter(contract, "rod_bolt_head_height_mm")
    bolts: list[Any] = []
    for index, sign in enumerate((-1.0, 1.0), start=1):
        z = sign * bolt_offset
        shank = cylinder_y(bolt_radius, bolt_length, z=z)
        head = cylinder_y(head_radius, head_height, y=bolt_length / 2.0 + head_height / 2.0, z=z)
        nut = cylinder_y(head_radius, head_height, y=-bolt_length / 2.0 - head_height / 2.0, z=z)
        bolt = Compound(children=[shank, head, nut], label=f"F44 rod bolt {index:02d} display-only")
        bolts.append(bolt)

    bearing_before_channel = tube_x(
        bearing_outer,
        bearing_inner,
        parameter(contract, "big_end_bearing_axial_width_mm"),
        boolean_overshoot=overshoot,
    )
    bearing = bearing_before_channel - channel
    bearing_upper = split_half(bearing, contract, upper=True, gap_name="bearing_split_visual_gap_mm")
    bearing_lower = split_half(bearing, contract, upper=False, gap_name="bearing_split_visual_gap_mm")
    bearing_upper.label = "F44 upper half bearing display-only"
    bearing_lower.label = "F44 lower half bearing display-only"

    bushing_before_channel = tube_x(
        bushing_outer,
        bushing_inner,
        parameter(contract, "small_end_bushing_axial_width_mm"),
        boolean_overshoot=overshoot,
        y=center_distance,
    )
    bushing = bushing_before_channel - channel
    bushing.label = "F44 small end bushing display-only"
    channel.label = "F44 oil channel subtractive reference display-only"
    assembly = Compound(
        children=[body, cap, *bolts, bearing_upper, bearing_lower, bushing],
        label="F44 single connecting rod display-only assembly",
    )
    shapes = {
        "connecting_rod_body": body,
        "connecting_rod_cap": cap,
        "rod_bolt_01": bolts[0],
        "rod_bolt_02": bolts[1],
        "big_end_half_bearing_upper": bearing_upper,
        "big_end_half_bearing_lower": bearing_lower,
        "small_end_bushing": bushing,
        "oil_channel_reference": channel,
        "connecting_rod_assembly": assembly,
    }
    pre_hole_body = split_half(
        outer_before_bolt_holes,
        contract,
        upper=True,
        gap_name="cap_joint_visual_gap_mm",
    )
    pre_hole_cap = split_half(
        outer_before_bolt_holes,
        contract,
        upper=False,
        gap_name="cap_joint_visual_gap_mm",
    )
    pre_oil_channel_body = split_half(
        outer_before_oil_channel,
        contract,
        upper=True,
        gap_name="cap_joint_visual_gap_mm",
    )
    spotface_records: list[dict[str, Any]] = []
    for spotface_id, y_sign, _spotface, nominal_spotface in spotface_tools:
        cut_shape = outer_before_spotfaces & nominal_spotface
        cut_volume = float(sum(solid.volume for solid in cut_shape.solids()))
        require(cut_volume > BOOLEAN_VOLUME_TOLERANCE_MM3, f"spotface_misses_boss:{spotface_id}")
        cut_bounds = cut_shape.bounding_box()
        observed_min_y = float(cut_bounds.min.Y)
        observed_max_y = float(cut_bounds.max.Y)
        if y_sign > 0.0:
            expected_min_y = seat_half_span
            expected_max_y = boss_half_span
        else:
            expected_min_y = -boss_half_span
            expected_max_y = -seat_half_span
        depth_delta = max(
            abs(observed_min_y - expected_min_y),
            abs(observed_max_y - expected_max_y),
        )
        post_residual = intersection_volume_mm3(outer_after_spotfaces, nominal_spotface)
        require(
            depth_delta <= SPOTFACE_LOCATION_TOLERANCE_MM,
            f"spotface_depth_or_location_drift:{spotface_id}",
        )
        require(
            post_residual <= BOOLEAN_VOLUME_TOLERANCE_MM3,
            f"spotface_subtraction_residual:{spotface_id}",
        )
        spotface_records.append(
            {
                "id": spotface_id,
                "pre_subtraction_cut_volume_mm3": round(cut_volume, 6),
                "expected_min_y_mm": round(expected_min_y, 6),
                "expected_max_y_mm": round(expected_max_y, 6),
                "observed_min_y_mm": round(observed_min_y, 6),
                "observed_max_y_mm": round(observed_max_y, 6),
                "depth_or_location_delta_mm": round(depth_delta, 9),
                "post_subtraction_residual_mm3": round(post_residual, 9),
            }
        )

    bearing_upper_before_channel = split_half(
        bearing_before_channel,
        contract,
        upper=True,
        gap_name="bearing_split_visual_gap_mm",
    )
    bearing_lower_before_channel = split_half(
        bearing_before_channel,
        contract,
        upper=False,
        gap_name="bearing_split_visual_gap_mm",
    )
    oil_channel_body_cut = intersection_volume_mm3(pre_oil_channel_body, channel)
    oil_channel_bearing_upper_cut = intersection_volume_mm3(bearing_upper_before_channel, channel)
    oil_channel_bearing_lower_cut = intersection_volume_mm3(bearing_lower_before_channel, channel)
    oil_channel_bushing_cut = intersection_volume_mm3(bushing_before_channel, channel)
    big_end_bore_reference = cylinder_x(bearing_inner, width + 2.0 * overshoot)
    small_end_bore_reference = cylinder_x(
        bushing_inner,
        width + 2.0 * overshoot,
        y=center_distance,
    )
    oil_channel_big_end_opening = intersection_volume_mm3(big_end_bore_reference, channel)
    oil_channel_small_end_opening = intersection_volume_mm3(small_end_bore_reference, channel)
    channel_radius = parameter(contract, "oil_channel_visual_diameter_mm") / 2.0
    channel_exit_overlap = parameter(contract, "oil_channel_boolean_overlap_mm")
    expected_big_end_outer_exit_y = -bearing_outer - channel_exit_overlap
    observed_big_end_outer_exit_y = float(channel.bounding_box().min.Y)
    oil_channel_big_end_outer_exit_depth_delta = abs(
        observed_big_end_outer_exit_y - expected_big_end_outer_exit_y
    )
    big_end_outer_exit_probe = cylinder_y(
        channel_radius,
        channel_exit_overlap,
        y=-bearing_outer - channel_exit_overlap / 2.0,
    )
    oil_channel_big_end_outer_exit_probe = intersection_volume_mm3(
        big_end_outer_exit_probe,
        channel,
    )
    oil_channel_component_count = len(channel.solids())
    oil_channel_post_residuals = {
        "connecting_rod_body": intersection_volume_mm3(body, channel),
        "big_end_half_bearing_upper": intersection_volume_mm3(bearing_upper, channel),
        "big_end_half_bearing_lower": intersection_volume_mm3(bearing_lower, channel),
        "small_end_bushing": intersection_volume_mm3(bushing, channel),
    }
    oil_channel_post_residual_maximum = max(oil_channel_post_residuals.values())
    oil_channel_pre_subtraction_intersections = {
        "connecting_rod_body": oil_channel_body_cut,
        "big_end_half_bearing_upper": oil_channel_bearing_upper_cut,
        "big_end_half_bearing_lower": oil_channel_bearing_lower_cut,
        "small_end_bushing": oil_channel_bushing_cut,
    }
    for feature_id, cut_volume in oil_channel_pre_subtraction_intersections.items():
        require(
            cut_volume > BOOLEAN_VOLUME_TOLERANCE_MM3,
            f"oil_channel_misses_pre_subtraction_feature:{feature_id}",
        )
    require(
        oil_channel_big_end_opening > BOOLEAN_VOLUME_TOLERANCE_MM3,
        "oil_channel_misses_big_end_bore",
    )
    require(
        oil_channel_small_end_opening > BOOLEAN_VOLUME_TOLERANCE_MM3,
        "oil_channel_misses_small_end_bore",
    )
    require(
        oil_channel_big_end_outer_exit_probe > BOOLEAN_VOLUME_TOLERANCE_MM3,
        "oil_channel_does_not_exit_beyond_big_end_bearing_outer_radius",
    )
    require(
        oil_channel_big_end_outer_exit_depth_delta <= SPOTFACE_LOCATION_TOLERANCE_MM,
        "oil_channel_big_end_outer_exit_depth_drift",
    )
    require(oil_channel_component_count == 1, "oil_channel_reference_must_be_single_connected_solid")
    require(
        oil_channel_post_residual_maximum <= BOOLEAN_VOLUME_TOLERANCE_MM3,
        "oil_channel_subtraction_residual",
    )
    fastener_records: list[dict[str, Any]] = []
    total_unintended_interference = 0.0
    for index, (hole, bolt) in enumerate(zip(bolt_holes, bolts, strict=True), start=1):
        pre_body_cut = intersection_volume_mm3(pre_hole_body, hole)
        pre_cap_cut = intersection_volume_mm3(pre_hole_cap, hole)
        post_body_residual = intersection_volume_mm3(body, hole)
        post_cap_residual = intersection_volume_mm3(cap, hole)
        bolt_body_interference = intersection_volume_mm3(bolt, body)
        bolt_cap_interference = intersection_volume_mm3(bolt, cap)
        total_unintended_interference += bolt_body_interference + bolt_cap_interference
        require(pre_body_cut > BOOLEAN_VOLUME_TOLERANCE_MM3, f"rod_bolt_hole_misses_body:{index}")
        require(pre_cap_cut > BOOLEAN_VOLUME_TOLERANCE_MM3, f"rod_bolt_hole_misses_cap:{index}")
        require(
            post_body_residual <= BOOLEAN_VOLUME_TOLERANCE_MM3,
            f"rod_bolt_hole_residual_in_body:{index}",
        )
        require(
            post_cap_residual <= BOOLEAN_VOLUME_TOLERANCE_MM3,
            f"rod_bolt_hole_residual_in_cap:{index}",
        )
        require(
            bolt_body_interference <= INTERFERENCE_VOLUME_TOLERANCE_MM3,
            f"rod_bolt_intersects_body:{index}",
        )
        require(
            bolt_cap_interference <= INTERFERENCE_VOLUME_TOLERANCE_MM3,
            f"rod_bolt_intersects_cap:{index}",
        )
        fastener_records.append(
            {
                "id": f"rod_bolt_{index:02d}",
                "pre_subtraction_body_cut_volume_mm3": round(pre_body_cut, 6),
                "pre_subtraction_cap_cut_volume_mm3": round(pre_cap_cut, 6),
                "post_subtraction_body_residual_mm3": round(post_body_residual, 9),
                "post_subtraction_cap_residual_mm3": round(post_cap_residual, 9),
                "bolt_body_interference_volume_mm3": round(bolt_body_interference, 9),
                "bolt_cap_interference_volume_mm3": round(bolt_cap_interference, 9),
            }
        )
    require(len(body.solids()) == 1, "fastener_bosses_disconnect_connecting_rod_body")
    require(len(cap.solids()) == 1, "fastener_bosses_disconnect_connecting_rod_cap")
    geometry_checks = {
        "minimum_ligament_mm": float(fastener_design["minimum_radial_ligament_to_housing_mm"]),
        "bolt_hole_cutter_body_intersection_mm3": round(
            min(record["pre_subtraction_body_cut_volume_mm3"] for record in fastener_records),
            6,
        ),
        "bolt_hole_cutter_cap_intersection_mm3": round(
            min(record["pre_subtraction_cap_cut_volume_mm3"] for record in fastener_records),
            6,
        ),
        "spotface_cutter_minimum_intersection_mm3": round(
            min(record["pre_subtraction_cut_volume_mm3"] for record in spotface_records),
            6,
        ),
        "spotface_cutter_maximum_depth_delta_mm": round(
            max(record["depth_or_location_delta_mm"] for record in spotface_records),
            9,
        ),
        "spotface_post_subtraction_maximum_residual_mm3": round(
            max(record["post_subtraction_residual_mm3"] for record in spotface_records),
            9,
        ),
        "oil_channel_cutter_body_intersection_mm3": round(oil_channel_body_cut, 6),
        "oil_channel_cutter_bearing_upper_intersection_mm3": round(
            oil_channel_bearing_upper_cut,
            6,
        ),
        "oil_channel_cutter_bearing_lower_intersection_mm3": round(
            oil_channel_bearing_lower_cut,
            6,
        ),
        "oil_channel_cutter_bushing_intersection_mm3": round(oil_channel_bushing_cut, 6),
        "oil_channel_big_end_bore_opening_mm3": round(oil_channel_big_end_opening, 6),
        "oil_channel_small_end_bore_opening_mm3": round(oil_channel_small_end_opening, 6),
        "oil_channel_big_end_outer_exit_probe_mm3": round(
            oil_channel_big_end_outer_exit_probe,
            6,
        ),
        "oil_channel_big_end_outer_exit_depth_delta_mm": round(
            oil_channel_big_end_outer_exit_depth_delta,
            9,
        ),
        "oil_channel_connected_component_count": oil_channel_component_count,
        "oil_channel_post_subtraction_maximum_residual_mm3": round(
            oil_channel_post_residual_maximum,
            9,
        ),
        "bearing_cap_split_gap_delta_mm": round(
            float(split_design["bearing_cap_split_gap_delta_mm"]),
            9,
        ),
        "unintended_fastener_interference_mm3": round(total_unintended_interference, 12),
    }
    require(geometry_checks["minimum_ligament_mm"] > 0.0, "nonpositive_fastener_ligament")
    require(
        total_unintended_interference <= INTERFERENCE_VOLUME_TOLERANCE_MM3,
        "unintended_fastener_interference",
    )
    geometry_audit = {
        "status": "display_only_brep_fastener_spotface_and_oil_path_checks_passed",
        "boolean_volume_tolerance_mm3": BOOLEAN_VOLUME_TOLERANCE_MM3,
        "spotface_location_tolerance_mm": SPOTFACE_LOCATION_TOLERANCE_MM,
        "analytic": fastener_design,
        "fasteners": fastener_records,
        "spotfaces": spotface_records,
        "oil_channel": {
            "status": "single_connected_reference_intersects_both_bores_and_all_declared_parts",
            "pre_subtraction_intersection_volumes_mm3": {
                feature_id: round(volume, 6)
                for feature_id, volume in oil_channel_pre_subtraction_intersections.items()
            },
            "bore_opening_volumes_mm3": {
                "big_end": round(oil_channel_big_end_opening, 6),
                "small_end": round(oil_channel_small_end_opening, 6),
            },
            "big_end_bearing_outer_exit": {
                "expected_min_y_mm": round(expected_big_end_outer_exit_y, 6),
                "observed_min_y_mm": round(observed_big_end_outer_exit_y, 6),
                "depth_delta_mm": round(oil_channel_big_end_outer_exit_depth_delta, 9),
                "probe_intersection_volume_mm3": round(
                    oil_channel_big_end_outer_exit_probe,
                    6,
                ),
            },
            "connected_component_count": oil_channel_component_count,
            "post_subtraction_residual_volumes_mm3": {
                feature_id: round(volume, 9)
                for feature_id, volume in oil_channel_post_residuals.items()
            },
            "lubrication_performance_evidence": False,
        },
        "split_gap": split_design,
        "geometry_checks": geometry_checks,
        "body_solid_count": len(body.solids()),
        "cap_solid_count": len(cap.solids()),
        "bearing_housing_intrusion_allowed": False,
        "positive_shape_interference_allowed": False,
        "physical_fastener_validation": False,
    }
    return shapes, geometry_audit


def build_shapes(contract: dict[str, Any]) -> dict[str, Any]:
    """Compatibilité : retourne les formes sans perdre les audits fail-closed."""

    shapes, _ = build_shapes_with_audit(contract)
    return shapes


def _vector(value: Any) -> list[float]:
    return [round(float(value.X), 6), round(float(value.Y), 6), round(float(value.Z), 6)]


def shape_metrics(shape: Any) -> dict[str, Any]:
    solids = list(shape.solids())
    bounds = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solid_count": len(solids),
        "all_solids_positive_volume": bool(solids) and all(item.volume > 0.0 for item in solids),
        "volume_mm3": round(sum(item.volume for item in solids), 6),
        "bounds_min_mm": _vector(bounds.min),
        "bounds_max_mm": _vector(bounds.max),
    }


def clean_export_shape(shape: Any) -> Any:
    """Supprime l'historique booléen build123d avant transfert XCAF/STEP.

    Les intersections ``split_half`` produisent des ``Part`` valides mais leur
    historique topologique fait échouer STEPCAF sous OCCT 7.8. Le transfert du
    solide OCCT résultant (ou d'un composé plat de solides) conserve exactement
    la géométrie et rend l'export déterministe.
    """

    from build123d import Compound

    solids = [solid.clean() for solid in shape.solids()]
    require(solids, "export_shape_has_no_solids")
    label = str(getattr(shape, "label", "") or "F44 display-only geometry")
    if len(solids) == 1:
        exportable = solids[0]
        exportable.label = label
        return exportable
    return Compound(children=solids, label=label)


def canonicalize_step_header(path: Path) -> None:
    payload = path.read_text(encoding="utf-8")
    canonical, count = re.subn(
        r"(FILE_NAME\([^,]+,\s*')[^']+(')",
        r"\g<1>1970-01-01T00:00:00\g<2>",
        payload,
        count=1,
    )
    require(count == 1, f"step_header_timestamp_not_found:{path}")
    path.write_text(canonical, encoding="utf-8", newline="\n")


def export_shape(
    shape: Any,
    step_path: Path,
    stl_path: Path,
    *,
    linear_tolerance: float,
    angular_tolerance: float,
) -> dict[str, Any]:
    from build123d import export_step, export_stl, import_step

    step_path.parent.mkdir(parents=True, exist_ok=True)
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    authored = shape_metrics(shape)
    require(authored["valid"], f"authored_shape_invalid:{step_path.name}")
    require(authored["all_solids_positive_volume"], f"authored_shape_nonpositive_volume:{step_path.name}")

    exportable = clean_export_shape(shape)
    created = shape_metrics(exportable)
    require(created["valid"], f"cleaned_shape_invalid:{step_path.name}")
    require(created["all_solids_positive_volume"], f"cleaned_shape_nonpositive_volume:{step_path.name}")
    clean_volume_delta = abs(float(created["volume_mm3"]) - float(authored["volume_mm3"]))
    clean_volume_relative_delta = clean_volume_delta / max(float(authored["volume_mm3"]), 1.0)
    clean_bounds_delta = max(
        abs(float(created[key][axis]) - float(authored[key][axis]))
        for key in ("bounds_min_mm", "bounds_max_mm")
        for axis in range(3)
    )
    require(authored["solid_count"] == created["solid_count"], f"clean_export_solid_count_drift:{step_path.name}")
    require(
        clean_volume_relative_delta <= CLEAN_EXPORT_VOLUME_RELATIVE_TOLERANCE,
        f"clean_export_volume_drift:{step_path.name}",
    )
    require(
        clean_bounds_delta <= CLEAN_EXPORT_BOUNDS_TOLERANCE_MM,
        f"clean_export_bounds_drift:{step_path.name}",
    )

    scratch_step = step_path.with_name(f".{step_path.name}.precanonical-{os.getpid()}")
    require(not scratch_step.exists(), f"step_canonicalization_scratch_exists:{scratch_step.name}")
    try:
        export_step(exportable, scratch_step)
        canonical_shape = clean_export_shape(import_step(scratch_step))
    finally:
        scratch_step.unlink(missing_ok=True)
    canonical = shape_metrics(canonical_shape)
    require(canonical["valid"], f"canonical_shape_invalid:{step_path.name}")
    require(canonical["all_solids_positive_volume"], f"canonical_shape_nonpositive_volume:{step_path.name}")
    canonical_volume_delta = abs(float(canonical["volume_mm3"]) - float(created["volume_mm3"]))
    canonical_volume_relative_delta = canonical_volume_delta / max(float(created["volume_mm3"]), 1.0)
    canonical_bounds_delta = max(
        abs(float(canonical[key][axis]) - float(created[key][axis]))
        for key in ("bounds_min_mm", "bounds_max_mm")
        for axis in range(3)
    )
    require(created["solid_count"] == canonical["solid_count"], f"canonicalization_solid_count:{step_path.name}")
    require(canonical_volume_relative_delta <= 1.0e-6, f"canonicalization_volume_drift:{step_path.name}")
    require(canonical_bounds_delta <= 1.0e-5, f"canonicalization_bounds_drift:{step_path.name}")

    export_step(canonical_shape, step_path)
    canonicalize_step_header(step_path)
    export_stl(
        canonical_shape,
        stl_path,
        tolerance=linear_tolerance,
        angular_tolerance=angular_tolerance,
    )
    reopened = shape_metrics(import_step(step_path))
    require(reopened["valid"], f"step_roundtrip_invalid:{step_path.name}")
    require(reopened["solid_count"] == canonical["solid_count"], f"step_roundtrip_solid_count:{step_path.name}")
    volume_delta = abs(float(reopened["volume_mm3"]) - float(canonical["volume_mm3"]))
    volume_relative_delta = volume_delta / max(float(canonical["volume_mm3"]), 1.0)
    bounds_delta = max(
        abs(float(reopened[key][axis]) - float(canonical[key][axis]))
        for key in ("bounds_min_mm", "bounds_max_mm")
        for axis in range(3)
    )
    require(
        math.isclose(
            float(reopened["volume_mm3"]),
            float(canonical["volume_mm3"]),
            rel_tol=1.0e-8,
            abs_tol=1.0e-4,
        ),
        f"step_roundtrip_volume_drift:{step_path.name}",
    )
    require(bounds_delta <= 1.0e-6, f"step_roundtrip_bounds_drift:{step_path.name}")
    return {
        "step": str(Path("step") / step_path.name),
        "stl": str(Path("stl") / stl_path.name),
        "step_sha256": sha256(step_path),
        "stl_sha256": sha256(stl_path),
        "authored_metrics": authored,
        "created_metrics": created,
        "canonical_metrics": canonical,
        "roundtrip_metrics": reopened,
        "clean_export_audit": {
            "authored_to_created_volume_absolute_delta_mm3": round(clean_volume_delta, 9),
            "authored_to_created_volume_relative_delta": round(clean_volume_relative_delta, 12),
            "authored_to_created_maximum_bounds_delta_mm": round(clean_bounds_delta, 9),
            "maximum_volume_relative_delta": CLEAN_EXPORT_VOLUME_RELATIVE_TOLERANCE,
            "maximum_bounds_delta_mm_allowed": CLEAN_EXPORT_BOUNDS_TOLERANCE_MM,
        },
        "canonicalization_audit": {
            "created_to_canonical_volume_absolute_delta_mm3": round(canonical_volume_delta, 9),
            "created_to_canonical_volume_relative_delta": round(canonical_volume_relative_delta, 12),
            "created_to_canonical_maximum_bounds_delta_mm": round(canonical_bounds_delta, 9),
            "maximum_volume_relative_delta": 1.0e-6,
            "maximum_bounds_delta_mm_allowed": 1.0e-5,
        },
        "roundtrip_audit": {
            "volume_absolute_delta_mm3": round(volume_delta, 9),
            "volume_relative_delta": round(volume_relative_delta, 12),
            "maximum_bounds_delta_mm": round(bounds_delta, 9),
            "maximum_volume_relative_delta": 1.0e-8,
            "maximum_volume_absolute_delta_mm3": 1.0e-4,
            "maximum_bounds_delta_mm_allowed": 1.0e-6,
        },
    }


def generate(project_root: Path, contract_path: Path, contract: dict[str, Any], output: Path) -> Path:
    work_root = project_root / "work"
    require(not work_root.is_symlink(), f"work_root_symlink_not_allowed:{work_root}")
    require(output.parent.resolve() == work_root.resolve(), f"output_must_be_direct_child_of_work:{output}")
    require(not output.is_symlink(), f"output_symlink_not_allowed:{output}")
    require(not output.exists(), f"output_already_exists:{output}")
    require(output.name == "917-connecting-rod-cad-f44", "unsafe_output_directory_name")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    require(not temporary.exists(), f"temporary_output_already_exists:{temporary}")
    temporary.mkdir()
    try:
        runtime = cad_runtime_provenance()
        provenance = source_provenance(project_root, contract_path)
        shapes, fastener_geometry_audit = build_shapes_with_audit(contract)
        exports: dict[str, Any] = {}
        linear_tolerance = parameter(contract, "stl_linear_tolerance_mm")
        angular_tolerance = parameter(contract, "stl_angular_tolerance_rad")
        for name, shape in shapes.items():
            exports[name] = export_shape(
                shape,
                temporary / "step" / f"{name}.step",
                temporary / "stl" / f"{name}-display-only.stl",
                linear_tolerance=linear_tolerance,
                angular_tolerance=angular_tolerance,
            )
        report = describe(contract)
        report.update(
            {
                "status": "display_only_single_connecting_rod_geometry_built_pair_topology_blocked",
                "contract_path": str(contract_path.relative_to(project_root)),
                "contract_sha256": sha256(contract_path),
                "cad_runtime_provenance": runtime,
                "source_provenance": provenance,
                "exports": exports,
                "fastener_geometry_audit": fastener_geometry_audit,
                "geometry_checks": fastener_geometry_audit["geometry_checks"],
                "property_assignment_intent": "skip",
                "physics_scene_authored": False,
                "paired_rod_assembly_exported": False,
            }
        )
        (temporary / "geometry-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        temporary.rename(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output / "geometry-report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--describe-only", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    contract_path = args.contract or root / "twins/reference-917-engine/connecting-rod-cad-f44.json"
    errors = validate(root, contract_path)
    if errors:
        for error in errors:
            print(f"F44 connecting-rod build error: {error}", file=sys.stderr)
        return 1
    contract = load_contract(contract_path)
    if args.describe_only:
        print(json.dumps(describe(contract), indent=2))
        return 0
    output_argument = args.output or root / contract["output_policy"]["default_output"]
    output = output_argument.resolve()
    report = generate(root, contract_path.resolve(), contract, output)
    print(f"F44 connecting-rod display-only report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
