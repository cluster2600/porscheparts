#!/usr/bin/env python3
"""Reconstruct a diagnosed multi-face junction with its exterior boundary fixed.

Private research candidate only. Point constraints and sampled distance are not
certified approximation bounds; no master or functional interface is replaced.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import signal
import time

import numpy as np
from trial_bounded_tip_cut import encode, indexed, read_native, tolerances
from run_parallel_cad_trials import BODY_SHA, native

PATCHES = {'lower': (141, 142, 143), 'upper': (1411, 1412, 1413, 1647, 1648)}


def exterior_edges(faces):
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedMapOfShape
    mapping = TopTools_IndexedMapOfShape(); uses = Counter()
    for face in faces:
        for edge in indexed(face, TopAbs_EDGE):
            uses[mapping.Add(edge)] += 1
    if not uses or any(n not in (1, 2) for n in uses.values()):
        raise ValueError('manifold_patch_edge_incidence_required')
    remaining = [TopoDS.Edge_s(mapping.FindKey(i)) for i, n in uses.items() if n == 1]
    vertices = TopTools_IndexedMapOfShape(); degree = Counter()
    for edge in remaining:
        for vertex in (TopExp.FirstVertex_s(edge, True), TopExp.LastVertex_s(edge, True)):
            if vertex.IsNull(): raise ValueError('bounded_boundary_vertices_required')
            degree[vertices.Add(vertex)] += 1
    if not remaining or any(n != 2 for n in degree.values()):
        raise ValueError('single_nonbranching_boundary_required')
    ordered = [remaining.pop(0)]
    # ponytail: quadratic traversal is bounded by the small local patch; no graph library.
    while remaining:
        end = TopExp.LastVertex_s(ordered[-1], True)
        matches = [(i, edge if TopExp.FirstVertex_s(edge, True).IsSame(end)
                    else TopoDS.Edge_s(edge.Reversed())) for i, edge in enumerate(remaining)
                   if any(v.IsSame(end) for v in (TopExp.FirstVertex_s(edge, True), TopExp.LastVertex_s(edge, True)))]
        if len(matches) != 1: raise ValueError('one_continuous_boundary_loop_required')
        i, edge = matches[0]; remaining.pop(i); ordered.append(edge)
    if not TopExp.LastVertex_s(ordered[-1], True).IsSame(TopExp.FirstVertex_s(ordered[0], True)):
        raise ValueError('closed_boundary_loop_required')
    return ordered


def interior_points(face, resolution):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_IN
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt2d
    face = TopoDS.Face_s(face); surface = BRepAdaptor_Surface(face)
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
    if not np.isfinite([u0, u1, v0, v1]).all() or not 2 <= resolution <= 41:
        raise ValueError('bounded_finite_surface_sampling_required')
    points = []
    for a in (np.arange(resolution)+.5)/resolution:
        for b in (np.arange(resolution)+.5)/resolution:
            u, v = u0+a*(u1-u0), v0+b*(v1-v0)
            if BRepClass_FaceClassifier(face, gp_Pnt2d(float(u), float(v)), 1e-9).State() == TopAbs_IN:
                points.append(surface.Value(float(u), float(v)))
    return points


def filling(faces, resolution, initial_plane=None):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeFilling
    from OCP.GeomAbs import GeomAbs_C0
    from OCP.TopoDS import TopoDS
    # Copy constraints: the builder must not mutate the reference's edges.
    edges = exterior_edges(faces)
    copied = BRepBuilderAPI_Copy(compound(edges), True, False)
    op = BRepOffsetAPI_MakeFilling(3, 25, 3, False, 1e-8, 1e-7, .01, .1, 8, 32)
    if initial_plane is not None:
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.GeomAbs import GeomAbs_Plane
        if BRepAdaptor_Surface(TopoDS.Face_s(initial_plane)).GetType() != GeomAbs_Plane:
            raise ValueError('orthogonal_planar_initial_surface_required')
        op.LoadInitSurface(TopoDS.Face_s(BRepBuilderAPI_Copy(initial_plane, True, False).Shape()))
    for edge in edges:
        op.Add(TopoDS.Edge_s(copied.ModifiedShape(edge)), GeomAbs_C0)
    count = 0
    if resolution:
        for face in faces:
            for point in interior_points(face, resolution):
                op.Add(point); count += 1
    op.Build()
    if not op.IsDone(): raise ValueError('constrained_surface_build_failed')
    return op.Shape(), dict(exterior_edges=len(edges), interior_constraints=count,
                           reported_G0_error=op.G0Error(), continuous_boundary=True,
                           boundary_copied_together=True, native_initial_plane=initial_plane is not None)


def sampled_distance(points, target, exceedance_limit=None):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    if exceedance_limit is not None and (not np.isfinite(exceedance_limit) or exceedance_limit <= 0):
        raise ValueError('positive_finite_exceedance_limit_required')
    values = []; witness = None; exceeding = []
    op = BRepExtrema_DistShapeShape(); op.LoadS2(target)
    for index, point in enumerate(points):
        if not np.isfinite(point.Coord()).all(): raise ValueError('finite_native_sample_required')
        op.LoadS1(BRepBuilderAPI_MakeVertex(point).Vertex()); op.Perform()
        if not op.IsDone() or not np.isfinite(op.Value()): raise ValueError('native_distance_failed')
        if witness is None or op.Value() > witness['distance']:
            witness = dict(sample_index=index, point=list(point.Coord()),
                           closest=list(op.PointOnShape2(1).Coord()), distance=op.Value())
        values.append(op.Value())
        if exceedance_limit is not None and op.Value() > exceedance_limit:
            exceeding.append(list(point.Coord()))
            if len(exceeding) > 20000: raise ValueError('bounded_exceedance_set_required')
    if not values: raise ValueError('nonempty_distance_samples_required')
    result = dict(samples=len(values), maximum=max(values), maximum_witness_private=witness)
    if exceedance_limit is not None:
        result.update(exceedance_limit_scan_units=exceedance_limit, exceedance_points_private=exceeding)
    return result


def compound(shapes):
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    shape = TopoDS_Compound(); builder = BRep_Builder(); builder.MakeCompound(shape)
    for item in shapes: builder.Add(shape, item)
    return shape


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SHELL, TopAbs_SOLID
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedMapOfShape
    pins = {args.body: BODY_SHA, Path(__file__): native.sha256(__file__)}
    for name in ('trial_bounded_tip_cut.py', 'trial_fixed_boundary_seam.py', 'run_parallel_cad_trials.py'):
        path = Path(__file__).with_name(name); pins[path] = native.sha256(path)
    if (args.output.exists() or args.output.is_symlink() or args.body.is_symlink()
            or OCP.__version__ != '7.9.3.1' or native.sha256(args.body) != BODY_SHA):
        raise ValueError('fresh_output_and_pinned_native_input_required')
    args.output.mkdir(mode=0o700); start = time.monotonic()
    report = dict(schema='m64-constrained-native-patch/v1', status='incomplete',
        input_sha256=BODY_SHA, source_sha256=pins[Path(__file__)],
        helper_sha256={p.name: h for p, h in pins.items() if p.suffix == '.py'},
        source_faces=PATCHES[args.patch], constraint_grid=args.grid, OCP_version=OCP.__version__,
        initial_plane_face=({'lower': 142, 'upper': 1412}[args.patch] if args.initial_plane else None),
        distance_screen_limit_scan_units=.020, master_replaced=False,
        native_Hausdorff_certified=False, functional_face_roles_verified=False,
        CAE_authorized=False, manufacturing_authorized=False)
    def save(): native.save(args.output/'report.json', report)
    save()
    try:
        body = read_native(args.body); before = encode(body); faces = indexed(body, TopAbs_FACE)
        valid = lambda s: BRepCheck_Analyzer(s, True, False, True).IsValid()
        if len(faces) != 4918 or not valid(body): raise ValueError('valid_reference_required')
        patch = [faces[i-1] for i in PATCHES[args.patch]]
        edges = exterior_edges(patch)
        allowed = {i for i, f in enumerate(faces, 1) if i in PATCHES[args.patch] or
                   any(e.IsSame(g) for e in indexed(f, TopAbs_EDGE) for g in edges)}
        protected = {i: encode(f) for i, f in enumerate(faces, 1) if i not in allowed}
        report.update(allowed_representation_faces=sorted(allowed), stage='building_fixed_boundary_patch'); save()
        initial = faces[report['initial_plane_face']-1] if args.initial_plane else None
        replacement, build = filling(patch, args.grid, initial)
        report.update(build=build, replacement_valid=valid(replacement),
                      source_in_memory_unchanged=encode(body) == before)
        output = args.output/'patch-private.brep'
        if not BRepTools.Write_s(replacement, str(output)): raise ValueError('private_patch_write_failed')
        output.chmod(0o600); report['patch_sha256'] = native.sha256(output); save()
        if (not report['replacement_valid'] or not report['source_in_memory_unchanged']
                or not np.isfinite(build['reported_G0_error']) or build['reported_G0_error'] > 1e-7):
            raise ValueError('fixed_boundary_construction_guard_failed')
        report['stage'] = 'screening_native_patch_distances'; save()
        report['distance_samples'] = dict(
            original_to_patch=sampled_distance([p for f in patch for p in interior_points(f, 13)], replacement),
            patch_to_original=sampled_distance(interior_points(replacement, 25), compound(patch)))
        save()
        if max(r['maximum'] for r in report['distance_samples'].values()) > .020:
            raise ValueError('sampled_shape_change_exceeds_exploratory_limit')
        # Sewing is diagnostic only: exact protected identity and tolerances are
        # checked afterwards. Never accept widespread automatic healing.
        sewing = BRepBuilderAPI_Sewing(1e-7, True, True, True, False)
        for i, face in enumerate(faces, 1):
            if i not in PATCHES[args.patch]: sewing.Add(face)
        sewing.Add(replacement); sewing.Perform(); shells = indexed(sewing.SewedShape(), TopAbs_SHELL)
        if len(shells) != 1 or sewing.NbFreeEdges() or sewing.NbMultipleEdges():
            raise ValueError('one_closed_manifold_sewn_shell_required')
        result = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shells[0])).Solid()
        after = indexed(result, TopAbs_FACE); mapping = TopTools_IndexedMapOfShape()
        for face in after: mapping.Add(face)
        changed = {i for i, face in enumerate(faces, 1) if not mapping.Contains(face)}
        old_tol, new_tol = tolerances(body), tolerances(result)
        report.update(changed_faces=sorted(changed), native_valid=valid(result), result_faces=len(after),
            solid_count=len(indexed(result, TopAbs_SOLID)), shell_count=len(shells),
            source_in_memory_unchanged=encode(body) == before,
            protected_unchanged=all(mapping.Contains(faces[i-1]) and encode(faces[i-1]) == b for i, b in protected.items()),
            tolerances_not_increased=all(max(new_tol[k]) <= max(old_tol[k]) for k in old_tol)); save()
        if (not set(PATCHES[args.patch]) <= changed <= allowed or report['solid_count'] != 1
                or not all(report[k] for k in ('native_valid', 'protected_unchanged',
                    'source_in_memory_unchanged', 'tolerances_not_increased'))):
            raise ValueError('native_locality_or_tolerance_guard_failed')
        path = args.output/'candidate-private.brep'
        if not BRepTools.Write_s(result, str(path)): raise ValueError('candidate_write_failed')
        path.chmod(0o600); reread = read_native(path)
        if not valid(reread) or len(indexed(reread, TopAbs_SOLID)) != 1: raise ValueError('readback_failed')
        report.update(candidate_sha256=native.sha256(path), status='candidate_pending_BOP_distance_and_mesh')
    except Exception as error:
        report.update(status='rejected', error=type(error).__name__+': '+str(error))
    finally:
        report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items()))
        if not report['inputs_unchanged']: report['status'] = 'rejected_inputs_changed'
        save()
    print(json.dumps({k: report.get(k) for k in ('status', 'error', 'build', 'distance_samples', 'seconds')}))
    return 0 if report['status'].startswith('candidate_pending') else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--patch', choices=PATCHES, required=True)
    parser.add_argument('--grid', type=int, choices=(0, 5, 9), default=5)
    parser.add_argument('--initial-plane', action='store_true', help='Initialize from the original patch plane, not an inferred surface.')
    signal.alarm(540)
    raise SystemExit(run(parser.parse_args()))
