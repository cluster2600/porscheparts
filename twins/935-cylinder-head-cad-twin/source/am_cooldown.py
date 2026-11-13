"""AM study, part 2: Adamantine whole-part cooldown screen on voxel hexahedra.

Declared-hypothesis screen, as in the 2026-10-29 study (H13): the closed twin
body, assumed fully solid and stress-free at a uniform 500 K, cools for 20 s
by convection to 300 K air while its lowest face is clamped. Generic
AlSi10Mg-class constants are declared in MATERIAL below; none is a measured
property of the specimen or of a build. There is no laser, no deposition, no
powder, no plasticity calibration and no build file. Nothing here qualifies a
material, a process or a part.

Steps (each is a sub-command; `all` chains them):

  prepare PRIVATE_DIR CASE_DIR --pitch 4|2 [--dt S] [--witness]
      Block the 0.25 mm occupancy grid into cubes of the given pitch (a cube
      is solid when at least half of its fine voxels are inside), keep the
      largest face-connected component, write a Gmsh 2.2 hexahedral mesh in
      metres and the Adamantine input deck.
  run CASE_DIR [--ranks 4]
      Run Adamantine in the pinned image under a 4 GiB cap.
  check CASE_DIR
      Independent post-check. Reads only the VTU files and the declared
      constants; shares no data with `prepare`. Re-derives volume, exterior
      area, thermal energy and convective loss, integrates the loss in time
      and reports the energy imbalance. The solver's return code is not used.
  summarize STUDY_DIR OUT.json
      Collect the scalar results of the cases into one JSON for Git.

Usage: am_cooldown.py all PRIVATE_DIR PARAMS_DIR
Private bytes go to PRIVATE_DIR/am-study/cooldown-*; only scalars reach Git.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import numpy as np

IMAGE = "rombur/adamantine:1.1"
MEMORY_CAP = "4g"

# Declared hypotheses. Same values as the 2026-10-29 study so the two can be
# compared; generic AlSi10Mg-class numbers, not a datasheet and not measured.
MATERIAL = {
    "label": "generic AlSi10Mg-class solid (declared hypothesis; no alloy, powder lot or heat treatment is established)",
    "density_kg_m3": 2670.0,
    "specific_heat_J_kgK": 900.0,
    "conductivity_W_mK": 150.0,
    "youngs_modulus_Pa": 70.0e9,
    "poisson_ratio": 0.33,
    "thermal_expansion_per_K": 2.3e-5,
    "solidus_K": 843.0,
}
CASE = {
    "initial_temperature_K": 500.0,
    "ambient_temperature_K": 300.0,
    "film_coefficient_W_m2K": 20.0,
    "duration_s": 20.0,
    "output_interval_s": 5.0,
    "time_integrator": "rk_fourth_order (explicit)",
    "thermal_fe_degree": 1,
    "mechanical_fe_degree": 1,
    "thermal_boundary": "convection on every exterior face, including the clamped one",
    "mechanical_boundary": "exterior faces on the lowest z plane of the voxel body clamped (deck side, provisional fixture); all others traction-free",
    "mechanical_reference": "strain-free at the initial temperature (Adamantine: unmelted substrate)",
}
DEFAULT_DT = {4.0: 0.02, 2.0: 0.005}

HEX_CORNERS = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
# Exterior face of a cell towards each neighbour offset, as corner indices.
FACE_OF_DIRECTION = {
    (-1, 0, 0): [0, 4, 7, 3], (1, 0, 0): [1, 2, 6, 5],
    (0, -1, 0): [0, 1, 5, 4], (0, 1, 0): [3, 7, 6, 2],
    (0, 0, -1): [0, 3, 2, 1], (0, 0, 1): [4, 5, 6, 7],
}

DECK = """geometry
{{
  import_mesh true
  mesh_file {mesh_file}
  mesh_format gmsh
  reset_material_id true
  dim 3
  material_height 1
  material_deposition false
  use_powder false
}}
physics
{{
  thermal true
  mechanical true
}}
discretization
{{
  thermal
  {{
    fe_degree {thermal_fe_degree}
    quadrature gauss
  }}
  mechanical
  {{
    fe_degree {mechanical_fe_degree}
  }}
}}
boundary
{{
  type convective,traction_free
  boundary_4
  {{
    type convective,clamped
  }}
}}
refinement
{{
  n_refinements 0
  time_steps_between_refinement 100000
}}
materials
{{
  initial_temperature {initial_temperature_K}
  property_format polynomial
  n_materials 1
  material_0
  {{
    solidus {solidus_K}
    convection_temperature_infty {ambient_temperature_K}
    solid
    {{
      lame_first_parameter {lame_first:.10g}
      lame_second_parameter {lame_second:.10g}
      thermal_expansion_coef {thermal_expansion_per_K}
      density {density_kg_m3}
      specific_heat {specific_heat_J_kgK}
      thermal_conductivity_x {conductivity_W_mK}
      thermal_conductivity_y {conductivity_W_mK}
      thermal_conductivity_z {conductivity_W_mK}
      convection_heat_transfer_coef {film_coefficient_W_m2K}
    }}
  }}
}}
sources
{{
  n_beams 0
}}
time_stepping
{{
  method rk_fourth_order
  scan_path_for_duration false
  duration {duration_s}
  time_step {dt}
  mechanical_time_step_factor {factor}
}}
post_processor
{{
  filename_prefix cooldown
  time_steps_between_output {factor}
  additional_output_refinement 0
}}
memory_space host
verbose_output false
"""


# --------------------------------------------------------------------------
# prepare


def block_fraction(wn, k: int, z_anchor: int) -> tuple[np.ndarray, int]:
    """Share of inside fine voxels (w > 0.5) in each k^3 block.

    The block lattice is shifted along z so that a block boundary falls on the
    lower face of fine voxel `z_anchor`. Reads one slab of k planes at a time.
    """

    nx, ny, nz = wn.shape
    front = (k - z_anchor % k) % k
    bx, by, bz = math.ceil(nx / k), math.ceil(ny / k), math.ceil((nz + front) / k)
    out = np.zeros((bx, by, bz), dtype=np.float32)
    pad = np.zeros((k, by * k, bz * k), dtype=bool)
    for i in range(bx):
        slab = np.asarray(wn[i * k:(i + 1) * k]) > 0.5
        pad[:] = False
        pad[:slab.shape[0], :ny, front:front + nz] = slab
        out[i] = pad.reshape(k, by, k, bz, k).sum(axis=(0, 2, 4)) / float(k ** 3)
    return out, front


def witness_field(pitch: float = 0.25):
    """Analytic block 20 x 12 x 8 mm on a 0.25 mm grid, padded by 4 mm of air.

    The block starts at the origin and the pad is one 4 mm cube, so the block
    faces coincide with the 4 mm lattice and the hexahedra reproduce it exactly.
    """

    n = [int(round(s / pitch)) for s in (20.0, 12.0, 8.0)]
    m = int(round(4.0 / pitch))
    w = np.zeros([s + 2 * m for s in n], dtype=np.float32)
    w[m:-m, m:-m, m:-m] = 1.0
    grid = {"pitch_mm": pitch, "x0": -4.0 + pitch / 2, "y0": -4.0 + pitch / 2, "z0": -4.0 + pitch / 2}
    exact = {"volume_mm3": 20.0 * 12.0 * 8.0, "area_mm2": 2.0 * (20 * 12 + 20 * 8 + 12 * 8)}
    return w, grid, exact


def prepare(private: Path, case: Path, pitch: float, dt: float | None, witness: bool) -> dict:
    from scipy import ndimage

    case.mkdir(parents=True, exist_ok=False)
    if witness:
        wn, grid, exact = witness_field()
        source = "analytic block 20 x 12 x 8 mm"
    else:
        grid = json.loads((private / "occupancy-grid.json").read_text())
        wn = np.load(private / grid["array"], mmap_mode="r")
        exact = None
        source = "occupancy-wn.npy (winding number > 0.5)"
    p = float(grid["pitch_mm"])
    k = int(round(pitch / p))
    assert abs(k * p - pitch) < 1e-9, "pitch must be a multiple of the grid pitch"
    # Fine voxel i spans [x0 + (i - 1/2) p, x0 + (i + 1/2) p]. Anchor the block
    # lattice on the fine-voxel face nearest to the deck datum z = 0.
    z_anchor = int(round((0.0 - (grid["z0"] - p / 2)) / p))
    frac, front = block_fraction(wn, k, z_anchor)
    fine_inside = float(frac.sum()) * k ** 3
    solid = frac >= 0.5
    labels, count = ndimage.label(solid)  # face connectivity
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    kept = labels == int(sizes.argmax())
    cells = np.argwhere(kept)

    node_id = -np.ones(tuple(s + 1 for s in kept.shape), dtype=np.int64)
    corner_ijk = (cells[:, None, :] + HEX_CORNERS[None]).reshape(-1, 3)
    node_id[corner_ijk[:, 0], corner_ijk[:, 1], corner_ijk[:, 2]] = 0
    used = np.argwhere(node_id == 0)
    node_id[used[:, 0], used[:, 1], used[:, 2]] = np.arange(len(used))
    hexes = node_id[corner_ijk[:, 0], corner_ijk[:, 1], corner_ijk[:, 2]].reshape(-1, 8)
    origin = np.array([grid["x0"] - p / 2, grid["y0"] - p / 2, grid["z0"] - p / 2 - front * p])
    nodes_mm = origin + used * pitch

    padded = np.pad(kept, 1)
    quads, ids = [], []
    k_min = int(cells[:, 2].min())
    for d, corners in FACE_OF_DIRECTION.items():
        nb = padded[1 + d[0]:padded.shape[0] - 1 + d[0],
                    1 + d[1]:padded.shape[1] - 1 + d[1],
                    1 + d[2]:padded.shape[2] - 1 + d[2]]
        ext = np.argwhere(kept & ~nb)
        c = (ext[:, None, :] + HEX_CORNERS[corners][None]).reshape(-1, 3)
        quads.append(node_id[c[:, 0], c[:, 1], c[:, 2]].reshape(-1, 4))
        clamp = (ext[:, 2] == k_min) if d == (0, 0, -1) else np.zeros(len(ext), dtype=bool)
        ids.append(np.where(clamp, 4, 1))
    quads, ids = np.concatenate(quads), np.concatenate(ids)

    with open(case / "mesh.msh", "w") as out:
        out.write("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n%d\n" % len(nodes_mm))
        for i, q in enumerate(nodes_mm / 1000.0, 1):
            out.write("%d %.12g %.12g %.12g\n" % (i, q[0], q[1], q[2]))
        out.write("$EndNodes\n$Elements\n%d\n" % (len(hexes) + len(quads)))
        for i, c in enumerate(hexes + 1, 1):
            out.write("%d 5 2 0 1 %d %d %d %d %d %d %d %d\n" % (i, *c))
        for i, (c, b) in enumerate(zip(quads + 1, ids), len(hexes) + 1):
            out.write("%d 3 2 %d 1 %d %d %d %d\n" % (i, b, *c))
        out.write("$EndElements\n")

    dt = float(dt if dt is not None else DEFAULT_DT[pitch])
    factor = int(round(CASE["output_interval_s"] / dt))
    e, nu = MATERIAL["youngs_modulus_Pa"], MATERIAL["poisson_ratio"]
    deck = DECK.format(mesh_file="/case/mesh.msh", dt=dt, factor=factor,
                       lame_first=e * nu / ((1 + nu) * (1 - 2 * nu)), lame_second=e / (2 * (1 + nu)),
                       **{**MATERIAL, **CASE})
    (case / "cooldown.info").write_text(deck)
    rep = {
        "source": source,
        "witness": bool(witness),
        "pitch_mm": pitch,
        "fine_voxels_per_block_edge": k,
        "solid_rule": "block solid when at least half of its fine voxels have w > 0.5; largest face-connected component kept",
        "lattice_anchor_z_mm": float(grid["z0"] - p / 2 + z_anchor * p),
        "hexahedra": int(len(hexes)),
        "nodes": int(len(nodes_mm)),
        "components": int(count),
        "excluded_hexahedra": int(solid.sum() - len(hexes)),
        "exterior_faces": int(len(quads)),
        "clamped_faces": int((ids == 4).sum()),
        "clamped_plane_z_mm": float(origin[2] + k_min * pitch),
        "volume_mm3": float(len(hexes) * pitch ** 3),
        "exterior_area_mm2": float(len(quads) * pitch ** 2),
        "clamped_area_mm2": float((ids == 4).sum() * pitch ** 2),
        "fine_grid_inside_volume_mm3": fine_inside * p ** 3,
        "bounds_mm": [nodes_mm.min(axis=0).round(4).tolist(), nodes_mm.max(axis=0).round(4).tolist()],
        "time_step_s": dt,
        "steps_between_outputs_and_mechanical_solves": factor,
        "explicit_step_over_fourier_limit": dt / (pitch ** 2 * 1e-6 / (6 * MATERIAL["conductivity_W_mK"]
                                                  / (MATERIAL["density_kg_m3"] * MATERIAL["specific_heat_J_kgK"]))),
    }
    if exact:
        rep["exact"] = exact
    (case / "prepare.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))
    return rep


# --------------------------------------------------------------------------
# run


def image_identity() -> dict:
    def sh(*cmd):
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()

    inside = sh("docker", "run", "--rm", "--memory", "1g", "--entrypoint", "bash", IMAGE, "-c",
                "cat /home/adamantine/.git/refs/heads/master; "
                "grep -o 'project(Adamantine.*' /home/adamantine/CMakeLists.txt; "
                "sha256sum /usr/bin/adamantine | cut -d' ' -f1; mpirun --version | head -1").splitlines()
    return {
        "image": IMAGE,
        "image_id": sh("docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"),
        "repo_digests": sh("docker", "image", "inspect", IMAGE, "--format", "{{join .RepoDigests \" \"}}"),
        "source_commit_in_image": inside[0] if inside else None,
        "cmake_project_line": inside[1] if len(inside) > 1 else None,
        "executable_sha256": inside[2] if len(inside) > 2 else None,
        "mpi": inside[3] if len(inside) > 3 else None,
    }


def run(case: Path, ranks: int) -> dict:
    case = case.resolve()
    assert str(case).startswith("/home/"), "mount the case from /home, not from /tmp"
    cmd = ["docker", "run", "--rm", "--memory", MEMORY_CAP, "--memory-swap", MEMORY_CAP, "--cpus", str(ranks),
           "--user", "%d:%d" % (os.getuid(), os.getgid()),
           "-e", "HOME=/case", "-e", "OMP_NUM_THREADS=1", "-e", "OMP_PROC_BIND=false",
           "-e", "OPENBLAS_NUM_THREADS=1", "-e", "DEAL_II_NUM_THREADS=1",
           "-v", "%s:/case" % case, "-w", "/case", "--entrypoint", "mpirun", IMAGE,
           "-np", str(ranks), "adamantine", "--input-file", "/case/cooldown.info"]
    # Measured on 2026-11-10: this image's binary writes its VTU files beside
    # the input deck; --output-dir and the working directory do not move them.
    started = time.time()
    with open(case / "solver.log", "w") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    shown = " ".join(cmd).replace(str(case), "CASE_DIR").replace("%d:%d" % (os.getuid(), os.getgid()), "UID:GID")
    rep = {"command": shown, "returncode": rc,
           "wall_seconds": round(time.time() - started, 1), "mpi_ranks": ranks, "memory_cap": MEMORY_CAP,
           "threads_per_rank": 1, **image_identity()}
    (case / "run.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))
    return rep


# --------------------------------------------------------------------------
# check (independent of prepare: VTU files and declared constants only)


def vtu_array(item, header_dtype: str) -> np.ndarray:
    dtype = {"Float32": "<f4", "Float64": "<f8", "Int32": "<i4", "UInt32": "<u4", "Int64": "<i8",
             "UInt64": "<u8", "UInt8": "u1", "Int8": "i1"}[item.attrib["type"]]
    if item.attrib.get("format") == "ascii":
        data = np.array((item.text or "").split(), dtype=dtype)
    else:
        text = "".join((item.text or "").split())
        hs = np.dtype(header_dtype).itemsize

        def b64len(n):
            return 4 * ((n + 2) // 3)

        # The header (block count, block size, last size, compressed sizes)
        # is one base64 stream of its own; its first word gives its length.
        blocks = int(np.frombuffer(base64.b64decode(text[:b64len(3 * hs)])[:hs], dtype=header_dtype)[0])
        head_chars = b64len(hs * (3 + blocks))
        head = np.frombuffer(base64.b64decode(text[:head_chars]), dtype=header_dtype)
        raw = base64.b64decode(text[head_chars:])
        out, at = [], 0
        for size in head[3:]:
            out.append(zlib.decompress(raw[at:at + int(size)]))
            at += int(size)
        data = np.frombuffer(b"".join(out), dtype=dtype)
    comps = int(item.attrib.get("NumberOfComponents", 1))
    return data.reshape(-1, comps) if comps > 1 else data


def read_step(files: list[Path]) -> dict:
    pts, conn, fields, times, at = [], [], {}, [], 0
    for path in files:
        root = ET.parse(path).getroot()
        assert root.attrib.get("compressor", "vtkZLibDataCompressor") == "vtkZLibDataCompressor"
        hd = {"UInt32": "<u4", "UInt64": "<u8"}[root.attrib.get("header_type", "UInt32")]
        piece = root.find(".//Piece")
        x = vtu_array(piece.find("./Points/DataArray"), hd).astype(np.float64)
        cell = {q.attrib["Name"]: vtu_array(q, hd) for q in piece.findall("./Cells/DataArray")}
        if len(x) == 0:
            continue
        assert np.all(cell["types"] == 12), "expected linear hexahedra"
        assert np.all(np.diff(np.r_[0, cell["offsets"]]) == 8)
        pts.append(x)
        conn.append(cell["connectivity"].astype(np.int64).reshape(-1, 8) + at)
        at += len(x)
        for q in piece.findall("./PointData/DataArray"):
            fields.setdefault(q.attrib["Name"], []).append(vtu_array(q, hd))
        t = root.find(".//FieldData/DataArray[@Name='TIME']")
        if t is None:
            t = root.find(".//FieldData/DataArray")
        times.append(float(vtu_array(t, hd)[0]))
    assert max(times) - min(times) < 1e-12
    return {"x": np.concatenate(pts), "conn": np.concatenate(conn), "time": times[0],
            "fields": {k: np.concatenate(v) for k, v in fields.items()}}


VTK_HEX_FACES = np.array([[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])


def integrate_step(step: dict) -> dict:
    x, conn, f = step["x"], step["conn"], step["fields"]
    for name, q in f.items():
        assert np.isfinite(q).all(), name
    rho_cp = MATERIAL["density_kg_m3"] * MATERIAL["specific_heat_J_kgK"]
    xyz = x[conn]
    span = np.ptp(xyz, axis=1)
    # Axis-aligned boxes only: every corner sits on the cell's bounding box.
    lo, hi = xyz.min(axis=1, keepdims=True), xyz.max(axis=1, keepdims=True)
    assert np.all(np.minimum(np.abs(xyz - lo), np.abs(xyz - hi)) <= 1e-6 * span.max()), "cells are not boxes"
    volume = np.prod(span, axis=1)
    h = float(np.median(span))
    # Weld the per-cell duplicated points on a lattice of h/8.
    key = np.round(x / (h / 8.0)).astype(np.int64)
    _, weld = np.unique(key, axis=0, return_inverse=True)
    weld = weld.reshape(-1)
    faces = conn[:, VTK_HEX_FACES].reshape(-1, 4)
    _, first, uses = np.unique(np.sort(weld[faces], axis=1), axis=0, return_index=True, return_counts=True)
    assert uses.max() == 2, "a face is shared by more than two cells"
    ext = faces[first[uses == 1]]
    p = x[ext]
    area = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 3] - p[:, 0]), axis=1)
    temp = f["temperature"].astype(np.float64)
    # Trilinear on a box: the cell (face) mean is the mean of its corner values.
    t_cell, t_face = temp[conn].mean(axis=1), temp[ext].mean(axis=1)
    row = {
        "time_s": step["time"],
        "cells": int(len(conn)),
        "welded_nodes": int(weld.max() + 1),
        "cell_edge_mm": h * 1e3,
        "volume_mm3": float(volume.sum() * 1e9),
        "exterior_faces": int(len(ext)),
        "exterior_area_mm2": float(area.sum() * 1e6),
        "temperature_K_min": float(temp.min()),
        "temperature_K_max": float(temp.max()),
        "temperature_K_mean": float(np.dot(volume, t_cell) / volume.sum()),
        "thermal_energy_change_J": float(np.dot(volume, t_cell - CASE["initial_temperature_K"]) * rho_cp),
        "convective_loss_W": float(np.dot(area, t_face - CASE["ambient_temperature_K"])
                                   * CASE["film_coefficient_W_m2K"]),
    }
    if "displacement" in f:
        row["displacement_mm_max"] = float(np.linalg.norm(f["displacement"], axis=1).max() * 1e3)
    if "stress" in f:
        row["native_von_mises_cell_mean_MPa_max"] = float(f["stress"].max() * 1e-6)
        row["native_von_mises_cell_mean_MPa_p99"] = float(np.percentile(f["stress"], 99) * 1e-6)
    return row


def check(case: Path) -> dict:
    out = case
    steps = sorted({int(p.name.split(".")[1]) for p in out.glob("cooldown.*.*.vtu")})
    rows = [integrate_step(read_step(sorted(out.glob("cooldown.%d.*.vtu" % s)))) for s in steps]
    assert rows, "no VTU output"
    t = np.array([r["time_s"] for r in rows])
    q = np.array([r["convective_loss_W"] for r in rows])
    trap = float(np.sum(0.5 * (q[1:] + q[:-1]) * np.diff(t)))
    change = rows[-1]["thermal_energy_change_J"] - rows[0]["thermal_energy_change_J"]
    rep = {
        "method": "independent VTU reader: volume, welded exterior faces, energy and loss re-integrated from the files",
        "output_steps": steps,
        "rows": rows,
        "completed_requested_duration": bool(abs(t[-1] - CASE["duration_s"]) < 1e-6),
        "geometry_constant_over_outputs": bool(len({(r["cells"], r["exterior_faces"]) for r in rows}) == 1),
        "integrated_convective_loss_J_trapezoid": trap,
        "thermal_energy_change_J": change,
        "energy_imbalance_relative_trapezoid": abs(change + trap) / max(abs(change), abs(trap)),
    }
    if len(t) >= 3 and len(t) % 2 == 1 and np.allclose(np.diff(t), t[1] - t[0]):
        simpson = float((t[1] - t[0]) / 3.0 * (q[0] + q[-1] + 4 * q[1:-1:2].sum() + 2 * q[2:-1:2].sum()))
        rep["integrated_convective_loss_J_simpson"] = simpson
        rep["energy_imbalance_relative_simpson"] = abs(change + simpson) / max(abs(change), abs(simpson))
    # Second independent estimate: lumped capacitance on the re-derived V and A
    # (Biot number h V / (A k) is about 1e-3, so the body is nearly isothermal).
    v, a = rows[0]["volume_mm3"] * 1e-9, rows[0]["exterior_area_mm2"] * 1e-6
    tau = MATERIAL["density_kg_m3"] * MATERIAL["specific_heat_J_kgK"] * v / (CASE["film_coefficient_W_m2K"] * a)
    lumped = CASE["ambient_temperature_K"] + (CASE["initial_temperature_K"] - CASE["ambient_temperature_K"]) \
        * math.exp(-t[-1] / tau)
    drop = CASE["initial_temperature_K"] - rows[-1]["temperature_K_mean"]
    rep["lumped_capacitance"] = {
        "biot_number": CASE["film_coefficient_W_m2K"] * v / a / MATERIAL["conductivity_W_mK"],
        "time_constant_s": tau,
        "mean_temperature_K_at_end": lumped,
        "solver_minus_lumped_K": rows[-1]["temperature_K_mean"] - lumped,
        "relative_difference_of_mean_drop": (drop - (CASE["initial_temperature_K"] - lumped)) / drop if drop else None,
    }
    (case / "check.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}))
    return rep


# --------------------------------------------------------------------------
# summarize


def case_summary(case: Path) -> dict:
    prep = json.loads((case / "prepare.json").read_text())
    out = {"mesh_as_written": prep}
    if (case / "run.json").exists():
        r = json.loads((case / "run.json").read_text())
        out["solver"] = {k: r[k] for k in ("returncode", "wall_seconds", "mpi_ranks", "threads_per_rank", "memory_cap")}
        log = (case / "solver.log").read_text(errors="replace").strip().splitlines()
        out["solver"]["log_tail"] = log[-6:]
    if (case / "check.json").exists():
        c = json.loads((case / "check.json").read_text())
        first, last = c["rows"][0], c["rows"][-1]
        out["independent_check"] = {k: v for k, v in c.items() if k != "method"}
        out["reread_vs_written"] = {
            "cells_match": first["cells"] == prep["hexahedra"],
            "nodes_match": first["welded_nodes"] == prep["nodes"],
            "exterior_faces_match": first["exterior_faces"] == prep["exterior_faces"],
            "volume_relative_difference": first["volume_mm3"] / prep["volume_mm3"] - 1.0,
            "area_relative_difference": first["exterior_area_mm2"] / prep["exterior_area_mm2"] - 1.0,
        }
        if "exact" in prep:
            out["reread_vs_exact"] = {
                "volume_relative_difference": first["volume_mm3"] / prep["exact"]["volume_mm3"] - 1.0,
                "area_relative_difference": first["exterior_area_mm2"] / prep["exact"]["area_mm2"] - 1.0,
            }
        out["at_end"] = {k: last[k] for k in last if k not in ("cells", "welded_nodes", "exterior_faces")}
    return out


def stl_area_volume(path: Path) -> tuple[float, float]:
    rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    tri = np.fromfile(path, dtype=rec, offset=84)["v"].astype(np.float64)
    cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return float(0.5 * np.linalg.norm(cr, axis=1).sum()), float(np.einsum("ij,ij->", tri[:, 0], cr) / 6.0)


def summarize(study: Path, out_json: Path, private: Path | None = None) -> dict:
    levels = {}
    for name, key in (("cooldown-4mm", "hex_4mm"), ("cooldown-2mm", "hex_2mm"), ("cooldown-witness", "witness_block")):
        if (study / name / "prepare.json").exists():
            levels[key] = case_summary(study / name)
    rep = {
        "schema": "935-cad-twin-am-cooldown/1",
        "scope": "declared-hypothesis screen: first 20 s of convective cooldown of an assumed fully solid, "
                 "initially stress-free and isothermal twin body on voxel hexahedra; no laser, deposition, powder, "
                 "plasticity or build simulation; no material or process qualification",
        "solver": "Adamantine (thermal: explicit RK4, matrix-free; mechanical: linear thermo-elastic, CG)",
        "material": MATERIAL,
        "case": CASE,
        "levels": levels,
    }
    for name in ("cooldown-4mm", "cooldown-2mm", "cooldown-witness"):
        if (study / name / "run.json").exists():
            r = json.loads((study / name / "run.json").read_text())
            rep["runtime"] = {k: r[k] for k in ("image", "image_id", "repo_digests", "source_commit_in_image",
                                                "cmake_project_line", "executable_sha256", "mpi", "command")}
            break
    a, b = levels.get("hex_4mm", {}).get("at_end"), levels.get("hex_2mm", {}).get("at_end")
    if a and b:
        def rel(key):
            return (b[key] - a[key]) / a[key]

        t0 = CASE["initial_temperature_K"]
        rep["difference_2mm_vs_4mm"] = {
            "volume_relative": rel("volume_mm3"),
            "exterior_area_relative": rel("exterior_area_mm2"),
            "mean_temperature_K": b["temperature_K_mean"] - a["temperature_K_mean"],
            "mean_temperature_drop_relative": (t0 - b["temperature_K_mean"]) / (t0 - a["temperature_K_mean"]) - 1.0,
            "minimum_temperature_K": b["temperature_K_min"] - a["temperature_K_min"],
            "thermal_energy_change_relative": rel("thermal_energy_change_J"),
            "displacement_max_relative": rel("displacement_mm_max") if "displacement_mm_max" in a else None,
            "native_von_mises_max_relative": rel("native_von_mises_cell_mean_MPa_max")
            if "native_von_mises_cell_mean_MPa_max" in a else None,
        }
    if private is not None:
        ref = {}
        for label, name in (("t1s_clean", "t1s-clean.stl"), ("mc_1p0mm", "t1-sim-mc100.stl")):
            if (private / name).exists():
                area, vol = stl_area_volume(private / name)
                ref[label] = {"area_mm2": round(area, 1), "volume_mm3": round(vol, 1)}
        rep["reference_surfaces"] = ref
        if "t1s_clean" in ref:
            # What both voxel meshes approximate, if the body stays isothermal.
            tau = MATERIAL["density_kg_m3"] * MATERIAL["specific_heat_J_kgK"] * ref["t1s_clean"]["volume_mm3"] * 1e-9 \
                / (CASE["film_coefficient_W_m2K"] * ref["t1s_clean"]["area_mm2"] * 1e-6)
            rep["lumped_capacitance_on_t1s_surface"] = {
                "time_constant_s": tau,
                "mean_temperature_K_at_end": CASE["ambient_temperature_K"]
                + (CASE["initial_temperature_K"] - CASE["ambient_temperature_K"])
                * math.exp(-CASE["duration_s"] / tau),
            }
        for key in ("hex_4mm", "hex_2mm"):
            if key in levels and "t1s_clean" in ref:
                m = levels[key]["mesh_as_written"]
                levels[key]["hex_vs_t1s_surface"] = {
                    "volume_relative_difference": m["volume_mm3"] / ref["t1s_clean"]["volume_mm3"] - 1.0,
                    "exterior_area_relative_difference": m["exterior_area_mm2"] / ref["t1s_clean"]["area_mm2"] - 1.0,
                }
    rep["limits"] = (
        "Numerical screen under declared hypotheses, uncorrelated with any build or measurement. The body is the "
        "study twin (1 scan unit = 1 mm by owner instruction; unobserved geometry closed by hypotheses), blocked "
        "into cubes: walls and gaps thinner than the pitch are merged or lost, and the stair-step exterior area "
        "does not converge to the surface area. With a Biot number near 1e-3 the mean temperature follows "
        "h*A/(rho*cp*V), so the difference between the two pitches is a difference of discrete area and volume, "
        "not a discretisation error estimate. Cell-mean von Mises values sit at re-entrant voxel corners where the "
        "elastic solution is singular; they are reported as solver output, not as stresses, and their maximum "
        "must not be quoted as a margin. Uniform 500 K start, h = 20 W/m2K, clamped lowest face, elastic "
        "constants and the AlSi10Mg-class properties are assumptions. No laser, layer deposition, powder bed, "
        "residual-stress build-up, support, distortion compensation, porosity or microstructure is modelled. "
        "Nothing here establishes printability, material, dimensional accuracy or function."
    )
    out_json.write_text(json.dumps(rep, indent=2) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prepare")
    s.add_argument("private", type=Path)
    s.add_argument("case", type=Path)
    s.add_argument("--pitch", type=float, required=True)
    s.add_argument("--dt", type=float)
    s.add_argument("--witness", action="store_true")
    s = sub.add_parser("run")
    s.add_argument("case", type=Path)
    s.add_argument("--ranks", type=int, default=4)
    s = sub.add_parser("check")
    s.add_argument("case", type=Path)
    s = sub.add_parser("summarize")
    s.add_argument("study", type=Path)
    s.add_argument("out", type=Path)
    s.add_argument("--private", type=Path)
    s = sub.add_parser("all")
    s.add_argument("private", type=Path)
    s.add_argument("params", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        prepare(a.private, a.case, a.pitch, a.dt, a.witness)
    elif a.cmd == "run":
        sys.exit(1 if run(a.case, a.ranks)["returncode"] else 0)
    elif a.cmd == "check":
        check(a.case)
    elif a.cmd == "summarize":
        summarize(a.study, a.out, a.private)
    else:
        study = a.private / "am-study"
        study.mkdir(exist_ok=True)
        for name, pitch, witness, ranks in (("cooldown-witness", 4.0, True, 1), ("cooldown-4mm", 4.0, False, 4),
                                            ("cooldown-2mm", 2.0, False, 4)):
            case = study / name
            if not case.exists():
                prepare(a.private, case, pitch, None, witness)
            if not (case / "run.json").exists():
                run(case, ranks)
            check(case)
        summarize(study, a.params / "am-cooldown.json", a.private)


if __name__ == "__main__":
    main()
