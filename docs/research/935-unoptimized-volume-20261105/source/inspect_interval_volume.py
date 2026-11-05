"""Inspect the complete raw volume with outward-rounded determinant intervals.

Every arithmetic interval endpoint is expanded by one binary64 neighbour.
Ambiguous determinant signs use exact fractions of the stored coordinates.
No coordinate or connectivity is changed, and the quality gate remains separate.
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def expand(low, high):
    return np.nextafter(low, -np.inf), np.nextafter(high, np.inf)


def subtract(a, b):
    return expand(a[0]-b[1], a[1]-b[0])


def add(a, b):
    return expand(a[0]+b[0], a[1]+b[1])


def multiply(a, b):
    products = (a[0]*b[0], a[0]*b[1], a[1]*b[0], a[1]*b[1])
    return expand(np.minimum.reduce(products), np.maximum.reduce(products))


def determinant_interval(xyz):
    coordinates = []
    for i in (1, 2, 3):
        difference = expand(xyz[:,i]-xyz[:,0], xyz[:,i]-xyz[:,0])
        coordinates.append([(difference[0][:,j], difference[1][:,j]) for j in range(3)])
    a, b, c = coordinates
    first = multiply(a[0], subtract(multiply(b[1], c[2]), multiply(b[2], c[1])))
    second = multiply(a[1], subtract(multiply(b[0], c[2]), multiply(b[2], c[0])))
    third = multiply(a[2], subtract(multiply(b[0], c[1]), multiply(b[1], c[0])))
    return add(subtract(first, second), third)


def exact_determinant(xyz):
    p = [[Fraction.from_float(float(x)) for x in row] for row in xyz]
    a, b, c = [[p[i][j]-p[0][j] for j in range(3)] for i in (1, 2, 3)]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def controls():
    rng = np.random.default_rng(935111)
    samples = rng.normal(size=(100, 4, 3))
    samples = np.concatenate((samples, samples[:,[0,2,1,3]]))
    flat = np.array([[0.,0,0],[1.,0,0],[0,1.,0],[.25,.25,0]])
    samples = np.concatenate((samples, flat[None]))
    thin = flat.copy(); thin[3,2] = 2.**-50
    samples = np.concatenate((samples, thin[None], thin[[0,2,1,3]][None]))
    lo, hi = determinant_interval(samples)
    for i, xyz in enumerate(samples):
        exact = exact_determinant(xyz)
        assert Fraction.from_float(float(lo[i])) <= exact <= Fraction.from_float(float(hi[i]))
    assert exact_determinant(flat) == 0
    assert exact_determinant(thin) > 0 and exact_determinant(thin[[0,2,1,3]]) < 0
    return {"exact_fraction_interval_enclosures": len(samples), "coplanar_refused": True,
            "thin_positive_and_negative_distinguished": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "surface", "surface-report", "frozen-inspector", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    assert np.dtype(float).itemsize == 8 and np.finfo(float).eps == 2.**-52
    control_report = controls()
    assert sha(args.frozen_inspector) == "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3"
    spec = importlib.util.spec_from_file_location("frozen_cell_helpers", args.frozen_inspector)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    with np.load(args.surface, allow_pickle=False) as data:
        source_vertices, source_faces = data["vertices"], data["triangles"]
    source_report = json.loads(args.surface_report.read_text())
    assert sha(args.surface) == source_report["input_sha256"] and source_report["geometry_export_gate_passed"]
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, tets, boundary = data["nodes"], data["tets"], data["boundary"]
    assert len(nodes) < 2**32 and np.all(np.isfinite(nodes)) and 0 <= tets.min() <= tets.max() < len(nodes)
    assert np.array_equal(nodes[:len(source_vertices)], source_vertices)
    source = helper.records(np.sort(source_faces, axis=1)); source_order = np.argsort(source)
    source = source[source_order]; source_sign = helper.sign(source_faces)[source_order]
    assert np.array_equal(np.sort(helper.records(np.sort(boundary, axis=1))), source)
    patterns = np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]])
    faces = np.empty((4*len(tets), 3), dtype="<u4")
    signs = np.empty(4*len(tets), dtype=np.int8)
    volumes = np.empty(len(tets)); quality = np.empty(len(tets)); used = np.zeros(len(nodes), bool)
    interval_positive = exact_positive = 0
    exact_ids = []
    for start in range(0, len(tets), 50000):
        cells = tets[start:start+50000]; xyz = nodes[cells]; used[cells] = True
        low, high = determinant_interval(xyz)
        assert np.all(np.isfinite(low)) and np.all(np.isfinite(high))
        determinant = np.einsum("ij,ij->i", xyz[:,1]-xyz[:,0], np.cross(xyz[:,2]-xyz[:,0], xyz[:,3]-xyz[:,0]))
        uncertain = np.flatnonzero(low <= 0)
        interval_positive += int((low > 0).sum())
        for i in uncertain:
            exact = exact_determinant(xyz[i])
            assert exact > 0, "Exact nonpositive cell; raw volume rejected"
            determinant[i] = float(exact)
            exact_positive += 1; exact_ids.append(start+int(i))
        assert np.all(determinant > 0)
        volume = determinant/6
        edge_sum = sum(np.sum((xyz[:,i]-xyz[:,j])**2, axis=1)
                       for i,j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)))
        volumes[start:start+len(cells)] = volume
        quality[start:start+len(cells)] = 12*(3*volume)**(2/3)/edge_sum
        outward = cells[:,patterns].reshape(-1,3)
        first, last = 4*start, 4*(start+len(cells))
        signs[first:last] = helper.sign(outward)
        faces[first:last] = np.sort(outward, axis=1)
    assert used.all()
    order = np.argsort(helper.records(faces)); ordered = faces[order]
    ordered_records = helper.records(ordered)
    starts = np.r_[0, np.flatnonzero(ordered_records[1:] != ordered_records[:-1])+1]
    counts = np.diff(np.r_[starts, len(ordered)]); assert np.all(counts <= 2)
    orientation = signs[order]; internal = starts[counts == 2]; external = starts[counts == 1]
    assert np.all(orientation[internal] + orientation[internal+1] == 0)
    assert np.array_equal(ordered_records[external], source)
    assert np.array_equal(orientation[external], source_sign)
    relative = abs(volumes.sum()/source_report["signed_volume_mm3"]-1); assert relative < 1e-8
    np.save(args.output/"private-exact-cell-indices.npy", np.array(exact_ids))
    result = {"source_sha256": sha(Path(__file__)), "frozen_helpers_sha256": sha(args.frozen_inspector),
              "mesh_sha256": sha(args.mesh), "surface_sha256": sha(args.surface),
              "nodes": len(nodes), "tetrahedra": len(tets), "boundary_faces": len(external),
              "interval_proven_positive_cells": interval_positive, "exact_fraction_positive_cells": exact_positive,
              "all_cells_positive_for_stored_binary_coordinates": interval_positive+exact_positive == len(tets),
              "all_nodes_used": True, "all_source_vertices_exact": True,
              "actual_complete_boundary_and_orientation_exact": True,
              "internal_paired_faces": len(internal), "all_internal_faces_oppositely_oriented": True,
              "volume_mm3": float(volumes.sum()), "relative_volume_difference": float(relative),
              "minimum_cell_volume_mm3": float(volumes.min()),
              "mean_ratio_quantiles": dict(zip(("minimum","p01","median","p99","maximum"),
                  map(float,np.quantile(quality,[0,.01,.5,.99,1])))),
              "mean_ratio_below": {str(x):int((quality < x).sum()) for x in (.0001,.001,.01,.05,.1)},
              "diagnostic_mean_ratio_floor": .01, "diagnostic_quality_passed": bool(np.all(quality >= .01)),
              "interval_scope": "Outward one-ULP expansion after every binary64 operation; ambiguous signs evaluated as exact fractions of stored coordinates",
              "controls": control_report, "tetrahedron_pair_intersections_exhaustively_checked": False,
              "mesh_modified": False, "physics_admitted": False, "manufacturing_qualified": False,
              "seconds": time.monotonic()-started}
    with (args.output/"report.json").open("x") as stream:
        stream.write(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
