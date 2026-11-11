"""v2 body: a loft through horizontal sections, closed into one solid.

Run f of fin_stack.py (prisms between fitted faces, analytic dome and port
cuts) stops at 69.9% of the acquired scan within 0.2 mm. Its error breakdown
shows why: the fins are rounded ribs and the pockets are curved, so a prism
with a mid-level sketch leaves a stair on every sloped wall, and the cast
"faces" are not planes within tolerance (plane fits leave 0.25 to 0.6 mm RMS).

This body keeps what the scan supports as exact features and lofts the rest:

- Machined faces normal to the bore axis are datum planes. They come from the
  0.02 mm level detector of fin_stack.levels(), and the section jumps across
  each of them: the body is a prism for FACE_CLEAR_MM on either side.
- Between two faces the body is a ruled loft through sections taken every
  --step mm. A section is the occupancy contour at that exact height (linear
  interpolation between voxel slices), simplified to POLY_TOL_MM.
- Rings of two consecutive sections are paired when they overlap enough
  (pair_rings). A paired ring is ruled to its partner; an unpaired ring stays
  vertical and ends on a flat cap at the next section. A band in which a long
  ring finds no partner is split at mid-height, down to MIN_STEP_MM.

Every polygon of every band is built as a closed, oriented triangle mesh
sharing its vertices between walls and caps. The meshes are then united with
Manifold, whose output is a manifold surface by construction; the result is
still checked here (watertight, winding, volume) and scored by score_twin.py,
which shares no code with this file. The body is a triangle solid, not a
B-rep.

Usage: loft_stack.py PRIVATE_DIR PARAMS_DIR LABEL [--step MM] [--workers N]
                     [--min-level-area A] [--no-faces]
Outputs (private): v2-loft-<label>.stl and .npz (the body), v2-loft-<label>/band-*.npz
        (params):  v2-loft-<label>-summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_brep import slice_region  # noqa: E402
from twin_common import face_geometry, write_json  # noqa: E402

FACE_CLEAR_MM = 0.25      # one voxel: the grid cannot place a wall closer to a face
POLY_TOL_MM = 0.05
MIN_RING_AREA_MM2 = 0.5
SEGMENT_MAX_MM = 1.0      # long straight edges are divided: needle triangles lose precision downstream
REFINE_EDGE_MM = 2.0      # longest edge left in the body's triangles
CRUMB_MAX_MM3 = 50.0      # a detached body smaller than this is dropped and counted
MATCH_IOU = 0.5
PAIR_REACH_MIN_MM = 0.6   # two paired rings may differ by this much ...
PAIR_REACH_SLOPE = 4.0    # ... or by this many times the band thickness, whichever is larger
LONG_RING_MM = 20.0       # an unpaired ring at least this long makes the band split in two
MIN_STEP_MM = 0.125       # ... until the band is this thin (half a voxel of the occupancy)
SHRINK_RETRY_MM = 0.01    # used only when a band is not a manifold as sampled

_G = {}


def plan_bands(faces, step):
    """Bands between consecutive faces as (z0, z1, sample0, sample1).

    A band whose two samples are equal is a prism. A gap too thin for two
    clearances is one prism sampled at its middle.
    """

    bands = []
    for f1, f2 in zip(faces[:-1], faces[1:]):
        gap = f2 - f1
        if gap <= 2 * FACE_CLEAR_MM + 1e-9:
            mid = 0.5 * (f1 + f2)
            bands.append((f1, f2, mid, mid))
            continue
        lo, hi = f1 + FACE_CLEAR_MM, f2 - FACE_CLEAR_MM
        n = max(1, int(np.ceil((hi - lo) / step - 1e-9))) if hi - lo > 1e-9 else 0
        q = np.linspace(lo, hi, n + 1) if n else np.array([lo])
        bands.append((f1, float(q[0]), float(q[0]), float(q[0])))
        bands += [(float(a), float(b), float(a), float(b)) for a, b in zip(q[:-1], q[1:])]
        bands.append((float(q[-1]), f2, float(q[-1]), float(q[-1])))
    return [b for b in bands if b[1] - b[0] > 1e-9]


def field_at(z):
    grid, wn = _G["grid"], _G["wn"]
    q = (z - grid["z0"]) / grid["pitch_mm"]
    k = int(np.clip(np.floor(q), 0, grid["shape"][2] - 2))
    t = float(np.clip(q - k, 0.0, 1.0))
    return (1 - t) * np.asarray(wn[:, :, k], dtype=np.float32) + t * np.asarray(wn[:, :, k + 1], dtype=np.float32)


def clean_region(region, shrink=0.0):
    """Simplified, oriented polygons (exterior CCW, holes CW) without specks."""

    from shapely import segmentize
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient

    if shrink:
        region = region.buffer(-shrink, join_style="mitre")
    out = []
    for poly in getattr(region, "geoms", [region]):
        if poly.is_empty or poly.geom_type != "Polygon":
            continue
        poly = poly.simplify(POLY_TOL_MM)
        if not poly.is_valid:
            poly = poly.buffer(0)
        for p in getattr(poly, "geoms", [poly]):
            if p.geom_type != "Polygon" or p.area < MIN_RING_AREA_MM2:
                continue
            holes = [r for r in p.interiors if Polygon(r).area >= MIN_RING_AREA_MM2]
            out.append(orient(segmentize(Polygon(p.exterior, holes), SEGMENT_MAX_MM), 1.0))
    return out


def region_at(z, shrink=0.0):
    return clean_region(slice_region(field_at(z), _G["grid"]), shrink)


def open_ring(ring):
    return np.asarray(ring.coords, dtype=np.float64)[:-1]


def signed_area(c):
    x, y = c[:, 0], c[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def pair_rings(polys_a, polys_b, reach):
    """For every ring of A, the coordinates of its partner in B, or None.

    Rings pair only with rings of the same kind (exterior or hole) and only
    when each is the other's best overlap. The overlap (intersection over
    union) must reach MATCH_IOU and also 1 - L * reach / A, the overlap left
    when a ring of length L and area A moves sideways by `reach` all along.
    A fixed threshold is not enough for a large ring: when the body splits in
    two between sections each half still overlaps the whole by one half, and
    ruling across that folds the wall (measured on 2026-11-10: one band lost
    44% of its volume). A whole-ring distance is too strict the other way: one
    small island joining a 900 mm outline disqualified the outline (ruled
    share of ring length 24%). The partner is returned with A's orientation.
    """

    from shapely.geometry import Polygon

    def rings(polys):
        out = []
        for pi, p in enumerate(polys):
            for ri, r in enumerate([p.exterior, *p.interiors]):
                c = open_ring(r)
                out.append({"poly": pi, "ring": ri, "hole": ri > 0, "coords": c, "fill": Polygon(c),
                            "length": r.length})
        return out

    ra, rb = rings(polys_a), rings(polys_b)
    iou = np.zeros((len(ra), len(rb)))
    for i, a in enumerate(ra):
        for j, b in enumerate(rb):
            if a["hole"] != b["hole"] or not a["fill"].intersects(b["fill"]):
                continue
            inter = a["fill"].intersection(b["fill"]).area
            iou[i, j] = inter / (a["fill"].area + b["fill"].area - inter)
    partner = {}
    for i, a in enumerate(ra):
        if not len(rb):
            break
        j = int(np.argmax(iou[i]))
        need = max(MATCH_IOU, 1.0 - a["length"] * reach / a["fill"].area)
        if iou[i, j] >= need and int(np.argmax(iou[:, j])) == i:
            c = rb[j]["coords"]
            if (signed_area(c) > 0) != (signed_area(a["coords"]) > 0):
                c = c[::-1]
            partner[(a["poly"], a["ring"])] = c
    return partner


def ruling_plans(poly, pi, partner):
    """Ways to build one polygon of a band, best first.

    Each plan is (bottom rings, top rings, holes to subtract, ruled rings):
      1. every paired ring ruled to its partner, unpaired rings vertical;
      2. if those rings do not form a valid polygon (typically a small unpaired
         hole under a wall that leans over it): the exterior and the paired
         holes ruled, and each unpaired hole subtracted afterwards as a prism;
      3. the prism of the polygon as sampled.
    """

    from shapely.geometry import Polygon

    own = [open_ring(r) for r in [poly.exterior, *poly.interiors]]
    paired = [ri for ri in range(len(own)) if (pi, ri) in partner]
    plans = []
    if paired:
        new = [partner.get((pi, ri), own[ri]) for ri in range(len(own))]
        if Polygon(new[0], new[1:]).is_valid:
            plans.append((own, new, [], len(paired)))
        keep = [0] + [ri for ri in paired if ri > 0]
        loose = [own[ri] for ri in range(1, len(own)) if ri not in paired]
        new = [partner.get((pi, ri), own[ri]) for ri in keep]
        if loose and Polygon(new[0], new[1:]).is_valid:
            plans.append(([own[ri] for ri in keep], new, loose, len(paired)))
    plans.append((own, own, [], 0))
    return plans


def stitch(a, b):
    """Triangles of the wall between ring a (below) and ring b (above).

    Only the rings' own vertices are used, so a ring carries the same vertices
    in the band below and in the band above. Each vertex of b is located by its
    closest point on a; the two rings are then walked together in that order.
    Returns (rolled b, triangles) with triangle entries (ring, index), ring 0
    for a and 1 for b.
    """

    from shapely import line_locate_point, points
    from shapely.geometry import LineString

    n, m = len(a), len(b)
    loop = LineString(np.vstack((a, a[:1])))
    length = loop.length
    ta = np.cumsum(np.hypot(*(np.roll(a, -1, axis=0) - a).T))   # key of each advance along a
    ta[-1] = length
    b = np.roll(b, -int(np.argmin(np.hypot(*(b - a[0]).T))), axis=0)
    tb = np.asarray(line_locate_point(loop, points(b)), dtype=np.float64)
    if tb[0] > 0.5 * length:
        tb[0] -= length
    d = np.diff(tb)
    d[d < -0.5 * length] += length
    d[d > 0.5 * length] -= length
    tb = np.maximum.accumulate(tb[0] + np.concatenate(([0.0], np.cumsum(d))))
    tb = np.minimum(tb, tb[0] + length)
    tb_next = np.concatenate((tb[1:], [tb[0] + length]))
    keys = np.concatenate((ta, tb_next))
    is_a = np.concatenate((np.ones(n, dtype=bool), np.zeros(m, dtype=bool)))
    order = np.argsort(keys, kind="stable")
    is_a = is_a[order]
    i = np.concatenate(([0], np.cumsum(is_a)[:-1]))   # advances of a made before each event
    j = np.concatenate(([0], np.cumsum(~is_a)[:-1]))
    tris = np.empty((n + m, 3, 2), dtype=np.int64)
    tris[is_a] = np.stack((np.stack((np.zeros(n, int), i[is_a] % n), 1),
                           np.stack((np.zeros(n, int), (i[is_a] + 1) % n), 1),
                           np.stack((np.ones(n, int), j[is_a] % m), 1)), 1)
    tris[~is_a] = np.stack((np.stack((np.zeros(m, int), i[~is_a] % n), 1),
                            np.stack((np.ones(m, int), (j[~is_a] + 1) % m), 1),
                            np.stack((np.ones(m, int), j[~is_a] % m), 1)), 1)
    return b, tris


def cap_triangles(rings, index):
    """Triangles of the polygon with these rings, as vertex indices, CCW."""

    from shapely import constrained_delaunay_triangles, get_coordinates, get_parts
    from shapely.geometry import Polygon

    poly = Polygon(rings[0], rings[1:])
    parts = [g for g in get_parts(constrained_delaunay_triangles(poly)) if g.geom_type == "Polygon"]
    xy = np.array([get_coordinates(g)[:3] for g in parts]).reshape(-1, 3, 2)
    tri = np.array([[index[(float(x), float(y))] for x, y in t] for t in xy], dtype=np.int64).reshape(-1, 3)
    e1, e2 = xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0]
    flip = (e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) < 0
    tri[flip] = tri[flip][:, ::-1]
    return tri


def polygon_mesh(bottom, top, z0, z1):
    """Closed oriented mesh between two ring sets: bottom cap, walls, top cap.

    Ring 0 is the exterior (counter-clockwise), the others are holes
    (clockwise); bottom and top hold the same number of rings.
    """

    verts, faces, off, idx_b, idx_t, new_top = [], [], 0, {}, {}, []
    for a, b in zip(bottom, top):
        b, tris = stitch(a, b)
        new_top.append(b)
        oa, ob = off, off + len(a)
        verts += [np.column_stack((a, np.full(len(a), z0))), np.column_stack((b, np.full(len(b), z1)))]
        faces.append(np.where(tris[:, :, 0] == 0, oa, ob) + tris[:, :, 1])
        for k, (x, y) in enumerate(a):
            idx_b[(float(x), float(y))] = oa + k
        for k, (x, y) in enumerate(b):
            idx_t[(float(x), float(y))] = ob + k
        off = ob + len(b)
    faces.append(cap_triangles(bottom, idx_b)[:, ::-1])
    faces.append(cap_triangles(new_top, idx_t))
    return np.vstack(verts), np.vstack(faces)


def as_manifold(v, f):
    import manifold3d as m3

    solid = m3.Manifold(m3.Mesh64(np.asarray(v, dtype=np.float64), np.asarray(f, dtype=np.uint64)))
    if solid.status() != m3.Error.NoError:
        raise ValueError(f"not an oriented 2-manifold: {solid.status()}")
    return solid


def is_manifold(v, f):
    try:
        as_manifold(v, f)
    except ValueError:
        return False
    return True


def polygon_solid(plan, z0, z1):
    """Mesh arrays of one plan of ruling_plans()."""

    import manifold3d as m3

    bottom, top, loose, _ = plan
    v, f = polygon_mesh(bottom, top, z0, z1)
    solid = as_manifold(v, f)
    if not loose:
        return v, f
    for hole in loose:
        ring = hole[::-1]                      # a hole is clockwise; its prism needs a CCW exterior
        solid -= as_manifold(*polygon_mesh([ring], [ring], z0, z1))
    if solid.status() != m3.Error.NoError:
        raise ValueError(f"subtraction failed: {solid.status()}")
    mesh = solid.to_mesh64()
    return np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3], np.asarray(mesh.tri_verts, dtype=np.int64)


def build_slab(z0, z1, s0, s1, shrink, notes, depth=0):
    """Solids between z0 and z1, splitting the band where a long ring finds no partner.

    Returns a list of (v, f, stats) per polygon solid, or None when a polygon
    gives no manifold even as a prism. s0 and s1 are the heights at which the
    bottom and top sections are sampled; a prism has s0 == s1.
    """

    polys_a = region_at(s0, shrink)
    if not polys_a:
        return []
    ruled_band = s1 != s0 and not shrink
    partner = {}
    if ruled_band:
        reach = max(PAIR_REACH_MIN_MM, PAIR_REACH_SLOPE * (z1 - z0))
        partner = pair_rings(polys_a, region_at(s1), reach)
        orphan = sum(r.length for pi, p in enumerate(polys_a) for ri, r in enumerate([p.exterior, *p.interiors])
                     if (pi, ri) not in partner and r.length >= LONG_RING_MM)
        if orphan and z1 - z0 > 2 * MIN_STEP_MM - 1e-9:
            mid = 0.5 * (z0 + z1)
            lower = build_slab(z0, mid, z0, mid, shrink, notes, depth + 1)
            upper = build_slab(mid, z1, mid, z1, shrink, notes, depth + 1)
            return None if lower is None or upper is None else lower + upper
    out = []
    for pi, p in enumerate(polys_a):
        rings = [p.exterior, *p.interiors]
        for plan in ruling_plans(p, pi, partner):
            try:
                v, f = polygon_solid(plan, z0, z1)
            except Exception as exc:  # recorded, never hidden
                notes.append(f"z={s0:.3f} polygon {pi} ({plan[3]} ruled, {len(plan[2])} cut): {exc!r}"[:160])
                continue
            out.append((v, f, {
                "rings": len(rings), "ruled_rings": plan[3], "prism": 0 if plan[3] else 1,
                "holes_cut": len(plan[2]), "length": sum(r.length for r in rings),
                "ruled_length": sum(r.length for ri, r in enumerate(rings) if (pi, ri) in partner) if plan[3] else 0.0,
                "ruled_band": ruled_band, "depth": depth, "dz": z1 - z0}))
            break
        else:
            return None
    return out


def build_band(job):
    """One closed mesh per polygon of the band, saved with the band's statistics.

    Each polygon takes the first plan of ruling_plans() that gives a manifold.
    Polygons of one band may overlap after ruling (a small island below a wall
    that leans over it); the union resolves that. A ruled band in which a long
    ring finds no partner is split at mid-height, down to MIN_STEP_MM, so that
    a change of topology costs a thin prism instead of a thick one. If a
    polygon gives no manifold even as a prism, the band is rebuilt as prisms of
    the section shrunk by SHRINK_RETRY_MM.
    """

    idx, z0, z1, s0, s1, out_dir = job
    rec = {"index": idx, "z": [round(z0, 4), round(z1, 4)], "ruled_requested": s1 != s0}
    notes = []
    for shrink in (0.0, SHRINK_RETRY_MM):
        parts = build_slab(z0, z1, s0, s1, shrink, notes)
        if parts is None:
            continue
        if not parts:
            return {**rec, "empty": True, "triangles": 0}
        sizes = np.cumsum([0] + [len(v) for v, _, _ in parts])
        np.savez(Path(out_dir) / f"band-{idx:04d}.npz", v=np.vstack([v for v, _, _ in parts]),
                 f=np.vstack([f + o for (_, f, _), o in zip(parts, sizes)]),
                 tri_part=np.concatenate([np.full(len(f), k) for k, (_, f, _) in enumerate(parts)]))
        st = [q for _, _, q in parts]
        in_ruled = [q for q in st if q["ruled_band"]]
        return {**rec, "shrunk": bool(shrink), "polygons": len(parts),
                "split": bool(any(q["depth"] for q in st)),
                "thinnest_slab_mm": round(min(q["dz"] for q in st), 4),
                "polygons_prism": sum(q["prism"] for q in in_ruled),
                "rings": sum(q["rings"] for q in in_ruled), "ruled_rings": sum(q["ruled_rings"] for q in st),
                "holes_cut_as_prisms": sum(q["holes_cut"] for q in st),
                "ring_length_mm": sum(q["length"] for q in in_ruled),
                "ruled_length_mm": sum(q["ruled_length"] for q in st),
                "triangles": int(sum(len(f) for _, f, _ in parts)), "notes": notes}
    return {**rec, "failed": True, "triangles": 0, "notes": notes}


def _init(private):
    private = Path(private)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    _G.update(grid=grid, wn=np.load(private / grid["array"], mmap_mode="r"))


def unite(files):
    """Union of every polygon solid of every band; returns the pieces too."""

    import manifold3d as m3

    parts = []
    for file in files:
        d = np.load(file)
        for k in np.unique(d["tri_part"]):
            f = d["f"][d["tri_part"] == k]
            used, inv = np.unique(f, return_inverse=True)
            parts.append(m3.Manifold(m3.Mesh64(d["v"][used].astype(np.float64), inv.reshape(-1, 3).astype(np.uint64))))
    return m3.Manifold.batch_boolean(parts, m3.OpType.Add), len(parts)


def mesh_arrays(body):
    mesh = body.to_mesh64()
    return np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3], np.asarray(mesh.tri_verts, dtype=np.int64)


def main(argv):
    from fin_stack import levels

    ap = argparse.ArgumentParser()
    ap.add_argument("private")
    ap.add_argument("params")
    ap.add_argument("label")
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-level-area", type=float, default=150.0)
    ap.add_argument("--no-faces", action="store_true", help="sections only, no datum faces (comparison run)")
    a = ap.parse_args(argv)
    private, params = Path(a.private), Path(a.params)
    t0 = time.time()
    bare = np.load(private / "bare-scan-twin.npz")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    grid = json.loads((private / "occupancy-grid.json").read_text())
    wn = np.load(private / grid["array"], mmap_mode="r")
    h = grid["pitch_mm"]
    zs = grid["z0"] + h * np.arange(grid["shape"][2])
    occupied = [k for k in range(len(zs)) if (np.asarray(wn[:, :, k]) > 0.5).any()]
    z_lo, z_hi = float(zs[occupied[0]] - h / 2), float(zs[occupied[-1]] + h / 2)
    found = [] if a.no_faces else [z for z, _ in levels(cen, n, area, z_lo + 0.1, z_hi - 0.1, a.min_level_area)]
    faces = [z_lo, *sorted(found), z_hi]
    bands = plan_bands(faces, a.step)
    out_dir = private / f"v2-loft-{a.label}"
    out_dir.mkdir(exist_ok=False)
    jobs = [(i, *b, str(out_dir)) for i, b in enumerate(bands)]
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(str(private),)) as pool:
        recs = list(pool.map(build_band, jobs, chunksize=4))
    t_build = time.time() - t0
    built = [r for r in recs if r["triangles"]]
    failed = [r for r in recs if r.get("failed")]

    import manifold3d as m3
    import trimesh

    whole, n_parts = unite([out_dir / f"band-{r['index']:04d}.npz" for r in built])
    t_union = time.time() - t0 - t_build
    # The largest piece is the head. A piece of negative volume is an enclosed
    # void and stays with it. Small positive pieces are islands that some
    # sections hold and their neighbours do not; they are counted and dropped.
    pieces = sorted(whole.decompose(), key=lambda b: -b.volume())
    crumbs = [b for b in pieces[1:] if 0 < b.volume() < CRUMB_MAX_MM3]
    voids = [b for b in pieces if b.volume() < 0]
    kept = [b for b in pieces if b not in crumbs]
    # The union leaves cap triangles tens of millimetres long and a fraction of
    # a millimetre wide. A single-precision distance kernel loses up to 0.02 mm
    # on them (measured with score_twin's oracle), so long edges are divided.
    # The surface does not move: new vertices lie on the existing triangles.
    body = m3.Manifold.compose(kept).refine_to_length(REFINE_EDGE_MM)
    v, f = mesh_arrays(body)
    mesh = trimesh.Trimesh(v, f, process=False)
    mesh.export(private / f"v2-loft-{a.label}.stl")
    np.savez(private / f"v2-loft-{a.label}.npz", v=v, f=f)    # double precision, indexed
    tri = v[f]
    nz = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    tri_area = 0.5 * np.linalg.norm(nz, axis=1)
    unit_z = np.abs(nz[:, 2]) / np.maximum(2 * tri_area, 1e-30)
    total = float(tri_area.sum())
    summary = {
        "schema": "935-cad-twin-v2-loft/1",
        "label": a.label,
        "section_step_mm": a.step,
        "face_clearance_mm": FACE_CLEAR_MM,
        "polygon_tolerance_mm": POLY_TOL_MM,
        "ring_match_iou_min": MATCH_IOU,
        "datum_faces": len(found),
        "min_level_area_mm2": a.min_level_area,
        "z_range_mm": [round(z_lo, 3), round(z_hi, 3)],
        "bands": len(built),
        "bands_ruled_requested": sum(1 for r in built if r["ruled_requested"]),
        "bands_split_at_a_topology_change": sum(1 for r in built if r["split"]),
        "thinnest_slab_mm": min(r["thinnest_slab_mm"] for r in built),
        "pair_reach": {"min_mm": PAIR_REACH_MIN_MM, "slope": PAIR_REACH_SLOPE},
        "long_ring_mm": LONG_RING_MM,
        "min_step_mm": MIN_STEP_MM,
        "bands_shrunk": sum(1 for r in built if r["shrunk"]),
        "bands_failed": [{"z": r["z"], "notes": r["notes"]} for r in failed],
        "polygon_solids": n_parts,
        "polygon_solids_prism_in_ruled_bands": sum(r["polygons_prism"] for r in built),
        "rings_in_ruled_bands": sum(r["rings"] for r in built),
        "rings_ruled": sum(r["ruled_rings"] for r in built),
        "holes_cut_as_prisms": sum(r["holes_cut_as_prisms"] for r in built),
        "ruled_share_of_ring_length_in_ruled_bands": round(
            sum(r["ruled_length_mm"] for r in built) / max(sum(r["ring_length_mm"] for r in built), 1e-9), 4),
        "fallback_notes": [n for r in recs for n in r.get("notes", [])][:40],
        "band_triangles": int(sum(r["triangles"] for r in built)),
        "union": {
            "tool": "manifold3d batch_boolean(Add), double precision",
            "status": str(whole.status()),
            "pieces": len(pieces),
            "solid_pieces_kept": len(kept) - len(voids),
            "enclosed_voids": len(voids),
            "enclosed_voids_volume_mm3": round(float(-sum(b.volume() for b in voids)), 2),
            "crumbs_dropped": len(crumbs),
            "crumbs_dropped_volume_mm3": round(float(sum(b.volume() for b in crumbs)), 2),
            "crumb_max_mm3": CRUMB_MAX_MM3,
        },
        "body": {
            "refined_to_edge_mm": REFINE_EDGE_MM,
            "triangles_without_area": int((2 * tri_area < 1e-12).sum()),
            "triangles": int(len(f)),
            "vertices": int(len(v)),
            "genus": int(body.genus()),
            "volume_mm3": round(float(body.volume()), 1),
            "surface_area_mm2": round(float(body.surface_area()), 1),
            "trimesh_watertight": bool(mesh.is_watertight),
            "trimesh_winding_consistent": bool(mesh.is_winding_consistent),
            "trimesh_volume_mm3": round(float(mesh.volume), 1),
        },
        "area_share_by_surface_kind": {
            "horizontal_faces": round(float(tri_area[unit_z > 0.999].sum() / total), 4),
            "vertical_walls": round(float(tri_area[unit_z < 0.02].sum() / total), 4),
            "ruled_walls": round(float(tri_area[(unit_z >= 0.02) & (unit_z <= 0.999)].sum() / total), 4),
        },
        "workers": a.workers,
        "seconds": {"bands": round(t_build, 1), "union": round(t_union, 1), "total": round(time.time() - t0, 1)},
    }
    write_json(params / f"v2-loft-{a.label}-summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("bands", "bands_split_at_a_topology_change", "bands_shrunk",
                                              "bands_failed", "polygon_solids",
                                              "rings_in_ruled_bands", "rings_ruled",
                                              "ruled_share_of_ring_length_in_ruled_bands", "union", "body",
                                              "area_share_by_surface_kind", "seconds")}))


if __name__ == "__main__":
    main(sys.argv[1:])
