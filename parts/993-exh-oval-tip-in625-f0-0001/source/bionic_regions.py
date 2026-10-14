#!/usr/bin/env python3
"""Writes source/bionic.json and its region meshes for the bionic oval exhaust tip.

    python bionic_regions.py            (this part)
    python bionic_regions.py <part dir> (another record of the same geometry,
                                         e.g. parts/993-exh-oval-tip-ti-f1-0001)

The flow bore is the legacy oval_exhaust_tip bore, exactly
(parts/picogk-catalog/exhaust/OvalExhaustTip.cs): round slip bore of
inlet_pipe_od_mm / 2 + slip_clearance_mm up to slip_depth_mm, then a
smoothstep loft to the oval aOut x bOut = outlet half-size minus
outer_wall + gap + inner_wall. The wetted shell around it is kept as a thin
inner_wall_mm wall with an exact clamp collar (collar_wall_mm) and closed outlet
lip (shell.stl, printed through shaping.base_stl); it enters the optimisation
only as "analysis_only" solids: the wall as a band of one element with
stiffness_scale = wall / element, collar and lip with stiffness 1. The legacy ventilated outer shell is
replaced by structure grown by the optimiser between the flow shell and the
published 120 x 85 mm outlet envelope (an elliptic cylinder): ribs from the
outlet lip down the flare to the clamp collar.

Every region mesh is written to parts/picogk-catalog/out/bionic-regions/<ID>/
(regenerable, not committed) as closed STLs used by topopt.py and
BionicTopology alike, cut into overlapping z tiles so trimesh.contains stays
fast.
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(sys.argv[1]).resolve() / "source" if len(sys.argv) > 1 else Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "parts" / "picogk-catalog" / "out"
PG = json.loads((HERE / "picogk.json").read_text(encoding="utf-8"))
PID = PG["part_id"]
P = {k: v["value"] for k, v in PG["parameters"].items()}
L, slip = P["length_mm"], P["slip_depth_mm"]
rIn = P["inlet_pipe_od_mm"] / 2 + P["slip_clearance_mm"]
W, H = P["outlet_width_mm"] / 2, P["outlet_height_mm"] / 2
wo, wi, gap, lip = P["outer_wall_mm"], P["inner_wall_mm"], P["gap_mm"], P["outlet_lip_mm"]
aOut, bOut = W - wo - gap - wi, H - wo - gap - wi
H_EL = 2.0                                   # element size (mm)
r_collar = rIn + P["collar_wall_mm"]         # slip / clamp collar outer radius


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def bore(z):
    t = smooth((z - slip) / (L - slip))
    return rIn + (aOut - rIn) * t, rIn + (bOut - rIn) * t


def rings(zs, ab, m):
    th = np.linspace(0, 2 * np.pi, m, endpoint=False)
    out = []
    for z in zs:
        a, b = ab(z)
        out.append(np.stack([a * np.cos(th), b * np.sin(th), np.full(m, z)], 1))
    return np.array(out)


def tube_faces(k, m, off=0):
    f = []
    for i in range(k - 1):
        for j in range(m):
            a, b = off + i * m + j, off + i * m + (j + 1) % m
            c, d = a + m, b + m
            f += [[a, b, d], [a, d, c]]
    return f


def solid_loft(R):
    """Closed filled solid from rings R (K, M, 3), fan caps at the end centroids."""
    k, m, _ = R.shape
    v = list(R.reshape(-1, 3)) + [R[0].mean(0), R[-1].mean(0)]
    f = tube_faces(k, m)
    c0, c1 = k * m, k * m + 1
    f += [[c0, (j + 1) % m, j] for j in range(m)]
    f += [[c1, (k - 1) * m + j, (k - 1) * m + (j + 1) % m] for j in range(m)]
    return finish(v, f)


def annulus_loft(Ro, Ri):
    """Closed annular solid between outer rings Ro and inner rings Ri (same K, M)."""
    k, m, _ = Ro.shape
    v = list(Ro.reshape(-1, 3)) + list(Ri.reshape(-1, 3))
    f = tube_faces(k, m) + tube_faces(k, m, k * m)
    for i, s in ((0, 1), (k - 1, -1)):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            f += [[a, b, k * m + b], [a, k * m + b, k * m + a]]
    return finish(v, f)


def finish(v, f):
    mesh = trimesh.Trimesh(np.array(v), np.array(f), process=True)
    mesh.fix_normals()
    assert mesh.is_watertight and mesh.volume > 0, "region mesh not closed"
    return mesh


def save(mesh, name):
    path = TILES / f"{name}.stl"
    mesh.export(path)
    return path.relative_to(ROOT).as_posix()


def tiles(name, z0, z1, ab, m, slab, step=2.0, overlap=0.5):
    """Filled loft cut into z slabs that overlap by `overlap` mm: each tile has a
    small bounding box, so trimesh.contains stays fast in topopt.py, and the
    overlap keeps the PicoGK union / subtraction free of seams."""
    edges = np.linspace(z0, z1, max(1, int(round((z1 - z0) / slab))) + 1)
    out = []
    for i in range(len(edges) - 1):
        a, b = max(z0, edges[i] - overlap), min(z1, edges[i + 1] + overlap)
        zs = np.linspace(a, b, max(2, int(np.ceil((b - a) / step)) + 1))
        out.append({"type": "stl", "path": save(solid_loft(rings(zs, ab, m)), f"{name}-{i:02d}")})
    return out


def off(d):
    return lambda z: tuple(x + d for x in bore(z))


TILES = OUT / "bionic-regions" / PID
TILES.mkdir(parents=True, exist_ok=True)
for old in TILES.glob("*.stl"):
    old.unlink()


def outer(z):
    """Outer profile of the printed base body: clamp collar, 6 mm taper onto the
    flow shell, flow shell, 3 mm flare out to the closed outlet lip at the envelope."""
    def lerp(p, q, u):
        return tuple(x + (y - x) * u for x, y in zip(p, q))
    z1, z2 = L - lip - 3.0, L - lip
    if z <= slip:
        return r_collar, r_collar
    if z < slip + 6.0:
        return lerp((r_collar, r_collar), off(wi)(slip + 6.0), (z - slip) / 6.0)
    if z < z1:
        return off(wi)(z)
    if z < z2:
        return lerp(off(wi)(z1), (W, H), smooth((z - z1) / 3.0))
    return W, H


zf = np.unique(np.r_[np.linspace(0, L, 481), slip, slip + 6.0, L - lip - 3.0, L - lip])
# printed: exact flow shell with collar and lip (fine mesh, PicoGK only), through shaping.base_stl
shell_path = save(annulus_loft(rings(zf, outer, 360), rings(zf, bore, 360)), "shell")
# exact wetted bore, both ends open (cut last); 0.5 mm z steps, 160 segments (chord error < 0.01 mm)
bore_tiles = tiles("bore", -2.0, L + 2.0, bore, 160, slab=4.0, step=0.5)
# analysis-only band: one element outside the bore (the bore void removes the inside)
band_tiles = tiles("band", -1.0, L, off(H_EL), 96, slab=6.0)
# design domain: the published outlet envelope as an elliptic cylinder above the clamp band
env_tiles = tiles("envelope", slip - 15, L, lambda z: (W, H), 96, slab=8.0, step=8.0)
# mid-flare load ring: band nodes on the wetted side only (inside the bore + 1 mm)
mid_tiles = tiles("midring", 70.0, 80.0, off(1.0), 96, slab=10.0)
# printed outlet lip: from half the shell wall out to the published outlet envelope
lip_path = save(annulus_loft(rings(np.linspace(L - lip, L, 5), lambda z: (W, H), 160),
                             rings(np.linspace(L - lip, L, 5), off(wi / 2), 160)), "lip")



def skin_patch(name, z0, z1, side, m=192, slab=17.0, d_in=-1.5, d_out=0.5):
    """Thin closed patches hugging the wetted bore surface (bore + d_in .. bore + d_out)
    where the outward normal points to `side`: pressure load regions that touch only
    the shell band's wetted-side nodes."""
    ax, sgn = {"+x": (0, 1), "-x": (0, -1), "+y": (1, 1), "-y": (1, -1)}[side]
    th = np.linspace(0, 2 * np.pi, m, endpoint=False)
    edges = np.linspace(z0, z1, max(1, int(round((z1 - z0) / slab))) + 1)
    out = []
    for i in range(len(edges) - 1):
        Z = np.linspace(edges[i], edges[i + 1], max(2, int(np.ceil((edges[i + 1] - edges[i]) / 2.0)) + 1))
        a, b = bore(Z[0])
        nrm = np.stack([np.cos(th) / a, np.sin(th) / b], 1)
        nrm /= np.linalg.norm(nrm, axis=1)[:, None]
        mask = sgn * nrm[:, ax] > np.cos(np.pi / 4)
        start = int(np.flatnonzero(mask & ~np.roll(mask, 1))[0])
        sel = (start + np.arange(int(mask.sum()))) % m
        Ro, Ri = rings(Z, off(d_out), m)[:, sel], rings(Z, off(d_in), m)[:, sel]
        k, j = Ro.shape[:2]
        v = list(Ro.reshape(-1, 3)) + list(Ri.reshape(-1, 3))
        f = []
        for base_ in (0, k * j):
            for r in range(k - 1):
                for c in range(j - 1):
                    p0 = base_ + r * j + c
                    f += [[p0, p0 + 1, p0 + j + 1], [p0, p0 + j + 1, p0 + j]]
        for r in range(k - 1):
            for c in (0, j - 1):
                p0, p1 = r * j + c, (r + 1) * j + c
                f += [[p0, p1, k * j + p1], [p0, k * j + p1, k * j + p0]]
        for r in (0, k - 1):
            for c in range(j - 1):
                p0, p1 = r * j + c, r * j + c + 1
                f += [[p0, p1, k * j + p1], [p0, k * j + p1, k * j + p0]]
        out.append({"type": "stl", "path": save(finish(v, f), f"skin{'p' if side[0] == '+' else 'm'}{side[1]}-{i:02d}")})
    return out


p_screen = 0.03                                    # N/mm2, screen_gauge_pressure_pa 30 kPa
zg = np.linspace(slip, L, 171)
Fpy = round(p_screen * np.trapezoid([2 * bore(z)[0] for z in zg], zg), 0)   # on each broad (+-y) side
Fpx = round(p_screen * np.trapezoid([2 * bore(z)[1] for z in zg], zg), 0)   # on each narrow (+-x) side
skins = {s: skin_patch("skin", slip, L - lip, s) for s in ("+x", "-x", "+y", "-y")}

mass_kg = {"993-EXH-OVAL-TIP-IN625-F0-0001": 0.40638, "993-EXH-OVAL-TIP-TI-F1-0001": 0.21234}[PID]
g_inertia = 20.0
F_in = round(mass_kg * 9.81 * g_inertia, 1)
F_p = 77.6
screen = "evidence/engineering-screen.json" if "IN625" in PID else "evidence/engineering-screen-ti64.json"
lipreg = [{"type": "stl", "path": lip_path}]
midreg = mid_tiles


def tag(shapes, basis, note):
    shapes[0].update({"basis": basis, "note": note})
    return shapes


def split(f):
    return [{"region": lipreg, "force_N": [x / 2 for x in f]}, {"region": midreg, "force_N": [x / 2 for x in f]}]


spec = {
    "part_id": PID,
    "method": "3D SIMP topology optimization (parts/picogk-catalog/bionic/topopt.py) of the structure between the exact thin flow shell and the published outlet envelope; the flow shell is an analysis_only band (stiffness inner_wall / element) printed from shaping.base_stl together with the exact clamp collar and outlet lip (analysis-only solids of stiffness 1), bore cut last. Region meshes: source/bionic_regions.py writes them to parts/picogk-catalog/out/bionic-regions/.",
    "basis_note": f"Interfaces and loads are NOT measured. Bore, collar and lip come from the F0 hypotheses of source/picogk.json; the slip collar is assumed clamped over its lower 18 mm. Inertia: screening mass {mass_kg * 1000:.0f} g ({screen}) x {g_inertia:g} g (assumed vibration / shock envelope, no published value); axial: the screen's axial_pressure_force_n {F_p} N plus the same inertia; ovalization: the screen's 30 kPa gauge pressure on the flare walls. Thermal growth is not a SIMP load.",
    "generator": "bionic_regions.py (this folder) writes this file and the region meshes from source/picogk.json",
    "optimization": {
        "element_mm": H_EL,
        "grid_min": [-W - 1, -H - 1, 0.0],
        "grid_max": [W + 1, H + 1, L],
        "design": tag(env_tiles, "published",
                      "published 120 x 85 mm outlet envelope as an elliptic cylinder (z tiles), from 15 mm below the end of the slip fit to the outlet"),
        "solid": tag([dict(t, analysis_only=True, stiffness_scale=round(wi / H_EL, 3)) for t in band_tiles], "assumption",
                     f"exact {wi:g} mm flow shell as a one-element band outside the bore (z tiles, stiffness {wi:g} / {H_EL:g}); printed from shaping.base_stl")
        + [
            {"type": "stl", "path": lip_path, "analysis_only": True, "stiffness_scale": 1.0, "basis": "assumption",
             "note": f"closed outlet lip, {lip:g} mm axial, out to the published outlet envelope; printed from shaping.base_stl"},
            {"type": "cyl", "a": [0, 0, 0], "b": [0, 0, slip], "r": round(r_collar, 3), "analysis_only": True, "stiffness_scale": 1.0, "basis": "assumption",
             "note": f"slip / clamp collar over the slip depth, collar_wall_mm thick (outer radius {r_collar:.1f} mm); printed from shaping.base_stl"},
        ],
        "void": tag(bore_tiles, "assumption", "exact wetted bore of OvalExhaustTip.cs (slip bore, smoothstep loft to the oval), open at both ends, z tiles overlapping 0.5 mm"),
        "supports": [
            {"type": "cyl", "a": [0, 0, -0.5], "b": [0, 0, 18.0], "r": round(r_collar + 0.6, 3), "basis": "assumption", "note": "band clamp over the lower 18 mm of the slip collar"},
        ],
        "load_cases": [
            {"name": "vertical_y", "basis": "assumption", "note": f"{mass_kg * 1000:.0f} g x {g_inertia:g} g = {F_in} N across the oval minor axis, half on the outlet lip, half on the mid-flare shell",
             "loads": split([0, -F_in, 0])},
            {"name": "lateral_x", "basis": "assumption", "note": f"same {F_in} N along the oval major axis", "loads": split([F_in, 0, 0])},
            {"name": "axial_z", "basis": "assumption", "note": f"screen axial_pressure_force_n {F_p} N + {F_in} N inertia along the axis",
             "loads": split([0, 0, round(F_p + F_in, 1)])},
            {"name": "pressure_ovalization", "basis": "assumption",
             "note": f"screen_gauge_pressure_pa 30 kPa ({screen}) x projected flare areas: {Fpy:g} N on each broad side, {Fpx:g} N on each narrow side, on the shell band's wetted-side nodes (the oval section bends under pressure)",
             "loads": [{"region": skins["+y"], "force_N": [0, Fpy, 0]}, {"region": skins["-y"], "force_N": [0, -Fpy, 0]},
                       {"region": skins["+x"], "force_N": [Fpx, 0, 0]}, {"region": skins["-x"], "force_N": [-Fpx, 0, 0]}]},
        ],
        "volume_fraction": None,
        "filter_radius_mm": 5.0,
        "iterations": 45,
        "analysis_only_layers": 2,
    },
    "shaping": {
        "smooth_mm": 2.5,
        "blend_mm": 0.35,
        "blend_note": f"PicoGK Smoothen offsets inward first: the blend stays below half the {wi:g} mm flow shell",
        "base_stl": shell_path,
        "lattice_grey": False,
    },
}

# volume fraction = fixed solids + 16 % of the free design elements (counted as topopt.py does)
o = spec["optimization"]
h = o["element_mm"]
lo, hi = np.array(o["grid_min"]), np.array(o["grid_max"])
n = np.ceil((hi - lo) / h).astype(int)
g = np.stack(np.meshgrid(*[lo[i] + (np.arange(n[i]) + 0.5) * h for i in range(3)], indexing="ij"), -1).reshape(-1, 3)


def inside(s):
    if s["type"] == "stl":
        return trimesh.load_mesh(ROOT / s["path"]).contains(g)
    a, b = np.array(s["a"]), np.array(s["b"])
    t = (g - a) @ (b - a) / ((b - a) @ (b - a))
    return (np.linalg.norm(g - a - np.outer(t, b - a), axis=1) <= s["r"]) & (t >= 0) & (t <= 1)


design = np.any([inside(s) for s in o["design"]], 0)
solid = np.any([inside(s) for s in o["solid"]], 0)
void = np.any([inside(s) for s in o["void"]], 0)
active = (design | solid) & ~void
fixed = solid & active
free_share = 0.06
o["volume_fraction"] = round(float((fixed.sum() + free_share * (active.sum() - fixed.sum())) / active.sum()), 3)
o["volume_fraction_note"] = f"{int(fixed.sum())} fixed (analysis-only shell band, lip, collar) + {free_share:.0%} of {int(active.sum() - fixed.sum())} free elements, over {int(active.sum())} active"
(HERE / "bionic.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"{PID}: active {int(active.sum())}, fixed {int(fixed.sum())}, volume_fraction {o['volume_fraction']}, F_in {F_in} N")
