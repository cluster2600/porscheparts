"""Port domain under a declared continuation rule (H17), and the unchanged audit on it.

The scan sections of each port stop where the section stops being a tube,
before the valve pocket (params/port-fit.json). Issue #697 asks for the
winding-number closure beyond that point to be replaced only by a declared,
sourced or explicitly assumed rule. This script applies one rule, declared
before any number was read, and states what the result is made of:

  1. loft: the scan sections of params/port-fit.json, as port_loft.py uses
     them (observed where an acquired facet lies within OBSERVED_MM);
  2. bowl (H17, declared): the convex hull of the last scan section, with the
     guide boss taken out of its outline, and the fitted throat circle at the
     cam-side end of the throat window. The rule adds no port dimension of
     its own: the hull is the smallest convex volume holding both outlines,
     and its one setting is the BOSS_MARGIN_MM that finds the boss rays;
  3. throat (fitted): a tube about the valve's datum axis with the fitted
     throat diameter, widening along the fitted seat cone, from the top of
     the throat window down to the seat mid-band;
  4. guide (fitted diameter): a cylinder of the fitted port-end guide outside
     diameter, from the fitted guide tip upward, is subtracted.

The domain is the Manifold union of 1 to 3 minus 4. Stations run every
STEP_MM along the loft, along the straight line through the bowl and along
the valve axis through the throat; each carries RAYS wall points, and the
share of those within OBSERVED_MM of an acquired facet is computed as
fit_ports.py does. The admissibility gates are applied by
audit_port_domain.audit, unchanged.

Every section of the bowl and the throat is closed because the rule makes it
so: gate 1 passing on this domain is a property of the rule, not of the head.

Usage: port_domain.py PRIVATE_DIR PARAMS_DIR HYPOTHESES.json OUT_DIR
  PRIVATE_DIR  the twin's private directory (port-sections.npz, bare-scan-twin.npz), read only
  OUT_DIR      new private outputs: domain meshes and station rings
Writes PARAMS_DIR/port-domain.json (scalars and hashes only).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_port_domain import audit  # noqa: E402

RULE = "H17-port-continuation-declared"
PORT_VALVE = {"port_y_minus": "valve_y_minus", "port_y_plus": "valve_y_plus"}
BOSS_MARGIN_MM = 1.0
GUIDE_TIP_KEY = {"valve_y_minus": "valve_y_minus_guide_bore", "valve_y_plus": "valve_y_plus_guide_boss_port"}
GUIDE_OD_KEY = {"valve_y_minus": "valve_y_minus_guide_od_port", "valve_y_plus": "valve_y_plus_guide_boss_port"}
CIRCLE_SEGMENTS = 96
SLIVER_MM3 = 1e-3
OVERLAP_MM = 0.5


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ring_points(centre, u, v, radii):
    ang = np.linspace(0.0, 2 * np.pi, len(radii), endpoint=False)
    return centre + (radii * np.cos(ang))[:, None] * u + (radii * np.sin(ang))[:, None] * v


def frame_for(d, ref):
    u = ref - (ref @ d) * d
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(d, [1.0, 0.0, 0.0])
    u = unit(u)
    return u, np.cross(d, u)


def remove_boss(ring, radii, axis_point, axis_dir, r_boss):
    """Radii with the rays that end on the guide boss replaced by periodic interpolation.

    A ray ends on the boss when its wall point lies within r_boss +
    BOSS_MARGIN_MM of the valve axis. Returns the new radii and the count replaced.
    """

    rel = ring - axis_point
    dist = np.linalg.norm(rel - np.outer(rel @ axis_dir, axis_dir), axis=1)
    boss = dist <= r_boss + BOSS_MARGIN_MM
    if not boss.any():
        return radii.copy(), 0
    if boss.all():
        raise ValueError("every ray of the section ends on the guide boss")
    k = np.arange(len(radii))
    out = radii.copy()
    out[boss] = np.interp(k[boss], k[~boss], radii[~boss], period=len(radii))
    return out, int(boss.sum())


def tube_mesh(rings):
    """Closed triangle mesh through stacked rings of equal point count, both ends capped, outward."""

    rings = np.asarray(rings, dtype=float)
    n_ring, n = rings.shape[:2]
    v = list(rings.reshape(-1, 3))
    faces = []
    for i in range(n_ring - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c, d = (i + 1) * n + j, (i + 1) * n + (j + 1) % n
            faces += [(a, c, b), (b, c, d)]
    for i, first in ((0, True), (n_ring - 1, False)):
        ci = len(v)
        v.append(rings[i].mean(axis=0))
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            faces.append((ci, a, b) if first else (ci, b, a))
    v, f = np.asarray(v), np.asarray(faces, dtype=np.int64)
    tri = v[f]
    if np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() < 0:
        f = f[:, ::-1]
    return v, f


def convex_exit(verts, tris, centre, u, v, rays):
    """Exit point of each ray from a convex closed mesh, from an inner centre in the plane (u, v).

    Each triangle gives a supporting plane n.x <= h; a ray c + s r leaves the
    solid at the smallest (h - n.c) / (n.r) over the planes it moves toward.
    Returns NaN rows if the centre is not inside.
    """

    tri = verts[tris]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    good = np.linalg.norm(n, axis=1) > 1e-12
    n = n[good] / np.linalg.norm(n[good], axis=1)[:, None]
    h = np.einsum("ij,ij->i", n, tri[good, 0])
    slack = h - n @ centre
    if (slack < -1e-9).any():
        return np.full((rays, 3), np.nan)
    ang = np.linspace(0.0, 2 * np.pi, rays, endpoint=False)
    dirs = np.outer(np.cos(ang), u) + np.outer(np.sin(ang), v)
    rate = dirs @ n.T
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(rate > 1e-12, slack[None, :] / rate, np.inf).min(axis=1)
    return centre + s[:, None] * dirs


def build_port(name, sections, fits, step, obs_mm, rays, tree):
    import manifold3d as m3
    import trimesh

    regions = {r["id"]: r for r in fits["regions"]}
    valve = PORT_VALVE[name]
    datum = fits["group_datums"][valve]
    p0, d = np.asarray(datum["axis_point"], float), unit(datum["axis_direction"])

    def about(rid):
        return regions[rid]["to_group_datum"]["about_datum_axis"]

    throat, seat = about(f"{valve}_throat"), about(f"{valve}_seat")
    r_throat = 0.5 * throat["diameter_mm"]
    s_throat_top = throat["station_mm"] + regions[f"{valve}_throat"]["fit"]["station_range_mm"][1]
    s_seat, r_seat_mid = seat["station_mm"], 0.5 * seat["diameter_mm"]
    tan_seat = math.tan(math.radians(abs(seat["half_angle_deg"])))
    r_guide = 0.5 * about(GUIDE_OD_KEY[valve])["diameter_mm"]
    tip = regions[GUIDE_TIP_KEY[valve]]
    s_tip = tip["to_group_datum"]["station_on_datum_axis_mm"] + tip["fit"]["station_range_mm"][0]

    c, t, u, v, radii, observed = (sections[k] for k in ("centre", "tangent", "u", "v", "radii", "observed"))
    loft_rings = [ring_points(c[i], u[i], v[i], radii[i]) for i in range(len(c))]
    loft_obs = [observed[i].astype(bool) for i in range(len(c))]

    def solid(vv, ff):
        s_ = m3.Manifold(m3.Mesh64(np.asarray(vv, np.float64), np.asarray(ff, np.uint64)))
        if s_.status() != m3.Error.NoError:
            raise ValueError(f"{name}: not an oriented 2-manifold: {s_.status()}")
        return s_

    # 2. bowl: convex hull of the boss-free last section and the throat-top circle.
    c_e, u_e, v_e = c[-1], u[-1], v[-1]
    r_end, boss_rays = remove_boss(loft_rings[-1], radii[-1], p0, d, r_guide)
    end_ring = ring_points(c_e, u_e, v_e, r_end)
    # The hull starts OVERLAP_MM inside the loft so that the two never share a face.
    hull_ring = end_ring - OVERLAP_MM * unit(t[-1])
    q_top = p0 + s_throat_top * d
    ua, va = frame_for(d, u_e)
    top_circle = ring_points(q_top, ua, va, np.full(CIRCLE_SEGMENTS, r_throat))
    bowl = m3.Manifold.hull_points(np.vstack([hull_ring, top_circle]))
    bowl_mesh = bowl.to_mesh64()
    bowl_v = np.asarray(bowl_mesh.vert_properties, dtype=np.float64)[:, :3]
    bowl_f = np.asarray(bowl_mesh.tri_verts, dtype=np.int64)
    line = q_top - c_e
    bowl_len = float(np.linalg.norm(line))
    n_bowl = max(2, int(round(bowl_len / step)))
    lu, lv = frame_for(unit(line), u_e)
    bowl_rings = []
    for k in range(1, n_bowl):
        ring = convex_exit(bowl_v, bowl_f, c_e + line * k / n_bowl, lu, lv, rays)
        if np.isnan(ring).any():
            raise ValueError(f"{name}: a bowl section is not closed")
        bowl_rings.append(ring)
    bowl_obs = [tree.query(r)[0] <= obs_mm for r in bowl_rings]

    # 3. throat: the fitted throat and seat cone, from the throat-window top to the seat mid-band.
    n_thr = max(1, int(round((s_throat_top - s_seat) / step)))
    thr_rings = []
    for k in range(n_thr + 1):
        s = s_throat_top - (s_throat_top - s_seat) * k / n_thr
        r = max(r_throat, r_seat_mid + (s_seat - s) * tan_seat)
        thr_rings.append(ring_points(p0 + s * d, ua, va, np.full(rays, r)))
    thr_obs = [tree.query(r)[0] <= obs_mm for r in thr_rings]

    # 4. guide: fitted port-end diameter, from the fitted tip upward. It is cut from the bowl and the
    # throat only: the scan sections of the loft already carry the boss where the scanner saw it.
    guide_rings = [ring_points(p0 + s * d, ua, va, np.full(CIRCLE_SEGMENTS, r_guide)) for s in (s_tip, s_tip + 80.0)]
    thr_solid_rings = [ring_points(p0 + s * d, ua, va, np.full(CIRCLE_SEGMENTS,
                       max(r_throat, r_seat_mid + (s_seat - s) * tan_seat)))
                       for s in np.linspace(s_throat_top, s_seat, n_thr + 1)]
    declared = m3.Manifold.batch_boolean([bowl, solid(*tube_mesh(thr_solid_rings))], m3.OpType.Add)
    domain = solid(*tube_mesh(loft_rings)) + (declared - solid(*tube_mesh(guide_rings)))
    pieces = domain.decompose()
    kept = [p for p in pieces if abs(p.volume()) > SLIVER_MM3]
    if len(kept) != 1:
        raise ValueError(f"{name}: the domain is {len(kept)} pieces")
    domain = kept[0]
    mesh = domain.to_mesh64()
    dv = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    df = np.asarray(mesh.tri_verts, dtype=np.int64)

    def share(obs_list):
        return round(float(np.mean(np.concatenate(obs_list))), 3) if obs_list else None

    all_obs = loft_obs + bowl_obs + thr_obs
    record = {
        "name": name,
        "valve": valve,
        "parts": {
            "loft": {"evidence": "scan sections of params/port-fit.json; an unobserved point is winding-number closure (H04)",
                     "stations": len(loft_rings), "observed_share": share(loft_obs)},
            "bowl": {"evidence": f"declared rule {RULE}: convex hull of the last scan section (guide boss removed) "
                                 "and the fitted throat circle at the top of the throat window",
                     "stations": len(bowl_rings), "length_mm": round(bowl_len, 2),
                     "guide_boss_rays_replaced": boss_rays, "observed_share": share(bowl_obs)},
            "throat": {"evidence": "fitted throat diameter and seat cone about the datum axis (params/feature-fits.json)",
                       "stations": len(thr_rings), "from_station_mm": round(s_throat_top, 2),
                       "to_station_mm": round(s_seat, 2), "diameter_mm": round(2 * r_throat, 3),
                       "observed_share": share(thr_obs)},
            "guide": {"evidence": "fitted port-end guide diameter, from the fitted guide tip upward; subtracted",
                      "diameter_mm": round(2 * r_guide, 3), "tip_station_mm": round(s_tip, 2)},
        },
        "stations": len(all_obs),
        "closed_stations": len(all_obs),
        "closed_by": "the scan for the loft; the declared rule for the bowl and the fitted features for the throat",
        "wall_points_observed_share": share(all_obs),
        "domain": {"volume_mm3": round(float(domain.volume()), 1), "genus": int(domain.genus()),
                   "slivers_dropped": len(pieces) - len(kept), "triangles": int(len(df))},
    }
    rings = {"loft": np.asarray(loft_rings), "bowl": np.asarray(bowl_rings), "throat": np.asarray(thr_rings)}
    return record, (dv, df), rings


def main(private, params, hypotheses, out):
    import trimesh
    from scipy.spatial import cKDTree

    from twin_common import face_geometry, write_json

    private, params, out = Path(private), Path(params), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fit = json.loads((params / "port-fit.json").read_text())
    fits = json.loads((params / "feature-fits.json").read_text())
    step, obs_mm, rays = fit["method"]["station_step_mm"], fit["method"]["observed_within_mm"], fit["method"]["rays"]
    raw = np.load(private / "port-sections.npz")
    bare = np.load(private / "bare-scan-twin.npz")
    cen, _, _ = face_geometry(bare["v"], bare["f"])
    tree = cKDTree(cen)

    ports, files = [], {}
    for name in PORT_VALVE:
        sections = {k.split("__")[1]: raw[k] for k in raw.files if k.startswith(name + "__")}
        rec, (dv, df), rings = build_port(name, sections, fits, step, obs_mm, rays, tree)
        stl = out / f"port-domain-{name}.stl"
        tm = trimesh.Trimesh(dv, df, process=False)
        tm.export(stl)
        np.savez_compressed(out / f"port-domain-{name}-rings.npz", **rings)
        # Manifold splits vertices along sharp edges; merge them (1e-6 mm) before counting edge uses.
        welded = trimesh.Trimesh(dv, df, process=False)
        welded.merge_vertices(digits_vertex=6)
        _, uses = np.unique(welded.edges_sorted, axis=0, return_counts=True)
        rec["domain"]["edges_not_used_twice_after_merge"] = int((uses != 2).sum())
        files[stl.name] = sha256_file(stl)
        ports.append(rec)
        print(name, rec["stations"], rec["wall_points_observed_share"],
              {p: q.get("observed_share") for p, q in rec["parts"].items()}, rec["domain"], flush=True)
    reg = json.loads(Path(hypotheses).read_text())
    like = {"method": {"station_step_mm": step},
            "ports": [{"name": p["name"], "stations": p["stations"], "closed_stations": p["closed_stations"],
                       "loft_length_mm": round((p["stations"] - 1) * step, 1),
                       "wall_points_observed_share": p["wall_points_observed_share"]} for p in ports]}
    gates = audit(like, reg)
    for p in ports:
        # Every station carries the same number of wall points, so gate 2 can be met only if the stations
        # added beyond the scan sections reach this share of acquired points.
        n, n_loft = p["stations"], p["parts"]["loft"]["stations"]
        p["gate_2_needs_on_added_stations"] = round(
            (gates["wall_observed_min"] * n - p["parts"]["loft"]["observed_share"] * n_loft) / (n - n_loft), 3)
    write_json(params / "port-domain.json", {
        "schema": "935-cad-twin-port-domain/1",
        "rule": RULE,
        "inputs": {"port_fit": "params/port-fit.json", "feature_fits": "params/feature-fits.json",
                   "observed_within_mm": obs_mm, "station_step_mm": step, "rays": rays,
                   "boss_margin_mm": BOSS_MARGIN_MM},
        "ports": ports,
        "audit_unchanged_gates": gates,
        "private_files_sha256": files,
        "claims": "a fluid domain under a declared continuation rule; it shows what the rule adds, not the port of "
                  "the specimen. Gate 1 passes by construction; gate 2 counts acquired facets only",
    })
    for p in gates["ports"]:
        print(p["name"], p["gates"], "admissible" if p["admissible"] else "not admissible")


if __name__ == "__main__":
    main(*sys.argv[1:5])
