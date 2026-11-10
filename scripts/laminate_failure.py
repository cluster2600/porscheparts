#!/usr/bin/env python3
"""Per-ply failure post-processing for a laminate: lamination theory and four criteria.

CalculiX solves a laminated shell but has no composite failure criterion
(docs/MONOCOQUE_964_993_COMPUTATION_CHAIN.md, section 2). This module supplies
the missing step for in-plane ply stresses:

* classical lamination theory: ply stiffness, the ABD matrix, and the stresses
  of every ply in its material axes for given force and moment resultants;
* four first-ply-failure criteria on those stresses: maximum stress, Tsai-Wu,
  Hashin (1980, plane stress) and Puck inter-fibre failure (modes A, B, C).

Each criterion returns a *reserve factor*: the number the applied stresses must
be multiplied by to reach the criterion. Below 1 the ply has failed by that
criterion. Reserve factors are comparable between criteria; raw indices are not.

Units are the caller's, used consistently: MPa and mm give N/mm for force
resultants and N for moment resultants per unit width.

It carries no material data. Every stiffness, strength and criterion parameter
is an input that needs its own cited source, for the actual fibre, resin,
fibre volume fraction, cure and test standard. It covers neither delamination
and interlaminar stresses, nor progressive damage, nor crash, nor buckling.
A reserve factor computed here is arithmetic on stated numbers, never a
strength claim for a part (AGENTS.md, SAFETY.md, ADR 0018).
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

STIFFNESS_KEYS = ("E1", "E2", "G12", "nu12")
STRENGTH_KEYS = ("Xt", "Xc", "Yt", "Yc", "S")     # all positive magnitudes


def reduced_stiffness(E1, E2, G12, nu12):
    """Plane-stress stiffness of a unidirectional ply in its material axes."""
    nu21 = nu12 * E2 / E1
    d = 1.0 - nu12 * nu21
    return np.array([[E1 / d, nu12 * E2 / d, 0.0], [nu12 * E2 / d, E2 / d, 0.0], [0.0, 0.0, G12]])


def _stress_rotation(angle_deg):
    """Matrix taking (sx, sy, txy) in laminate axes to (s1, s2, t12) in axes turned by the ply angle."""
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return np.array([[c * c, s * s, 2 * c * s], [s * s, c * c, -2 * c * s], [-c * s, c * s, c * c - s * s]])


_REUTER = np.diag([1.0, 1.0, 2.0])               # engineering to tensor shear strain


def to_material_axes(stress_xy, angle_deg):
    return _stress_rotation(angle_deg) @ np.asarray(stress_xy, dtype=float)


def rotated_stiffness(Q, angle_deg):
    """Ply stiffness in laminate axes, relating engineering strains to stresses."""
    T = _stress_rotation(angle_deg)
    return np.linalg.inv(T) @ Q @ _REUTER @ T @ np.linalg.inv(_REUTER)


def _interfaces(layup):
    thickness = np.array([ply["thickness"] for ply in layup], dtype=float)
    if np.any(thickness <= 0):
        raise ValueError("ply thickness must be positive")
    return np.concatenate([[0.0], np.cumsum(thickness)]) - thickness.sum() / 2


def abd(layup):
    """A, B, D of a layup listed from the bottom face (z < 0) to the top."""
    z = _interfaces(layup)
    A, B, D = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
    for k, ply in enumerate(layup):
        Qbar = rotated_stiffness(reduced_stiffness(*(ply["stiffness"][key] for key in STIFFNESS_KEYS)), ply["angle_deg"])
        A += Qbar * (z[k + 1] - z[k])
        B += Qbar * (z[k + 1] ** 2 - z[k] ** 2) / 2
        D += Qbar * (z[k + 1] ** 3 - z[k] ** 3) / 3
    return A, B, D


def ply_stresses(layup, N, M=(0.0, 0.0, 0.0)):
    """Stresses in material axes at the bottom and top face of every ply.

    ``N`` and ``M`` are the force and moment resultants per unit width, in
    laminate axes. Returns the mid-plane strains, the curvatures and one row
    per ply face.
    """
    A, B, D = abd(layup)
    response = np.linalg.solve(np.block([[A, B], [B, D]]), np.concatenate([N, M]).astype(float))
    strain0, curvature = response[:3], response[3:]
    z = _interfaces(layup)
    rows = []
    for k, ply in enumerate(layup):
        Q = reduced_stiffness(*(ply["stiffness"][key] for key in STIFFNESS_KEYS))
        Qbar = rotated_stiffness(Q, ply["angle_deg"])
        for face, height in (("bottom", z[k]), ("top", z[k + 1])):
            stress = to_material_axes(Qbar @ (strain0 + height * curvature), ply["angle_deg"])
            rows.append({"ply": k, "angle_deg": ply["angle_deg"], "face": face, "z": float(height),
                         "stress": [float(v) for v in stress]})
    return strain0, curvature, rows


# --- criteria: each takes (s1, s2, t12) and returns {"reserve", "mode", "index"} ---

def _positive_root(a, b):
    """R > 0 with a R^2 + b R = 1, for a >= 0."""
    if a <= 0:
        return math.inf if b <= 0 else 1.0 / b
    return (-b + math.sqrt(b * b + 4 * a)) / (2 * a)


def _result(reserves, indices=None):
    mode = min(reserves, key=reserves.get)
    out = {"reserve": reserves[mode], "mode": mode}
    if indices is not None:
        out["index"] = indices
    return out


def max_stress(stress, strength):
    s1, s2, t12 = stress
    ratio = {"fibre_tension": max(s1, 0) / strength["Xt"], "fibre_compression": max(-s1, 0) / strength["Xc"],
             "matrix_tension": max(s2, 0) / strength["Yt"], "matrix_compression": max(-s2, 0) / strength["Yc"],
             "shear": abs(t12) / strength["S"]}
    return _result({k: math.inf if v == 0 else 1.0 / v for k, v in ratio.items()}, ratio)


def tsai_wu(stress, strength, f12_star):
    """Tsai-Wu with the interaction term F12 = f12_star * sqrt(F11 F22). ``f12_star`` must be stated."""
    if not -1.0 < f12_star < 1.0:
        raise ValueError("f12_star must lie in (-1, 1) for a closed failure surface")
    s1, s2, t12 = stress
    F1, F2 = 1 / strength["Xt"] - 1 / strength["Xc"], 1 / strength["Yt"] - 1 / strength["Yc"]
    F11, F22, F66 = 1 / (strength["Xt"] * strength["Xc"]), 1 / (strength["Yt"] * strength["Yc"]), 1 / strength["S"] ** 2
    linear = F1 * s1 + F2 * s2
    quadratic = F11 * s1 ** 2 + F22 * s2 ** 2 + F66 * t12 ** 2 + 2 * f12_star * math.sqrt(F11 * F22) * s1 * s2
    return {"reserve": _positive_root(quadratic, linear), "mode": "interactive", "index": linear + quadratic}


def hashin(stress, strength, St):
    """Hashin 1980, plane stress. ``St`` is the transverse shear strength and must be stated."""
    s1, s2, t12 = stress
    shear = (t12 / strength["S"]) ** 2
    reserves = {}
    if s1 >= 0:
        reserves["fibre_tension"] = _positive_root((s1 / strength["Xt"]) ** 2 + shear, 0.0)
    else:
        reserves["fibre_compression"] = strength["Xc"] / -s1
    if s2 >= 0:
        reserves["matrix_tension"] = _positive_root((s2 / strength["Yt"]) ** 2 + shear, 0.0)
    else:
        reserves["matrix_compression"] = _positive_root(
            (s2 / (2 * St)) ** 2 + shear, ((strength["Yc"] / (2 * St)) ** 2 - 1.0) * s2 / strength["Yc"])
    return _result(reserves)


def puck_inter_fibre(stress, strength, p_plus, p_minus):
    """Puck inter-fibre failure for plane stress (Puck and Schuermann 2002; VDI 2014 Part 3).

    ``p_plus`` and ``p_minus`` are the inclination parameters of the fracture
    curve at zero transverse stress, on the tension and compression side. They
    are material inputs and must be stated. The stress exposure is homogeneous
    of degree one, so the reserve factor is its inverse. Weakening of the
    matrix by fibre-parallel stress is not included.
    """
    _, s2, t = stress
    S, Yt, Yc = strength["S"], strength["Yt"], strength["Yc"]
    Ra = S / (2 * p_minus) * (math.sqrt(1 + 2 * p_minus * Yc / S) - 1)     # resistance of the action plane to transverse shear
    p_tt = p_minus * Ra / S
    t_c = S * math.sqrt(1 + 2 * p_tt)                                       # shear at the change from mode B to C
    if s2 >= 0:
        mode, exposure = "A", math.sqrt((t / S) ** 2 + (1 - p_plus * Yt / S) ** 2 * (s2 / Yt) ** 2) + p_plus * s2 / S
    elif abs(t) * Ra >= -s2 * t_c:
        mode, exposure = "B", (math.sqrt(t * t + (p_minus * s2) ** 2) + p_minus * s2) / S
    else:
        mode, exposure = "C", ((t / (2 * (1 + p_tt) * S)) ** 2 + (s2 / Yc) ** 2) * Yc / -s2
    return {"reserve": math.inf if exposure == 0 else 1.0 / exposure, "mode": mode, "index": exposure}


def assess(layup, N, M=(0.0, 0.0, 0.0), ply_stress_rows=None):
    """Reserve factors of every ply face, and the first ply to fail by each criterion.

    Each ply needs ``strength`` (Xt, Xc, Yt, Yc, S). A criterion is evaluated
    only where its own parameters are stated: ``tsai_wu_f12_star``,
    ``hashin_St``, ``puck_p_plus`` with ``puck_p_minus``. ``ply_stress_rows``
    replaces lamination theory by stresses from another solver, as rows of
    ``{"ply", "face", "stress": [s1, s2, t12]}`` in material axes.
    """
    if ply_stress_rows is None:
        strain0, curvature, rows = ply_stresses(layup, np.asarray(N, dtype=float), np.asarray(M, dtype=float))
        source = {"method": "classical lamination theory", "mid_plane_strain": strain0.tolist(),
                  "curvature": curvature.tolist()}
    else:
        rows, source = [dict(r) for r in ply_stress_rows], {"method": "ply stresses supplied by the caller"}
    first = {}
    for row in rows:
        ply = layup[row["ply"]]
        strength = ply["strength"]
        if any(strength[key] <= 0 for key in STRENGTH_KEYS):
            raise ValueError("strengths are positive magnitudes")
        criteria = {"max_stress": max_stress(row["stress"], strength)}
        if "tsai_wu_f12_star" in ply:
            criteria["tsai_wu"] = tsai_wu(row["stress"], strength, ply["tsai_wu_f12_star"])
        if "hashin_St" in ply:
            criteria["hashin"] = hashin(row["stress"], strength, ply["hashin_St"])
        if "puck_p_plus" in ply and "puck_p_minus" in ply:
            criteria["puck_inter_fibre"] = puck_inter_fibre(row["stress"], strength, ply["puck_p_plus"], ply["puck_p_minus"])
        row["criteria"] = criteria
        for name, result in criteria.items():
            if name not in first or result["reserve"] < first[name]["reserve"]:
                first[name] = {"reserve": result["reserve"], "mode": result["mode"], "ply": row["ply"],
                               "face": row.get("face")}
    return {"schema": "laminate-failure/1", "source": source, "first_ply_failure": first, "ply_faces": rows,
            "claims": "arithmetic on the stated stiffness, strength and criterion parameters; in-plane first-ply "
                      "failure only; no delamination, progressive damage, crash or material qualification"}


def _finite(value):
    """JSON has no infinity: an unloaded mode reports null."""
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite(v) for v in value]
    return None if isinstance(value, float) and math.isinf(value) else value


def main():
    ap = argparse.ArgumentParser(description="Per-ply first-ply-failure reserve factors of a laminate.")
    ap.add_argument("case", type=Path, help='JSON: {"materials": {name: {"stiffness", "strength", criterion parameters}}, '
                                            '"layup": [{"material", "angle_deg", "thickness"}], "N": [..], "M": [..]} '
                                            'and optionally "ply_stresses"')
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    case = json.loads(args.case.read_text())
    layup = [{**case["materials"][ply["material"]], "angle_deg": ply["angle_deg"], "thickness": ply["thickness"]}
             for ply in case["layup"]]
    report = assess(layup, case.get("N", (0, 0, 0)), case.get("M", (0, 0, 0)), case.get("ply_stresses"))
    report["case"] = args.case.name
    args.output.write_text(json.dumps(_finite(report), indent=2) + "\n")
    for name, result in report["first_ply_failure"].items():
        print(f"{name}: reserve {result['reserve']:.4g} ({result['mode']}, ply {result['ply']} {result['face']})")


if __name__ == "__main__":
    main()
