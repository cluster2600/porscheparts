"""Torsion of the closed-ring PicoGK study (../picogk-rings/), on the shell
model and load case of torsion_monocoque.py, so that the two PicoGK
architectures, and the open shell, are compared on one mesh and one load.

The two architectures close the body differently:

- ../picogk/ makes every closed section out of the skin itself: a band
  around each aperture, an inner wall offset 60 to 100 mm and side walls;
- ../picogk-rings/ adds discrete tubes, 50 to 70 mm in diameter, tangent to
  the skin from inside (windscreen frame and A-pillars, B-hoop, C-pillars,
  roof rails, wheel arches), plus boxed sills and a tunnel.

Members are read from ../picogk-rings/params/monocoque-f0.json and the
member paths that ../picogk-rings/prepare.py computes, so nothing is
re-guessed here:

- sills and tunnel: skin bands with an inner wall, as in torsion_monocoque.py
  (sill band 140 mm wide under the door sill, 130 mm deep; tunnel 180 mm
  wide, 120 deep), walls of the study's 3 mm;
- tubes: B32 beams on the paths, cut every 40 mm, with the solid circular
  section that has the tube's area, bending and torsion stiffness
  (torsion.tube_equivalent); tube nodes closer than 20 mm are welded, which
  joins the rings where PicoGK fuses them; every tube node within its radius
  plus 40 mm of the skin is tied to the nearest skin node by a short stiff
  beam, the tangent bond. Checked on a cantilever plate with a tube: 12%
  stiffer than composite beam theory, the side S3 errs on;
- floor and bulkheads: the two 1.5 mm faces, as torsion_monocoque.py counts
  sandwiches (the core is in the mass).

Three cases at the three shell densities, each value the median of three
solves: uniform 0.8 mm steel (shells and tube walls), the study's assumed
CFRP layup, and the same CFRP model without its tubes, which measures what
the tubes bring. These are values of this model, not of a vehicle.

    python3 torsion_rings.py           # cadsim image, shapely from the PYLIB
    python3 torsion_rings.py --quick   # published density only
"""
import argparse
import importlib.util
import json
import pathlib
import sys
import tempfile

import numpy as np
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import build_shell as bs  # noqa: E402
import torsion as tr  # noqa: E402
import torsion_monocoque as tm  # noqa: E402

RINGS = HERE.parent / "picogk-rings"
PARAMS = RINGS / "params" / "monocoque-f0.json"
OUT_JSON = HERE.parent / "derived" / "torsion-rings.json"
OUT_NPZ = HERE.parent / "derived" / "torsion-rings-model.npz"
SEGMENT_MM = 40.0
WELD_MM = 20.0
LINK_REACH_MM = 40.0
LINK_DIAMETER_MM, LINK_E = 20.0, 20 * tm.STEEL["E"]
GROUPS = {"front_ring": "front_ring", "b_ring": "b_ring", "rear_ring": "rear_ring",
          "roof_rails": "roof_rail", "arches": "arch"}


def geometry():
    """Parameters and member paths, from the study's own prepare.py."""
    spec = importlib.util.spec_from_file_location("rings_prepare", RINGS / "prepare.py")
    prep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prep)
    with tempfile.TemporaryDirectory() as tmp:
        geo = prep.main(PARAMS, tmp)
    P = {k: v["value"] for k, v in json.loads(PARAMS.read_text())["parameters"].items()}
    return P, geo


def bands(P, geo):
    w_mid = geo["half_width_at"]["door_mid"]
    sill_top = geo["door_aperture"]["sill_top_z"]
    fb, rb = P["front_bulkhead_d_mm"], P["rear_bulkhead_d_mm"]

    def fn(p, s):
        d, y, z = -p[:, 0], p[:, 1], p[:, 2]
        zb = np.interp(d, s["stations_d"], s["bottom"])
        floor = z < zb + 5
        inside = (d > fb) & (d < rb)
        return [("sills", inside & (np.abs(y) > w_mid - P["sill_width_mm"]) & (z < sill_top), P["sill_width_mm"] - 10.0),
                ("tunnel", inside & floor & (np.abs(y) < P["tunnel_width_mm"] / 2), P["tunnel_height_mm"])]
    return fn


def tubes(P, geo, pts, n_skin):
    """Tube and link beams. Returns the new nodes, the B32 elements per
    group, the links, the tube lengths per group and counts."""
    nodes, paths, od = [], [], []
    for name, path in geo["paths"].items():
        q = np.array(path["points"], float)
        ids = []
        for a, b in zip(q[:-1], q[1:]):
            n = max(1, int(np.ceil(np.linalg.norm(b - a) / SEGMENT_MM)))
            for t in np.linspace(0, 1, n + 1)[:-1]:
                nodes.append(a + (b - a) * t)
                ids.append(len(nodes) - 1)
        nodes.append(q[-1])
        ids.append(len(nodes) - 1)
        od += [P[f"{GROUPS[path['group']]}_od_mm"]] * len(ids)
        paths.append((path["group"], ids))
    nodes, od = np.array(nodes), np.array(od)
    rep = np.arange(len(nodes))                      # weld: union of nodes closer than WELD_MM
    for i, j in sorted(cKDTree(nodes).query_pairs(WELD_MM)):
        ri, rj = rep[i], rep[j]
        while rep[ri] != ri:
            ri = rep[ri]
        while rep[rj] != rj:
            rj = rep[rj]
        rep[max(ri, rj)] = min(ri, rj)
    for i in range(len(rep)):
        while rep[rep[i]] != rep[i]:
            rep[i] = rep[rep[i]]
    keep = np.unique(rep)
    np.maximum.at(od, rep, od)                       # a welded node takes the largest tube through it
    index = -np.ones(len(nodes), int)
    index[keep] = len(pts) + np.arange(len(keep))
    tube_pts = nodes[keep]
    new = [tube_pts]
    base = len(pts) + len(keep)
    elements, length = {g: [] for g in GROUPS}, {g: 0.0 for g in GROUPS}
    for group, ids in paths:
        g = [index[rep[i]] for i in ids]
        for a, b in zip(g[:-1], g[1:]):
            if a == b:
                continue
            pa, pb = tube_pts[a - len(pts)], tube_pts[b - len(pts)]
            new.append([(pa + pb) / 2])
            elements[group].append((a, base, b))
            base += 1
            length[group] += float(np.linalg.norm(pb - pa))
    dist, near = cKDTree(pts[:n_skin]).query(tube_pts)
    links = []
    for k, (dd, s) in enumerate(zip(dist, near)):
        if dd < od[keep[k]] / 2 + LINK_REACH_MM:
            new.append([(pts[s] + tube_pts[k]) / 2])
            links.append((int(s), base, len(pts) + k))
            base += 1
    allpts = np.vstack([pts] + [np.atleast_2d(x) for x in new])
    info = {"tube_nodes": len(tube_pts), "welded": int(len(nodes) - len(keep)), "links": len(links),
            "unlinked_tube_nodes": int(len(tube_pts) - len(links)),
            "tube_length_m": {g: round(v / 1000, 2) for g, v in length.items()}}
    return allpts, {g: np.array(e, int).reshape(-1, 3) for g, e in elements.items()}, np.array(links, int), length, info


def cases(P, kind, area, elements, links, length):
    """{name: (shell sections, beams, mass kg)}"""
    rho_cf = tm.CARBON["rho"]
    out = {}
    for name, e_mod, nu, rho, skin, wall, face, tube_wall in (
            ("rings, 0.8 mm steel", tm.STEEL["E"], tm.STEEL["nu"], tm.STEEL["rho"], 0.8, 0.8, 0.4, lambda g: 0.8),
            ("rings, CFRP layup", tm.CARBON["E"], tm.CARBON["nu"], rho_cf, P["skin_thickness_mm"], P["sill_wall_mm"],
             P["panel_skin_mm"], lambda g: P[f"{GROUPS[g]}_wall_mm"])):
        secs, mass = [], 0.0
        steel = name.startswith("rings, 0.8")
        core = 0.0 if steel else (P["panel_thickness_mm"] - 2 * P["panel_skin_mm"]) * P["core_density_g_cm3"]
        for k, t, kg_m2 in ((0, skin, skin * rho), (1, wall, wall * rho), (2, 2 * face, 2 * face * rho + core),
                            (3, 2 * face, 2 * face * rho + core)):
            m = kind == k
            secs.append((m, t, e_mod, nu))
            mass += float(area[m].sum() * 1e-6 * kg_m2)
        beams = []
        for g, el in elements.items():
            if not len(el):
                continue
            od, tw = P[f"{GROUPS[g]}_od_mm"], tube_wall(g)
            dia, e_eq = tr.tube_equivalent(od, tw, e_mod)
            beams.append((el, dia, e_eq, nu))
            mass += length[g] * np.pi * ((od / 2) ** 2 - (od / 2 - tw) ** 2) * rho * 1e-6
        beams.append((links, LINK_DIAMETER_MM, LINK_E, 0.3))
        out[name] = (secs, beams, mass)
        if not steel:                                # what the tubes bring: same model without them
            tube_mass = sum(length[g] * np.pi * ((P[f"{GROUPS[g]}_od_mm"] / 2) ** 2 - (P[f"{GROUPS[g]}_od_mm"] / 2 - tube_wall(g)) ** 2)
                            for g in elements) * rho * 1e-6
            out["rings without tubes, CFRP layup"] = (secs, [], mass - tube_mass)
    return out


def solve_density(n_stations, res, P, geo, stations, keep_fields):
    s = None if n_stations == bs.N_STATIONS and res == 1.0 else bs.structural(n_stations, res)[2]
    s, p, tri = tr.load_shell(s)
    rear, fl, fr = tr.supports(s, p)
    pts, all_tri, kind, used, folds, n_region = tm.build(s, p, tri, bands(P, geo))
    area = tm.areas(pts, all_tri)
    allpts, elements, links, length, info = tubes(P, geo, pts, len(p))
    print(f"{n_stations} sections: {len(allpts)} nodes, {len(all_tri)} triangles, "
          f"{sum(len(e) for e in elements.values())} tube beams, {len(links)} links")
    row, extra = {}, {}
    for name, (secs, beams, mass) in cases(P, kind, area, elements, links, length).items():
        k, u, vm, reps = tm.solve_repeated(allpts, all_tri, secs, rear, fl, fr, beams=beams)
        row[name] = (round(k), round(mass, 1), reps)
        if keep_fields:
            extra[name] = tm.twist(allpts[:len(pts)], u[:len(pts)], s, stations)
        print(f"  {name:22s} K = {k:7.0f} N.m/deg (runs {reps}), mass {mass:6.1f} kg")
    mesh = {"sections": n_stations, "points_per_section_factor": res, "nodes": len(allpts), "triangles": len(all_tri),
            "skin_triangles_under_sections": n_region, "offset_folds": folds, "members_vertices": used, "tubes": info}
    model = (allpts, all_tri, kind, elements, links)
    return row, mesh, extra, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="published density only")
    a = ap.parse_args()
    P, geo = geometry()
    stations = np.arange(-600, 2451, 50.0)
    densities = [(bs.N_STATIONS, 1.0)] if a.quick else [(210, 0.5), (300, 0.71), (bs.N_STATIONS, 1.0)]
    rows, meshes = [], []
    for n, res in densities:
        row, mesh, extra, model = solve_density(n, res, P, geo, stations, n == bs.N_STATIONS)
        rows.append(row)
        meshes.append(mesh)
    results = {name: {"mass_kg": rows[-1][name][1], "K": [r[name][0] for r in rows],
                      "K_repeats": [r[name][2] for r in rows],
                      "K_per_kg": [round(r[name][0] / rows[-1][name][1], 1) for r in rows],
                      "twist_deg": [None if np.isnan(x) else round(x, 5) for x in extra[name]]}
               for name in rows[-1]}
    doc = {
        "model": "shell-and-beam model of the closed-ring PicoGK study (../picogk-rings/); torsion load case of torsion.py",
        "classification": "values of this model under this load, not of a vehicle; prohibited_pending_engineering",
        "members": {"tubes": "B32 beams, solid circular section equivalent to each tube (area, bending, torsion); "
                              f"nodes welded within {WELD_MM:.0f} mm; tied to the nearest skin node within radius + {LINK_REACH_MM:.0f} mm "
                              f"by {LINK_DIAMETER_MM:.0f} mm beams at {LINK_E:.0f} MPa",
                    "sills_and_tunnel": "skin bands with an inner wall, as torsion_monocoque.py",
                    "sandwich": "faces only for stiffness; faces and core in the mass",
                    "params": "../picogk-rings/params/monocoque-f0.json"},
        "meshes": meshes,
        "mesh_note": "K lists are at the densities of 'meshes', coarsest first, each the median of K_repeats",
        "twist_stations_d_mm": stations.tolist(),
        "cases": results,
    }
    OUT_JSON.write_text(json.dumps(doc, indent=1) + "\n")
    allpts, all_tri, kind, elements, links = model
    segs = np.vstack([e[:, [0, 2]] for e in elements.values() if len(e)])
    np.savez_compressed(OUT_NPZ, points=allpts.astype(np.float32), triangles=all_tri.astype(np.int32),
                        kind=kind.astype(np.uint8), tube_segments=segs.astype(np.int32), links=links[:, [0, 2]].astype(np.int32))
    print(f"wrote {OUT_JSON.name} and {OUT_NPZ.name}")


if __name__ == "__main__":
    main()
