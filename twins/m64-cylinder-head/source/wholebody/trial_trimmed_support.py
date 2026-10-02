#!/usr/bin/env python3
"""Extend the existing bilinear support across its diagnosed thin lip.

Unlike a spherical notch, the cutter floor is the existing native surface.
The operation is a private design trial, not a repaired or released master.
"""
import argparse
import json
from pathlib import Path
import signal
import time

import numpy as np
from trial_bounded_tip_cut import encode, indexed, read_native, tolerances
from run_parallel_cad_trials import BODY_SHA, native


def unify_local(shape, protected_faces):
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_EDGE
    op = ShapeUpgrade_UnifySameDomain(shape, False, True, False)
    op.SetSafeInputMode(True); op.SetLinearTolerance(1e-7); op.SetAngularTolerance(1e-12)
    for face in protected_faces:
        for edge in indexed(face, TopAbs_EDGE): op.KeepShape(edge)
    op.Build()
    return op.Shape()


def support_tool(support, lip_faces, direction):
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Vec
    surface = BRep_Tool.Surface_s(TopoDS.Face_s(support)).Copy()
    if (not hasattr(surface, 'NbUPoles') or surface.IsURational() or surface.IsVRational()
            or (surface.UDegree(), surface.VDegree(), surface.NbUPoles(), surface.NbVPoles()) != (1, 1, 2, 2)):
        raise ValueError('native_nonrational_bilinear_support_required')
    axis = np.asarray(direction, dtype=float)
    if axis.shape != (3,) or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1) > 1e-12:
        raise ValueError('finite_unit_extrusion_required')
    uv, gaps = [], []
    for face in lip_faces:
        for edge in indexed(face, TopAbs_EDGE):
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(edge))
            for t in np.linspace(curve.FirstParameter(), curve.LastParameter(), 65):
                projection = GeomAPI_ProjectPointOnSurf(curve.Value(float(t)), surface)
                if not projection.NbPoints(): raise ValueError('native_projection_failed')
                uv.append(projection.LowerDistanceParameters()); gaps.append(projection.LowerDistance())
    if not uv or not np.isfinite(uv).all() or not np.isfinite(gaps).all() or max(gaps) > .040:
        raise ValueError('bounded_projected_lip_required')
    bounds = np.array(surface.Bounds()).reshape(2, 2)
    margin = .01*(bounds[:, 1]-bounds[:, 0])
    lo, hi = np.min(uv, axis=0)-margin, np.max(uv, axis=0)+margin
    if not np.all(lo > bounds[:, 0]) or not np.all(hi < bounds[:, 1]):
        raise ValueError('tool_must_stay_inside_native_support_rectangle')
    face = BRepBuilderAPI_MakeFace(surface, float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1]), 1e-7).Face()
    tool = BRepPrimAPI_MakePrism(face, gp_Vec(*(.1*axis)), True, False).Shape()
    return tool, dict(support_uv_private=[lo.tolist(), hi.tolist()],
                     projected_boundary_samples=len(uv), maximum_sampled_projection_gap=max(gaps),
                     extrusion_scan_units=.1, support_geometry_modified=False)


def run(args):
    import OCP
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_SHELL, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_ListOfShape, TopTools_IndexedMapOfShape
    if (args.output.exists() or args.output.is_symlink() or args.body.is_symlink()
            or native.sha256(args.body) != BODY_SHA or OCP.__version__ != '7.9.3.1'):
        raise ValueError('pinned_body_and_fresh_output_required')
    pins = {args.body: BODY_SHA, Path(__file__): native.sha256(__file__)}
    args.output.mkdir(mode=0o700); start = time.monotonic()
    report = dict(schema='m64-trimmed-native-support/v1', status='incomplete', input_sha256=BODY_SHA,
        source_sha256=pins[Path(__file__)], source_faces=[1412, 1648], support_face=1647,
        same_domain_unification=args.unify,
        floor_fillet_radius_scan_units=args.fillet,
        master_replaced=False, native_Hausdorff_certified=False, physical_millimetres_certified=False,
        functional_face_roles_verified=False, CAE_authorized=False, manufacturing_authorized=False)
    def save(): native.save(args.output/'report.json', report)
    save()
    try:
        body = read_native(args.body); before = encode(body); faces = indexed(body, TopAbs_FACE)
        valid = lambda s: BRepCheck_Analyzer(s, True, False, True).IsValid()
        if len(faces) != 4918 or not valid(body): raise ValueError('valid_reference_required')
        allowed = {1165, 1411, 1412, 1413, 1647, 1648}
        if args.fillet:
            circle_edges = [e for j in (1411, 1413, 1415) for e in indexed(faces[j-1], TopAbs_EDGE)
                            if any(e.IsSame(g) for g in indexed(faces[1164], TopAbs_EDGE))]
            vertices = [v for e in circle_edges for v in indexed(e, TopAbs_VERTEX)]
            allowed.update(i for i, f in enumerate(faces, 1) if any(v.IsSame(w)
                           for v in indexed(f, TopAbs_VERTEX) for w in vertices))
            if len(circle_edges) != 3 or len(allowed) > 12: raise ValueError('bounded_three_edge_fillet_star_required')
        protected = {i: encode(f) for i, f in enumerate(faces, 1) if i not in allowed}
        direction = BRepAdaptor_Surface(TopoDS.Face_s(faces[1164])).Plane().Axis().Direction().Coord()
        tool, construction = support_tool(faces[1646], [faces[1411], faces[1647]], direction)
        report.update(tool=construction, tool_valid=valid(tool), stage='reintersecting_local_support'); save()
        if not report['tool_valid']: raise ValueError('invalid_native_tool')
        inputs, tools = TopTools_ListOfShape(), TopTools_ListOfShape(); inputs.Append(body); tools.Append(tool)
        op = BRepAlgoAPI_Cut(); op.SetArguments(inputs); op.SetTools(tools)
        op.SetNonDestructive(True); op.SetRunParallel(False); op.SetFuzzyValue(0.); op.Build()
        if not op.IsDone(): raise ValueError('native_reintersection_failed')
        result = op.Shape()
        if args.unify: result = unify_local(result, [faces[i-1] for i in protected])
        if args.fillet:
            from build_local_port_junction_fillet import build_fillet, STRICT_PARAMETERS
            from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
            current = indexed(result, TopAbs_FACE)
            edges = [TopoDS.Edge_s(e) for j in (1411, 1413, 1415) for e in indexed(current[j-1], TopAbs_EDGE)
                     if any(e.IsSame(g) for g in indexed(current[1164], TopAbs_EDGE))]
            if len(edges) != 3: raise ValueError('reconstructed_three_circle_edges_required')
            preflight = BRepFilletAPI_MakeFillet(result); preflight.SetParams(*STRICT_PARAMETERS)
            for edge in edges: preflight.Add(args.fillet, edge)
            contour_edges = [preflight.Edge(i, j) for i in range(1, preflight.NbContours()+1)
                             for j in range(1, preflight.NbEdges(i)+1)]
            report.update(fillet_source_face_pairs=[[1165, j] for j in (1411, 1413, 1415)],
                          fillet_contour_count=preflight.NbContours(), fillet_contour_edges=len(contour_edges),
                          allowed_faces=sorted(allowed)); save()
            if len(contour_edges) != 3 or not all(any(e.IsSame(g) for g in edges) for e in contour_edges):
                raise ValueError('fillet_contour_propagation_rejected')
            fillet, build = build_fillet(result, edges, args.fillet, 'strict-approximation-v1')
            report['fillet_build'] = build; save()
            if not fillet.IsDone(): raise ValueError('local_fillet_failed')
            result = fillet.Shape()
        after = indexed(result, TopAbs_FACE); mapping = TopTools_IndexedMapOfShape()
        for face in after: mapping.Add(face)
        changed = {i for i, f in enumerate(faces, 1) if not mapping.Contains(f)}
        old_tol, new_tol = tolerances(body), tolerances(result)
        report.update(changed_faces=sorted(changed), allowed_faces=sorted(allowed), native_valid=valid(result),
            result_faces=len(after), solid_count=len(indexed(result, TopAbs_SOLID)),
            shell_count=len(indexed(result, TopAbs_SHELL)), source_in_memory_unchanged=encode(body) == before,
            protected_unchanged=all(mapping.Contains(faces[i-1]) and encode(faces[i-1]) == value for i, value in protected.items()),
            tolerances_not_increased=all(max(new_tol[k]) <= max(old_tol[k]) for k in old_tol),
            lip_faces_deleted=[op.IsDeleted(faces[i-1]) for i in (1412, 1648)]); save()
        if (not {1412, 1647, 1648} <= changed <= allowed or report['solid_count'] != 1 or report['shell_count'] != 1
                or not all(report[k] for k in ('native_valid', 'source_in_memory_unchanged', 'protected_unchanged', 'tolerances_not_increased'))
                or not all(report['lip_faces_deleted'])):
            raise ValueError('locality_topology_or_lip_removal_guard_failed')
        path = args.output/'candidate-private.brep'
        if not BRepTools.Write_s(result, str(path)): raise ValueError('native_write_failed')
        path.chmod(0o600); reread = read_native(path)
        if not valid(reread) or len(indexed(reread, TopAbs_SOLID)) != 1: raise ValueError('readback_failed')
        report.update(candidate_sha256=native.sha256(path), status='candidate_pending_BOP_distance_and_mesh')
    except Exception as error:
        report.update(status='rejected', error=type(error).__name__+': '+str(error))
    finally:
        report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items())); save()
    print(json.dumps({k: v for k, v in report.items() if k != 'tool'}))
    return 0 if report['status'].startswith('candidate_pending') and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    optional = parser.add_mutually_exclusive_group()
    optional.add_argument('--unify', action='store_true', help='Merge coincident faces only inside the protected-edge fence.')
    optional.add_argument('--fillet', type=float, choices=(.005, .01, .02), help='Round three explicitly selected floor/cylinder edges.')
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
