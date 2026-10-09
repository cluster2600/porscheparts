"""Inputs for the PicoGK monocoque study, from the plate 50-05a shell.

Reuses ../source/build_shell.py (stations, sections, closed surface) so the
PicoGK model sits exactly on the outline already traced from Porsche's
drawing. Writes to ./input/ (regenerable, not committed):

- body-closed.stl      closed body volume: the 420 station sections, end caps
- skin-surface.stl     the structural shell with its openings (from the .npz)
- geometry.json        member paths and panel extents, in the vehicle frame
                       (x forward = -d, y left, z up, mm)

Every path is computed on the modelled surface; the parameters that place
them (insets, heights, which station) are in ../picogk-rings/params/*.json and carry
their basis. Nothing here is measured on a car.

    python prepare.py params/monocoque-f0.json
"""
import importlib.util
import json
import pathlib
import struct
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MONO = HERE.parent
spec = importlib.util.spec_from_file_location("build_shell", MONO / "source" / "build_shell.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)


def write_stl(path, vertices, faces):
    with open(path, "wb") as f:
        f.write(b"picogk-monocoque-input".ljust(80, b" "))
        f.write(struct.pack("<I", len(faces)))
        for a, b, c in faces:
            p0, p1, p2 = vertices[a], vertices[b], vertices[c]
            n = np.cross(p1 - p0, p2 - p0)
            n = n / (np.linalg.norm(n) or 1.0)
            f.write(struct.pack("<12fH", *n, *p0, *p1, *p2, 0))


def closed_body(d, zt, zb, w, zbelt):
    rings, v, f = bs.surface(d, zt, zb, w, zbelt)
    nr = len(rings[0])
    v = list(v)
    faces = [tuple(t) for t in f]
    for i, flip in ((0, True), (len(d) - 1, False)):          # fan caps at both ends
        ring = np.array([[-d[i], y, z] for y, z in rings[i]])
        c = len(v)
        v.append(ring.mean(axis=0))
        base = i * nr
        for j in range(nr):
            a, b = base + j, base + (j + 1) % nr
            faces.append((c, b, a) if flip else (c, a, b))
    v, faces = np.array(v, dtype=np.float64), np.array(faces)
    # Orient outward: the station rings run clockwise in this frame.
    signed = np.einsum("ij,ij->i", v[faces[:, 0]], np.cross(v[faces[:, 1]], v[faces[:, 2]])).sum() / 6.0
    return v, (faces[:, ::-1] if signed < 0 else faces)


def surface_y(i, rings, z, side=1):
    """|y| of the section at station i, at height z (outer surface)."""
    r = rings[i]
    half = r[r[:, 0] >= 0]
    o = np.argsort(half[:, 1])
    return float(np.interp(z, half[o, 1], half[o, 0]))


def main(params_path, out=None):
    params = json.loads(pathlib.Path(params_path).read_text(encoding="utf-8"))
    P = {k: v["value"] for k, v in params["parameters"].items()}
    profiles = json.loads((MONO / "data" / "profiles-50-05a.json").read_text(encoding="utf-8"))
    d, zt, zb, w, zbelt = bs.stations(profiles)
    rings = [bs.section(w[i], zbelt[i], zt[i], zb[i], d[i]) for i in range(len(d))]
    out = pathlib.Path(out) if out else HERE / "input"
    out.mkdir(parents=True, exist_ok=True)

    v, f = closed_body(d, zt, zb, w, zbelt)
    write_stl(out / "body-closed.stl", v, f)
    npz = np.load(MONO / "derived" / "monocoque-shell-structural.npz")
    write_stl(out / "skin-surface.stl", npz["points"].astype(np.float64), npz["triangles"])

    def at(dd):
        return int(np.argmin(np.abs(d - dd)))

    def inward(i, z, inset):
        return surface_y(i, rings, z) - inset

    door = np.array(profiles["openings"]["door_aperture"])
    sill_top = float(door[:, 1].min())                          # door aperture bottom (plate)
    a_d, b_d = float(door[:, 0].min()), float(door[:, 0].max())  # A and B door edges (plate)
    fb, rb = P["front_bulkhead_d_mm"], P["rear_bulkhead_d_mm"]
    ws0, ws1 = P["windscreen_base_d_mm"], P["windscreen_header_d_mm"]
    rw0, rw1 = P["rear_window_header_d_mm"], P["rear_window_base_d_mm"]
    # Each tube sits tangent to the skin from inside (inset = outer radius), so
    # the closed section is bonded to the skin instead of floating behind it.
    group_od = {"front_ring": "front_ring_od_mm", "b_ring": "b_ring_od_mm", "rear_ring": "rear_ring_od_mm",
                "roof_rails": "roof_rail_od_mm", "arches": "arch_od_mm"}
    ins = P["front_ring_od_mm"] / 2.0

    def pt(dd, z, side, inset=None, group="front_ring"):
        inset = P[group_od[group]] / 2.0 if inset is None else inset
        i = at(dd)
        return [-float(d[i]), side * inward(i, z, inset), float(z)]

    def roof_z(dd, drop):
        return float(zt[at(dd)] - drop)

    paths = {}
    for side, tag in ((1, "L"), (-1, "R")):
        # A-pillar: from the sill at the door's front edge, up the windscreen edge, to the header.
        a_path = [pt(a_d, sill_top, side)]
        for t in np.linspace(0, 1, 9):
            dd = ws0 + (ws1 - ws0) * t
            z = float(zbelt[at(dd)] + (roof_z(dd, P["roof_rail_drop_mm"]) - zbelt[at(dd)]) * t)
            a_path.append(pt(dd, z, side))
        paths[f"a_pillar_{tag}"] = {"points": a_path, "group": "front_ring"}
        # Roof rail: header to rear-window header along the roof edge.
        paths[f"roof_rail_{tag}"] = {"points": [pt(dd, roof_z(dd, P["roof_rail_drop_mm"]), side, group="roof_rails")
                                                for dd in np.linspace(ws1, rw0, 12)], "group": "roof_rails"}
        # B-hoop side: sill at the door's rear edge up to the roof rail.
        paths[f"b_pillar_{tag}"] = {"points": [pt(b_d, z, side, group="b_ring") for z in
                                               np.linspace(sill_top, roof_z(b_d, P["roof_rail_drop_mm"]), 8)],
                                    "group": "b_ring"}
        # C-pillar: rear-window header down to its base, then to the rear bulkhead top.
        c_path = []
        for t in np.linspace(0, 1, 8):
            dd = rw0 + (rw1 - rw0) * t
            z = roof_z(dd, P["roof_rail_drop_mm"]) + (float(zbelt[at(dd)]) - roof_z(dd, P["roof_rail_drop_mm"])) * t
            c_path.append(pt(dd, z, side, group="rear_ring"))
        c_path.append(pt(rb, float(zbelt[at(rb)]) - 40.0, side, group="rear_ring"))
        paths[f"c_pillar_{tag}"] = {"points": c_path, "group": "rear_ring"}
        # Wheel-arch rings (structural extension of the side rail at the ends).
        for name, dc, rad in (("front_arch", bs.FRONT_AXLE_D, P["front_arch_radius_mm"]),
                              ("rear_arch", bs.REAR_AXLE_D, P["rear_arch_radius_mm"])):
            arc = []
            for th in np.radians(np.linspace(-10, 190, 15)):
                dd, z = dc + rad * np.cos(th), 300.0 + rad * np.sin(th)
                i = at(dd)
                arc.append([-float(dd), side * (surface_y(i, rings, min(max(z, zb[i] + 30), zbelt[i])) - P["arch_od_mm"] / 2.0), float(z)])
            paths[f"{name}_{tag}"] = {"points": arc, "group": "arches"}
    # Cross members closing the rings at the top.
    hdr_y = inward(at(ws1), roof_z(ws1, P["roof_rail_drop_mm"]), ins)
    paths["windscreen_header"] = {"points": [[-ws1, -hdr_y, roof_z(ws1, P["roof_rail_drop_mm"])],
                                             [-ws1, hdr_y, roof_z(ws1, P["roof_rail_drop_mm"])]], "group": "front_ring"}
    cowl_z = float(zbelt[at(ws0)])
    cowl_y = inward(at(ws0), cowl_z, ins)
    paths["windscreen_cowl"] = {"points": [[-ws0, -cowl_y, cowl_z], [-ws0, cowl_y, cowl_z]], "group": "front_ring"}
    by = inward(at(b_d), roof_z(b_d, P["roof_rail_drop_mm"]), P["b_ring_od_mm"] / 2.0)
    paths["b_hoop_roof"] = {"points": [[-b_d, -by, roof_z(b_d, P["roof_rail_drop_mm"])],
                                       [-b_d, by, roof_z(b_d, P["roof_rail_drop_mm"])]], "group": "b_ring"}
    ry = inward(at(rw0), roof_z(rw0, P["roof_rail_drop_mm"]), P["rear_ring_od_mm"] / 2.0)
    paths["rear_window_header"] = {"points": [[-rw0, -ry, roof_z(rw0, P["roof_rail_drop_mm"])],
                                              [-rw0, ry, roof_z(rw0, P["roof_rail_drop_mm"])]], "group": "rear_ring"}

    floor_z = float(np.median(zb[(d > fb) & (d < rb)]))
    geometry = {
        "frame": "vehicle: x forward = -d (plate 0 line), y left, z up; mm",
        "source": "twins/964-chassis/monocoque/source/build_shell.py + data/profiles-50-05a.json",
        "stations": {"x": (-d).tolist(), "top": zt.tolist(), "bottom": zb.tolist(),
                     "half_width": w.tolist(), "belt": zbelt.tolist()},
        "door_aperture": {"front_d": a_d, "rear_d": b_d, "sill_top_z": sill_top},
        "floor_z_mm": floor_z,
        "front_bulkhead_x": -fb, "rear_bulkhead_x": -rb,
        "front_bulkhead_top_z": P["front_bulkhead_top_z_mm"], "rear_bulkhead_top_z": float(zbelt[at(rb)]),
        "half_width_at": {"front_bulkhead": float(w[at(fb)]), "rear_bulkhead": float(w[at(rb)]),
                          "door_mid": float(w[at((a_d + b_d) / 2)])},
        "paths": paths,
    }
    (out / "geometry.json").write_text(json.dumps(geometry, indent=1) + "\n", encoding="utf-8")
    print(f"body-closed.stl {len(f)} tris; skin-surface.stl {len(npz['triangles'])} tris; "
          f"{len(paths)} member paths; floor z {floor_z:.0f} mm; sill top z {sill_top:.0f} mm; "
          f"door edges d {a_d:.0f}..{b_d:.0f} mm")
    return geometry


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "params" / "monocoque-f0.json")
