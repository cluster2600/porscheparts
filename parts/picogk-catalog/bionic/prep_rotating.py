#!/usr/bin/env python3
"""Bionic preparation of the rotating-machinery parts: the aerodynamic
surfaces stay exactly as in the functional model, only the structure behind
them (hub interior, back face, cup web, stator hub, housing spokes, actuator
bracket) is handed to the topology optimization (topopt.py).

    python prep_rotating.py <PART_ID> [element=..] [volfrac=..] [iters=..] [smooth=..] [blend=..]

1. The previous functional model (out/<PART_ID>-functional.stl, full
   resolution) is voxelized by z-ray parity at 0.75 x its PicoGK voxel size.
2. A structural region R (c_rem > 0) is removed from it: per part, the hub
   interior below a skin of constant thickness opened through the back face,
   the flat cup web, the stator hub annulus, the housing spoke disc, the
   actuator strut. The design domain D (c_des > 0, default R) is where
   topopt.py may grow material.
3. Written to out/bionic/ (not committed, regenerable):
     <PART_ID>-base.stl    functional body minus R (shaping.base_stl, full resolution)
     <PART_ID>-design.stl  D (topopt "design" region)
     <PART_ID>-shell.stl   kept body within 1.5 elements of D (topopt "solid"
                           keep-in: the optimizer sees the skin, rings and bosses
                           the new structure must join)
   and parts/<id>/source/bionic.json (regions, supports, load cases; every
   load is stated with its basis).

The rotors (compressor, turbine, impeller) are turned 180 deg about X (a
rotation, not a mirror: blade handedness is kept) so that the optimized back
face faces the catalogue's three-quarter view, as the fan housing is already
modelled inlet-up. Shapes are written in the published (model) frame.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh
from scipy import ndimage as ndi

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]
OUT = CATALOG / "out" / "bionic"
REL = "parts/picogk-catalog/out/bionic"
G = 9.81


def params(part_id):
    spec = json.loads((ROOT / "parts" / part_id.lower() / "source" / "picogk.json").read_text(encoding="utf-8"))
    return spec, {k: v["value"] for k, v in spec["parameters"].items()}


def screen(part_id):
    return json.loads((ROOT / "parts" / part_id.lower() / "evidence" / "engineering-screen.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- voxelization / meshing
def occupancy(V, F, lo, h, shape):
    """Inside of a closed mesh on cell-centred samples lo + (i + 0.5) h, by z-ray parity."""
    nx, ny, nz = shape
    jit = np.array([0.1234567, 0.2345678]) * h          # rays never run along PicoGK lattice edges
    x0, y0 = lo[0] + 0.5 * h + jit[0], lo[1] + 0.5 * h + jit[1]
    z0 = lo[2] + 0.5 * h
    T = V[F]
    i0 = np.ceil((T[:, :, 0].min(1) - x0) / h).astype(np.int64)
    i1 = np.floor((T[:, :, 0].max(1) - x0) / h).astype(np.int64)
    j0 = np.ceil((T[:, :, 1].min(1) - y0) / h).astype(np.int64)
    j1 = np.floor((T[:, :, 1].max(1) - y0) / h).astype(np.int64)
    ni, nj = np.clip(i1 - i0 + 1, 0, None), np.clip(j1 - j0 + 1, 0, None)
    k = ni * nj
    flat = []
    idx_all = np.flatnonzero(k)
    for c in range(0, len(idx_all), 200_000):
        idx = idx_all[c:c + 200_000]
        kk = k[idx]
        rep = np.repeat(idx, kk)
        off = np.arange(len(rep)) - np.repeat(np.cumsum(kk) - kk, kk)
        ii = i0[rep] + off % ni[rep]
        jj = j0[rep] + off // ni[rep]
        px, py = x0 + ii * h, y0 + jj * h
        A, B, C = T[rep, 0], T[rep, 1], T[rep, 2]
        w0 = (B[:, 0] - px) * (C[:, 1] - py) - (C[:, 0] - px) * (B[:, 1] - py)
        w1 = (C[:, 0] - px) * (A[:, 1] - py) - (A[:, 0] - px) * (C[:, 1] - py)
        w2 = (A[:, 0] - px) * (B[:, 1] - py) - (B[:, 0] - px) * (A[:, 1] - py)
        hit = ((w0 > 0) & (w1 > 0) & (w2 > 0)) | ((w0 < 0) & (w1 < 0) & (w2 < 0))
        hit &= (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny)
        s = w0 + w1 + w2
        z = (w0 * A[:, 2] + w1 * B[:, 2] + w2 * C[:, 2])[hit] / s[hit]
        kz = np.clip(np.ceil((z - z0) / h).astype(np.int64), 0, nz)
        flat.append((jj[hit] * nx + ii[hit]) * (nz + 1) + kz)
    flat = np.concatenate(flat)
    cnt = np.bincount(flat, minlength=nx * ny * (nz + 1)).astype(np.uint8).reshape(ny, nx, nz + 1)
    occ = (np.cumsum(cnt, axis=2, dtype=np.uint8)[:, :, :nz] & 1).astype(bool)
    return np.ascontiguousarray(occ.transpose(1, 0, 2))      # [i, j, k]


def contour(field, lo, h, sub=1):
    """Closed, outward-oriented surface of field > 0 (field sampled at cell centres lo + (i + 0.5) h)."""
    if sub > 1:
        field = field[::sub, ::sub, ::sub]
    g = pv.ImageData(dimensions=field.shape, spacing=(h * sub,) * 3, origin=tuple(np.asarray(lo) + 0.5 * h))
    g.point_data["f"] = field.ravel(order="F").astype(np.float32)
    m = g.contour([0.0], scalars="f").clean().triangulate()
    tm = trimesh.Trimesh(m.points, m.faces.reshape(-1, 4)[:, 1:], process=True)
    if tm.volume < 0:
        tm.invert()
    return tm


def r3(v):
    return [round(float(a), 3) for a in v]


class Frame:
    """model = Rot @ orig + t. orig is the generator's own frame (formulas, screen positions)."""

    def __init__(self, rot=None, t=None):
        self.R = np.eye(3) if rot is None else np.asarray(rot, float)
        self.t = np.zeros(3) if t is None else np.asarray(t, float)

    def p(self, v):
        return self.R @ np.asarray(v, float) + self.t

    def v(self, v):
        return self.R @ np.asarray(v, float)

    def shape(self, s):
        s = dict(s)
        if s["type"] == "box":
            a, b = self.p(s["min"]), self.p(s["max"])
            s["min"], s["max"] = r3(np.minimum(a, b)), r3(np.maximum(a, b))
        elif s["type"] in ("cyl", "capsule"):
            s["a"], s["b"] = r3(self.p(s["a"])), r3(self.p(s["b"]))
        elif s["type"] == "sphere":
            s["c"] = r3(self.p(s["c"]))
        return s

    def load(self, ld):
        return {"region": [self.shape(s) for s in ld["region"]], "force_N": r3(self.v(ld["force_N"]))}


def flip(H):
    """180 deg about X: orig z = 0 goes to model z = H (rotation, handedness kept)."""
    return Frame(np.diag([1.0, -1.0, -1.0]), [0.0, 0.0, H])


def ring_loads(n, r, z, th0, f_radial=None, f_tan=None, f_axial=None, f_vec=None, rs=2.0):
    """n loads at angles th0 + k 2 pi / n (orig frame), each on a sphere at radius r, height z."""
    out = []
    for k in range(n):
        th = th0 + k * 2 * math.pi / n
        c = [r * math.cos(th), r * math.sin(th), z]
        f = np.zeros(3)
        if f_radial:
            f += f_radial * np.array([math.cos(th), math.sin(th), 0.0])
        if f_tan:
            f += f_tan * np.array([-math.sin(th), math.cos(th), 0.0])
        if f_axial:
            f += np.array([0.0, 0.0, f_axial])
        if f_vec is not None:
            f += np.asarray(f_vec, float)
        out.append({"region": [{"type": "sphere", "c": c, "r": rs}], "force_N": f.tolist()})
    return out


# --------------------------------------------------------------------------- rotors (hub interior)
def wheel_common(cfg, H, R, skin, r_boss, r_open):
    """Hub interior deeper than `skin` below every functional surface, between the
    bore boss and the rim ring, opened through the back face (orig z = 0)."""

    def c_rem(ctx):
        r = np.sqrt(ctx.X ** 2 + ctx.Y ** 2)
        pad = (r < r_open + 1.0) & (ctx.Z < 0.3)
        depth = ndi.distance_transform_edt(ctx.occ | pad).astype(np.float32) * ctx.h
        c = np.minimum(depth - skin, r - r_boss)
        c = np.minimum(c, r_open - r)
        return np.minimum(c, ctx.Z + 0.0 * r).astype(np.float32)

    cfg.update(frame=flip(H), R=R, c_rem=c_rem, H=H, rotate_mesh=True,
               grid=lambda e: ([-R - 0.6, -R - 0.6, 0.0], [R + 0.6, R + 0.6, H + 0.6]),
               vox_box=([-R - 1.0, -R - 1.0, -1.0], [R + 1.0, R + 1.0, H + skin + 2.0]))
    cfg["design_note"] = (f"hub interior deeper than {skin} mm below the functional (wetted) surfaces, between the bore boss "
                          f"(r {r_boss:.2f} mm) and the rim ring (r {r_open:.2f} mm), open through the back face")
    cfg["design_mode"] = "slabs"
    return cfg


def all_spheres(loads):
    return [s for ld in loads for s in ld["region"]]


def blade_loads(blades, depth=0.75, rs=1.1, tdir=-1.0, torque=0.0):
    nbl = len(blades)
    cen, tor = [], []
    for kind, k, pts, f in blades:
        reg = [{"type": "sphere", "c": [r * math.cos(th), r * math.sin(th), z - depth], "r": rs} for r, z, th in pts]
        thm = float(np.mean([p[2] for p in pts]))
        rm = float(np.mean([p[0] for p in pts]))
        cen.append({"region": reg, "force_N": (f * np.array([math.cos(thm), math.sin(thm), 0.0])).tolist()})
        ft = torque / (nbl * rm / 1000.0)
        tor.append({"region": reg, "force_N": (tdir * ft * np.array([-math.sin(thm), math.cos(thm), 0.0])).tolist()})
    return cen, tor


def compressor(part_id, P):
    R2, r1h, H, tb = P["exducer_diameter_mm"] / 2, P["inducer_hub_diameter_mm"] / 2, P["total_height_mm"], P["backplate_thickness_mm"]
    zLe, rBore, n = P["leading_edge_z_mm"], P["bore_diameter_mm"] / 2, P["hub_profile_exponent"]
    wrap, sweep = math.radians(P["inducer_wrap_deg"]), math.radians(P["exit_backsweep_wrap_deg"])
    ah, bh = R2 - r1h, zLe - tb
    sc = screen(part_id)
    res = sc["results"]
    if "main_blade" in res:
        f_main, f_spl = res["main_blade"]["centrifugal_force_n"], res["splitter_blade"]["centrifugal_force_n"]
    else:
        f_main, f_spl = res["main_blade_centrifugal_force_n"], res["splitter_blade_centrifugal_force_n"]
    torque, rpm = res["screening_compressor_torque_nm"], res["derived_shaft_speed_rpm"]

    def zh(r):
        return zLe - bh * (1 - ((R2 - r) / ah) ** n) ** (1 / n)

    def camber(r, z):
        m = min(max(math.atan2(max(zLe - z, 0) / bh, max(R2 - r, 1e-4) / ah) / (math.pi / 2), 0), 1)
        return wrap * (1 - m) ** 2 - sweep * m * m

    blades = []
    for k in range(6):
        blades.append(("main", k, [(r, zh(r), camber(r, zh(r)) + k * math.pi / 3) for r in (11.0, 18.0, 25.0)], f_main))
        blades.append(("splitter", k, [(r, zh(r), camber(r, zh(r)) + math.pi / 6 + k * math.pi / 3) for r in (19.0, 26.0)], f_spl))
    cen, tor = blade_loads(blades, tdir=-1.0, torque=torque)
    op = sc["synthetic_operating_case"]
    p1, pr = op["inlet_absolute_pressure_pa"], op["pressure_ratio"]
    thrust = 0.5 * p1 * (pr - 1) * math.pi * ((R2 / 1000) ** 2 - (rBore / 1000) ** 2)
    skin, r_boss, r_open = 1.5, rBore + 2.5, R2 - 2.0
    cfg = wheel_common({}, H, R2, skin, r_boss, r_open)
    cfg["voids"] = [{"type": "cyl", "a": [0, 0, -1.0], "b": [0, 0, H + 1.0], "r": rBore, "basis": "assumption",
                     "note": f"through bore {2 * rBore:.1f} mm of the functional model (shaft not measured)"}]
    cfg["supports"] = [{"type": "cyl", "a": [0, 0, -1.0], "b": [0, 0, H + 1.0], "r": r_boss + 0.4, "basis": "assumption",
                        "note": "clamped on the shaft through the bore boss (nut clamp; fit not measured)"}]
    cfg["cases"] = [
        {"name": "centrifugal", "basis": "derived",
         "note": f"centrifugal force of each blade at the screen's derived {rpm:.0f} rpm (engineering-screen.json: main {f_main:.0f} N, splitter {f_spl:.0f} N), radial, on the skin under the blade root; the skin ring carries its own hoop load",
         "loads": cen},
        {"name": "torque", "basis": "derived",
         "note": f"screening compressor torque {torque:.2f} N m (engineering-screen.json) as tangential blade forces against the rotation (rotation assumed from the backsweep)",
         "loads": tor},
        {"name": "axial_thrust", "basis": "assumption",
         "note": f"0.5 x (p2 - p1) x back-face area = {thrust:.0f} N from the screen's synthetic {p1/1000:.0f} kPa inlet and pressure ratio {pr}, towards the inlet, on the skin under the blade roots",
         "loads": [{"region": all_spheres(cen), "force_N": [0.0, 0.0, thrust]}]},
    ]
    cfg["defaults"] = dict(element=0.7, volfrac=0.22, blend=0.2)
    return cfg


def turbine(part_id, P):
    R1, H, zb = P["inducer_diameter_mm"] / 2, P["total_height_mm"], P["backface_thickness_mm"]
    rShaft, rExh, zEx, n = P["shaft_diameter_mm"] / 2, P["exducer_hub_radius_mm"], P["exducer_plane_z_mm"], P["hub_profile_exponent"]
    wrap, nb, scal = math.radians(P["exducer_wrap_deg"]), int(P["blade_count"]), P["backface_scallop_depth_mm"]
    ah, bh = R1 - rExh, zEx - zb
    res = screen(part_id)["results"]
    f_bl, torque, rpm = res["blade"]["centrifugal_force_n"], res["shaft_torque_nm"], res["derived_shaft_speed_rpm"]

    def zh(r):
        return zEx - bh * (1 - ((R1 - r) / ah) ** n) ** (1 / n)

    def camber(r, z):
        m = min(max(math.atan2(max(R1 - r, 0) / ah, max(zEx - z, 1e-4) / bh) / (math.pi / 2), 0), 1)
        return wrap * m * m

    blades = [("blade", k, [(r, zh(r), camber(r, zh(r)) + k * 2 * math.pi / nb) for r in (11.0, 17.0, 23.0)], f_bl)
              for k in range(nb)]
    # same shaft as the compressor: its rotation is -z in this wheel's frame; the gas drives the blades with it
    cen, tor = blade_loads(blades, tdir=-1.0, torque=torque)
    p3 = res["turbine_inlet_pressure_pa_required"]
    thrust = 0.5 * (p3 - 101325.0) * math.pi * (R1 / 1000) ** 2
    skin, r_boss, r_open = 1.5, rShaft + 2.8, R1 - scal - 1.5
    cfg = wheel_common({}, H, R1 + 0.5, skin, r_boss, r_open)
    cfg["voids"] = []
    cfg["supports"] = [{"type": "cyl", "a": [0, 0, -1.0], "b": [0, 0, H + 1.0], "r": r_boss + 0.4, "basis": "assumption",
                        "note": f"fixed to the {2 * rShaft:.2f} mm shaft at the back-face hub (friction weld; joint not measured)"}]
    cfg["cases"] = [
        {"name": "centrifugal", "basis": "derived",
         "note": f"centrifugal force of each blade at the screen's derived {rpm:.0f} rpm (engineering-screen.json results.blade: {f_bl:.0f} N), radial, on the skin under the blade root; the skin ring carries its own hoop load",
         "loads": cen},
        {"name": "torque", "basis": "derived",
         "note": f"turbine shaft torque {torque:.2f} N m (engineering-screen.json) as tangential blade forces in the sense of rotation",
         "loads": tor},
        {"name": "axial_thrust", "basis": "assumption",
         "note": f"0.5 x (p3 - p_atm) x back-face area = {thrust:.0f} N from the screen's required {p3/1000:.0f} kPa turbine inlet pressure, towards the exducer, on the skin under the blade roots",
         "loads": [{"region": all_spheres(cen), "force_N": [0.0, 0.0, thrust]}]},
    ]
    cfg["defaults"] = dict(element=0.7, volfrac=0.22, blend=0.2)
    return cfg


# --------------------------------------------------------------------------- impeller (cup web)
def impeller(part_id, P):
    Ro, depth, rc, wall, web = P["outer_diameter_mm"] / 2, P["cup_depth_mm"], P["cup_diameter_mm"] / 2, P["cup_wall_mm"], P["web_thickness_mm"]
    rBore, nb, rbc, rbh, nBolt = P["bore_diameter_mm"] / 2, int(P["blade_count"]), P["bolt_circle_radius_mm"], P["bolt_hole_radius_mm"], int(P["bolt_count"])
    sc = screen(part_id)
    s = json.dumps(sc)
    rpm = 10000.0
    shaft_w = 9251.204914578426
    dp = 2154.753020753286
    blade_g = 6.326491970298041
    assert str(round(shaft_w, 3))[:7] in s and "single_blade_mass_g" in s
    w = rpm * 2 * math.pi / 60
    r_bl = (P["blade_hub_radius_mm"] + P["blade_tip_radius_mm"]) / 2
    f_bl = blade_g / 1000 * w * w * r_bl / 1000
    torque = shaft_w / w
    thrust = dp * math.pi * ((Ro / 1000) ** 2 - (rc / 1000) ** 2)
    zw = web + 1.0                                   # design plate: web + 1 mm into the cup
    rin = rc - wall

    def c_rem(ctx):
        r = np.sqrt(ctx.X ** 2 + ctx.Y ** 2)
        c = np.minimum(r - rBore, rin - r)
        c = np.minimum(c, np.minimum(ctx.Z + 0.6, zw - ctx.Z))
        return c.astype(np.float32)

    bolts = [(rbc * math.cos(-math.pi / nBolt + k * 2 * math.pi / nBolt), rbc * math.sin(-math.pi / nBolt + k * 2 * math.pi / nBolt))
             for k in range(nBolt)]
    cfg = dict(frame=flip(depth), R=rin, c_rem=c_rem, H=depth,
               grid=lambda e: ([-rin - 2.2, -rin - 2.2, -0.7], [rin + 2.2, rin + 2.2, zw + 2.6]), rotate_mesh=True,
               vox_box=([-Ro - 1.0, -Ro - 1.0, -2.0], [Ro + 1.0, Ro + 1.0, depth + 2.0]))
    cfg["design_note"] = (f"cup web plate r {rBore:.1f}..{rin:.1f} mm, {zw:.1f} mm thick (web {web} mm + 1 mm into the cup; "
                          "alternator clearance not measured); the windows of the functional web are not kept, the optimizer places the openings")
    cfg["design_shapes"] = [{"type": "cyl", "a": [0, 0, -0.6], "b": [0, 0, zw], "r": rin + 2.0, "basis": "assumption",
                             "note": cfg["design_note"] + "; the 2 mm of cup wall around it are included so the web can join the wall"}]
    cfg["solids"] = [{"type": "cyl", "a": [0, 0, -0.6], "b": [0, 0, web], "r": rBore + 3.5, "basis": "assumption",
                      "note": f"bore boss around the {2 * rBore:.0f} mm bore (functional bore)"}] + [
        {"type": "cyl", "a": [bx, by, -0.6], "b": [bx, by, web], "r": rbh + 3.0, "basis": "assumption",
         "note": f"bolt boss {k + 1} of {nBolt} on the {2 * rbc:.0f} mm bolt circle (functional model)"} for k, (bx, by) in enumerate(bolts)]
    cfg["voids"] = [{"type": "cyl", "a": [0, 0, -2.0], "b": [0, 0, zw + 1.0], "r": rBore, "basis": "assumption", "note": "bore (functional model)"}] + [
        {"type": "cyl", "a": [bx, by, -2.0], "b": [bx, by, zw + 1.0], "r": rbh, "basis": "assumption", "note": f"bolt hole {k + 1}"}
        for k, (bx, by) in enumerate(bolts)]
    cfg["supports"] = [{"type": "cyl", "a": [bx, by, -1.0], "b": [bx, by, web + 0.5], "r": rbh + 3.0, "basis": "assumption",
                        "note": f"bolt boss {k + 1} clamped to the drive hub (bolt pattern not measured)"} for k, (bx, by) in enumerate(bolts)]
    rr = rin + 1.0
    cfg["cases"] = [
        {"name": "centrifugal", "basis": "derived",
         "note": f"centrifugal force of each of the {nb} blades, {blade_g:.2f} g (engineering-screen.json mass.single_blade_mass_g) at r {r_bl:.0f} mm and the screen's nominal {rpm:.0f} rpm = {f_bl:.0f} N, radial, where the blade row meets the cup wall; the wall ring carries its own hoop load",
         "loads": ring_loads(nb, rr, 3.0, 0.0, f_radial=f_bl, rs=2.2)},
        {"name": "torque", "basis": "derived",
         "note": f"shaft power {shaft_w:.0f} W at {rpm:.0f} rpm (engineering-screen.json duty point) = {torque:.2f} N m, as tangential forces at the blade roots against the rotation (sense of rotation assumed)",
         "loads": ring_loads(nb, rr, 3.0, 0.0, f_tan=-torque / (nb * rr / 1000), rs=2.2)},
        {"name": "axial_thrust", "basis": "derived",
         "note": f"useful pressure {dp:.0f} Pa (engineering-screen.json) x blade annulus = {thrust:.0f} N, plus 10 g on the {sc['mass']['f1_mass_in_we43_g'] if 'mass' in sc else 421:.0f} g rotor (assumption), at the blade roots",
         "loads": ring_loads(nb, rr, 3.0, 0.0, f_axial=-(thrust + 0.421 * 10 * G) / nb, rs=2.2)},
    ]
    cfg["defaults"] = dict(element=1.4, volfrac=0.25, blend=0.4)
    return cfg


# --------------------------------------------------------------------------- stator (hub annulus)
def stator(part_id, P):
    L, rHub, tIn, rSeat, tSeat = P["ring_axial_length_mm"], P["hub_radius_mm"], P["inner_ring_thickness_mm"], P["inner_ring_bore_mm"] / 2, P["seat_sleeve_thickness_mm"]
    Ro, nv = P["outer_ring_outer_diameter_mm"] / 2, int(P["vane_count"])
    sc = screen(part_id)
    s = json.dumps(sc)
    torque, mass_g = 8.342210827187273, 614.1148851218762
    assert "swirl_reaction_torque_nm" in s and "8.3422108" in s and "614.11488" in s
    r_in, r_out = rSeat + tSeat, rHub - tIn

    def c_rem(ctx):
        r = np.sqrt(ctx.X ** 2 + ctx.Y ** 2)
        c = np.minimum(r - r_in, r_out - r)
        c = np.minimum(c, np.minimum(ctx.Z + 0.5, L - ctx.Z))
        return c.astype(np.float32)

    cfg = dict(frame=Frame(), R=r_out, c_rem=c_rem, H=L,
               grid=lambda e: ([-r_out - 1.5 * e, -r_out - 1.5 * e, -0.5], [r_out + 1.5 * e, r_out + 1.5 * e, L]),
               vox_box=([-Ro - 1.0, -Ro - 1.0, -2.0], [Ro + 1.0, Ro + 1.0, L + 2.0]))
    cfg["design_note"] = (f"whole hub annulus between the alternator seat sleeve (r {r_in:.1f} mm) and the vane-carrying inner sleeve "
                          f"(r {r_out:.1f} mm) over the {L:.0f} mm ring length; the functional flat web is not kept")
    cfg["design_shapes"] = [{"type": "cyl", "a": [0, 0, -0.5], "b": [0, 0, L], "r": r_out + 2.4, "basis": "assumption",
                             "note": cfg["design_note"] + "; the seat sleeve and 2.4 mm of the vane sleeve are included so the structure can join them"}]
    cfg["solids"] = []
    cfg["voids"] = [{"type": "cyl", "a": [0, 0, -2.0], "b": [0, 0, L + 2.0], "r": rSeat, "basis": "assumption",
                     "note": f"alternator seat bore {2 * rSeat:.0f} mm (functional model)"}]
    cfg["supports"] = [{"type": "cyl", "a": [0, 0, -1.0], "b": [0, 0, L + 1.0], "r": r_in + 0.4, "basis": "assumption",
                        "note": "seat sleeve held on the housing alternator seat (interface not measured)"}]
    rr = r_out + 1.2
    fg = mass_g / 1000 * 10 * G
    cfg["cases"] = [
        {"name": "swirl_torque", "basis": "derived",
         "note": f"swirl reaction torque {torque:.2f} N m (engineering-screen.json) as tangential forces at the {nv} vane roots",
         "loads": ring_loads(nv, rr, L / 2, 0.0, f_tan=torque / (nv * rr / 1000), rs=3.0)},
        {"name": "axial_10g", "basis": "assumption",
         "note": f"10 g axial on the {mass_g:.0f} g stator (cad_mass_g, engineering-screen.json) = {fg:.0f} N at the vane roots (vibration level assumed)",
         "loads": ring_loads(nv, rr, L / 2, 0.0, f_axial=fg / nv, rs=3.0)},
        {"name": "lateral_10g", "basis": "assumption",
         "note": f"10 g lateral on the same mass = {fg:.0f} N at the vane roots (vibration level assumed)",
         "loads": ring_loads(nv, rr, L / 2, 0.0, f_vec=[fg / nv, 0.0, 0.0], rs=3.0)},
    ]
    cfg["defaults"] = dict(element=2.4, volfrac=0.15, blend=0.4)
    return cfg


# --------------------------------------------------------------------------- fan housing (spoke disc)
def housing(part_id, P):
    Ro, D = P["outer_diameter_mm"] / 2, P["depth_mm"]
    rT, rHo, rHi, hD = P["throat_diameter_mm"] / 2, P["hub_outer_diameter_mm"] / 2, P["hub_bore_diameter_mm"] / 2, P["hub_depth_mm"]
    Rb, sT, lT, t = P["bellmouth_radius_mm"], P["spoke_thickness_mm"], P["throat_land_length_mm"], P["shell_thickness_mm"]
    sc = screen(part_id)
    radial = 2000.0
    assert '"radial_load_n": 2000.0' in json.dumps(sc, indent=2) or "2000.0" in json.dumps(sc)
    zS = Rb + sT / 2 + 2
    hz0 = zS - hD / 2
    z0, z1 = hz0 - 2.0, lT - 2.0                    # generator frame: z from the inlet face

    def c_rem(ctx):
        r = np.sqrt(ctx.X ** 2 + ctx.Y ** 2)
        c = np.minimum(r - rHo, rT - r)
        c = np.minimum(c, np.minimum(ctx.Z - z0, z1 - ctx.Z))
        return c.astype(np.float32)

    # model z = D - generator z (the generator flips its own frame inlet-up)
    fr = Frame(np.diag([1.0, 1.0, -1.0]), [0.0, 0.0, D])
    cfg = dict(frame=fr, R=rT, c_rem=c_rem, H=D,
               grid=lambda e: ([-rT - 1.5 * e, -rT - 1.5 * e, z0 - 1.5 * e], [rT + 1.5 * e, rT + 1.5 * e, z1 + 1.5 * e]),
               vox_box=([-Ro - 1.0, -Ro - 1.0, -1.5], [Ro + 1.0, Ro + 1.0, D + 1.5]))
    cfg["design_note"] = (f"spoke disc inside the throat: r {rHo:.0f}..{rT:.0f} mm (hub to throat sleeve), {z1 - z0:.0f} mm deep behind the bellmouth; "
                          "the six functional spokes are not kept")
    cfg["design_shapes"] = [
        {"type": "cyl", "a": [0, 0, z0], "b": [0, 0, z1], "r": rT, "basis": "assumption",
         "note": cfg["design_note"] + "; hub annulus included so the structure can join it"},
        {"type": "cyl", "a": [0, 0, Rb + 0.5], "b": [0, 0, z1], "r": rT + t / 2, "basis": "assumption",
         "note": "half the throat sleeve wall, behind the bellmouth, so the structure can join it"}]
    cfg["solids"] = []
    cfg["voids"] = [{"type": "cyl", "a": [0, 0, z0 - 1.0], "b": [0, 0, z1 + 1.0], "r": rHi, "basis": "assumption",
                     "note": f"alternator seat bore {2 * rHi:.0f} mm (functional model)"}]
    ns = 72
    rs = rT + t / 2
    cfg["supports"] = [{"type": "cyl", "a": [rs * math.cos(k * 2 * math.pi / ns), rs * math.sin(k * 2 * math.pi / ns), z0 - 1.0],
                        "b": [rs * math.cos(k * 2 * math.pi / ns), rs * math.sin(k * 2 * math.pi / ns), z1 + 1.0], "r": 2.6,
                        "basis": "assumption", "note": "throat sleeve, carried by the shell and the mount flange (taken as rigid)"}
                       for k in range(ns)]
    hub = [{"type": "cyl", "a": [0, 0, hz0], "b": [0, 0, hz0 + hD], "r": rHo + 0.5}]
    cfg["cases"] = [
        {"name": "radial_vertical", "basis": "derived",
         "note": f"radial hub load {radial:.0f} N of the engineering screen (synthetic regression input: alternator, belt and fan), vertical assumed along -Y",
         "loads": [{"region": hub, "force_N": [0.0, -radial, 0.0]}]},
        {"name": "radial_lateral", "basis": "assumption",
         "note": f"the same {radial:.0f} N along X (belt direction not measured)",
         "loads": [{"region": hub, "force_N": [radial, 0.0, 0.0]}]},
        {"name": "axial", "basis": "assumption",
         "note": f"axial hub load 0.25 x {radial:.0f} N (fan thrust and fore-aft inertia; not published)",
         "loads": [{"region": hub, "force_N": [0.0, 0.0, 0.25 * radial]}]},
    ]
    cfg["defaults"] = dict(element=3.0, volfrac=0.15, blend=1.0)
    return cfg


# --------------------------------------------------------------------------- K16 pair (actuator bracket)
def _box2(x, y, x0, x1, y0, y1, rr):
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    rr = min(rr, min(hx, hy) * 0.999)
    qx, qy = np.abs(x - (x0 + x1) / 2) - (hx - rr), np.abs(y - (y0 + y1) / 2) - (hy - rr)
    return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - rr


def _revx(X, rho, x0, x1, r, rr):
    return _box2(X, rho, x0, x1, -r, r, rr)


def _scroll(X, Y, Z, xs, psi0, sgn, rc0, rc1, a0, a1):
    rho = np.sqrt(Y ** 2 + Z ** 2)
    phi = sgn * (np.arctan2(Z, Y) - psi0)
    phi = phi - 2 * np.pi * np.floor(phi / (2 * np.pi))
    t = phi / (2 * np.pi)
    return np.sqrt((rho - (rc0 + (rc1 - rc0) * t)) ** 2 + (X - xs) ** 2) - (a0 + (a1 - a0) * t)


def _capsule(X, Y, Z, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1] + (Z - a[2]) * ab[2]) / (ab @ ab), 0, 1)
    return np.sqrt((X - a[0] - t * ab[0]) ** 2 + (Y - a[1] - t * ab[1]) ** 2 + (Z - a[2] - t * ab[2]) ** 2) - r


def pair(part_id, P):
    L, W, H, half, wall = P["unit_length_mm"], P["unit_width_mm"], P["unit_height_mm"], P["pair_spacing_mm"] / 2, P["wall_mm"]
    rTs, rOut = P["turbine_volute_outer_radius_mm"], P["turbine_outlet_bore_diameter_mm"] / 2
    zTop = H - W / 2
    xt, a1t, a0t, rc0t = 212.0, 27.0, 9.0, 45.0
    rc1t = rTs - a1t
    bx0, bx1, by, bz0, bz1 = 194.0, 264.0, 32.0, 36.0, zTop - 23.0

    def envelope(c):                                   # turbine housing outer solids incl. their gas paths (> 0 outside)
        rho = np.sqrt(c.Y ** 2 + c.Z ** 2)
        e = _revx(c.X, rho, 182.5, 242.0, 50.0, 4.0)
        e = np.minimum(e, _scroll(c.X, c.Y, c.Z, xt, 0.0, 1.0, rc1t, rc0t, a1t, a0t))
        return np.minimum(e, _revx(c.X, rho, 238.0, 270.0, rOut + wall + 6.0, 2.0))

    def c_rem(c):                                      # the functional strut between the wastegate boss and the can
        d = np.sqrt((c.X - 229.0) ** 2 + c.Y ** 2)
        r = np.minimum(np.minimum(7.6 - d, c.Z - 67.0), (zTop - 27.5) - c.Z)
        return np.minimum(r, envelope(c)).astype(np.float32)

    def c_des(c):
        box = np.minimum(np.minimum(c.X - bx0, bx1 - c.X), np.minimum(by - np.abs(c.Y), np.minimum(c.Z - bz0, bz1 - c.Z)))
        clear = np.minimum(_capsule(c.X, c.Y, c.Z, (250.0, 0, zTop - 27.0), (250.0, 0, 62.0), 7.5),
                           _capsule(c.X, c.Y, c.Z, (250.0, 0, 62.0), (226.0, 0, 62.0), 7.5))
        return np.minimum(np.minimum(box, envelope(c)), clear).astype(np.float32)

    maps = [lambda u: u + L / 2, lambda u: np.abs(u) - half, lambda u: u]
    cfg = dict(frame=Frame(), R=None, c_rem=c_rem, c_des=c_des, H=H, axis_maps=maps, design_mode="boxes",
               grid=lambda e: ([bx0 - L / 2 - 1.5 * e, -half - by - 1.5 * e, bz0 - 1.5 * e], [bx1 - L / 2 + 1.5 * e, half + by + 1.5 * e, bz1 + 1.5 * e]),
               vox_box=([-L / 2 - 1, -half - W / 2 - 30, -W / 2 - 2], [L / 2 + 1, half + W / 2 + 30, zTop + 2]))
    cfg["masks"] = {"support": lambda c: (zTop - 31.0) - c.Z, "load": lambda c: c.Z - (zTop - 29.0)}
    cfg["design_note"] = ("per unit, the space between the turbine housing (volute, core, outlet; their gas paths excluded) and the wastegate "
                          f"actuator can, x {bx0 - L / 2:.0f}..{bx1 - L / 2:.0f} mm, |y| {half - by:.0f}..{half + by:.0f} mm, z {bz0:.0f}..{bz1:.0f} mm, "
                          "with 7.5 mm clearance around the actuator rod and lever; the functional strut is not kept")
    cfg["solids"], cfg["voids"] = [], []
    cfg["supports"] = [{"type": "@support", "basis": "assumption",
                        "note": "turbine housing surface next to the design region (volute, core, outlet, wastegate boss), taken as rigid"}]
    m_act, acc, boost, d_diaph = 0.6, 30.0, 80_000.0, 0.050
    f_d = boost * math.pi * d_diaph ** 2 / 4
    f_i = m_act * acc * G
    ld = [{"type": "@load"}]
    cfg["cases"] = [
        {"name": "diaphragm", "basis": "assumption",
         "note": f"actuator diaphragm reaction {f_d:.0f} N per unit: 0.8 bar boost (assumed) on a {d_diaph * 1000:.0f} mm effective diaphragm, pushing the can away from the lever",
         "loads": [{"region": ld, "force_N": [0.0, 0.0, 2 * f_d]}]},
        {"name": "vertical_30g", "basis": "assumption",
         "note": f"{acc:.0f} g turbo-mounted vibration on a {m_act} kg actuator (mass and level assumed) = {f_i:.0f} N per unit",
         "loads": [{"region": ld, "force_N": [0.0, 0.0, -2 * f_i]}]},
        {"name": "lateral_30g", "basis": "assumption", "note": f"the same {f_i:.0f} N per unit along Y",
         "loads": [{"region": ld, "force_N": [0.0, 2 * f_i, 0.0]}]},
        {"name": "fore_aft_30g", "basis": "assumption", "note": f"the same {f_i:.0f} N per unit along X",
         "loads": [{"region": ld, "force_N": [2 * f_i, 0.0, 0.0]}]},
    ]
    cfg["defaults"] = dict(element=2.2, volfrac=0.18, blend=1.2)
    return cfg


CONFIG = {
    "993-ENG-K16-COMPRESSOR-WHEEL-ALSI10MG-F0-0001": compressor,
    "993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001": compressor,
    "993-ENG-K16-TURBINE-WHEEL-IN718-F0-0001": turbine,
    "993-ENG-COOLING-IMPELLER-WE43-F1-0001": impeller,
    "993-ENG-FAN-STATOR-ALSI10MG-F1-0001": stator,
    "993-ENG-FAN-HOUSING-ALSI10MG-F0-0001": housing,
    "993-TURBOCHARGER-K16-PAIR-0001": pair,
}


class Ctx:
    pass


def merged_boxes(mask):
    """Greedy cuboid cover of a boolean grid: runs in x, merged over y, then over z. Returns (i0, i1, j0, j1, k0, k1)."""
    nx, ny, nz = mask.shape
    out, active = [], {}
    for k in range(nz):
        rects, open_r = set(), {}
        for j in range(ny + 1):
            runs = set()
            if j < ny:
                d = np.diff(np.concatenate([[0], mask[:, j, k].astype(np.int8), [0]]))
                runs = set(zip(np.flatnonzero(d == 1).tolist(), (np.flatnonzero(d == -1) - 1).tolist()))
            for r in list(open_r):
                if r not in runs:
                    rects.add((r[0], r[1], open_r.pop(r), j - 1))
            for r in runs:
                open_r.setdefault(r, j)
        new = {rc: active.pop(rc, k) for rc in rects}
        out += [rc + (z0, k - 1) for rc, z0 in active.items()]
        active = new
    out += [rc + (z0, nz - 1) for rc, z0 in active.items()]
    return out


def main(part_id, element=None, volfrac=None, iters=45, smooth=None, blend=None):
    spec, P = params(part_id)
    cfg = CONFIG[part_id](part_id, P)
    element = element or cfg["defaults"]["element"]
    volfrac = volfrac or cfg["defaults"]["volfrac"]
    fr = cfg["frame"]
    voxel = float(spec["voxel_mm"])
    h = 0.75 * voxel
    e = element
    base_rel = f"{REL}/{part_id}-base.stl"
    t0 = time.time()
    mesh = trimesh.load_mesh(CATALOG / "out" / f"{part_id}-functional.stl", process=False)
    V, F = np.asarray(mesh.vertices, float), np.asarray(mesh.faces)
    if cfg.get("rotate_mesh"):            # the functional model is in the generator frame
        V = V @ fr.R.T + fr.t
    a, b = fr.p(cfg["vox_box"][0]), fr.p(cfg["vox_box"][1])
    lo = np.minimum(np.minimum(a, b), V.min(0) - 1.0)
    hi = np.maximum(np.maximum(a, b), V.max(0) + 1.0)
    shape = tuple(int(x) for x in np.ceil((hi - lo) / h))
    occ = occupancy(V, F, lo, h, shape)
    print(f"occupancy {shape} h {h:.3f}: {occ.sum() * h ** 3 / 1000:.2f} cm3 in {time.time() - t0:.0f} s", flush=True)
    ax = [lo[d] + (np.arange(shape[d]) + 0.5) * h for d in range(3)]
    Rd = np.diag(fr.R)
    assert np.allclose(fr.R, np.diag(Rd)), "diagonal frames only"
    maps = cfg.get("axis_maps") or [lambda u, d=d: (u - fr.t[d]) / Rd[d] for d in range(3)]
    ctx = Ctx()
    ctx.h, ctx.occ = h, occ
    ctx.X = maps[0](ax[0])[:, None, None].astype(np.float32)
    ctx.Y = maps[1](ax[1])[None, :, None].astype(np.float32)
    ctx.Z = maps[2](ax[2])[None, None, :].astype(np.float32)
    c_rem = cfg["c_rem"](ctx)
    c_des = cfg["c_des"](ctx) if "c_des" in cfg else c_rem
    occ_s = ndi.gaussian_filter(occ.astype(np.float32), 0.6) - 0.5
    del occ, ctx.occ
    k = 0.66 / h
    OUT.mkdir(parents=True, exist_ok=True)
    base = contour(np.minimum(occ_s, -c_rem * k), lo, h)
    base.export(ROOT / base_rel)
    removed_cm3 = float(((occ_s > 0) & (c_rem > 0)).sum()) * h ** 3 / 1000
    print(f"base: {len(base.faces)} tris, watertight {base.is_watertight}, {len(base.split(only_watertight=False))} bodies, "
          f"volume {base.volume / 1000:.2f} cm3; removed {removed_cm3:.2f} cm3", flush=True)

    # topopt grid (model frame) and the masks at its element centres
    gmin, gmax = cfg["grid"](e)
    ga, gb = fr.p(gmin), fr.p(gmax)
    g0, g1 = np.minimum(ga, gb), np.maximum(ga, gb)
    nel = np.maximum(np.ceil((g1 - g0) / e).astype(int), 1)
    idx = [np.clip(np.round((g0[d] + (np.arange(nel[d]) + 0.5) * e - lo[d]) / h - 0.5).astype(int), 0, shape[d] - 1) for d in range(3)]
    ov = (1.0 if cfg.get("design_mode") == "slabs" else 1.5) * e
    if cfg.get("design_mode") == "slabs":           # c_des is a depth, not a distance to D: measure it
        near = ndi.distance_transform_edt(c_des <= 0) * h < ov
    else:
        near = c_des > -ov
    band = (occ_s > 0) & (c_rem <= 0) & near
    del near
    mask_all = (c_des > 0) | band

    def at(m):
        return m[np.ix_(*idx)]

    regions = {}
    mode = cfg.get("design_mode", "explicit")
    if mode == "slabs":
        me = at(mask_all)
        cx = g0[0] + (np.arange(nel[0]) + 0.5) * e
        cy = g0[1] + (np.arange(nel[1]) + 0.5) * e
        rr = np.sqrt(cx[:, None] ** 2 + cy[None, :] ** 2)
        design = []
        for kz in range(nel[2]):
            if not me[:, :, kz].any():
                continue
            rmax = float(rr[me[:, :, kz]].max()) + 0.3 * e
            z0 = g0[2] + kz * e
            design.append({"type": "cyl", "a": r3([0, 0, z0 - 0.01]), "b": r3([0, 0, z0 + e + 0.01]), "r": round(rmax, 3)})
        design[0]["basis"], design[0]["note"] = "assumption", cfg["design_note"] + f"; written as {len(design)} axial slabs that enclose it and the one-element skin band next to it (the skin itself stays in shaping.base_stl)"
    elif mode == "boxes":
        me = at(mask_all)
        bx = merged_boxes(me)
        design = [{"type": "box", "min": r3(g0 + (np.array([i0, j0, k0]) + 0.5) * e - 0.3 * e),
                   "max": r3(g0 + (np.array([i1, j1, k1]) + 0.5) * e + 0.3 * e)} for i0, i1, j0, j1, k0, k1 in bx]
        design[0]["basis"], design[0]["note"] = "assumption", cfg["design_note"] + f"; written as {len(design)} boxes (element-exact cover of it and the 1.5-element skin band next to it)"
        for name, fn in cfg.get("masks", {}).items():
            mm = at(band & (fn(ctx) > 0))
            regions[name] = [{"type": "box", "min": r3(g0 + np.array([i0, j0, k0]) * e - 0.01),
                              "max": r3(g0 + (np.array([i1, j1, k1]) + 1) * e + 0.01)} for i0, i1, j0, j1, k0, k1 in merged_boxes(mm)]
            print(f"region {name}: {int(mm.sum())} elements, {len(regions[name])} boxes")
    else:
        design = [fr.shape(s) for s in cfg["design_shapes"]]
    n_mask = int(at(mask_all).sum())
    print(f"grid {nel.tolist()}, design+band elements (mask) {n_mask}, design shapes {len(design)}", flush=True)

    def sh(s):
        if s.get("type", "").startswith("@"):
            return [dict(r, basis=s.get("basis", "assumption"), note=s.get("note", "")) if i == 0 and "note" in s else r
                    for i, r in enumerate(regions[s["type"][1:]])]
        return [fr.shape(s)]

    def shl(lst):
        return [x for s in lst for x in sh(s)]

    opt = {
        "element_mm": e,
        "grid_min": r3(g0),
        "grid_max": r3(g0 + nel * e),
        "design": design,
        "solid": shl(cfg.get("solids", [])),
        "void": shl(cfg.get("voids", [])),
        "supports": shl(cfg["supports"]),
        "load_cases": [{"name": c["name"], "basis": c["basis"], "note": c["note"],
                        "loads": [{"region": shl(ld["region"]), "force_N": r3(fr.v(ld["force_N"]))} for ld in c["loads"]]}
                       for c in cfg["cases"]],
        "volume_fraction": volfrac,
        "filter_radius_mm": round(2.5 * e, 2),
        "iterations": int(iters),
    }
    smooth = smooth or round(1.2 * e, 2)
    flipped = bool(np.allclose(np.diag(fr.R), [1, -1, -1]))
    frame_note = (" Model frame: the rotor is turned 180 deg about X (back face up) so the optimized structure faces the catalogue view; "
                  "blade handedness is kept.") if flipped else ""
    bio = {
        "part_id": part_id,
        "method": ("3D SIMP topology optimization (parts/picogk-catalog/bionic/topopt.py) of the structure behind the exact functional "
                   "surfaces, prepared by parts/picogk-catalog/bionic/prep_rotating.py; PicoGK smoothing, exact functional body fused"),
        "basis_note": ("Blades, vanes, wetted surfaces, rings and interfaces are the previous functional model, kept exactly (shaping.base_stl, "
                       "regenerated by prep_rotating.py from out/<PART_ID>-functional.stl). Only the structural region described in "
                       f"optimization.design is re-grown ({removed_cm3:.1f} cm3 of the functional body removed there), for loads derived from the "
                       "part's own engineering screen (synthetic operating points, not measured) and stated assumptions. A load-path concept, "
                       "not a stress, burst or fatigue result." + frame_note),
        "optimization": opt,
        "shaping": {"smooth_mm": smooth, "blend_mm": blend or cfg["defaults"].get("blend") or round(0.5 * smooth, 2), "base_stl": base_rel, "lattice_grey": False},
    }
    path = ROOT / "parts" / part_id.lower() / "source" / "bionic.json"
    path.write_text(json.dumps(bio, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(ROOT)}; element {e}, volfrac {volfrac}, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    kw = {}
    for x in a[1:]:
        k, v = x.split("=")
        kw[k] = int(v) if k == "iters" else float(v)
    main(a[0], **kw)
