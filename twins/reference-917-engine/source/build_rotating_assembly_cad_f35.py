#!/usr/bin/env python3
"""Build the F35 rotating-group design study with build123d/OCCT.

The generated solids are an editable engineering hypothesis.  They deliberately
do not inherit the disconnected F1/F10 primitives and they are never presented
as measured 917 manufacturing geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any

from rotating_assembly_f35_math import (
    BANK_AXES,
    CRANK_AXIS,
    DESIGN_CRANKPIN_PHASES_DEG,
    assembly_sample,
    paired_rod_axial_layout_mm,
    paired_rod_axial_offset_mm,
)


CAD_RUNTIME_IMAGE_ENV = "F35_CAD_RUNTIME_IMAGE_REF"
CAD_RUNTIME_IMAGE_REPOSITORY = "ghcr.io/cluster2600/3dprinting993-cad-author-f28"
REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS = {
    "crankshaft_axis": 1,
    "main_journal_centres_01_to_08": 8,
    "crankpin_centres_01_to_06": 6,
    "rod_big_end_axis": 12,
    "rod_small_end_axis": 12,
    "piston_pin_axis": 12,
    "piston_crown_datum": 12,
    "piston_ring_groove_datums": 36,
}
EXPECTED_INTERFACE_FRAME_TOTAL = sum(REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS.values())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cad_runtime_provenance() -> dict[str, str]:
    """Capture l'image réellement passée à ``docker run`` par le Makefile.

    Le générateur n'a volontairement aucun digest par défaut : l'appelant doit
    injecter la même référence immuable que celle utilisée pour démarrer ce
    processus. Un lancement hors de cette frontière échoue au lieu d'attribuer
    silencieusement la provenance d'une autre image.
    """

    image_ref = os.environ.get(CAD_RUNTIME_IMAGE_ENV, "")
    match = re.fullmatch(
        rf"{re.escape(CAD_RUNTIME_IMAGE_REPOSITORY)}@sha256:([0-9a-f]{{64}})",
        image_ref,
    )
    require(match is not None, f"immutable_cad_runtime_image_required:{CAD_RUNTIME_IMAGE_ENV}")
    return {
        "image_ref": image_ref,
        "repository": CAD_RUNTIME_IMAGE_REPOSITORY,
        "digest": f"sha256:{match.group(1)}",
        "evidence": "docker_run_image_argument_exported_to_process_environment",
    }


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


def vector(value: Any) -> list[float]:
    return [round(float(value.X), 6), round(float(value.Y), 6), round(float(value.Z), 6)]


def shape_metrics(shape: Any) -> dict[str, Any]:
    solids = list(shape.solids())
    bounds = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "manifold": bool(shape.is_manifold),
        "solid_count": len(solids),
        "all_solids_positive_volume": bool(solids) and all(solid.volume > 0.0 for solid in solids),
        "face_count": len(shape.faces()),
        "edge_count": len(shape.edges()),
        "volume_mm3": round(sum(solid.volume for solid in solids), 6),
        "bounds_min_mm": vector(bounds.min),
        "bounds_max_mm": vector(bounds.max),
        "bounds_size_mm": vector(bounds.size),
    }


def parameter(variant: dict[str, Any], name: str) -> float:
    record = variant["parameters"][name]
    value = record.get("value")
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"numeric_parameter_required:{name}")
    return float(value)


def validate_contract(contract: dict[str, Any]) -> None:
    """Verrouille les exigences F35 consommées par le générateur CAO."""

    require(contract.get("phase") == "F35", "expected_F35_contract")
    required_families = contract.get("required_interface_frames_per_variant")
    require(
        required_families == list(REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS),
        "unexpected_required_interface_frame_families",
    )
    require(
        contract.get("required_interface_frame_counts_per_variant")
        == REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS,
        "unexpected_required_interface_frame_counts",
    )
    output_policy = contract.get("output_policy")
    require(isinstance(output_policy, dict), "output_policy_required")
    require(
        set(output_policy.get("derived_formats", []))
        == {"STEP", "STL", "JSON", "USD", "USDC"},
        "unexpected_derived_formats",
    )
    require(
        output_policy.get("derived_output_layout", {}).get("animated_usdc_stage")
        == "{variant}/usd/rotating-assembly-f35.usdc",
        "unexpected_usdc_stage_layout",
    )
    require(
        output_policy.get("derived_output_layout", {}).get("converted_usd_prototype")
        == "usd-conversion/{variant}/prototypes/{family}/{family}.usd",
        "unexpected_usd_prototype_layout",
    )
    release_gates = contract.get("release_gates")
    require(isinstance(release_gates, dict) and release_gates, "release_gates_required")
    require(all(value is False for value in release_gates.values()), "release_gate_must_remain_false")


def cylinder_x(radius: float, length: float, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return (
        Pos(x, y, z)
        * Rot(0.0, 90.0, 0.0)
        * Cylinder(radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    )


def cylinder_y(radius: float, length: float, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return (
        Pos(x, y, z)
        * Rot(90.0, 0.0, 0.0)
        * Cylinder(radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    )


def tube_x(outer_radius: float, inner_radius: float, length: float) -> Any:
    return cylinder_x(outer_radius, length) - cylinder_x(inner_radius, length + 2.0)


def tube_y(outer_radius: float, inner_radius: float, length: float, y: float = 0.0) -> Any:
    return cylinder_y(outer_radius, length, y=y) - cylinder_y(inner_radius, length + 2.0, y=y)


def cylinder_stations(variant: dict[str, Any]) -> list[float]:
    pitch = parameter(variant, "cylinder_pitch_mm")
    central = parameter(variant, "central_pair_pitch_mm")
    return [
        -(central / 2.0 + 2.0 * pitch),
        -(central / 2.0 + pitch),
        -central / 2.0,
        central / 2.0,
        central / 2.0 + pitch,
        central / 2.0 + 2.0 * pitch,
    ]


def main_bearing_stations(variant: dict[str, Any]) -> list[float]:
    """Derive eight design-study stations, including the twin central supports."""

    throws = cylinder_stations(variant)
    envelope = parameter(variant, "crankshaft_envelope_length_mm")
    width = parameter(variant, "main_journal_width_mm")
    end = envelope / 2.0 - width / 2.0 - 3.0
    central_half_gap = (throws[3] - throws[2]) / 4.0
    return [
        -end,
        (throws[0] + throws[1]) / 2.0,
        (throws[1] + throws[2]) / 2.0,
        -central_half_gap,
        central_half_gap,
        (throws[3] + throws[4]) / 2.0,
        (throws[4] + throws[5]) / 2.0,
        end,
    ]


def throw_phases_deg() -> list[float]:
    """Expose the single F35 phase authority as a mutable JSON-ready list."""

    return list(DESIGN_CRANKPIN_PHASES_DEG)


def build_crankshaft(variant: dict[str, Any]) -> Any:
    from build123d import Compound, Pos, Rot

    main_diameter = parameter(variant, "main_journal_diameter_mm")
    main_width = parameter(variant, "main_journal_width_mm")
    pin_diameter = parameter(variant, "crankpin_diameter_mm")
    pin_width = parameter(variant, "crankpin_width_mm")
    radius = parameter(variant, "crank_radius_mm")
    web_thickness = max(8.0, 0.42 * main_width)
    web_hub_radius = max(main_diameter * 0.64, pin_diameter * 0.66)
    counterweight_radius = max(main_diameter * 0.72, pin_diameter * 0.78)
    pieces: list[Any] = []

    for station in main_bearing_stations(variant):
        pieces.append(cylinder_x(main_diameter / 2.0, main_width, x=station))

    for station, phase in zip(cylinder_stations(variant), throw_phases_deg(), strict=True):
        angle = math.radians(phase)
        pin_y = radius * math.cos(angle)
        pin_z = radius * math.sin(angle)
        pieces.append(cylinder_x(pin_diameter / 2.0, pin_width, station, pin_y, pin_z))
        for side in (-1.0, 1.0):
            web_x = station + side * (pin_width / 2.0 + web_thickness / 2.0)
            hub = cylinder_x(web_hub_radius, web_thickness, web_x, 0.0, 0.0)
            pin_hub = cylinder_x(pin_diameter * 0.62, web_thickness, web_x, pin_y, pin_z)
            counter = cylinder_x(
                counterweight_radius,
                web_thickness,
                web_x,
                -0.72 * pin_y,
                -0.72 * pin_z,
            )
            pieces.extend((hub, pin_hub, counter))

    # A slender construction spine and a central power-take-off envelope make
    # the visual compound contiguous enough to review; neither is a forging
    # definition and both remain explicit hypotheses in the report.
    envelope = parameter(variant, "crankshaft_envelope_length_mm")
    pieces.append(cylinder_x(main_diameter * 0.22, envelope - 4.0))
    pieces.append(cylinder_x(main_diameter * 0.82, 24.0))
    return Compound(children=pieces, label=f"{variant['id']} F35 crankshaft design study")


def build_main_bearing(variant: dict[str, Any]) -> Any:
    from build123d import Align, Box, Pos

    journal_radius = parameter(variant, "main_journal_diameter_mm") / 2.0
    width = parameter(variant, "main_journal_width_mm")
    shell = tube_x(journal_radius + 3.0, journal_radius + 0.35, width)
    # Two narrow split cuts make upper/lower shells visible as separate solids.
    cutter = Pos(0.0, 0.0, 0.0) * Box(
        width + 2.0,
        2.0 * (journal_radius + 5.0),
        0.8,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    return shell - cutter


def build_connecting_rod(variant: dict[str, Any]) -> Any:
    from build123d import Align, Box, Pos

    length = parameter(variant, "rod_center_distance_mm")
    width = parameter(variant, "rod_width_mm")
    big_bore = parameter(variant, "crankpin_diameter_mm")
    big_outer = parameter(variant, "rod_big_end_outer_diameter_mm")
    small_bore = parameter(variant, "rod_small_end_bore_mm")
    small_outer = small_bore + 15.0
    beam_height = max(14.0, 0.34 * big_outer)
    beam_length = length - big_outer / 2.0 - small_outer / 2.0 + 6.0
    body = cylinder_x(big_outer / 2.0, width)
    body = body + cylinder_x(small_outer / 2.0, width, y=length)
    body = body + Pos(0.0, length / 2.0, 0.0) * Box(
        width,
        beam_length,
        beam_height,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    body = body - cylinder_x(big_bore / 2.0 + 0.15, width + 4.0)
    body = body - cylinder_x(small_bore / 2.0 + 0.10, width + 4.0, y=length)

    pocket_depth = max(2.0, width * 0.27)
    pocket_length = max(10.0, beam_length - 14.0)
    for side in (-1.0, 1.0):
        pocket_x = side * (width / 2.0 - pocket_depth / 2.0 + 0.1)
        body = body - Pos(pocket_x, length / 2.0, 0.0) * Box(
            pocket_depth,
            pocket_length,
            max(5.0, beam_height - 5.0),
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
    return body


def build_piston_pin(variant: dict[str, Any]) -> Any:
    diameter = parameter(variant, "piston_pin_diameter_mm")
    length = parameter(variant, "piston_pin_length_mm")
    wall = max(2.0, diameter * 0.16)
    return tube_x(diameter / 2.0, diameter / 2.0 - wall, length)


def build_piston(variant: dict[str, Any]) -> Any:
    from build123d import Align, Box, Pos, Sphere

    bore = parameter(variant, "bore_mm")
    clearance = parameter(variant, "piston_radial_clearance_mm")
    crown = parameter(variant, "piston_crown_to_pin_axis_mm")
    skirt = parameter(variant, "piston_skirt_below_pin_mm")
    pin_diameter = parameter(variant, "piston_pin_diameter_mm")
    outer_radius = bore / 2.0 - clearance
    total_height = crown + skirt
    center_y = (crown - skirt) / 2.0
    body = cylinder_y(outer_radius, total_height, y=center_y)

    wall = max(4.5, bore * 0.055)
    crown_thickness = max(7.0, bore * 0.085)
    hollow_height = max(8.0, total_height - crown_thickness + 1.0)
    hollow_center = -skirt + hollow_height / 2.0 - 1.0
    body = body - cylinder_y(outer_radius - wall, hollow_height, y=hollow_center)

    boss_outer = pin_diameter / 2.0 + 6.5
    boss_length = min(parameter(variant, "piston_pin_length_mm") * 0.68, 2.0 * outer_radius - 3.0)
    body = body + cylinder_x(boss_outer, boss_length)
    body = body - cylinder_x(pin_diameter / 2.0 + 0.08, 2.0 * outer_radius + 4.0)

    ring_count = int(round(parameter(variant, "ring_count")))
    ring_height = parameter(variant, "ring_axial_height_mm")
    groove_depth = parameter(variant, "ring_radial_thickness_mm") + 0.35
    first_ring_y = crown - crown_thickness - ring_height
    for index in range(ring_count):
        groove_y = first_ring_y - index * (ring_height + 2.0)
        annulus = tube_y(outer_radius + 1.0, outer_radius - groove_depth, ring_height + 0.18, groove_y)
        body = body - annulus

    # A shallow spherical dish visually distinguishes the crown without
    # claiming a compression volume or combustion-chamber match.
    dish_radius = max(outer_radius * 0.62, 20.0)
    dish = Pos(0.0, crown + dish_radius - 2.0, 0.0) * Sphere(dish_radius)
    body = body - dish

    # Relief windows reduce the skirt into two load faces.  They are a visual
    # design hypothesis, not an FEA-derived skirt profile.
    relief_width = outer_radius * 1.12
    relief_height = max(8.0, skirt * 0.58)
    for side in (-1.0, 1.0):
        body = body - Pos(side * outer_radius * 0.82, -skirt * 0.55, 0.0) * Box(
            relief_width,
            relief_height,
            2.0 * outer_radius + 4.0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
    return body


def build_piston_ring(variant: dict[str, Any]) -> Any:
    from build123d import Align, Box, Pos

    bore = parameter(variant, "bore_mm")
    clearance = parameter(variant, "piston_radial_clearance_mm")
    axial = parameter(variant, "ring_axial_height_mm")
    radial = parameter(variant, "ring_radial_thickness_mm")
    outer_radius = bore / 2.0 - clearance * 0.55
    ring = tube_y(outer_radius, outer_radius - radial, axial)
    gap = Pos(outer_radius, 0.0, 0.0) * Box(
        radial * 2.2,
        axial + 2.0,
        max(0.8, bore * 0.012),
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    return ring - gap


def prototype_shapes(variant: dict[str, Any]) -> dict[str, Any]:
    return {
        "crankshaft": build_crankshaft(variant),
        "main_bearing_pair": build_main_bearing(variant),
        "connecting_rod": build_connecting_rod(variant),
        "piston": build_piston(variant),
        "piston_pin": build_piston_pin(variant),
        "piston_ring": build_piston_ring(variant),
    }


def mechanism_state(variant: dict[str, Any], crank_angle_deg: float) -> list[dict[str, Any]]:
    """Return a closed 180-degree V12 design-study linkage at one angle."""

    radius = parameter(variant, "crank_radius_mm")
    rod_length = parameter(variant, "rod_center_distance_mm")
    rod_width = parameter(variant, "rod_width_mm")
    sample = assembly_sample(
        crank_angle_deg=crank_angle_deg,
        station_x_mm=cylinder_stations(variant),
        crankpin_phases_deg=throw_phases_deg(),
        crank_radius_mm=radius,
        connecting_rod_length_mm=rod_length,
    )
    result: list[dict[str, Any]] = []
    for station_index, crankpin in enumerate(sample["crankpins"], start=1):
        station = float(crankpin["station_x_mm"])
        for piston in crankpin["pistons"]:
            bank = piston["bank"]
            x = station + paired_rod_axial_offset_mm(bank, rod_width)
            rod = piston["connecting_rod"]
            crank = [float(value) for value in rod["big_end_center_mm"]]
            pin = [float(value) for value in rod["small_end_center_mm"]]
            crank[0] = x
            pin[0] = x
            dy = pin[1] - crank[1]
            dz = pin[2] - crank[2]
            rod_angle = math.degrees(math.atan2(dz, dy))
            result.append(
                {
                    "station_id": f"station_{station_index:02d}",
                    "geometric_id": f"{bank}_station_{station_index:02d}",
                    "bank": bank,
                    "historical_cylinder_id": None,
                    "x_mm": x,
                    "crankpin_center_mm": crank,
                    "piston_pin_center_mm": pin,
                    "rod_midpoint_mm": [
                        x,
                        (crank[1] + pin[1]) / 2.0,
                        (crank[2] + pin[2]) / 2.0,
                    ],
                    "rod_rotation_x_deg": rod_angle,
                    "closure_error_mm": abs(float(rod["closure_error_mm"])),
                }
            )
    return result


def ring_offsets_from_pin_mm(variant: dict[str, Any]) -> list[float]:
    """Dérive les trois plans de gorge depuis l'axe de piston."""

    ring_count = int(round(parameter(variant, "ring_count")))
    require(ring_count == 3, f"f35_ring_count_must_be_three:{variant.get('id')}")
    crown = parameter(variant, "piston_crown_to_pin_axis_mm")
    ring_height = parameter(variant, "ring_axial_height_mm")
    crown_thickness = max(7.0, parameter(variant, "bore_mm") * 0.085)
    first = crown - crown_thickness - ring_height
    return [first - index * (ring_height + 2.0) for index in range(ring_count)]


def _interface_frame(
    *,
    frame_id: str,
    family: str,
    kind: str,
    origin_mm: list[float] | tuple[float, float, float],
    axis: list[float] | tuple[float, float, float],
    member_id: str,
) -> dict[str, Any]:
    """Construit un repère candidat homogène et explicitement non physique."""

    origin = [float(value) for value in origin_mm]
    direction = [float(value) for value in axis]
    require(len(origin) == 3 and all(math.isfinite(value) for value in origin), f"invalid_frame_origin:{frame_id}")
    require(len(direction) == 3 and all(math.isfinite(value) for value in direction), f"invalid_frame_axis:{frame_id}")
    require(math.isclose(math.sqrt(sum(value * value for value in direction)), 1.0, abs_tol=1.0e-12), f"frame_axis_not_unit:{frame_id}")
    return {
        "id": frame_id,
        "family": family,
        "member_id": member_id,
        "kind": kind,
        "origin_mm": origin,
        "axis": direction,
        "classification": "design_hypothesis_frame_not_measured",
        "physical_joint_enabled": False,
    }


def interface_frame_records(variant: dict[str, Any], crank_angle_deg: float) -> list[dict[str, Any]]:
    """Matérialise les 99 datums exigés par le contrat F35 pour une variante."""

    frames = [
        _interface_frame(
            frame_id="crankshaft_axis",
            family="crankshaft_axis",
            member_id="crankshaft",
            kind="revolute_candidate_axis",
            origin_mm=(0.0, 0.0, 0.0),
            axis=CRANK_AXIS,
        )
    ]
    for index, station in enumerate(main_bearing_stations(variant), start=1):
        frames.append(
            _interface_frame(
                frame_id=f"main_journal_centre_{index:02d}",
                family="main_journal_centres_01_to_08",
                member_id=f"main_journal_{index:02d}",
                kind="revolute_candidate_load_station",
                origin_mm=(station, 0.0, 0.0),
                axis=CRANK_AXIS,
            )
        )

    sample = assembly_sample(
        crank_angle_deg=crank_angle_deg,
        station_x_mm=cylinder_stations(variant),
        crankpin_phases_deg=throw_phases_deg(),
        crank_radius_mm=parameter(variant, "crank_radius_mm"),
        connecting_rod_length_mm=parameter(variant, "rod_center_distance_mm"),
    )
    for crankpin in sample["crankpins"]:
        station_id = str(crankpin["station_id"])
        frames.append(
            _interface_frame(
                frame_id=f"crankpin_centre_{station_id}",
                family="crankpin_centres_01_to_06",
                member_id=station_id,
                kind="revolute_candidate_axis",
                origin_mm=crankpin["center_mm"],
                axis=CRANK_AXIS,
            )
        )

    crown = parameter(variant, "piston_crown_to_pin_axis_mm")
    ring_offsets = ring_offsets_from_pin_mm(variant)
    for state in mechanism_state(variant, crank_angle_deg):
        geometric_id = str(state["geometric_id"])
        crank = state["crankpin_center_mm"]
        pin = state["piston_pin_center_mm"]
        bank_axis = BANK_AXES[state["bank"]]
        frames.extend(
            (
                _interface_frame(
                    frame_id=f"rod_big_end_axis_{geometric_id}",
                    family="rod_big_end_axis",
                    member_id=geometric_id,
                    kind="revolute_candidate_axis",
                    origin_mm=crank,
                    axis=CRANK_AXIS,
                ),
                _interface_frame(
                    frame_id=f"rod_small_end_axis_{geometric_id}",
                    family="rod_small_end_axis",
                    member_id=geometric_id,
                    kind="revolute_candidate_axis",
                    origin_mm=pin,
                    axis=CRANK_AXIS,
                ),
                _interface_frame(
                    frame_id=f"piston_pin_axis_{geometric_id}",
                    family="piston_pin_axis",
                    member_id=geometric_id,
                    kind="revolute_candidate_axis",
                    origin_mm=pin,
                    axis=CRANK_AXIS,
                ),
                _interface_frame(
                    frame_id=f"piston_crown_datum_{geometric_id}",
                    family="piston_crown_datum",
                    member_id=geometric_id,
                    kind="plane_datum",
                    origin_mm=tuple(pin[index] + crown * bank_axis[index] for index in range(3)),
                    axis=bank_axis,
                ),
            )
        )
        for ring_index, offset in enumerate(ring_offsets, start=1):
            frames.append(
                _interface_frame(
                    frame_id=f"piston_ring_groove_datum_{geometric_id}_{ring_index:02d}",
                    family="piston_ring_groove_datums",
                    member_id=f"{geometric_id}_{ring_index:02d}",
                    kind="plane_datum",
                    origin_mm=tuple(pin[index] + offset * bank_axis[index] for index in range(3)),
                    axis=bank_axis,
                )
            )

    counts = {
        family: sum(frame["family"] == family for frame in frames)
        for family in REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS
    }
    require(counts == REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS, f"interface_frame_count_mismatch:{variant.get('id')}:{counts}")
    require(len(frames) == EXPECTED_INTERFACE_FRAME_TOTAL, f"interface_frame_total_mismatch:{variant.get('id')}")
    require(len({frame["id"] for frame in frames}) == len(frames), f"duplicate_interface_frame_id:{variant.get('id')}")
    return frames


def transformed_assembly(variant: dict[str, Any], shapes: dict[str, Any], angle: float) -> tuple[Any, list[dict[str, Any]]]:
    from build123d import Compound, Pos, Rot

    children: list[Any] = []
    frames = interface_frame_records(variant, angle)
    children.append(Rot(angle, 0.0, 0.0) * shapes["crankshaft"])
    for index, station in enumerate(main_bearing_stations(variant), start=1):
        children.append(Pos(station, 0.0, 0.0) * shapes["main_bearing_pair"])

    crown = parameter(variant, "piston_crown_to_pin_axis_mm")
    ring_height = parameter(variant, "ring_axial_height_mm")
    ring_count = int(round(parameter(variant, "ring_count")))
    ring_first = crown - max(7.0, parameter(variant, "bore_mm") * 0.085) - ring_height
    states = mechanism_state(variant, angle)
    for index, state in enumerate(states, start=1):
        crank = state["crankpin_center_mm"]
        pin = state["piston_pin_center_mm"]
        midpoint = state["rod_midpoint_mm"]
        rod = Pos(*midpoint) * Rot(state["rod_rotation_x_deg"], 0.0, 0.0) * Pos(0.0, -parameter(variant, "rod_center_distance_mm") / 2.0, 0.0) * shapes["connecting_rod"]
        children.append(rod)
        piston_rotation = 0.0 if state["bank"] == "bank_A" else 180.0
        piston = Pos(*pin) * Rot(piston_rotation, 0.0, 0.0) * shapes["piston"]
        children.append(piston)
        children.append(Pos(*pin) * shapes["piston_pin"])
        bank_sign = 1.0 if state["bank"] == "bank_A" else -1.0
        for ring_index in range(ring_count):
            offset = bank_sign * (ring_first - ring_index * (ring_height + 2.0))
            children.append(
                Pos(pin[0], pin[1] + offset, pin[2])
                * Rot(piston_rotation, 0.0, 0.0)
                * shapes["piston_ring"]
            )
    return Compound(children=children, label=f"{variant['id']} F35 rotating assembly"), frames


def export_shape(shape: Any, step_path: Path, stl_path: Path) -> dict[str, Any]:
    from build123d import export_step, export_stl, import_step

    step_path.parent.mkdir(parents=True, exist_ok=True)
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    created = shape_metrics(shape)
    require(created["valid"], f"created_shape_invalid:{step_path.name}")
    require(created["solid_count"] > 0, f"created_shape_has_no_solids:{step_path.name}")
    require(created["all_solids_positive_volume"], f"created_shape_nonpositive_volume:{step_path.name}")
    export_step(shape, step_path)
    canonicalize_step_header(step_path)
    export_stl(shape, stl_path, tolerance=0.10, angular_tolerance=0.14)
    reopened = import_step(step_path)
    reopened_metrics = shape_metrics(reopened)
    require(reopened_metrics["valid"], f"step_roundtrip_invalid:{step_path.name}")
    require(reopened_metrics["solid_count"] == created["solid_count"], f"step_roundtrip_solid_count:{step_path.name}")
    relative_volume_error = abs(reopened_metrics["volume_mm3"] - created["volume_mm3"]) / created["volume_mm3"]
    require(relative_volume_error <= 1.0e-5, f"step_roundtrip_volume:{step_path.name}")
    return {
        "step": step_path.name,
        "stl": stl_path.name,
        "step_sha256": sha256(step_path),
        "stl_sha256": sha256(stl_path),
        "created_metrics": created,
        "roundtrip_metrics": reopened_metrics,
        "roundtrip_relative_volume_error": relative_volume_error,
    }


def build_variant(
    contract_path: Path,
    contract: dict[str, Any],
    variant: dict[str, Any],
    output_root: Path,
    runtime_provenance: dict[str, str],
) -> dict[str, Any]:
    variant_root = output_root / variant["id"]
    variant_root.mkdir(parents=True, exist_ok=True)
    shapes = prototype_shapes(variant)
    prototypes: dict[str, Any] = {}
    for family, shape in shapes.items():
        prototypes[family] = export_shape(
            shape,
            variant_root / "step" / f"{family}.step",
            variant_root / "stl" / f"{family}-display-only.stl",
        )

    angle = float(contract["cad_policy"]["static_review_crank_angle_deg"])
    assembly, frames = transformed_assembly(variant, shapes, angle)
    assembly_export = export_shape(
        assembly,
        variant_root / "step" / "rotating-assembly.step",
        variant_root / "stl" / "rotating-assembly-display-only.stl",
    )
    states = mechanism_state(variant, angle)
    maximum_closure_error = max(item["closure_error_mm"] for item in states)
    require(maximum_closure_error <= 1.0e-9, "analytical_linkage_not_closed")

    report = {
        "schema_version": "1.0.0",
        "phase": "F35",
        "status": "cad_design_study_built_not_physically_released",
        "variant_id": variant["id"],
        "contract_sha256": sha256(contract_path),
        "cad_runtime_image": runtime_provenance["image_ref"],
        "cad_runtime_provenance": runtime_provenance,
        "property_assignment_intent": "skip",
        "documentary_mass_record": contract["documentary_mass_register"][variant["id"]],
        "physical_mass_assignment_enabled": False,
        "scan_used": False,
        "historical_cylinder_mapping_resolved": False,
        "crank_topology_status": "2026_design_hypothesis_not_historical_measurement",
        "static_review_crank_angle_deg": angle,
        "prototype_count": len(prototypes),
        "component_instance_counts": {
            "crankshaft": 1,
            "main_bearing_pair": 8,
            "connecting_rod": 12,
            "piston": 12,
            "piston_pin": 12,
            "piston_ring": 12 * int(round(parameter(variant, "ring_count"))),
        },
        "candidate_joint_counts": {
            "crankcase_to_crankshaft_revolute": 1,
            "crankpin_to_rod_revolute": 12,
            "rod_to_pin_revolute": 12,
            "piston_to_cylinder_prismatic": 12,
            "total": 37,
            "enabled": 0,
        },
        "throw_stations_mm": cylinder_stations(variant),
        "main_bearing_stations_mm": main_bearing_stations(variant),
        "throw_phase_hypothesis_deg": throw_phases_deg(),
        "paired_rod_axial_layout": paired_rod_axial_layout_mm(
            parameter(variant, "rod_width_mm")
        ),
        "maximum_analytical_linkage_closure_error_mm": maximum_closure_error,
        "prototypes": prototypes,
        "assembly": assembly_export,
        "interface_frames": frames,
        "interface_frame_family_counts": {
            family: sum(frame["family"] == family for frame in frames)
            for family in REQUIRED_INTERFACE_FRAME_FAMILY_COUNTS
        },
        "interface_frame_total": len(frames),
        "release_gates": contract["release_gates"],
        "limitations": contract["prohibited_claims"],
    }
    report_path = variant_root / "geometry-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {
        "variant_id": variant["id"],
        "report": str(report_path.relative_to(output_root)),
        "report_sha256": sha256(report_path),
        "maximum_closure_error_mm": maximum_closure_error,
        "assembly_step_sha256": assembly_export["step_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract_path = args.contract.resolve()
    output = args.output.resolve()
    contract = load_json(contract_path)
    validate_contract(contract)
    require(output.name == "917-rotating-assembly-f35", "unsafe_output_directory_name")
    runtime_provenance = cad_runtime_provenance()
    output.mkdir(parents=True, exist_ok=True)
    variants = contract.get("variants")
    require(isinstance(variants, list) and len(variants) == 2, "exactly_two_variants_required")
    summaries = [
        build_variant(contract_path, contract, variant, output, runtime_provenance)
        for variant in variants
    ]
    run_report = {
        "schema_version": "1.0.0",
        "phase": "F35",
        "status": "two_rotating_assembly_design_studies_built",
        "contract_sha256": sha256(contract_path),
        "cad_runtime_image": runtime_provenance["image_ref"],
        "cad_runtime_provenance": runtime_provenance,
        "variant_count": len(summaries),
        "variants": summaries,
        "physical_kinematics_ready": False,
        "manufacturing_geometry_ready": False,
        "engine_power_proven": False,
    }
    run_path = output / "run-report.json"
    run_path.write_text(json.dumps(run_report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run_report, indent=2))


if __name__ == "__main__":
    main()
