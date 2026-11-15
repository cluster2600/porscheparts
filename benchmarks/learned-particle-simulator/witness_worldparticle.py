#!/usr/bin/env python3
"""Witness of the WorldParticle learned particle simulator: what its rollouts are worth here.

Two kinds of check, on rollouts made beforehand with the authors' code and checkpoints:

  reproduction   a held-out sample of the authors' own data, cloth and fluid: distance of every
                 particle from their reference along the rollout, against the particle spacing;
  transfer       three cases the checkpoints were not trained on, each with an answer known
                 without the model: a cloth sheet on a flat plane (it ends flat on the plane), the
                 same sheet over a half-cylinder (mirror symmetry, no penetration), and a level
                 slab of fluid at rest in a tank of another size (it stays, level and inside).

The acceptance values below were fixed before the first rollout was read. The script computes
scalars only; it runs no model.

Usage: witness_worldparticle.py EVAL_DIR OUT.json
EVAL_DIR holds hf/ (checkpoints and samples), cases/ (make_cases.py) and the rollout folders.
"""

from __future__ import annotations

import glob
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ACCEPT = {
    "reproduction_mean_error_at_the_end_in_spacings": 1.0,
    "cloth_p95_edge_strain": 0.05,
    "cloth_below_ground_mm": 2.0,
    "cloth_plane_flatness_mm": 17.4,          # one particle spacing
    "cloth_tunnel_inside_the_cylinder_mm": 5.0,
    "cloth_tunnel_mirror_error_in_spacings": 1.0,
    "fluid_particles_outside_the_tank": 0,
    "fluid_still_mean_speed_m_s": 0.05,
    "fluid_still_mean_drift_in_spacings": 1.0,
}
CLOTH_START = 10                              # frame_start of the cloth checkpoint's configuration
TUNNEL_RADIUS = 0.3


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def edges(npz):
    idx, splits = npz["neighbors_index"], npz["neighbors_row_splits"]
    return np.repeat(np.arange(len(splits) - 1), np.diff(splits)), idx


def strain(positions, rest, npz) -> dict:
    i, j = edges(npz)
    e = np.linalg.norm(positions[i] - positions[j], axis=1) / np.linalg.norm(rest[i] - rest[j], axis=1) - 1.0
    return {"median": float(np.median(e)), "p95": float(np.percentile(e, 95)), "largest": float(e.max()), "smallest": float(e.min())}


def error_rows(pred, ref, spacing, frames) -> list:
    out = []
    for f in frames:
        d = np.linalg.norm(pred[f] - ref[f], axis=1)
        out.append({"step": int(f), "mean_mm": float(d.mean() * 1e3), "p95_mm": float(np.percentile(d, 95) * 1e3),
                    "largest_mm": float(d.max() * 1e3), "mean_in_spacings": float(d.mean() / spacing),
                    "mean_travel_of_the_reference_mm": float(np.linalg.norm(ref[f] - ref[0], axis=1).mean() * 1e3)})
    return out


def bulk_rows(pred, ref, frames, lo, hi) -> list:
    """How the fluid as a whole compares, where single particles have long since diverged (information)."""

    out = []
    edges_x = np.linspace(lo[0], hi[0], 21)
    for f in frames:
        tops = []
        for a, b in zip(edges_x[:-1], edges_x[1:]):
            p, r = pred[f][(pred[f][:, 0] >= a) & (pred[f][:, 0] < b)], ref[f][(ref[f][:, 0] >= a) & (ref[f][:, 0] < b)]
            if len(p) >= 10 and len(r) >= 10:
                tops.append(np.percentile(p[:, 1], 95) - np.percentile(r[:, 1], 95))
        out.append({"step": int(f), "centre_of_mass_distance_mm": float(np.linalg.norm(pred[f].mean(axis=0) - ref[f].mean(axis=0)) * 1e3),
                    "surface_height_rms_difference_mm": float(np.sqrt(np.mean(np.square(tops))) * 1e3) if tops else None,
                    "columns_compared": len(tops)})
    return out


def tank_case(case, roll) -> dict:
    """A fluid in a closed tank with no reference: what leaves it, how fast it moves, where its surface is."""

    from scipy.spatial import cKDTree

    pos, vel = roll["position"], roll["velocity"]
    lo, hi = case["box"].min(axis=0), case["box"].max(axis=0)
    out_any = ((pos < lo) | (pos > hi)).any(axis=2)
    ever = out_any.any(axis=0)
    steps_with_a_leak = np.flatnonzero(out_any.any(axis=1))
    end = pos[-1]
    walls = {"x_minus": int((end[:, 0] < lo[0]).sum()), "x_plus": int((end[:, 0] > hi[0]).sum()), "floor": int((end[:, 1] < lo[1]).sum()),
             "z_minus": int((end[:, 2] < lo[2]).sum()), "z_plus": int((end[:, 2] > hi[2]).sum())}
    drift = np.linalg.norm(end - pos[0], axis=1)
    nn = lambda p: float(np.median(cKDTree(p).query(p, k=2)[0][:, 1]))
    speed = lambda f: float(np.linalg.norm(vel[f], axis=1).mean())
    marks = sorted({min(f, len(pos) - 1) for f in (10, 50, 100, 200, len(pos) - 1)})
    return {"steps": len(pos) - 1, "particles": int(pos.shape[1]), "tank_m": [float(v) for v in (hi - lo)],
            "particles_ever_outside_the_tank": int(ever.sum()),
            "first_step_with_a_particle_outside": int(steps_with_a_leak[0]) if len(steps_with_a_leak) else None,
            "outside_at_the_end_by_wall": walls,
            "mean_speed_m_s_by_step": {str(f): speed(f) for f in marks},
            "drift_mm": {"mean": float(drift.mean() * 1e3), "p95": float(np.percentile(drift, 95) * 1e3), "largest": float(drift.max() * 1e3)},
            "surface_height_p99_mm": {"start": float(np.percentile(pos[0][:, 1], 99) * 1e3), "end": float(np.percentile(end[:, 1], 99) * 1e3)},
            "lowest_particle_above_the_floor_mm": {"start": float((pos[0][:, 1].min() - lo[1]) * 1e3), "end": float((end[:, 1].min() - lo[1]) * 1e3)},
            "nearest_neighbour_spacing_mm": {"start": nn(pos[0]) * 1e3, "end": nn(end) * 1e3}}


def one(pattern):
    found = sorted(glob.glob(str(pattern)))
    assert len(found) == 1, (pattern, found)
    return Path(found[0])


def main(eval_dir, out) -> None:
    ev = Path(eval_dir)
    checks = []

    def check(name, value, limit, smaller=True):
        ok = value <= limit if smaller else value >= limit
        checks.append({"check": name, "value": float(value), "limit": float(limit), "passed": bool(ok)})

    # ---- reproduction: cloth
    cloth_ref = np.load(ev / "hf/cloth_on_ball/dataset/10/10.npz")
    pred = np.load(one(ev / "out/outcomes/npz/10/*.npz"))["position"]
    ref = cloth_ref["position"][CLOTH_START:CLOTH_START + len(pred)]
    i, j = edges(cloth_ref)
    cloth_spacing = float(np.median(np.linalg.norm(cloth_ref["position"][0][i] - cloth_ref["position"][0][j], axis=1)))
    last = len(pred) - 1
    cloth_rep = {"sample": "cloth_on_ball/dataset/10 (validation split)", "particles": int(pred.shape[1]), "steps": last,
                 "particle_spacing_mm": cloth_spacing * 1e3, "errors": error_rows(pred, ref, cloth_spacing, (1, 30, last)),
                 "edge_strain_of_the_reference_at_the_end": strain(ref[last], cloth_ref["position"][0], cloth_ref),
                 "edge_strain_of_the_rollout_at_the_end": strain(pred[last], cloth_ref["position"][0], cloth_ref)}
    check("reproduction, cloth: mean error at the end, in spacings", cloth_rep["errors"][-1]["mean_in_spacings"],
          ACCEPT["reproduction_mean_error_at_the_end_in_spacings"])

    # ---- reproduction: fluid (the long rollout was made on a rented GPU, a shorter one on the CPU)
    fluid_ref = np.load(ev / "hf/fancy_fluid/dataset/66/66.npz")
    from scipy.spatial import cKDTree

    def nn_spacing(p):
        return float(np.median(cKDTree(p).query(p, k=2)[0][:, 1]))
    fluid_spacing = nn_spacing(fluid_ref["position"][-1])            # the settled reference
    lo, hi = fluid_ref["box"].min(axis=0), fluid_ref["box"].max(axis=0)
    fluid_rep = {"sample": "fancy_fluid/dataset/66 (validation split)", "particle_spacing_mm": fluid_spacing * 1e3, "rollouts": {}}
    for where, folder in (("gpu", ev / "gpu/out-fluid"), ("cpu", ev / "out-fluid")):
        if not folder.exists():
            continue
        pred = np.load(one(folder / "outcomes/npz/66/*.npz"))["position"]
        ref = fluid_ref["position"][:len(pred)]
        last = len(pred) - 1
        frames = sorted({f for f in (1, 30, 150, 300, last) if f <= last})
        outside = int(((pred < lo) | (pred > hi)).any(axis=2).any(axis=0).sum())
        fluid_rep["rollouts"][where] = {
            "particles": int(pred.shape[1]), "steps": last, "errors": error_rows(pred, ref, fluid_spacing, frames),
            "bulk": bulk_rows(pred, ref, frames, lo, hi), "particles_ever_outside_the_tank": outside,
            "nearest_neighbour_spacing_at_the_end_mm": {"reference": nn_spacing(ref[last]) * 1e3, "rollout": nn_spacing(pred[last]) * 1e3}}
        check(f"reproduction, fluid ({where}, {last} steps): mean error at the end, in spacings",
              fluid_rep["rollouts"][where]["errors"][-1]["mean_in_spacings"], ACCEPT["reproduction_mean_error_at_the_end_in_spacings"])
        check(f"reproduction, fluid ({where}, {last} steps): particles ever outside the tank", outside, ACCEPT["fluid_particles_outside_the_tank"])

    # ---- transfer: cloth on a plane
    rest = cloth_ref["position"][0]
    ground = float(cloth_ref["ground_points"][0, 1])
    case = np.load(ev / "cases/cloth-plane/cloth-plane.npz")
    roll = np.load(one(ev / "out-cases/outcomes/npz/cloth-plane/*.npz"))
    end, vel = roll["position"][-1], roll["velocity"][-1]
    plane = {"steps": len(roll["position"]) - 1, "ground_height_mm": ground * 1e3,
             "height_above_the_ground_mm": {"mean": float((end[:, 1].mean() - ground) * 1e3), "lowest": float((end[:, 1].min() - ground) * 1e3),
                                            "highest": float((end[:, 1].max() - ground) * 1e3)},
             "flatness_p99_minus_p1_mm": float((np.percentile(end[:, 1], 99) - np.percentile(end[:, 1], 1)) * 1e3),
             "sheet_extent_mm": [float((end[:, a].max() - end[:, a].min()) * 1e3) for a in (0, 2)],
             "sheet_extent_at_rest_mm": [float((rest[:, a].max() - rest[:, a].min()) * 1e3) for a in (0, 2)],
             "mean_speed_at_the_end_m_s": float(np.linalg.norm(vel, axis=1).mean()),
             "edge_strain_at_the_end": strain(end, rest, case),
             "lowest_point_of_the_authors_reference_above_the_ground_mm": float((cloth_ref["position"][-1][:, 1].min() - ground) * 1e3)}
    check("cloth on a plane: deepest vertex below the ground, mm", max(0.0, -plane["height_above_the_ground_mm"]["lowest"]), ACCEPT["cloth_below_ground_mm"])
    check("cloth on a plane: flatness, mm", plane["flatness_p99_minus_p1_mm"], ACCEPT["cloth_plane_flatness_mm"])
    check("cloth on a plane: p95 edge strain", plane["edge_strain_at_the_end"]["p95"], ACCEPT["cloth_p95_edge_strain"])

    # ---- transfer: cloth over a half-cylinder
    case = np.load(ev / "cases/cloth-tunnel/cloth-tunnel.npz")
    roll = np.load(one(ev / "out-cases/outcomes/npz/cloth-tunnel/*.npz"))
    start, end, vel = roll["position"][0], roll["position"][-1], roll["velocity"][-1]
    radial = np.hypot(end[:, 0], end[:, 1] - ground)
    over = end[:, 1] > ground
    inside = np.where(over, TUNNEL_RADIUS - radial, 0.0)
    # mirror partner of every vertex, found on the flat sheet at rest (its grid is symmetric about x = 0)
    mirror = cKDTree(rest[:, [0, 2]]).query(rest[:, [0, 2]] * np.array([-1.0, 1.0]))
    assert mirror[0].max() < 0.25 * cloth_spacing, "the sheet at rest has no mirror vertex for every vertex"
    m = mirror[1]
    mirror_error = np.linalg.norm(end * np.array([-1.0, 1.0, 1.0]) - end[m], axis=1)
    crown = np.abs(start[:, 0]) < 0.1
    tunnel = {"steps": len(roll["position"]) - 1, "radius_mm": TUNNEL_RADIUS * 1e3,
              "deepest_vertex_inside_the_cylinder_mm": float(max(0.0, inside.max()) * 1e3),
              "vertices_more_than_1_mm_inside": int((inside > 1e-3).sum()),
              "deepest_vertex_below_the_ground_mm": float(max(0.0, ground - end[:, 1].min()) * 1e3),
              "mirror_error_mm": {"mean": float(mirror_error.mean() * 1e3), "p95": float(np.percentile(mirror_error, 95) * 1e3),
                                  "largest": float(mirror_error.max() * 1e3)},
              "gap_over_the_crown_mm": {"median": float(np.median(radial[crown] - TUNNEL_RADIUS) * 1e3),
                                        "largest": float((radial[crown] - TUNNEL_RADIUS).max() * 1e3)},
              "share_of_vertices_within_one_spacing_of_the_cylinder_or_the_ground":
                  float(((np.abs(radial - TUNNEL_RADIUS) < cloth_spacing) | (end[:, 1] - ground < cloth_spacing)).mean()),
              "mean_speed_at_the_end_m_s": float(np.linalg.norm(vel, axis=1).mean()),
              "edge_strain_at_the_end": strain(end, rest, case)}
    check("cloth over a half-cylinder: deepest vertex inside the cylinder, mm", tunnel["deepest_vertex_inside_the_cylinder_mm"],
          ACCEPT["cloth_tunnel_inside_the_cylinder_mm"])
    check("cloth over a half-cylinder: deepest vertex below the ground, mm", tunnel["deepest_vertex_below_the_ground_mm"], ACCEPT["cloth_below_ground_mm"])
    check("cloth over a half-cylinder: mean mirror error, in spacings", tunnel["mirror_error_mm"]["mean"] / (cloth_spacing * 1e3),
          ACCEPT["cloth_tunnel_mirror_error_in_spacings"])
    check("cloth over a half-cylinder: p95 edge strain", tunnel["edge_strain_at_the_end"]["p95"], ACCEPT["cloth_p95_edge_strain"])

    # ---- transfer: fluid in a tank of another size, and the control in a tank of the training size
    fluid_cases = {}
    for name, label, folder in (("fluid-still", "fluid_at_rest", ev / "gpu" if (ev / "gpu").exists() else ev),
                                ("fluid-still-training-tank", "fluid_at_rest_in_a_tank_of_the_training_size", ev / "gpu"),
                                ("fluid-dam", "dam_break_in_the_other_tank", ev / "gpu")):
        files = sorted(glob.glob(str(folder / f"out-cases/outcomes/npz/{name}/*.npz")))
        if not files:
            continue
        case = np.load(folder / f"cases/{name}/{name}.npz") if (folder / f"cases/{name}/{name}.npz").exists() else np.load(ev / f"cases/{name}/{name}.npz")
        fluid_cases[label] = tank_case(case, np.load(files[0]))
    lattice = 60.0
    still = fluid_cases["fluid_at_rest"]
    last_speed = lambda c: list(c["mean_speed_m_s_by_step"].values())[-1]
    check("fluid at rest: particles ever outside the tank", still["particles_ever_outside_the_tank"], ACCEPT["fluid_particles_outside_the_tank"])
    check("fluid at rest: mean speed at the end, m/s", last_speed(still), ACCEPT["fluid_still_mean_speed_m_s"])
    check("fluid at rest: mean drift, in lattice spacings", still["drift_mm"]["mean"] / lattice, ACCEPT["fluid_still_mean_drift_in_spacings"])
    # The two cases below were added after the first reading of the still slab; they reuse its limits.
    if "fluid_at_rest_in_a_tank_of_the_training_size" in fluid_cases:
        control = fluid_cases["fluid_at_rest_in_a_tank_of_the_training_size"]
        check("control, fluid at rest in a tank of the training size: particles ever outside the tank",
              control["particles_ever_outside_the_tank"], ACCEPT["fluid_particles_outside_the_tank"])
        check("control, fluid at rest in a tank of the training size: mean speed at the end, m/s", last_speed(control), ACCEPT["fluid_still_mean_speed_m_s"])
    if "dam_break_in_the_other_tank" in fluid_cases:
        check("dam break in the other tank: particles ever outside the tank",
              fluid_cases["dam_break_in_the_other_tank"]["particles_ever_outside_the_tank"], ACCEPT["fluid_particles_outside_the_tank"])
    if (ev / "gpu").exists() and glob.glob(str(ev / "out-cases/outcomes/npz/fluid-still/*.npz")):
        fluid_cases["fluid_at_rest_on_the_cpu_100_steps"] = tank_case(np.load(ev / "cases/fluid-still/fluid-still.npz"),
                                                                      np.load(one(ev / "out-cases/outcomes/npz/fluid-still/*.npz")))

    here = Path(__file__).resolve().parent
    record = {
        "schema": "learned-particle-simulator-witness/1", "date": time.strftime("%Y-%m-%d"),
        "tool": {"name": "WorldParticle", "code": "https://github.com/WorldParticle/WorldParticle",
                 "code_commit": (ev / "src-commit.txt").read_text().strip(), "licence": "MIT",
                 "paper": "arXiv:2605.15305", "weights": "https://huggingface.co/datasets/wclw1021/WorldParticle",
                 "checkpoints_sha256": {name: sha256(ev / f"hf/{name}/checkpoint/final.ckpt") for name in ("cloth_on_ball", "fancy_fluid")},
                 "attention_backend": "PyTorch scaled-dot-product attention (ATTN_IMPL=sdpa), on this host's CPU and on one rented "
                                      "RTX 3090; the authors' FlashAttention path was not run"},
        "scope": "rollouts of two released checkpoints: one held-out sample of the authors' data each, and three cases outside "
                 "their training scenes with answers known without the model. A witness of the tool as released: it calibrates no "
                 "material, and no case here is a part of this repository",
        "acceptance_fixed_before_the_first_reading": ACCEPT,
        "script_sha256": sha256(Path(__file__)), "cases_script_sha256": sha256(here / "make_cases.py"),
        "reproduction": {"cloth": cloth_rep, "fluid": fluid_rep},
        "transfer": {"cloth_on_a_plane": plane, "cloth_over_a_half_cylinder": tunnel, **fluid_cases},
        "checks": checks, "passed": all(c["passed"] for c in checks),
        "not_covered": ["gases: the paper and the released checkpoints hold no gas case; its fluids are liquids with a free surface",
                        "training: no training code is released, so the model cannot be fitted to this repository's solver results",
                        "granular material, elastic solids, non-Newtonian fluids, molecular dynamics: no checkpoint released",
                        "any part, mould or material of this repository"],
    }
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"passed": record["passed"], "checks": checks}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
