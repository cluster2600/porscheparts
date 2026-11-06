"""Diagnose every raw tetrahedron without repairing or admitting the volume."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def exact_sign(xyz):
    points = [[Fraction.from_float(float(x)) for x in row] for row in xyz]
    a, b, c = [[points[i][j] - points[0][j] for j in range(3)] for i in (1, 2, 3)]
    determinant = (a[0] * (b[1]*c[2]-b[2]*c[1])
                   - a[1] * (b[0]*c[2]-b[2]*c[0])
                   + a[2] * (b[0]*c[1]-b[1]*c[0]))
    return int(determinant > 0) - int(determinant < 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    control = np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]])
    assert exact_sign(control) == 1 and exact_sign(control[[0,2,1,3]]) == -1
    control[3] = [.25, .25, 0]
    assert exact_sign(control) == 0
    control[3, 2] = 2.**-50
    assert exact_sign(control) == 1
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, tets = data["nodes"], data["tets"]
    with np.load(args.surface, allow_pickle=False) as data:
        source_count = len(data["vertices"])
        assert np.array_equal(nodes[:source_count], data["vertices"])
    volumes = np.empty(len(tets))
    ratios = np.empty(len(tets))
    for start in range(0, len(tets), 100000):
        xyz = nodes[tets[start:start+100000]]
        a, b, c = xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0], xyz[:,3]-xyz[:,0]
        volume = np.einsum("ij,ij->i", a, np.cross(b, c))/6
        edges_squared = sum(np.sum((xyz[:,i]-xyz[:,j])**2, axis=1)
                            for i,j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)))
        assert np.all(edges_squared > 0) and np.all(np.isfinite(volume))
        volumes[start:start+len(xyz)] = volume
        ratios[start:start+len(xyz)] = np.sign(volume)*12*(3*np.abs(volume))**(2/3)/edges_squared
    assert np.all(np.isfinite(ratios))
    nonpositive = np.flatnonzero(volumes <= 0)
    worst = np.argsort(ratios)[:8]
    selected = np.unique(np.r_[nonpositive, worst])
    exact = np.array([exact_sign(nodes[tets[index]]) for index in selected])
    np.savez_compressed(args.output / "private-defect-cells.npz", indices=selected,
                        cells=tets[selected], xyz=nodes[tets[selected]],
                        floating_volume=volumes[selected], exact_sign=exact)
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh),
              "surface_sha256": sha(args.surface), "nodes": len(nodes), "tetrahedra": len(tets),
              "all_source_vertices_exact": True, "all_cells_scanned": True,
              "floating_nonpositive_cells": len(nonpositive),
              "floating_negative_cells": int((volumes < 0).sum()),
              "floating_zero_cells": int((volumes == 0).sum()),
              "signed_volume_sum_mm3": float(volumes.sum()),
              "minimum_signed_cell_volume_mm3": float(volumes.min()),
              "signed_mean_ratio_quantiles": dict(zip(("minimum", "p01", "median", "p99", "maximum"),
                  map(float, np.quantile(ratios, [0, .01, .5, .99, 1])))),
              "signed_mean_ratio_below": {str(x): int((ratios < x).sum()) for x in (.0001,.001,.01,.05,.1)},
              "exact_predicate_scope": "All floating nonpositive cells and eight worst signed-mean-ratio cells, using exact binary-float coordinates",
              "exact_cells_checked": len(selected), "exact_negative_in_checked_cells": int((exact < 0).sum()),
              "exact_zero_in_checked_cells": int((exact == 0).sum()),
              "defect_cells_use_original_boundary_vertices_only": bool(np.all(tets[nonpositive] < source_count)),
              "exact_predicate_controls": {"positive": True, "negative": True, "coplanar": True, "thin_positive": True},
              "actual_cell_face_pairing_completed": False, "mesh_modified": False,
              "physics_admitted": False, "manufacturing_qualified": False,
              "seconds": time.monotonic()-started}
    with (args.output / "report.json").open("x") as stream:
        stream.write(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
