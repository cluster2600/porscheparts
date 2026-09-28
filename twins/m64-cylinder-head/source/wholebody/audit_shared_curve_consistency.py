#!/usr/bin/env python3
"""Sample the six obstructing native faces; do not infer missing engine roles."""
import argparse
from pathlib import Path
import time

import numpy as np
from run_local_surface_trial import BODY_SHA, native
from trial_fixed_boundary_seam import indexed, read_native


def inspect(faces):
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    rows = []
    for face_id, face in faces:
        face = TopoDS.Face_s(face); surface = BRepAdaptor_Surface(face)
        for edge_id, shape in enumerate(indexed(face, TopAbs_EDGE), 1):
            edge = TopoDS.Edge_s(shape)
            if BRep_Tool.Degenerated_s(edge): raise ValueError('degenerate_edge_requires_separate_audit')
            c3 = BRepAdaptor_Curve(edge); c2 = BRepAdaptor_Curve2d(edge, face)
            ranges = [c3.FirstParameter(), c3.LastParameter(), c2.FirstParameter(), c2.LastParameter()]
            if not np.isfinite(ranges).all() or max(abs(ranges[0]-ranges[2]), abs(ranges[1]-ranges[3])) > 1e-12:
                raise ValueError('matching_finite_parameter_ranges_required')
            errors = []
            for t in np.linspace(ranges[0], ranges[1], 129):
                uv = c2.Value(float(t)); actual = surface.Value(uv.X(), uv.Y())
                errors.append(c3.Value(float(t)).Distance(actual))
            rows.append(dict(face=face_id, edge_within_face=edge_id, samples=129,
                maximum_sampled_gap=max(errors), edge_tolerance=BRep_Tool.Tolerance_s(edge),
                same_parameter=BRep_Tool.SameParameter_s(edge), same_range=BRep_Tool.SameRange_s(edge)))
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.body.is_symlink() or native.sha256(args.body) != BODY_SHA:
        raise ValueError('exact_body_fresh_output_required')
    from OCP.TopAbs import TopAbs_FACE
    start = time.monotonic(); faces = indexed(read_native(args.body), TopAbs_FACE)
    selected = (141, 143, 686, 1411, 1413, 1648)
    rows = inspect([(i, faces[i-1]) for i in selected])
    native.save(args.output, dict(schema='m64-shared-curve-sampling/v1', rows=rows,
        maximum_sampled_gap=max(r['maximum_sampled_gap'] for r in rows),
        input_sha256=BODY_SHA, source_sha256=native.sha256(__file__),
        input_unchanged=native.sha256(args.body) == BODY_SHA, seconds=time.monotonic()-start,
        unsampled_error_certified=False, geometry_changed=False, manufacturing_authorized=False))
