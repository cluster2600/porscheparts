"""AM study, part 1: LPBF orientation screen of the twin body (geometry only).

For six axis-aligned candidate build orientations of the closed twin body this
measures, on the winding-number occupancy grid:

- the build height;
- the down-facing overhang area whose surface lies below 45 degrees from the
  plate, and the support volume as the air column under it (voxel column
  method), split by where the column lands (plate or part);
- the enclosed-void volume (trapped powder) by flood fill of the air from the
  grid boundary. This does not depend on the orientation.

Method. The 0.25 mm grid is thresholded (inside = w > 0.5) and screened at
that pitch; a block-averaged 0.5 mm grid is the sensitivity. In every column
along the build direction each solid-over-air transition is one down-facing
surface element of projected area pitch^2. Its outward normal comes from the
gradient of the solid fraction smoothed by a 0.5 mm Gaussian; it is an
overhang when the normal is within 45 degrees of straight down. Its support
column runs down to the next solid voxel or to the plate (the lowest solid
level). The overhang area is re-measured independently on the triangles of
the closed surfaces.

The method is first run on analytic witnesses whose answers are computed by
hand below; the measured errors are written to the output. The pitch and the
smoothing were chosen on those witnesses (at 0.5 mm the 45 degree limit of a
7 mm wide cap is quantised to 6%), not on the head.

This is a geometric screen of a study twin. It designs no supports, selects no
orientation, and says nothing about printability, material or function.

Usage: am_supports.py PRIVATE_DIR PARAMS_DIR
Output: PARAMS_DIR/am-supports.json (scalars only)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

OVERHANG_ANGLE_DEG = 45.0
WORKING_PITCH_MM = 0.25
SENSITIVITY_PITCH_MM = 0.5
NORMAL_SMOOTHING_MM = 0.5
NEAR_PLATE_MM = 1.0
PLATE_TOLERANCE_MM = 0.5
VOID_PROBE_PITCH_MM = 0.5
TILE_PLANES = 64
PROBE_BALL_DIAMETER_MM = 2.0
WITNESS_TOLERANCE = 0.05

# name: (axis of the twin frame, sign of the build-up direction)
ORIENTATIONS = {
    "deck_down": (2, +1),
    "deck_up": (2, -1),
    "flange_y_minus_down": (1, +1),
    "flange_y_plus_down": (1, -1),
    "side_x_minus_down": (0, +1),
    "side_x_plus_down": (0, -1),
}
ORIENTATION_NOTES = {
    "deck_down": "build direction +Z (bore axis); the combustion-deck side faces the plate, cam side up",
    "deck_up": "build direction -Z; the cam-housing side faces the plate",
    "flange_y_minus_down": "build direction +Y; the flange at y = -104.26 mm faces the plate",
    "flange_y_plus_down": "build direction -Y; the flange at y = +85.39 mm faces the plate",
    "side_x_minus_down": "build direction +X; the -X side faces the plate",
    "side_x_plus_down": "build direction -X; the +X side faces the plate",
}


def orient(a: np.ndarray, axis: int, sign: int) -> np.ndarray:
    """View of `a` with the build-up direction as the last, increasing axis."""

    b = np.moveaxis(a, axis, 2)
    return b if sign > 0 else b[:, :, ::-1]


def block_mean(inside: np.ndarray, k: int) -> np.ndarray:
    """Solid fraction of k^3 blocks of a boolean grid (zero-padded to fit)."""

    pad = [(0, (-s) % k) for s in inside.shape]
    a = np.pad(inside, pad) if any(p[1] for p in pad) else inside
    nx, ny, nz = (s // k for s in a.shape)
    total = a.reshape(nx, k, ny, k, nz, k).sum(axis=(1, 3, 5), dtype=np.uint16)
    return (total / float(k ** 3)).astype(np.float32)


def column_screen(field: np.ndarray, pitch: float) -> dict:
    """Overhang and support-column screen; the last axis of `field` points up.

    `field` is a boolean solid mask or a solid fraction (solid at 0.5 or more).
    Works through tiles of planes along the first axis so that the native grid
    fits in memory; each tile carries a halo for the Gaussian.
    """

    sigma = NORMAL_SMOOTHING_MM / pitch
    halo = int(math.ceil(4 * sigma)) + 2
    cos_limit = math.cos(math.radians(OVERHANG_ANGLE_DEG))
    is_solid = (lambda a: a) if field.dtype == bool else (lambda a: a >= 0.5)
    levels = np.zeros(field.shape[2], dtype=bool)
    for s in range(0, field.shape[0], TILE_PLANES):
        levels |= is_solid(field[s:s + TILE_PLANES]).any(axis=(0, 1))
    levels = np.flatnonzero(levels)
    k_min, k_max = int(levels[0]) + 1, int(levels[-1]) + 1  # +1: tiles are padded by one air voxel
    a, v = pitch ** 2, pitch ** 3
    keys = ("plate_contact_area_mm2", "down_facing_projected_area_any_angle_mm2", "overhang_area_mm2",
            "overhang_projected_area_mm2", "support_volume_mm3", "support_volume_landing_on_plate_mm3",
            "support_volume_landing_on_part_mm3", "overhang_area_within_1mm_of_plate_mm2",
            "support_volume_within_1mm_of_plate_mm3")
    out = dict.fromkeys(keys, 0.0)
    gap_max = 0
    for start in range(0, field.shape[0], TILE_PLANES):
        lo, hi = max(start - halo, 0), min(start + TILE_PLANES + halo, field.shape[0])
        f = np.pad(np.asarray(field[lo:hi], dtype=np.float32), 1)
        solid = f >= 0.5
        smooth = ndimage.gaussian_filter(f, sigma, mode="constant")
        # Highest solid index at or below each voxel, -1 when there is none.
        last = np.where(solid, np.arange(f.shape[2], dtype=np.int16)[None, None, :], np.int16(-1))
        np.maximum.accumulate(last, axis=2, out=last)
        i, j, k = np.nonzero(solid[:, :, 1:] & ~solid[:, :, :-1])
        k = k + 1  # the solid voxel of each solid-over-air transition
        own = (i - 1 + lo >= start) & (i - 1 + lo < start + TILE_PLANES)
        i, j, k = i[own], j[own], k[own]
        below = last[i, j, k - 1].astype(np.int64)
        on_plate = below < 0
        gap = k - 1 - np.where(on_plate, k_min - 1, below)  # air voxels down to the part or the plate level

        def gradient(kk):
            return np.stack([smooth[i + 1, j, kk] - smooth[i - 1, j, kk],
                             smooth[i, j + 1, kk] - smooth[i, j - 1, kk],
                             smooth[i, j, kk + 1] - smooth[i, j, kk - 1]], axis=1).astype(np.float64)

        g = gradient(k) + gradient(k - 1)
        norm = np.linalg.norm(g, axis=1)
        cos_down = np.divide(g[:, 2], norm, out=np.zeros(len(g)), where=norm > 0)
        contact = k == k_min
        over = (cos_down >= cos_limit) & ~contact
        near = over & on_plate & (gap * pitch <= NEAR_PLATE_MM)
        out["plate_contact_area_mm2"] += float(contact.sum() * a)
        out["down_facing_projected_area_any_angle_mm2"] += float((~contact).sum() * a)
        out["overhang_area_mm2"] += float((a / cos_down[over]).sum())
        out["overhang_projected_area_mm2"] += float(over.sum() * a)
        out["support_volume_mm3"] += float(gap[over].sum() * v)
        out["support_volume_landing_on_plate_mm3"] += float(gap[over & on_plate].sum() * v)
        out["support_volume_landing_on_part_mm3"] += float(gap[over & ~on_plate].sum() * v)
        out["overhang_area_within_1mm_of_plate_mm2"] += float((a / cos_down[near]).sum())
        out["support_volume_within_1mm_of_plate_mm3"] += float(gap[near].sum() * v)
        if over.any():
            gap_max = max(gap_max, int(gap[over].max()))
    out["build_height_mm"] = float((k_max - k_min + 1) * pitch)
    out["support_height_max_mm"] = float(gap_max * pitch)
    return out


def trapped_voids(inside: np.ndarray, pitch: float) -> dict:
    """Air not connected (through voxel faces) to the grid boundary."""

    air = ~inside
    boundary_all_air = bool(air[0].all() and air[-1].all() and air[:, 0].all() and air[:, -1].all()
                            and air[:, :, 0].all() and air[:, :, -1].all())
    labels, count = ndimage.label(air)
    del air
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    outside = np.unique(np.concatenate([labels[0].ravel(), labels[-1].ravel(), labels[:, 0].ravel(),
                                        labels[:, -1].ravel(), labels[:, :, 0].ravel(), labels[:, :, -1].ravel()]))
    closed = np.ones(count + 1, dtype=bool)
    closed[outside] = False
    closed[0] = False
    vol = sizes[closed] * pitch ** 3
    return {
        "pitch_mm": pitch,
        "grid_boundary_all_air": boundary_all_air,
        "enclosed_void_volume_mm3": float(vol.sum()),
        "enclosed_voids": int(len(vol)),
        "enclosed_voids_of_1mm3_or_more": int((vol >= 1.0).sum()),
        "largest_enclosed_void_mm3": float(vol.max()) if len(vol) else 0.0,
        "enclosed_void_volume_in_voids_of_1mm3_or_more_mm3": float(vol[vol >= 1.0].sum()),
    }


def necked_voids(inside: np.ndarray, pitch: float, ball_diameter: float) -> dict:
    """Air pockets that hold a ball of the given diameter which cannot roll out.

    Sensitivity to the strict flood fill above, which lets powder leave through
    a one-voxel crack. Ball centres are the air voxels at least one radius from
    any solid; pockets are the centre components that do not reach the grid
    boundary, swept by the ball.
    """

    r = ball_diameter / 2.0
    air = ~inside
    centres = ndimage.distance_transform_edt(air, sampling=pitch) >= r
    labels, count = ndimage.label(centres)
    outside = np.unique(np.concatenate([labels[0].ravel(), labels[-1].ravel(), labels[:, 0].ravel(),
                                        labels[:, -1].ravel(), labels[:, :, 0].ravel(), labels[:, :, -1].ravel()]))
    closed = np.ones(count + 1, dtype=bool)
    closed[outside] = False
    closed[0] = False
    held = closed[labels]
    pocket = air & (ndimage.distance_transform_edt(~held, sampling=pitch) <= r)
    return {
        "pitch_mm": pitch,
        "ball_diameter_mm": ball_diameter,
        "pockets": int(closed.sum()),
        "pocket_volume_mm3": float(pocket.sum() * pitch ** 3),
    }


# --------------------------------------------------------------------------
# independent overhang area on triangles


def stl_overhang(path: Path, plate_tolerance: float) -> dict:
    """Area of triangles within 45 degrees of straight down, per orientation.

    Reads the binary STL in chunks. Triangles whose centroid lies within
    `plate_tolerance` of the lowest vertex are plate contact, not overhang.
    """

    rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    tris = np.memmap(path, dtype=rec, mode="r", offset=84)
    step = 500_000
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for s in range(0, len(tris), step):
        v = tris["v"][s:s + step]
        lo, hi = np.minimum(lo, v.min(axis=(0, 1))), np.maximum(hi, v.max(axis=(0, 1)))
    cos_limit = math.cos(math.radians(OVERHANG_ANGLE_DEG))
    out = {name: {"overhang_area_mm2": 0.0, "plate_contact_area_mm2": 0.0} for name in ORIENTATIONS}
    total = 0.0
    for s in range(0, len(tris), step):
        v = np.asarray(tris["v"][s:s + step], dtype=np.float64)
        cr = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        dbl = np.linalg.norm(cr, axis=1)
        area = 0.5 * dbl
        n = cr / np.where(dbl > 0, dbl, 1.0)[:, None]
        cen = v.mean(axis=1)
        total += float(area.sum())
        for name, (axis, sign) in ORIENTATIONS.items():
            down = -sign * n[:, axis] >= cos_limit
            height = (cen[:, axis] - lo[axis]) if sign > 0 else (hi[axis] - cen[:, axis])
            contact = down & (height <= plate_tolerance)
            out[name]["overhang_area_mm2"] += float(area[down & ~contact].sum())
            out[name]["plate_contact_area_mm2"] += float(area[contact].sum())
    return {"triangles": int(len(tris)), "area_mm2": round(total, 1), "plate_tolerance_mm": plate_tolerance,
            "orientations": {k: {kk: round(vv, 1) for kk, vv in d.items()} for k, d in out.items()}}


# --------------------------------------------------------------------------
# analytic witnesses


def _grid(lo, hi, pitch=0.25):
    axes = [np.arange(a + pitch / 2, b, pitch) for a, b in zip(lo, hi)]
    return np.meshgrid(*axes, indexing="ij")


def witness() -> dict:
    """Run the same functions on shapes with hand-computed answers.

    W1, T block: stem 20 x 20 x 30 mm (z 0..30) under a cap 40 x 40 x 10 mm.
      cap up (+Z):  overhang = 40^2 - 20^2 = 1200 mm2; support = 1200 * 30 = 36000 mm3, all on the plate.
      cap down (-Z): no overhang, no support.
      on its side (+X): the stem flank 20 x 30 = 600 mm2 hangs 10 mm above the plate: 6000 mm3.
    W2, cube 40 mm with a horizontal through-hole (radius R = 8, along Y) and an
      enclosed sphere (radius r = 5):
      +Z: hole ceiling within 45 deg is an arc of 90 deg: (pi/2) R L = 502.65 mm2; the column under it
          is L * integral_{-R/sqrt2}^{R/sqrt2} 2 sqrt(R^2 - x^2) dx = L R^2 (1 + pi/2) = 6581.24 mm3.
          Sphere cap within 45 deg: 2 pi r^2 (1 - cos 45) = 46.01 mm2; column (4 pi / 3) r^3 (1 - 2^-1.5)
          = 338.47 mm3. Every column lands on the part. Enclosed void = (4/3) pi r^3 = 523.60 mm3.
      +Y: the hole is vertical and has no overhang; only the sphere terms remain.
    W3, cube 24 mm with a sphere (r = 5) vented to the top by a 1 x 1 mm channel:
      strict flood fill finds no enclosed void; a 2 mm ball cannot leave, pocket = 523.60 mm3.
    """

    p = 0.25
    cases = []

    def add(name, quantity, expected, measured, pitch):
        err = (measured - expected) / expected if expected else measured
        cases.append({"witness": name, "quantity": quantity, "pitch_mm": pitch, "expected": round(expected, 2),
                      "measured": round(measured, 2),
                      "relative_error" if expected else "absolute_error": round(err, 5),
                      "within_tolerance": bool(abs(err) <= WITNESS_TOLERANCE) if expected else bool(measured == 0.0)})

    def field(solid, pitch):
        k = int(round(pitch / p))
        return solid if k == 1 else block_mean(solid, k)

    pitches = (WORKING_PITCH_MM, SENSITIVITY_PITCH_MM)
    # W1
    x, y, z = _grid((-22, -22, -2), (22, 22, 42))
    solid = ((abs(x) < 10) & (abs(y) < 10) & (z > 0) & (z < 30)) | ((abs(x) < 20) & (abs(y) < 20) & (z > 30) & (z < 40))
    for pitch in pitches:
        for label, axis, sign, area, vol in (("cap up", 2, 1, 1200.0, 36000.0), ("cap down", 2, -1, 0.0, 0.0),
                                             ("on its side", 0, 1, 600.0, 6000.0)):
            m = column_screen(orient(field(solid, pitch), axis, sign), pitch)
            add("W1 T block, " + label, "overhang_area_mm2", area, m["overhang_area_mm2"], pitch)
            add("W1 T block, " + label, "overhang_projected_area_mm2", area, m["overhang_projected_area_mm2"], pitch)
            add("W1 T block, " + label, "support_volume_mm3", vol, m["support_volume_mm3"], pitch)
            add("W1 T block, " + label, "build_height_mm", 40.0, m["build_height_mm"], pitch)
    add("W1 T block", "enclosed_void_volume_mm3", 0.0, trapped_voids(solid, p)["enclosed_void_volume_mm3"], p)

    # W2
    big_r, small_r, length = 8.0, 5.0, 40.0
    solid = (abs(x) < 20) & (abs(y) < 20) & (z > 0) & (z < 40)
    solid &= ~(x ** 2 + (z - 14.0) ** 2 < big_r ** 2)
    solid &= ~(x ** 2 + y ** 2 + (z - 31.0) ** 2 < small_r ** 2)
    hole_a, hole_v = math.pi / 2 * big_r * length, length * big_r ** 2 * (1 + math.pi / 2)
    cap_a = 2 * math.pi * small_r ** 2 * (1 - math.cos(math.pi / 4))
    cap_v = 4 * math.pi / 3 * small_r ** 3 * (1 - 2 ** -1.5)
    for pitch in pitches:
        for label, axis, area, vol in (("hole horizontal (+Z)", 2, hole_a + cap_a, hole_v + cap_v),
                                       ("hole vertical (+Y)", 1, cap_a, cap_v)):
            m = column_screen(orient(field(solid, pitch), axis, 1), pitch)
            add("W2 holed cube, " + label, "overhang_area_mm2", area, m["overhang_area_mm2"], pitch)
            add("W2 holed cube, " + label, "support_volume_mm3", vol, m["support_volume_mm3"], pitch)
            add("W2 holed cube, " + label, "support_volume_landing_on_part_mm3", vol,
                m["support_volume_landing_on_part_mm3"], pitch)
            add("W2 holed cube, " + label, "build_height_mm", 40.0, m["build_height_mm"], pitch)
    sphere = 4 * math.pi / 3 * small_r ** 3
    add("W2 holed cube", "enclosed_void_volume_mm3", sphere, trapped_voids(solid, p)["enclosed_void_volume_mm3"], p)

    # W3
    x, y, z = _grid((-14, -14, -2), (14, 14, 26))
    solid = (abs(x) < 12) & (abs(y) < 12) & (z > 0) & (z < 24)
    solid &= ~(x ** 2 + y ** 2 + (z - 12.0) ** 2 < small_r ** 2)
    solid &= ~((abs(x) < 0.5) & (abs(y) < 0.5) & (z > 12.0))
    add("W3 vented sphere", "enclosed_void_volume_mm3", 0.0, trapped_voids(solid, p)["enclosed_void_volume_mm3"], p)
    half = block_mean(solid, int(round(VOID_PROBE_PITCH_MM / p))) >= 0.5
    add("W3 vented sphere", "pocket_volume_2mm_ball_mm3", sphere,
        necked_voids(half, VOID_PROBE_PITCH_MM, PROBE_BALL_DIAMETER_MM)["pocket_volume_mm3"], VOID_PROBE_PITCH_MM)
    working = [c for c in cases if c["pitch_mm"] != SENSITIVITY_PITCH_MM or c["quantity"].startswith("pocket")]
    worst = max((abs(c.get("relative_error", 0.0)) for c in working), default=0.0)
    return {"tolerance_relative": WITNESS_TOLERANCE,
            "applies_to": "the working pitch and the void checks; the sensitivity-pitch rows are information",
            "all_within_tolerance": all(c["within_tolerance"] for c in working),
            "largest_relative_error_at_working_pitch": worst,
            "largest_relative_error_at_sensitivity_pitch": max(
                abs(c.get("relative_error", 0.0)) for c in cases if c not in working),
            "cases": cases}


# --------------------------------------------------------------------------


def main(private, params):
    private, params = Path(private), Path(params)
    started = time.time()
    wit = witness()
    print("witness all within tolerance:", wit["all_within_tolerance"], flush=True)

    grid = json.loads((private / "occupancy-grid.json").read_text())
    p = float(grid["pitch_mm"])
    wn = np.load(private / grid["array"], mmap_mode="r")
    inside = np.empty(wn.shape, dtype=bool)
    for s in range(0, wn.shape[0], 32):
        inside[s:s + 32] = np.asarray(wn[s:s + 32]) > 0.5
    del wn
    # One body: keep the largest face-connected solid component, as T1 does.
    labels, count = ndimage.label(inside)
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    sizes[0] = 0
    grid_inside = int(sizes.sum())
    inside = labels == int(sizes.argmax())
    del labels
    dropped = {"components": int(count - 1), "volume_mm3": round(float((grid_inside - sizes.max()) * p ** 3), 3)}
    origin = np.array([grid["x0"], grid["y0"], grid["z0"]])
    extent = []
    for axis in range(3):
        idx = np.flatnonzero(inside.any(axis=tuple(a for a in range(3) if a != axis)))
        extent.append((float(origin[axis] + (idx[0] - 0.5) * p), float(origin[axis] + (idx[-1] + 0.5) * p)))
    volume = float(inside.sum() * p ** 3)
    assert abs(WORKING_PITCH_MM - p) < 1e-9, "the working pitch is the grid pitch"
    coarse = block_mean(inside, int(round(SENSITIVITY_PITCH_MM / p)))
    print("grid loaded; flood fill", flush=True)
    voids = {"strict_flood_fill_fine": trapped_voids(inside, p)}
    half = block_mean(inside, int(round(VOID_PROBE_PITCH_MM / p))) >= 0.5
    voids["strict_flood_fill_coarse"] = trapped_voids(half, VOID_PROBE_PITCH_MM)
    voids["ball_probe_coarse"] = necked_voids(half, VOID_PROBE_PITCH_MM, PROBE_BALL_DIAMETER_MM)
    del half
    print(json.dumps(voids), flush=True)

    levels = json.loads((params / "frame.json").read_text())["levels_twin"]
    datum = {"deck_down": ("deck plane z = 0", levels["deck_z"] - extent[2][0]),
             "flange_y_minus_down": ("flange plane y = %.2f" % levels["flange_y_high_B"],
                                     levels["flange_y_high_B"] - extent[1][0]),
             "flange_y_plus_down": ("flange plane y = %.2f" % levels["flange_y_low_B"],
                                    extent[1][1] - levels["flange_y_low_B"])}
    surfaces = {}
    for label, name in (("mc_1p0mm", "t1-sim-mc100.stl"), ("t1s_clean", "t1s-clean.stl")):
        if (private / name).exists():
            surfaces[label] = stl_overhang(private / name, PLATE_TOLERANCE_MM)
            print("surface check", label, flush=True)

    results = {}
    for name, (axis, sign) in ORIENTATIONS.items():
        r = {"definition": ORIENTATION_NOTES[name], "build_axis": "XYZ"[axis], "build_sign": sign}
        if name in datum:
            r["named_face"] = datum[name][0]
            r["named_face_above_lowest_point_mm"] = round(datum[name][1], 2)
        m = column_screen(orient(inside, axis, sign), WORKING_PITCH_MM)
        r.update({k: round(v, 2 if k.endswith("_mm") else 1) for k, v in m.items()})
        r["support_volume_over_part_volume"] = round(m["support_volume_mm3"] / volume, 4)
        r["enclosed_void_volume_mm3"] = round(voids["strict_flood_fill_fine"]["enclosed_void_volume_mm3"], 1)
        c = column_screen(orient(coarse, axis, sign), SENSITIVITY_PITCH_MM)
        r["sensitivity_0p5mm"] = {k: round(c[k], 1) for k in ("overhang_area_mm2", "support_volume_mm3",
                                                             "build_height_mm", "plate_contact_area_mm2")}
        r["sensitivity_0p5mm"]["overhang_area_relative_to_working"] = round(
            c["overhang_area_mm2"] / m["overhang_area_mm2"] - 1.0, 4)
        r["sensitivity_0p5mm"]["support_volume_relative_to_working"] = round(
            c["support_volume_mm3"] / m["support_volume_mm3"] - 1.0, 4)
        r["triangle_overhang_area_mm2"] = {s: surfaces[s]["orientations"][name]["overhang_area_mm2"]
                                           for s in surfaces}
        r["overhang_area_relative_to_triangles"] = {
            s: round(m["overhang_area_mm2"] / surfaces[s]["orientations"][name]["overhang_area_mm2"] - 1.0, 4)
            for s in surfaces}
        results[name] = r
        print(name, json.dumps(r), flush=True)

    rep = {
        "schema": "935-cad-twin-am-supports/1",
        "scope": "geometric LPBF orientation screen of the study twin body; no support design, no orientation "
                 "choice, no build file, no material or process qualification",
        "inputs": {"occupancy_grid": grid["array"], "grid_pitch_mm": p, "inside_rule": "winding number > 0.5",
                   "inside_volume_mm3": round(volume, 1),
                   "body": "largest face-connected solid component", "dropped_solid_components": dropped,
                   "body_extent_mm": {"x": extent[0], "y": extent[1], "z": extent[2]},
                   "surfaces_for_the_triangle_check": {k: {kk: v[kk] for kk in ("triangles", "area_mm2")}
                                                       for k, v in surfaces.items()}},
        "method": {
            "overhang_angle_from_plate_deg": OVERHANG_ANGLE_DEG,
            "working_pitch_mm": WORKING_PITCH_MM,
            "sensitivity_pitch_mm": SENSITIVITY_PITCH_MM,
            "normal": "gradient of the solid fraction after a Gaussian of %.2f mm" % NORMAL_SMOOTHING_MM,
            "overhang_area": "sum of pitch^2 / cos(angle to straight down) over solid-over-air column "
                             "transitions within 45 deg of straight down, plate contact excluded",
            "support_volume": "air column under each such transition, down to the next solid voxel or to the "
                              "lowest solid level (the plate)",
            "plate_contact": "transitions on the lowest solid level; the plate touches the lowest point, no "
                             "stock or raft is added",
            "enclosed_voids": "air components not face-connected to the grid boundary (orientation independent)",
            "ball_probe": "pockets holding a %.0f mm ball that cannot reach the grid boundary, on the %.1f mm "
                          "grid" % (PROBE_BALL_DIAMETER_MM, VOID_PROBE_PITCH_MM),
            "triangle_check": "area of surface triangles whose normal is within 45 deg of straight down, "
                              "centroids within %.1f mm of the lowest vertex excluded" % PLATE_TOLERANCE_MM,
        },
        "witness": wit,
        "voids": voids,
        "orientations": results,
        "seconds": round(time.time() - started, 1),
        "limits": (
            "Screen of the study twin (1 scan unit = 1 mm by owner instruction, no physical calibration; 12% of "
            "its area is hypothesis closure, and the enclosed voids and thin handles in the unobserved regions "
            "are winding-number artefacts as much as geometry). Only six axis-aligned orientations are measured; "
            "tilted orientations are not. The 45 degree rule and the air-column volume are conventions, not a "
            "support design: no support type, density, tooth, removal access, heat path, recoater load or "
            "distortion is considered, short bridges are not credited, and the plate touches the lowest point "
            "without machining stock. Column volumes are envelope volumes, not support material. The strict "
            "flood fill lets powder leave through a 0.25 mm opening; the ball probe is the sensitivity to that. "
            "Attached studs are excluded from the body. Nothing here establishes printability, an orientation "
            "choice, a material, dimensional accuracy or function."
        ),
    }
    (params / "am-supports.json").write_text(json.dumps(rep, indent=2) + "\n")
    print("written", params / "am-supports.json", "in", rep["seconds"], "s")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--witness":
        print(json.dumps(witness(), indent=1))
    else:
        main(*sys.argv[1:3])
