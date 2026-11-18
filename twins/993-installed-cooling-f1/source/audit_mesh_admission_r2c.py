#!/usr/bin/env python3
"""Admission audit of the R2c duct surface, with the criteria of the 2026-11-10 audit (issue #452).

``audit_mesh_admission_r2.py`` is pinned by the R2a and R2b receipts and is not
edited. This script loads it by hash, as it loads ``audit_mesh_admission.py`` by
hash, and reuses its admission rule, its edge locator and the R1 faces,
junction rule, thresholds and surface statistics as they are. It adds only the
constructive fluid model of ``source-r2c/Program.cs`` (pinned by hash), used for
the check that the model describes the surface to within one voxel.

The surface is prepared by the unchanged ``prepare_duct_cfd_r2.py``. Its
explicit feature edges are the port rims of the R2 model of the card; the R2c
change lies far from every port, and this audit checks that the R2c model gives
the same walls at those rims before it accepts them.

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
R2_AUDITOR = STUDY / "source/audit_mesh_admission_r2.py"
R2_AUDITOR_SHA256 = "5b27fd93b1415153619f8acdfe79d8e331b512cb6718f45dec0b6aa730ee991c"
R2C_PROGRAM = STUDY / "source-r2c/Program.cs"
R2C_PROGRAM_SHA256 = "5a041070f97abc285842ed2047d686191832d0dd989bf487354f9e1c79c3ab6f"
PREPARER = STUDY / "source/prepare_duct_cfd_r2.py"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_r2():
    """The pinned R2 auditor as a module of its own; it loads the pinned R1 auditor itself."""
    if sha256(R2_AUDITOR.read_bytes()) != R2_AUDITOR_SHA256:
        raise ValueError("audit_mesh_admission_r2.py changed; the R2c audit is defined on the pinned revision")
    spec = importlib.util.spec_from_file_location("audit_mesh_admission_r2_pinned", R2_AUDITOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corner(v, box, side):
    """Hard Boolean of the three surfaces; v is the distance beyond the shared plane (Program.cs Corner)."""
    return np.minimum(np.maximum(v, -side), np.maximum(box, np.minimum(-side, -v)))


def plane_mean(u, box, side, c):
    """Mean of corner(u - t) over t uniform in [-c, c], exactly (Program.cs PlaneMean).

    corner is piecewise linear in v with breaks at +-side, +-box and 0, so the
    trapezoid rule over the sorted breaks inside the window is exact.
    """
    u, box, side = (np.atleast_1d(np.asarray(a, float)) for a in (u, box, side))
    lo, hi = u - c, u + c
    x = np.stack([lo, hi, -side, side, box, -box, np.zeros_like(u)], axis=1)
    x = np.clip(x, lo[:, None], hi[:, None])
    x.sort(axis=1)
    g = corner(x, box[:, None], side[:, None])
    return ((g[:, 1:] + g[:, :-1]) * 0.5 * np.diff(x, axis=1)).sum(axis=1) / (2 * c)


def corner_blend(g):
    return float(g.get("three_surface_corner_blend_mm", 0))


def bind_r2c_model(r2, base, card_geometry):
    """Give the pinned R1 auditor the fluid model of source-r2c/Program.cs for one study card.

    The R2 model of the card is bound first. Without three_surface_corner_blend_mm
    it is left as it is, as Program.cs keeps the R2 path. With it, ``constituents``
    gains the shared-plane coordinate and the alternator's side, and ``wall_sdf``
    and ``fluid_sdf`` combine them as Program.cs does. FACES, ``face_distances``,
    ``junction_kind`` and every threshold stay the pinned R1 ones.
    """
    r2.bind_r2_model(base, card_geometry)
    k, s = r2.blends(card_geometry)
    c = corner_blend(card_geometry)
    if c <= 0:
        return base
    if not (k == s == c and card_geometry["alternator_rear_y_mm"] == base.CYLINDER_END_Y):
        raise ValueError("The corner blend needs k = s = c and the shared plane y = -5")
    r2_constituents = base.constituents

    def constituents(p, g):
        values, parts = r2_constituents(p, g)
        values = dict(values)
        alt_dr, _ = parts["alternator"]
        values["r2c_alternator_side"] = np.maximum(alt_dr, g["fan_rear_y_mm"] + base.ALTERNATOR_FRONT_DY - p[:, 1])
        values["r2c_shared_plane"] = p[:, 1] - g["alternator_rear_y_mm"]
        return values, parts

    def wall_sdf(values):
        """The duct before the inlet and outlet planes cut it."""
        union = np.maximum(r2.smin(values["r2_fan_cylinder"], values["plenum_box"], k),
                           plane_mean(values["r2c_shared_plane"], values["plenum_box"], values["r2c_alternator_side"], c))
        for name in sorted(values):
            if name.startswith("branch_cone_"):
                union = r2.smin(union, values[name], base.CONE_BLEND_K)
        return union

    def fluid_sdf(values):
        return np.maximum(wall_sdf(values), np.maximum(values["inlet_plane"], values["outlet_plane"]))

    base.constituents = constituents
    base.wall_sdf = wall_sdf
    base.fluid_sdf = fluid_sdf
    return base


def rims_unchanged(r2, g):
    """Largest |R2c wall - R2 wall| on the port rims that the unchanged preparer writes, in mm."""
    r2_model = r2.bind_r2_model(r2.load_base(), g)
    r2c_model = bind_r2c_model(r2, r2.load_base(), g)
    rims = r2.constructive_rims(r2_model, g, g["voxel_mm"])
    points = np.vstack(list(rims.values()))
    old = r2_model.wall_sdf(r2_model.constituents(points, g)[0])
    new = r2c_model.wall_sdf(r2c_model.constituents(points, g)[0])
    return float(np.abs(new - old).max()), len(points)


def run(case, native, study, output):
    if output.exists():
        raise FileExistsError(output)
    r2 = load_r2()
    base = r2.load_base()
    if sha256(R2C_PROGRAM.read_bytes()) != R2C_PROGRAM_SHA256:
        raise ValueError("source-r2c/Program.cs changed; re-derive the R2c constructive model first")
    card = json.loads(study.read_text())
    g = card["geometry"]
    k, s = r2.blends(g)
    c = corner_blend(g)

    preparation = json.loads((case / "preparation.json").read_text())
    raw = (case / "constant/triSurface/duct.stl").read_bytes()
    model = preparation["explicit_feature_edges"]["constructive_model"]
    for label, actual, recorded in (
            ("analysis surface", sha256(raw), preparation["files"]["constant/triSurface/duct.stl"]),
            ("native surface", sha256(native.read_bytes()), preparation["native_surface_sha256"]),
            ("study card", sha256(study.read_bytes()), preparation["study"]["sha256"]),
            ("preparer", sha256(PREPARER.read_bytes()), preparation["source_sha256"]),
            ("rim model auditor", R2_AUDITOR_SHA256, model["auditor_sha256"]),
            ("rim model generator", r2.R2_PROGRAM_SHA256, model["generator_sha256"])):
        if actual != recorded:
            raise ValueError(f"The {label} is not the one the preparation receipt records")
    generation = json.loads((native.parent / "runtime-receipt.json").read_text())
    if (generation["outputs"][native.name] != preparation["native_surface_sha256"]
            or generation["source_hashes"][str(R2C_PROGRAM.relative_to(ROOT))] != R2C_PROGRAM_SHA256
            or generation["study"]["sha256"] != preparation["study"]["sha256"]):
        raise ValueError("The native surface was not generated from this card by the pinned R2c generator")
    rim_change, rim_points = rims_unchanged(r2, g)
    if rim_change > 1e-6:
        raise ValueError("The R2c model moves a port rim; the R2 preparer's feature edges do not apply")

    bind_r2c_model(r2, base, g)
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
        "status": "r2c_surface_audit_admissible" if admissible else "r2c_surface_audit_not_admissible",
        "issue": 452,
        "scope": "admission audit of the R2c analysis surface; criteria of audit_mesh_admission.py unchanged",
        "criteria": {"pinned_auditor": {"path": str(r2.BASE_PATH.relative_to(ROOT)), "sha256": r2.BASE_SHA256},
                     "pinned_r2_auditor": {"path": str(R2_AUDITOR.relative_to(ROOT)), "sha256": R2_AUDITOR_SHA256},
                     "sharp_deg": base.SHARP_DEG, "surface_tol_mm": base.SURFACE_TOL_MM,
                     "hard_re_entrant_kinds": list(base.HARD_RE_ENTRANT),
                     "rule": "no re-entrant sharp-edge length in any hard kind and no sharp edge off a constructive junction",
                     "kind_names": "R1 names kept: in R2c these joins are blended, and a sharp edge there still counts"},
        "generator": {"path": str(R2C_PROGRAM.relative_to(ROOT)), "sha256": R2C_PROGRAM_SHA256,
                      "reentrant_blend_mm": k, "alternator_subtraction_blend_mm": s,
                      "three_surface_corner_blend_mm": c,
                      "blend_basis": "unmeasured layout hypothesis chosen for numerical admissibility"},
        "auditor_sha256": sha256(Path(__file__).read_bytes()),
        "study": preparation["study"],
        "native_surface_sha256": preparation["native_surface_sha256"],
        "preparation": {"preparer_sha256": preparation["source_sha256"], "decimation": preparation["decimation"],
                        "explicit_feature_edges": preparation["explicit_feature_edges"],
                        "rims_under_r2c_model": {
                            "meaning": "largest |R2c wall - R2 wall| at the rim points the R2 preparer writes",
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
                        help="delivery-fluid-domain.stl beside the runtime-receipt.json of source-r2c/generate.py")
    parser.add_argument("--study", type=Path, required=True, help="study card the surface was generated from")
    parser.add_argument("--output", type=Path, required=True, help="new JSON report path")
    args = parser.parse_args()
    report = run(args.case, args.native, args.study, args.output)
    print(json.dumps({k: report[k] for k in ("status", "verdict")}, indent=2))
    print(json.dumps(report["analysis_surface"]["sharp_edges_by_construction"], indent=1))


if __name__ == "__main__":
    main()
