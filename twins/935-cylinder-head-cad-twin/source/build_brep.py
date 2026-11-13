"""T2 v0: editable B-rep of the bare head as a stack of sketch + extrude bands.

The head is close to 2.5-D along its bore axis: the fins are plates normal
to Z. Each band is one sketch (polygon loops of the occupancy iso-contour of the
band's middle slice) extruded between two Z levels. Slices
are merged into one band while every member differs from the band's first
slice by less than BAND_TOL_MM; walls that slope against Z therefore get thin
bands and bounded stair steps. Fin faces, deck and cam pads fall on band
boundaries.

Usage: build_brep.py PRIVATE_DIR PARAMS_DIR [BAND_TOL_MM] [Z_MIN Z_MAX]
Outputs (private): t2-bare-head.step, t2-bare-head.stl; (params) t2-brep-summary.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import write_json  # noqa: E402

POLY_TOL_MM = 0.05
MIN_RING_AREA_MM2 = 0.5


def slice_region(w2d, grid):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from skimage.measure import find_contours

    h = grid["pitch_mm"]
    padded = np.pad(w2d, 1, constant_values=0.0)
    rings = []
    for c in find_contours(padded, 0.5):
        if len(c) < 4:
            continue
        xy = np.column_stack((grid["x0"] + (c[:, 0] - 1) * h, grid["y0"] + (c[:, 1] - 1) * h))
        p = Polygon(xy)
        if not p.is_valid:
            p = p.buffer(0)
        if p.area >= MIN_RING_AREA_MM2:
            rings.append(p)
    rings.sort(key=lambda p: -p.area)
    # Even-odd nesting: depth 0, 2, ... are material; 1, 3, ... are holes.
    # Rings are applied from the largest to the smallest, so an island inside a
    # hole is added back after its hole was cut. Until 2026-11-10 this function
    # united the even rings and subtracted the odd ones in one step, which
    # removed every such island: the land inside the sealing groove and the
    # valve-guide bosses inside the spring pockets were missing from all bodies
    # built from it (fin_stack runs a to h).
    depth = [sum(1 for q in rings[:i] if q.contains(p.representative_point())) for i, p in enumerate(rings)]
    region = Polygon()
    for p, d in zip(rings, depth):
        region = region.union(p) if d % 2 == 0 else region.difference(p)
    return region.buffer(0)


def same_band(a, b, tol):
    x = a.symmetric_difference(b)
    return x.is_empty or x.buffer(-tol / 2.0).is_empty


def horizontal_levels(private, min_area_mm2=20.0, res=0.02):
    """Z levels of planar faces normal to the bore axis, from acquired facets.

    Area histogram of facets with |n_z| > 0.98 at `res` mm; local maxima above
    `min_area_mm2` are returned with their area.
    """

    d = np.load(private / "bare-scan-twin.npz")
    v, f = d["v"], d["f"]
    t = v[f]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    nz = np.abs(n[:, 2]) / np.maximum(2 * a, 1e-30)
    sel = nz > 0.98
    z = t[sel].mean(axis=1)[:, 2]
    edges = np.arange(z.min() - res, z.max() + 2 * res, res)
    hist, _ = np.histogram(z, bins=edges, weights=a[sel])
    peaks = []
    for i in range(1, len(hist) - 1):
        if hist[i] >= min_area_mm2 and hist[i] >= hist[i - 1] and hist[i] > hist[i + 1]:
            lo, hi = max(0, i - 2), min(len(hist), i + 3)
            centres = 0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1])
            peaks.append((float((centres * hist[lo:hi]).sum() / hist[lo:hi].sum()), float(hist[lo:hi].sum())))
    return peaks


def snap(z, levels, reach):
    best = min(levels, key=lambda p: abs(p[0] - z), default=None)
    return best[0] if best is not None and abs(best[0] - z) <= reach else z


def ring_wire(coords):
    """Closed polygon wire of the contour simplified to POLY_TOL_MM.

    Measured on 2026-11-06 on one mid-height band: B-spline interpolation of
    the resampled contour took 190 s, gave an invalid solid and 35% excess
    volume; the polygon wire takes 0.64 s, is valid and matches the region
    area exactly. Planar side faces are kept; smooth analytic surfaces are the
    job of the feature overrides, not of this scaffold.
    """

    from build123d import Wire

    c = list(coords)[:-1]
    return Wire.make_polygon([(float(x), float(y), 0.0) for x, y in c], close=True)


def band_solid(region, z0, z1):
    from build123d import Face, Pos, extrude
    from shapely.geometry import Polygon

    solids = []
    geoms = getattr(region, "geoms", [region])
    for poly in geoms:
        if poly.area < MIN_RING_AREA_MM2:
            continue
        poly = poly.simplify(POLY_TOL_MM)
        if poly.is_empty or poly.geom_type != "Polygon":
            continue
        outer = ring_wire(poly.exterior.coords)
        inners = [ring_wire(r.coords) for r in poly.interiors if Polygon(r).area >= MIN_RING_AREA_MM2]
        face = Face(outer, inners)
        # The contour orientation decides the face normal, and extrude() follows
        # the normal by default. Until 2026-11-10 that put every band one
        # thickness below its interval (measured: asked 41.80..44.12, got
        # 39.48..41.80). The direction is now explicit and checked.
        solid = Pos(0, 0, z0) * extrude(face, amount=z1 - z0, dir=(0, 0, 1))
        box = solid.bounding_box()
        if abs(box.min.Z - z0) > 1e-6 or abs(box.max.Z - z1) > 1e-6:
            raise ValueError(f"band {z0}..{z1} built at {box.min.Z}..{box.max.Z}")
        solids.append(solid)
    return solids


def main(private, params, tol="0.2", zmin=None, zmax=None):
    from build123d import Compound, export_step, export_stl

    private, params = Path(private), Path(params)
    tol = float(tol)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    wn = np.load(private / grid["array"], mmap_mode="r")
    h = grid["pitch_mm"]
    zs = grid["z0"] + h * np.arange(grid["shape"][2])
    ks = [k for k in range(len(zs)) if (zmin is None or zs[k] >= float(zmin)) and (zmax is None or zs[k] <= float(zmax))]
    t0 = time.time()
    regions = {}
    for k in ks:
        r = slice_region(np.asarray(wn[:, :, k], dtype=np.float32), grid)
        if not r.is_empty:
            regions[k] = r
    ks = sorted(regions)
    bands, start = [], ks[0]
    for prev, k in zip(ks, ks[1:] + [None]):
        if k is not None and k == prev + 1 and same_band(regions[start], regions[k], tol):
            continue
        bands.append((start, prev))
        start = k
    t_slices = time.time() - t0
    levels = horizontal_levels(private)
    bounds = sorted({zs[k0] - h / 2 for k0, _ in bands} | {zs[k1] + h / 2 for _, k1 in bands})
    snapped = {b: snap(b, levels, h / 2) for b in bounds}
    solids, failures = [], []
    for k0, k1 in bands:
        mid = regions[(k0 + k1) // 2]
        z0, z1 = snapped[zs[k0] - h / 2], snapped[zs[k1] + h / 2]
        if z1 - z0 < 0.02:
            failures.append({"band": [int(k0), int(k1)], "error": "collapsed by level snapping"})
            continue
        try:
            solids.extend(band_solid(mid, z0, z1))
        except Exception as exc:  # retained and reported, never silently dropped
            failures.append({"band": [int(k0), int(k1)], "error": repr(exc)[:200]})
    t_bands = time.time() - t0 - t_slices
    # Pairwise fuse tree: neighbouring bands share planar faces (glue mode).
    layer = solids
    while len(layer) > 1:
        layer = [layer[i].fuse(layer[i + 1], glue=True) if i + 1 < len(layer) else layer[i]
                 for i in range(0, len(layer), 2)]
    body = layer[0]
    t_fuse = time.time() - t0 - t_slices - t_bands
    export_step(body, str(private / "t2-bare-head.step"))
    export_stl(body, str(private / "t2-bare-head.stl"), tolerance=0.01, angular_tolerance=0.1)
    summary = {
        "schema": "935-cad-twin-t2-brep/1",
        "method": "sketch+extrude band stack from occupancy iso-contours; polygon loops simplified to "
                  f"{POLY_TOL_MM} mm; bands merged while slices differ by less than {tol} mm",
        "band_tolerance_mm": tol,
        "slices": len(ks),
        "bands": len(bands),
        "band_thickness_mm": {"min": float(h), "max": float(h * max(b - a + 1 for a, b in bands)),
                              "median": float(h * np.median([b - a + 1 for a, b in bands]))},
        "horizontal_levels_found": len(levels),
        "band_boundaries_snapped": int(sum(1 for b in bounds if snapped[b] != b)),
        "band_boundaries": len(bounds),
        "solids_before_fuse": len(solids),
        "band_failures": failures,
        "is_valid": bool(body.is_valid),
        "solid_count": len(body.solids()),
        "face_count": len(body.faces()),
        "volume_mm3": round(float(body.volume), 1),
        "seconds": {"slices": round(t_slices, 1), "bands": round(t_bands, 1), "fuse": round(t_fuse, 1)},
        "z_range": [float(zs[ks[0]] - h / 2), float(zs[ks[-1]] + h / 2)],
    }
    write_json(params / "t2-brep-summary.json", summary)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:6])
