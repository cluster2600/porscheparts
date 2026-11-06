"""Complete same-triangulation distance bound for one changed vertex."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def certify(before, after, maximum_mm):
    if not math.isfinite(maximum_mm) or maximum_mm <= 0:
        raise ValueError("Positive finite edit budget required")
    with np.load(before, allow_pickle=False) as old, np.load(after, allow_pickle=False) as new:
        a, b = old["vertices"], new["vertices"]
        f, g = old["triangles"], new["triangles"]
        if a.dtype != np.float64 or b.dtype != np.float64 or a.shape != b.shape:
            raise ValueError("Matching float64 vertex arrays required")
        if a.ndim != 2 or a.shape[1] != 3 or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError("Finite three-dimensional vertices required")
        if not np.array_equal(f, g):
            raise ValueError("Triangle correspondence changed")
        changed = np.flatnonzero(np.any(a != b, axis=1))
        if len(changed) != 1:
            raise ValueError("Exactly one changed vertex required")
        i = int(changed[0])
        for x, y in zip(a[i], b[i]):
            if x == y or x == 0 or y == 0:
                continue
            if (np.signbit(x) != np.signbit(y)
                    or min(abs(x), abs(y)) < np.finfo(float).tiny
                    or max(abs(x), abs(y))/2 > min(abs(x), abs(y))):
                raise ValueError("Exact Sterbenz subtraction not established")
        # Changed-coordinate differences are exact by Sterbenz or subtraction of zero.
        delta = np.abs(b[i]-a[i])
        l1, squared = 0., 0.
        for value in delta:
            l1 = float(np.nextafter(l1+value, np.inf))
            product = float(np.nextafter(value*value, np.inf))
            squared = float(np.nextafter(squared+product, np.inf))
        euclidean = math.nextafter(math.sqrt(squared), math.inf)
        if l1 > maximum_mm:
            raise ValueError("Complete edit budget exceeded")
        return dict(status="complete_single_vertex_edit_bound_passed", changed_vertex=i,
                    triangles_compared=len(f), all_other_vertices_identical=True,
                    all_triangles_identical=True, exact_coordinate_differences=True,
                    whole_surface_bidirectional_distance_upper_mm=euclidean,
                    complete_l1_displacement_upper_mm=l1, maximum_l1_budget_mm=maximum_mm,
                    proof="Identical indexed triangles admit forward and reverse barycentric correspondences; each complete triangle displacement is bounded by its largest vertex displacement",
                    embedding_or_mechanical_admission_established=False)


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("before",type=Path);p.add_argument("after",type=Path)
    p.add_argument("output",type=Path);p.add_argument("--maximum-mm",type=float,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise ValueError("Fresh output required")
    result=certify(args.before,args.after,args.maximum_mm)
    result.update(input_sha256=hashlib.sha256(args.before.read_bytes()).hexdigest(),
                  output_geometry_sha256=hashlib.sha256(args.after.read_bytes()).hexdigest(),
                  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
