#!/usr/bin/env python3
"""Heat paths added to the assembly thermal screen: a barrel, oil, and a conductance at each joint (#701).

The first assembly screen (assembly_thermal.py) put valves, guides and plugs in
perfect contact with the head, oil on the spring pockets only, and the cylinder
as one film on the register recess. This script keeps every value of that case
and adds, from ``params/assembly-heat-paths-case.json``:

* a barrel: a tube on the bore axis whose collar fills the fitted register
  recess, with its bore on the fitted chamber shoulder and its heights from a
  published replacement cylinder of another 911 engine; a gas film on its bore,
  an effective fin film on its finned length, and a crankcase contact below;
* oil where it reaches: the spring pockets as before, and the cam-housing face;
* a contact conductance at each joint: valve seats, valve stems, guides, plugs
  and the barrel collar.

Labels by centroid leave islands of a few tetrahedra; each joins the material
it shares most faces with. A joint is then made by giving each material its own
copy of the nodes it shares with another and tying the two copies with a
CalculiX node-to-surface contact pair (face-based slave surface) and a gap
conductance, in a plain heat-transfer step. The meshed interface follows the
tetrahedra and is larger than the smooth surface it stands for, so each joint's
conductance is scaled by the area the interface projects onto the analytic part
surface.

    assembly_heat_paths.py occupancy BODY_OCC_DIR PARAMS_DIR OUT_OCC_DIR
        (twin environment) body + valves + plugs + barrel on a grid extended below the deck

    assembly_heat_paths.py prepare SURFACE.stl PARAMS_DIR BODY_OCC_DIR WORK_DIR
        (cadsim image) mesh, materials, film groups, joints, split nodes: WORK_DIR/prepared.npz

    assembly_heat_paths.py solve WORK_DIR PARAMS_DIR SUMMARY.json [JOBS]
        (cadsim image) the four variants, the sensitivity sweep and the perfect-contact witness

    assembly_heat_paths.py reference WORK_DIR PARAMS_DIR SUMMARY.json OUT.json
        (cadsim image) the reference configuration of SUMMARY on another prepared mesh

    assembly_heat_paths.py witness FOLDER OUT.json
        (cadsim image) one joint across a jagged plane and cylinder, against the closed form

    assembly_heat_paths.py probe WORK_DIR PARAMS_DIR OUT.json
        (cadsim image) one uncalibrated solve, split and with shared nodes: time, heat, balances

    assembly_heat_paths.py record SUMMARY.json BASE_WORK_DIR FINE.json AGAIN.json WITNESS.json OUT.json
        (twin environment) the committed record and media/heat-paths.png

Nothing here is a measurement, an engine temperature or a material qualification.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assembly_thermal as at  # noqa: E402

SCHEMA = "935-cad-twin-assembly-heat-paths/1"
MATERIALS = at.MATERIALS + ("barrel",)
GROUPS = at.GROUPS + ("cam_housing", "barrel_gas", "barrel_fins", "crankcase")
JOINTS = ("seat", "stem", "guide", "plug", "deck")
# C3D4 face id -> local node indices (sim_thermal.C3D4_FACES inverted).
FACE_NODES = {1: (0, 1, 2), 2: (0, 1, 3), 3: (1, 2, 3), 4: (0, 2, 3)}


def load(params: Path) -> tuple:
    params = Path(params)
    base = json.loads((params / "assembly-case.json").read_text())
    case = json.loads((params / "assembly-heat-paths-case.json").read_text())
    comps = at.build_components(base, json.loads((params / "feature-fits.json").read_text()))
    return base, case, comps, barrel_geometry(case)


def barrel_geometry(case: dict) -> dict:
    b = case["barrel"]
    top = b["top_z_mm"]["value"]
    return {"r_bore": b["bore_radius_mm"]["value"], "r_collar": b["collar_radius_mm"]["value"],
            "r_register": 0.5 * b["register_diameter_mm"]["value"], "z_top": top,
            "z_shoulder": top - b["collar_height_mm"]["value"], "z_bottom": top - b["total_height_mm"]["value"],
            "overlap": b["overlap_into_head_mm"]["value"]}


def barrel_mask(points, g, grow: float = 0.0) -> np.ndarray:
    """Inside the barrel. ``grow`` widens it inward, outward below the deck and at the bottom, never at the deck."""

    r = np.hypot(points[:, 0], points[:, 1])
    z = points[:, 2]
    outward = np.where(z < -grow, grow, 0.0)
    collar = (z <= g["z_top"] + g["overlap"]) & (z > g["z_shoulder"]) & (r <= g["r_collar"] + outward)
    register = (z <= g["z_shoulder"]) & (z >= g["z_bottom"] - grow) & (r <= g["r_register"] + outward)
    return (collar | register) & (r >= g["r_bore"] - grow)


def material_of(points, comps, g, in_body, skin_mm: float) -> np.ndarray:
    """Index into MATERIALS: the first screen's rule, then barrel for what lies outside the body in the barrel."""

    out = at.material_of(points, comps, in_body, skin_mm)
    out[(out == 0) & ~np.asarray(in_body) & barrel_mask(points, g, skin_mm)] = MATERIALS.index("barrel")
    return out


def occupancy(body_dir, params, out_dir) -> None:
    """Body, valves, plugs and barrel on the body grid, extended downward by whole 4-voxel blocks."""

    body_dir, out_dir = Path(body_dir), Path(out_dir)
    _, case, comps, g = load(params)
    grid = json.loads((body_dir / "occupancy-grid.json").read_text())
    body = np.load(body_dir / grid["array"], mmap_mode="r")
    h = grid["pitch_mm"]
    pad = int(math.ceil((grid["z0"] - (g["z_bottom"] - 2.0)) / (4 * h))) * 4
    shape = (body.shape[0], body.shape[1], body.shape[2] + pad)
    out_dir.mkdir(parents=True, exist_ok=False)
    out = np.lib.format.open_memmap(out_dir / "occupancy-wn.npy", mode="w+", dtype=np.uint8, shape=shape)
    x = grid["x0"] + h * np.arange(shape[0])
    y = grid["y0"] + h * np.arange(shape[1])
    z0 = grid["z0"] - pad * h
    added = {"valves_and_plugs": 0, "barrel": 0}
    for k0 in range(0, shape[2], 8):
        k1 = min(k0 + 8, shape[2])
        z = z0 + h * np.arange(k0, k1)
        points = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1).reshape(-1, 3)
        parts = at.added_solid(points, comps).reshape(len(x), len(y), len(z))
        barrel = barrel_mask(points, g).reshape(len(x), len(y), len(z))
        slab = np.zeros((len(x), len(y), len(z)), dtype=bool)
        lo, hi = max(k0 - pad, 0), max(k1 - pad, 0)
        if hi > lo:
            slab[:, :, (lo + pad) - k0:] = np.asarray(body[:, :, lo:hi]) > 0.5
        added["valves_and_plugs"] += int((parts & ~slab).sum())
        added["barrel"] += int((barrel & ~slab & ~parts).sum())
        out[:, :, k0:k1] = slab | parts | barrel
    out.flush()
    (out_dir / "occupancy-grid.json").write_text(json.dumps(
        {**grid, "z0": z0, "shape": list(shape), "array": "occupancy-wn.npy"}, indent=2) + "\n")
    report = {"padding_voxels_below": pad, "voxels_added": added,
              "volume_added_mm3": {k: round(v * h ** 3, 1) for k, v in added.items()},
              "solids_reaching_the_grid_boundary": bool(np.asarray(out[:, :, 0]).any() or np.asarray(out[:, :, -1]).any()
                                                       or np.asarray(out[0]).any() or np.asarray(out[-1]).any())}
    (out_dir / "assembly-occupancy.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


# ---------------------------------------------------------------- profiles of the parts, for the joint areas

def _segments_valve(v):
    t0, m, L = v["t_face"], v["margin"], v["tulip_length"]
    return [("face", (t0 - m, 0.0), (t0 - m, v["r_head"])), ("rim", (t0 - m, v["r_head"]), (t0, v["r_head"])),
            ("seat", (t0, v["r_head"]), (v["t_inner"], v["r_inner"])),
            ("tulip", (v["t_inner"], v["r_inner"]), (v["t_inner"] + L, v["r_stem"])),
            ("stem", (v["t_inner"] + L, v["r_stem"]), (v["t_tip"], v["r_stem"])), ("tip", (v["t_tip"], v["r_stem"]), (v["t_tip"], 0.0))]


def _segments_guide(v):
    s0, s1 = v["guide_stations"]
    return [("end", (s0, v["r_stem"]), (s0, v["r_guide"])), ("od", (s0, v["r_guide"]), (s1, v["r_guide"])),
            ("end", (s1, v["r_guide"]), (s1, v["r_stem"]))]


def _segments_plug(p):
    return [("tip", (p["t_tip"], 0.0), (p["t_tip"], p["r_thread"])), ("thread", (p["t_tip"], p["r_thread"]), (p["t_seat"], p["r_thread"])),
            ("seat", (p["t_seat"], p["r_thread"]), (p["t_seat"], p["r_body"])), ("body", (p["t_seat"], p["r_body"]), (p["t_top"], p["r_body"])),
            ("top", (p["t_top"], p["r_body"]), (p["t_top"], 0.0))]


def _segments_barrel(g):
    return [("top", (g["z_top"], g["r_bore"]), (g["z_top"], g["r_collar"])), ("collar", (g["z_top"], g["r_collar"]), (g["z_shoulder"], g["r_collar"])),
            ("shoulder", (g["z_shoulder"], g["r_collar"]), (g["z_shoulder"], g["r_register"])),
            ("register", (g["z_shoulder"], g["r_register"]), (g["z_bottom"], g["r_register"])),
            ("bottom", (g["z_bottom"], g["r_register"]), (g["z_bottom"], g["r_bore"])), ("bore", (g["z_bottom"], g["r_bore"]), (g["z_top"], g["r_bore"]))]


def profiles(comps, g) -> dict:
    """Solids of revolution as (origin, axis, segments in the station/radius half-plane), by material."""

    out = {"valve": [], "guide": [], "plug": [], "barrel": [((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), _segments_barrel(g))]}
    for v in comps["valves"].values():
        out["valve"].append((v["origin"], v["direction"], _segments_valve(v)))
        out["guide"].append((v["origin"], v["direction"], _segments_guide(v)))
    for p in comps["plugs"].values():
        out["plug"].append((p["origin"], p["direction"], _segments_plug(p)))
    return out


def nearest_segment(points, solids) -> tuple:
    """Name and 3D normal (unsigned) of the profile segment nearest each point, over every solid of one kind."""

    best = np.full(len(points), np.inf)
    name = np.empty(len(points), dtype=object)
    normal = np.zeros((len(points), 3))
    for origin, direction, segments in solids:
        d = np.asarray(direction, dtype=float)
        t, rho = at.axis_coordinates(points, origin, d)
        radial = points - np.asarray(origin, dtype=float) - np.outer(t, d)
        radial /= np.maximum(np.linalg.norm(radial, axis=1), 1e-12)[:, None]
        for label, a, b in segments:
            a, b = np.asarray(a), np.asarray(b)
            e = b - a
            s = np.clip(((t - a[0]) * e[0] + (rho - a[1]) * e[1]) / max(e @ e, 1e-12), 0.0, 1.0)
            dist = np.hypot(t - (a[0] + s * e[0]), rho - (a[1] + s * e[1]))
            closer = dist < best
            n2 = np.array([-e[1], e[0]]) / np.linalg.norm(e)
            best[closer], name[closer] = dist[closer], label
            normal[closer] = n2[0] * d + n2[1] * radial[closer]
    return name, normal, best


# ---------------------------------------------------------------- mesh topology

def face_pairs(tets) -> tuple:
    """Boundary faces (element, face id) and internal face pairs (element a, face a, element b, face b)."""

    loc = list(FACE_NODES.items())
    tri = np.concatenate([tets[:, list(nodes)] for _, nodes in loc])
    elem = np.tile(np.arange(len(tets)), len(loc))
    fid = np.repeat([f for f, _ in loc], len(tets)).astype(np.int8)
    key = np.sort(tri, axis=1)
    del tri
    order = np.lexsort((key[:, 2], key[:, 1], key[:, 0]))
    key, elem, fid = key[order], elem[order], fid[order]
    same = np.all(key[1:] == key[:-1], axis=1)
    del key
    first = np.flatnonzero(same)
    paired = np.zeros(len(elem), dtype=bool)
    paired[first] = paired[first + 1] = True
    return (elem[~paired], fid[~paired]), (elem[first], fid[first], elem[first + 1], fid[first + 1])


def split_nodes(tets, material) -> tuple:
    """Give each material its own copy of every node it shares with another: new tets and the source of each node."""

    n = int(tets.max()) + 1
    owner = np.full(n, -1, dtype=np.int16)
    new = tets.copy()
    sources = [np.arange(n)]
    next_id = n
    for m in np.unique(material):
        sel = np.flatnonzero(material == m)
        used = np.unique(tets[sel])
        owner[used[owner[used] == -1]] = m
        taken = used[owner[used] != m]
        lut = np.full(n, -1, dtype=np.int64)
        lut[taken] = np.arange(next_id, next_id + len(taken))
        next_id += len(taken)
        sources.append(taken)
        block = lut[tets[sel]]
        new[sel] = np.where(block >= 0, block, tets[sel])
    return new, np.concatenate(sources)


PARTS_PER_MATERIAL = {"alloy": 1, "valve": 2, "guide": 2, "plug": 2, "barrel": 1}


def merge_islands(n_tets, material, pairs) -> tuple:
    """Give every stray component of a material the material of the neighbours it shares most faces with.

    Labels by centroid leave islands of a few tetrahedra (a valve sliver in the port, alloy between a
    stem and its guide). After the split an island touches the rest only through joints, and one that a
    joint does not reach floats at its film's sink temperature. Each material keeps as many components
    as it has parts: one head, two valves, two guides, two plugs, one barrel.
    """

    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    ea, eb = pairs
    material = material.copy()
    moved = {name: 0 for name in MATERIALS}
    for _ in range(4):
        same = material[ea] == material[eb]
        graph = coo_matrix((np.ones(int(same.sum()), dtype=np.int8), (ea[same], eb[same])), shape=(n_tets, n_tets))
        _, label = connected_components(graph, directed=False)
        size = np.bincount(label)
        comp_material = np.zeros(len(size), dtype=np.int8)
        comp_material[label] = material
        island = np.zeros(len(size), dtype=bool)
        for m, name in enumerate(MATERIALS):
            comps = np.flatnonzero(comp_material == m)
            island[comps[np.argsort(-size[comps])][PARTS_PER_MATERIAL[name]:]] = True
        if not island.any():
            break
        a, b = ea[~same], eb[~same]
        comp = np.concatenate([label[a][island[label[a]]], label[b][island[label[b]]]])
        vote = np.concatenate([material[b][island[label[a]]], material[a][island[label[b]]]]).astype(np.int64)
        tally = np.zeros((len(size), len(MATERIALS)), dtype=np.int64)
        np.add.at(tally, (comp, vote), 1)
        voted = island & (tally.sum(axis=1) > 0)
        new = np.where(voted, tally.argmax(axis=1), comp_material).astype(np.int8)
        change = voted[label]
        for m, name in enumerate(MATERIALS):
            moved[name] += int((change & (material == m)).sum())
        material[change] = new[label[change]]
    return material, {"tets_relabelled_from": moved, "islands_left": int(island.sum()) if island.any() else 0}


def face_geometry(xyz, tets, elem, fid) -> tuple:
    """Centroid, unit normal pointing out of the element, and area of element faces."""

    local = np.array([FACE_NODES[int(f)] for f in range(1, 5)])
    nodes = tets[elem[:, None], local[fid - 1]]
    p = xyz[nodes]
    c = p.mean(axis=1)
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    n /= np.maximum(2.0 * area, 1e-30)[:, None]
    inward = np.einsum("ij,ij->i", n, xyz[tets[elem]].mean(axis=1) - c) > 0
    n[inward] *= -1.0
    return c, n, area, nodes


def joint_of(mat_a, mat_b, segment_name) -> np.ndarray:
    """Joint name of each interface face from its two materials (and, valve on alloy, the valve segment it faces)."""

    names = np.full(len(mat_a), "", dtype=object)
    pair = {frozenset(("valve", "alloy")): "seat", frozenset(("valve", "guide")): "stem",
            frozenset(("guide", "alloy")): "guide", frozenset(("plug", "alloy")): "plug",
            frozenset(("barrel", "alloy")): "deck"}
    for i, (a, b) in enumerate(zip(mat_a, mat_b)):
        names[i] = pair.get(frozenset((MATERIALS[a], MATERIALS[b])), "other")
    stem = (names == "seat") & np.isin(segment_name, ["stem", "tip"])
    names[stem] = "stem"
    return names


def classify(centroid, normal, owner, comps, g, base, case, ports) -> np.ndarray:
    """Index into GROUPS for each boundary face: the first screen's groups, then the cam housing, then the barrel."""

    group = at.classify_faces(centroid, normal, comps, base, ports).astype(np.int8)
    reg = case["regions"]
    well = np.zeros(len(centroid), dtype=bool)
    for p in comps["plugs"].values():
        t, rho = at.axis_coordinates(centroid, p["origin"], np.asarray(p["direction"]))
        well |= (t > p["t_seat"]) & (rho < reg["plug_well_radius_mm"])
    for v in comps["valves"].values():
        # The rest of the spring pocket: above the seat, near the axis, looking toward it.
        d = np.asarray(v["direction"])
        t, rho = at.axis_coordinates(centroid, v["origin"], d)
        to_axis = np.asarray(v["origin"]) + np.outer(t, d) - centroid
        toward = np.einsum("ij,ij->i", normal, to_axis) > 0.0
        mouth = (t > v["t_spring_seat"] - base["regions"]["oil_below_spring_seat_mm"]) & (rho < reg["pocket_mouth_radius_mm"])
        group[mouth & toward & ~well & (group == GROUPS.index("air"))] = GROUPS.index("oil")
    cam = (centroid[:, 2] >= reg["cam_face_z_mm"] - reg["cam_face_band_mm"]) & ~well & (group != GROUPS.index("oil"))
    group[cam] = GROUPS.index("cam_housing")
    on_barrel = owner == MATERIALS.index("barrel")
    r = np.hypot(centroid[:, 0], centroid[:, 1])
    tol = reg["barrel_face_tolerance_mm"]
    radial = (normal[:, 0] * centroid[:, 0] + normal[:, 1] * centroid[:, 1]) / np.maximum(r, 1e-9)
    bore = on_barrel & (r < g["r_bore"] + tol) & (radial < 0.0)
    crank = on_barrel & ~bore & (centroid[:, 2] <= g["z_shoulder"] + tol)
    fins = on_barrel & ~bore & ~crank & (centroid[:, 2] < 0.0)
    group[on_barrel] = GROUPS.index("air")
    group[bore] = GROUPS.index("barrel_gas")
    group[crank] = GROUPS.index("crankcase")
    group[fins] = GROUPS.index("barrel_fins")
    return group


def prepare(surface, params, body_dir, work) -> None:
    import sim_thermal

    params, work = Path(params), Path(work)
    base, case, comps, g = load(params)
    fits_ports = {p["name"]: p["station_detail"] for p in json.loads((params / "port-fit.json").read_text())["ports"]}
    ports = {v["role"]: fits_ports[base["valves"][name]["port_fit_name"]] for name, v in comps["valves"].items()}
    work.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    tag, xyz, tets_tag, quality, mesh_s = sim_thermal.mesh(surface, work, float(case["mesh"]["size_max_mm"]))
    tets = np.searchsorted(tag, tets_tag).astype(np.int64)
    del tets_tag
    centre = xyz[tets].mean(axis=1)
    in_body = at.body_sampler(body_dir)(centre)
    material = material_of(centre, comps, g, in_body, float(base["material_skin_mm"])).astype(np.int8)
    corner = xyz[tets]
    volume = np.abs(np.einsum("ij,ij->i", np.cross(corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0]),
                              corner[:, 3] - corner[:, 0])) / 6.0
    del corner, centre
    (b_elem, b_fid), (ea, fa, eb, fb) = face_pairs(tets)
    material, islands = merge_islands(len(tets), material, (ea, eb))
    c, n, area, _ = face_geometry(xyz, tets, b_elem, b_fid)
    group = classify(c, n, material[b_elem], comps, g, base, case, ports)
    # Interfaces: internal faces between two materials. The part is the slave side; a valve is the slave on a guide.
    diff = material[ea] != material[eb]
    ea, fa, eb, fb = ea[diff], fa[diff], eb[diff], fb[diff]
    # The slave side: valve over plug and barrel over guide over alloy.
    priority = np.array([{"alloy": 0, "guide": 1, "plug": 2, "barrel": 2, "valve": 3}[m] for m in MATERIALS])
    swap = priority[material[eb]] > priority[material[ea]]
    s_e, s_f, m_e, m_f = np.where(swap, eb, ea), np.where(swap, fb, fa), np.where(swap, ea, eb), np.where(swap, fa, fb)
    s_mat, m_mat = material[s_e], material[m_e]
    ic, inormal, iarea, _ = face_geometry(xyz, tets, s_e, s_f)
    sols = profiles(comps, g)
    seg = np.empty(len(s_e), dtype=object)
    true_n = np.zeros((len(s_e), 3))
    off = np.zeros(len(s_e))
    for name in ("valve", "guide", "plug", "barrel"):
        sel = s_mat == MATERIALS.index(name)
        if sel.any():
            seg[sel], true_n[sel], off[sel] = nearest_segment(ic[sel], sols[name])
    joint = joint_of(s_mat, m_mat, seg)
    cosine = np.abs(np.einsum("ij,ij->i", inormal, true_n))
    joints = {}
    for name in JOINTS + ("other",):
        sel = joint == name
        if not sel.any():
            continue
        joints[name] = {"faces": int(sel.sum()), "meshed_area_mm2": round(float(iarea[sel].sum()), 1),
                        "projected_area_mm2": round(float((iarea[sel] * cosine[sel]).sum()), 1),
                        "area_factor": round(float((iarea[sel] * cosine[sel]).sum() / iarea[sel].sum()), 4),
                        "distance_to_part_surface_mm_p95": round(float(np.percentile(off[sel], 95)), 3),
                        "by_segment_mm2": {str(k): round(float(iarea[sel & (seg == k)].sum()), 1) for k in sorted(set(seg[sel]))}}
    if "other" in joints:
        # Parts that touch only inside the extraction skin (a valve head on a plug tip): left insulated, never tied.
        sel = joint == "other"
        pairs = sorted({"/".join(sorted((MATERIALS[a], MATERIALS[b]))) for a, b in zip(s_mat[sel], m_mat[sel])})
        joints["other"].update(pairs=pairs, treatment="insulated: no contact pair")
        if joints["other"]["meshed_area_mm2"] > 10.0:
            raise SystemExit(f"interfaces between materials that share no declared joint: {joints['other']}")
    split, source = split_nodes(tets, material)
    joint_index = np.array([JOINTS.index(j) if j in JOINTS else -1 for j in joint], dtype=np.int8)
    np.savez(work / "prepared.npz", xyz=xyz, source=source, tets=tets.astype(np.int32), split=split.astype(np.int32),
             material=material, volume=volume, b_elem=b_elem.astype(np.int32), b_fid=b_fid, group=group,
             s_elem=s_e.astype(np.int32), s_fid=s_f, m_elem=m_e.astype(np.int32), m_fid=m_f, joint=joint_index)
    report = {
        "surface": str(surface), "mesher": "Gmsh HXT", "size_max_mm": case["mesh"]["size_max_mm"], "mesh_s": round(mesh_s, 1),
        "nodes": int(len(xyz)), "nodes_after_split": int(len(source)), "tets": int(len(tets)),
        "share_with_minSICN_below_0p1": round(float((quality < 0.1).mean()), 6),
        "tets_by_material": {name: int((material == i).sum()) for i, name in enumerate(MATERIALS)},
        "volume_mm3_by_material": {name: round(float(volume[material == i].sum()), 1) for i, name in enumerate(MATERIALS)},
        "film_area_mm2_by_group": {name: round(float(area[group == i].sum()), 1) for i, name in enumerate(GROUPS)},
        "joints": joints, "islands": islands, "prepare_s": round(time.time() - t0, 1)}
    (work / "prepared.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


# ---------------------------------------------------------------- the CalculiX deck

def _lines(fh, values, per=12):
    values = [str(v) for v in values]
    for i in range(0, len(values), per):
        fh.write(",".join(values[i:i + per]) + "\n")


def write_mesh(path, d, perfect: bool = False) -> None:
    """Nodes, elements by material, film element sets by group and face, and the contact surfaces of each joint.

    ``perfect`` writes the unsplit mesh: every joint is perfect contact through shared nodes, no surfaces.
    """

    xyz = d["xyz"] if perfect else d["xyz"][d["source"]]
    tets = d["tets"] if perfect else d["split"]
    material = d["material"]
    with open(path, "w") as fh:
        fh.write("*NODE\n")
        np.savetxt(fh, np.column_stack([np.arange(1, len(xyz) + 1), xyz]), fmt="%d,%.6f,%.6f,%.6f")
        fh.write("*NSET,NSET=NALL,GENERATE\n1,%d,1\n" % len(xyz))
        for i, name in enumerate(MATERIALS):
            sel = np.flatnonzero(material == i)
            fh.write(f"*ELEMENT,TYPE=C3D4,ELSET=E{name.upper()}\n")
            np.savetxt(fh, np.column_stack([sel + 1, tets[sel] + 1]), fmt="%d,%d,%d,%d,%d")
        for gi, name in enumerate(GROUPS):
            for f in range(1, 5):
                sel = d["b_elem"][(d["group"] == gi) & (d["b_fid"] == f)]
                if len(sel):
                    fh.write(f"*ELSET,ELSET=F{gi}S{f}\n")
                    _lines(fh, np.sort(sel) + 1)
        if perfect:
            return
        for ji, name in enumerate(JOINTS):
            sel = d["joint"] == ji
            if not sel.any():
                continue
            for side, e, f in (("S", d["s_elem"], d["s_fid"]), ("M", d["m_elem"], d["m_fid"])):
                fh.write(f"*SURFACE,NAME={side}{name.upper()},TYPE=ELEMENT\n")
                np.savetxt(fh, np.column_stack([e[sel] + 1, f[sel]]), fmt="%d,S%d")


def write_job(path, mesh_name, d, conductivity, films, joints, perfect: bool = False) -> None:
    """One solve: materials, joint conductances (W/mm2 K, already scaled by the area factor), films by element set."""

    with open(path, "w") as fh:
        fh.write("*HEADING\n935 head, assembly with heat paths: steady thermal screen (hypothesis case)\n")
        fh.write(f"*INCLUDE,INPUT={mesh_name}\n")
        for name in MATERIALS:
            fh.write(f"*MATERIAL,NAME=M{name.upper()}\n*CONDUCTIVITY\n{conductivity[name] * 1.0e-3:g}\n")
            fh.write(f"*SOLID SECTION,ELSET=E{name.upper()},MATERIAL=M{name.upper()}\n")
        if not perfect:
            for ji, name in enumerate(JOINTS):
                if not (d["joint"] == ji).any():
                    continue
                # Node to surface with a face-based slave surface: on jagged interfaces it carries the declared
                # conductance within 0.5 % (witness in the record); surface to surface carried 4 % less.
                fh.write(f"*CONTACT PAIR,INTERACTION=I{name.upper()},TYPE=NODE TO SURFACE\nS{name.upper()},M{name.upper()}\n")
                fh.write(f"*SURFACE INTERACTION,NAME=I{name.upper()}\n*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR\n1.e6,1.,0.\n")
                h = joints[name]
                fh.write(f"*GAP CONDUCTANCE\n{h:g},0.,20.\n{h:g},1.e9,20.\n")
        fh.write("*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,%g\n" % films["air"]["sink_temperature_C"])
        fh.write("*STEP\n*HEAT TRANSFER,STEADY STATE,SOLVER=ITERATIVE CHOLESKY\n1.,1.\n*FILM\n")
        for gi, name in enumerate(GROUPS):
            sink, h = film_of(films, name)
            for f in range(1, 5):
                if ((d["group"] == gi) & (d["b_fid"] == f)).any():
                    fh.write(f"F{gi}S{f},F{f},{sink:g},{h:g}\n")
        fh.write("*NODE FILE\nNT\n*END STEP\n")


def film_of(films, name) -> tuple:
    film = films.get(name) or films["air"]
    return film["sink_temperature_C"], film["coefficient_W_per_m2K"] * 1.0e-6


# ---------------------------------------------------------------- configurations

def resolve(base, case, variant_id, overrides=None) -> dict:
    """Films, joint conductances (W/m2 K) and conductivities of one variant, before any calibration."""

    overrides = overrides or {}
    bvar = next(v for v in base["variants"] if v["id"] == variant_id)
    hvar = next(v for v in case["variants"] if v["id"] == variant_id)
    films = at.variant_films(base, bvar)
    oil_sink = overrides.get("oil.sink_temperature_C", case["oil"]["sink_temperature_C"]["value"])
    oil_h = overrides.get("oil.coefficient_W_per_m2K", case["oil"]["coefficient_W_per_m2K"]["value"])
    if films.get("oil") is not None:
        films["oil"] = {**films["oil"], "sink_temperature_C": oil_sink, "coefficient_W_per_m2K": oil_h}
    fin = overrides.get("barrel.fin_factor", case["barrel"]["fin_factor"]["value"])
    for name, spec in case["films"].items():
        if spec is None:
            films[name] = None
            continue
        film = {"sink_temperature_C": spec.get("sink_temperature_C"), "coefficient_W_per_m2K": spec.get("coefficient_W_per_m2K")}
        if spec.get("sink_from") == "oil":
            film["sink_temperature_C"] = oil_sink
        if spec.get("sink_from") == "air":
            film["sink_temperature_C"] = films["air"]["sink_temperature_C"]
        if "coefficient_times_air" in spec:
            film["coefficient_W_per_m2K"] = films["air"]["coefficient_W_per_m2K"] * fin
        if f"films.{name}" in overrides:
            film["coefficient_W_per_m2K"] = overrides[f"films.{name}"]
        films[name] = film
    for name, change in hvar.get("films", {}).items():
        films[name] = None if change is None else {**(films.get(name) or {}), **change}
    joints = {name: overrides.get(f"joints.items.{name}", item["value"]) for name, item in case["joints"]["items"].items()}
    conductivity = {name: base["materials"][name]["conductivity_W_per_mK"] for name in ("valve", "guide", "plug")}
    conductivity["barrel"] = overrides.get("barrel.conductivity_W_per_mK", case["barrel"]["conductivity_W_per_mK"]["value"])
    return {"films": films, "joints": joints, "conductivity": conductivity}


def declared_range(case, path) -> tuple:
    node = case
    for key in path.split("."):
        node = node[key]
    value = node.get("value", node.get("coefficient_W_per_m2K"))
    return value, tuple(node["range"])


# ---------------------------------------------------------------- one solve

_D = {}


def _setup(work, params):
    """Load the prepared mesh and derived node sets once per worker."""

    if _D:
        return _D
    d = dict(np.load(Path(work) / "prepared.npz", allow_pickle=False))
    base, case, comps, g = load(params)
    xyz = d["xyz"][d["source"]]
    node_mat = np.full(len(xyz), -1, dtype=np.int8)
    for i in range(len(MATERIALS)):
        node_mat[np.unique(d["split"][d["material"] == i])] = i
    alloy = node_mat == 0
    zone = at.zones(xyz, alloy, comps, base)
    parts = {}
    for name, v in comps["valves"].items():
        parts[f"{v['role']}_valve"] = (node_mat == MATERIALS.index("valve")) & at.valve_mask(xyz, v, 2.0)
        parts[f"{v['role']}_guide"] = (node_mat == MATERIALS.index("guide")) & at.guide_mask(xyz, v)
    for name, p in comps["plugs"].items():
        parts[name] = (node_mat == MATERIALS.index("plug")) & at.plug_mask(xyz, p, 2.0)
    parts["barrel"] = node_mat == MATERIALS.index("barrel")
    parts["barrel_top_ring"] = parts["barrel"] & (xyz[:, 2] > -2.0)
    _, _, b_area, b_nodes = face_geometry(xyz, d["split"], d["b_elem"], d["b_fid"])
    _, _, s_area, s_nodes = face_geometry(xyz, d["split"], d["s_elem"], d["s_fid"])
    _, _, _, m_nodes = face_geometry(xyz, d["split"], d["m_elem"], d["m_fid"])
    prepared = json.loads((Path(work) / "prepared.json").read_text())
    _D.update(d=d, base=base, case=case, comps=comps, xyz=xyz, alloy=alloy, zone=zone, parts=parts,
              b_area=b_area, b_nodes=b_nodes, s_area=s_area, s_nodes=s_nodes, m_nodes=m_nodes,
              b_owner=d["material"][d["b_elem"]], s_owner=d["material"][d["s_elem"]], m_owner=d["material"][d["m_elem"]],
              factor={j: prepared["joints"][j]["area_factor"] for j in JOINTS if j in prepared["joints"]}, work=Path(work))
    return _D


def run(job) -> dict:
    """Write and solve one configuration; return its temperatures and heat flows. ``job`` = (label, alloy_k, config, perfect)."""

    label, alloy_k, config, perfect = job
    D = _D
    d, work = D["d"], D["work"]
    folder = work / "jobs" / label
    folder.mkdir(parents=True, exist_ok=False)
    conductivity = {"alloy": alloy_k, **config["conductivity"]}
    h_mm = {j: config["joints"][j] * D["factor"].get(j, 1.0) * 1.0e-6 for j in JOINTS}
    mesh_name = "../../mesh-perfect.inc" if perfect else "../../mesh.inc"
    write_job(folder / "head.inp", mesh_name, d, conductivity, config["films"], h_mm, perfect)
    t0 = time.time()
    done = subprocess.run(["ccx", "-i", "head"], cwd=folder, capture_output=True, text=True,
                          env={"OMP_NUM_THREADS": "1", "CCX_NPROC_EQUATION_SOLVER": "1", "PATH": "/usr/bin:/bin"})
    (folder / "ccx.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode or not (folder / "head.frd").exists():
        raise RuntimeError(f"{label}: ccx returned {done.returncode}")
    import sim_thermal

    temps = sim_thermal.read_frd_temperatures(folder / "head.frd")
    for name in ("head.frd", "head.dat", "head.12d", "head.cvg", "head.sta"):
        (folder / name).unlink(missing_ok=True)
    if perfect:
        # The unsplit mesh: copies take the temperature of the node they were split from.
        temps = temps[d["source"]]
    if len(temps) != len(D["xyz"]):
        raise RuntimeError(f"{label}: {len(temps)} temperatures for {len(D['xyz'])} nodes")
    films = config["films"]
    face_t = temps[D["b_nodes"]].mean(axis=1)
    heat, by_material_film = {}, np.zeros(len(MATERIALS))
    for gi, name in enumerate(GROUPS):
        sink, h = film_of(films, name)
        sel = d["group"] == gi
        q = h * D["b_area"][sel] * (face_t[sel] - sink)
        heat[name] = round(float(q.sum()), 2)
        np.add.at(by_material_film, D["b_owner"][sel], q)
    joint_heat, by_material_joint = {}, np.zeros(len(MATERIALS))
    for ji, name in enumerate(JOINTS):
        sel = d["joint"] == ji
        if not sel.any():
            continue
        q = h_mm[name] * D["s_area"][sel] * (temps[D["s_nodes"][sel]].mean(axis=1) - temps[D["m_nodes"][sel]].mean(axis=1))
        joint_heat[name] = round(float(q.sum()), 2)
        np.add.at(by_material_joint, D["s_owner"][sel], q)
        np.add.at(by_material_joint, D["m_owner"][sel], -q)
    into = -sum(v for v in heat.values() if v < 0)
    residual = by_material_film + by_material_joint
    alloy_nodes = np.flatnonzero(D["alloy"])
    hottest = alloy_nodes[int(np.argmax(temps[alloy_nodes]))]
    wall = {name: round(-1000.0 * heat[name] / float(D["b_area"][d["group"] == GROUPS.index(name)].sum()), 1)
            for name in ("chamber_gas", "hot_port", "barrel_gas")}
    result = {
        "label": label, "alloy_conductivity_W_per_mK": alloy_k,
        "peak_C": {name: round(float(temps[sel].max()), 2) for name, sel in D["zone"].items() if sel.any()},
        "peak_alloy_at_mm": [round(float(x), 1) for x in D["xyz"][hottest]],
        "mean_alloy_C": round(float(temps[D["alloy"]].mean()), 2),
        "part_peak_C": {name: round(float(temps[sel].max()), 2) for name, sel in D["parts"].items() if sel.any()},
        "barrel_top_ring_mean_C": round(float(temps[D["parts"]["barrel_top_ring"]].mean()), 2),
        "heat_out_W_by_group": heat,
        "heat_W_through_joint_from_part": joint_heat,
        "wall_loading_kW_per_m2": wall,
        "heat_into_the_assembly_W": round(into, 2),
        "energy_imbalance_relative": round(abs(sum(heat.values())) / into, 6),
        "part_balance_residual_W": {name: round(float(residual[i]), 3) for i, name in enumerate(MATERIALS)},
        "ccx_s": round(time.time() - t0, 1),
    }
    print(label, result["peak_C"].get("alloy"), wall, result["heat_into_the_assembly_W"],
          result["energy_imbalance_relative"], result["ccx_s"], flush=True)
    return result


def _pool(work, params, jobs, n):
    import multiprocessing as mp

    _setup(work, params)
    if n <= 1:
        return [run(j) for j in jobs]
    with mp.get_context("fork").Pool(n) as pool:
        return pool.map(run, jobs, chunksize=1)


def calibrate(work, params, variant, rule, reference_k) -> tuple:
    """Scale each gas-side coefficient until its wall carries the target loading, at the reference conductivity.

    The first update is target over achieved, as in the first case; then a secant through the last two
    (coefficient, loading) pairs of each group, because the barrel bore's loading saturates as its wall
    nears the gas temperature. Stops when every loading is within the tolerance, keeping the coefficients
    of the last solved step, never an unchecked update.
    """

    D = _D
    config = resolve(D["base"], D["case"], variant["id"])
    targets = variant.get("calibrate_wall_loading_kW_per_m2", {})
    for name in targets:
        if config["films"][name]["coefficient_W_per_m2K"] is None:
            raise SystemExit(f"{name}: no coefficient to calibrate")
    rows, history = [], {name: [] for name in targets}
    for step in range(int(rule["max_steps"]) if targets else 0):
        result = run((f"{variant['id']}-calibration{step}", reference_k, config, False))
        row = {"step": step}
        for name, target in targets.items():
            h, q = config["films"][name]["coefficient_W_per_m2K"], result["wall_loading_kW_per_m2"][name]
            row[name] = {"coefficient_W_per_m2K": round(h, 2), "loading_kW_per_m2": q, "target_kW_per_m2": target}
            history[name].append((h, q))
        row["converged"] = all(abs(row[n]["loading_kW_per_m2"] / t - 1.0) <= rule["tolerance_relative"] for n, t in targets.items())
        rows.append(row)
        if row["converged"] or step == int(rule["max_steps"]) - 1:
            break
        for name, target in targets.items():
            config["films"][name]["coefficient_W_per_m2K"] = next_coefficient(history[name], target)
    return config, rows


def next_coefficient(history, target) -> float:
    """Target over achieved on the first step, then the secant through the last two (coefficient, loading) pairs."""

    h, q = history[-1]
    if len(history) > 1 and history[-1][1] != history[-2][1]:
        (h0, q0), (h1, q1) = history[-2:]
        secant = h1 + (target - q1) * (h1 - h0) / (q1 - q0)
        if 0.0 < secant < 4.0 * h1:
            return secant
    return h * target / q


def _calibrate_job(args):
    work, params, variant, rule, reference_k = args
    _setup(work, params)
    return calibrate(work, params, variant, rule, reference_k)


def solve(work, params, summary, jobs="4") -> None:
    import multiprocessing as mp

    work, params, n = Path(work), Path(params), int(jobs)
    D = _setup(work, params)
    base, case = D["base"], D["case"]
    write_mesh(work / "mesh.inc", D["d"])
    write_mesh(work / "mesh-perfect.inc", D["d"], perfect=True)
    (work / "jobs").mkdir(exist_ok=True)
    candidates = json.loads((params / "alloy-candidates.json").read_text())["candidates"]
    all_k = sorted({c["conductivity_W_per_mK"] for c in candidates})
    reference_k = float(base["reference_conductivity_W_per_mK"])
    t0 = time.time()

    # Calibrations: one worker per calibrated variant, steps in sequence.
    calibrated = [v for v in case["variants"] if v.get("calibrate_wall_loading_kW_per_m2")]
    with mp.get_context("fork").Pool(max(1, min(n, len(calibrated)))) as pool:
        out = pool.map(_calibrate_job, [(work, params, v, case["calibration"], reference_k) for v in calibrated])
    configs = {v["id"]: resolve(base, case, v["id"]) for v in case["variants"]}
    calibration = {v["id"]: [] for v in case["variants"]}
    for v, (config, rows) in zip(calibrated, out):
        configs[v["id"]], calibration[v["id"]] = config, rows

    # Sweeps, sensitivity and the perfect-contact witness, in one pool.
    sweep = []
    for v in case["variants"]:
        bvar = next(b for b in base["variants"] if b["id"] == v["id"])
        ks = all_k if bvar["sweep"] == "all" else sorted({all_k[0], reference_k, all_k[-1]})
        sweep += [(f"{v['id']}-k{k:g}", k, configs[v["id"]], False) for k in ks]
    sens_variant = case["sensitivity"]["variant"]
    fixed = configs[sens_variant]
    sens = []
    for item in case["sensitivity"]["items"]:
        value, (low, high) = declared_range(case, item["path"])
        for end, x in (("low", low), ("high", high)):
            config = resolve(base, case, sens_variant, {item["path"]: x})
            for name in case["variants"][[v["id"] for v in case["variants"]].index(sens_variant)].get(
                    "calibrate_wall_loading_kW_per_m2", {}):
                config["films"][name]["coefficient_W_per_m2K"] = fixed["films"][name]["coefficient_W_per_m2K"]
            sens.append((f"sens-{item['id']}-{end}", reference_k, config, False))
    big = case["joints"]["perfect_contact_witness_W_per_m2K"]
    stiff = {**fixed, "joints": {j: big for j in JOINTS}}
    witness = [("witness-joints-at-1e7", reference_k, stiff, False), ("witness-shared-nodes", reference_k, fixed, True)]
    results = {r["label"]: r for r in _pool(work, params, sweep + sens + witness, n)}

    variants = {}
    for v in case["variants"]:
        rows = sorted((r for r in results.values() if r["label"].startswith(v["id"] + "-k")),
                      key=lambda r: r["alloy_conductivity_W_per_mK"])
        variants[v["id"]] = {
            "what": v["what"],
            "films": {name: (None if f is None else {"sink_temperature_C": f["sink_temperature_C"],
                                                     "coefficient_W_per_m2K": round(f["coefficient_W_per_m2K"], 2)})
                      for name, f in configs[v["id"]]["films"].items()},
            "joints_W_per_m2K": configs[v["id"]]["joints"], "conductivity_W_per_mK": configs[v["id"]]["conductivity"],
            "calibration": calibration[v["id"]], "by_conductivity": rows}
    centre = results[f"{sens_variant}-k{reference_k:g}"]
    sensitivity = []
    for item in case["sensitivity"]["items"]:
        value, (low, high) = declared_range(case, item["path"])
        lo, hi = results[f"sens-{item['id']}-low"], results[f"sens-{item['id']}-high"]
        sensitivity.append({"id": item["id"], "path": item["path"], "value": value, "range": [low, high],
                            "peak_alloy_C": [lo["peak_C"]["alloy"], centre["peak_C"]["alloy"], hi["peak_C"]["alloy"]],
                            "peak_alloy_at_mm": [lo["peak_alloy_at_mm"], hi["peak_alloy_at_mm"]],
                            "valve_bridge_C": [lo["peak_C"]["valve_bridge"], centre["peak_C"]["valve_bridge"], hi["peak_C"]["valve_bridge"]],
                            "exhaust_valve_C": [lo["part_peak_C"]["exhaust_valve"], centre["part_peak_C"]["exhaust_valve"],
                                                hi["part_peak_C"]["exhaust_valve"]],
                            "heat_into_the_assembly_W": [lo["heat_into_the_assembly_W"], centre["heat_into_the_assembly_W"],
                                                         hi["heat_into_the_assembly_W"]],
                            "energy_imbalance_relative": max(lo["energy_imbalance_relative"], hi["energy_imbalance_relative"])})
    sensitivity.sort(key=lambda s: -abs(s["peak_alloy_C"][2] - s["peak_alloy_C"][0]))
    reference = case["sensitivity"]["variant"]
    by_k = {r["alloy_conductivity_W_per_mK"]: r for r in variants[reference]["by_conductivity"]}
    ranking = [{"id": c["id"], "alloy": c["alloy"], "condition": c["condition"],
                "alloy_conductivity_W_per_mK": c["conductivity_W_per_mK"], "peak_C": by_k[c["conductivity_W_per_mK"]]["peak_C"]}
               for c in candidates if c["conductivity_W_per_mK"] in by_k]
    ranking.sort(key=lambda r: (r["peak_C"]["alloy"], r["id"]))
    prepared = json.loads((work / "prepared.json").read_text())
    w_split, w_shared = results["witness-joints-at-1e7"], results["witness-shared-nodes"]
    Path(summary).write_text(json.dumps({
        "schema": SCHEMA,
        "case_file": "params/assembly-heat-paths-case.json",
        "extends": "params/assembly-case.json",
        "mesh": {k: prepared[k] for k in ("mesher", "size_max_mm", "nodes", "nodes_after_split", "tets",
                                          "share_with_minSICN_below_0p1", "tets_by_material", "volume_mm3_by_material")},
        "film_area_mm2_by_group": prepared["film_area_mm2_by_group"],
        "joints": prepared["joints"],
        "zone_nodes": {name: int(sel.sum()) for name, sel in D["zone"].items()},
        "variants": variants,
        "ranking_variant": reference,
        "ranking_by_peak_alloy_temperature": ranking,
        "sensitivity": {"variant": reference, "alloy_conductivity_W_per_mK": reference_k,
                        "rule": case["sensitivity"]["what"], "centre": {"peak_alloy_C": centre["peak_C"]["alloy"],
                                                                        "label": centre["label"]},
                        "items": sensitivity},
        "perfect_contact_witness": {
            "what": "the reference configuration with every joint at a conductance a thousand times the declared value, against the same mesh with shared nodes (perfect contact, no contact pairs)",
            "joints_W_per_m2K": big,
            "peak_alloy_C": [w_split["peak_C"]["alloy"], w_shared["peak_C"]["alloy"]],
            "max_peak_difference_C": round(max(abs(w_split["peak_C"][z] - w_shared["peak_C"][z]) for z in w_shared["peak_C"]), 3),
            "heat_into_the_assembly_W": [w_split["heat_into_the_assembly_W"], w_shared["heat_into_the_assembly_W"]],
            "heat_W_through_deck_joint": w_split["heat_W_through_joint_from_part"].get("deck")},
        "solve_wall_s": round(time.time() - t0, 1),
        "claims": "peak temperatures under declared hypothesis cases: hypothetical valves, guides, plugs and barrel, declared "
                  "joint conductances, films uncorrelated with any engine, room-temperature conductivities. Not an engine "
                  "temperature, not a material qualification",
    }, indent=2) + "\n")
    print("solved", len(results), "configurations in", round(time.time() - t0), "s")


def reference(work, params, summary, out) -> None:
    """Solve the reference configuration of a finished summary on another prepared mesh."""

    work, params = Path(work), Path(params)
    D = _setup(work, params)
    s = json.loads(Path(summary).read_text())
    variant = s["sensitivity"]["variant"]
    config = resolve(D["base"], D["case"], variant)
    for name, film in s["variants"][variant]["films"].items():
        if film is not None:
            config["films"][name]["coefficient_W_per_m2K"] = film["coefficient_W_per_m2K"]
    write_mesh(work / "mesh.inc", D["d"])
    (work / "jobs").mkdir(exist_ok=True)
    result = run((f"reference-{variant}", s["sensitivity"]["alloy_conductivity_W_per_mK"], config, False))
    prepared = json.loads((work / "prepared.json").read_text())
    Path(out).write_text(json.dumps({"prepared": prepared, "result": result}, indent=2) + "\n")


def probe(work, params, out) -> None:
    """One uncalibrated solve of the ranking variant, split and shared-node: time, heat and the parts' balance."""

    work, params = Path(work), Path(params)
    D = _setup(work, params)
    write_mesh(work / "mesh.inc", D["d"])
    write_mesh(work / "mesh-perfect.inc", D["d"], perfect=True)
    (work / "jobs").mkdir(exist_ok=True)
    config = resolve(D["base"], D["case"], D["case"]["sensitivity"]["variant"])
    k = float(D["base"]["reference_conductivity_W_per_mK"])
    results = [run(("probe-split", k, config, False)), run(("probe-shared", k, config, True))]
    Path(out).write_text(json.dumps(results, indent=2) + "\n")


def _witness_case(shape, size, contact, folder) -> dict:
    """Two materials labelled by centroid across a plane or a cylinder, Dirichlet on two faces, one joint.

    The interface follows the tetrahedra, as in the assembly. The heat that crosses is compared with the
    closed-form answer for the smooth interface at the declared conductance.
    """

    import gmsh

    import sim_thermal

    k, h, t_hot, t_cold, cut = 0.15, 0.01, 300.0, 100.0, 10.137
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    if shape == "plane":
        occ.addBox(0, 0, 0, 20.0, 20.0, 20.0)
    else:
        occ.cut([(3, occ.addCylinder(0, 0, 0, 0, 0, 10.0, 20.0))], [(3, occ.addCylinder(0, 0, 0, 0, 0, 10.0, 5.0))])
    occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.MeshSizeMin", size / 2)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    gmsh.model.mesh.generate(3)
    tag, xyz, _ = gmsh.model.mesh.getNodes()
    _, _, en = gmsh.model.mesh.getElements(3)
    gmsh.finalize()
    order = np.argsort(tag)
    tag, xyz = tag[order], xyz.reshape(-1, 3)[order]
    tets = np.searchsorted(tag, np.asarray(en[0]).reshape(-1, 4)).astype(np.int64)
    centre = xyz[tets].mean(axis=1)
    radius = np.hypot(centre[:, 0], centre[:, 1])
    material = np.where((centre[:, 2] if shape == "plane" else radius) < cut, 0, 2).astype(np.int8)
    _, (ea, fa, eb, fb) = face_pairs(tets)
    diff = material[ea] != material[eb]
    ea, fa, eb, fb = ea[diff], fa[diff], eb[diff], fb[diff]
    swap = material[eb] > material[ea]
    se, sf, me, mf = np.where(swap, eb, ea), np.where(swap, fb, fa), np.where(swap, ea, eb), np.where(swap, fa, fb)
    c, n, area, _ = face_geometry(xyz, tets, se, sf)
    true_n = np.tile([0.0, 0.0, 1.0], (len(c), 1)) if shape == "plane" else \
        np.column_stack([c[:, :2] / np.linalg.norm(c[:, :2], axis=1)[:, None], np.zeros(len(c))])
    factor = float((area * np.abs(np.einsum("ij,ij->i", n, true_n))).sum() / area.sum())
    split, source = split_nodes(tets, material)
    x = xyz[source]
    r = np.hypot(x[:, 0], x[:, 1])
    hot = np.flatnonzero(np.abs(x[:, 2]) < 1e-9 if shape == "plane" else np.abs(r - 5.0) < 1e-6) + 1
    cold = np.flatnonzero(np.abs(x[:, 2] - 20.0) < 1e-9 if shape == "plane" else np.abs(r - 20.0) < 1e-6) + 1
    if shape == "plane":
        expected = (t_hot - t_cold) * 400.0 / (cut / k + 1.0 / h + (20.0 - cut) / k)
    else:
        expected = 2 * math.pi * 10.0 * (t_hot - t_cold) / (math.log(cut / 5.0) / k + 1.0 / (h * cut) + math.log(20.0 / cut) / k)
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "w.inp", "w") as fh:
        fh.write("*NODE\n")
        np.savetxt(fh, np.column_stack([np.arange(1, len(x) + 1), x]), fmt="%d,%.9f,%.9f,%.9f")
        for m in (0, 2):
            sel = np.flatnonzero(material == m)
            fh.write(f"*ELEMENT,TYPE=C3D4,ELSET=E{m}\n")
            np.savetxt(fh, np.column_stack([sel + 1, split[sel] + 1]), fmt="%d,%d,%d,%d,%d")
            fh.write(f"*MATERIAL,NAME=M{m}\n*CONDUCTIVITY\n{k}\n*SOLID SECTION,ELSET=E{m},MATERIAL=M{m}\n")
        fh.write("*NSET,NSET=NHOT\n")
        _lines(fh, hot)
        fh.write("*NSET,NSET=NCOLD\n")
        _lines(fh, cold)
        for side, e, f in (("S", se, sf), ("M", me, mf)):
            fh.write(f"*SURFACE,NAME={side}J,TYPE=ELEMENT\n")
            np.savetxt(fh, np.column_stack([e + 1, f]), fmt="%d,S%d")
        if contact == "node to surface":
            fh.write("*CONTACT PAIR,INTERACTION=IJ,TYPE=NODE TO SURFACE\nSJ,MJ\n*SURFACE INTERACTION,NAME=IJ\n"
                     "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR\n1.e6,1.,0.\n")
        else:
            fh.write("*CONTACT PAIR,INTERACTION=IJ,TYPE=SURFACE TO SURFACE\nSJ,MJ\n*SURFACE INTERACTION,NAME=IJ\n"
                     "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=TIED\n1.e6\n")
        fh.write(f"*GAP CONDUCTANCE\n{h * factor:g},0.,20.\n{h * factor:g},1.e9,20.\n")
        fh.write("*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNHOT,200.\nNCOLD,200.\n")
        fh.write(f"*STEP\n*HEAT TRANSFER,STEADY STATE,SOLVER=ITERATIVE CHOLESKY\n1.,1.\n*BOUNDARY\nNHOT,11,11,{t_hot}\n"
                 f"NCOLD,11,11,{t_cold}\n*NODE FILE\nNT\n*NODE PRINT,NSET=NHOT,TOTALS=ONLY\nRFL\n*END STEP\n")
    subprocess.run(["ccx", "-i", "w"], cwd=folder, capture_output=True, text=True,
                   env={"OMP_NUM_THREADS": "1", "PATH": "/usr/bin:/bin"})
    heat = float((folder / "w.dat").read_text().split()[-1])
    temps = sim_thermal.read_frd_temperatures(folder / "w.frd")
    local = np.array([FACE_NODES[f] for f in range(1, 5)])
    jump = temps[split[se[:, None], local[sf - 1]]].mean(axis=1) - temps[split[me[:, None], local[mf - 1]]].mean(axis=1)
    summed = abs(float((h * factor * area * jump).sum()))
    return {"shape": shape, "size_mm": size, "contact": contact, "tets": int(len(tets)), "area_factor": round(factor, 4),
            "expected_W": round(expected, 2), "carried_W": round(heat, 2), "relative_error": round(heat / expected - 1.0, 4),
            "over_face_sum": round(heat / summed, 4)}


def witness(folder, out) -> None:
    """Contact conductance across a jagged interface, against the closed-form answer."""

    folder = Path(folder)
    rows = [_witness_case(shape, size, contact, folder / f"{shape}-{size:g}-{contact.split()[0]}")
            for shape in ("plane", "cylinder") for size in (0.5, 1.0, 2.0)
            for contact in ("node to surface", "surface to surface")]
    Path(out).write_text(json.dumps({
        "what": "two materials labelled by centroid across a plane (20 mm cube) or a cylinder (tube 5 to 20 mm), split "
                "and tied by one contact pair at 10,000 W/(m2 K) scaled by the projected-area factor; heat carried "
                "between two fixed temperatures against the closed-form answer for the smooth interface",
        "rows": rows}, indent=2) + "\n")
    for r in rows:
        print(r)


SERIES = {  # categorical slots 1-4 of the repository chart palette, with a marker each (colour is never alone)
    "declared": ("#2a78d6", "o", "declared: gas 900 °C, no oil path"),
    "declared_oil": ("#eb6834", "s", "declared, with oil"),
    "published_loading_oil": ("#1baf7a", "D", "published wall loading, air 150"),
    "published_loading_oil_air_233": ("#eda100", "^", "published wall loading, air 233"),
}
LABELS = {"joint_seat": "valve seat joint", "joint_stem": "valve stem joint", "joint_guide": "guide joint",
          "joint_plug": "plug joint", "joint_deck": "barrel joint", "barrel_conductivity": "barrel conductivity",
          "barrel_fin_factor": "barrel fin factor", "crankcase_coefficient": "crankcase contact",
          "cam_housing_coefficient": "cam-housing contact", "oil_coefficient": "oil film coefficient",
          "oil_temperature": "oil temperature"}


def plot(s: dict, out: Path) -> None:
    """Peak head-alloy temperature against conductivity, and its sensitivity to each new value."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid, surface = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    fig, (a, b) = plt.subplots(1, 2, figsize=(13.0, 6.2), dpi=110, gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.patch.set_facecolor(surface)
    for ax in (a, b):
        ax.set_facecolor(surface)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(muted)
        ax.tick_params(colors=muted, labelsize=9)
    first = s["first_screen"]["peak_alloy_C_by_conductivity"][s["ranking_variant"]]
    ks = sorted(float(k) for k in first)
    a.plot(ks, [first[str(k)] for k in ks], "--", color="#8a8985", linewidth=2.0,
           label="first screen, published loading, air 150")
    a.annotate("first screen", (ks[-1], first[str(ks[-1])]), xytext=(6, 0), textcoords="offset points",
               color=muted, fontsize=8.5, va="center")
    for name, v in s["variants"].items():
        colour, marker, label = SERIES[name]
        rows = sorted(v["by_conductivity"], key=lambda r: r["alloy_conductivity_W_per_mK"])
        x = [r["alloy_conductivity_W_per_mK"] for r in rows]
        y = [r["peak_C"]["alloy"] for r in rows]
        a.plot(x, y, "-", marker=marker, color=colour, linewidth=2.0, markersize=6, label=label,
               markeredgecolor=surface, markeredgewidth=1.0)
        a.annotate(f"{y[-1]:.0f} °C", (x[-1], y[-1]), xytext=(6, 0), textcoords="offset points", color=ink,
                   fontsize=8.5, va="center")
    a.axhspan(235.0, 250.0, color="#eda100", alpha=0.18, linewidth=0)
    a.text(96, 242.5, "published limit 235 to 250 °C (Mackerle)", fontsize=8.5, color=muted, va="center")
    a.axhline(300.0, color=muted, linewidth=1.0, linestyle=":")
    a.text(210, 296, "about 300 °C (Heywood)", fontsize=8.5, color=muted, ha="right", va="top")
    a.set_xlim(90, 212)
    a.set_xlabel("Head alloy conductivity at room temperature, W/(m·K)", color=ink, fontsize=9.5)
    a.set_ylabel("Peak head-alloy temperature, °C", color=ink, fontsize=9.5)
    a.set_title("With barrel, oil and joint conductances", color=ink, fontsize=11, loc="left")
    a.grid(True, color=grid, linewidth=0.6)
    a.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, labelcolor=ink)

    sens = s["sensitivity"]
    centre = sens["centre"]["peak_alloy_C"]
    items = sens["items"][::-1]
    for i, item in enumerate(items):
        low, _, high = item["peak_alloy_C"]
        for value, colour, end in ((low, "#2a78d6", "low"), (high, "#eb6834", "high")):
            b.barh(i, value - centre, left=centre, height=0.62, color=colour, edgecolor=surface, linewidth=2.0,
                   label=f"{end} end of the declared range" if i == 0 else None)
        # The cooler end is labelled left of the bars, the hotter end right of them, so tiny spans never collide.
        for value, side in ((min(low, high), -1), (max(low, high), 1)):
            anchor = min(value, centre) if side < 0 else max(value, centre)
            b.annotate(f"{value:.0f}", (anchor, i), xytext=(4 * side, 0), textcoords="offset points",
                       ha="left" if side > 0 else "right", va="center", fontsize=8, color=ink)
    b.axvline(centre, color=ink, linewidth=1.0)
    b.set_yticks(range(len(items)))
    b.set_yticklabels([LABELS.get(it["id"], it["id"]) for it in items], fontsize=9, color=ink)
    lo = min(min(it["peak_alloy_C"]) for it in items)
    hi = max(max(it["peak_alloy_C"]) for it in items)
    b.set_xlim(lo - 0.12 * (hi - lo) - 2, hi + 0.12 * (hi - lo) + 2)
    b.set_xlabel(f"Peak head-alloy temperature, °C (centre {centre:.0f} °C)", color=ink, fontsize=9.5)
    b.set_title(f"One value at a time, {sens['alloy_conductivity_W_per_mK']:g} W/(m·K), published loading",
                color=ink, fontsize=11, loc="left")
    b.grid(True, axis="x", color=grid, linewidth=0.6)
    b.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, labelcolor=ink)
    fig.suptitle("935 head assembly thermal screen: hypothesis cases, not an engine prediction", x=0.01, ha="left",
                 color=muted, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out, facecolor=surface)
    plt.close(fig)


def record(summary, base_work, fine, again, joint_witness, out) -> None:
    """The committed record: the sweep, the joint witness, the mesh comparison and the first screen beside it."""

    s = json.loads(Path(summary).read_text())
    s["mesh"]["islands"] = json.loads((Path(base_work) / "prepared.json").read_text())["islands"]
    s["joint_witness"] = json.loads(Path(joint_witness).read_text())
    params = Path(out).parent
    case = json.loads((params / "assembly-heat-paths-case.json").read_text())
    first = json.loads((params / "assembly-thermal.json").read_text())
    variant, k = s["sensitivity"]["variant"], s["sensitivity"]["alloy_conductivity_W_per_mK"]
    base = next(r for r in s["variants"][variant]["by_conductivity"] if r["alloy_conductivity_W_per_mK"] == k)

    def entry(pitch, mesh, result):
        return {"surface_pitch_mm": pitch, "tets": mesh["tets"], "nodes_after_split": mesh["nodes_after_split"],
                "peak_C": result["peak_C"], "peak_alloy_at_mm": result["peak_alloy_at_mm"],
                "part_peak_C": result["part_peak_C"], "heat_into_the_assembly_W": result["heat_into_the_assembly_W"],
                "energy_imbalance_relative": result["energy_imbalance_relative"]}

    rows = {"base": entry(case["mesh"]["surface_pitch_mm"], s["mesh"], base)}
    for name, path, pitch in (("finer_surface", fine, case["mesh"]["comparison_surface_pitch_mm"]),
                              ("second_mesh_same_surface", again, case["mesh"]["surface_pitch_mm"])):
        r = json.loads(Path(path).read_text())
        rows[name] = entry(pitch, r["prepared"], r["result"])
        rows[name]["joint_area_factor"] = {j: v["area_factor"] for j, v in r["prepared"]["joints"].items()}
        rows[name]["islands"] = r["prepared"]["islands"]
    for name in ("finer_surface", "second_mesh_same_surface"):
        rows[name]["difference_from_base_C"] = {z: round(rows[name]["peak_C"][z] - rows["base"]["peak_C"][z], 2)
                                                for z in rows["base"]["peak_C"]}
        rows[name]["peak_moved_mm"] = round(math.dist(rows[name]["peak_alloy_at_mm"], rows["base"]["peak_alloy_at_mm"]), 1)
    s["mesh_comparison"] = {"rule": case["mesh"]["rule"], "variant": variant, "alloy_conductivity_W_per_mK": k, **rows}
    s["first_screen"] = {
        "record": "params/assembly-thermal.json",
        "what": "the same four variants without the heat paths: perfect contact, the cylinder as one film, oil on the pockets only",
        "peak_alloy_C_by_conductivity": {name: {str(r["alloy_conductivity_W_per_mK"]): r["peak_C"]["alloy"]
                                                for r in v["by_conductivity"]} for name, v in first["variants"].items()}}
    Path(out).write_text(json.dumps(s, indent=2) + "\n")
    plot(s, params.parent / "media" / "heat-paths.png")
    print(json.dumps(s["mesh_comparison"], indent=1)[:3000])


if __name__ == "__main__":
    {"occupancy": occupancy, "prepare": prepare, "solve": solve, "reference": reference, "probe": probe,
     "witness": witness, "record": record}[sys.argv[1]](*sys.argv[2:])
