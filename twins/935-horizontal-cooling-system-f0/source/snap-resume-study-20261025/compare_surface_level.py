"""Compare the pinned 935 level-(3 4) and level-(3 3) native mesh trials."""

import gzip
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile

import numpy as np
import trimesh

from compare_snap_tolerance import (
    PARENT_SHA, PARENT_WALL_GZ_SHA, PARENT_WALL_SHA, QUALITY_SHA, ROTOR_SHA,
    PARENT, digest, distances, extract_rotor_wall, member, member_digest,
    member_text, mesh_metrics, summary,
)
from localize_concave_cells import read_label_list, read_set


CHILD_SHA = "62b9411a409c56513a82575c7a8039e6a4c203173d89b5827e06555f412033be"
CHILD_WALL_SHA = "0636dde25fb5f73df7d86b645368c057178fe50f28bdbfa5a9c30f94b8b9f0b3"
CHILD = "level33-case"


def run(parent_path, child_path, parent_wall_gz, output):
    paths = [path.resolve() for path in (parent_path, child_path, parent_wall_gz)]
    output = output.resolve()
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report path")
    if tuple(map(digest, paths)) != (PARENT_SHA, CHILD_SHA, PARENT_WALL_GZ_SHA):
        raise ValueError("Pinned archive or parent wall changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(paths[0], "r:gz") as parent, tarfile.open(paths[1], "r:gz") as child:
        common = ("system/blockMeshDict", "system/controlDict", "system/fvSchemes",
                  "system/fvSolution", "system/meshQualityDict", "constant/triSurface/rotor.obj")
        hashes = {}
        for name in common:
            old = member_digest(parent, f"{PARENT}/{name}")
            new = member_digest(child, f"{CHILD}/{name}")
            if old != new:
                raise ValueError(f"Common input changed: {name}")
            hashes[name] = old
        if (hashes["system/meshQualityDict"] != QUALITY_SHA
                or hashes["constant/triSurface/rotor.obj"] != ROTOR_SHA):
            raise ValueError("Unexpected corrected rotor or quality dictionary")
        old_dict = member_text(parent, f"{PARENT}/system/snappyHexMeshDict")
        new_dict = member_text(child, f"{CHILD}/system/snappyHexMeshDict")
        if (old_dict.count("level (3 4);") != 1
                or new_dict.count("level (3 3);") != 1
                or new_dict.replace("level (3 3);", "level (3 4);") != old_dict):
            raise ValueError("Snappy inputs changed beyond rotor surface level")
        old_mesh = mesh_metrics(member_text(parent, f"{PARENT}/log.checkMesh.full"))
        new_mesh = mesh_metrics(member_text(child, f"{CHILD}/log.checkMesh.full"))
        snap_log = member_text(child, f"{CHILD}/log.snappyHexMesh")
        if snap_log.count("Finished meshing without any errors") != 1:
            raise ValueError("New native meshing did not finish")
        elapsed = re.search(r"Finished meshing in = ([0-9.]+) s\.", snap_log)
        if elapsed is None:
            raise ValueError("Native meshing duration missing")
        with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
            folder = Path(temporary)
            rotor_path = folder / "rotor.obj"
            with member(child, f"{CHILD}/constant/triSurface/rotor.obj") as source, rotor_path.open("wb") as dest:
                shutil.copyfileobj(source, dest)
            old_wall = folder / "parent-rotor-wall.stl"
            new_wall = folder / "child-rotor-wall.stl"
            with gzip.open(paths[2], "rb") as source:
                extract_rotor_wall(source, old_wall)
            with member(child, f"{CHILD}/boundary.stl") as source:
                extract_rotor_wall(source, new_wall)
            if digest(old_wall) != PARENT_WALL_SHA or digest(new_wall) != CHILD_WALL_SHA:
                raise ValueError("Extracted rotor wall changed")
            rotor = trimesh.load_mesh(rotor_path, process=True)
            if len(rotor.vertices) != 439365 or len(rotor.faces) != 878730:
                raise ValueError("Corrected rotor topology changed")
            walls = {}
            for label, path in (("parent", old_wall), ("child", new_wall)):
                wall = trimesh.load_mesh(path, process=True)
                rotor_to_wall = distances(rotor, wall)
                worst = int(np.argmax(rotor_to_wall))
                walls[label] = {
                    "sha256": digest(path), "vertices": len(wall.vertices),
                    "faces": len(wall.faces),
                    "wall_to_rotor": summary(distances(wall, rotor)),
                    "rotor_to_wall": summary(rotor_to_wall),
                    "worst_rotor_vertex_index": worst,
                    "worst_rotor_vertex_m_conditional": rotor.vertices[worst].tolist(),
                }
            mesh = folder / "native-mesh"
            for name in ("cellLevel", "owner", "neighbour", "sets/concaveCells"):
                destination = mesh / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with member(child, f"{CHILD}/constant/polyMesh/{name}") as source, destination.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
            levels = read_label_list(mesh / "cellLevel")
            owner = read_label_list(mesh / "owner")
            neighbour = read_label_list(mesh / "neighbour")
            bad_ids = read_set(mesh / "sets/concaveCells")
            if len(levels) != new_mesh["cells"] or len(bad_ids) != new_mesh["concave_cells"]:
                raise ValueError("Native cell levels or concave set disagree with checkMesh")
            if (len(neighbour) >= len(owner) or owner.min() < 0 or neighbour.min() < 0
                    or owner.max() >= len(levels) or neighbour.max() >= len(levels)):
                raise ValueError("Invalid native face ownership")
            bad = np.zeros(len(levels), dtype=bool)
            bad[bad_ids] = True
            inner_owner = owner[:len(neighbour)]
            jumps = np.abs(levels[inner_owner] - levels[neighbour])
            if jumps.max() > 1:
                raise ValueError("Unexpected refinement-level jump")
            adjacent = np.zeros(len(levels), dtype=bool)
            crossing = jumps != 0
            adjacent[inner_owner[crossing]] = True
            adjacent[neighbour[crossing]] = True
            pairs = []
            for lower in range(int(levels.max())):
                faces = ((levels[inner_owner] == lower) & (levels[neighbour] == lower + 1)
                         | (levels[inner_owner] == lower + 1) & (levels[neighbour] == lower))
                touched = np.zeros(len(levels), dtype=bool)
                touched[inner_owner[faces]] = True
                touched[neighbour[faces]] = True
                pairs.append({"levels": [lower, lower + 1],
                              "internal_faces": int(np.count_nonzero(faces)),
                              "lower_side_concave_cells": int(np.count_nonzero(touched & (levels == lower) & bad)),
                              "higher_side_concave_cells": int(np.count_nonzero(touched & (levels == lower + 1) & bad))})
            topology = {"native_input_sha256": {
                name: digest(mesh / name) for name in
                ("cellLevel", "owner", "neighbour", "sets/concaveCells")},
                "transition_adjacent_cells": int(np.count_nonzero(adjacent)),
                "transition_adjacent_concave_cells": int(np.count_nonzero(adjacent & bad)),
                "other_concave_cells": int(np.count_nonzero(~adjacent & bad)),
                "by_transition_pair": pairs}
    if old_mesh["failed_mesh_checks"] < 1 or new_mesh["failed_mesh_checks"] < 1:
        raise ValueError("Native mesh admission state changed")
    result = {
        "status": "rejected_uniform_surface_level_no_CFD",
        "archive_sha256": {"parent": PARENT_SHA, "child": CHILD_SHA,
                           "parent_boundary_stl_gz": PARENT_WALL_GZ_SHA},
        "common_input_sha256": hashes,
        "only_snappy_dictionary_change": "rotor refinementSurfaces.level (3 4) -> (3 3)",
        "checkMesh": {"parent": old_mesh, "child": new_mesh},
        "concave_cell_fraction": {
            "parent": old_mesh["concave_cells"] / old_mesh["cells"],
            "child": new_mesh["concave_cells"] / new_mesh["cells"]},
        "new_snappy_duration_s": float(elapsed[1]),
        "rotor_wall_vertex_distances": walls,
        "child_concavity_topology": topology,
        "all_unique_vertices_checked": True,
        "triangle_interior_supremum_verified": False,
        "source_unit_to_mm_verified": False,
        "full_checkMesh_passed": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    output.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(output),
                      "child_concave_cells": new_mesh["concave_cells"]}))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: compare_surface_level.py PARENT_ARCHIVE CHILD_ARCHIVE PARENT_WALL_GZ NEW_PRIVATE_REPORT")
    run(*(Path(item) for item in sys.argv[1:]))
