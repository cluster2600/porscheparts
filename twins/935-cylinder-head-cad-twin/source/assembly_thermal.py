#!/usr/bin/env python3
"""Steady thermal screen of the head in its assembly, under declared hypotheses.

The bare-head screen (sim_thermal.py) holds the chamber wall at one
temperature. In an engine the combustion sets the heat input, the exhaust
valve passes its heat through seat and guide, and the cylinder takes heat at
the joint. This script adds those as hypotheses, every one stated in
``params/assembly-case.json`` and in the register:

* two closed valves, two guides and two spark plugs, as solids of revolution
  about the axes that ``fit_features.py`` fitted, with sizes from the fits and
  from the case file;
* a gas film on the chamber, a hot film in the port of the smaller valve, a
  cool film in the other port, an air film on everything else, and a contact
  film on the deck toward a cylinder at a declared temperature.

The solids are united with the CAD body on its occupancy lattice, the union is
meshed as one domain, and each tetrahedron takes the material of the solid its
centroid lies in. Contacts are therefore perfect: no gap, no contact
resistance. Only the head alloy's conductivity changes between candidates.

    assembly_thermal.py occupancy BODY_OCC_DIR PARAMS_DIR OUT_OCC_DIR
        (twin environment) write the occupancy of body + hypothesis solids

    assembly_thermal.py solve SURFACE.stl PARAMS_DIR BODY_OCC_DIR WORK_DIR SUMMARY.json
        (cadsim image; BODY_OCC_DIR after PARAMS_DIR) mesh once, then solve for each alloy candidate and for
        the load sensitivity of the case file

Nothing here is a measurement, an engine temperature or a material
qualification. Valve, guide and plug shapes are hypotheses, the films are
uncorrelated with any engine, and insert materials are assumed.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "935-cad-twin-assembly-thermal/1"
MATERIALS = ("alloy", "valve", "guide", "plug")
GROUPS = ("chamber_gas", "hot_port", "cool_port", "cylinder_contact", "air")


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def axis_coordinates(points, origin, direction):
    """Station along an axis and distance from it."""

    v = points - np.asarray(origin, dtype=float)
    t = v @ direction
    return t, np.linalg.norm(v - np.outer(t, direction), axis=1)


def build_components(case: dict, fits: dict) -> dict:
    """Valves, guides and plugs as solids of revolution about the fitted axes.

    Every length that the fits do not give comes from the case file and is a
    hypothesis. Stations run along each datum axis, positive toward the cam side.
    """

    regions = {r["id"]: r for r in fits["regions"]}
    datums = fits["group_datums"]

    def about(region):
        return regions[region]["to_group_datum"]["about_datum_axis"]

    def station(region):
        return regions[region]["to_group_datum"]["station_on_datum_axis_mm"]

    valves = {}
    for name, spec in case["valves"].items():
        datum = datums[name]
        seat = about(f"{name}_seat")
        alpha = math.radians(abs(seat["half_angle_deg"]))
        r_seat, t_seat = 0.5 * seat["diameter_mm"], station(f"{name}_seat")
        r_head = r_seat + spec["head_radius_beyond_seat_mid_band_mm"]
        t_face = t_seat - spec["head_radius_beyond_seat_mid_band_mm"] / math.tan(alpha)
        r_inner = r_head - spec["seat_face_radial_width_mm"]
        t_inner = t_face + spec["seat_face_radial_width_mm"] / math.tan(alpha)
        r_stem = 0.5 * about(spec["stem_from_guide_bore"])["diameter_mm"]
        guide_od = 0.5 * about(spec["guide_od_from"])["diameter_mm"]
        valves[name] = {
            "origin": datum["axis_point"], "direction": unit(datum["axis_direction"]).tolist(),
            "alpha_rad": alpha, "r_head": r_head, "t_face": t_face, "margin": spec["margin_thickness_mm"],
            "r_inner": r_inner, "t_inner": t_inner, "tulip_length": spec["tulip_length_mm"], "r_stem": r_stem,
            # The stem is modelled to just above its guide: spring, retainer and stem tip are left out.
            "t_tip": spec["guide_stations_mm"][1] + spec["stem_above_guide_mm"],
            "r_guide": guide_od, "guide_stations": spec["guide_stations_mm"],
            "r_throat": 0.5 * about(f"{name}_throat")["diameter_mm"], "t_seat": t_seat, "r_seat": r_seat,
            "port": spec["port"], "role": spec["role"],
        }
    plugs = {}
    for name, spec in case["plugs"].items():
        datum = datums[name]
        relief = regions[f"{name}_chamber_relief"]
        t_tip = station(f"{name}_chamber_relief") + relief["fit"]["station_range_mm"][1]
        t_seat = station(f"{name}_seat_face")
        plugs[name] = {
            "origin": datum["axis_point"], "direction": unit(datum["axis_direction"]).tolist(),
            "r_thread": 0.5 * about(f"{name}_thread_bore")["diameter_mm"], "t_tip": t_tip, "t_seat": t_seat,
            "r_body": 0.5 * spec["body_diameter_mm"], "t_top": t_seat + spec["body_length_mm"],
        }
    return {"valves": valves, "plugs": plugs}


def valve_mask(points, v, grow: float = 0.0) -> np.ndarray:
    """Inside the valve solid; ``grow`` enlarges it by that much in radius and at both ends."""

    t, rho = axis_coordinates(points, v["origin"], np.asarray(v["direction"]))
    rho = rho - grow
    tan_a = math.tan(v["alpha_rad"])
    disc = (t >= v["t_face"] - v["margin"] - grow) & (t < v["t_face"]) & (rho <= v["r_head"])
    seat = (t >= v["t_face"]) & (t < v["t_inner"]) & (rho <= v["r_head"] - tan_a * (t - v["t_face"]))
    slope = (v["r_inner"] - v["r_stem"]) / v["tulip_length"]
    tulip = (t >= v["t_inner"]) & (t < v["t_inner"] + v["tulip_length"]) & (rho <= v["r_inner"] - slope * (t - v["t_inner"]))
    stem = (t >= v["t_inner"]) & (t <= v["t_tip"] + grow) & (rho <= v["r_stem"])
    return disc | seat | tulip | stem


def guide_mask(points, v) -> np.ndarray:
    t, rho = axis_coordinates(points, v["origin"], np.asarray(v["direction"]))
    return (t >= v["guide_stations"][0]) & (t <= v["guide_stations"][1]) & (rho <= v["r_guide"])


def plug_mask(points, p, grow: float = 0.0) -> np.ndarray:
    t, rho = axis_coordinates(points, p["origin"], np.asarray(p["direction"]))
    rho = rho - grow
    thread = (t >= p["t_tip"] - grow) & (t <= p["t_seat"]) & (rho <= p["r_thread"])
    body = (t > p["t_seat"]) & (t <= p["t_top"] + grow) & (rho <= p["r_body"])
    return thread | body


def material_of(points, comps, in_body=None, skin_mm: float = 0.0) -> np.ndarray:
    """Index into MATERIALS for each point of the united domain: valve over plug over guide over alloy.

    The united surface is extracted at a coarser pitch than the solids are
    defined, so it stands up to ``skin_mm`` off them. A point outside the CAD
    body (``in_body`` false) cannot be head alloy: within that skin of a valve
    or a plug it belongs to that part. Without this, a skin of "alloy" sits on
    each valve face and reads the valve's temperature.
    """

    out = np.zeros(len(points), dtype=np.int8)
    outside = np.zeros(len(points), dtype=bool) if in_body is None else ~np.asarray(in_body)
    for v in comps["valves"].values():
        out[guide_mask(points, v)] = MATERIALS.index("guide")
    for p in comps["plugs"].values():
        out[plug_mask(points, p) | (outside & plug_mask(points, p, skin_mm))] = MATERIALS.index("plug")
    for v in comps["valves"].values():
        out[valve_mask(points, v) | (outside & valve_mask(points, v, skin_mm))] = MATERIALS.index("valve")
    return out


def body_sampler(body_dir: Path):
    """A function telling whether points lie inside the CAD body, from its occupancy lattice."""

    grid = json.loads((Path(body_dir) / "occupancy-grid.json").read_text())
    field = np.load(Path(body_dir) / grid["array"], mmap_mode="r")
    origin = np.array([grid["x0"], grid["y0"], grid["z0"]])

    def inside(points):
        index = np.rint((points - origin) / grid["pitch_mm"]).astype(np.int64)
        valid = np.all((index >= 0) & (index < np.array(field.shape)), axis=1)
        out = np.zeros(len(points), dtype=bool)
        i = index[valid]
        out[valid] = field[i[:, 0], i[:, 1], i[:, 2]] > 0.5
        return out

    return inside


def added_solid(points, comps) -> np.ndarray:
    """Points inside a valve or a plug: the solids added to the body (a guide adds nothing, it renames alloy)."""

    out = np.zeros(len(points), dtype=bool)
    for v in comps["valves"].values():
        out |= valve_mask(points, v)
    for p in comps["plugs"].values():
        out |= plug_mask(points, p)
    return out


def classify_faces(centroid, normal, comps, case, ports) -> np.ndarray:
    """Index into GROUPS for each boundary face of the united domain.

    ``normal`` points out of the solid. A face is on the cylinder contact when
    it looks down from the register recess, between the chamber and the recess wall;
    in a port when it lies behind a valve head inside the throat tube, or looks
    at a port centreline from within the port radius; in the chamber when it
    is inside the chamber radius below the chamber height; otherwise in air.
    """

    geo = case["regions"]
    group = np.full(len(centroid), GROUPS.index("air"), dtype=np.int8)
    r = np.hypot(centroid[:, 0], centroid[:, 1])
    behind = {}
    for name, v in comps["valves"].items():
        t, rho = axis_coordinates(centroid, v["origin"], np.asarray(v["direction"]))
        # Behind the valve head, inside the bowl: the closed valve separates this from the chamber.
        behind[name] = (t > v["t_face"] + geo["behind_head_offset_mm"]) & (t < v["guide_stations"][0] + geo["bowl_past_guide_tip_mm"]) \
            & (rho < v["r_throat"] + geo["bowl_radius_beyond_throat_mm"])
    chamber = (r < geo["chamber_radius_mm"]) & (centroid[:, 2] < geo["chamber_z_max_mm"])
    for mask in behind.values():
        chamber &= ~mask
    group[chamber] = GROUPS.index("chamber_gas")
    for name, v in comps["valves"].items():
        index = GROUPS.index(v["port"])
        for row in ports[v["role"]]:
            to_axis = np.asarray(row["centre"]) - centroid
            distance = np.linalg.norm(to_axis, axis=1)
            facing = np.einsum("ij,ij->i", normal, to_axis) > geo["port_facing_cosine"] * distance
            near = distance < row.get("radius_max_mm", geo["port_radius_default_mm"]) + geo["port_radius_margin_mm"]
            group[near & facing & ~chamber] = index
        group[behind[name]] = index
    # The cylinder seats in the register recess only; the deck plane outside it faces air.
    deck = (centroid[:, 2] < geo["deck_contact_z_max_mm"]) & (normal[:, 2] < -0.9) \
        & (r >= geo["chamber_radius_mm"]) & (r <= geo["register_radius_mm"])
    group[deck] = GROUPS.index("cylinder_contact")
    return group


def occupancy(body_dir, params, out_dir) -> None:
    body_dir, params, out_dir = Path(body_dir), Path(params), Path(out_dir)
    case = json.loads((params / "assembly-case.json").read_text())
    comps = build_components(case, json.loads((params / "feature-fits.json").read_text()))
    grid = json.loads((body_dir / "occupancy-grid.json").read_text())
    body = np.load(body_dir / grid["array"], mmap_mode="r")
    out_dir.mkdir(parents=True, exist_ok=False)
    out = np.lib.format.open_memmap(out_dir / "occupancy-wn.npy", mode="w+", dtype=np.uint8, shape=body.shape)
    h = grid["pitch_mm"]
    x = grid["x0"] + h * np.arange(body.shape[0])
    y = grid["y0"] + h * np.arange(body.shape[1])
    added = 0
    for k0 in range(0, body.shape[2], 8):
        z = grid["z0"] + h * np.arange(k0, min(k0 + 8, body.shape[2]))
        points = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1).reshape(-1, 3)
        solid = added_solid(points, comps).reshape(len(x), len(y), len(z))
        slab = np.asarray(body[:, :, k0:k0 + len(z)]) > 0.5
        added += int((solid & ~slab).sum())
        out[:, :, k0:k0 + len(z)] = slab | solid
    out.flush()
    (out_dir / "occupancy-grid.json").write_text(json.dumps({**grid, "array": "occupancy-wn.npy"}, indent=2) + "\n")
    report = {"voxels_added_by_valves_and_plugs": added, "volume_added_mm3": round(added * h ** 3, 1),
              "solids_reaching_the_grid_boundary": bool(out[:, :, -1].any() and not np.asarray(body[:, :, -1] > 0.5).any())}
    (out_dir / "assembly-occupancy.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


def write_deck(path, tag, xyz, tets, material, faces, group, case, alloy_w_per_mk, load) -> None:
    elem, fid, _ = faces
    films = case["films"]
    with open(path, "w") as fh:
        fh.write("*HEADING\n935 head in its assembly, steady thermal screen (hypothesis case)\n*NODE\n")
        for t, p in zip(tag, xyz):
            fh.write(f"{t},{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}\n")
        fh.write("*NSET,NSET=NALL,GENERATE\n%d,%d,1\n" % (int(tag[0]), int(tag[-1])))
        for index, name in enumerate(MATERIALS):
            fh.write(f"*ELEMENT,TYPE=C3D4,ELSET=E{name.upper()}\n")
            for i in np.flatnonzero(material == index):
                t = tets[i]
                fh.write(f"{i + 1},{t[0]},{t[1]},{t[2]},{t[3]}\n")
        for name in MATERIALS:
            k = alloy_w_per_mk if name == "alloy" else case["materials"][name]["conductivity_W_per_mK"]
            fh.write(f"*MATERIAL,NAME=M{name.upper()}\n*CONDUCTIVITY\n{k * 1.0e-3:g}\n")
            fh.write(f"*SOLID SECTION,ELSET=E{name.upper()},MATERIAL=M{name.upper()}\n")
        fh.write("*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,%g\n" % films["air"]["sink_temperature_C"])
        fh.write("*STEP\n*HEAT TRANSFER,STEADY STATE,SOLVER=ITERATIVE CHOLESKY\n1.,1.\n*FILM\n")
        for e, face, g in zip(elem, fid, group):
            film = films[GROUPS[g]]
            h = film["coefficient_W_per_m2K"] * 1.0e-6 * (load if GROUPS[g] in ("chamber_gas", "hot_port") else 1.0)
            fh.write(f"{e + 1},F{face},{film['sink_temperature_C']:g},{h:g}\n")
        fh.write("*NODE FILE\nNT\n*END STEP\n")


def heat_by_group(temps, tag, xyz, faces, group, case, load) -> dict:
    """Heat leaving the solid through each film group, recomputed from the nodal temperatures."""

    _, _, tri = faces
    index = np.searchsorted(tag, tri)
    p = xyz[index]
    area = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    mean = temps[index].mean(axis=1)
    out = {}
    for g, name in enumerate(GROUPS):
        film = case["films"][name]
        h = film["coefficient_W_per_m2K"] * 1.0e-6 * (load if name in ("chamber_gas", "hot_port") else 1.0)
        sel = group == g
        out[name] = {"area_mm2": round(float(area[sel].sum()), 1),
                     "heat_out_W": round(float((h * area[sel] * (mean[sel] - film["sink_temperature_C"])).sum()), 2)}
    return out


def zones(xyz, node_is_alloy, comps, case) -> dict:
    """Node sets of the head alloy where the peak temperatures are read."""

    out = {"alloy": node_is_alloy}
    seats = {}
    for name, v in comps["valves"].items():
        t, rho = axis_coordinates(xyz, v["origin"], np.asarray(v["direction"]))
        band = (np.abs(t - v["t_seat"]) < case["zones"]["seat_half_length_mm"]) \
            & (np.abs(rho - v["r_seat"]) < case["zones"]["seat_radial_depth_mm"])
        out[f"{v['role']}_seat"] = node_is_alloy & band
        seats[name] = (np.abs(t - v["t_seat"]) < case["zones"]["bridge_half_length_mm"]) \
            & (rho < v["r_seat"] + case["zones"]["bridge_reach_mm"])
    # The bridge is the land between the two seats: alloy close to both seat circles at once.
    out["valve_bridge"] = node_is_alloy & np.logical_and.reduce(list(seats.values()))
    plug = np.zeros(len(xyz), dtype=bool)
    for p in comps["plugs"].values():
        t, rho = axis_coordinates(xyz, p["origin"], np.asarray(p["direction"]))
        plug |= (t >= p["t_tip"]) & (t <= p["t_seat"]) & (rho < p["r_thread"] + case["zones"]["plug_boss_depth_mm"])
    out["plug_bosses"] = node_is_alloy & plug
    return out


def solve(surface, params, body_dir, work, summary, only=None) -> None:
    import sim_thermal

    params, work = Path(params), Path(work)
    case = json.loads((params / "assembly-case.json").read_text())
    fits = json.loads((params / "feature-fits.json").read_text())
    candidates = json.loads((params / "alloy-candidates.json").read_text())["candidates"]
    port_fit = {p["name"]: p["station_detail"] for p in json.loads((params / "port-fit.json").read_text())["ports"]}
    comps = build_components(case, fits)
    ports = {v["role"]: port_fit[case["valves"][name]["port_fit_name"]] for name, v in comps["valves"].items()}
    work.mkdir(parents=True, exist_ok=False)

    tag, xyz, tets, quality, mesh_s = sim_thermal.mesh(surface, work, float(case["mesh_size_max_mm"]))
    node = np.searchsorted(tag, tets)
    corner = xyz[node]
    centre = corner.mean(axis=1)
    material = material_of(centre, comps, body_sampler(body_dir)(centre), float(case["material_skin_mm"]))
    volume = np.abs(np.einsum("ij,ij->i", np.cross(corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0]),
                              corner[:, 3] - corner[:, 0])) / 6.0
    faces = sim_thermal.boundary_faces(tets)
    elem, _, tri = faces
    p = xyz[np.searchsorted(tag, tri)]
    centroid = p.mean(axis=1)
    normal = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    inward = np.einsum("ij,ij->i", normal, corner[elem].mean(axis=1) - centroid) > 0
    normal[inward] *= -1.0
    group = classify_faces(centroid, normal, comps, case, ports)
    # A node counts as head alloy only if every tetrahedron around it is alloy: the nodes shared
    # with a valve, a guide or a plug carry the contact temperature and are reported with those parts.
    node_is_alloy = np.ones(len(tag), dtype=bool)
    node_is_alloy[np.unique(node[material != MATERIALS.index("alloy")])] = False
    zone = zones(xyz, node_is_alloy, comps, case)
    node_is_valve = {}
    for name, v in comps["valves"].items():
        node_is_valve[v["role"]] = valve_mask(xyz, v)

    def run(label, alloy_k, load):
        job = work / label
        job.mkdir()
        write_deck(job / "head.inp", tag, xyz, tets, material, faces, group, case, alloy_k, load)
        done = subprocess.run(["ccx", "-i", "head"], cwd=job, capture_output=True, text=True,
                              env={"OMP_NUM_THREADS": "1", "CCX_NPROC_EQUATION_SOLVER": "1", "PATH": "/usr/bin:/bin"})
        (job / "ccx.log").write_text(done.stdout + done.stderr)
        if done.returncode or not (job / "head.frd").exists():
            raise SystemExit(f"{label}: ccx returned {done.returncode}")
        temps = sim_thermal.read_frd_temperatures(job / "head.frd")
        heat = heat_by_group(temps, tag, xyz, faces, group, case, load)
        into = -sum(v["heat_out_W"] for v in heat.values() if v["heat_out_W"] < 0)
        result = {"alloy_conductivity_W_per_mK": alloy_k, "load_factor_on_gas_films": load,
                  "peak_C": {name: round(float(temps[sel].max()), 2) for name, sel in zone.items() if sel.any()},
                  "peak_alloy_at_mm": [round(float(x), 1) for x in xyz[np.flatnonzero(node_is_alloy)[
                      int(np.argmax(temps[node_is_alloy]))]]],
                  "mean_alloy_C": round(float(temps[node_is_alloy].mean()), 2),
                  "valve_peak_C": {name: round(float(temps[sel].max()), 2) for name, sel in node_is_valve.items()},
                  "heat_out_W_by_group": {name: v["heat_out_W"] for name, v in heat.items()},
                  "heat_into_the_assembly_W": round(into, 2),
                  "energy_imbalance_relative": round(abs(sum(v["heat_out_W"] for v in heat.values())) / into, 6)}
        for name in ("head.frd", "head.dat", "head.12d", "head.cvg", "head.sta", "head.inp"):
            (job / name).unlink(missing_ok=True)
        print(label, result["peak_C"], result["heat_into_the_assembly_W"], flush=True)
        return result, {name: v["area_mm2"] for name, v in heat.items()}

    solved, areas = {}, None
    if only is not None:                                # one exploratory solve: no ranking is drawn from it
        candidates = [c for c in candidates if c["conductivity_W_per_mK"] == float(only)]
        case = {**case, "load_sensitivity_factors": []}
    for k in sorted({c["conductivity_W_per_mK"] for c in candidates}):
        solved[k], areas = run(f"k{k:g}", k, 1.0)
    rows = [{"id": c["id"], "alloy": c["alloy"], "condition": c["condition"], "method": c["method"],
             "verification": c["verification"], **solved[c["conductivity_W_per_mK"]]} for c in candidates]
    rows.sort(key=lambda r: (r["peak_C"]["alloy"], r["id"]))
    sensitivity = []
    for load in case["load_sensitivity_factors"]:
        for k in (min(solved), max(solved)):
            sensitivity.append(run(f"load{load:g}-k{k:g}", k, load)[0])

    Path(summary).write_text(json.dumps({
        "schema": SCHEMA,
        "exploratory_single_solve": only is not None,
        "case_file": "params/assembly-case.json",
        "mesh": {"mesher": "Gmsh HXT", "size_max_mm": case["mesh_size_max_mm"], "nodes": int(len(tag)), "tets": int(len(tets)),
                 "share_with_minSICN_below_0p1": round(float((quality < 0.1).mean()), 6),
                 "volume_mm3_by_material": {name: round(float(volume[material == i].sum()), 1) for i, name in enumerate(MATERIALS)},
                 "tets_by_material": {name: int((material == i).sum()) for i, name in enumerate(MATERIALS)}},
        "film_area_mm2_by_group": areas,
        "zone_nodes": {name: int(sel.sum()) for name, sel in zone.items()},
        "distinct_conductivities_solved": len(solved),
        "ranking_by_peak_alloy_temperature": rows,
        "spread": {"peak_alloy_C_best_minus_worst": round(rows[0]["peak_C"]["alloy"] - rows[-1]["peak_C"]["alloy"], 2),
                   "valve_bridge_C_best_minus_worst": round(min(r["peak_C"]["valve_bridge"] for r in rows)
                                                             - max(r["peak_C"]["valve_bridge"] for r in rows), 2)},
        "load_sensitivity": sensitivity,
        "claims": "a ranking under one declared hypothesis case: hypothetical valves, guides and plugs in perfect "
                  "contact, films uncorrelated with any engine, room-temperature conductivities. Not an engine "
                  "temperature, not a material qualification; strength at temperature is not considered",
    }, indent=2) + "\n")


if __name__ == "__main__":
    {"occupancy": occupancy, "solve": solve}[sys.argv[1]](*sys.argv[2:])
