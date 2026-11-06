#!/usr/bin/env python3
"""993 Turbo/GT2 intercooler bracket, F1 concept with photo-informed topology.

What changed from F0
--------------------
F0 was a two-rail open plate whose whole topology was invented inside the FVD
envelope. F1 keeps the envelope but takes its *topology* from public evidence:

* PET illustration 107-45 (charge air cooler), transcribed in the
  PorscheFanatics dataset ``data/oem-listed.json``: position 5 "bracket"
  993 110 110 50 / -52, listed with rubber mountings 930 113 430 00 (pos 9),
  sleeves 993 110 111 50 (pos 10), washers 900 151 008 02 (pos 11),
  combination screws 900 067 207 02 (pos 6) and nuts 964 126 311 00 (pos 7).
* A seller photograph of the genuine part (Auto Atlanta listing
  "Support intercooler 993 Turbo", image R99311011050.jpg, FVD watermark),
  linked from the PorscheFanatics dataset ``data/parts/006.json`` and read
  for topology only. It shows a single curved cast arm, one thick socket eye
  at each end and a raised pad with two through holes, off-centre on the arm.

What is still NOT known
-----------------------
Every coordinate, bore, hole spacing, section and height below is either
fitted to the published FVD envelope or an assumption. The photograph has no
scale and is a perspective view; nothing is measured from it. Which fastener
stack goes to which interface, and what the bracket bolts to, is not
established. ``INTERFACES`` records each interface with that status so the
geometry cannot be mistaken for a fit-ready contract.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-INTERCOOLER-BRACKET-TI-F1-0001"

# Published FVD11011050 envelope (aftermarket reinforced replacement).
PUBLISHED_LENGTH_MM = 255.0
PUBLISHED_WIDTH_MM = 80.0
PUBLISHED_HEIGHT_MM = 23.0
PUBLISHED_MASS_G = 200.0

# Assumptions (topology from the photograph, sizes not measured).
EYE_OUTER_RADIUS_MM = 13.0
EYE_BORE_DIAMETER_MM = 16.0
EYE_HEIGHT_MM = 16.0
ARM_WIDTH_MM = 12.0
ARM_HEIGHT_MM = 9.0
PAD_ARC_FRACTION = 0.62  # position along the arm, 0 = left eye, 1 = right eye
PAD_LENGTH_MM = 48.0  # along the arm tangent
PAD_WIDTH_MM = 22.0
PAD_HEIGHT_MM = PUBLISHED_HEIGHT_MM
PAD_HOLE_DIAMETER_MM = 8.5
PAD_HOLE_PITCH_MM = 30.0

# Derived so that the solid fills the published envelope exactly.
EYE_CHORD_MM = PUBLISHED_LENGTH_MM - 2.0 * EYE_OUTER_RADIUS_MM
# ARM_SAGITTA_MM is solved below (fit_sagitta) so the pad corners or the arm
# apex, whichever is higher, touch the published 80 mm width.

DENSITY_TI64_G_CM3 = 4.42
DENSITY_ALUMINIUM_CAST_G_CM3 = 2.68

INTERFACES = [
    {
        "id": "IF-1",
        "feature": "left end eye (socket boss with through bore)",
        "topology_evidence": "photograph: thick cylindrical eye at each end of the arm",
        "candidate_hardware": "rubber mounting 930 113 430 00, sleeve 993 110 111 50, washer 900 151 008 02 (PET 107-45 pos 9-11)",
        "hardware_assignment": "candidate only: the PET text lists the parts but the illustration that assigns them was not read",
        "position": "assumed (eye centre at the published envelope end)",
        "bore": "assumed",
        "mating_part": "unknown",
        "status": "blocked_unmeasured",
    },
    {
        "id": "IF-2",
        "feature": "right end eye (socket boss with through bore)",
        "topology_evidence": "photograph",
        "candidate_hardware": "same stack as IF-1",
        "hardware_assignment": "candidate only",
        "position": "assumed",
        "bore": "assumed",
        "mating_part": "unknown",
        "status": "blocked_unmeasured",
    },
    {
        "id": "IF-3",
        "feature": "raised pad with two through holes, off-centre on the arm",
        "topology_evidence": "photograph: one raised pad, two holes, roughly 60 % along the arm",
        "candidate_hardware": "combination screws 900 067 207 02 and/or nuts 964 126 311 00 (PET 107-45 pos 6-7)",
        "hardware_assignment": "candidate only",
        "position": "assumed (PAD_ARC_FRACTION)",
        "hole_pitch": "assumed",
        "mating_part": "unknown",
        "status": "blocked_unmeasured",
    },
]


def _arc(sagitta: float) -> dict[str, float]:
    chord = EYE_CHORD_MM
    radius = (chord**2 / 4.0 + sagitta**2) / (2.0 * sagitta)
    half_angle = math.asin(chord / (2.0 * radius))
    eye_y = EYE_OUTER_RADIUS_MM
    centre = (PUBLISHED_LENGTH_MM / 2.0, eye_y + sagitta - radius)
    return {
        "radius_mm": radius,
        "half_angle_rad": half_angle,
        "centre_x_mm": centre[0],
        "centre_y_mm": centre[1],
        "arc_length_mm": 2.0 * radius * half_angle,
    }


def _pad(arc: dict[str, float]) -> tuple[float, float, float]:
    # Angle measured from +Y, negative to the left eye.
    theta = -arc["half_angle_rad"] + PAD_ARC_FRACTION * 2.0 * arc["half_angle_rad"]
    x = arc["centre_x_mm"] + arc["radius_mm"] * math.sin(theta)
    y = arc["centre_y_mm"] + arc["radius_mm"] * math.cos(theta)
    return x, y, -math.degrees(theta)


def _top_y(sagitta: float) -> float:
    arc = _arc(sagitta)
    x, y, angle = _pad(arc)
    a = math.radians(angle)
    corners = [
        y + u * math.sin(a) + v * math.cos(a)
        for u in (-PAD_LENGTH_MM / 2.0, PAD_LENGTH_MM / 2.0)
        for v in (-PAD_WIDTH_MM / 2.0, PAD_WIDTH_MM / 2.0)
    ]
    apex = EYE_OUTER_RADIUS_MM + sagitta + ARM_WIDTH_MM / 2.0
    return max([apex] + corners)


def fit_sagitta() -> float:
    """Bisection: sagitta whose highest feature meets the published width."""

    low, high = 1.0, PUBLISHED_WIDTH_MM
    for _ in range(80):
        mid = (low + high) / 2.0
        if _top_y(mid) > PUBLISHED_WIDTH_MM:
            high = mid
        else:
            low = mid
    return (low + high) / 2.0


ARM_SAGITTA_MM = fit_sagitta()


def arc_geometry() -> dict[str, float]:
    """Circle through both eye centres with the envelope-fitted sagitta."""

    return _arc(ARM_SAGITTA_MM)


def pad_pose() -> tuple[float, float, float]:
    """Pad centre (x, y) and tangent angle in degrees."""

    return _pad(arc_geometry())


def build_solid():
    """Build the F1 BREP (build123d, available in the cadsim image)."""

    from build123d import (
        Align,
        Box,
        BuildLine,
        BuildSketch,
        CenterArc,
        Cylinder,
        Line,
        Pos,
        Rot,
        extrude,
        make_face,
    )

    arc = arc_geometry()
    cx, cy, r = arc["centre_x_mm"], arc["centre_y_mm"], arc["radius_mm"]
    start = 90.0 - math.degrees(arc["half_angle_rad"])
    span = 2.0 * math.degrees(arc["half_angle_rad"])
    r_out, r_in = r + ARM_WIDTH_MM / 2.0, r - ARM_WIDTH_MM / 2.0

    with BuildSketch() as sketch:
        with BuildLine():
            outer = CenterArc((cx, cy), r_out, start, span)
            inner = CenterArc((cx, cy), r_in, start, span)
            Line(outer @ 0, inner @ 0)
            Line(outer @ 1, inner @ 1)
        make_face()
    solid = extrude(sketch.sketch, amount=ARM_HEIGHT_MM)

    centred = (Align.CENTER, Align.CENTER, Align.MIN)
    eyes = [
        (EYE_OUTER_RADIUS_MM, EYE_OUTER_RADIUS_MM),
        (PUBLISHED_LENGTH_MM - EYE_OUTER_RADIUS_MM, EYE_OUTER_RADIUS_MM),
    ]
    for ex, ey in eyes:
        solid = solid + Pos(ex, ey, 0) * Cylinder(EYE_OUTER_RADIUS_MM, EYE_HEIGHT_MM, align=centred)

    px, py, angle = pad_pose()
    pad_frame = Pos(px, py, 0) * Rot(0, 0, angle)
    solid = solid + pad_frame * Box(PAD_LENGTH_MM, PAD_WIDTH_MM, PAD_HEIGHT_MM, align=centred)

    for ex, ey in eyes:
        solid = solid - Pos(ex, ey, 0) * Cylinder(EYE_BORE_DIAMETER_MM / 2.0, EYE_HEIGHT_MM, align=centred)
    for offset in (-PAD_HOLE_PITCH_MM / 2.0, PAD_HOLE_PITCH_MM / 2.0):
        solid = solid - pad_frame * Pos(offset, 0, 0) * Cylinder(
            PAD_HOLE_DIAMETER_MM / 2.0, PAD_HEIGHT_MM, align=centred
        )
    return solid


def screen(volume_mm3: float | None = None) -> dict[str, object]:
    """Mass and section screen; no load case, because none is evidenced."""

    arc = arc_geometry()
    px, py, angle = pad_pose()
    report: dict[str, object] = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f1_photo_informed_topology_envelope_fitted_sizes",
        "supersedes": "993-ENG-INTERCOOLER-BRACKET-TI-F0-0001 (two-rail plate topology not supported by any evidence)",
        "geometry_authority": {
            "published": [
                "FVD11011050 envelope 255 x 80 x 23 mm",
                "FVD11011050 mass 200 g",
            ],
            "identity": [
                "PET 107-45 pos 5 bracket 993 110 110 50 / -52",
                "PET 107-45 pos 6, 7, 9, 10, 11 candidate fastener and isolation stack",
            ],
            "topology_from_photograph": [
                "single curved arm",
                "one socket eye at each end",
                "one raised pad with two through holes, off-centre on the arm",
                "cast aluminium-coloured part with cast-in markings",
            ],
            "envelope_fitted": ["eye chord", "arm sagitta"],
            "assumptions": [
                "eye outer radius, bore and height",
                "arm width and height",
                "pad position, size, hole diameter and pitch",
            ],
            "not_claimed": "No measured OEM or FVD coordinate; not fit-ready.",
        },
        "interfaces": INTERFACES,
        "arc": dict(arc, sagitta_mm=ARM_SAGITTA_MM),
        "pad_pose": {"x_mm": px, "y_mm": py, "tangent_deg": angle},
        "section": {
            "arm_area_mm2": ARM_WIDTH_MM * ARM_HEIGHT_MM,
            "arm_second_moment_vertical_bending_mm4": ARM_WIDTH_MM * ARM_HEIGHT_MM**3 / 12.0,
            "arm_second_moment_lateral_bending_mm4": ARM_HEIGHT_MM * ARM_WIDTH_MM**3 / 12.0,
        },
        "load_case": None,
        "load_case_note": "No vehicle load, mass, vibration spectrum or temperature field is evidenced; F1 deliberately carries no stress result.",
        "release_authorized": False,
    }
    if volume_mm3 is not None:
        report["mass"] = {
            "volume_mm3": volume_mm3,
            "ti64_mass_g": volume_mm3 / 1000.0 * DENSITY_TI64_G_CM3,
            "cast_aluminium_equivalent_mass_g": volume_mm3 / 1000.0 * DENSITY_ALUMINIUM_CAST_G_CM3,
            "published_fvd_mass_g": PUBLISHED_MASS_G,
            "note": "The aluminium-equivalent mass is the useful plausibility check: the photographed OEM part looks cast aluminium. A titanium copy of the same shape is heavier, not lighter.",
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, help="STEP output")
    parser.add_argument("--stl", type=Path, help="STL output")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    volume = None
    if args.out or args.stl:
        from build123d import export_step, export_stl, import_step

        solid = build_solid()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("F1 is not a single valid BREP solid.")
        size = solid.bounding_box().size
        envelope = (size.X, size.Y, size.Z)
        target = (PUBLISHED_LENGTH_MM, PUBLISHED_WIDTH_MM, PUBLISHED_HEIGHT_MM)
        if any(abs(a - b) > 0.05 for a, b in zip(envelope, target)):
            raise SystemExit(f"Envelope mismatch: {envelope} vs {target}")
        volume = solid.volume
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            export_step(solid, str(args.out))
            back = import_step(str(args.out))
            if abs(back.volume - volume) > 0.05:
                raise SystemExit("STEP round trip changed the volume.")
        if args.stl:
            args.stl.parent.mkdir(parents=True, exist_ok=True)
            export_stl(solid, str(args.stl), tolerance=0.02, angular_tolerance=0.1)

    report = screen(volume)
    if volume is not None:
        report["step_check"] = {"valid_brep": True, "solid_count": 1, "envelope_mm": [round(v, 3) for v in envelope]}
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
