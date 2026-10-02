#!/usr/bin/env python3
"""Try a bounded ball cut or planar tip truncation on disposable native CAD.

This is a design-change experiment, not automatic healing or release evidence.
Ball support bounds the set operation, not a certified surface Hausdorff error.
"""
import argparse
import io
import itertools
import json
import math
from pathlib import Path
import signal
import time

import numpy as np
from audit_native_acute_faces import angle_degrees
from trial_fixed_boundary_seam import read_native, indexed, tolerances
from run_parallel_cad_trials import BODY_SHA, native


def encode(shape):
    from OCP.BRepTools import BRepTools
    stream = io.BytesIO(); BRepTools.Write_s(shape, stream); return stream.getvalue()


def corner_rays(face):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt, gp_Vec
    ends = []
    for i, edge in enumerate(indexed(face, TopAbs_EDGE)):
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(edge))
        for u, sign in ((curve.FirstParameter(), 1), (curve.LastParameter(), -1)):
            p, v = gp_Pnt(), gp_Vec(); curve.D1(u, p, v)
            ends.append((i, np.array(p.Coord()), sign*np.array(v.Coord())))
    pairs = [(angle_degrees(a[2], b[2]), a[1]) for a, b in itertools.combinations(ends, 2)
             if a[0] != b[0] and np.linalg.norm(a[1]-b[1]) <= 1e-7]
    if not pairs: raise ValueError('joined_native_corner_required')
    return sorted(pairs, key=lambda x: x[0])


def acute_tip(face):
    return corner_rays(face)[0]


def cut_ball(body, centre, radius):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.gp import gp_Pnt
    if radius not in (.005, .01, .02) or len(centre) != 3 or not np.isfinite(centre).all():
        raise ValueError('finite_bounded_ball_required')
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(body); tools.Append(BRepPrimAPI_MakeSphere(gp_Pnt(*map(float, centre)), radius).Shape())
    op = BRepAlgoAPI_Cut(); op.SetArguments(args); op.SetTools(tools)
    op.SetNonDestructive(True); op.SetRunParallel(False); op.SetFuzzyValue(0.)
    op.Build()
    if not op.IsDone(): raise ValueError('native_boolean_failed')
    return op.Shape()


def cut_tip_plane(body, centre, radius):
    """Cut only a convex vertex cap; reject every exposed cutter side wall."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_ListOfShape, TopTools_IndexedMapOfShape
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
    centre=np.asarray(centre,dtype=float)
    if radius not in (.005,.01,.02) or centre.shape!=(3,) or not np.isfinite(centre).all():
        raise ValueError('finite_bounded_tip_required')
    vertices=[v for v in indexed(body,TopAbs_VERTEX) if np.linalg.norm(
        np.asarray(BRep_Tool.Pnt_s(TopoDS.Vertex_s(v)).Coord())-centre)<=1e-7]
    if len(vertices)!=1: raise ValueError('one_exact_native_vertex_required')
    rays=[]
    for edge in indexed(body,TopAbs_EDGE):
        edge=TopoDS.Edge_s(edge); curve=BRepAdaptor_Curve(edge)
        for t,sign,vertex in ((curve.FirstParameter(),1,TopExp.FirstVertex_s(edge)),
                              (curve.LastParameter(),-1,TopExp.LastVertex_s(edge))):
            if vertex.IsSame(vertices[0]):
                p,v=gp_Pnt(),gp_Vec(); curve.D1(t,p,v)
                ray=sign*np.asarray(v.Coord()); length=np.linalg.norm(ray)
                if not np.isfinite(length) or length<=1e-14: raise ValueError('regular_tip_edges_required')
                rays.append(ray/length)
    if not 3<=len(rays)<=8: raise ValueError('bounded_vertex_edge_star_required')
    # Equal projections on unit edge tangents avoid bias towards duplicate directions.
    axis=np.linalg.lstsq(np.asarray(rays),np.ones(len(rays)),rcond=None)[0]
    length=np.linalg.norm(axis)
    if not np.isfinite(length) or length<=1e-12: raise ValueError('convex_tip_direction_required')
    axis/=length; alignment=float(np.min(np.asarray(rays)@axis))
    if alignment<=1e-3: raise ValueError('strictly_forward_tip_edges_required')
    depth=radius*alignment/2
    side=np.cross(axis,np.eye(3)[np.argmin(abs(axis))]); side/=np.linalg.norm(side)
    normal=np.cross(axis,side)
    origin=centre-radius*(axis+side+normal)
    frame=gp_Ax2(gp_Pnt(*origin),gp_Dir(*normal),gp_Dir(*axis))
    tool=BRepPrimAPI_MakeBox(frame,radius+depth,2*radius,2*radius).Shape()
    args,tools=TopTools_ListOfShape(),TopTools_ListOfShape(); args.Append(body); tools.Append(tool)
    op=BRepAlgoAPI_Cut(); op.SetArguments(args); op.SetTools(tools)
    op.SetNonDestructive(True); op.SetRunParallel(False); op.SetFuzzyValue(0.); op.Build()
    if not op.IsDone(): raise ValueError('native_planar_truncation_failed')
    original_descendants=TopTools_IndexedMapOfShape()
    for face in indexed(body,TopAbs_FACE):
        original_descendants.Add(face)
        for changed in op.Modified(face): original_descendants.Add(changed)
    caps=[f for f in indexed(op.Shape(),TopAbs_FACE) if not original_descendants.Contains(f)]
    if len(caps)!=1: raise ValueError(f'exactly_one_planar_cap_required: new_faces={len(caps)}')
    surface=BRepAdaptor_Surface(TopoDS.Face_s(caps[0]))
    if surface.GetType()!=GeomAbs_Plane: raise ValueError('planar_cap_required')
    plane=surface.Plane()
    if (abs(np.dot(plane.Axis().Direction().Coord(),axis))<1-1e-12
            or plane.Distance(gp_Pnt(*(centre+depth*axis)))>1e-7):
        raise ValueError('cutter_side_wall_exposed')
    return op.Shape()


def run(args):
    import OCP
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_SHELL, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedMapOfShape
    if (args.output.exists() or args.output.is_symlink() or args.body.is_symlink()
            or native.sha256(args.body) != BODY_SHA or OCP.__version__ != '7.9.3.1'):
        raise ValueError('fresh_output_and_pinned_native_input_required')
    pins = {args.body: BODY_SHA, Path(__file__): native.sha256(__file__)}
    args.output.mkdir(mode=0o700); start = time.monotonic()
    report = dict(schema='m64-bounded-native-tip-cut/v1', status='incomplete', input_sha256=BODY_SHA,
        source_sha256=pins[Path(__file__)], source_faces=args.face, radius_scan_units=args.radius,
        ball_volume=None if args.planar else 4*math.pi*args.radius**3/3,
        cutter='bounded_planar_cap' if args.planar else 'ball', CAD_modified=True, master_replaced=False,
        native_Hausdorff_certified=False, functional_face_roles_verified=False,
        CAE_authorized=False, manufacturing_authorized=False)
    def save(): native.save(args.output/'report.json', report)
    save()
    try:
        body = read_native(args.body); before = encode(body); faces = indexed(body, TopAbs_FACE)
        if len(faces) != 4918 or not BRepCheck_Analyzer(body, True, False, True).IsValid():
            raise ValueError('valid_original_body_required')
        tips = []
        for face_id in args.face:
            for angle, centre in corner_rays(faces[face_id-1]):
                if 0 < angle < 5 and not any(np.linalg.norm(centre-p) <= 1e-7 for _, p in tips):
                    tips.append((angle, centre))
        if not 1 <= len(tips) <= 10: raise ValueError('bounded_acute_tips_required')
        allowed = set()
        for _, centre in tips:
            star = {i for i, face in enumerate(faces, 1) if any(np.linalg.norm(
                np.array(BRep_Tool.Pnt_s(TopoDS.Vertex_s(v)).Coord())-centre) <= 1e-7
                for v in indexed(face, TopAbs_VERTEX))}
            if len(star) > 8: raise ValueError('bounded_vertex_star_required')
            allowed.update(star)
        if not set(args.face) <= allowed: raise ValueError('diagnosed_faces_required')
        protected = {i: encode(f) for i, f in enumerate(faces, 1) if i not in allowed}
        report.update(tips_private=[dict(angle_degrees=a, centre=p.tolist()) for a, p in tips],
                      tip_count=len(tips), allowed_faces=sorted(allowed)); save()
        result = body
        for _, centre in tips:
            result = (cut_tip_plane if args.planar else cut_ball)(result,centre,args.radius)
        after = indexed(result, TopAbs_FACE); mapping = TopTools_IndexedMapOfShape()
        for face in after: mapping.Add(face)
        changed = {i for i, f in enumerate(faces, 1) if not mapping.Contains(f)}
        old_tol, new_tol = tolerances(body), tolerances(result)
        report.update(changed_faces=sorted(changed), result_faces=len(after),
            native_valid=BRepCheck_Analyzer(result, True, False, True).IsValid(),
            solid_count=len(indexed(result, TopAbs_SOLID)), shell_count=len(indexed(result, TopAbs_SHELL)),
            original_shell_count=len(indexed(body, TopAbs_SHELL)),
            source_in_memory_unchanged=encode(body) == before,
            protected_unchanged=all(mapping.Contains(faces[i-1]) and encode(faces[i-1]) == value
                                    for i, value in protected.items()),
            tolerances_not_increased=all(max(new_tol[k]) <= max(old_tol[k]) for k in old_tol),
            before_max_tolerances={k: max(v) for k, v in old_tol.items()},
            after_max_tolerances={k: max(v) for k, v in new_tol.items()})
        if (not changed or not changed <= allowed or not set(args.face) <= changed
                or not all(report[k] for k in ('native_valid', 'source_in_memory_unchanged',
                    'protected_unchanged', 'tolerances_not_increased')) or report['solid_count'] != 1
                or report['shell_count'] != report['original_shell_count']):
            raise ValueError('locality_validity_or_tolerance_guard_failed')
        path = args.output/'candidate-private.brep'
        if not BRepTools.Write_s(result, str(path)): raise ValueError('native_write_failed')
        path.chmod(0o600); readback = read_native(path)
        if (not BRepCheck_Analyzer(readback, True, False, True).IsValid()
                or len(indexed(readback, TopAbs_SOLID)) != 1): raise ValueError('native_readback_failed')
        report.update(candidate_sha256=native.sha256(path), status='candidate_pending_BOP_distance_and_mesh')
    except Exception as error:
        report.update(status='rejected', error=type(error).__name__+': '+str(error))
    finally:
        report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items()))
        if not report['inputs_unchanged']: report['status'] = 'rejected_inputs_changed'
        save()
    print(json.dumps({k: v for k, v in report.items() if k != 'tips_private'}), flush=True)
    return 0 if report['status'].startswith('candidate_pending') else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--face', type=int, nargs='+', choices=(141, 143, 1411, 1413, 1648), default=[1648])
    parser.add_argument('--radius', type=float, choices=(.005, .01, .02), required=True)
    parser.add_argument('--planar',action='store_true',help='Try one convex planar cap per tip; reject exposed cutter walls.')
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
