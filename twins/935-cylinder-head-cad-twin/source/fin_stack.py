"""v1 feature tree, body: one sketch + extrude per interval between measured
horizontal faces (fin tops/bottoms, deck steps, pads).

Band boundaries are not slicing artefacts: they are the Z levels where the
acquired scan has planar faces normal to the bore axis. Each band's sketch is
the occupancy contour at the band's mid-level (polygon, simplified to
POLY_TOL_MM). Bands are kept as a compound of individually valid solids (an
OCCT glue fuse of dense prisms was measured invalid on 2026-11-06); the
compound's tessellation is scored by score_twin.

Runs, each kept with its summary and scorecard:
  a  fine levels only (0.1 mm window, at least MIN_LEVEL_AREA mm2). The fin
     faces are cast and drafted over 1 to 2 mm, so this found levels near only
     7 of the 28 and left single bands from z = 7.6 to 38.1 mm and from 50.0
     to 69.4 mm.
  b  a + the fin faces fitted by fit_fins.py as boundaries.
  Both a and b were built with band_solid() extruding downward, so every band
  sat one thickness too low. Their scores are kept as measured, not corrected.
  c  b with the extrusion direction fixed (build_brep.band_solid).
  d  c with --tilt: a fin face becomes a tilted plane when its plane fit beats
     its level fit (TILT_RMS_RATIO) and tilts at least TILT_MIN_DEG. The band
     prism is then cut by that plane. A tilted boundary that would cross a
     neighbour over the body footprint is demoted to its level.
  e  d with --ports: the lofts of port_loft.py replace the staircase port
     walls. In each band the sketch first regains the loft's footprint (the
     loft wall grown radially by PORT_FILL_MM, never beyond the loft's end
     planes), then the loft solid is cut from the prism.
  f  e with --dome and --split-thick. The chamber is the fitted sphere inside
     the fitted shoulder (deck-features.json): each band regains the dome's
     footprint where the occupancy is material at the top of the band, then
     the dome solid is cut. A band thicker than SPLIT_MIN_MM that holds no
     fitted face is split where the occupancy cross-section changes by at
     least SPLIT_AREA_MM2 between two slices (tops of bosses too small for
     the level detector). Only lofts that port_loft.py adopted are cut.
  g  f with --interpolate and --dome-reach fitted, h with --interpolate only.
     Both changes were suggested by error_breakdown.py on run f and both
     lowered the shell score, so neither is adopted and f stays the reference:
     - --dome-reach fitted ends the dome where a flat ring at the register
       floor starts to replace the sphere (42 mm instead of the 46.4 mm
       shoulder). It restores that ring but gives up the sphere in the same
       rings, where most facets still follow it (g against h: 69.3% against
       69.7% of scan area within 0.2 mm).
     - --interpolate takes each sketch from the occupancy interpolated at the
       exact mid-level instead of the nearest 0.25 mm slice (h against f:
       69.7% against 69.9%).

Bands are built and tessellated in a process pool; each worker writes one BREP
and one triangle file per band, so the STEP is assembled only on request.

Two triangle files are written. `v1-body-stack-<label>.stl` is the compound as
built, including the faces two touching bands share. `...-shell.stl` is the
outer surface: of each pair of caps meeting on a boundary only the parts not
covered by the other band are kept (2D difference of the cap polygons). Scores
are taken on the shell; a scan facet lying on a hidden shared face must not
count as explained. Runs a and b predate the shell.

Usage: fin_stack.py PRIVATE_DIR PARAMS_DIR LABEL [--no-fin-faces] [--tilt]
                    [--ports] [--dome] [--dome-reach shoulder|fitted]
                    [--split-thick] [--interpolate] [--step] [--workers N]
                    [--min-level-area A]
                    [--shell-only]
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
from build_brep import band_solid, slice_region  # noqa: E402
from twin_common import face_geometry, write_json  # noqa: E402

TILT_RMS_RATIO = 0.8
TILT_MIN_DEG = 0.3
MIN_BAND_MM = 0.05
STL_TOL_MM = 0.01
PORT_FILL_MM = 0.3
PORT_GRID_MM = 0.25
SPLIT_MIN_MM = 6.0
SPLIT_AREA_MM2 = 15.0
SPLIT_MERGE_MM = 0.75
DOME_FLAT_SHARE_MAX = 0.05

_G = {}


def levels(cen, n, area, zmin, zmax, min_area, res=0.02):
    sel = (np.abs(n[:, 2]) > 0.98) & (cen[:, 2] > zmin) & (cen[:, 2] < zmax)
    z, a = cen[sel, 2], area[sel]
    edges = np.arange(zmin, zmax + res, res)
    h, _ = np.histogram(z, bins=edges, weights=a)
    # Merge each local peak with its +-2 bins.
    out = []
    i = 1
    while i < len(h) - 1:
        if h[i] >= h[i - 1] and h[i] > h[i + 1]:
            lo, hi = max(0, i - 2), min(len(h), i + 3)
            tot = h[lo:hi].sum()
            if tot >= min_area:
                c = 0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1])
                out.append((float((c * h[lo:hi]).sum() / tot), float(tot)))
            i = hi
        else:
            i += 1
    return out


def z_at(b, x, y):
    return b["z"] if b["plane"] is None else b["plane"][0] + b["plane"][1] * x + b["plane"][2] * y


def min_gap(lo, hi, corners):
    return min(z_at(hi, x, y) - z_at(lo, x, y) for x, y in corners)


def make_boundaries(fine, fin_faces, z_lo, z_hi, tilt, corners):
    """Sorted boundary list plus what was dropped or demoted on the way."""

    notes = {"fine_levels_dropped": 0, "tilted": 0, "demoted": []}
    bounds = [{"z": z_lo, "plane": None, "source": "body_extent"}, {"z": z_hi, "plane": None, "source": "body_extent"}]
    spans = []
    for f in fin_faces:
        plane = None
        if tilt and f["rms_plane_mm"] <= TILT_RMS_RATIO * f["rms_level_mm"] and f["plane_tilt_deg"] >= TILT_MIN_DEG:
            plane = (f["plane_z_at_axis_mm"], f["plane_slope_xy"][0], f["plane_slope_xy"][1])
            spans.append((f["plane_z_span_mm"][0] - 0.1, f["plane_z_span_mm"][1] + 0.1))
        bounds.append({"z": f["z_level_mm"], "plane": plane, "source": f["side"]})
    for z in fine:
        # A fitted fin face replaces the fine levels inside its own scatter.
        if any(abs(z - f["z_level_mm"]) <= 0.3 for f in fin_faces) or any(a <= z <= b for a, b in spans):
            notes["fine_levels_dropped"] += 1
            continue
        bounds.append({"z": z, "plane": None, "source": "level"})
    bounds.sort(key=lambda b: b["z"])
    changed = True
    while changed:
        changed = False
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            if min_gap(lo, hi, corners) >= MIN_BAND_MM or (lo["plane"] is None and hi["plane"] is None):
                continue
            # Demote the tilted boundary; with two, the one fitted on the smaller rise.
            victim = hi if lo["plane"] is None else lo if hi["plane"] is None else \
                min((lo, hi), key=lambda b: abs(b["plane"][1]) + abs(b["plane"][2]))
            victim["plane"] = None
            notes["demoted"].append(round(victim["z"], 3))
            changed = True
    notes["tilted"] = sum(1 for b in bounds if b["plane"] is not None)
    return bounds, notes


def dome_reach(params, cen, n, area):
    """Largest radius out to which the chamber wall follows the fitted sphere.

    In 1 mm rings from the register axis, the share of inward-facing chamber
    facets that lie flat at the register floor instead of on the sphere is
    measured; the dome ends before the first ring where it reaches
    DOME_FLAT_SHARE_MAX.
    """

    feats = json.loads((Path(params) / "deck-features.json").read_text())
    ch, reg = feats["chamber"], feats["register"]
    c, rsh = np.array(ch["sphere_centre"]), ch["shoulder_diameter_mm"] / 2
    rad = np.hypot(cen[:, 0] - reg["centre"][0], cen[:, 1] - reg["centre"][1])
    res = np.abs(np.linalg.norm(cen - c, axis=1) - ch["sphere_radius_mm"])
    inside = (rad < rsh) & (cen[:, 2] > reg["floor_z"] - 0.6) & (cen[:, 2] < c[2] + ch["sphere_radius_mm"] + 1) & (n[:, 2] < -0.05)
    flat = inside & (res >= 0.3) & (cen[:, 2] < reg["floor_z"] + 0.45) & (n[:, 2] < -0.94)
    reach = rsh
    for lo in np.arange(np.floor(rsh) - 20, rsh, 1.0):
        ring = inside & (rad >= lo) & (rad < lo + 1.0)
        if area[ring].sum() > 0 and area[ring & flat].sum() / area[ring].sum() >= DOME_FLAT_SHARE_MAX:
            reach = float(lo)
            break
    return reach


def load_dome(params, reach):
    from build123d import Cylinder, Pos, Sphere

    feats = json.loads((Path(params) / "deck-features.json").read_text())
    ch, reg = feats["chamber"], feats["register"]
    c, r, floor = np.array(ch["sphere_centre"]), ch["sphere_radius_mm"], reg["floor_z"]
    rsh = min(reach, ch["shoulder_diameter_mm"] / 2)
    top = float(c[2] + r)
    solid = (Pos(*c) * Sphere(r)) & (Pos(reg["centre"][0], reg["centre"][1], (floor + top + 1) / 2)
                                    * Cylinder(rsh, top + 1 - floor))
    return {"name": "chamber_dome", "solid": solid, "c": c, "r": r, "rsh": rsh, "axis": reg["centre"],
            "floor": floor, "top": top, "lo": np.array([reg["centre"][0] - rsh, reg["centre"][1] - rsh, floor]),
            "hi": np.array([reg["centre"][0] + rsh, reg["centre"][1] + rsh, top])}


def dome_footprint(dome, z0, z1):
    """Dome footprint in the band, kept only where the band's top is material."""

    from shapely.geometry import Point

    if z1 <= dome["floor"] or z0 >= dome["top"]:
        return None
    rho2 = dome["r"] ** 2 - (max(z0, dome["floor"]) - dome["c"][2]) ** 2
    if rho2 <= 0:
        return None
    disc = Point(dome["c"][0], dome["c"][1]).buffer(rho2 ** 0.5, 128).intersection(
        Point(*dome["axis"]).buffer(dome["rsh"], 128))
    grid = _G["grid"]
    fill = disc.intersection(slice_region(occupancy_at(z1 - grid["pitch_mm"] / 2), grid))
    return None if fill.is_empty else fill


def split_levels(wn, grid, lo, hi):
    """Levels inside lo..hi where the occupancy cross-section changes abruptly."""

    h = grid["pitch_mm"]
    ks = np.arange(int(np.ceil((lo + 0.5 - grid["z0"]) / h)), int(np.floor((hi - 0.5 - grid["z0"]) / h)) + 1)
    if len(ks) < 2:
        return []
    area = np.array([float((np.asarray(wn[:, :, k]) > 0.5).sum()) * h * h for k in ks])
    jump = np.abs(np.diff(area))
    picked = []
    for j in np.argsort(-jump):
        if jump[j] < SPLIT_AREA_MM2:
            break
        z = float(grid["z0"] + (ks[j] + 0.5) * h)
        if all(abs(z - q) >= SPLIT_MERGE_MM for q in picked):
            picked.append(z)
    return sorted(picked)


def load_ports(private, params):
    from build123d import import_brep
    from scipy.spatial import cKDTree

    raw = np.load(private / "port-sections.npz")
    adopted = {p["name"] for p in json.loads((Path(params) / "port-loft-check.json").read_text())["ports"]
               if p.get("adopted")}
    ports = []
    for name in sorted({k.split("__")[0] for k in raw.files} & adopted):
        d = {k.split("__")[1]: raw[k] for k in raw.files if k.startswith(name + "__")}
        ang = np.linspace(0.0, 2 * np.pi, d["radii"].shape[1], endpoint=False)
        wall = (d["centre"][:, None, :] + (d["radii"] * np.cos(ang))[:, :, None] * d["u"][:, None, :]
                + (d["radii"] * np.sin(ang))[:, :, None] * d["v"][:, None, :]).reshape(-1, 3)
        ports.append({"name": name, **d, "tree": cKDTree(d["centre"]), "lo": wall.min(axis=0) - 1.0,
                      "hi": wall.max(axis=0) + 1.0, "solid": import_brep(str(private / f"v1-{name}.brep"))})
    return ports


def port_footprint(port, z0, z1):
    """XY polygon of the loft, grown radially by PORT_FILL_MM, within z0..z1."""

    if z1 <= port["lo"][2] or z0 >= port["hi"][2]:
        return None
    g = PORT_GRID_MM
    xs = np.arange(port["lo"][0], port["hi"][0] + g, g)
    ys = np.arange(port["lo"][1], port["hi"][1] + g, g)
    zs = np.arange(max(z0, port["lo"][2]), min(z1, port["hi"][2]) + g / 2, g)
    mask = np.zeros((len(xs), len(ys)), dtype=bool)
    xx, yy = np.meshgrid(xs, ys, indexing="ij")
    c, t, rad = port["centre"], port["tangent"], port["radii"]
    rays = rad.shape[1]
    for z in zs:
        p = np.column_stack((xx.ravel(), yy.ravel(), np.full(xx.size, z)))
        k = port["tree"].query(p)[1]
        q = p - c[k]
        a, b = np.einsum("ij,ij->i", q, port["u"][k]), np.einsum("ij,ij->i", q, port["v"][k])
        th = np.mod(np.arctan2(b, a), 2 * np.pi) / (2 * np.pi) * rays
        i0 = np.floor(th).astype(int) % rays
        w = th - np.floor(th)
        r_wall = (1 - w) * rad[k, i0] + w * rad[k, (i0 + 1) % rays]
        inside = (np.hypot(a, b) < r_wall + PORT_FILL_MM) & ((p - c[0]) @ t[0] > 0) & ((p - c[-1]) @ t[-1] < 0)
        mask |= inside.reshape(mask.shape)
    if not mask.any():
        return None
    poly = slice_region(mask.astype(np.float32), {"pitch_mm": g, "x0": float(xs[0]), "y0": float(ys[0])})
    return None if poly.is_empty else poly


def occupancy_at(z):
    """Occupancy slice at height z: the nearest voxel slice, or the linear
    interpolation between two slices when the run asked for it."""

    grid, wn = _G["grid"], _G["wn"]
    q = (z - grid["z0"]) / grid["pitch_mm"]
    top = grid["shape"][2] - 1
    if not _G.get("interpolate"):
        return np.asarray(wn[:, :, int(np.clip(round(q), 0, top))], dtype=np.float32)
    k = int(np.clip(np.floor(q), 0, top - 1))
    t = float(np.clip(q - k, 0.0, 1.0))
    return (1 - t) * np.asarray(wn[:, :, k], dtype=np.float32) + t * np.asarray(wn[:, :, k + 1], dtype=np.float32)


def _init(private, params=None, with_ports=False, dome_reach_mm=None, interpolate=False):
    private = Path(private)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    _G.update(grid=grid, wn=np.load(private / grid["array"], mmap_mode="r"), interpolate=interpolate,
              ports=load_ports(private, params) if with_ports else [],
              dome=load_dome(params, dome_reach_mm) if dome_reach_mm is not None else None)


def _cut(solid, b, keep_above):
    from build123d import Keep, Plane, Vector

    nrm = Vector(-b["plane"][1], -b["plane"][2], 1.0).normalized()
    got = solid.split(Plane(origin=(0, 0, b["plane"][0]), z_dir=(nrm.X, nrm.Y, nrm.Z)),
                      keep=Keep.TOP if keep_above else Keep.BOTTOM)
    return [] if got is None else list(got.solids())


def build_band(job):
    from build123d import Compound, export_brep

    idx, lo, hi, corners, out_dir = job
    grid = _G["grid"]
    rec = {"index": idx, "z": [round(lo["z"], 4), round(hi["z"], 4)],
           "tilted": [lo["plane"] is not None, hi["plane"] is not None]}
    region = slice_region(occupancy_at((lo["z"] + hi["z"]) / 2), grid)
    if region.is_empty:
        return {**rec, "solids": 0, "empty": True}
    z0 = min(z_at(lo, x, y) for x, y in corners)
    z1 = max(z_at(hi, x, y) for x, y in corners)
    cut_ports = []
    for port in _G["ports"]:
        foot = port_footprint(port, z0, z1)
        if foot is not None:
            region = region.union(foot).buffer(0)
            cut_ports.append(port)
    if _G["dome"] is not None:
        foot = dome_footprint(_G["dome"], z0, z1)
        if foot is not None:
            region = region.union(foot).buffer(0)
        if z1 > _G["dome"]["floor"] and z0 < _G["dome"]["top"]:
            cut_ports.append(_G["dome"])
    rec["ports_cut"] = [p["name"] for p in cut_ports]
    try:
        solids = band_solid(region, z0, z1)
        for port in cut_ports:
            cut = []
            for s in solids:
                box = s.bounding_box()
                if (box.max.X < port["lo"][0] or box.min.X > port["hi"][0]
                        or box.max.Y < port["lo"][1] or box.min.Y > port["hi"][1]):
                    cut.append(s)
                else:
                    cut.extend((s - port["solid"]).solids())
            solids = cut
        if lo["plane"] is not None:
            solids = [p for s in solids for p in _cut(s, lo, True)]
        if hi["plane"] is not None:
            solids = [p for s in solids for p in _cut(s, hi, False)]
    except Exception as exc:  # recorded, never hidden
        return {**rec, "solids": 0, "error": repr(exc)[:200]}
    if not solids:
        return {**rec, "solids": 0, "empty": True}
    verts, faces, off = [], [], 0
    for s in solids:
        v, f = s.tessellate(STL_TOL_MM, 0.1)
        verts.append(np.array([(p.X, p.Y, p.Z) for p in v], dtype=np.float64))
        faces.append(np.asarray(f, dtype=np.int64) + off)
        off += len(v)
    np.savez(Path(out_dir) / f"band-{idx:03d}.npz", v=np.vstack(verts), f=np.vstack(faces))
    export_brep(Compound(solids), str(Path(out_dir) / f"band-{idx:03d}.brep"))
    return {**rec, "solids": len(solids), "valid": bool(all(s.is_valid for s in solids)),
            "volume_mm3": float(sum(s.volume for s in solids)), "area_mm2": round(region.area, 1)}


def cap_polygon(v, tris):
    from shapely import polygons
    from shapely.ops import unary_union

    if len(tris) == 0:
        return None
    return unary_union(polygons(v[tris][:, :, :2])).buffer(0)


def cap_flags(v, f, boundary):
    """A triangle is a cap when its three vertices lie on the boundary surface."""

    z = boundary["z"] if boundary["plane"] is None else \
        boundary["plane"][0] + boundary["plane"][1] * v[:, 0] + boundary["plane"][2] * v[:, 1]
    return np.abs(v[:, 2] - z)[f].max(axis=1) < 1e-5


def write_shell(band_files, bounds, path):
    """Outer surface: side triangles as built, caps reduced to their exposed part."""

    import trimesh

    lower, upper, soup = {}, {}, []
    for i, file in band_files.items():
        d = np.load(file)
        v, f = d["v"], d["f"]
        lo, hi = cap_flags(v, f, bounds[i]), cap_flags(v, f, bounds[i + 1])
        lower[i] = cap_polygon(v, f[lo])
        upper[i + 1] = cap_polygon(v, f[hi])
        soup.append(v[f[~(lo | hi)]])
    cap_area = hidden_area = 0.0
    for k in sorted(set(lower) | set(upper)):
        below, above = upper.get(k), lower.get(k)   # caps of the bands under and over boundary k
        for mine, other in ((below, above), (above, below)):
            tris, shown = exposed_cap(mine, other, bounds[k])
            soup.append(tris)
            if mine is not None:
                cap_area += mine.area
                hidden_area += mine.area - shown
    shell = np.vstack(soup)
    trimesh.Trimesh(shell.reshape(-1, 3), np.arange(len(shell) * 3).reshape(-1, 3), process=False).export(path)
    return {"triangles": int(len(shell)), "cap_area_mm2": round(cap_area, 1),
            "cap_area_hidden_mm2": round(hidden_area, 1)}


def exposed_cap(mine, other, boundary):
    """Triangles of the part of a cap that the neighbouring band does not cover."""

    from shapely import constrained_delaunay_triangles, get_coordinates, get_parts

    if mine is None:
        return np.zeros((0, 3, 3)), 0.0
    part = mine if other is None else mine.difference(other)
    part = part.buffer(-1e-4).buffer(1e-4)
    if part.is_empty:
        return np.zeros((0, 3, 3)), 0.0
    tri = [g for g in get_parts(constrained_delaunay_triangles(part)) if g.geom_type == "Polygon"]
    xy = np.array([get_coordinates(g)[:3] for g in tri]).reshape(-1, 3, 2)
    z = np.array([[z_at(boundary, x, y) for x, y in t] for t in xy])
    return np.dstack((xy, z)), float(part.area)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("private")
    ap.add_argument("params")
    ap.add_argument("label")
    ap.add_argument("--no-fin-faces", action="store_true")
    ap.add_argument("--tilt", action="store_true")
    ap.add_argument("--ports", action="store_true")
    ap.add_argument("--dome", action="store_true")
    ap.add_argument("--split-thick", action="store_true")
    ap.add_argument("--dome-reach", choices=("shoulder", "fitted"), default="shoulder")
    ap.add_argument("--interpolate", action="store_true", help="sketch from the interpolated mid-level (runs g, h)")
    ap.add_argument("--step", action="store_true")
    ap.add_argument("--shell-only", action="store_true", help="re-derive the shell of an existing run")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-level-area", type=float, default=150.0)
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
    x0, y0 = cen[:, :2].min(axis=0) - 2.0
    x1, y1 = cen[:, :2].max(axis=0) + 2.0
    corners = [(float(x), float(y)) for x in (x0, x1) for y in (y0, y1)]
    fine = [round(z, 4) for z, _ in levels(cen, n, area, z_lo + 0.1, z_hi - 0.1, a.min_level_area)]
    fin_faces = [] if a.no_fin_faces else json.loads((params / "fin-faces.json").read_text())["faces"]
    bounds, notes = make_boundaries(fine, fin_faces, z_lo, z_hi, a.tilt, corners)
    added = []
    if a.split_thick:
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            if hi["z"] - lo["z"] > SPLIT_MIN_MM and lo["plane"] is None and hi["plane"] is None:
                added += split_levels(wn, grid, lo["z"], hi["z"])
        bounds = sorted(bounds + [{"z": z, "plane": None, "source": "occupancy_step"} for z in added],
                        key=lambda b: b["z"])
    reach = None
    if a.dome:
        reach = dome_reach(params, cen, n, area) if a.dome_reach == "fitted" else 1e9
    out_dir = private / f"v1-body-stack-{a.label}"
    if a.shell_only:
        # Same options as the original run are required: they decide the boundaries.
        files = {int(p.stem.split("-")[1]): p for p in sorted(out_dir.glob("band-*.npz"))}
        summary_path = params / f"v1-body-stack-{a.label}-summary.json"
        summary = json.loads(summary_path.read_text())
        summary["shell"] = write_shell(files, bounds, private / f"v1-body-stack-{a.label}-shell.stl")
        write_json(summary_path, summary)
        print(json.dumps(summary["shell"]))
        return
    out_dir.mkdir(exist_ok=False)
    jobs = [(i, lo, hi, corners, str(out_dir)) for i, (lo, hi) in enumerate(zip(bounds[:-1], bounds[1:]))
            if hi["z"] - lo["z"] >= MIN_BAND_MM]
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(str(private), str(params), a.ports, reach, a.interpolate)) as pool:
        recs = list(pool.map(build_band, jobs))
    t_build = time.time() - t0
    built = [r for r in recs if r["solids"]]
    failures = [r for r in recs if "error" in r]

    import trimesh

    verts, faces, off = [], [], 0
    for r in built:
        d = np.load(out_dir / f"band-{r['index']:03d}.npz")
        verts.append(d["v"])
        faces.append(d["f"] + off)
        off += len(d["v"])
    trimesh.Trimesh(np.vstack(verts), np.vstack(faces), process=False).export(private / f"v1-body-stack-{a.label}.stl")

    shell = write_shell({r["index"]: out_dir / f"band-{r['index']:03d}.npz" for r in built}, bounds,
                        private / f"v1-body-stack-{a.label}-shell.stl")
    if a.step:
        from build123d import Compound, export_step, import_brep

        export_step(Compound([s for r in built for s in import_brep(str(out_dir / f"band-{r['index']:03d}.brep")).solids()]),
                    str(private / f"v1-body-stack-{a.label}.step"))
    thick = [r["z"][1] - r["z"][0] for r in built]
    summary = {
        "schema": "935-cad-twin-v1-body-stack/2",
        "label": a.label,
        "fin_face_boundaries": len(fin_faces),
        "tilt_requested": a.tilt,
        "tilt_rule": {"rms_plane_over_rms_level_max": TILT_RMS_RATIO, "tilt_min_deg": TILT_MIN_DEG},
        "tilted_boundaries": notes["tilted"],
        "tilted_boundaries_demoted_z_mm": notes["demoted"],
        "ports_requested": a.ports,
        "port_fill_mm": PORT_FILL_MM,
        "bands_with_port_cut": sum(1 for r in recs if r.get("ports_cut")),
        "features_cut": sorted({n for r in recs for n in r.get("ports_cut", [])}),
        "dome_requested": a.dome,
        "dome_cut_radius_mm": None if reach is None else ("shoulder" if reach > 1e8 else round(reach, 2)),
        "sketch_level": "interpolated_mid_level" if a.interpolate else "nearest_slice",
        "split_thick": {"requested": a.split_thick, "min_band_mm": SPLIT_MIN_MM, "area_step_mm2": SPLIT_AREA_MM2,
                        "levels_added": [round(z, 3) for z in added]},
        "fine_levels_found": len(fine),
        "fine_levels_dropped": notes["fine_levels_dropped"],
        "min_level_area_mm2": a.min_level_area,
        "bands": len(built),
        "solids": sum(r["solids"] for r in built),
        "all_solids_valid": bool(all(r["valid"] for r in built)),
        "band_failures": failures,
        "z_range_mm": [round(z_lo, 3), round(z_hi, 3)],
        "band_thickness_mm": {"min": round(min(thick), 3), "median": round(float(np.median(thick)), 3),
                              "max": round(max(thick), 3)},
        "volume_mm3_sum_of_solids": round(sum(r["volume_mm3"] for r in built), 1),
        "triangles": int(sum(len(f) for f in faces)),
        "shell": shell,
        "step_written": a.step,
        "workers": a.workers,
        "seconds": {"build_and_tessellate": round(t_build, 1), "total": round(time.time() - t0, 1)},
    }
    write_json(params / f"v1-body-stack-{a.label}-summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("bands", "solids", "all_solids_valid", "tilted_boundaries",
                                              "tilted_boundaries_demoted_z_mm", "fine_levels_dropped",
                                              "band_failures", "volume_mm3_sum_of_solids", "seconds")}))


if __name__ == "__main__":
    main(sys.argv[1:])
