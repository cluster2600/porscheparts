#!/usr/bin/env python3
"""Exact functional bodies for the bionic engine parts (bionic.json inputs).

    python bionic_bases.py <PART_ID>

The bionic generator grows the load-carrying structure from topopt.py's
density field; the functional skins that are NOT free for the optimiser
(piston crown/ring belt/skirt, valve-cover shell and flange, chain-case shell,
oil-console galleries, valve exterior) are rebuilt here from the same signed
distances as the previous generators (engine/*.cs), meshed by marching cubes
and written to parts/picogk-catalog/out/bionic/:

  <ID>.base.stl      full resolution, shaping.base_stl (PicoGK only)

topopt.py sees these skins only through primitive keep-ins/keep-outs in
bionic.json that lie inside them (STL regions are too slow for trimesh at
these sizes), so the density body never crosses a functional surface.

Dimensions come from parts/<id>/source/picogk.json (same parameter names as
the previous generator). Nothing here is measured; see each bionic.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]
OUT = CATALOG / "out" / "bionic"


# --- vectorised helpers (same formulas as engine/EngineSdf.cs) -----------------
def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def len2(x, y):
    return np.sqrt(x * x + y * y)


def rect2(px, py, cx, cy, hx, hy, r):
    qx, qy = np.abs(px - cx) - hx + r, np.abs(py - cy) - hy + r
    return len2(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def round_edge(d2, dz, r):
    qx, qz = d2 + r, dz + r
    return len2(np.maximum(qx, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, qz), 0) - r


FAR, CULL = 1e6, 8.0     # culled primitives return FAR (outside), beyond any blend radius


def _far(P, a, b, r):
    """True when the z-range of P (one meshing slice) misses the primitive by more than CULL."""
    z0, z1 = P[:, 2].min(), P[:, 2].max()
    return z1 < min(a[2], b[2]) - r - CULL or z0 > max(a[2], b[2]) + r + CULL


def cyl(P, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if _far(P, a, b, r):
        return np.full(len(P), FAR)
    ba = b - a
    pa = P - a
    baba = ba @ ba
    paba = pa @ ba
    x = np.linalg.norm(pa * baba - np.outer(paba, ba), axis=1) - r * baba
    y = np.abs(paba - baba * 0.5) - baba * 0.5
    x2, y2 = x * x, y * y * baba
    d = np.where(np.maximum(x, y) < 0, -np.minimum(x2, y2), np.where(x > 0, x2, 0) + np.where(y > 0, y2, 0))
    return np.sign(d) * np.sqrt(np.abs(d)) / baba


def capsule(P, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if _far(P, a, b, r):
        return np.full(len(P), FAR)
    pa, ba = P - a, b - a
    if ba @ ba < 1e-12:                                  # zero-length segment: a sphere
        return np.linalg.norm(pa, axis=1) - r
    h = np.clip(pa @ ba / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - np.outer(h, ba), axis=1) - r


def tube(P, pts, r):
    d = np.full(len(P), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        d = np.minimum(d, capsule(P, a, b, r))
    return d


def cubic_pts(a, b, c, d, n):
    a, b, c, d = (np.asarray(v, float) for v in (a, b, c, d))
    t = np.linspace(0, 1, n + 1)[:, None]
    u = 1 - t
    return list(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d)


def round_box(P, c, half, r):
    q = np.abs(P - np.asarray(c, float)) - (np.asarray(half, float) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r


def twin_circle(x, y, c1, c2, r1, r2):
    px, py, h = np.abs(y), x - c1, c2 - c1
    b = (r1 - r2) / h
    a = np.sqrt(1 - b * b)
    k = -b * px + a * py
    return np.where(k < 0, len2(px, py) - r1, np.where(k > a * h, len2(px, py - h) - r2, a * px + b * py - r1))


def twin_contour(s01, c1, c2, r1, r2):
    h = c2 - c1
    b = (r1 - r2) / h
    a = np.sqrt(1 - b * b)
    th0 = np.arctan2(a, b)
    seg, big, small = h * a, r1 * (2 * np.pi - 2 * th0), r2 * 2 * th0
    s = (s01 - np.floor(s01)) * (big + small + 2 * seg)
    if s < small:
        t = -th0 + s / r2
        n = np.array([np.cos(t), np.sin(t)])
        return np.array([c2, 0]) + r2 * n, n
    s -= small
    if s < seg:
        p0, p1 = np.array([c2 + b * r2, a * r2]), np.array([c1 + b * r1, a * r1])
        return p0 + (p1 - p0) * s / seg, np.array([b, a])
    s -= seg
    if s < big:
        t = th0 + s / r1
        n = np.array([np.cos(t), np.sin(t)])
        return np.array([c1, 0]) + r1 * n, n
    s -= big
    q0, q1 = np.array([c1 + b * r1, -a * r1]), np.array([c2 + b * r2, -a * r2])
    return q0 + (q1 - q0) * s / seg, np.array([b, -a])


# --- meshing ---------------------------------------------------------------------
def mesh_sdf(F, lo, hi, step, path, dec_step=0):
    """Marching cubes of F at `step` -> path; if dec_step, a coarse copy of the
    same field (a re-mesh, faster than decimating) -> *.base-dec.stl / *.neg-dec.stl."""
    m = _mesh(F, lo, hi, step, path)
    if dec_step:
        dpath = path.with_name(path.name.replace(".base.stl", ".base-dec.stl").replace(".neg.stl", ".neg-dec.stl"))
        _mesh(F, lo, hi, max(dec_step, step), dpath)
    return m


def _mesh(F, lo, hi, step, path):
    # grid shifted off round coordinates: no sample lands exactly on a flat face (zero values open the contour)
    # (padding 1.5 mm: smooth-min fillets bulge a little past the nominal box)
    lo, hi = np.asarray(lo, float) - 1.5 - 0.1234 * step, np.asarray(hi, float) + 1.5
    n = np.ceil((hi - lo) / step).astype(int) + 1
    xs, ys, zs = (lo[i] + np.arange(n[i]) * step for i in range(3))
    vals = np.empty((n[2], n[1], n[0]), np.float32)
    X, Y = np.meshgrid(xs, ys, indexing="xy")          # (ny, nx)
    for k, z in enumerate(zs):
        P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], 1)
        vals[k] = F(P).reshape(n[1], n[0])
    grid = pv.ImageData(dimensions=tuple(int(v) for v in n), spacing=(step,) * 3, origin=tuple(lo))
    grid.point_data["d"] = vals.ravel()                  # x fastest, then y, then z
    surf = grid.contour([0.0], scalars="d").triangulate().clean()
    m = trimesh.Trimesh(surf.points, surf.faces.reshape(-1, 4)[:, 1:], process=False)
    if m.volume < 0:                                     # contour winding follows the gradient: one flip at most
        m.invert()
    OUT.mkdir(parents=True, exist_ok=True)
    m.export(path)
    print(f"{path.name}: {len(m.faces)} tris, volume {m.volume / 1000:.2f} cm3, bounds {m.bounds.round(2).tolist()}", flush=True)
    return m


def params(part_id):
    d = json.loads((ROOT / "parts" / part_id.lower() / "source" / "picogk.json").read_text(encoding="utf-8"))
    return {k: v["value"] for k, v in d["parameters"].items()}


# --- piston ----------------------------------------------------------------------
def piston(pid):
    s = params(pid)
    R, H = s["piston_outer_diameter_mm"] / 2, s["piston_height_mm"]
    zTop = H / 2
    rCav, zCav = s["inner_cavity_diameter_mm"] / 2, s["inner_cavity_top_z_mm"]
    zPin, rBoss, xBoss = s["pin_axis_z_mm"], s["pin_boss_outer_diameter_mm"] / 2, s["pin_boss_length_mm"] / 2
    rRoot = s["ring_groove_root_diameter_mm"] / 2
    gz = [s[f"ring_groove_{i}_center_z_mm"] for i in (1, 2, 3)]
    gh = [s[f"ring_groove_{i}_height_mm"] for i in (1, 2, 3)]
    rBowl, dBowl = s["bowl_diameter_mm"] / 2, s["bowl_depth_mm"]
    Rg, rg, zg = s["gallery_major_radius_mm"], s["gallery_minor_radius_mm"], s["gallery_center_z_mm"]
    rPort, xPort, lPort = s["gallery_port_diameter_mm"] / 2, s["gallery_port_center_x_mm"], s["gallery_port_length_mm"]
    xWin, yWin, zWin = s["skirt_panel_x_mm"], s["skirt_panel_half_width_mm"], s["skirt_panel_top_z_mm"]
    skirt = s["skirt_wall_mm"]
    nDrain, rDrain = int(s["oil_drain_hole_count"]), s["oil_drain_hole_diameter_mm"] / 2
    sphR = (rBowl ** 2 + dBowl ** 2) / (2 * dBowl)
    sphC = np.array([0, 0, zTop - dBowl + sphR])
    drains = [(np.cos((k + 0.5) * 2 * np.pi / nDrain), np.sin((k + 0.5) * 2 * np.pi / nDrain)) for k in range(nDrain)]

    def exterior_negative(P):
        """< 0 where the functional exterior must stay empty."""
        x, y, z = P.T
        r, ax = len2(x, y), np.abs(x)
        q = np.stack([ax, y, z], 1)
        neg = np.minimum(R - r, zTop - z)                                   # outside the piston OD / above the crown
        neg = np.minimum(neg, z + zTop)                                      # below the skirt
        neg = np.minimum(neg, np.linalg.norm(P - sphC, axis=1) - sphR)       # crown dish
        for c, h in zip(gz, gh):                                             # ring grooves
            neg = np.minimum(neg, np.maximum(rRoot - r, np.abs(z - c) - h / 2))
        neg = np.minimum(neg, len2(r - Rg, z - zg) - rg)                     # cooling gallery
        neg = np.minimum(neg, cyl(q, (xPort - lPort / 2, 0, zg), (xPort + lPort / 2, 0, zg), rPort))
        for ux, uy in drains:                                                # oil-ring drain holes
            neg = np.minimum(neg, cyl(P, (ux * (rCav - 4), uy * (rCav - 4), gz[2]), (ux * (R - 1), uy * (R - 1), gz[2]), rDrain))
        panel = smax(smax(xWin - ax, np.abs(y) - yWin, 4), z - zWin, 4)    # slipper-skirt pin-side recess ...
        boss = cyl(q, (0, 0, zPin), (xBoss, 0, zPin), rBoss)                 # ... around the pin-boss stub
        neg = np.minimum(neg, np.maximum(panel, -boss))
        return neg

    def shell(P):
        x, y, z = P.T
        r = len2(x, y)
        outer = rect2(r, z, 0, 0, R, H / 2, 0.8)
        cavA = smax(r - rCav, z - zCav, 5)                                   # under-crown cavity (as before)
        cavB = np.maximum(r - (R - skirt), z - zWin)                         # thin skirt below the ring belt
        cav = smin(cavA, cavB, 3)
        d = np.maximum(outer, -cav)
        return np.maximum(d, -exterior_negative(P))

    lo, hi = (-R, -R, -zTop), (R, R, zTop)
    mesh_sdf(shell, lo, hi, 0.3, OUT / f"{pid}.base.stl")



# --- upper valve cover -------------------------------------------------------------
def valve_cover(pid):
    """Sealing skin (roof, walls, gasket flange), bolt bosses and coil towers;
    the roof fins of the previous model are left to the optimiser."""
    s = params(pid)
    L, W, H = s["length_mm"] / 2, s["width_mm"] / 2, s["shell_height_mm"]
    roof, wall = s["roof_thickness_mm"], s["wall_thickness_mm"]
    inset, tf = s["side_flange_width_mm"], s["flange_thickness_mm"]
    rTop, rCorner = s["top_edge_radius_mm"], s["plan_corner_radius_mm"]
    towerH, rTower, rTowerBore = s["cop_tower_height_mm"], s["cop_tower_outer_diameter_mm"] / 2, s["cop_tower_bore_diameter_mm"] / 2
    towerX = [s[f"cop_tower_{i}_x_mm"] for i in (1, 2, 3)]
    earOff, rEar, rEarHole = s["coil_ear_offset_mm"], s["coil_ear_diameter_mm"] / 2, s["coil_ear_hole_diameter_mm"] / 2
    rBoss, rBolt, hBoss, rScallop = s["bolt_boss_outer_diameter_mm"] / 2, s["bolt_bore_diameter_mm"] / 2, s["bolt_boss_height_mm"], s["bolt_pocket_radius_mm"]
    nBolt, pitch, boltY = int(s["bolt_count_per_side"]), s["bolt_pitch_x_mm"], s["bolt_y_mm"]
    rib = s["rib_layer_mm"]
    bolts = [((i - (nBolt - 1) / 2) * pitch, y) for i in range(nBolt) for y in (-boltY, boltY)]
    zTowerTop = H + towerH

    def forms(P):
        x, y, z = P.T
        plan = rect2(x, y, 0, 0, L - inset, W - inset, rCorner)
        ext = round_edge(plan, z - H, rTop)
        pockets = np.full(len(P), np.inf)
        bosses = np.full(len(P), np.inf)
        holes = np.full(len(P), np.inf)
        for bx, by in bolts:
            rb = len2(x - bx, y - by)
            pockets = np.minimum(pockets, np.maximum(rb - rScallop, hBoss - z))
            bosses = np.minimum(bosses, round_edge(rb - rBoss, np.maximum(-z, z - hBoss), 0.8))
            holes = np.minimum(holes, rb - rBolt)
        ext = smax(ext, -pockets, 2)
        fplan = rect2(x, y, 0, 0, L, W, rCorner + inset)
        return plan, ext, pockets, bosses, holes, fplan

    def skin(P):
        x, y, z = P.T
        plan, ext, pockets, bosses, holes, fplan = forms(P)
        shell = np.maximum(np.maximum(ext, -z), -(ext + wall))       # conformal skin (wall = roof here)
        flange = np.maximum(np.maximum(round_edge(fplan, z - tf, 1.5), -z), -(plan + wall))
        d = smin(shell, flange, 3)
        d = smin(d, bosses, 1.5)
        towers = np.full(len(P), np.inf)
        bores = np.full(len(P), np.inf)
        for tx in towerX:
            rt = len2(x - tx, y)
            towers = np.minimum(towers, round_edge(rt - rTower, np.maximum(H - roof - z, z - zTowerTop), 1.2))
            re = len2(x - tx - earOff, y)
            towers = smin(towers, round_edge(re - rEar, np.maximum(H - roof - z, z - (zTowerTop - 6)), 1), 2)
            bores = np.minimum(bores, np.maximum(rt - rTowerBore, H - roof - 2 - z))
            bores = np.minimum(bores, np.maximum(re - rEarHole, zTowerTop - 16 - z))
        d = smin(d, towers, 4)
        d = np.maximum(d, -bores)
        return np.maximum(d, -np.maximum(holes, -z - 1))


    lo, hi = (-L, -W, 0), (L, W, zTowerTop)
    mesh_sdf(skin, lo, hi, 0.3, OUT / f"{pid}.base.stl")


# --- oil filter console -------------------------------------------------------------
def oil_filter_console(pid):
    """Gallery tubes with their minimum wall, port bosses, mounting pads and the
    filter interface (pedestal cap, seal land, inlet annulus, spigot). The body
    between them is left to the optimiser."""
    s = params(pid)
    L, W = s["body_length_mm"] / 2, s["body_width_mm"] / 2
    hPad, rPad, rMount = s["body_height_mm"], s["mount_pad_diameter_mm"] / 2, s["mount_bore_diameter_mm"] / 2
    mx, my = s["mount_x_mm"], s["mount_y_mm"]
    cx, rPed = s["filter_pedestal_center_x_mm"], s["filter_pedestal_outer_diameter_mm"] / 2
    zPed = hPad + s["filter_pedestal_height_mm"]
    rSealO, rSealI, hSeal = s["filter_seal_land_outer_diameter_mm"] / 2, s["filter_seal_land_inner_diameter_mm"] / 2, s["filter_seal_land_height_mm"]
    rSpig, rSpigBore, hSpig = s["filter_spigot_outer_diameter_mm"] / 2, s["filter_spigot_bore_diameter_mm"] / 2, s["filter_spigot_height_mm"]
    annulusDepth = s["filter_inlet_annulus_depth_mm"]
    rPortBoss, lPortBoss = s["external_port_boss_diameter_mm"] / 2, s["external_port_boss_length_mm"]
    rGal, galWall = s["main_gallery_diameter_mm"] / 2, s["minimum_channel_wall_mm"]
    yIn, zIn, yOut, zOut = s["inlet_gallery_y_mm"], s["inlet_gallery_z_mm"], s["outlet_gallery_y_mm"], s["outlet_gallery_z_mm"]
    cap = s["pedestal_cap_mm"]
    xEnd = L + lPortBoss / 2
    zSpigTop = zPed + hSpig
    inlet = [np.array([-xEnd - 1, yIn, zIn]), np.array([-L + 8, yIn, zIn])]
    inlet += cubic_pts((-L + 8, yIn, zIn), (cx - 20, yIn, zIn), (cx, yIn, zIn + 2), (cx, yIn, zIn + 17), 12)
    inlet.append(np.array([cx, yIn, zPed + 2]))
    outlet = cubic_pts((cx, yOut, zPed - 12), (cx, yOut, zOut + 2), (cx + 14, yOut, zOut), (L - 6, yOut, zOut), 12)
    outlet.append(np.array([xEnd + 1, yOut, zOut]))
    pads = [(-mx, -my), (-mx, my), (mx, -my), (mx, my)]

    def bores(P):
        x, y, z = P.T
        rp = len2(x - cx, y)
        gal = np.minimum(tube(P, inlet, rGal), tube(P, outlet, rGal))
        spigBore = np.maximum(rp - rSpigBore, zPed - 13 - z)
        mounts = np.full(len(P), np.inf)
        for m in pads:
            mounts = np.minimum(mounts, len2(x - m[0], y - m[1]) - rMount)
        annulus = np.maximum(np.maximum(rp - (rSealI - 2), rSpig + 2 - rp), zPed - annulusDepth - z)
        return np.minimum(np.minimum(gal, spigBore), np.minimum(mounts, annulus))

    def base(P):
        x, y, z = P.T
        rp = len2(x - cx, y)
        padD = np.full(len(P), np.inf)
        for m in pads:
            padD = np.minimum(padD, round_edge(len2(x - m[0], y - m[1]) - rPad, z - hPad, 1.5))
        d = np.maximum(padD, -z)
        pedcap = round_edge(rp - rPed, np.maximum(zPed - cap - z, z - zPed), 2.5)      # filter-side cap of the pedestal
        d = np.minimum(d, pedcap)
        seal = np.maximum(np.maximum(rp - rSealO, rSealI - rp), np.maximum(zPed - 1 - z, z - (zPed + hSeal)))
        d = smin(d, seal, 0.5)
        tubes = np.minimum(tube(P, inlet, rGal + galWall), tube(P, outlet, rGal + galWall))
        tubes = np.maximum(np.maximum(tubes, -z), np.maximum(np.abs(x) - xEnd, z - (zPed - 2)))
        ports = np.minimum(cyl(P, (-xEnd, yIn, zIn), (-xEnd + lPortBoss, yIn, zIn), rPortBoss),
                           cyl(P, (xEnd - lPortBoss, yOut, zOut), (xEnd, yOut, zOut), rPortBoss))
        d = smin(d, np.maximum(np.minimum(tubes, ports), -z), 4)
        d = smax(d, -np.maximum(np.maximum(rp - (rSealI - 2), rSpig + 2 - rp), zPed - annulusDepth - z), 1)
        spig = round_edge(rp - rSpig, np.maximum(zPed - annulusDepth - 1 - z, z - zSpigTop), 1)
        d = smin(d, spig, 1.5)
        return np.maximum(d, -bores(P))


    lo, hi = (-xEnd, -W, 0), (xEnd, W, zSpigTop)
    mesh_sdf(base, lo, hi, 0.25, OUT / f"{pid}.base.stl")


# --- chain case ----------------------------------------------------------------------
def chain_case(pid):
    """Conformal skin on the bolted perimeter flange, flange bosses, the two bolted
    lid plateaus (parting groove, bolt heads) and the tensioner boss; gussets and
    face ribs are left to the optimiser."""
    s = params(pid)
    L, W, H = s["length_mm"], s["width_mm"], s["height_mm"]
    wall, inset, tf = s["wall_mm"], s["flange_width_mm"], s["flange_thickness_mm"]
    rSmallBay, rEdge, lidRaise = s["small_bay_radius_mm"], s["top_edge_radius_mm"], s["lid_raise_mm"]
    rLidA, bcA, nLidA = s["lid_a_radius_mm"], s["lid_a_bolt_circle_mm"] / 2, int(s["lid_a_bolt_count"])
    rLidB, bcB, nLidB = s["lid_b_radius_mm"], s["lid_b_bolt_circle_mm"] / 2, int(s["lid_b_bolt_count"])
    nFlange = int(s["flange_bolt_count"])
    rFB, rFBolt, hFB = s["flange_boss_diameter_mm"] / 2, s["flange_bolt_diameter_mm"] / 2, s["flange_boss_height_mm"]
    rTens, rTensBore = s["tensioner_boss_diameter_mm"] / 2, s["tensioner_bore_diameter_mm"] / 2
    xTens, zTens, reach = s["tensioner_x_mm"], s["tensioner_z_mm"], s["tensioner_reach_mm"]
    rib = s["rib_layer_mm"]
    R1, R2 = W / 2, rSmallBay
    c1, c2 = -L / 2 + R1, L / 2 - R2
    zShell = H - lidRaise
    S1, S2 = R1 - inset, R2 - inset
    fbolts = [twin_contour((i + 0.5) / nFlange, c1, c2, R1 - inset / 2, R2 - inset / 2)[0] for i in range(nFlange)]
    ring = lambda cx, rc, n: [(cx + rc * np.cos(np.pi / n + i * 2 * np.pi / n), rc * np.sin(np.pi / n + i * 2 * np.pi / n)) for i in range(n)]
    lidA_b, lidB_b = ring(c1, bcA, nLidA), ring(c2, bcB, nLidB)
    h = c2 - c1
    b = (S1 - S2) / h
    a = np.sqrt(1 - b * b)
    nT = np.array([b, -a])
    t = np.clip((xTens - (c1 + b * S1)) / (c2 - c1), 0, 1)
    wallPt = np.array([c1 + b * S1, -a * S1]) + t * (np.array([c2 + b * S2, -a * S2]) - np.array([c1 + b * S1, -a * S1]))
    tensIn = np.array([*(wallPt - nT * 6), zTens])
    tensOut = np.array([*(wallPt + nT * reach), zTens])
    capIn = np.array([*(wallPt + nT * (reach - 4)), zTens])
    n3 = np.array([nT[0], nT[1], 0.0])
    info = {"c1": c1, "c2": c2, "S1": S1, "S2": S2, "zShell": zShell, "flange_bolts": [p.round(3).tolist() for p in fbolts],
            "lid_a_bolts": np.round(lidA_b, 3).tolist(), "lid_b_bolts": np.round(lidB_b, 3).tolist(),
            "tensioner_in": tensIn.round(3).tolist(), "tensioner_out": tensOut.round(3).tolist(), "tensioner_axis": n3.round(4).tolist()}
    (OUT / f"{pid}.base.json").write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8", newline="\n")

    def lid(x, y, cx, rLid, bolts):
        plan = len2(x - cx, y) - rLid
        heads = np.full(len(x), np.inf)
        for qx, qy in bolts:
            rq = len2(x - qx, y - qy)
            plan = smin(plan, rq - 6, 3)
            heads = np.minimum(heads, rq - 3.5)
        return plan, heads

    def skin(P):
        x, y, z = P.T
        plan = twin_circle(x, y, c1, c2, S1, S2)
        ext = round_edge(plan, z - zShell, rEdge)
        d = np.maximum(np.maximum(ext, -z), -(ext + wall))
        fplan = twin_circle(x, y, c1, c2, R1, R2)
        flange = np.maximum(np.maximum(round_edge(fplan, z - tf, 1.5), -z), -(plan + wall))
        d = smin(d, flange, 3)
        bosses = np.full(len(P), np.inf)
        holes = np.full(len(P), np.inf)
        for qx, qy in fbolts:
            rq = len2(x - qx, y - qy)
            bosses = np.minimum(bosses, round_edge(rq - rFB, z - hFB, 1))
            holes = np.minimum(holes, rq - rFBolt)
        d = smin(d, np.maximum(np.maximum(bosses, -z), -(plan + wall)), 2)
        la, ha = lid(x, y, c1, rLidA, lidA_b)
        lb, hb = lid(x, y, c2, rLidB, lidB_b)
        lids = round_edge(np.minimum(la, lb), np.maximum(zShell - 2 - z, z - (H - 1.2)), 1.2)
        heads = round_edge(np.minimum(ha, hb), np.maximum(zShell - z, z - H), 0.6)
        lidRing = np.maximum(np.abs(np.minimum(la, lb) - 0.6) - 0.5, np.abs(z - zShell) - 0.6)
        d = np.maximum(np.minimum(d, lids), -lidRing)
        d = np.minimum(d, heads)
        d = smin(d, cyl(P, tensIn, tensOut, rTens), 3)
        capGroove = np.maximum(cyl(P, capIn, capIn + n3 * 0.8, rTens + 1), -cyl(P, capIn - n3, capIn + n3 * 1.8, rTens - 0.8))
        d = np.maximum(d, -capGroove)
        d = np.maximum(d, -cyl(P, tensIn - n3 * 4, capIn - n3 * 1.5, rTensBore))
        return np.maximum(d, -np.maximum(holes, np.maximum(-z - 1, z - hFB - 1)))


    lo, hi = (-L / 2, -W / 2, 0), (L / 2, W / 2, H)
    mesh_sdf(skin, lo, hi, 0.3, OUT / f"{pid}.base.stl")


# --- hollow valve -----------------------------------------------------------------------
def hollow_valve(pid):
    """Exact valve exterior (Valves.cs profile: margin, 45 deg seat, tulip, stem,
    keeper grooves, tip chamfer) as a skin around the conformal head cavity and
    the stem bore, without the old radial ribs (the optimiser grows them)."""
    s = params(pid)
    HeadR, Margin, Seat = s["head_diameter_mm"] / 2, s["head_margin_mm"], s["seat_radial_width_mm"]
    StemR, Length = s["stem_diameter_mm"] / 2, s["overall_length_mm"]
    nG, gR, gP, gT, tipC = int(s["keeper_groove_count"]), s["keeper_groove_radius_mm"], s["keeper_groove_pitch_mm"], s["keeper_groove_from_tip_mm"], s["tip_chamfer_mm"]
    wallH, lig = s["head_wall_mm"], s["head_cavity_bottom_z_mm"]
    rCav, zCavTop, rBore = s["head_cavity_bottom_radius_mm"], s["head_cavity_top_z_mm"], s["hollow_bore_diameter_mm"] / 2
    Rf = HeadR - Seat - StemR
    rSeat, zSeat, zf = HeadR - Seat, Margin + Seat, Margin + Seat + Rf
    i2 = 0.70710678

    def profile(r, z):
        face = smax(-z, r - HeadR, 0.4)
        lower = np.maximum(np.maximum(face, z - zSeat), (r + (z - Margin) - HeadR) * i2)
        tulip = np.maximum(np.maximum(r - rSeat, Margin - z), np.maximum(z - zf, Rf - len2(r - rSeat, z - zf)))
        stem = np.maximum(np.maximum(r - StemR, z - Length), Margin - z)
        stem = np.maximum(stem, (r + z - (Length + StemR - tipC)) * i2)
        d = np.minimum(np.minimum(lower, tulip), stem)
        for i in range(nG):
            zg = Length - gT - i * gP
            d = np.maximum(d, -(len2(r - StemR - 0.2 * gR, z - zg) - gR))
        return d

    def cavity(P):
        x, y, z = P.T
        r = len2(x, y)
        d = profile(r, z)
        cav = smax(smax(d + wallH, lig - z, 1), r - rCav, 2)
        return np.maximum(cav, z - zCavTop)

    def bore(P):
        x, y, z = P.T
        return np.maximum(len2(x, y) - rBore, lig + 0.8 - z)

    def skin(P):
        x, y, z = P.T
        return np.maximum(profile(len2(x, y), z), -np.minimum(cavity(P), bore(P)))



    mesh_sdf(skin, (-HeadR, -HeadR, 0), (HeadR, HeadR, Length), 0.2, OUT / f"{pid}.base.stl")


BUILDERS = {"993-ENG-PISTON-CP1-GALLERY-F0-0001": piston,
            "993-ENG-CHAIN-CASE-0001": chain_case,
            "993-ENG-INTAKE-VALVE-TI64-HOLLOW-F0-0001": hollow_valve,
            "993-ENG-UPPER-VALVE-COVER-ALSI10MG-F0-0001": valve_cover,
            "993-ENG-OIL-FILTER-CONSOLE-ALSI10MG-F0-0001": oil_filter_console}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in BUILDERS:
        raise SystemExit(__doc__)
    BUILDERS[sys.argv[1]](sys.argv[1])
