"""Torsion of the PicoGK monocoque architecture, on a mid-surface shell model.

The PicoGK model (../picogk/) is voxels: 14 million triangles of 6 mm walls,
not something CalculiX can take. This script builds the same members as
shells on the open shell that torsion.py already solves, so that the two
answers differ by the architecture and nothing else:

- same mesh, same rear clamp, same +/-1000 N at the front wheel-house tops;
- each closed section is a band of the skin (its outer wall), a copy of the
  band offset inward by the section depth (its inner wall) and a wall along
  every free edge of the band (its sides, including the flange on the
  aperture edge). Bands of different members are united first, as in the
  voxel model, so meeting rings make one section;
- members and sizes come from ../derived/zesad-monocoque.report.json, so the
  shell model and the voxel model cannot drift apart.

Differences from the voxel model, all on the soft side or neutral for this
load case: the sills are 140 mm deep, not 210 (a deeper offset folds over
the 150 mm bottom corner); the front rails sit on the floor skin, not 20 mm
above it; the rear rails are left out (they lie behind the clamp, in the
engine bay, with no skin to hang on); the wheel tubs are out of the load
path, as in torsion.py.

Four cases: {open shell, monocoque} x {0.8 mm steel, assumed CFRP layup}.
The steel pair isolates the architecture; the CFRP monocoque is the product
hypothesis. CFRP is the quasi-isotropic carbon of ../../fea/laminate.py.
Sandwich floor and bulkheads count by their two faces only (2.4 mm of
carbon): membrane stiffness right, bending under-estimated, so on the soft
side; an equivalent 41 mm shell with the sandwich's bending stiffness
inverts S3 elements once the mesh is refined. The core is in the mass.

The run is linear S3, which converges from above (../../fea/README.md).
Every case is solved at three densities of the shell (210, 300 and 420
sections, points per section in proportion); only ratios that hold across
them are used. Two other checks were tried and rejected: S6 elements (the
slivers left by the aperture clip make the open shell collapse, K = 63
N.m/deg) and splitting every triangle in four (the direct solver needs more
than 12 GB on the monocoque). These are values of this model, not of a
vehicle.

    python3 torsion_monocoque.py           # cadsim image, three densities
    python3 torsion_monocoque.py --quick   # published density only
"""
import argparse
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import build_shell as bs  # noqa: E402
import laminate  # noqa: E402
import torsion as tr  # noqa: E402

REPORT = HERE.parent / "derived" / "zesad-monocoque.report.json"
OUT_JSON = HERE.parent / "derived" / "torsion-monocoque.json"
OUT_NPZ = HERE.parent / "derived" / "torsion-monocoque-snapshot.npz"
CHANNELS = ["door", "quarter_window", "rear_arch", "front_arch", "windscreen",
            "rear_window", "front_lid", "engine_lid", "engine_bay_underside"]
SILL_DEPTH_MM = 140.0          # < the 150 mm corner radius of the section
SMOOTHING_PASSES = 20          # normal smoothing before the offset
REPEATS = 3                    # solves per value, median kept

CARBON = laminate.quasi_isotropic(laminate.reduced_stiffness(**laminate.LAMINA["carbon"]))
CARBON["rho"] = laminate.LAMINA["carbon"]["rho"]
STEEL = laminate.STEEL
# ASSUMED layups, as in ../picogk/figures.py
T_SKIN, T_SECTION = 2.0, 2.5
FACE, CORE, CORE_RHO = 1.2, 22.6, 0.048
SANDWICH_KG_M2 = 2 * FACE * CARBON["rho"] + CORE * CORE_RHO


def vertex_normals(p, tri, centre):
    a, b, c = p[tri[:, 0]], p[tri[:, 1]], p[tri[:, 2]]
    fn = np.cross(b - a, c - a)
    n = np.zeros_like(p)
    for k in range(3):
        np.add.at(n, tri[:, k], fn)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    flip = np.einsum("ij,ij->i", n, p - centre) < 0
    n[flip] *= -1                                  # outward, away from the section centre
    return n


def smooth(n, tri, region, passes):
    """Average normals over neighbours inside the region, so that a deep
    offset does not fold at tight corners."""
    for _ in range(passes):
        acc, cnt = np.zeros_like(n), np.zeros(len(n))
        for i, j in ((0, 1), (1, 2), (2, 0), (1, 0), (2, 1), (0, 2)):
            m = region[tri[:, i]] & region[tri[:, j]]
            np.add.at(acc, tri[m, i], n[tri[m, j]])
            np.add.at(cnt, tri[m, i], 1)
        upd = cnt > 0
        n[upd] = (n[upd] + acc[upd]) / (1 + cnt[upd])[:, None]
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return n


def picogk_bands(p, s, rep, profiles):
    """The closed sections of ../picogk/, as skin bands: (name, vertex mask,
    section depth mm)."""
    d, y, z = -p[:, 0], p[:, 1], p[:, 2]
    st = s["stations_d"]
    w, zb = np.interp(d, st, s["half_width"]), np.interp(d, st, s["bottom"])
    f = bs.opening_fields(p, profiles, st, s["top"], s["bottom"], s["half_width"], s["belt"])
    hyp = rep["hypotheses"]
    bands = [(r["name"], f[CHANNELS.index(r["name"])] > -r["width_mm"], r["depth_mm"]) for r in hyp["aperture_rings"]]
    sill = hyp["sills_mm"]
    bands.append(("sills", (d > sill["d"][0]) & (d < sill["d"][1]) & (np.abs(y) > w - sill["width"])
                  & (z < zb + sill["height_above_floor"]), SILL_DEPTH_MM))
    floor = z < zb + 5
    fb, rb = bs.FRONT_BULKHEAD_D, bs.REAR_BULKHEAD_D
    tun = hyp["tunnel_mm"]
    bands.append(("tunnel", floor & (d > fb) & (d < rb) & (np.abs(y) < tun["half_width"]), tun["height_above_floor"]))
    fr = hyp["front_rails_mm"]
    bands.append(("front rails", floor & (d > -640) & (d < fb + 12) & (np.abs(y) > fr["y"][0]) & (np.abs(y) < fr["y"][1]),
                  fr["z_above_floor"][1]))
    b0, b1 = hyp["b_ring_d_mm"]
    bands.append(("B-ring", (d > b0) & (d < b1), 100.0))
    return bands


def member_depths(n_points, bands):
    """Per-vertex section depth (0 = no closed section): the deepest band
    wins, so bands that meet make one section."""
    depth, used = np.zeros(n_points), {}
    for name, mask, dd in bands:
        np.maximum.at(depth, np.where(mask)[0], dd)
        used[name] = int(mask.sum())
    return depth, used


def build(s, p, tri, bands):
    """Shell model: the open shell plus, for the bands, an inner wall offset
    by the section depth and side walls on every free edge. kind: 0 skin,
    1 section wall, 2 bulkhead, 3 floor."""
    d = -p[:, 0]
    centre = np.c_[p[:, 0], np.zeros(len(p)), 0.5 * (np.interp(d, s["stations_d"], s["bottom"])
                                                     + np.interp(d, s["stations_d"], s["top"]))]
    a, b, c = p[tri[:, 0]], p[tri[:, 1]], p[tri[:, 2]]
    fn = np.cross(b - a, c - a)
    fn /= np.linalg.norm(fn, axis=1, keepdims=True)
    fd = -(a[:, 0] + b[:, 0] + c[:, 0]) / 3
    bulk = (np.abs(fn[:, 0]) > 0.95) & ((np.abs(fd - bs.FRONT_BULKHEAD_D) < 2) | (np.abs(fd - bs.REAR_BULKHEAD_D) < 2))
    depth, used = member_depths(len(p), bands(p, s))
    in_band = depth > 0
    region = in_band[tri].all(axis=1) & ~bulk
    rv = np.zeros(len(p), bool)
    rv[tri[region].ravel()] = True
    n = smooth(vertex_normals(p, tri[~bulk], centre), tri[region], rv, SMOOTHING_PASSES)
    # inner wall; where the offset would fold (deeper than the local
    # curvature allows), the depth is cut back locally until nothing folds
    idx = -np.ones(len(p), int)
    ids = np.where(rv)[0]
    idx[ids] = len(p) + np.arange(len(ids))
    inner = idx[tri[region]]
    outer = tri[region]
    on = np.cross(p[outer[:, 1]] - p[outer[:, 0]], p[outer[:, 2]] - p[outer[:, 0]])
    depth0, folded_first = depth.copy(), None
    for _ in range(60):
        inner_pts = p[ids] - n[ids] * depth[ids][:, None]
        q = inner_pts[inner - len(p)]
        inn = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
        bad = np.einsum("ij,ij->i", on, inn) <= 0.05 * np.einsum("ij,ij->i", on, on)
        folded_first = int(bad.sum()) if folded_first is None else folded_first
        if not bad.any():
            break
        depth[np.unique(outer[bad])] *= 0.85
    else:
        sys.exit(f"inner wall still folds on {int(bad.sum())} triangles")
    cut_back = rv & (depth < 0.999 * depth0)
    # side walls along the free edges of the region
    e = np.concatenate([tri[region][:, [0, 1]], tri[region][:, [1, 2]], tri[region][:, [2, 0]]])
    key = np.sort(e, axis=1)
    _, first, count = np.unique(key, axis=0, return_index=True, return_counts=True)
    free = e[first[count == 1]]
    side = np.vstack([np.c_[free[:, 0], free[:, 1], idx[free[:, 1]]], np.c_[free[:, 0], idx[free[:, 1]], idx[free[:, 0]]]])
    pts = np.vstack([p, inner_pts])
    walls = np.vstack([inner, side])
    walls = walls[areas(pts, walls) > 2.0]          # slivers on short free edges and cut-back corners
    all_tri = np.vstack([tri, walls])
    kind = np.concatenate([np.where(bulk, 2, 0), np.ones(len(walls), int)])   # 0 skin, 1 section wall, 2 bulkhead
    zb = np.interp(fd, s["stations_d"], s["bottom"])
    floor = ((a[:, 2] + b[:, 2] + c[:, 2]) / 3 < zb + 10) & (fd > bs.FRONT_BULKHEAD_D) & (fd < bs.REAR_BULKHEAD_D) & ~bulk
    kind[:len(tri)][floor] = 3                                                           # 3 floor
    folds = {"inner_triangles_folding_at_full_depth": folded_first,
             "section_vertices_cut_back": int(cut_back.sum()), "section_vertices": int(rv.sum()),
             "mean_depth_ratio_where_cut_back": round(float((depth[cut_back] / depth0[cut_back]).mean()), 3) if cut_back.any() else 1.0}
    return pts, all_tri, kind, used, folds, int(region.sum())


def areas(pts, tri):
    return np.linalg.norm(np.cross(pts[tri[:, 1]] - pts[tri[:, 0]], pts[tri[:, 2]] - pts[tri[:, 0]]), axis=1) / 2


def cases(kind, area):
    """{name: (sections, mass kg)} for the four cases."""
    steel = (0.8, STEEL["E"], STEEL["nu"])
    cf = lambda t: (t, CARBON["E"], CARBON["nu"])                      # noqa: E731
    sandwich = cf(2 * FACE)                                             # faces only
    base = kind != 1
    out = {}
    for arch, keep in (("open shell", base), ("monocoque", np.ones(len(kind), bool))):
        secs = [(keep, *steel)]
        out[f"{arch}, 0.8 mm steel"] = (secs, float(area[keep].sum() * 0.8 * STEEL["rho"] * 1e-6))
        secs, mass = [], 0.0
        for k, (t, e, nu), kg_m2 in ((0, cf(T_SKIN), T_SKIN * CARBON["rho"]), (1, cf(T_SECTION), T_SECTION * CARBON["rho"]),
                                     (2, sandwich, SANDWICH_KG_M2), (3, sandwich, SANDWICH_KG_M2)):
            m = keep & (kind == k)
            if m.any():
                secs.append((m, t, e, nu))
                mass += float(area[m].sum() * 1e-6 * kg_m2)
        out[f"{arch}, CFRP layup"] = (secs, mass)
    return out


def twist(p, u, s, stations):
    """Section rotation about the car's long axis, by least squares on the
    skin nodes of each slab."""
    d = -p[:, 0]
    out = []
    for di in stations:
        m = np.abs(d - di) < 15
        if m.sum() < 20:
            out.append(np.nan)
            continue
        y, z = p[m, 1], p[m, 2] - p[m, 2].mean()
        A = np.zeros((2 * m.sum(), 3))
        A[0::2, 0], A[0::2, 2] = 1, -z
        A[1::2, 1], A[1::2, 2] = 1, y
        rhs = np.empty(2 * m.sum())
        rhs[0::2], rhs[1::2] = u[m, 1], u[m, 2]
        out.append(float(np.degrees(np.linalg.lstsq(A, rhs, rcond=None)[0][2])))
    return out


def solve_repeated(pts, tri, secs, rear, fl, fr, beams=(), n=REPEATS):
    """Median of n identical solves. CalculiX occasionally returns a K a
    few per cent away on the same input (seen 3 times in about 40 solves,
    0.1 to 7%), so each value is the median of three, with the spread kept."""
    runs = [tr.solve(pts, tri, secs, rear, fl, fr, beams=beams) for _ in range(n)]
    ks = [float(r[0]) for r in runs]
    i = int(np.argsort(ks)[len(ks) // 2])
    return ks[i], runs[i][1], runs[i][2], [round(k) for k in ks]


def solve_density(n_stations, res, rep, profiles, stations, keep_fields):
    s = None if n_stations == bs.N_STATIONS and res == 1.0 else bs.structural(n_stations, res)[2]
    s, p, tri = tr.load_shell(s)
    rear, fl, fr = tr.supports(s, p)
    pts, all_tri, kind, used, folds, n_region = build(s, p, tri, lambda q, st: picogk_bands(q, st, rep, profiles))
    area = areas(pts, all_tri)
    print(f"{n_stations} sections: {len(pts)} nodes, {len(all_tri)} triangles; depth cut back on "
          f"{folds['section_vertices_cut_back']} of {folds['section_vertices']} section vertices")
    row, extra = {}, {}
    for name, (secs, mass) in cases(kind, area).items():
        k, u, vm, reps = solve_repeated(pts, all_tri, secs, rear, fl, fr)
        row[name] = (round(float(k)), round(mass, 1), reps)
        if keep_fields:
            extra[name] = (vm, twist(pts, u, s, stations))
        print(f"  {name:28s} K = {k:7.0f} N.m/deg, mass {mass:6.1f} kg")
    mesh = {"sections": n_stations, "points_per_section_factor": res, "nodes": len(pts), "triangles": len(all_tri),
            "skin_triangles_under_sections": n_region, "offset_folds": folds, "members_vertices": used,
            "clamp_nodes": len(rear), "load_nodes": [len(fl), len(fr)]}
    return row, mesh, extra, (pts, all_tri, kind)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="published density only")
    a = ap.parse_args()
    rep = json.loads(REPORT.read_text())
    profiles = json.loads(bs.PROFILES.read_text())
    stations = np.arange(-600, 2451, 50.0)
    densities = [(bs.N_STATIONS, 1.0)] if a.quick else [(210, 0.5), (300, 0.71), (bs.N_STATIONS, 1.0)]
    rows, meshes = [], []
    for n, res in densities:
        row, mesh, extra, model = solve_density(n, res, rep, profiles, stations, n == bs.N_STATIONS)
        rows.append(row)
        meshes.append(mesh)
    results = {}
    for name in rows[-1]:
        k = [r[name][0] for r in rows]
        results[name] = {"mass_kg": rows[-1][name][1], "K": k, "K_repeats": [r[name][2] for r in rows],
                         "K_per_kg": [round(x / rows[-1][name][1], 1) for x in k],
                         "twist_deg": [None if np.isnan(x) else round(x, 5) for x in extra[name][1]]}
    ratio = lambda num, den: [round(rn[num][0] / rn[den][0], 2) for rn in rows]   # noqa: E731
    doc = {
        "model": "mid-surface shell model of the PicoGK monocoque architecture; torsion load case of torsion.py",
        "classification": "values of this model under this load, not of a vehicle; prohibited_pending_engineering",
        "load_case": {"force_N": tr.FORCE_N, "clamp": "d 2050-2450, z 450-720, |y| > 0.8 W",
                      "loads": "d -200..150, z 470-640, |y| > 0.72 W"},
        "meshes": meshes,
        "mesh_note": "K lists are at the densities of 'meshes', coarsest first, each the median of K_repeats; S3 converges from above, so only ratios that hold across densities are used",
        "ratios": {"monocoque / open shell, steel": ratio("monocoque, 0.8 mm steel", "open shell, 0.8 mm steel"),
                   "monocoque / open shell, CFRP": ratio("monocoque, CFRP layup", "open shell, CFRP layup"),
                   "CFRP / steel, monocoque": ratio("monocoque, CFRP layup", "monocoque, 0.8 mm steel")},
        "materials": {
            "steel": {"t_mm": 0.8, "E_MPa": STEEL["E"], "rho_g_cm3": STEEL["rho"]},
            "cfrp_qi": {"E_MPa": round(CARBON["E"]), "nu": round(CARBON["nu"], 3), "rho_g_cm3": CARBON["rho"],
                        "skin_mm": T_SKIN, "section_walls_mm": T_SECTION, "basis": "ASSUMED layups; ply constants of ../../fea/laminate.py"},
            "sandwich": {"faces_mm": FACE, "core_mm": CORE, "core_rho_g_cm3": CORE_RHO,
                         "stiffness": "faces only (2.4 mm CFRP shell): membrane right, bending under-estimated",
                         "mass": "faces and core"},
        },
        "differences_from_voxel_model": ["sills 140 mm deep, not 210", "front rails on the floor skin",
                                         "rear rails left out", "wheel tubs outside the load path"],
        "twist_stations_d_mm": stations.tolist(),
        "cases": results,
    }
    OUT_JSON.write_text(json.dumps(doc, indent=1) + "\n")
    pts, all_tri, kind = model
    np.savez_compressed(OUT_NPZ, points=pts.astype(np.float32), triangles=all_tri.astype(np.int32), kind=kind.astype(np.uint8),
                        von_mises_monocoque_steel=extra["monocoque, 0.8 mm steel"][0].astype(np.float32),
                        von_mises_open_steel=extra["open shell, 0.8 mm steel"][0].astype(np.float32))
    print("ratios", doc["ratios"])
    print(f"wrote {OUT_JSON.name} and {OUT_NPZ.name}")


if __name__ == "__main__":
    main()
