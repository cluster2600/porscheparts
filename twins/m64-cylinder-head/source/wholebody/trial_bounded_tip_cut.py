#!/usr/bin/env python3
"""Remove one tiny ball at an acute native corner, on a disposable CAD copy.

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
        ball_volume=4*math.pi*args.radius**3/3, CAD_modified=True, master_replaced=False,
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
        for _, centre in tips: result = cut_ball(result, centre, args.radius)
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
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
