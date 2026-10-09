"""A 964 body-in-white shell for the monocoque programme, from plate 50-05a.

Replaces, for presentation and for first whole-body calculations, the box
cell of ../../fea/: that model answers relative questions well but has no
911 shape. This one takes its shape from Porsche's own drawing:

- side profile, plan half width and the door, quarter-window and rear
  wheel-house outlines traced from plate 50-05a (../data/profiles-50-05a.json,
  see trace_plate_50_05a.py);
- one closed section per station (420 stations, 11 mm apart): a rounded
  lower body with a barrel side up to an 880 mm beltline, then a
  superellipse greenhouse to the roof, which gives the 911 tumblehome; where
  the profile drops below the belt the section becomes a crowned lid;
- openings cut along continuous signed fields, so their edges are smooth:
  doors, quarter windows, windscreen and rear window (pillars left by the
  angle around the greenhouse), front-lid and engine-lid openings, the open
  engine-bay underside, front and rear wheel arches;
- a front bulkhead under the scuttle, a rear bulkhead behind the seats, and
  four cylindrical wheel houses.

What is NOT from a publication, and is labelled as such in the output: the
section shapes (barrel, tumblehome exponents, corner radii), the 880 mm
beltline, the glass and lid extents, the wheel-house radii and the bulkhead
heights. The outline is Porsche's; the surfaces between outlines are a
modelling hypothesis. No sheet thickness, no reinforcement, no sill box
section.

Run where numpy, scipy, shapely, matplotlib and pyvista exist (the cadsim
image, with shapely from the print-simulation PYLIB):

    python3 build_shell.py      # writes ../derived/monocoque-shell.ply and .npz
"""
import json
import pathlib

import numpy as np
from matplotlib.path import Path
from scipy.ndimage import gaussian_filter1d, median_filter

HERE = pathlib.Path(__file__).parent
PROFILES = HERE.parent / "data" / "profiles-50-05a.json"
OUT = HERE.parent / "derived"

BELT_MM = 880.0             # beltline, from the quarter-window bottom on the plate
FRONT_AXLE_D = -25.5        # d of the front wheel centres (scan tie, datum chain)
REAR_AXLE_D = FRONT_AXLE_D + 2272.0
FRONT_BULKHEAD_D, REAR_BULKHEAD_D = 380.0, 1975.0
N_STATIONS = 420


def clean(curve, med, sig):
    a = np.array(curve)
    o = np.argsort(a[:, 0])
    x, y = a[o, 0], median_filter(a[o, 1], med)
    return x, gaussian_filter1d(y, sig)


def stations(p, n=N_STATIONS):
    tx, tz = clean(p["side_top"], 5, 1.0)
    bx, bz = clean(p["side_bottom"], 21, 2.0)
    px, pw = clean(p["plan_half_width"], 31, 2.0)
    d = np.linspace(-700, 3080, n)
    zt = np.interp(d, tx, tz)
    zb = np.clip(np.interp(d, bx, bz), 140, 380)      # spikes from markers removed
    w = np.interp(d, px, pw)
    w = np.where(d > 2580, np.maximum(w, np.interp(d, [2580, 3080], [760, 650])), w)  # arch-cut dip in the plan trace
    zbelt = np.minimum(BELT_MM, zt - 70.0)
    nose = np.clip((d - d[0]) / 220.0, 0, 1)
    tail = np.clip((d[-1] - d) / 260.0, 0, 1)
    w = np.maximum(w * np.sqrt(1 - (1 - nose) ** 2) ** 0.35 * np.sqrt(1 - (1 - tail) ** 2) ** 0.35, 120.0)
    return d, zt, zb, w, zbelt


def section(W, B, T, Z0, d, res=1.0):
    rb = min(150.0, 0.45 * (B - Z0))
    bulge = 0.045 if 1950 < d < 2900 else 0.025      # rear quarters swell more
    Wl = W * (1 - bulge)
    k = lambda c: max(3, round(c * res))             # noqa: E731  points per segment
    half = [(y, Z0) for y in np.linspace(0, Wl - rb, k(10))]
    half += [(Wl - rb + rb * np.cos(a), Z0 + rb + rb * np.sin(a)) for a in np.linspace(-np.pi / 2, 0, k(10))[1:]]
    for z in np.linspace(Z0 + rb, B, k(12))[1:]:
        u = (z - (Z0 + rb)) / max(B - Z0 - rb, 1.0)
        half.append((Wl + (W - Wl) * np.sin(np.pi * 0.5 * u) ** 0.8, z))
    n, m = 2.6, 2.4
    half += [(W * np.cos(t) ** (2 / n), B + (T - B) * np.sin(t) ** (2 / m)) for t in np.linspace(0, np.pi / 2, k(22))[1:]]
    return np.array(half + [(-y, z) for y, z in half[::-1][1:-1]])


def surface(d, zt, zb, w, zbelt, res=1.0):
    rings = [section(w[i], zbelt[i], zt[i], zb[i], d[i], res) for i in range(len(d))]
    nr = len(rings[0])
    v = np.array([[-di, y, z] for di, r in zip(d, rings) for y, z in r])   # x forward = -d
    f = []
    for i in range(len(d) - 1):
        for j in range(nr):
            a, b = i * nr + j, i * nr + (j + 1) % nr
            f += [(a, b, (i + 1) * nr + (j + 1) % nr), (a, (i + 1) * nr + (j + 1) % nr, (i + 1) * nr + j)]
    return rings, v, np.array(f)


def opening_field(v, p, d, zt, zb, w, zbelt):
    """Signed field per vertex, > 0 inside an opening."""
    return np.max(opening_fields(v, p, d, zt, zb, w, zbelt), axis=0)


def opening_fields(v, p, d, zt, zb, w, zbelt):
    """One signed field per opening (rows: door, quarter window, rear arch,
    front arch, windscreen, rear window, front lid, engine lid, engine-bay
    underside), > 0 inside it."""
    import shapely
    from shapely.geometry import Polygon
    dv, yv, zv = -v[:, 0], v[:, 1], v[:, 2]
    wv, bv, tv, z0v = (np.interp(dv, d, a) for a in (w, zbelt, zt, zb))
    lateral = np.abs(yv) - 0.55 * wv
    pts = shapely.points(np.c_[dv, zv])

    def sd(poly):
        pg = Polygon(poly).buffer(0)
        dist = shapely.distance(pg.exterior, pts)
        return np.where(shapely.contains(pg, pts), dist, -dist)

    def box(x, lo, hi):
        return np.minimum(x - lo, hi - x)

    s_y = np.clip(np.abs(yv) / np.maximum(wv, 1.0), 1e-6, 1)
    s_z = np.clip((zv - bv) / np.maximum(tv - bv, 1.0), 1e-6, 1)
    pillar = (np.arctan2(s_z ** 1.2, s_y ** 1.3) - 0.62) * 400.0
    rear_arch = np.maximum(sd(p["openings"]["rear_wheel_house"]),
                           np.minimum(345 - np.hypot(dv - REAR_AXLE_D, zv - 300), 560 - zv))
    lid_top = zv - (tv - 90)
    fields = [
        np.minimum(sd(p["openings"]["door_aperture"]), lateral),
        np.minimum(sd(p["openings"]["quarter_window"]), lateral),
        np.minimum(rear_arch, lateral),
        np.minimum(335 - np.hypot(dv - FRONT_AXLE_D, zv - 300), np.abs(yv) - 0.62 * wv),
        np.minimum.reduce([box(dv, 440, 955), zv - bv - 25, pillar]),                      # windscreen
        np.minimum.reduce([box(dv, 2000, 2540), zv - 905, pillar]),                        # rear window
        np.minimum.reduce([box(dv, -640, 360), lid_top, 0.86 * wv - np.abs(yv)]),          # front lid
        np.minimum.reduce([box(dv, 2660, 3040), lid_top, 0.86 * wv - np.abs(yv)]),         # engine lid
        np.minimum.reduce([dv - 1960, z0v + 25 - zv, 0.8 * wv - np.abs(yv)]),               # engine bay underside
    ]
    return np.array(fields)


def bulkhead(d, rings, zb, dd, zcap):
    i = int(np.argmin(np.abs(d - dd)))
    r = rings[i][rings[i][:, 1] <= zcap + 1]
    o = np.argsort(np.arctan2(r[:, 1] - (zb[i] + zcap) / 2, r[:, 0]))
    r = r[o]
    v = [[-dd, 0.0, 0.5 * (zb[i] + zcap)]] + [[-dd, y, z] for y, z in r]
    f = [[0, k, k + 1] for k in range(1, len(r))] + [[0, len(r), 1]]
    return np.array(v), np.array(f)


def wheel_house(d, w, dc, zc, radius):
    wd = float(np.interp(dc, d, w))
    parts = []
    th = np.linspace(np.radians(-15), np.radians(195), 60)
    for sgn in (1, -1):
        ys = np.linspace(0.6 * wd, wd, 8) * sgn
        v = np.array([[-(dc + radius * np.cos(t)), y, zc + radius * np.sin(t)] for y in ys for t in th])
        f = []
        for a in range(len(ys) - 1):
            for b in range(len(th) - 1):
                p0 = a * len(th) + b
                f += [[p0, p0 + 1, p0 + len(th) + 1], [p0, p0 + len(th) + 1, p0 + len(th)]]
        parts.append((v, np.array(f)))
        v = np.array([[-dc, 0.6 * wd * sgn, zc]] + [[-(dc + radius * np.cos(t)), 0.6 * wd * sgn, zc + radius * np.sin(t)] for t in th])
        parts.append((v, np.array([[0, k, k + 1] for k in range(1, len(th))])))
    return parts


def structural(n_stations=N_STATIONS, res=1.0):
    """The clipped shell with its bulkheads, and the wheel houses apart.
    n_stations and res (points per section, relative) set the mesh density;
    the defaults are the published model."""
    import pyvista as pv
    p = json.loads(PROFILES.read_text())
    d, zt, zb, w, zbelt = stations(p, n_stations)
    rings, v, f = surface(d, zt, zb, w, zbelt, res)
    mesh = pv.PolyData(v, np.c_[np.full(len(f), 3), f].ravel())
    mesh.point_data["opening"] = opening_field(v, p, d, zt, zb, w, zbelt)
    shell = mesh.clip_scalar(scalars="opening", value=0.0, invert=True).extract_surface(algorithm="dataset_surface").triangulate()
    bulkheads = [bulkhead(d, rings, zb, FRONT_BULKHEAD_D, 860.0), bulkhead(d, rings, zb, REAR_BULKHEAD_D, BELT_MM)]
    out = shell
    for bv, bf in bulkheads:
        out = out + pv.PolyData(bv, np.c_[np.full(len(bf), 3), bf].ravel())
    out = out.clean(tolerance=1.0).triangulate().connectivity("largest").extract_surface(algorithm="dataset_surface").clean()
    houses = wheel_house(d, w, REAR_AXLE_D, 300.0, 350.0) + wheel_house(d, w, FRONT_AXLE_D, 300.0, 340.0)
    st = dict(points=np.asarray(out.points, dtype=np.float32), triangles=out.faces.reshape(-1, 4)[:, 1:].astype(np.int32),
              stations_d=d, top=zt, bottom=zb, half_width=w, belt=zbelt)
    return out, houses, st


def build():
    import pyvista as pv
    structural_mesh, houses, st = structural()
    full = structural_mesh
    for wv, wf in houses:
        full = full + pv.PolyData(wv, np.c_[np.full(len(wf), 3), wf].ravel())
    OUT.mkdir(parents=True, exist_ok=True)
    full.clean().save(OUT / "monocoque-shell.ply", binary=True)
    np.savez_compressed(OUT / "monocoque-shell-structural.npz", **st)
    print(f"monocoque-shell.ply: {full.n_points} points; structural shell: {len(st['points'])} points, {len(st['triangles'])} triangles")


if __name__ == "__main__":
    build()
