"""Torsion of the closed-ring PicoGK study with its tubes meshed as shells.

torsion_rings.py modelled the tubes of ../picogk-rings/ as beams. A beam
section cannot ovalize, so its result followed the bond width assumed, from
23,665 to 57,508 N.m/deg, and the ranking against the skin-formed boxes
could not be settled. Here every tube is a shell of its own wall:

- each member path is cut at the skin's own section spacing (18, 12.6 and
  9 mm on the three meshes); at each station a ring of nodes on the tube's
  mid-surface (radius = outer radius minus half the wall), about as many as
  keep the elements square, the section frame carried along the path so
  the mesh does not twist; quadrilaterals split into S3 triangles. A tube
  mesh kept fixed while the skin is refined does not converge: the bond
  line becomes ever sparser point ties, which sink into the finer skin;
- the bond is the line of tangency: at each station, the node nearest the
  skin is tied (translations, *EQUATION) to the skin triangle under it,
  with its barycentric weights. Tying more generators around the tube was
  tried and rejected: those nodes sit above the skin and the ties then
  over-constrain the section (a cantilever check came out stiffer than
  composite beam theory, which is impossible). A real bonded flange is
  stiffer than a line, so this is the conservative bond;
- where tubes meet, every node of a tube's end ring is tied to the nearest
  node of another tube within JOINT_MM, so the rings join as PicoGK fuses
  them;
- sills, tunnel, floor and bulkheads exactly as torsion_rings.py.

Checked on a cantilever plate with a Ø60 x 3 mm tube tied along its line of
tangency: the tip deflection converges (1.358, 1.414, 1.439, 1.443 mm over
four meshes) to 9% softer than composite beam theory, which assumes rigid
sections and full shear transfer.

Same load case, three meshes, every K the value two solves agree on. Values
of this model, not of a vehicle.

    python3 torsion_shell_tubes.py      # cadsim image, shapely from the PYLIB
"""
import json
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import build_shell as bs  # noqa: E402
import torsion as tr  # noqa: E402
import torsion_monocoque as tm  # noqa: E402
import torsion_rings as trg  # noqa: E402

OUT_JSON = HERE.parent / "derived" / "torsion-shell-tubes.json"
OUT_NPZ = HERE.parent / "derived" / "torsion-shell-tubes-model.npz"
SEGMENT_MM = 15.0              # set per mesh by solve_density: the skin's section spacing
N_AROUND = 16                  # likewise, so the tube's elements are about square
JOINT_MM = 12.0
BOND_REACH_MM = 40.0           # a station whose tangent node is farther from the skin is not bonded


def resample(q, step):
    out = [q[0]]
    for a, b in zip(q[:-1], q[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
    return np.array(out)


def closest_on_triangles(x, pts, tri, centroids_tree, centroids_k=12):
    """Closest point of the skin to x: triangle index and clamped
    barycentric weights."""
    _, cand = centroids_tree.query(x, k=centroids_k)
    best = None
    for t in np.atleast_1d(cand):
        a, b, c = pts[tri[t]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        y = x - np.dot(x - a, n) * n
        m = np.array([b - a, c - a]).T
        uv, *_ = np.linalg.lstsq(m, y - a, rcond=None)
        w = np.clip(np.array([1 - uv.sum(), uv[0], uv[1]]), 0, 1)
        w /= w.sum()
        d = np.linalg.norm(w @ np.array([a, b, c]) - x)
        if best is None or d < best[0]:
            best = (d, t, w)
    return best


def shell_tubes(P, geo, pts, skin_tri, n_skin):
    """New nodes, tube triangles per group, bond and joint equations."""
    tree = cKDTree(pts[skin_tri].mean(axis=1))
    skin_nodes = cKDTree(pts[np.unique(skin_tri)])
    nodes, tris, rings_of, eqs, info = [], {g: [] for g in trg.GROUPS}, [], [], {"stations": 0, "bonded": 0}
    base = len(pts)
    for name, path in geo["paths"].items():
        g = path["group"]
        od, wall = P[f"{trg.GROUPS[g]}_od_mm"], P[f"{trg.GROUPS[g]}_wall_mm"]
        rm = od / 2 - wall / 2
        axis = resample(np.array(path["points"], float), SEGMENT_MM)
        tang = np.gradient(axis, axis=0)
        tang /= np.linalg.norm(tang, axis=1, keepdims=True)
        rings = []
        e1 = None
        for i, (c, t) in enumerate(zip(axis, tang)):
            d, tri_i, w = closest_on_triangles(c, pts, skin_tri, tree)
            toward = w @ pts[skin_tri[tri_i]] - c
            if e1 is None:
                e1 = toward - np.dot(toward, t) * t
            else:                                        # carried along the path: no twist
                e1 = e1 - np.dot(e1, t) * t
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(t, e1)
            ring = []
            for k in range(N_AROUND):
                th = 2 * np.pi * k / N_AROUND
                nodes.append(c + rm * (np.cos(th) * e1 + np.sin(th) * e2))
                ring.append(base + len(nodes) - 1)
            rings.append(ring)
            info["stations"] += 1
            # bond: the ring node nearest the skin, on the line of tangency
            rp = np.array([nodes[n - base] for n in ring])
            k = int(np.argmin(skin_nodes.query(rp)[0]))
            dk = closest_on_triangles(rp[k], pts, skin_tri, tree)
            if dk[0] < wall / 2 + BOND_REACH_MM:
                eqs.append((ring[k], [(int(skin_tri[dk[1]][j]), float(dk[2][j])) for j in range(3) if dk[2][j] > 1e-6]))
                info["bonded"] += 1
        for r0, r1 in zip(rings[:-1], rings[1:]):
            for k in range(N_AROUND):
                a, b, c, d = r0[k], r1[k], r1[(k + 1) % N_AROUND], r0[(k + 1) % N_AROUND]
                tris[g] += [(a, b, c), (a, c, d)]
        rings_of.append((name, rings))
    allpts = np.vstack([pts, np.array(nodes)])
    # joints: end rings tied to the nearest node of another tube
    owner = np.empty(len(nodes), int)
    for j, (_, rings) in enumerate(rings_of):
        for r in rings:
            owner[np.array(r) - base] = j
    tube_tree = cKDTree(np.array(nodes))
    dependent = {e[0] for e in eqs}
    independent = set()                          # a node used on the right is never made dependent: no cycles
    joints = 0
    for j, (_, rings) in enumerate(rings_of):
        for r in (rings[0], rings[-1]):
            for n in r:
                if n in dependent or n in independent:
                    continue
                for m in tube_tree.query_ball_point(allpts[n], JOINT_MM):
                    if owner[m] != j and base + m not in dependent:
                        eqs.append((n, [(base + int(m), 1.0)]))
                        dependent.add(n)
                        independent.add(base + int(m))
                        joints += 1
                        break
    info["joint_ties"] = joints
    info["tube_triangles"] = int(sum(len(v) for v in tris.values()))
    return allpts, {g: np.array(v, int).reshape(-1, 3) for g, v in tris.items()}, eqs, info


def cases(P, kind, area_shell, tube_tris, allpts):
    """{name: (sections, mass kg)}; tubes are shell sections appended after
    the shell model's triangles."""
    out = {}
    n_shell = len(kind)
    offsets, start = {}, n_shell
    for g, t in tube_tris.items():
        offsets[g] = (start, start + len(t))
        start += len(t)
    tube_area = {g: tm.areas(allpts, t).sum() if len(t) else 0.0 for g, t in tube_tris.items()}
    for name, e_mod, nu, rho, skin, wall, face, tube_wall in (
            ("rings, 0.8 mm steel", tm.STEEL["E"], tm.STEEL["nu"], tm.STEEL["rho"], 0.8, 0.8, 0.4, lambda g: 0.8),
            ("rings, CFRP layup", tm.CARBON["E"], tm.CARBON["nu"], tm.CARBON["rho"], P["skin_thickness_mm"], P["sill_wall_mm"],
             P["panel_skin_mm"], lambda g: P[f"{trg.GROUPS[g]}_wall_mm"])):
        steel = name.startswith("rings, 0.8")
        core = 0.0 if steel else (P["panel_thickness_mm"] - 2 * P["panel_skin_mm"]) * P["core_density_g_cm3"]
        secs, mass = [], 0.0
        total = start
        for k, t, kg_m2 in ((0, skin, skin * rho), (1, wall, wall * rho), (2, 2 * face, 2 * face * rho + core),
                            (3, 2 * face, 2 * face * rho + core)):
            m = np.zeros(total, bool)
            m[:n_shell] = kind == k
            secs.append((m, t, e_mod, nu))
            mass += float(area_shell[kind == k].sum() * 1e-6 * kg_m2)
        shells_only = list(secs)
        for g, (a, b) in offsets.items():
            if b == a:
                continue
            m = np.zeros(total, bool)
            m[a:b] = True
            secs.append((m, tube_wall(g), e_mod, nu))
            mass += float(tube_area[g] * 1e-6 * tube_wall(g) * rho)
        out[name] = (secs, mass, True)
        if not steel:
            out["rings without tubes, CFRP layup"] = (shells_only, mass - sum(tube_area[g] * 1e-6 * tube_wall(g) * rho
                                                                               for g in offsets), False)
    return out


def solve_density(n_stations, res, P, geo, stations, keep_fields):
    """The tube mesh is refined with the skin's: a fixed tube mesh on a
    finer skin turns the bond line into ever sparser point ties, which sink
    (K lost 17% per refinement that way)."""
    global SEGMENT_MM, N_AROUND
    SEGMENT_MM = 3780.0 / (n_stations - 1)
    N_AROUND = int(np.clip(round(2 * np.pi * 28.0 / SEGMENT_MM), 12, 24))
    s = None if n_stations == bs.N_STATIONS and res == 1.0 else bs.structural(n_stations, res)[2]
    s, p, tri = tr.load_shell(s)
    rear, fl, fr = tr.supports(s, p)
    pts, all_tri, kind, *_ = tm.build(s, p, tri, trg.bands(P, geo))
    skin_tri = all_tri[:len(tri)]
    allpts, tube_tris, eqs, info = shell_tubes(P, geo, pts, skin_tri, len(p))
    tri_all = np.vstack([all_tri] + [t for t in tube_tris.values() if len(t)])
    print(f"{n_stations} sections: {len(allpts)} nodes, {len(tri_all)} triangles ({info['tube_triangles']} in tubes), "
          f"{info['bonded']} of {info['stations']} stations bonded, {info['joint_ties']} joint ties", flush=True)
    row, extra = {}, {}
    for name, (secs, mass, with_tubes) in cases(P, kind, tm.areas(pts, all_tri), tube_tris, allpts).items():
        k, u, vm, reps = tm.solve_repeated(allpts, tri_all, secs, rear, fl, fr, equations=eqs if with_tubes else ())
        row[name] = (round(k), round(mass, 1), reps)
        if keep_fields:
            extra[name] = tm.twist(pts, u[:len(pts)], s, stations)
        print(f"  {name:32s} K = {k:7.0f} N.m/deg (runs {reps}), mass {mass:6.1f} kg", flush=True)
    return row, dict(sections=n_stations, segment_mm=round(SEGMENT_MM, 1), around=N_AROUND, nodes=len(allpts),
                     triangles=len(tri_all), **info), extra, (allpts, tri_all, len(all_tri))


def main():
    P, geo = trg.geometry()
    stations = np.arange(-600, 2451, 50.0)
    rows, meshes = [], []
    for n, res in trg.DENSITIES:
        row, mesh, extra, model = solve_density(n, res, P, geo, stations, n == bs.N_STATIONS)
        rows.append(row)
        meshes.append(mesh)
    doc = {
        "model": "closed-ring PicoGK study (../picogk-rings/) with its tubes meshed as shells; torsion load case of torsion.py",
        "classification": "values of this model under this load, not of a vehicle; prohibited_pending_engineering",
        "tubes": "S3 shells of each tube's wall, stations at the skin's section spacing, nodes around in proportion; "
                 "bonded along the line of tangency to the skin triangle under it (*EQUATION, translations); "
                 f"end rings tied to another tube's nearest node within {JOINT_MM:.0f} mm",
        "check": "cantilever plate with a tube tied along its line of tangency: converges to 9% softer than composite beam theory",
        "meshes": meshes,
        "twist_stations_d_mm": stations.tolist(),
        "cases": {name: {"mass_kg": rows[-1][name][1], "K": [r[name][0] for r in rows], "K_repeats": [r[name][2] for r in rows],
                         "K_per_kg": [round(r[name][0] / rows[-1][name][1], 1) for r in rows],
                         "twist_deg": [None if np.isnan(x) else round(x, 5) for x in extra[name]]}
                  for name in rows[-1]},
    }
    OUT_JSON.write_text(json.dumps(doc, indent=1) + "\n")
    allpts, tri_all, n_shell = model
    np.savez_compressed(OUT_NPZ, points=allpts.astype(np.float32), triangles=tri_all.astype(np.int32), n_shell=n_shell)
    print(f"wrote {OUT_JSON.name} and {OUT_NPZ.name}")


if __name__ == "__main__":
    main()
