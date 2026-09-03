#!/usr/bin/env python3
"""Rend 36 coupes cinématiques F38 conditionnelles depuis l'écran F37."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def valve_vector(tilt_deg: float) -> tuple[float, float]:
    angle = math.radians(tilt_deg)
    return math.sin(angle), math.cos(angle)


def spring_polyline(y: float, z0: float, length: float, width: float, turns: int = 10) -> tuple[list[float], list[float]]:
    ys, zs = [], []
    for index in range(2 * turns + 1):
        fraction = index / (2 * turns)
        ys.append(y + (width / 2.0 if index % 2 else -width / 2.0))
        zs.append(z0 + fraction * length)
    return ys, zs


def render_frame(output: Path, phase_fraction: float, lift: float, spec: dict, kinematic: dict, frame_index: int) -> None:
    fig, ax = plt.subplots(figsize=(12, 8), dpi=130)
    fig.patch.set_facecolor("#07131c")
    ax.set_facecolor("#0b1b25")
    carrier = spec["carrier"]
    rail_y = float(carrier["rail_size_xyz_mm"][1])
    rail_z = float(carrier["rail_size_xyz_mm"][2])
    rail_cz = float(carrier["rail_centre_z_mm"])
    for axis_y in (carrier["intake_axis_yz_mm"][0], carrier["exhaust_axis_yz_mm"][0]):
        ax.add_patch(FancyBboxPatch(
            (float(axis_y) - rail_y / 2.0, rail_cz - rail_z / 2.0), rail_y, rail_z,
            boxstyle="round,pad=0,rounding_size=3", facecolor="#d3a348", edgecolor="#ffd782", linewidth=1.8, alpha=0.78,
        ))
        ax.add_patch(Circle((float(axis_y), float(carrier["intake_axis_yz_mm"][1])), 7.0, facecolor="#101820", edgecolor="#d9edf2", linewidth=1.4))

    colours = {"intake": "#63d7ff", "exhaust": "#ff8c64"}
    for family in ("intake", "exhaust"):
        data = spec["valvetrain"][family]
        tilt = float(data["tilt_y_deg"])
        uy, uz = valve_vector(tilt)
        seat_y = float(data["centres_mm"][0][1])
        moved_y = seat_y + lift * uy
        moved_z = lift * uz
        head_radius = float(data["head_diameter_mm"]) / 2.0
        tangent_y, tangent_z = uz, -uy
        p1 = (moved_y - tangent_y * head_radius, moved_z - tangent_z * head_radius)
        p2 = (moved_y + tangent_y * head_radius, moved_z + tangent_z * head_radius)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=colours[family], linewidth=5.0, solid_capstyle="round")
        stem_end = (moved_y + uy * 104.0, moved_z + uz * 104.0)
        ax.plot([moved_y, stem_end[0]], [moved_z, stem_end[1]], color=colours[family], linewidth=3.2)
        guide_start = (seat_y + uy * 20.0, uz * 20.0)
        guide_end = (guide_start[0] + uy * 56.0, guide_start[1] + uz * 56.0)
        ax.plot([guide_start[0], guide_end[0]], [guide_start[1], guide_end[1]], color="#a8b5bd", linewidth=9.0, alpha=0.45)
        pivot_y, pivot_z = next(case["pivot_yz_mm"] for case in kinematic["cases"] if case["id"].startswith(family))
        closed_tip = next(case["closed_valve_tip_yz_mm"] for case in kinematic["cases"] if case["id"].startswith(family))
        tip_y = float(closed_tip[0]) + lift * uy
        tip_z = float(closed_tip[1]) - lift * uz
        ax.plot([float(pivot_y), tip_y], [float(pivot_z), tip_z], color="#eaf2f5", linewidth=7.0, solid_capstyle="round")
        ax.add_patch(Circle((float(pivot_y), float(pivot_z)), 3.0, facecolor="#07131c", edgecolor="#ffffff", linewidth=1.5))
        spring_length = max(30.0, float(spec["valvetrain"]["spring"]["installed_length_mm"]) - 0.55 * lift)
        ys, zs = spring_polyline(seat_y + uy * 49.0, uz * 49.0, spring_length, 15.0)
        ax.plot(ys, zs, color=colours[family], linewidth=1.6, alpha=0.9)

    ax.add_patch(Rectangle((-62.0, -7.0), 124.0, 10.0, facecolor="#354752", edgecolor="#8299a5", linewidth=1.0))
    ax.text(-61, -14, "PLAN CHAMBRE / SIÈGES", color="#91aab5", fontsize=9)
    ax.set_xlim(-75, 75)
    ax.set_ylim(-20, 130)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color="#29404c", alpha=0.25, linewidth=0.6)
    ax.set_xlabel("Y local [mm]", color="#b8c9d1")
    ax.set_ylabel("Z local [mm]", color="#b8c9d1")
    ax.tick_params(colors="#78909b")
    for spine in ax.spines.values():
        spine.set_color("#38515e")
    ax.set_title(
        f"F38 — COUPE 4 SOUPAPES • image {frame_index + 1:02d}/36 • levée écran {lift:.2f} mm",
        color="white", fontsize=15, fontweight="bold", pad=16,
    )
    fig.text(0.5, 0.02, "CINÉMATIQUE F37 RÉUTILISÉE — PROFIL DE CAME NON MESURÉ — ÉCRAN CONDITIONNEL, PAS UNE VALIDATION DYNAMIQUE", ha="center", color="#ffca74", fontsize=9, fontweight="bold")
    fig.tight_layout(rect=(0.02, 0.05, 0.98, 0.97))
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--kinematics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    kinematic = json.loads(args.kinematics.read_text(encoding="utf-8"))
    require(spec["phase"] == "F38", "spec_phase_must_be_f38")
    require(sha256(args.kinematics) == spec["parent_evidence"]["f37_kinematic_report"]["sha256"], "kinematic_sha256_mismatch")
    require(kinematic["gates"]["measured_cam_profile_available"] is False, "measured_cam_profile_state_changed")
    require(kinematic["gates"]["spintron_correlated"] is False, "spintron_state_changed")
    args.output.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(36):
        phase = index / 36.0
        lift = float(spec["carrier"]["valve_lift_mm"]) * 0.5 * (1.0 - math.cos(2.0 * math.pi * phase))
        frame = args.output / f"frame-{index:03d}.png"
        render_frame(frame, phase, lift, spec, kinematic, index)
        frames.append({"index": index, "phase_fraction": phase, "screen_lift_mm": lift, "path": frame.name, "sha256": sha256(frame), "bytes": frame.stat().st_size})
    key_states = {"closed": 0, "mid_lift": 9, "open": 18}
    for name, index in key_states.items():
        source = args.output / f"frame-{index:03d}.png"
        destination = args.output / f"state-{name}.png"
        destination.write_bytes(source.read_bytes())
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "status": "conditional_36_frame_valvetrain_section_sequence_complete_dynamic_validation_blocked",
        "classification": "kinematic_visualization_from_unmeasured_cam_profile_not_dynamic_simulation",
        "inputs": {"spec_sha256": sha256(args.spec), "f37_kinematic_report_sha256": sha256(args.kinematics)},
        "frame_count": len(frames),
        "frames": frames,
        "key_states": {name: {"frame_index": index, "path": f"state-{name}.png", "sha256": sha256(args.output / f"state-{name}.png")} for name, index in key_states.items()},
        "gates": {"measured_cam_profile_available": False, "dynamic_contact_and_flexure_fea_complete": False, "spintron_correlated": False, "engine_start_authorized": False},
    }
    (args.output / "f38-valvetrain-sequence-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "frames": len(frames)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
