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


def junction(edge, faces):
    """Sample oriented native normals, including both trimmed endpoints."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_FORWARD, TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt, gp_Vec
    edge = TopoDS.Edge_s(edge); curve = BRepAdaptor_Curve(edge)
    samples = np.linspace(curve.FirstParameter(), curve.LastParameter(), 129)
    if not np.isfinite(samples).all() or samples[0] >= samples[-1]:
        raise ValueError('finite_trimmed_curve_required')
    normals, errors = [], []
    for shape in faces:
        face = TopoDS.Face_s(shape); surface = BRepAdaptor_Surface(face)
        if face.Orientation() not in (TopAbs_FORWARD, TopAbs_REVERSED):
            raise ValueError('oriented_face_required')
        pcurve = BRepAdaptor_Curve2d(edge, face)
        if max(abs(samples[0]-pcurve.FirstParameter()), abs(samples[-1]-pcurve.LastParameter())) > 1e-12:
            raise ValueError('same_parameter_range_required')
        ns = []
        for t in samples:
            uv = pcurve.Value(float(t)); point, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
            surface.D1(uv.X(), uv.Y(), point, du, dv)
            cross = np.cross([du.X(),du.Y(),du.Z()], [dv.X(),dv.Y(),dv.Z()])
            length = np.linalg.norm(cross)
            if not np.isfinite(length) or length <= 1e-14:
                raise ValueError('nonsingular_finite_surface_normal_required')
            ns.append(cross/length * (-1 if face.Orientation() == TopAbs_REVERSED else 1))
            errors.append(curve.Value(float(t)).Distance(point))
        normals.append(ns)
    if len(normals) != 2 or not np.isfinite(errors).all() or max(errors) > 1e-6:
        raise ValueError('two_native_faces_with_matching_pcurves_required')
    a, b = np.asarray(normals)
    angles = np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=1), np.einsum('ij,ij->i',a,b)))
    return dict(samples=129, endpoints_included=True, maximum_pcurve_gap=max(errors),
        minimum_oriented_normal_angle_degrees=float(angles.min()),
        maximum_oriented_normal_angle_degrees=float(angles.max()),
        sampled_tangent_under_0p1_degree=bool(angles.max() < .1),
        continuous_tangency_certified=False, functional_role_certified=False)


def internal_junctions(faces):
    from OCP.TopAbs import TopAbs_EDGE
    from trial_constrained_patch import PATCHES
    import itertools
    rows = []
    for name, group in PATCHES.items():
        for a, b in itertools.combinations(group, 2):
            fa, fb = faces[a-1], faces[b-1]
            shared = [e for e in indexed(fa, TopAbs_EDGE)
                      if any(e.IsSame(f) for f in indexed(fb, TopAbs_EDGE))]
            for edge in shared:
                rows.append(dict(patch=name, face_pair_private=[a,b], **junction(edge,(fa,fb))))
    if len(rows) != 6: raise ValueError('six_internal_compound_junctions_required')
    return rows


if __name__ == '__main__':
    import OCP
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--internal-compounds', action='store_true')
    args = parser.parse_args()
    source_hash = native.sha256(__file__)
    if (args.output.exists() or args.output.is_symlink() or args.body.is_symlink()
            or native.sha256(args.body) != BODY_SHA or OCP.__version__ != '7.9.3.1'):
        raise ValueError('exact_body_fresh_output_required')
    from OCP.TopAbs import TopAbs_FACE
    start = time.monotonic(); faces = indexed(read_native(args.body), TopAbs_FACE)
    selected = (141, 143, 686, 1411, 1413, 1648)
    rows = inspect([(i, faces[i-1]) for i in selected])
    result = dict(schema='m64-shared-curve-sampling/v1', rows=rows,
        maximum_sampled_gap=max(r['maximum_sampled_gap'] for r in rows),
        input_sha256=BODY_SHA, source_sha256=source_hash, OCP_version=OCP.__version__,
        input_unchanged=native.sha256(args.body) == BODY_SHA, seconds=time.monotonic()-start,
        unsampled_error_certified=False, geometry_changed=False, manufacturing_authorized=False)
    if args.internal_compounds: result['internal_junctions_private'] = internal_junctions(faces)
    result['seconds'] = time.monotonic()-start
    result['input_unchanged'] = native.sha256(args.body) == BODY_SHA
    result['source_unchanged'] = native.sha256(__file__) == source_hash
    native.save(args.output, result)
