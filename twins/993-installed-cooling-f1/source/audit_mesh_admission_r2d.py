#!/usr/bin/env python3
"""Admission audit of the R2d duct surface, with the criteria of the 2026-11-10 audit (issue #452).

``audit_mesh_admission_r2c.py`` is pinned by the R2c receipts and is not edited.
This script loads it by hash; it loads ``audit_mesh_admission_r2.py`` by hash,
which loads ``audit_mesh_admission.py`` by hash. The admission rule, the edge
locator, the R1 faces, junction rule, thresholds and surface statistics are
reused as they are. Only the constructive fluid model of ``source-r2d/Program.cs``
(pinned by hash) is added: the R2c plane mean, averaged again over the
alternator side's position.

The surface is prepared by the unchanged ``prepare_duct_cfd_r2.py``. Its
explicit feature edges are the port rims of the R2 model of the card; this
audit checks that the R2d model gives the same walls at those rims.

No mesh trial is located here: the audit decides whether one may start.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]
R2C_AUDITOR = STUDY / "source/audit_mesh_admission_r2c.py"
R2C_AUDITOR_SHA256 = "c7aefcb433147ca88a48ed2921822d1efceff5541eb4ba2e7a4ea0948b4e1d06"
R2D_PROGRAM = STUDY / "source-r2d/Program.cs"
R2D_PROGRAM_SHA256 = "40667099267608948dd33fd61f6c880ea35d756e0b72e330de5b2bc907c1991e"
PREPARER = STUDY / "source/prepare_duct_cfd_r2.py"
SIDE_POSITIONS = 24            # Program.cs SidePositions


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_r2c():
    """The pinned R2c auditor as a module of its own; it loads the pinned R2 and R1 auditors."""
    if sha256(R2C_AUDITOR.read_bytes()) != R2C_AUDITOR_SHA256:
        raise ValueError("audit_mesh_admission_r2c.py changed; the R2d audit is defined on the pinned revision")
    spec = importlib.util.spec_from_file_location("audit_mesh_admission_r2c_pinned", R2C_AUDITOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def line_blend(g):
    return float(g.get("corner_line_blend_mm", 0))


def side_mean(r2c, u, box, side, c, a, n=SIDE_POSITIONS):
    """Program.cs SideMean: the R2c plane mean averaged over the side moved by t2 in [-a, a].

    Where every side break stays outside the plane's window and the kink at
    side = -box stays outside the side's range, the plane mean is affine in the
    side and the mean is its value at the side itself, as Program.cs takes it.
    """
    u, box, side = (np.atleast_1d(np.asarray(v, float)) for v in (u, box, side))
    out = r2c.plane_mean(u, box, side, c)
    full = ~((np.abs(side - u) > a + c) & (np.abs(side + u) > a + c) & (np.abs(side + box) > a))
    if full.any():
        t = -a + (np.arange(n) + 0.5) * (2 * a / n)
        out[full] = np.mean([r2c.plane_mean(u[full], box[full], side[full] + ti, c) for ti in t], axis=0)
    return out


def bind_r2d_model(r2c, r2, base, card_geometry):
    """Give the pinned R1 auditor the fluid model of source-r2d/Program.cs for one study card.

    The R2c model of the card is bound first; without corner_line_blend_mm it is
    left as it is, as Program.cs keeps the R2c path. With it, only ``wall_sdf``
    and ``fluid_sdf`` change: the plane mean becomes the side mean. FACES,
    ``face_distances``, ``junction_kind`` and every threshold stay the pinned R1 ones.
    """
    r2c.bind_r2c_model(r2, base, card_geometry)
    a = line_blend(card_geometry)
    if a <= 0:
        return base
    k, _ = r2.blends(card_geometry)
    c = r2c.corner_blend(card_geometry)
    if not (c > 0 and a == c):
        raise ValueError("The corner line blend needs the corner blend and a = c")

    def wall_sdf(values):
        union = np.maximum(r2.smin(values["r2_fan_cylinder"], values["plenum_box"], k),
                           side_mean(r2c, values["r2c_shared_plane"], values["plenum_box"],
                                     values["r2c_alternator_side"], c, a))
        for name in sorted(values):
            if name.startswith("branch_cone_"):
                union = r2.smin(union, values[name], base.CONE_BLEND_K)
        return union

    def fluid_sdf(values):
        return np.maximum(wall_sdf(values), np.maximum(values["inlet_plane"], values["outlet_plane"]))

    base.wall_sdf = wall_sdf
    base.fluid_sdf = fluid_sdf
    return base


def rims_unchanged(r2c, r2, g):
    """Largest |R2d wall - R2 wall| on the port rims that the unchanged preparer writes, in mm."""
    r2_model = r2.bind_r2_model(r2.load_base(), g)
    r2d_model = bind_r2d_model(r2c, r2, r2.load_base(), g)
    rims = r2.constructive_rims(r2_model, g, g["voxel_mm"])
    points = np.vstack(list(rims.values()))
    old = r2_model.wall_sdf(r2_model.constituents(points, g)[0])
    new = r2d_model.wall_sdf(r2d_model.constituents(points, g)[0])
    return float(np.abs(new - old).max()), len(points)


def run(case, native, study, output):
    if output.exists():
        raise FileExistsError(output)
    r2c = load_r2c()
    r2 = r2c.load_r2()
    base = r2.load_base()
    if sha256(R2D_PROGRAM.read_bytes()) != R2D_PROGRAM_SHA256:
        raise ValueError("source-r2d/Program.cs changed; re-derive the R2d constructive model first")
    card = json.loads(study.read_text())
    g = card["geometry"]
    k, s = r2.blends(g)
    c, a = r2c.corner_blend(g), line_blend(g)

    preparation = json.loads((case / "preparation.json").read_text())
    raw = (case / "constant/triSurface/duct.stl").read_bytes()
    model = preparation["explicit_feature_edges"]["constructive_model"]
    for label, actual, recorded in (
            ("analysis surface", sha256(raw), preparation["files"]["constant/triSurface/duct.stl"]),
            ("native surface", sha256(native.read_bytes()), preparation["native_surface_sha256"]),
            ("study card", sha256(study.read_bytes()), preparation["study"]["sha256"]),
            ("preparer", sha256(PREPARER.read_bytes()), preparation["source_sha256"]),
            ("rim model auditor", r2c.R2_AUDITOR_SHA256, model["auditor_sha256"]),
            ("rim model generator", r2.R2_PROGRAM_SHA256, model["generator_sha256"])):
        if actual != recorded:
            raise ValueError(f"The {label} is not the one the preparation receipt records")
    generation = json.loads((native.parent / "runtime-receipt.json").read_text())
    if (generation["outputs"][native.name] != preparation["native_surface_sha256"]
            or generation["source_hashes"][str(R2D_PROGRAM.relative_to(ROOT))] != R2D_PROGRAM_SHA256
            or generation["study"]["sha256"] != preparation["study"]["sha256"]):
        raise ValueError("The native surface was not generated from this card by the pinned R2d generator")
    rim_change, rim_points = rims_unchanged(r2c, r2, g)
    if rim_change > 1e-6:
        raise ValueError("The R2d model moves a port rim; the R2 preparer's feature edges do not apply")

    bind_r2d_model(r2c, r2, base, g)
    _, mesh, regions, face_region = base.load_analysis_surface(r2._Gzipped(raw))
    surface = base.surface_audit(mesh, g, regions, face_region)
    admissible, hard_re_entrant, creases = r2.admission(base, surface)
    counted = r2.counted_edges(base, mesh, g)
    parts = [f"{v:.1f} mm of re-entrant sharp edge at {name}" for name, v in hard_re_entrant.items() if v]
    if creases["edges"]:
        parts.append(f"{creases['edges']} sharp edges ({creases['length_mm']:.1f} mm) that no constructive junction explains")
    reason = ("No re-entrant sharp edge at the union seam or on the alternator, and no sharp edge off a constructive "
              "junction." if admissible else "The surface carries " + "; ".join(parts) + ".")
    report = {
        "status": "r2d_surface_audit_admissible" if admissible else "r2d_surface_audit_not_admissible",
        "issue": 452,
        "scope": "admission audit of the R2d analysis surface; criteria of audit_mesh_admission.py unchanged",
        "criteria": {"pinned_auditor": {"path": str(r2.BASE_PATH.relative_to(ROOT)), "sha256": r2.BASE_SHA256},
                     "pinned_r2_auditor": {"path": str(r2c.R2_AUDITOR.relative_to(ROOT)), "sha256": r2c.R2_AUDITOR_SHA256},
                     "pinned_r2c_auditor": {"path": str(R2C_AUDITOR.relative_to(ROOT)), "sha256": R2C_AUDITOR_SHA256},
                     "sharp_deg": base.SHARP_DEG, "surface_tol_mm": base.SURFACE_TOL_MM,
                     "hard_re_entrant_kinds": list(base.HARD_RE_ENTRANT),
                     "rule": "no re-entrant sharp-edge length in any hard kind and no sharp edge off a constructive junction",
                     "kind_names": "R1 names kept: in R2d these joins are blended, and a sharp edge there still counts"},
        "generator": {"path": str(R2D_PROGRAM.relative_to(ROOT)), "sha256": R2D_PROGRAM_SHA256,
                      "reentrant_blend_mm": k, "alternator_subtraction_blend_mm": s,
                      "three_surface_corner_blend_mm": c, "corner_line_blend_mm": a,
                      "side_positions": SIDE_POSITIONS,
                      "blend_basis": "unmeasured layout hypothesis chosen for numerical admissibility"},
        "auditor_sha256": sha256(Path(__file__).read_bytes()),
        "study": preparation["study"],
        "native_surface_sha256": preparation["native_surface_sha256"],
        "preparation": {"preparer_sha256": preparation["source_sha256"], "decimation": preparation["decimation"],
                        "explicit_feature_edges": preparation["explicit_feature_edges"],
                        "rims_under_r2d_model": {
                            "meaning": "largest |R2d wall - R2 wall| at the rim points the R2 preparer writes",
                            "max_mm": rim_change, "points": rim_points}},
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--case", type=Path, required=True, help="case directory written by prepare_duct_cfd_r2.py")
    parser.add_argument("--native", type=Path, required=True,
                        help="delivery-fluid-domain.stl beside the runtime-receipt.json of source-r2d/generate.py")
    parser.add_argument("--study", type=Path, required=True, help="study card the surface was generated from")
    parser.add_argument("--output", type=Path, required=True, help="new JSON report path")
    args = parser.parse_args()
    report = run(args.case, args.native, args.study, args.output)
    print(json.dumps({k: report[k] for k in ("status", "verdict")}, indent=2))
    print(json.dumps(report["analysis_surface"]["sharp_edges_by_construction"], indent=1))


if __name__ == "__main__":
    main()
