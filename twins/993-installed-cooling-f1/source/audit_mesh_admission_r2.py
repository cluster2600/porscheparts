#!/usr/bin/env python3
"""Admission audit of the R2 duct surface, with the criteria of the 2026-11-10 audit (issue #452).

``audit_mesh_admission.py`` is pinned by the audit it produced and is not edited.
This script loads it by hash and reuses its faces, its junction rule, its
thresholds, its surface statistics and its cell locator as they are. It adds
only what R2 needs:

- the constructive fluid model of ``source-r2/Program.cs`` (pinned by hash),
  used for the check that the model describes the surface to within one voxel;
- a reader for the surface that ``prepare_duct_cfd_r2.py`` writes;
- the same admission rule, written once as a function so that a test can apply
  it to the retained R1 report and find the R1 verdict again.

The R1 kind names are kept on purpose. In R2 the joins they name are blended,
so a sharp edge found there counts against R2 exactly as it counted against R1:
re-entrant sharp edges at the union seam or on the alternator, and sharp edges
that no constructive junction explains, each make the input inadmissible.

With ``--case`` it also locates the concave cells and faces of a meshed trial.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]
BASE_PATH = STUDY / "source/audit_mesh_admission.py"
BASE_SHA256 = "6bbaaffb9ad5854359938e61f153fae1d29d368cef6c59457aee72e0c58c5156"
R2_PROGRAM = STUDY / "source-r2/Program.cs"
R2_PROGRAM_SHA256 = "96ebe20a5b032e885231f81c6f41379295e6702043d637e32f16245928d131cf"
CYLINDER_FRONT_DY_R2 = -30.0   # with s > 0 the fan cylinder starts at rear - 30


def load_base():
    """The pinned R1 auditor as a module of its own."""
    if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError("audit_mesh_admission.py changed; the R2 audit is defined on the pinned revision")
    spec = importlib.util.spec_from_file_location("audit_mesh_admission_pinned", BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def smin(a, b, k):
    """RotKit.SMin: the hard minimum for k <= 0."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def blends(g):
    """(k, s): the re-entrant blend and the alternator-subtraction blend of a study card, 0 when absent."""
    return float(g.get("reentrant_blend_mm", 0)), float(g.get("alternator_subtraction_blend_mm", 0))


def bind_r2_model(base, card_geometry):
    """Give the pinned auditor the fluid model of source-r2/Program.cs for one study card.

    Only ``constituents`` and ``fluid_sdf`` are replaced, and only to add the
    blended fields and to combine them as the generator does. FACES,
    ``face_distances``, ``junction_kind`` and every threshold stay the pinned
    ones. With both blends at 0 the model is the R1 model again.
    """
    k, s = blends(card_geometry)
    r1_constituents = base.constituents

    def constituents(p, g):
        values, parts = r1_constituents(p, g)
        values = dict(values)
        rear, zf = g["fan_rear_y_mm"], g["fan_centre_z_mm"]
        values["r2_alternator"] = values["alternator"]
        values["r2_fan_cylinder"] = values["fan_cylinder"]
        if k > 0:
            alt_dr, _ = parts["alternator"]
            side = np.maximum(alt_dr, rear + base.ALTERNATOR_FRONT_DY - p[:, 1])
            values["r2_alternator"] = smax(side, p[:, 1] - g["alternator_rear_y_mm"], k)
        if s > 0:
            values["r2_fan_cylinder"] = base.cylinder_y_parts(
                p, zf, g["fan_radius_mm"] + g["tip_gap_mm"], rear + CYLINDER_FRONT_DY_R2, base.CYLINDER_END_Y)[0]
        return values, parts

    def wall_sdf(values):
        """The duct before the inlet and outlet planes cut it."""
        union = smin(values["r2_fan_cylinder"], values["plenum_box"], k)
        for name in sorted(values):
            if name.startswith("branch_cone_"):
                union = smin(union, values[name], base.CONE_BLEND_K)
        return smax(union, -values["r2_alternator"], s)

    def fluid_sdf(values):
        return np.maximum(wall_sdf(values), np.maximum(values["inlet_plane"], values["outlet_plane"]))

    base.constituents = constituents
    base.fluid_sdf = fluid_sdf
    base.wall_sdf = wall_sdf
    return base


def constructive_rims(base, g, pitch):
    """The eight rims where the port planes cut the walls, as closed polylines in mm.

    Each rim is star-shaped about its port centre in its plane, so it is found by
    bisection of the wall model along rays, sampled at about ``pitch`` along the rim.
    """
    zf, rear, oz = g["fan_centre_z_mm"], g["fan_rear_y_mm"], g["outlet_z_mm"]
    outer, inner = g["fan_radius_mm"] + g["tip_gap_mm"], g["alternator_radius_mm"]

    def loop(point_at, lo, hi, radius):
        theta = np.linspace(0, 2 * np.pi, int(np.ceil(2 * np.pi * radius / pitch)), endpoint=False)
        lo, hi = np.full(len(theta), float(lo)), np.full(len(theta), float(hi))
        sign = np.sign(base.wall_sdf(base.constituents(point_at(lo, theta), g)[0]))
        if np.any(sign == np.sign(base.wall_sdf(base.constituents(point_at(hi, theta), g)[0]))):
            raise ValueError("A rim is not bracketed along its rays")
        for _ in range(60):
            mid = (lo + hi) / 2
            same = np.sign(base.wall_sdf(base.constituents(point_at(mid, theta), g)[0])) == sign
            lo, hi = np.where(same, mid, lo), np.where(same, hi, mid)
        return point_at((lo + hi) / 2, theta)

    def inlet(rho, theta):
        return np.column_stack((rho * np.cos(theta), np.full(len(theta), rear), zf + rho * np.sin(theta)))

    rims = {"inlet_inner": loop(inlet, 0, (inner + outer) / 2, inner),
            "inlet_outer": loop(inlet, (inner + outer) / 2, outer + 50, outer)}
    h = (base.CONE_START_Z - oz) / (base.CONE_START_Z - (oz + base.CONE_END_DZ))
    for side, s in (("left", -1), ("right", 1)):
        for i, y in enumerate(g["outlet_y_mm"]):
            x = s * (base.CONE_START_X + h * (g["outlet_x_mm"] - base.CONE_START_X))

            def outlet(rho, theta, x=x, y=y):
                return np.column_stack((x + rho * np.cos(theta), y + rho * np.sin(theta), np.full(len(theta), oz)))

            radius = g["outlet_radius_mm"] + base.CONE_START_EXTRA_R
            rims[f"{side}{i + 1}"] = loop(outlet, 0, radius + 20, radius)
    return rims


class _Gzipped:
    """Hands raw STL bytes to the pinned loader, which reads a gzip file."""

    def __init__(self, raw):
        self.raw = raw

    def read_bytes(self):
        return gzip.compress(self.raw, 1)


def admission(base, surface):
    """The rule of audit_mesh_admission.py run(), applied to a surface_audit report."""
    kinds = surface["sharp_edges_by_construction"]
    hard_re_entrant = {k: kinds[k]["re_entrant_length_mm"] for k in base.HARD_RE_ENTRANT if k in kinds}
    creases = kinds.get("smooth_surface_no_constructive_edge", {"edges": 0, "length_mm": 0.0})
    admissible = not any(hard_re_entrant.values()) and creases["edges"] == 0
    return admissible, hard_re_entrant, {"edges": creases["edges"], "length_mm": creases["length_mm"]}


def counted_edges(base, mesh, g, limit=200):
    """Where the edges that the rule counts are: re-entrant at a hard-listed junction, or a crease."""
    angles = np.degrees(mesh.face_adjacency_angles)
    sharp = angles > base.SHARP_DEG
    edges = mesh.face_adjacency_edges[sharp]
    midpoints = mesh.vertices[edges].mean(axis=1)
    lengths = np.linalg.norm(mesh.vertices[edges[:, 0]] - mesh.vertices[edges[:, 1]], axis=1)
    rows = []
    for row, mid, length, angle, salient in zip(base.nearest_junctions(midpoints, g, base.SURFACE_TOL_MM), midpoints,
                                                lengths, angles[sharp], mesh.face_adjacency_convex[sharp]):
        crease = row["construction"] == "smooth_surface_no_constructive_edge"
        if crease or (row["construction"] in base.HARD_RE_ENTRANT and not salient):
            rows.append({"midpoint_mm": [round(float(c), 2) for c in mid], "length_mm": round(float(length), 2),
                         "normal_angle_deg": round(float(angle), 2), "re_entrant": not bool(salient),
                         "construction": row["construction"], "faces": row["faces"],
                         "junction_distance_mm": row["junction_distance_mm"]})
    rows.sort(key=lambda r: -r["normal_angle_deg"])
    return {"count": len(rows), "listed": rows[:limit]}


def run(case, native, study, output, located_case=None):
    if output.exists():
        raise FileExistsError(output)
    base = load_base()
    sha256 = base.sha256
    if sha256(R2_PROGRAM.read_bytes()) != R2_PROGRAM_SHA256:
        raise ValueError("source-r2/Program.cs changed; re-derive the R2 constructive model first")
    card = json.loads(study.read_text())
    g = card["geometry"]
    k, s = blends(g)
    bind_r2_model(base, g)

    preparation = json.loads((case / "preparation.json").read_text())
    raw = (case / "constant/triSurface/duct.stl").read_bytes()
    for label, actual, recorded in (
            ("analysis surface", sha256(raw), preparation["files"]["constant/triSurface/duct.stl"]),
            ("native surface", sha256(native.read_bytes()), preparation["native_surface_sha256"]),
            ("study card", sha256(study.read_bytes()), preparation["study"]["sha256"]),
            ("preparer", sha256((STUDY / "source/prepare_duct_cfd_r2.py").read_bytes()), preparation["source_sha256"]),
            ("constructive model", sha256(Path(__file__).read_bytes()),
             preparation["explicit_feature_edges"]["constructive_model"]["auditor_sha256"])):
        if actual != recorded:
            raise ValueError(f"The {label} is not the one the preparation receipt records")
    generation = json.loads((native.parent / "runtime-receipt.json").read_text())
    if (generation["outputs"][native.name] != preparation["native_surface_sha256"]
            or generation["source_hashes"][str(R2_PROGRAM.relative_to(ROOT))] != R2_PROGRAM_SHA256
            or generation["study"]["sha256"] != preparation["study"]["sha256"]):
        raise ValueError("The native surface was not generated from this card by the pinned R2 generator")

    _, mesh, regions, face_region = base.load_analysis_surface(_Gzipped(raw))
    surface = base.surface_audit(mesh, g, regions, face_region)
    admissible, hard_re_entrant, creases = admission(base, surface)
    counted = counted_edges(base, mesh, g)
    parts = [f"{v:.1f} mm of re-entrant sharp edge at {name}" for name, v in hard_re_entrant.items() if v]
    if creases["edges"]:
        parts.append(f"{creases['edges']} sharp edges ({creases['length_mm']:.1f} mm) that no constructive junction explains")
    reason = ("No re-entrant sharp edge at the union seam or on the alternator, and no sharp edge off a constructive "
              "junction." if admissible else "The surface carries " + "; ".join(parts) + ".")
    report = {
        "status": "r2_surface_audit_admissible" if admissible else "r2_surface_audit_not_admissible",
        "issue": 452,
        "scope": "admission audit of the R2 analysis surface; criteria of audit_mesh_admission.py unchanged",
        "criteria": {"pinned_auditor": {"path": str(BASE_PATH.relative_to(ROOT)), "sha256": BASE_SHA256},
                     "sharp_deg": base.SHARP_DEG, "surface_tol_mm": base.SURFACE_TOL_MM,
                     "hard_re_entrant_kinds": list(base.HARD_RE_ENTRANT),
                     "rule": "no re-entrant sharp-edge length in any hard kind and no sharp edge off a constructive junction",
                     "kind_names": "R1 names kept: in R2 these joins are blended, and a sharp edge there still counts"},
        "generator": {"path": str(R2_PROGRAM.relative_to(ROOT)), "sha256": R2_PROGRAM_SHA256,
                      "reentrant_blend_mm": k, "alternator_subtraction_blend_mm": s,
                      "blend_basis": "unmeasured layout hypothesis chosen for numerical admissibility"},
        "auditor_sha256": sha256(Path(__file__).read_bytes()),
        "study": preparation["study"],
        "native_surface_sha256": preparation["native_surface_sha256"],
        "preparation": {"preparer_sha256": preparation["source_sha256"], "decimation": preparation["decimation"],
                        "explicit_feature_edges": preparation["explicit_feature_edges"]},
        "analysis_surface": {"sha256": sha256(raw), **surface},
        "counted_edges": counted,
        "verdict": {
            "input_admissible_for_settings_sweep": admissible,
            "mesh_admitted": False,
            "flow_solver_started": False,
            "reason": reason,
            "hard_re_entrant_length_mm": hard_re_entrant,
            "creases_off_constructive_junctions": creases,
        },
        "manufacturing_authorized": False,
        "physical_validation": False,
    }
    if located_case is not None:
        report["located_trial"] = locate_trial(base, located_case, mesh, g, raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def locate_trial(base, case, mesh, g, raw):
    """Concave cells and faces of a meshed case, mapped to the constructive junctions."""
    if base.sha256((case / "constant/triSurface/duct.stl").read_bytes()) != base.sha256(raw):
        raise ValueError("The meshed case does not use the audited surface")
    check = base.parse_check_log((case / "log.checkMesh").read_text())
    sets = case / "constant/polyMesh/sets"
    cells = base.read_label_list(sets / "concaveCells") if (sets / "concaveCells").exists() else []
    faces = base.read_label_list(sets / "concaveFaces") if (sets / "concaveFaces").exists() else []
    if len(cells) != (check["concave_cells"] or 0) or len(faces) != (check["concave_angle_faces"] or 0):
        raise ValueError("Written sets disagree with the checkMesh log")
    query = trimesh.proximity.ProximityQuery(mesh)
    located_cells, located_faces = [], []
    if cells:
        centres = base.read_vectors(case / "0/C")[: check["cells"]] * 1000.0
        points = centres[cells]
        located_cells = base.locate(points, g, query.on_surface(points)[1])
        for label, row in zip(cells, located_cells):
            row["cell"] = label
    if faces:
        points = base.read_vectors(case / "constant/polyMesh/points") * 1000.0
        face_points = base.read_faces(case / "constant/polyMesh/faces")
        centres = np.array([points[face_points[f]].mean(axis=0) for f in faces])
        located_faces = base.locate(centres, g, query.on_surface(centres)[1])
    summary = {}
    for row in located_faces:
        summary[row["construction"]] = summary.get(row["construction"], 0) + 1
    return {"checkMesh": check, "concave_cells": located_cells,
            "concave_faces": {"count": len(faces), "by_construction": dict(sorted(summary.items())),
                              "faces": located_faces}}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--case", type=Path, required=True, help="case directory written by prepare_duct_cfd_r2.py")
    parser.add_argument("--native", type=Path, required=True,
                        help="delivery-fluid-domain.stl beside the runtime-receipt.json of source-r2/generate.py")
    parser.add_argument("--study", type=Path, required=True, help="study card the surface was generated from")
    parser.add_argument("--output", type=Path, required=True, help="new JSON report path")
    parser.add_argument("--located-case", type=Path,
                        help="the same case after snappyHexMesh, checkMesh and writeCellCentres")
    args = parser.parse_args()
    report = run(args.case, args.native, args.study, args.output, args.located_case)
    print(json.dumps({k: report[k] for k in ("status", "verdict")}, indent=2))
    print(json.dumps(report["analysis_surface"]["sharp_edges_by_construction"], indent=1))


if __name__ == "__main__":
    main()
