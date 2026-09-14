#!/usr/bin/env python3
"""Mesure des interfaces visibles sur le scan de culasse billet 935 (niveau C).

Usage :
    python measure_interfaces.py /chemin/local/935+Xtreme+Cyl+head.obj \
        --output twins/m64-cylinder-head/evidence/scan935-interfaces-20260914.json

Le scan et tout dérivé géométrique restent hors Git (instruction du
propriétaire). Ce script n'écrit que des nombres, des méthodes et des
empreintes. Il refuse tout fichier dont le SHA-256 diffère de la fiche
catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json.

Toutes les grandeurs sont en unités OBJ. L'échelle « mm » est jugée
cohérente par recoupement (voir ``scale_assessment``) mais n'est pas
étalonnée. Aucune valeur n'est une cote M64.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_primitives as fp  # noqa: E402

EXPECTED_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
STATUS = "measured_on_935_scan_evidence_C"
UNIT = "obj_unit_mm_coherent_not_calibrated"

# Repère provisoire A/B/C repris de
# twins/reference-935-cylinder-head/source/scan_frame.py (facettes planes).
C_AXIS = np.array([0.09216808492652868, -0.8170262691134965, -0.5691863664033568])
B_HINT = np.array([-0.66828442, 0.37015754, -0.64527462])
A_AXIS = np.cross(B_HINT, C_AXIS)
A_AXIS /= np.linalg.norm(A_AXIS)
B_AXIS = np.cross(C_AXIS, A_AXIS)
B_AXIS /= np.linalg.norm(B_AXIS)
FRAME_ABC = np.vstack((A_AXIS, B_AXIS, C_AXIS))

# Graines de région en coordonnées A/B/C, issues de l'exploration par coupes
# (voir le rapport). Elles ne fixent que l'endroit où chercher.
SEEDS = {
    "chamber_centre_AB": (128.0, -169.0),
    "seal_face_C": -87.0,
    "recess_floor_C": -89.0,
    "head_studs_ABC": [(84.8, -125.9, -95.0), (171.3, -125.6, -95.0),
                       (171.5, -211.2, -95.0), (85.3, -211.6, -95.0)],
    "spark_plugs_ABC": [(101.4, -171.0, -115.0), (154.8, -174.6, -115.0)],
    "valve_bucket_bores": [
        {"seed": (127.7, -111.5, -170.0), "axis_hint": (0.0, -0.49, 0.87)},
        {"seed": (127.4, -236.0, -170.0), "axis_hint": (0.0, 0.49, 0.87)},
    ],
    # goujons saillants (boule 9) ou trous visibles seulement près de la face (boule 5)
    "flange_low_B": {"plane_B": -251.5, "port_slab_B": -245.0,
                     "studs_ABC_ball": [((104.5, -262.0, -98.0), 9.0), ((150.5, -262.0, -145.1), 9.0),
                                        ((104.1, -248.6, -144.8), 5.0), ((151.1, -248.9, -98.2), 5.0)]},
    "flange_high_B": {"plane_B": -62.0,
                      "studs_ABC_ball": [((113.9, -50.0, -104.1), 9.0), ((141.6, -50.0, -164.1), 9.0)]},
    "carrier_face_C": -173.8,
}


# ------------------------------------------------------------------ E/S
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    with path.open() as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append(line[2:])
            elif line.startswith("f "):
                faces.append([int(tok.split("/")[0]) for tok in line.split()[1:4]])
    return np.loadtxt(vertices), np.asarray(faces, dtype=np.int64) - 1


def vertex_normals(points, faces):
    tri = points[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    out = np.zeros_like(points)
    for k in range(3):
        np.add.at(out, faces[:, k], n)
    return out / np.maximum(np.linalg.norm(out, axis=1), 1e-12)[:, None]


def r3(x):
    return None if x is None else float(round(float(x), 3))


def vec(x, nd=4):
    return [float(round(float(v), nd)) for v in x]


def combine(boot, spread):
    return r3(np.sqrt(boot ** 2 + (spread / 2.0) ** 2))


def measurement(value, uncertainty, method, region, quality, **extra):
    item = {"value": value, "uncertainty_k1": uncertainty, "unit": UNIT,
            "method": method, "region": region, "quality": quality, "status": STATUS}
    item.update(extra)
    return item


def not_measurable(reason, **extra):
    item = {"value": None, "status": "not_measurable_on_935_scan", "reason": reason}
    item.update(extra)
    return item


# ------------------------------------------------------------------ primitives réutilisables (testées)
def fit_axis_hole(points, seed, axis_hint, ball, radius_range, normals=None, threshold=0.3):
    """Perçage/alésage près d'une graine : cylindre RANSAC puis stats.

    ``centre_xy`` est l'intersection de l'axe avec le plan z = 0 du repère des
    points (plan d'étanchéité dans le repère local).
    """
    pts = np.asarray(points, float)
    seed = np.asarray(seed, float)
    m = np.linalg.norm(pts - seed, axis=1) < ball
    q = pts[m]
    axis = np.asarray(axis_hint, float)
    if normals is not None:
        nq = normals[m]
        if axis_hint is None:
            _, vecs = np.linalg.eigh(nq.T @ nq)
            axis = vecs[:, 0]
        q = q[np.abs(nq @ axis) < 0.35]
    axis = axis / np.linalg.norm(axis)
    u, v = fp.orthonormal_basis(axis)
    xy = (q - seed) @ np.column_stack((u, v))
    _, _, inl = fp.ransac_circle(xy, 0.4, radius_range=radius_range)
    o, a, r, res, inl3 = fp.ransac_cylinder(q[inl], axis, threshold, radius_range=radius_range)
    sel = q[inl][inl3]
    t = (sel - o) @ a
    boot = fp.bootstrap(lambda d: 2 * fp.fit_cylinder(d, a, iterations=10)[2], sel, n=30)
    centre_z0 = o - (o[2] / a[2]) * a if abs(a[2]) > 1e-6 else o
    return {
        "centre_xy": [float(centre_z0[0]), float(centre_z0[1])],
        "axis_point": o.tolist(), "axis": a.tolist(), "diameter": float(2 * r),
        "diameter_bootstrap_sd": float(boot[0]), "axial_extent": float(np.ptp(t)),
        "t_range": [float(t.min()), float(t.max())], **fp.residual_stats(res),
    }


def pattern_summary(centres):
    c = np.asarray(centres, float)
    d = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2)
    iu = np.triu_indices(len(c), 1)
    return {"count": int(len(c)), "span_x": float(np.ptp(c[:, 0])), "span_y": float(np.ptp(c[:, 1])),
            "centroid": c.mean(axis=0).tolist(), "pair_distances": sorted(float(x) for x in d[iu])}


def _grid_clusters(xy, cell=0.8):
    key = np.floor(xy / cell).astype(np.int64)
    keys, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    index = {tuple(k): i for i, k in enumerate(keys)}
    parent = list(range(len(keys)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, k in enumerate(keys):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                j = index.get((k[0] + dx, k[1] + dy))
                if j is not None:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[ri] = rj
    return np.array([find(i) for i in range(len(keys))])[inv]


def circles_in_slab(xy, radius_range=(1.5, 30.0), min_points=30, min_coverage=250.0):
    """Cercles fermés dans une tranche 2D (amas de points connexes)."""
    xy = np.asarray(xy, float)
    labels = _grid_clusters(xy)
    found = []
    for label in np.unique(labels):
        pts = xy[labels == label]
        if len(pts) < min_points or np.ptp(pts, axis=0).max() > 2.2 * radius_range[1]:
            continue
        c, r = fp.fit_circle_geometric(pts)
        if not radius_range[0] <= r <= radius_range[1]:
            continue
        stats = fp.residual_stats(fp.circle_residuals(pts, c, r))
        coverage = fp.angular_coverage_deg(pts, c)
        if stats["p95"] < 0.25 * r and coverage >= min_coverage:
            found.append({"centre": c.tolist(), "diameter": float(2 * r), "coverage_deg": coverage, **stats})
    return found


# ------------------------------------------------------------------ mesures
def seal_plane(P):
    cen = np.asarray(SEEDS["chamber_centre_AB"])
    rad = np.linalg.norm(P[:, :2] - cen, axis=1)
    ref = np.array([0, 0, 1.0])
    m = (np.abs(P[:, 2] - SEEDS["seal_face_C"]) < 0.8) & (rad > 58.5) & (rad < 75)
    region = P[m]
    c, n, inl = fp.ransac_plane(region, 0.15, reference_normal=ref, max_angle_deg=5)
    res = fp.plane_residuals(region[inl], c, n)
    variants = []
    for thr in (0.10, 0.15, 0.25):
        for r0, r1 in ((58.5, 75), (60, 70), (62, 75)):
            mm = (np.abs(P[:, 2] - SEEDS["seal_face_C"]) < 0.8) & (rad > r0) & (rad < r1)
            cc, nn, _ = fp.ransac_plane(P[mm], thr, reference_normal=ref, max_angle_deg=5)
            variants.append((cc, nn))
    ang = np.array([np.arctan2(*(region[inl][:, :2] - cen).T[::-1])]).ravel()
    sectors = []
    for k in range(4):
        sel = region[inl][(np.floor((ang + np.pi) / (np.pi / 2)).astype(int) % 4) == k]
        cs, ns = fp.fit_plane_lsq(sel)
        ns = ns if ns @ n > 0 else -ns
        sectors.append((cs, ns, len(sel)))
    offsets = [float(cc @ n - c @ n) for cc, _ in variants]
    angles = [fp.angle_between_deg(nn, n) for _, nn in variants + [(s[0], s[1]) for s in sectors]]
    sector_offsets = [float(fp.plane_residuals(s[0][None, :], c, n)[0]) for s in sectors]
    return c, n, {
        "points_in_region": int(len(region)), "inliers": int(inl.sum()),
        "inlier_fraction": r3(inl.mean()), **{k: r3(v) for k, v in fp.residual_stats(res).items() if k != "points"},
        "peak_to_valley_inliers": r3(np.ptp(res)),
        "sensitivity_offset_range": r3(np.ptp(offsets)), "sensitivity_normal_max_deg": r3(max(angles)),
        "sector_centroid_offsets": [r3(x) for x in sector_offsets],
        "normal_tilt_vs_provisional_C_deg": r3(fp.angle_between_deg(n, ref)),
    }


def local_frame(seal_centroid, normal, centre_ab):
    z = normal / np.linalg.norm(normal)
    x = np.array([1.0, 0, 0]) - z[0] * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    centre = np.array([centre_ab[0], centre_ab[1], 0.0])
    centre[2] = seal_centroid[2] - (z[0] * (centre[0] - seal_centroid[0]) + z[1] * (centre[1] - seal_centroid[1])) / z[2]
    return centre, np.vstack((x, y, z))


def circle_band(L, z0, z1, r0, r1, thr=0.2):
    rad = np.linalg.norm(L[:, :2], axis=1)
    m = (L[:, 2] > z0) & (L[:, 2] < z1) & (rad > r0) & (rad < r1)
    xy = L[m][:, :2]
    c, r, inl = fp.ransac_circle(xy, thr, radius_range=(r0, r1))
    sel = xy[inl]
    boot = fp.bootstrap(lambda d: 2 * fp.fit_circle_geometric(d)[1], sel, n=40)
    return c, 2 * r, sel, {"points": int(len(sel)), "inlier_fraction": r3(inl.mean()),
                           "coverage_deg": fp.angular_coverage_deg(sel, c),
                           **{k: r3(v) for k, v in fp.residual_stats(fp.circle_residuals(sel, c, r)).items() if k != "points"},
                           "bootstrap_sd": float(boot[0])}


def register_and_depth(L, N_local):
    out = {}
    specs = {
        "register_wall": [(-1.6, -0.4, 55, 60), (-1.4, -0.6, 55.5, 59), (-1.8, -0.3, 54, 61)],
        "chamber_lip_wall": [(-5.0, -2.7, 43, 47.5), (-4.5, -3.0, 44, 47), (-5.0, -2.5, 43.5, 47.5)],
        "floor_inner_edge": [(-2.3, -1.9, 45, 49), (-2.4, -1.8, 45.5, 48.5), (-2.3, -1.9, 44.5, 49.5)],
    }
    for name, variants in specs.items():
        diam, centres, info0 = [], [], None
        for k, (z0, z1, r0, r1) in enumerate(variants):
            c, d, sel, info = circle_band(L, z0, z1, r0, r1)
            diam.append(d)
            centres.append(c)
            if k == 0:
                info0 = info
        spread = float(np.ptp(diam))
        out[name] = measurement(
            r3(diam[0]), combine(info0["bootstrap_sd"], spread),
            "RANSAC cercle (seuil 0,2) puis Gauss-Newton géométrique sur la bande de sommets, axe = normale du plan d'étanchéité",
            {"z_window": variants[0][:2], "radial_window": variants[0][2:]},
            {**info0, "sensitivity_range_3_windows": r3(spread),
             "centre_offset_from_origin": r3(np.linalg.norm(centres[0]))},
            quantity="diameter")
    # axe du registre : cylindre libre (paroi courte, angle peu contraint)
    rad = np.linalg.norm(L[:, :2], axis=1)
    m = (L[:, 2] > -1.6) & (L[:, 2] < -0.4) & (rad > 55) & (rad < 60)
    o, a, r, res, inl = fp.ransac_cylinder(L[m], np.array([0, 0, 1.0]), 0.2, radius_range=(54, 60))
    out["register_axis_tilt_vs_seal_normal_deg"] = measurement(
        r3(fp.angle_between_deg(a, [0, 0, 1])), None,
        "cylindre RANSAC libre sur la paroi du registre ; paroi haute d'environ 1,2 unité, angle faiblement contraint",
        {"z_window": [-1.6, -0.4], "radial_window": [55, 60]},
        {"points": int(inl.sum()), "rms": r3(np.sqrt(np.mean(res ** 2)))}, quantity="angle_deg")
    # profondeur : plan du fond de lamage
    floor_m = (L[:, 2] > -2.9) & (L[:, 2] < -1.3) & (rad > 48.5) & (rad < 55.5)
    depths = []
    for thr in (0.10, 0.15, 0.25):
        c, n, inl = fp.ransac_plane(L[floor_m], thr, reference_normal=np.array([0, 0, 1.0]), max_angle_deg=5)
        depths.append((c, n, inl))
    c, n, inl = depths[1]
    res = fp.plane_residuals(L[floor_m][inl], c, n)
    depth_vals = [-float(cc[2]) for cc, _, _ in depths]
    boot = fp.bootstrap(lambda d: fp.fit_plane_lsq(d)[0][2], L[floor_m][inl], n=40)
    out["register_depth"] = measurement(
        r3(-c[2]), combine(float(boot[0]), float(np.ptp(depth_vals))),
        "distance du plan d'étanchéité (z = 0) au plan RANSAC du fond de lamage annulaire, prise au centroïde",
        {"z_window": [-2.9, -1.3], "radial_window": [48.5, 55.5]},
        {**{k: r3(v) for k, v in fp.residual_stats(res).items()},
         "floor_parallelism_deg": r3(fp.angle_between_deg(n, [0, 0, 1])),
         "sensitivity_range_thresholds": r3(np.ptp(depth_vals))}, quantity="depth")
    return out


def studs(L, N_local, to_local):
    holes = []
    for seed_abc in SEEDS["head_studs_ABC"]:
        seed = to_local(np.asarray(seed_abc))
        fits = [fit_axis_hole(L, seed, np.array([0, 0, 1.0]), ball, (4.0, 7.0), normals=N_local)
                for ball in (7.0, 8.0, 10.0)]
        f = fits[1]
        d_spread = float(np.ptp([x["diameter"] for x in fits]))
        pos_spread = float(np.max(np.linalg.norm(np.array([x["centre_xy"] for x in fits]) - f["centre_xy"], axis=1)))
        holes.append({
            "centre_xy_at_seal_plane": measurement(vec(f["centre_xy"], 3), combine(0.0, 2 * pos_spread) or 0.0,
                                                   "intersection de l'axe du cylindre RANSAC avec z = 0",
                                                   {"seed_local": vec(seed, 2), "ball_radius": 8.0},
                                                   {"points": f["points"], "rms": r3(f["rms"]), "p95": r3(f["p95"]),
                                                    "axial_extent": r3(f["axial_extent"])}, quantity="position"),
            "diameter": measurement(r3(f["diameter"]), combine(f["diameter_bootstrap_sd"], d_spread),
                                    "cylindre RANSAC (seuil 0,3) sur sommets à normale perpendiculaire à l'axe ; bootstrap 30 tirages ; boules 7/8/10",
                                    {"seed_local": vec(seed, 2)}, {"sensitivity_range_ball": r3(d_spread)}, quantity="diameter"),
            "axis_tilt_vs_seal_normal_deg": r3(fp.angle_between_deg(f["axis"], [0, 0, 1])),
            "_centre": f["centre_xy"],
        })
    centres = [h.pop("_centre") for h in holes]
    pat = pattern_summary(centres)
    return {
        "count_found": len(holes),
        "search_note": "quatre trous fermés trouvés dans les tranches z = -5 à -8 ; aucune autre ouverture circulaire 4-7 de rayon sur l'emprise",
        "holes": holes,
        "pattern": measurement({"span_x": r3(pat["span_x"]), "span_y": r3(pat["span_y"]),
                                "pair_distances": [r3(x) for x in pat["pair_distances"]],
                                "centroid_offset_from_register_axis": vec(pat["centroid"], 3)},
                               0.1, "entraxes entre intersections d'axes au plan d'étanchéité",
                               "quatre trous de goujon de culasse", "incertitude = somme majorante des positions",
                               quantity="pattern"),
    }


def spark_plugs(L, N_local, to_local):
    plugs = []
    for seed_abc in SEEDS["spark_plugs_ABC"]:
        seed = to_local(np.asarray(seed_abc))
        fits = [fit_axis_hole(L, seed, None, ball, (4.5, 8.0), normals=N_local) for ball in (8.0, 9.0, 11.0)]
        f = fits[1]
        angles = [90.0 - fp.angle_between_deg(x["axis"], [0, 0, 1]) for x in fits]
        diam = [x["diameter"] for x in fits]
        plugs.append({
            "diameter_apparent": measurement(r3(f["diameter"]), combine(f["diameter_bootstrap_sd"], np.ptp(diam)),
                                             "cylindre RANSAC, axe initial = plus petite direction propre des normales locales",
                                             {"seed_local": vec(seed, 2), "ball_radius": 9.0},
                                             {"points": f["points"], "rms": r3(f["rms"]), "p95": r3(f["p95"]),
                                              "axial_extent": r3(f["axial_extent"]), "sensitivity_range_ball": r3(np.ptp(diam))},
                                             quantity="diameter"),
            "axis_angle_to_seal_plane_deg": measurement(r3(angles[1]), combine(0.0, np.ptp(angles)),
                                                        "angle entre l'axe ajusté et le plan z = 0", {"seed_local": vec(seed, 2)},
                                                        {"sensitivity_range_ball_deg": r3(np.ptp(angles))}, quantity="angle_deg"),
            "axis_unit_local": vec(f["axis"]),
            "axis_point_local": vec(f["axis_point"], 3),
            "axis_at_seal_plane_xy": vec(f["centre_xy"], 3),
        })
    return {"count_found": len(plugs),
            "note": "deux logements symétriques (double allumage 935) ; le filetage n'est pas résolu par le scan, seul un alésage lisse apparent est ajusté",
            "plugs": plugs}


def valves(L, N_local, to_local, seal_z=0.0):
    out = []
    for spec in SEEDS["valve_bucket_bores"]:
        seed = to_local(np.asarray(spec["seed"]))
        hint = np.asarray(spec["axis_hint"])
        hint = hint / np.linalg.norm(hint)
        fits = [fit_axis_hole(L, seed, hint, ball, (17.0, 23.0), normals=N_local) for ball in (20.0, 22.0, 25.0)]
        f = fits[1]
        o, a = np.asarray(f["axis_point"]), np.asarray(f["axis"])
        u, v = fp.orthonormal_basis(a)
        d = L - o
        s = d @ a
        xy = d @ np.column_stack((u, v))
        rho = np.linalg.norm(xy, axis=1)
        throat, guide, centres3d = [], [], []
        t_seal = (seal_z - o[2]) / a[2]
        for t in np.arange(0.0, t_seal, 1.0):
            m = (np.abs(s - t) < 0.3) & (rho < 30)
            q = xy[m]
            for lo, hi, bucket in ((17.0, 24.0, throat), (5.5, 7.5, guide)):
                mm = (np.linalg.norm(q, axis=1) > lo - 1.5) & (np.linalg.norm(q, axis=1) < hi + 1.5)
                if mm.sum() < 20:
                    continue
                try:
                    c, r, inl = fp.ransac_circle(q[mm], 0.2, trials=300, radius_range=(lo, hi))
                except ValueError:
                    continue
                cov = fp.angular_coverage_deg(q[mm][inl], c)
                if cov >= 240 and inl.sum() >= 20 and np.linalg.norm(c) < 3.0:
                    z = float((o + t * a)[2])
                    bucket.append((t, z, 2 * r, float(np.linalg.norm(c)), cov, int(inl.sum())))
                    centres3d.append(o + t * a + c[0] * u + c[1] * v)
        # gorge : cercles 17-24 entre 5 et 25 unités sous le plan d'étanchéité
        thr = [x for x in throat if -25.0 < x[1] < -5.0]
        guide_hits = [x for x in guide if x[1] < -60.0]
        line_axis = None
        if len(centres3d) >= 3:
            cc = np.asarray(centres3d)
            _, _, vt = np.linalg.svd(cc - cc.mean(axis=0))
            line_axis = vt[0] if vt[0] @ a > 0 else -vt[0]
        at_seal = o + t_seal * a
        tilt = [fp.angle_between_deg(x["axis"], [0, 0, 1]) for x in fits]
        entry = {
            "bucket_or_spring_bore_diameter": measurement(
                r3(f["diameter"]), combine(f["diameter_bootstrap_sd"], np.ptp([x["diameter"] for x in fits])),
                "cylindre RANSAC sur l'alésage côté plan d'appui du porte-arbre ; boules 20/22/25",
                {"seed_local": vec(seed, 2)},
                {"points": f["points"], "rms": r3(f["rms"]), "p95": r3(f["p95"]), "axial_extent": r3(f["axial_extent"])},
                quantity="diameter"),
            "axis_angle_to_seal_normal_deg": measurement(
                r3(tilt[1]),
                combine(0.0, max(np.ptp(tilt), 2 * (fp.angle_between_deg(line_axis, a) if line_axis is not None else 0.0))),
                "axe de l'alésage ajusté ; incertitude élargie par l'écart à la droite des centres des cercles concentriques (alésage, gorge)",
                {"seed_local": vec(seed, 2)},
                {"axis_from_circle_centres_deg": r3(fp.angle_between_deg(line_axis, [0, 0, 1])) if line_axis is not None else None,
                 "circle_centres_used": len(centres3d)}, quantity="angle_deg"),
            "axis_unit_local": vec(a),
            "axis_at_seal_plane_xy": vec(at_seal[:2], 3),
            "throat_diameter_apparent": (measurement(
                r3(np.median([x[2] for x in thr])), r3(max(np.std([x[2] for x in thr]), 0.2)),
                "médiane des cercles RANSAC (couverture >= 240°, centre à < 3 de l'axe) dans des tranches perpendiculaires à l'axe, z entre -25 et -5",
                {"z_window": [-25.0, -5.0]},
                {"slices": len(thr), "diameters": [r3(x[2]) for x in thr], "centre_offsets": [r3(x[3]) for x in thr]},
                quantity="diameter") if thr else not_measurable("aucune tranche à couverture suffisante")),
            "guide_bore_diameter_apparent": (measurement(
                r3(np.median([x[2] for x in guide_hits])), r3(max(np.std([x[2] for x in guide_hits]), 0.2)),
                "cercles RANSAC rayon 5,5-7,5 le long de l'axe, côté porte-arbre",
                {"z_below": -60.0}, {"slices": len(guide_hits), "diameters": [r3(x[2]) for x in guide_hits],
                                     "z": [r3(x[1]) for x in guide_hits]},
                quantity="diameter") if guide_hits else not_measurable("alésage de guide non fermé dans le scan")),
            "seat_insert": not_measurable("portée de siège, angle de siège et logement de bague non séparables d'une surface ouverte sans soupape ni coupe"),
        }
        out.append(entry)
    a1 = np.asarray(out[0]["axis_unit_local"])
    a2 = np.asarray(out[1]["axis_unit_local"])
    p1 = np.asarray(out[0]["axis_at_seal_plane_xy"])
    p2 = np.asarray(out[1]["axis_at_seal_plane_xy"])
    return {
        "count_found": 2,
        "labels": ["valve_1_high_B_side", "valve_2_low_B_side"],
        "valves": out,
        "included_angle_deg": measurement(r3(fp.angle_between_deg(a1, a2)),
                                          combine(0.0, 2 * max(out[0]["axis_angle_to_seal_normal_deg"]["uncertainty_k1"],
                                                               out[1]["axis_angle_to_seal_normal_deg"]["uncertainty_k1"])),
                                          "angle entre les deux axes ajustés", "deux alésages de soupape", "dépend de la qualité des axes",
                                          quantity="angle_deg"),
        "axis_spacing_at_seal_plane": measurement(r3(np.linalg.norm(p1 - p2)), 1.0,
                                                  "distance des intersections des axes avec z = 0 (extrapolation d'environ 85 unités)",
                                                  "deux axes de soupape", "incertitude majorée : 1° d'axe déplace le point de 1,5",
                                                  quantity="distance"),
        "axis_skew_A_offset": r3(abs(p1[0] - p2[0])),
    }


def flanges(P, N, frame_rows, to_local):
    result = {}
    seal_normal_abc = frame_rows[2]
    for key, spec in (("low_B", SEEDS["flange_low_B"]), ("high_B", SEEDS["flange_high_B"])):
        ref = np.array([0, 1.0, 0])
        m = (np.abs(P[:, 1] - spec["plane_B"]) < 1.2) & (np.abs(N @ ref) > 0.95)
        c, n, inl = fp.ransac_plane(P[m], 0.15, reference_normal=ref, max_angle_deg=6)
        res = fp.plane_residuals(P[m][inl], c, n)
        e1 = np.array([1.0, 0, 0]) - n[0] * n
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        studs_out = []
        for seed_abc, ball in spec["studs_ABC_ball"]:
            f = fit_axis_hole(P, np.asarray(seed_abc), ref, ball, (2.5, 5.0), normals=N)
            o, a = np.asarray(f["axis_point"]), np.asarray(f["axis"])
            hit = o + ((c - o) @ n) / (a @ n) * a
            studs_out.append({"in_plane_uv": [r3((hit - c) @ e1), r3((hit - c) @ e2)], "_hit": hit,
                              "diameter_apparent": r3(f["diameter"]), "diameter_bootstrap_sd": r3(f["diameter_bootstrap_sd"]),
                              "points": f["points"], "p95": r3(f["p95"]), "axial_extent": r3(f["axial_extent"]),
                              "axis_tilt_vs_flange_normal_deg": r3(fp.angle_between_deg(a, n))})
        hits = np.array([s.pop("_hit") for s in studs_out])
        pairs = pattern_summary([[s["in_plane_uv"][0], s["in_plane_uv"][1]] for s in studs_out])
        entry = {
            "plane": measurement({"normal_abc": vec(n), "offset_B": r3(c[1]),
                                  "angle_normal_to_seal_normal_deg": r3(fp.angle_between_deg(n, seal_normal_abc))},
                                 {"offset": 0.1, "angle_deg": 0.2},
                                 "RANSAC plan (seuil 0,15) sur sommets à normale ±B puis moindres carrés",
                                 {"B_window": [spec["plane_B"] - 1.2, spec["plane_B"] + 1.2]},
                                 {**{k: r3(v) for k, v in fp.residual_stats(res).items()}}, quantity="plane"),
            "studs_or_holes": studs_out,
            "stud_pattern": measurement({"count": len(studs_out), "pair_distances": [r3(x) for x in pairs["pair_distances"]]},
                                        0.3, "entraxes des intersections d'axes avec le plan de bride", "goujons ou trous visibles",
                                        "positions contraintes par des tronçons de 5 à 17 unités", quantity="pattern"),
            "stud_positions_local": [vec(to_local(h), 3) for h in hits],
        }
        if key == "low_B":
            sm = np.abs(P[:, 1] - spec["port_slab_B"]) < 0.3
            ports = [x for x in circles_in_slab(P[sm][:, [0, 2]], radius_range=(15, 25))]
            entry["port_circle_at_B_minus_245"] = (measurement(
                r3(ports[0]["diameter"]), r3(max(ports[0]["p95"], 0.3)),
                "cercle géométrique sur l'amas de sommets de la tranche B = -245 ± 0,3 (6 unités sous la face)",
                "conduit débouchant bride B basse", {"points": ports[0]["points"], "coverage_deg": ports[0]["coverage_deg"],
                                                     "p95": r3(ports[0]["p95"])}, quantity="diameter",
                centre_local=vec(to_local(np.array([ports[0]["centre"][0], spec["port_slab_B"], ports[0]["centre"][1]])), 3))
                if ports else not_measurable("aucun contour circulaire fermé"))
        else:
            entry["port_circle"] = not_measurable("contour de conduit non circulaire ou ouvert dans les tranches B -80 à -62")
        result[key] = entry
    return result


def carrier(P, N, frame_rows, origin_abc, to_local):
    ref = np.array([0, 0, 1.0])
    m = (np.abs(P[:, 2] - SEEDS["carrier_face_C"]) < 1.2) & (np.abs(N @ ref) > 0.95)
    c, n, inl = fp.ransac_plane(P[m], 0.15, reference_normal=ref, max_angle_deg=6)
    res = fp.plane_residuals(P[m][inl], c, n)
    seal_n = frame_rows[2]
    height = float((origin_abc - c) @ n)
    holes = []
    for level in (-174.5, -175.5):
        sm = np.abs(P[:, 2] - level) < 0.3
        for h in circles_in_slab(P[sm][:, :2], radius_range=(2.5, 5.0)):
            centre = to_local(np.array([h["centre"][0], h["centre"][1], level]))
            if not any(np.linalg.norm(np.asarray(x["centre_local_xy"]) - centre[:2]) < 2.0 for x in holes):
                holes.append({"centre_local_xy": vec(centre[:2], 3), "diameter_apparent": r3(h["diameter"]),
                              "points": h["points"], "p95": r3(h["p95"]), "coverage_deg": h["coverage_deg"], "slice_C": level})
    return {
        "carrier_face_plane": measurement(
            {"height_from_seal_plane": r3(abs(height)), "parallelism_to_seal_deg": r3(fp.angle_between_deg(n, seal_n))},
            {"height": 0.1, "angle_deg": 0.2},
            "RANSAC plan sur la face arrière (normale ±C) ; hauteur = distance de l'origine du repère au plan",
            {"C_window": [SEEDS["carrier_face_C"] - 1.2, SEEDS["carrier_face_C"] + 1.2]},
            {**{k: r3(v) for k, v in fp.residual_stats(res).items()}}, quantity="plane"),
        "carrier_fastener_holes": measurement(
            holes, 0.3, "cercles fermés dans les tranches C -174,5 et -175,5 (amas connexes, couverture >= 250°)",
            "face d'appui porte-arbre", "liste non exhaustive : seuls les trous à contour fermé sont retenus",
            quantity="hole_list", count_found=len(holes)),
        "cam_axes": not_measurable("aucun palier d'arbre dans la culasse scannée : les arbres sont portés par un carter séparé absent du scan"),
        "oil_feed_and_return": not_measurable("aucun passage d'huile identifiable sans ambiguïté ; surfaces internes ouvertes, pas de coupe ni de CT"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    digest = sha256(args.scan)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"refus : SHA-256 inattendu {digest}")
    V, F = load_obj(args.scan)
    P = V @ FRAME_ABC.T
    N = vertex_normals(P, F)

    seal_c, seal_n, seal_info = seal_plane(P)
    centre_ab = SEEDS["chamber_centre_AB"]
    origin, rows = local_frame(seal_c, seal_n, centre_ab)
    # recentrage sur l'axe du registre mesuré
    L0 = (P - origin) @ rows.T
    c_reg, _, _, _ = circle_band(L0, -1.6, -0.4, 55, 60)
    origin = origin + c_reg[0] * rows[0] + c_reg[1] * rows[1]
    L = (P - origin) @ rows.T
    NL = N @ rows.T

    def to_local(p_abc):
        return (np.asarray(p_abc) - origin) @ rows.T

    regs = register_and_depth(L, NL)
    result = {
        "schema": "scan935-interfaces/1",
        "date": "2026-09-14",
        "status": STATUS,
        "source": {"catalog_record": "catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json",
                   "sha256": digest, "vertices": int(len(V)), "triangles": int(len(F)),
                   "raw_and_geometric_derivatives_in_git": False,
                   "applicability": "culasse billet Porsche 935, pas M64 ; maillage ouvert ; unités non déclarées"},
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "script": "twins/m64-cylinder-head/source/scan935/measure_interfaces.py",
                     "fit_module": "twins/m64-cylinder-head/source/scan935/fit_primitives.py"},
        "parameters": {"seeds_abc": SEEDS, "provisional_frame_rows_abc_in_obj": FRAME_ABC.tolist(),
                       "ransac_seed": 935, "bootstrap_samples": {"circles_planes": 40, "cylinders": 30},
                       "uncertainty_rule": "k=1 : racine(sd_bootstrap² + (étendue de sensibilité / 2)²) ; exclut l'échelle OBJ et l'erreur du scanner"},
        "frame": {
            "definition": "origine = axe du registre (cercle) sur le plan d'étanchéité ; z = normale du plan orientée vers le cylindre (matière de culasse en z < 0) ; x = A provisoire projeté ; y = z × x",
            "origin_obj": vec(origin @ FRAME_ABC, 4), "rows_xyz_in_obj": (rows @ FRAME_ABC).tolist(),
        },
        "sealing_plane": measurement(
            {"flatness_rms": seal_info["rms"], "flatness_p95": seal_info["p95"],
             "peak_to_valley_inliers": seal_info["peak_to_valley_inliers"]},
            {"offset": combine(0.0, seal_info["sensitivity_offset_range"]), "normal_deg": seal_info["sensitivity_normal_max_deg"]},
            "RANSAC plan (seuil 0,15 ; 500 hypothèses à moins de 5° de C) puis moindres carrés ; sensibilité 3 seuils × 3 couronnes et 4 secteurs",
            {"C_window": [-87.8, -86.2], "radial_window_around_chamber": [58.5, 75]}, seal_info, quantity="planarity",
            note="planéité apparente du maillage, bruit de scan inclus ; pas une planéité métrologique"),
        **regs,
    }
    result["head_studs"] = studs(L, NL, to_local)
    result["spark_plugs"] = spark_plugs(L, NL, to_local)
    result["valves"] = valves(L, NL, to_local)
    result["flanges"] = flanges(P, N, rows, to_local)
    result["cam_carrier"] = carrier(P, N, rows, origin, to_local)

    reg = result["register_wall"]["value"]
    lip = result["chamber_lip_wall"]["value"]
    edge = result["floor_inner_edge"]["value"]
    guides = [v["guide_bore_diameter_apparent"].get("value") for v in result["valves"]["valves"]]
    result["scale_assessment"] = {
        "conclusion": "mm_coherent_not_calibrated",
        "checks": [
            {"scan": "floor_inner_edge", "value": edge, "reference": "alésage 95 (bas de la plage Swindon 95-102,7) et 100 M64 (P3)",
             "ratio_to_95": r3(edge / 95.0), "ratio_to_100": r3(edge / 100.0)},
            {"scan": "chamber_lip_wall", "value": lip, "ratio_to_95": r3(lip / 95.0)},
            {"scan": "register_wall", "value": reg, "note": "diamètre de centrage, supérieur à l'alésage comme attendu"},
            {"scan": "guide_bore_diameter_apparent", "values": guides,
             "reference": "logement de guide 993 2V 13,000-13,018 (WM993 p.154), autre moteur, recoupement d'ordre de grandeur seulement"},
        ],
        "rule": "unités OBJ = mm retenues comme cohérentes à quelques % ; facteur d'échelle non étalonné, aucune cote physique connue de cette pièce",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"written": str(args.output), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
