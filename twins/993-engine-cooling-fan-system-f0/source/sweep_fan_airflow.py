#!/usr/bin/env python3
"""Controlled organic-blade experiments; geometric screening is not CFD."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CHANGES = {
    "e-control": {},
    "pitch30": {"blade_pitch_deg": 30},
    "pitch42": {"blade_pitch_deg": 42},
    "pitch48": {"blade_pitch_deg": 48},
    "twist4": {"tip_twist_deg": -4},
    "twist16": {"tip_twist_deg": -16},
    "camber15": {"camber_mm": -1.5},
    "camber55": {"camber_mm": -5.5},
    "sweep-minus8": {"sweep_mm": -8},
    "sweep0": {"sweep_mm": 0},
    "sweep16": {"sweep_mm": 16},
    "chord60": {"blade_tip_chord_mm": 60},
    "chord80": {"blade_tip_chord_mm": 80},
    "pitch42-camber55": {"blade_pitch_deg": 42, "camber_mm": -5.5},
    "pitch30-chord80": {"blade_pitch_deg": 30, "blade_tip_chord_mm": 80},
    "twist16-sweep0": {"tip_twist_deg": -16, "sweep_mm": 0},
}


def plan(output):
    base = json.loads((HERE / "picogk-reference/organic-e.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    for name, change in CHANGES.items():
        candidate = base | change
        candidate["parameter_evidence"] = base["parameter_evidence"] | {
            "sweep_changes": "Unmeasured design experiment: " + json.dumps(change)}
        (output / (name + ".json")).write_text(json.dumps(candidate, indent=2) + "\n")
    (output / "plan.json").write_text(json.dumps({
        "baseline": "e-control", "variants": CHANGES,
        "fixed": ["rotor_diameter_mm", "blade_count", "cup_radius_mm", "bore_radius_mm", "blade_thickness_mm"],
        "objective": "Compare flow and shaft power at matched speed, pressure and numerical settings",
        "geometric_screen_is_airflow_prediction": False,
        "installed_assembly_represented": False,
        "manufacturing_authorized": False,
    }, indent=2) + "\n")


def screen(source, output, device):
    import numpy as np
    import trimesh
    import warp as wp

    # Compile from a real file: Warp needs source locations for its kernel.
    from warp_fan_screen import axial_hits
    m = trimesh.load_mesh(source, process=True)
    if not (m.is_watertight and m.is_winding_consistent and m.body_count == 1 and m.volume > 0):
        raise ValueError("Reject invalid or disconnected geometry")
    mesh = wp.Mesh(points=wp.array(m.vertices.astype(np.float32), dtype=wp.vec3, device=device),
                   indices=wp.array(m.faces.astype(np.int32).ravel(), dtype=wp.int32, device=device))
    # Deterministic equal-area samples of the blade annulus, in millimetres.
    r = np.sqrt(82.5**2 + (np.arange(128) + .5) / 128 * (122.5**2 - 82.5**2))
    theta = (np.arange(720) + .5) * 2 * np.pi / 720
    rr, tt = np.meshgrid(r, theta, indexing="ij")
    points = np.column_stack((rr.ravel()*np.cos(tt.ravel()), rr.ravel()*np.sin(tt.ravel()),
                              np.full(rr.size, -100))).astype(np.float32)
    origins = wp.array(points, dtype=wp.vec3, device=device)
    hits = wp.zeros(len(points), dtype=wp.int32, device=device)
    wp.launch(axial_hits, dim=len(points), inputs=[mesh.id, origins, hits], device=device)
    wp.synchronize_device(device)
    blocked = hits.numpy()
    report = {"status": "geometric_screen_only", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "warp_version": wp.__version__, "device": str(wp.get_device(device)),
              "samples": len(points), "axial_unblocked_annulus_fraction": float(1-blocked.mean()),
              "volume_mm3": float(m.volume), "assumed_alsi10mg_mass_g": float(m.volume*.002670),
              "bounds_mm": m.bounds.tolist(), "watertight": True, "connected_bodies": 1,
              "airflow_m3_s": None, "manufacturing_authorized": False}
    output.write_text(json.dumps(report, indent=2) + "\n")


def prepare(geometry, output, device):
    subprocess.run([sys.executable, str(HERE / "prepare_reference_cfd.py"), str(geometry),
                    str(output), "--level", "3", "--iterations", "500", "--device", device], check=True)
    case = output / "case"
    mesh = case / "system/snappyHexMeshDict"
    text = mesh.read_text().replace("nSmoothPatch 3", "nSmoothPatch 5").replace("nRelaxIter 8", "nRelaxIter 12")
    # Correct the permissive 80-degree mesh-generation default, not checkMesh's gate.
    text = text.replace("maxBoundarySkewness 3.5;", "maxBoundarySkewness 3.5;\n maxConcave 5;")
    mesh.write_text(text)
    schemes = case / "system/fvSchemes"
    schemes.write_text(schemes.read_text().replace("div(phi,U) bounded Gauss upwind;",
        "div(phi,U) bounded Gauss linearUpwind grad(U);"))
    control = case / "system/controlDict"
    control.write_text(control.read_text().replace("endTime 500;", "endTime 1200;")
                      .replace("writeInterval 500;", "writeInterval 1200;"))
    manifest = case / "fan-input.json"
    data = json.loads(manifest.read_text())
    data.update(study_iteration_budget=1200, extended_mesh_required=True,
                velocity_advection="linearUpwind", wall_layers=False,
                termination_policy="Reject failed extended mesh; cap at 1200 iterations; require flow and torque convergence")
    manifest.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "screen", "prepare"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    if args.action == "plan":
        plan(args.output)
    else:
        if args.source is None or args.output.exists():
            parser.error("Existing source and new output required; preserve previous runs")
        if args.action == "screen":
            screen(args.source, args.output, args.device)
        else:
            prepare(args.source, args.output, args.device)
