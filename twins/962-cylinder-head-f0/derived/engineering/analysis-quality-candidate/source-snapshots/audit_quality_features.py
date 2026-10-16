"""Exact indexed patch continuity and eight float64 opening probes, not an OEM map."""
import argparse
from collections import Counter, defaultdict
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from audit_quality_head import read, qualities
from mesh_head import ROOT, FAMILY, array_sha, new_output, sha
from prepare_head_analysis import polydata

CONTRACT = FAMILY / "engineering/analysis-quality-features-contract.json"
OUTPUT = ROOT / "work/962-engineering/quality-patch-features-001"


def write_new(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def connected(nodes, edges):
    neighbours = {int(v): set() for v in nodes}
    for a, b in edges:
        neighbours[int(a)].add(int(b)); neighbours[int(b)].add(int(a))
    count = 0; unseen = set(neighbours)
    while unseen:
        count += 1; pending = [unseen.pop()]
        while pending:
            for v in neighbours[pending.pop()] & unseen:
                unseen.remove(v); pending.append(v)
    return count


def patch_groups(faces):
    incidence = defaultdict(list)
    for i, row in enumerate(faces):
        for a, b in zip(row, np.roll(row, -1)):
            incidence[tuple(sorted((int(a), int(b))))].append(i)
    neighbours = [set() for _ in faces]
    for incident in incidence.values():
        for i in incident:
            neighbours[i].update(set(incident) - {i})
    unseen = set(range(len(faces))); groups = []
    while unseen:
        first = min(unseen); unseen.remove(first); pending = [first]; group = []
        while pending:
            i = pending.pop(); group.append(i)
            for j in neighbours[i] & unseen:
                unseen.remove(j); pending.append(j)
        groups.append(np.array(sorted(group), dtype=np.int64))
    return groups


def patch_topology(faces):
    directed = [(int(a), int(b)) for row in faces for a, b in zip(row, np.roll(row, -1))]
    counts = Counter(tuple(sorted(edge)) for edge in directed)
    balance = Counter()
    for a, b in directed:
        balance[tuple(sorted((a, b)))] += 1 if a < b else -1
    if any(n not in (1, 2) for n in counts.values()) or any(counts[e] == 2 and v for e, v in balance.items()):
        raise ValueError("Patch edge manifold/orientation failure")
    boundary = sorted(edge for edge in directed if counts[tuple(sorted(edge))] == 1)
    incoming, outgoing = Counter(b for a, b in boundary), Counter(a for a, b in boundary)
    if incoming != outgoing or any(n != 1 for n in incoming.values()):
        raise ValueError("Patch boundary must consist of disjoint oriented loops")
    vertices = sorted(set(int(v) for v in faces.flat)); boundary_vertices = set(incoming)
    links = defaultdict(list)
    for row in faces:
        for i, v in enumerate(row):
            links[int(v)].append((int(row[(i+1) % 3]), int(row[(i+2) % 3])))
    for v, edges in links.items():
        degrees = Counter(x for e in edges for x in e)
        expected = sorted([1, 1] + [2]*(len(degrees)-2)) if v in boundary_vertices else [2]*len(degrees)
        if connected(degrees, edges) != 1 or sorted(degrees.values()) != expected:
            raise ValueError("Patch vertex link is not a boundary path or interior cycle")
    result = dict(vertices=len(vertices), edges=len(counts), faces=len(faces),
        euler_characteristic=len(vertices)-len(counts)+len(faces),
        components=len(patch_groups(faces)), boundary_loops=connected(boundary_vertices, boundary) if boundary else 0,
        boundary_vertices=len(boundary_vertices), boundary_edges=len(boundary), vertex_link_manifold=True)
    if result["components"] != 1:
        raise ValueError("A patch must remain connected")
    return result, np.asarray(boundary, dtype=np.int64).reshape(-1, 2)


def compare_patch(p, f, q, g):
    before, boundary = patch_topology(f); after, other = patch_topology(g)
    if before != after or not np.array_equal(boundary, other):
        raise ValueError("Patch topology or exact oriented boundary changed")
    ids = np.unique(boundary)
    if not np.array_equal(p[ids], q[ids]):
        raise ValueError("Fixed patch boundary coordinates changed")
    return before, boundary


def verify(contract):
    if sha(Path(contract["interpreter"]).resolve()) != contract["interpreter_sha256"]:
        raise ValueError("Pinned feature-audit interpreter changed")
    for name, digest in contract["input_hashes"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Frozen feature input changed: " + name)


def distance(poly):
    from vtkmodules.vtkFiltersCore import vtkImplicitPolyDataDistance
    result = vtkImplicitPolyDataDistance(); result.SetInput(poly)
    return result


def audit(contract):
    from vtkmodules.vtkCommonCore import vtkVersion, vtkMultiThreader, vtkSMPTools
    from vtkmodules.util.numpy_support import vtk_to_numpy
    vtkMultiThreader.SetGlobalMaximumNumberOfThreads(2); vtkSMPTools.Initialize(2)
    runtime = dict(vtk_version=vtkVersion.GetVTKVersion(), module_hashes={n: sha(Path(importlib.import_module(n).__file__))
        for n in contract["runtime"]["module_hashes"]})
    if runtime != contract["runtime"]:
        raise ValueError("Pinned VTK modules changed")
    tetra = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    tf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
    td = distance(polydata(tetra, tf)); fixture = [td.EvaluateFunction((.25, .25, .25)), td.EvaluateFunction((2., 2., 2.))]
    expected = [-.25/math.sqrt(3), 5/math.sqrt(3)]
    if any(abs(a-b) > 1e-12 for a, b in zip(fixture, expected)):
        raise ValueError("Known unit-tetrahedron signed-distance fixture failed")
    p, f = read(ROOT / contract["original"]); q, g = read(ROOT / contract["candidate"])
    hashes = [array_sha(a) for a in (p, f, q, g)]
    if p.shape != q.shape or f.shape != g.shape:
        raise ValueError("Original indexed count identity changed")
    bad = qualities(p, f) < 2/29; seeds = np.unique(f[bad]); mask = np.any(np.isin(f, seeds), axis=1)
    indices = np.flatnonzero(mask); groups = patch_groups(f[mask])
    if int(bad.sum()) != 744 or len(seeds) != 1284 or int(mask.sum()) != 4704 or len(groups) != 228:
        raise ValueError("Frozen exact-incidence patch partition changed")
    rows = []
    for i, group in enumerate(groups):
        selected = indices[group]; before, boundary = compare_patch(p, f[selected], q, g[selected])
        ids = np.unique(f[selected]); moved = ids[np.any(p[ids] != q[ids], axis=1)]
        rows.append(dict(patch_id=i, first_source_face=int(selected[0]), source_face_indices_sha256=array_sha(selected),
            topology=before, is_disk=before["euler_characteristic"] == 1 and before["boundary_loops"] == 1,
            exact_oriented_boundary_indices_sha256=array_sha(boundary),
            exact_boundary_coordinates_sha256=array_sha(p[np.unique(boundary)]),
            boundary_coordinates_unchanged=True, source_bounds_mm=[p[ids].min(axis=0).tolist(), p[ids].max(axis=0).tolist()],
            candidate_bounds_mm=[q[ids].min(axis=0).tolist(), q[ids].max(axis=0).tolist()],
            moved_vertices=len(moved)))
    retained = json.loads((ROOT / contract["retained_inspection"]).read_text())
    points = retained["dry_opening_probes_mm"]
    if points != contract["opening_points_mm"] or len(points) != 8:
        raise ValueError("All eight exact retained opening points required")
    probes = []
    for name, xyz, triangles in (("original", p, f), ("candidate", q, g)):
        poly = polydata(xyz, triangles)
        if not np.array_equal(vtk_to_numpy(poly.GetPoints().GetData()), xyz):
            raise ValueError("Direct float64 VTK coordinates changed")
        if not np.array_equal(vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1, 3), triangles):
            raise ValueError("Direct indexed VTK triangles changed")
        fn = distance(poly); values = [float(fn.EvaluateFunction(point)) for point in points]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("Retained dry-opening point is blocked or ambiguous")
        probes.append(dict(surface=name, signed_distances_mm=values, all_strictly_outside_metal=True,
            vtk_point_scalar_type=poly.GetPoints().GetData().GetDataTypeAsString(), exact_indexed_roundtrip=True))
    verify(contract)
    if hashes != [array_sha(a) for a in (p, f, q, g)]:
        raise ValueError("Input arrays changed during feature audit")
    return dict(status="scoped_original_bionic_patch_and_opening_continuity_passed", runtime=runtime,
        vtk_thread_control=dict(global_maximum=vtkMultiThreader.GetGlobalMaximumNumberOfThreads(),
            SMP_estimated_threads=vtkSMPTools.GetEstimatedNumberOfThreads(), hard_OS_CPU_quota_claimed=False),
        known_tetrahedron_distance_fixture=dict(observed=fixture, expected=expected, fixture_only_absolute_error_bound_mm=1e-12),
        exact_incidence_mask_sha256=array_sha(mask), patch_count=len(rows), disk_patch_count=sum(r["is_disk"] for r in rows),
        all_patch_topology_and_fixed_boundaries_retained=True, patches=rows,
        opening_points_mm=points, opening_probes=probes, retained_water_dry_clearance_mm=retained["sampled_water_dry_clearance_mm"],
        retained_water_dry_clearance_samples=retained["clearance_samples"],
        unchanged_fluid_mesh_sha256={name: sha(ROOT / path) for name, path in contract["fluid_meshes"].items()},
        retained_inspection_sha256=sha(ROOT / contract["retained_inspection"]),
        retained_clearance_scope="Unchanged water/dry meshes only; not candidate metal-wall thickness or conformal interface proof.",
        bound_inputs_and_arrays_unchanged=True, complete_semantic_feature_map=False,
        candidate_wall_clearance_qualified=False, conformal_metal_fluid_interface_validated=False,
        solver_admission_established=False, engineering_accepted=False, manufacturing_authorized=False)


def run(worker=False):
    contract = json.loads(CONTRACT.read_text()); verify(contract)
    if worker:
        launch = json.loads((OUTPUT / "running-receipt.json").read_text())
        if (sha(CONTRACT) != launch["contract_sha256"] or sha(Path(__file__)) != launch["source_sha256"]
                or sha(OUTPUT / "frozen-contract.json") != launch["contract_sha256"]):
            raise ValueError("Bound feature controller required")
        for name, digest in contract["input_hashes"].items():
            if name.endswith(".py") and sha(OUTPUT / "source-snapshots" / Path(name).name) != digest:
                raise ValueError("Bound feature source snapshot changed")
        with (OUTPUT / "worker-claimed.json").open("x") as stream: json.dump(dict(pid=os.getpid()), stream)
        started = time.monotonic()
        try:
            result = audit(contract)
            if sha(CONTRACT) != launch["contract_sha256"]:
                raise ValueError("Feature contract changed during audit")
        except Exception as exc:
            result = dict(status="failed_or_rejected_outputs_preserved", error=type(exc).__name__+": "+str(exc),
                solver_admission_established=False, engineering_accepted=False, manufacturing_authorized=False)
        result["wall_seconds"] = time.monotonic()-started
        write_new(OUTPUT / "worker-report.json", result)
        return 0 if result["status"].startswith("scoped_") else 2
    new_output(OUTPUT)
    (OUTPUT / "frozen-contract.json").write_bytes(CONTRACT.read_bytes())
    snapshots = OUTPUT / "source-snapshots"; snapshots.mkdir()
    for name in contract["input_hashes"]:
        if name.endswith(".py"): (snapshots / Path(name).name).write_bytes((ROOT / name).read_bytes())
    command = [str(ROOT / contract["interpreter"]), "-B", str(Path(__file__).resolve()), "--worker"]
    receipt = dict(status="running", command=command, contract_sha256=sha(CONTRACT), source_sha256=sha(Path(__file__)),
        hard_wall_seconds=120, thread_caps=2, solver_admission_established=False, manufacturing_authorized=False)
    write_new(OUTPUT / "running-receipt.json", receipt); started = time.monotonic()
    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2")
    with (OUTPUT / "native.log").open("x") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        timeout = False
        try: process.wait(timeout=120)
        except subprocess.TimeoutExpired: timeout=True; process.kill(); process.wait(timeout=10)
    receipt.update(returncode=process.returncode, deadline_exceeded=timeout, wall_seconds=time.monotonic()-started,
        native_log_sha256=sha(OUTPUT / "native.log"))
    result = OUTPUT / "worker-report.json"
    if result.exists(): receipt.update(worker_report_sha256=sha(result), worker_report=json.loads(result.read_text()))
    receipt["status"] = "scoped_feature_subgates_passed_no_solver_admission" if process.returncode == 0 and not timeout else "failed_or_rejected_outputs_preserved"
    write_new(OUTPUT / "receipt.json", receipt)
    print(json.dumps({k:receipt[k] for k in ("status", "returncode", "deadline_exceeded", "wall_seconds")}))
    return 0 if process.returncode == 0 and not timeout else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    raise SystemExit(run(parser.parse_args().worker))
