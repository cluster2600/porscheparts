"""Support layout of the print body under declared rules (geometry only).

The orientation screen (am_supports.py) measures how much surface hangs below
45 degrees and the air under it. This tool turns that into a layout: which
down-facing surface gets a support, where each support stands, what it melts,
what it touches and whether a straight tool can reach it.

Rules, all read from the case file with their sources:

- a down-facing surface below the critical angle from the plate is supported;
- an attached overhang narrower than the declared self-supporting width is
  left bare, unless it is where an island starts (a region of a layer with no
  solid under it): an island always gets a support;
- a support is a block support: thin walls on a square hatch, standing in the
  air column under the surface down to the plate or to the part below. Its
  melted share of that column is 2 t / s - (t / s)^2 for walls t on a hatch s;
- teeth reduce the contact with the part to a declared share of the wall line.

Outputs, on the 0.25 mm occupancy grid with the build direction up:

- the support envelope (the air columns that hold a block support), kept as a
  private voxel array for the build screen;
- scalars: supported area, envelope and melted volume, split by landing (plate
  or part), the support bodies with their height and slenderness, the contact
  with the part, and the share with no straight lateral access: a support voxel
  is hidden when the part stands between it and the outside along both
  horizontal axes of the grid, in both senses.

Before the head, the same functions run on shapes with hand-computed answers,
and the totals before any exemption are compared with the orientation screen.

This is a layout by rule on a study body. It is not a build file, it was not
prepared in a build processor, and no person has judged whether the supports
can be removed.

Usage: support_design.py witness CASE.json OUT.json
       support_design.py layout OCC_DIR CASE.json ORIENTATION_SCREEN.json PRIVATE_OUT_DIR OUT.json
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

NORMAL_SMOOTHING_MM = 0.5          # as in am_supports.py, chosen there on analytic witnesses
TILE_PLANES = 64
WITNESS_TOLERANCE = 0.05
FULL = np.ones((3, 3, 3), dtype=bool)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def block_fraction(rules: dict) -> float:
    t, s = rules["block_support"]["wall_thickness_mm"], rules["block_support"]["hatch_mm"]
    return 2 * t / s - (t / s) ** 2


def transitions(solid: np.ndarray, pitch: float, critical_deg: float) -> dict:
    """Every solid-over-air transition of a boolean grid whose last axis points up.

    Returns the index of the solid voxel of each transition, the number of air voxels under it down to
    the next solid voxel or to the plate (the lowest solid level), whether that column lands on the
    plate, and whether the surface there lies below the critical angle. The normal is the gradient of
    the solid fraction after a Gaussian, as in the orientation screen.
    """

    sigma = NORMAL_SMOOTHING_MM / pitch
    halo = int(math.ceil(4 * sigma)) + 2
    cos_limit = math.cos(math.radians(critical_deg))
    levels = np.flatnonzero(solid.any(axis=(0, 1)))
    k_min = int(levels[0])
    out = {key: [] for key in ("i", "j", "k", "gap", "on_plate", "over", "contact", "cos_down")}
    for start in range(0, solid.shape[0], TILE_PLANES):
        lo, hi = max(start - halo, 0), min(start + TILE_PLANES + halo, solid.shape[0])
        f = np.pad(solid[lo:hi].astype(np.float32), 1)
        s = f >= 0.5
        smooth = ndimage.gaussian_filter(f, sigma, mode="constant")
        last = np.where(s, np.arange(f.shape[2], dtype=np.int16)[None, None, :], np.int16(-1))
        np.maximum.accumulate(last, axis=2, out=last)
        i, j, k = np.nonzero(s[:, :, 1:] & ~s[:, :, :-1])
        k = k + 1
        own = (i - 1 + lo >= start) & (i - 1 + lo < start + TILE_PLANES)
        i, j, k = i[own], j[own], k[own]
        below = last[i, j, k - 1].astype(np.int64)
        on_plate = below < 0
        gap = k - 1 - np.where(on_plate, k_min, below)             # k_min + 1 is the plate level in padded indices

        def gradient(kk):
            return np.stack([smooth[i + 1, j, kk] - smooth[i - 1, j, kk],
                             smooth[i, j + 1, kk] - smooth[i, j - 1, kk],
                             smooth[i, j, kk + 1] - smooth[i, j, kk - 1]], axis=1).astype(np.float64)

        g = gradient(k) + gradient(k - 1)
        norm = np.linalg.norm(g, axis=1)
        cos_down = np.divide(g[:, 2], norm, out=np.zeros(len(g)), where=norm > 0)
        contact = (k - 1) == k_min
        out["i"].append(i - 1 + lo)
        out["j"].append(j - 1)
        out["k"].append(k - 1)
        out["gap"].append(gap)
        out["on_plate"].append(on_plate)
        out["contact"].append(contact)
        out["over"].append((cos_down >= cos_limit) & ~contact)
        out["cos_down"].append(cos_down)
    return {key: np.concatenate(v) for key, v in out.items()}


def inscribed_width(mask2d: np.ndarray, pitch: float) -> float:
    """Diameter of the largest disc that fits in a 2D mask."""

    return float(2.0 * ndimage.distance_transform_edt(np.pad(mask2d, 1)).max() * pitch)


def layout(solid: np.ndarray, pitch: float, rules: dict) -> tuple[dict, np.ndarray]:
    """Scalars of the support layout of a boolean grid whose last axis points up, and its envelope.

    The envelope comes back as a small-integer grid: 0 none, 1 a support that lands on the plate,
    2 one that lands on the part, plus 4 where no straight lateral access exists.
    """

    a, v = pitch ** 2, pitch ** 3
    t = transitions(solid, pitch, rules["critical_angle_from_plate_deg"])
    over = t["over"]
    i, j, k, gap, on_plate = (t[key][over] for key in ("i", "j", "k", "gap", "on_plate"))
    cos_down = t["cos_down"][over]
    rep = {"plate_contact_area_mm2": float(t["contact"].sum() * a),
           "before_exemption": {"overhang_projected_area_mm2": float(len(i) * a),
                                "overhang_area_mm2": float((a / cos_down).sum()),
                                "air_column_volume_mm3": float(gap.sum() * v)}}

    # Patches of supported surface, and the exemption of narrow attached overhangs.
    surface = np.zeros(solid.shape, dtype=bool)
    surface[i, j, k] = True
    labels, count = ndimage.label(surface, structure=FULL)
    patch = labels[i, j, k]
    del labels, surface
    keep = np.ones(len(i), dtype=bool)
    limit = rules.get("self_supporting_width_mm")
    exempt = {"rule_width_mm": limit, "patches": int(count), "patches_left_bare": 0, "narrow_patches_kept_as_island_starts": 0,
              "projected_area_left_bare_mm2": 0.0}
    if limit is not None:
        order = np.argsort(patch, kind="stable")
        bounds = np.flatnonzero(np.diff(patch[order])) + 1
        layer_cache: dict = {}
        for group in np.split(order, bounds):
            gi, gj, gk = i[group], j[group], k[group]
            foot = np.zeros((gi.max() - gi.min() + 1, gj.max() - gj.min() + 1), dtype=bool)
            foot[gi - gi.min(), gj - gj.min()] = True
            if inscribed_width(foot, pitch) > limit:
                continue
            # An island starts where a region of a layer has no solid under it: such a patch keeps its support.
            k0 = int(gk.min())
            if k0 not in layer_cache:
                lab, _ = ndimage.label(solid[:, :, k0])
                under = ndimage.binary_dilation(solid[:, :, k0 - 1]) if k0 > 0 else np.zeros(lab.shape, dtype=bool)
                carried = np.zeros(int(lab.max()) + 1, dtype=bool)
                carried[np.unique(lab[under & (lab > 0)])] = True
                layer_cache[k0] = (lab, carried)
            lab, carried = layer_cache[k0]
            low = gk == k0
            if not carried[lab[gi[low], gj[low]]].all():
                exempt["narrow_patches_kept_as_island_starts"] += 1
                continue
            keep[group] = False
            exempt["patches_left_bare"] += 1
            exempt["projected_area_left_bare_mm2"] += float(len(group) * a)
        del layer_cache
    rep["exemption"] = exempt
    i, j, k, gap, on_plate, cos_down = (q[keep] for q in (i, j, k, gap, on_plate, cos_down))

    # Envelope: the air column under every supported transition.
    diff = np.zeros(solid.shape[:2] + (solid.shape[2] + 1,), dtype=np.int8)
    np.add.at(diff, (i, j, k - gap), 1)
    np.add.at(diff, (i, j, k), -1)
    envelope = np.cumsum(diff, axis=2, dtype=np.int8)[:, :, :-1] > 0
    diff[:] = 0
    np.add.at(diff, (i[on_plate], j[on_plate], (k - gap)[on_plate]), 1)
    np.add.at(diff, (i[on_plate], j[on_plate], k[on_plate]), -1)
    kind = np.where(envelope, np.uint8(2), np.uint8(0))                      # 1: lands on the plate, 2: on the part
    kind[np.cumsum(diff, axis=2, dtype=np.int8)[:, :, :-1] > 0] = 1
    del diff
    assert not (envelope & solid).any()
    assert int(envelope.sum()) == int(gap.sum())
    f = block_fraction(rules)
    teeth = rules["block_support"]["tooth_contact_share_of_the_wall_line"]
    wall_line_per_area = 2.0 / rules["block_support"]["hatch_mm"]           # wall length per supported area, mm / mm2
    top_area = float((a / cos_down).sum())
    rep["supported"] = {
        "projected_area_mm2": float(len(i) * a), "surface_area_mm2": top_area,
        "envelope_volume_mm3": float(gap.sum() * v),
        "envelope_landing_on_plate_mm3": float(gap[on_plate].sum() * v),
        "envelope_landing_on_part_mm3": float(gap[~on_plate].sum() * v),
        "landing_area_on_part_mm2": float((~on_plate).sum() * a),
        "largest_height_mm": float(gap.max() * pitch) if len(gap) else 0.0}
    # Every support touches the part at its top, under the surface it holds; one that stands on the
    # part touches it a second time at its foot. One that stands on the plate has no second contact.
    top_line = len(i) * a * wall_line_per_area
    foot_line = float((~on_plate).sum()) * a * wall_line_per_area
    rep["block_support"] = {
        "melted_share_of_the_envelope": round(f, 4), "melted_volume_mm3": float(gap.sum() * v * f),
        "wall_line_under_the_supported_surface_mm": float(top_line),
        "wall_line_at_the_foot_of_supports_standing_on_the_part_mm": foot_line,
        "wall_line_on_the_part_mm": float(top_line + foot_line),
        "tooth_contact_line_on_the_part_mm": float((top_line + foot_line) * teeth)}

    # Support bodies.
    labels, bodies = ndimage.label(envelope)
    slices = ndimage.find_objects(labels)
    heights, widths, volumes = [], [], []
    for b, sl in enumerate(slices, start=1):
        body = labels[sl] == b
        heights.append(body.any(axis=(0, 1)).sum() * pitch)
        widths.append(inscribed_width(body.any(axis=2), pitch))
        volumes.append(float(body.sum() * v))
    del labels
    heights, widths, volumes = np.array(heights), np.array(widths), np.array(volumes)
    slender = heights / np.maximum(widths, pitch)
    rep["bodies"] = {"count": int(bodies),
                     "of_1_mm3_or_more": int((volumes >= 1.0).sum()),
                     "largest_volume_mm3": float(volumes.max()) if bodies else 0.0,
                     "tallest_mm": float(heights.max()) if bodies else 0.0,
                     "height_over_inscribed_width": {"median": float(np.median(slender)) if bodies else 0.0,
                                                     "largest": float(slender.max()) if bodies else 0.0}}
    limit_s = rules.get("slenderness_limit")
    if limit_s is not None:
        over_limit = slender > limit_s
        rep["bodies"]["slenderness_limit"] = limit_s
        rep["bodies"]["over_the_slenderness_limit"] = {"count": int(over_limit.sum()),
                                                       "envelope_volume_mm3": float(volumes[over_limit].sum())}

    # Straight lateral access: no part between the voxel and the outside along one horizontal axis.
    visible = np.zeros(solid.shape, dtype=bool)
    for axis in (0, 1):
        for flip in (False, True):
            s = np.flip(solid, axis) if flip else solid
            blocked = np.logical_or.accumulate(s, axis=axis)
            visible |= ~(np.flip(blocked, axis) if flip else blocked)
            del blocked
    hidden = envelope & ~visible
    kind[hidden] += 4                                                        # +4: no straight lateral access
    top_hidden = hidden[i, j, k - 1]
    rep["lateral_access"] = {
        "rule": "hidden: the part stands between the voxel and the outside along both horizontal grid axes, in both senses; "
                "oblique and vertical access are not tested",
        "hidden_envelope_volume_mm3": float(hidden.sum() * v),
        "hidden_share_of_the_envelope": float(hidden.sum() / max(int(envelope.sum()), 1)),
        "hidden_supported_projected_area_mm2": float(top_hidden.sum() * a),
        "hidden_share_of_the_supported_area": float(top_hidden.sum() / max(len(i), 1))}
    return rep, kind


# --------------------------------------------------------------------------
# witnesses


def _grid(lo, hi, pitch=0.25):
    axes = [np.arange(a + pitch / 2, b, pitch) for a, b in zip(lo, hi)]
    return np.meshgrid(*axes, indexing="ij")


def witness(case_file, out) -> None:
    """Shapes with hand-computed answers, at 0.25 mm, under the rules of the case file.

    W1, T block: stem 20 x 20 x 30 mm under a cap 40 x 40 x 10 mm. Supported area 40^2 - 20^2 = 1200 mm2,
      envelope 1200 x 30 = 36000 mm3, all on the plate, one body (a square ring 10 mm wide), 30 mm tall, nothing
      hidden. The largest disc in the ring sits in a corner, against the two outer faces and the stem's edge:
      its diameter is 20 sqrt(2) / (1 + sqrt(2)) = 11.72 mm, so the slenderness is 30 / 11.72 = 2.56.
    W2, cube 40 mm with a box cavity 20 x 20 x 10 mm (z 10..20) open to the top through a 4 x 4 mm chimney.
      Supported area 20^2 - 4^2 = 384 mm2, envelope 3840 mm3, all landing on the part, all hidden, one body.
    W3, a wall 10 mm thick and 30 mm high (y 0..40) with two ledges at z 20..24 on opposite faces: one stands
      out by w0, the self-supporting width, the other by 3 mm. The narrow one is bare, left so by the rule or
      not seen as an overhang at all by the smoothed normal; the wide one is supported: 3 x 40 = 120 mm2,
      120 x 20 = 2400 mm3.
    W4, a blade 40 mm long and 1.5 mm thick, hanging 10 mm under a slab that stands on two posts, with the
      self-supporting width raised to 2 mm so that the blade's edge is narrow by the rule:
      its lower edge is narrow, but an island starts there, so it keeps its support: w0 x 40 mm2 under the blade.
      The slab is 40 x 40 at z 30..34 on posts 4 x 40 at both ends in x; its underside between the posts and
      outside the blade is supported as well: (32 - w0) x 40 mm2 at 30 mm.
    """

    case = json.loads(Path(case_file).read_text())
    rules = case["rules"]
    p = 0.25
    cases = []

    def add(name, quantity, expected, measured):
        err = (measured - expected) / expected if expected else measured
        cases.append({"witness": name, "quantity": quantity, "expected": round(expected, 3), "measured": round(measured, 3),
                      "relative_error" if expected else "absolute_error": round(err, 5),
                      "within_tolerance": bool(abs(err) <= WITNESS_TOLERANCE) if expected else bool(measured == 0.0)})

    x, y, z = _grid((-22, -22, 0), (22, 22, 42))
    solid = ((abs(x) < 10) & (abs(y) < 10) & (z < 30)) | ((abs(x) < 20) & (abs(y) < 20) & (z > 30) & (z < 40))
    r, _ = layout(solid, p, rules)
    add("W1 T block", "supported_projected_area_mm2", 1200.0, r["supported"]["projected_area_mm2"])
    add("W1 T block", "envelope_volume_mm3", 36000.0, r["supported"]["envelope_volume_mm3"])
    add("W1 T block", "envelope_landing_on_part_mm3", 0.0, r["supported"]["envelope_landing_on_part_mm3"])
    add("W1 T block", "melted_volume_mm3", 36000.0 * block_fraction(rules), r["block_support"]["melted_volume_mm3"])
    add("W1 T block", "bodies", 1.0, float(r["bodies"]["count"]))
    add("W1 T block", "tallest_mm", 30.0, r["bodies"]["tallest_mm"])
    add("W1 T block", "slenderness_largest", 30.0 * (1 + math.sqrt(2)) / (20 * math.sqrt(2)),
        r["bodies"]["height_over_inscribed_width"]["largest"])
    add("W1 T block", "hidden_envelope_volume_mm3", 0.0, r["lateral_access"]["hidden_envelope_volume_mm3"])

    solid = (abs(x) < 20) & (abs(y) < 20) & (z < 40)
    solid &= ~((abs(x) < 10) & (abs(y) < 10) & (z > 10) & (z < 20))
    solid &= ~((abs(x) < 2) & (abs(y) < 2) & (z > 15))
    r, _ = layout(solid, p, rules)
    add("W2 cavity with a chimney", "supported_projected_area_mm2", 384.0, r["supported"]["projected_area_mm2"])
    add("W2 cavity with a chimney", "envelope_volume_mm3", 3840.0, r["supported"]["envelope_volume_mm3"])
    add("W2 cavity with a chimney", "envelope_landing_on_part_mm3", 3840.0, r["supported"]["envelope_landing_on_part_mm3"])
    add("W2 cavity with a chimney", "landing_area_on_part_mm2", 384.0, r["supported"]["landing_area_on_part_mm2"])
    add("W2 cavity with a chimney", "hidden_envelope_volume_mm3", 3840.0, r["lateral_access"]["hidden_envelope_volume_mm3"])
    add("W2 cavity with a chimney", "bodies", 1.0, float(r["bodies"]["count"]))

    limit = rules.get("self_supporting_width_mm")
    if limit is not None:
        w0 = round(limit / p) * p
        x, y, z = _grid((-12, 0, 0), (12, 40, 32))
        solid = (abs(x) < 5) & (z < 30)
        solid |= (x > 0) & (x < 5 + w0) & (z > 20) & (z < 24)
        solid |= (x < 0) & (x > -8) & (z > 20) & (z < 24)
        r, _ = layout(solid, p, rules)
        add("W3 two ledges", "supported_projected_area_mm2", 120.0, r["supported"]["projected_area_mm2"])
        add("W3 two ledges", "envelope_volume_mm3", 2400.0, r["supported"]["envelope_volume_mm3"])
        cases.append({"witness": "W3 two ledges", "quantity": "narrow ledge: patches left bare by the rule (0: not seen as an overhang)",
                      "measured": r["exemption"]["patches_left_bare"], "within_tolerance": r["exemption"]["patches_left_bare"] in (0, 1)})

        x, y, z = _grid((-20, 0, 0), (20, 40, 36))
        solid = (abs(x) < 20) & (z > 30) & (z < 34)
        solid |= (abs(x) > 16) & (z < 34)
        w0 = 1.5
        solid |= (abs(x) < w0 / 2) & (z > 20) & (z < 34)
        r, _ = layout(solid, p, {**rules, "self_supporting_width_mm": 2.0})
        area = w0 * 40.0 + (32.0 - w0) * 40.0
        add("W4 hanging blade", "supported_projected_area_mm2", area, r["supported"]["projected_area_mm2"])
        add("W4 hanging blade", "envelope_volume_mm3", w0 * 40.0 * 20.0 + (32.0 - w0) * 40.0 * 30.0,
            r["supported"]["envelope_volume_mm3"])
        add("W4 hanging blade", "narrow_patches_kept_as_island_starts", 1.0,
            float(r["exemption"]["narrow_patches_kept_as_island_starts"]))
        add("W4 hanging blade", "patches_left_bare", 0.0, float(r["exemption"]["patches_left_bare"]))

    rep = {"schema": "935-cad-twin-support-design-witness/1", "date": time.strftime("%Y-%m-%d"),
           "pitch_mm": p, "tolerance_relative": WITNESS_TOLERANCE,
           "rules_sha256": hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest(),
           "passed": all(c["within_tolerance"] for c in cases),
           "largest_relative_error": max(abs(c.get("relative_error", 0.0)) for c in cases), "cases": cases}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({"passed": rep["passed"], "largest_relative_error": rep["largest_relative_error"],
                      "failed": [c for c in cases if not c["within_tolerance"]]}))
    assert rep["passed"]


# --------------------------------------------------------------------------


def run_layout(occ_dir, case_file, screen_file, private_out, out) -> None:
    occ_dir, private_out = Path(occ_dir), Path(private_out)
    started = time.time()
    case = json.loads(Path(case_file).read_text())
    rules = case["rules"]
    grid = json.loads((occ_dir / "occupancy-grid.json").read_text())
    pitch = float(grid["pitch_mm"])
    assert case["build"]["direction"] == "-y"
    inside = np.load(occ_dir / grid["array"], mmap_mode="r") > 0.5
    labels, count = ndimage.label(inside)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    inside = labels == int(sizes.argmax())
    del labels
    # Axes x, z, build height: the frame of the build screen (build_sim.py prepare), before its crop.
    solid = np.ascontiguousarray(inside.transpose(0, 2, 1)[:, :, ::-1])
    del inside
    rep, kind = layout(solid, pitch, rules)
    envelope = kind > 0

    # The totals before any exemption are the orientation screen's, when the critical angle is its 45 degrees.
    screen = json.loads(Path(screen_file).read_text())
    ref = screen["orientations"][case["build"]["orientation_in_the_screen"]]
    check = {"orientation_screen_file": "params/" + Path(screen_file).name,
             "orientation": case["build"]["orientation_in_the_screen"]}
    if rules["critical_angle_from_plate_deg"] == screen["method"]["overhang_angle_from_plate_deg"]:
        pairs = (("overhang_projected_area_mm2", "overhang_projected_area_mm2"), ("overhang_area_mm2", "overhang_area_mm2"),
                 ("air_column_volume_mm3", "support_volume_mm3"))
        check["relative_difference"] = {mine: round(rep["before_exemption"][mine] / ref[theirs] - 1.0, 6) for mine, theirs in pairs}
        check["agrees_within_0p1_percent"] = all(abs(d) < 1e-3 for d in check["relative_difference"].values())
        assert check["agrees_within_0p1_percent"], check
    else:
        check["note"] = "another critical angle than the orientation screen's: the totals are not comparable"

    process = case["process_for_the_time_estimate"]
    part_volume = float(solid.sum()) * pitch ** 3
    melted = rep["block_support"]["melted_volume_mm3"]
    rep["against_the_part"] = {
        "part_volume_mm3": part_volume,
        "envelope_over_part_volume": rep["supported"]["envelope_volume_mm3"] / part_volume,
        "melted_support_over_part_volume": melted / part_volume,
        "added_exposure_h": melted * process["volumetric_energy_density_J_mm3"] / process["laser_power_W"] / 3600.0,
        "part_exposure_h": part_volume * process["volumetric_energy_density_J_mm3"] / process["laser_power_W"] / 3600.0}

    private_out.mkdir(parents=True, exist_ok=True)
    np.save(private_out / "support-envelope.npy", envelope)
    np.save(private_out / "support-kind.npy", kind)       # 1 plate, 2 part, +4 hidden: for the picture
    (private_out / "support-envelope.json").write_text(json.dumps({
        "frame": "x, z, build height (-y), uncropped: the frame of build_sim.py prepare before its crop",
        "shape": list(envelope.shape), "pitch_mm": pitch,
        "occupancy_sha256": sha256(occ_dir / grid["array"]),
        "rules_sha256": hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest(),
        "melted_share_of_the_envelope": block_fraction(rules)}, indent=1) + "\n")
    record = {
        "schema": "935-cad-twin-support-design/1", "date": time.strftime("%Y-%m-%d"),
        "scope": "support layout of the print body by declared rules, on the 0.25 mm occupancy grid, flange y+ on the plate. "
                 "Geometry only: no build file, no build processor, no judgement of removal by a person",
        "case_file": "params/" + Path(case_file).name, "case_sha256": sha256(Path(case_file)),
        "occupancy_sha256": sha256(occ_dir / grid["array"]), "grid_pitch_mm": pitch,
        "dropped_solid_components": int(count) - 1,
        "check_against_the_orientation_screen": check,
        **rep,
        "gates": {"layout_prepared_in_a_build_processor": False, "removal_judged_by_a_person": False,
                  "support_parameters_from_the_machine_maker": False, "metal_print_authorized": False},
        "seconds": round(time.time() - started, 1),
    }
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("check_against_the_orientation_screen", "before_exemption", "exemption", "supported",
                                             "block_support", "bodies", "lateral_access", "against_the_part", "seconds")}))


if __name__ == "__main__":
    {"witness": witness, "layout": run_layout}[sys.argv[1]](*sys.argv[2:])
