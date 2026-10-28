"""Compare the pinned 935 snap-tolerance trial, including rotor-wall vertices.

The scan scale remains conditional. A passing script does not admit CFD: the
complete native checkMesh result is the quality gate.
"""

import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile

import numpy as np
import trimesh
from trimesh.proximity import closest_point


PARENT_SHA = "dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41"
CHILD_SHA = "5ce390801d28af9590affc0e41f382eeb82a936320450c5cef39ceacf9876c63"
PARENT_WALL_GZ_SHA = "4f7fba20703cf431153dd79379b1dfa934b666c0fceb949ba035c9a2fc01d624"
ROTOR_SHA = "ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6"
QUALITY_SHA = "bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d"
PARENT_WALL_SHA = "d1d56bd0f3dc7bafbfd83cb3b11629037c640c1c1736b0780aec012fa5e63d79"
CHILD_WALL_SHA = "0b06d70152fdc3e563dc608b17e3ddf6e3709dd779b9ff9e85bb1914ee324300"
PARENT = "snappy-refine34-spaced3-20261028"
CHILD = "tolerance1-case"


def sha_stream(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(block)
    return value.hexdigest()


def digest(path):
    with path.open("rb") as stream:
        return sha_stream(stream)


def member(archive, name):
    stream = archive.extractfile(name)
    if stream is None:
        raise ValueError(f"Missing archive member: {name}")
    return stream


def member_digest(archive, name):
    with member(archive, name) as stream:
        return sha_stream(stream)


def member_text(archive, name):
    with member(archive, name) as stream:
        return stream.read().decode("utf-8")


def metric(log, expression):
    matches = re.findall(expression, log, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"Expected one native log value matching {expression}")
    return int(matches[0])


def mesh_metrics(log):
    return {
        "cells": metric(log, r"^\s+cells:\s+(\d+)\s*$"),
        "concave_cells": metric(log, r"^ \*\*\*Concave cells \(using face planes\) found, number of cells: (\d+)"),
        "failed_mesh_checks": metric(log, r"^Failed (\d+) mesh checks\.\s*$"),
    }


def extract_rotor_wall(source, destination):
    active = False
    found = 0
    with destination.open("wb") as output:
        for line in source:
            if line == b"solid rotor\n":
                if active:
                    raise ValueError("Nested rotor STL section")
                active = True
                found += 1
            if active:
                output.write(line)
            if line == b"endsolid rotor\n" and active:
                active = False
    if found != 1 or active:
        raise ValueError("Expected one complete rotor STL section")


def distances(source, target):
    chunks = []
    for start in range(0, len(source.vertices), 5000):
        _, values, _ = closest_point(target, source.vertices[start:start + 5000])
        if not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError("Invalid closest-triangle distances")
        chunks.append(values)
    return np.concatenate(chunks)


def summary(values):
    return {f"{name}_mm_conditional": float(np.quantile(values, quantile) * 1000)
            for name, quantile in (("p50", .5), ("p95", .95), ("p99", .99))} | {
                "max_mm_conditional": float(values.max() * 1000)}


def run(parent_path, child_path, parent_wall_gz, output):
    paths = [path.resolve() for path in (parent_path, child_path, parent_wall_gz)]
    output = output.resolve()
    work = (Path.cwd() / "work").resolve()
    if output.exists() or not output.is_relative_to(work):
        raise ValueError("Use a new private work/ report path")
    expected = (PARENT_SHA, CHILD_SHA, PARENT_WALL_GZ_SHA)
    if tuple(map(digest, paths)) != expected:
        raise ValueError("Pinned archive or parent wall changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(paths[0], "r:gz") as parent, tarfile.open(paths[1], "r:gz") as child:
        common = ("system/blockMeshDict", "system/controlDict", "system/fvSchemes",
                  "system/fvSolution", "system/meshQualityDict", "constant/triSurface/rotor.obj")
        common_hashes = {}
        for item in common:
            old = member_digest(parent, f"{PARENT}/{item}")
            new = member_digest(child, f"{CHILD}/{item}")
            if old != new:
                raise ValueError(f"Common input changed: {item}")
            common_hashes[item] = old
        if (common_hashes["system/meshQualityDict"] != QUALITY_SHA
                or common_hashes["constant/triSurface/rotor.obj"] != ROTOR_SHA):
            raise ValueError("Unexpected corrected rotor or quality controls")
        old_dict = member_text(parent, f"{PARENT}/system/snappyHexMeshDict")
        new_dict = member_text(child, f"{CHILD}/system/snappyHexMeshDict")
        if (old_dict.count("tolerance 2.0;") != 1
                or new_dict.count("tolerance 1.0;") != 1
                or new_dict.replace("tolerance 1.0;", "tolerance 2.0;") != old_dict):
            raise ValueError("snappyHexMesh inputs changed beyond snap tolerance")
        old_mesh = mesh_metrics(member_text(parent, f"{PARENT}/log.checkMesh.full"))
        new_mesh = mesh_metrics(member_text(child, f"{CHILD}/log.checkMesh.full"))
        snap_log = member_text(child, f"{CHILD}/log.snappyHexMesh")
        if snap_log.count("Finished meshing without any errors") != 1:
            raise ValueError("New snappyHexMesh run did not finish")
        elapsed = re.search(r"Finished meshing in = ([0-9.]+) s\.", snap_log)
        if elapsed is None:
            raise ValueError("Missing native meshing duration")
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
                walls[label] = {
                    "sha256": digest(path), "vertices": len(wall.vertices),
                    "faces": len(wall.faces),
                    "wall_to_rotor": summary(distances(wall, rotor)),
                    "rotor_to_wall": summary(distances(rotor, wall)),
                }
    if old_mesh["failed_mesh_checks"] < 1 or new_mesh["failed_mesh_checks"] < 1:
        raise ValueError("Mesh admission state changed; review natively")
    report = {
        "status": "rejected_snap_tolerance_trial_no_CFD",
        "archive_sha256": {"parent": PARENT_SHA, "child": CHILD_SHA,
                           "parent_boundary_stl_gz": PARENT_WALL_GZ_SHA},
        "common_input_sha256": common_hashes,
        "only_snappy_dictionary_change": "snapControls.tolerance 2.0 -> 1.0",
        "checkMesh": {"parent": old_mesh, "child": new_mesh},
        "delta_concave_cells": new_mesh["concave_cells"] - old_mesh["concave_cells"],
        "new_snappy_duration_s": float(elapsed[1]),
        "rotor_wall_vertex_distances": walls,
        "all_unique_vertices_checked": True,
        "triangle_interior_supremum_verified": False,
        "source_unit_to_mm_verified": False,
        "full_checkMesh_passed": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    output.chmod(0o600)
    print(json.dumps({"status": report["status"], "report_sha256": digest(output),
                      "delta_concave_cells": report["delta_concave_cells"]}))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: compare_snap_tolerance.py PARENT_ARCHIVE CHILD_ARCHIVE PARENT_WALL_GZ NEW_PRIVATE_REPORT")
    run(*(Path(item) for item in sys.argv[1:]))
