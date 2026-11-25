"""Valve, seat insert and guide of each valve as separate bodies on the fitted axes.

Issue #698. Every dimension comes from params/valve-seat-guide-case.json,
where each value names its source or its hypothesis (H16 for published values
of other heads and explicit assumptions, H09 for the inlet and exhaust
roles), or from a fit on the scan (params/feature-fits.json). Nothing here is
a measurement of the specimen.

Each body is a solid of revolution about its valve's datum axis. Stations s
run along that axis, positive toward the cam side; radii r from it:

  seat insert  bore = fitted throat; the published 45 degree seat cone passes
               through the mid-band circle of the fitted seat, with the
               published 30 and 75 degree cuts on either side of the contact
               band; outside diameter and height from the case;
  valve        closed on that cone: its contact band (published width, inset
               from the edge of the 45 degree face) lies on the seat; margin,
               face, straight tulip, 8 mm stem, published overall length;
  guide        fitted outside diameter and stations, an assumed running
               clearance on the stem; the port end follows its fitted cone.

Checks: the bodies do not overlap (closed and at the published largest
lifts), the stem runs in the guide, the contact band lies inside the fitted
seat window, and the two valve heads keep a stated distance at full lift.

Usage: valve_seat_guide.py PARAMS_DIR OUT_DIR
  OUT_DIR  new private directory: one STEP per body, an STL of the assembly
Writes PARAMS_DIR/valve-seat-guide.json (numbers and hashes only).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

TAN = lambda deg: math.tan(math.radians(deg))  # noqa: E731
COS45 = math.cos(math.radians(45.0))
VALVES = ("valve_y_minus", "valve_y_plus")
GUIDE_START = {"valve_y_minus": "valve_y_minus_guide_bore", "valve_y_plus": "valve_y_plus_guide_boss_port"}
GUIDE_END = {"valve_y_minus": "valve_y_minus_guide_bore", "valve_y_plus": "valve_y_plus_guide_od_cam"}
GUIDE_OD = {"valve_y_minus": "valve_y_minus_guide_od_cam", "valve_y_plus": "valve_y_plus_guide_od_cam"}
GUIDE_PORT_CONE = {"valve_y_minus": "valve_y_minus_guide_od_port", "valve_y_plus": None}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def value(entry):
    return entry["value"] if isinstance(entry, dict) else entry


def profiles(case: dict, fits: dict) -> dict:
    """Closed (r, s) outlines of the three bodies of each valve, and the numbers they rest on."""

    regions = {r["id"]: r for r in fits["regions"]}

    def about(rid):
        return regions[rid]["to_group_datum"]["about_datum_axis"]

    def window(rid):
        r = regions[rid]
        st = r["to_group_datum"]["station_on_datum_axis_mm"]
        lo, hi = r["fit"]["station_range_mm"]
        return st + lo, st + hi

    seats, guides = case["seats"], case["guides"]
    ang = value(seats["angles_deg"])
    t_top, t_bottom = TAN(90.0 - ang["top_cut"]), TAN(90.0 - ang["bottom_cut"])  # dr/ds of each cut
    out = {}
    for name in VALVES:
        v = case["valves"][name]
        seat_fit, throat_fit = about(f"{name}_seat"), about(f"{name}_throat")
        r_m, s_m = 0.5 * seat_fit["diameter_mm"], seat_fit["station_mm"]
        r_t = 0.5 * throat_fit["diameter_mm"]

        def s_cone(r):  # the 45 degree seat cone through the fitted mid-band circle
            return s_m + (r_m - r)

        # valve
        r_v = 0.5 * value(v["head_diameter_mm"])
        r_stem = 0.5 * value(v["stem_diameter_mm"])
        inset, width = value(v["contact_inset_from_face_edge_mm"]), value(v["seat_contact_width_mm"])
        r_o = r_v - inset * COS45
        r_i = r_o - width * COS45
        s_e = s_cone(r_v)
        s_bot = s_e - value(v["margin_thickness_mm"])
        w_f = value(v["face_radial_width_mm"])
        s_face_in = s_e + w_f
        s_tulip = s_face_in + value(v["tulip_length_mm"])
        s_tip = s_bot + value(v["overall_length_mm"])
        valve = [(0.0, s_bot), (r_v, s_bot), (r_v, s_e), (r_v - w_f, s_face_in), (r_stem, s_tulip),
                 (r_stem, s_tip), (0.0, s_tip)]
        if r_i <= r_t:
            raise ValueError(f"{name}: the contact band ({2 * r_i:.2f} mm) falls inside the throat ({2 * r_t:.2f} mm)")

        # seat insert
        r_ins = 0.5 * value(seats["outer_diameter_mm"][name])
        s_o, s_i = s_cone(r_o), s_cone(r_i)
        s_face = s_bot
        r_30 = r_o + (s_o - s_face) * t_top
        knife = r_30 > r_ins
        if knife:
            s_face, r_30 = s_o - (r_ins - r_o) / t_top, r_ins
        s_b = s_i + (r_i - r_t) / t_bottom
        s_ins_top = s_face + value(seats["height_mm"])
        if s_ins_top <= s_b:
            raise ValueError(f"{name}: the insert ends below its bottom cut")
        insert = [(r_t, s_ins_top), (r_ins, s_ins_top), (r_ins, s_face), (r_30, s_face), (r_o, s_o),
                  (r_i, s_i), (r_t, s_b)]

        # guide
        r_gi = 0.5 * value(guides["inside_diameter_mm"])
        r_go = 0.5 * about(GUIDE_OD[name])["diameter_mm"]
        s_g0, s_g1 = window(GUIDE_START[name])[0], window(GUIDE_END[name])[1]
        cone = GUIDE_PORT_CONE[name]
        if cone:
            c = about(cone)
            slope = TAN(c["half_angle_deg"])
            r_tip = 0.5 * c["diameter_mm"] + (s_g0 - c["station_mm"]) * slope
            s_full = c["station_mm"] + (r_go - 0.5 * c["diameter_mm"]) / slope
            guide = [(r_gi, s_g0), (r_tip, s_g0), (r_go, s_full), (r_go, s_g1), (r_gi, s_g1)]
        else:
            guide = [(r_gi, s_g0), (r_go, s_g0), (r_go, s_g1), (r_gi, s_g1)]
        if r_stem >= r_gi:
            raise ValueError(f"{name}: the stem does not enter the guide")
        out[name] = {
            "valve": valve, "insert": insert, "guide": guide,
            "numbers": {
                "seat_mid_band": {"diameter_mm": round(2 * r_m, 3), "station_mm": round(s_m, 3)},
                "contact_band_diameters_mm": [round(2 * r_i, 3), round(2 * r_o, 3)],
                "contact_band_stations_mm": [round(s_o, 3), round(s_i, 3)],
                "valve_face_edge_station_mm": round(s_e, 3),
                "valve_combustion_face_station_mm": round(s_bot, 3),
                "valve_tip_station_mm": round(s_tip, 3),
                "insert_stations_mm": [round(s_face, 3), round(s_ins_top, 3)],
                "insert_diameters_mm": [round(2 * r_t, 3), round(2 * r_ins, 3)],
                "insert_knife_edge_at_chamber_face": knife,
                "bottom_cut_top_station_mm": round(s_b, 3),
                "guide_stations_mm": [round(s_g0, 3), round(s_g1, 3)],
                "guide_diameters_mm": [round(2 * r_gi, 3), round(2 * r_go, 3)],
                "stem_clearance_diametral_mm": round(2 * (r_gi - r_stem), 3),
                "throat_to_valve_ratio": round(r_t / r_v, 3),
            },
        }
    return out


def contact_band_in_window(prof: dict, fits: dict) -> dict:
    """Whether the contact band lies inside the radial extent of the fitted seat window."""

    regions = {r["id"]: r for r in fits["regions"]}
    out = {}
    for name in VALVES:
        seat = regions[f"{name}_seat"]
        a = seat["to_group_datum"]["about_datum_axis"]
        lo, hi = seat["fit"]["station_range_mm"]
        slope = TAN(a["half_angle_deg"])  # signed: negative when the cone narrows toward the cam side
        r_m = 0.5 * a["diameter_mm"]
        r_window = sorted((r_m + lo * slope, r_m + hi * slope))
        band = [0.5 * d for d in prof[name]["numbers"]["contact_band_diameters_mm"]]
        out[name] = {"window_diameters_mm": [round(2 * r, 3) for r in r_window],
                     "band_inside_window": bool(r_window[0] <= band[0] and band[1] <= r_window[1])}
    return out


def solid_of(outline, origin, direction):
    """A solid of revolution of an (r, s) outline about the axis through origin along direction."""

    from build123d import Axis, Plane, Polyline, make_face, revolve

    pts = [(float(r), 0.0, float(s)) for r, s in outline]
    face = make_face(Polyline(*pts, close=True))
    local = revolve(face, Axis.Z, 360.0)
    x = [1.0, 0.0, 0.0] if abs(direction[0]) < 0.9 else [0.0, 1.0, 0.0]
    plane = Plane(origin=tuple(origin), x_dir=tuple(x), z_dir=tuple(direction))
    return plane.location * local


def main(params, out):
    import numpy as np
    from build123d import Compound, export_step, export_stl

    params, out = Path(params), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    case = json.loads((params / "valve-seat-guide-case.json").read_text())
    fits = json.loads((params / "feature-fits.json").read_text())
    prof = profiles(case, fits)
    window = contact_band_in_window(prof, fits)
    bodies, files, lifted = {}, {}, {}
    for name in VALVES:
        datum = fits["group_datums"][name]
        d = np.asarray(datum["axis_direction"], float)
        d /= np.linalg.norm(d)
        p0 = np.asarray(datum["axis_point"], float)
        for part in ("valve", "insert", "guide"):
            bodies[f"{part}_{name}"] = solid_of(prof[name][part], p0, d)
        lift = value(case["valves"][name]["largest_lift_mm"])
        lifted[name] = solid_of([(r, s - lift) for r, s in prof[name]["valve"]], p0, d)
    for key, body in bodies.items():
        if not body.is_valid:
            raise ValueError(f"{key} is not a valid solid")
        path = out / f"{key}.step"
        export_step(body, str(path))
        files[path.name] = sha256_file(path)
    stl = out / "valve-seat-guide-closed.stl"
    export_stl(Compound(list(bodies.values())), str(stl), tolerance=0.01, angular_tolerance=0.1)
    files[stl.name] = sha256_file(stl)
    stl_open = out / "valves-at-largest-lift.stl"
    export_stl(Compound(list(lifted.values())), str(stl_open), tolerance=0.01, angular_tolerance=0.1)
    files[stl_open.name] = sha256_file(stl_open)

    def overlap(a, b):
        inter = a & b
        return round(float(sum(s.volume for s in inter.solids())) if inter else 0.0, 4)

    checks = {}
    for name in VALVES:
        v, i, g = (bodies[f"{p}_{name}"] for p in ("valve", "insert", "guide"))
        checks[name] = {
            "overlap_mm3": {"valve_insert_closed": overlap(v, i), "valve_guide": overlap(v, g),
                            "insert_guide": overlap(i, g), "lifted_valve_insert": overlap(lifted[name], i),
                            "lifted_valve_guide": overlap(lifted[name], g)},
            "distance_valve_to_insert_closed_mm": round(float(v.distance_to(i)), 4),
            "contact_band_in_fitted_seat_window": window[name],
        }
    checks["valve_heads_both_at_largest_lift_distance_mm"] = round(float(
        lifted["valve_y_minus"].distance_to(lifted["valve_y_plus"])), 3)
    checks["valve_heads_closed_distance_mm"] = round(float(
        bodies["valve_valve_y_minus"].distance_to(bodies["valve_valve_y_plus"])), 3)
    # The bodies are consistent when nothing overlaps, closed or at the largest lift, and the two heads
    # stay apart with both at their largest lift. Whether each contact band falls inside the fitted seat
    # window is reported beside it: it compares the declared values with the scan, it does not gate them.
    checks["bodies_consistent"] = bool(
        all(max(checks[name]["overlap_mm3"].values()) < 0.01 for name in VALVES)
        and checks["valve_heads_both_at_largest_lift_distance_mm"] > 0.0)
    checks["contact_bands_inside_fitted_windows"] = {
        name: checks[name]["contact_band_in_fitted_seat_window"]["band_inside_window"] for name in VALVES}
    volumes = {k: round(float(b.volume), 1) for k, b in bodies.items()}
    record = {
        "schema": "935-cad-twin-valve-seat-guide/1",
        "case": "params/valve-seat-guide-case.json",
        "fits": "params/feature-fits.json",
        "hypotheses": ["H09", "H16"],
        "roles": {name: value(case["valves"][name]["role"]) for name in VALVES},
        "bodies": {name: prof[name]["numbers"] for name in VALVES},
        "volumes_mm3": volumes,
        "checks": checks,
        "private_files_sha256": files,
        "claims": "separate solids of revolution on the fitted axes, from published values of other heads, the "
                  "maker's catalogue ranges and explicit assumptions; no dimension of the specimen. The v2 body still "
                  "holds the scanned guides and seats as one solid with the head",
    }
    from twin_common import write_json

    write_json(params / "valve-seat-guide.json", record)
    print(json.dumps({"volumes": volumes, "checks": checks}, indent=1))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(*sys.argv[1:3])
