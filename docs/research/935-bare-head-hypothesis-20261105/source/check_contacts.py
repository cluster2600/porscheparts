#!/usr/bin/env python3
"""Prove reported triangle contacts equal their indexed shared simplex.

An injective coordinate projection of each triangle can establish an upper
bound on its 3D intersection. No distance tolerance suppresses an intersection.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np


def side(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])


def intersection(a, b):
    if side(*a) == 0 or side(*b) == 0:
        return None
    if side(*b) < 0:
        b = b[::-1]
    polygon = a
    for i in range(3):
        output = []
        u, w = b[i], b[(i+1) % 3]
        for s, t in zip(polygon, polygon[1:] + polygon[:1]):
            ds, dt = side(u, w, s), side(u, w, t)
            if ds >= 0:
                output.append(s)
            if (ds < 0) != (dt < 0):
                ratio = ds / (ds-dt)
                output.append(tuple(s[j]+ratio*(t[j]-s[j]) for j in range(2)))
        polygon = output
    return polygon


def prove(v, f, i, j):
    shared = sorted(set(map(int, f[i])) & set(map(int, f[j])))
    if len(shared) not in (1, 2):
        return None
    for drop in range(3):
        axes = [k for k in range(3) if k != drop]
        points = [[tuple(Fraction(float(x)) for x in row) for row in v[f[q]][:, axes]] for q in (i, j)]
        overlap = intersection(*points)
        if overlap is None or not overlap:
            continue
        expected = [tuple(Fraction(float(x)) for x in v[k, axes]) for k in shared]
        if len(shared) == 1:
            accepted = all(p == expected[0] for p in overlap)
        else:
            a, b = expected
            if a == b:
                continue
            accepted = all(side(a,b,p) == 0 and all(min(a[k],b[k]) <= p[k] <= max(a[k],b[k]) for k in range(2)) for p in overlap)
        if accepted:
            return {"shared_vertices": len(shared), "projection_drop_axis": drop,
                    "exact_projected_intersection_is_only_shared_simplex": True}
    return None


def controls():
    v = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.],
                  [.2,.2,0.],[.2,1.,0.],[1.,.2,0.],[0.,0.,1.]],dtype=float)
    f = np.array([[0,1,2],[0,3,4],[0,1,4],[0,5,6],[5,6,7],[0,1,8]])
    assert prove(v,f,0,1) is not None  # shared point only
    assert prove(v,f,0,2) is not None  # shared edge only
    assert prove(v,f,0,3) is None      # shared point AND positive-area overlap
    assert prove(v,f,0,4) is None      # overlap with no shared source vertex
    assert prove(v,f,0,5) is None      # projection-degenerate case not silently accepted
    shifted = v + np.array([8.,-4.,16.])
    assert prove(shifted,f,0,1) is not None
    return {"shared_point_accepted": True, "shared_edge_accepted": True,
            "additional_overlap_refused": True, "unshared_overlap_refused": True,
            "unproved_projection_refused": True, "translation_control": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh",type=Path,required=True)
    parser.add_argument("--pairs",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Existing output refused")
    control = controls()
    with np.load(args.mesh,allow_pickle=False) as data:
        v,f = data["vertices"],data["triangles"]
    pairs = np.load(args.pairs,allow_pickle=False)
    rows = []
    for i,j in pairs:
        result = prove(v,f,int(i),int(j))
        rows.append({"triangle_pair":[int(i),int(j)],"proof":result})
    report = {"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "raw_reported_pairs":len(pairs),"proved_expected_shared_simplex_contacts":sum(x["proof"] is not None for x in rows),
              "unresolved_pairs":sum(x["proof"] is None for x in rows),"controls":control,
              "proof_uses_distance_tolerance":False,"private_pair_proofs":rows,
              "physical_acceptance":False,"manufacturing_release_authorized":False}
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:val for k,val in report.items() if k!="private_pair_proofs"}))
    if report["unresolved_pairs"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
