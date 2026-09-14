#!/usr/bin/env python3
"""One bounded native fillet prototype on a gas-branch/cap junction.

This is not a complete port fairing: the residual outer cap and branch/branch
bifurcation remain separate constraints. Private geometry is never embedded.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import time

import build_scan_seeded_ports as ports
import build_bounded_c1_trunk as bounded


CONSTRUCTION_MODES = ('default', 'strict-approximation-v1')
# OCCT V7_9_3 ChFi3d_Builder_1.cxx defaults, ordered as SetParams arguments.
# The strict variant changes construction accuracy, never acceptance guards.
STRICT_PARAMETERS = (1e-2, 1e-7, 1e-7, 1e-8, 1e-8, 1e-4)
PARAMETER_NAMES = ('Tang', 'Tesp', 'T2d', 'TApp3d', 'TolApp2d', 'Fleche')


def validate_radius(radius, maximum=1.0):
    """Exploratory design cap in scan units, not an OEM/manufacturing value."""
    if not math.isfinite(radius) or not 0 < radius <= maximum:
        raise ValueError('finite positive radius no greater than design cap required')
    return radius


def read_native(path):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
        raise ValueError('native BRep read failed')
    return shape


def topology(cad, shape):
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SOLID
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    result = {'valid': cad.valid(shape), 'solids': cad.indexed(shape, TopAbs_SOLID).Extent()}
    for name, kind, cast in [('faces', TopAbs_FACE, TopoDS.Face_s),
                             ('edges', TopAbs_EDGE, TopoDS.Edge_s),
                             ('vertices', TopAbs_VERTEX, TopoDS.Vertex_s)]:
        indexed = cad.indexed(shape, kind)
        values = [BRep_Tool.Tolerance_s(cast(indexed.FindKey(i)))
                  for i in range(1, indexed.Extent()+1)]
        result[name] = {'count': len(values), 'tolerance_min': min(values),
                        'tolerance_max': max(values)}
    return result


def branch_cap_edges(cad, shape, section, radial_reserve=1e-5):
    """Find inner branch/cap boundaries, excluding the constrained outer ring.

    Identification samples radial location; later build/history and exact
    section checks are separate. No indices are transferred between shapes.
    """
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    centre, radius = section['center'], section['radius']
    if len(centre) != 3 or not all(math.isfinite(v) for v in [*centre, radius]) or radius <= 0:
        raise ValueError('finite circle required')
    edges = cad.indexed(shape, TopAbs_EDGE)
    ancestors = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, ancestors)
    selected = []
    for i in range(1, edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        faces = list(ancestors.FindFromKey(edge))
        if len(faces) != 2:
            continue
        cap_count = 0
        for face in faces:
            surface = BRepAdaptor_Surface(TopoDS.Face_s(face), False)
            if surface.GetType() == GeomAbs_Plane:
                plane = surface.Plane()
                if abs(abs(plane.Axis().Direction().Y())-1) <= 1e-12 and abs(plane.Location().Y()-centre[1]) <= 1e-9:
                    cap_count += 1
        if cap_count != 1:
            continue
        curve = BRepAdaptor_Curve(edge)
        points = [curve.Value(curve.FirstParameter()+(curve.LastParameter()-curve.FirstParameter())*j/32)
                  for j in range(33)]
        if max(abs(p.Y()-centre[1]) for p in points) > 1e-7:
            continue
        radial_max = max(math.hypot(p.X()-centre[0], p.Z()-centre[2]) for p in points)
        if radial_max < radius-radial_reserve:
            selected.append((i, edge, radial_max))
    return selected


def build_fillet(shape, edges, radius, construction_mode='default'):
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    validate_radius(radius)
    if construction_mode not in CONSTRUCTION_MODES:
        raise ValueError('unknown construction mode')
    if not edges:
        raise ValueError('no identified branch-cap edge')
    maker = BRepFilletAPI_MakeFillet(shape)
    if construction_mode == 'strict-approximation-v1':
        # Must precede Add: Add creates spines using current construction Tesp.
        maker.SetParams(*STRICT_PARAMETERS)
        # Internal C1 / angular 0.01 rad remain the historical defaults.
    for edge in edges:
        if not maker.Contour(edge):
            maker.Add(radius, edge)
    # Do not loosen construction, angular, or topological tolerances.
    maker.Build()
    result = {'done': maker.IsDone(), 'contours': maker.NbContours(),
              'faulty_contours': [{'index': maker.FaultyContour(i),
                                   'status': str(maker.StripeStatus(maker.FaultyContour(i)))}
                                  for i in range(1, maker.NbFaultyContours()+1)],
              'faulty_vertices': maker.NbFaultyVertices(),
              'partial_result_exists_not_accepted': maker.HasResult(),
              'construction_mode': construction_mode,
              'tolerance_parameters_overridden': construction_mode != 'default',
              'SetParams_explicit': dict(zip(PARAMETER_NAMES, STRICT_PARAMETERS))
                  if construction_mode != 'default' else None,
              'acceptance_guards_relaxed': False}
    return maker, result


def sample_generated_tangency(cad, shape, generated):
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.gp import gp_Pnt, gp_Vec
    edges = cad.indexed(shape, TopAbs_EDGE)
    ancestors = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, ancestors)
    rows = []
    for i in range(1, edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i)); faces = list(ancestors.FindFromKey(edge))
        if len(faces) != 2 or sum(any(f.IsSame(g) for g in generated) for f in faces) != 1:
            continue
        curve = BRepAdaptor_Curve(edge); angles = []
        for j in range(1, 20):
            t = curve.FirstParameter()+(curve.LastParameter()-curve.FirstParameter())*j/20
            normals = []
            for f in faces:
                face = TopoDS.Face_s(f); uv = BRepAdaptor_Curve2d(edge, face).Value(t)
                p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
                BRepAdaptor_Surface(face, False).D1(uv.X(), uv.Y(), p, du, dv)
                normal = du.Crossed(dv)
                if normal.Magnitude() <= 1e-15:
                    raise ValueError('singular normal on generated boundary')
                normal.Normalize(); normals.append(normal)
            angles.append(math.degrees(math.acos(min(1., abs(normals[0].Dot(normals[1]))))))
        rows.append({'edge_index': i, 'samples': 19, 'tangent_plane_angle_deg_max': max(angles),
                     'not_a_global_G1_proof': True})
    return rows


def run(args):
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_FACE
    cad = ports.design.CAD(); api = ports.native(); start = time.monotonic()
    validate_radius(args.radius)
    if args.output.exists():
        raise FileExistsError(args.output)
    checkpoint = json.loads(args.checkpoint.read_text())
    if checkpoint['kind'] != 'intake' or ports.sha(args.negative) != checkpoint['exports']['native_BRep_sha256']:
        raise ValueError('expected exact intake checkpoint/negative pair')
    inputs = {'negative': args.negative, 'checkpoint': args.checkpoint, 'source': Path(__file__),
              'routing_source': Path(ports.__file__), 'bounded_source': Path(bounded.__file__)}
    hashes = {k: ports.sha(p) for k, p in inputs.items()}
    shape = read_native(args.negative); original = topology(cad, shape)
    selected = branch_cap_edges(cad, shape, checkpoint['seed_sections_private'][0])
    if len(selected) != 3:
        raise ValueError('expected exactly three independently identified intake branch/cap edges')
    args.output.mkdir(mode=0o700)
    report = {'schema': 'private-local-port-junction-fillet/v1', 'inputs_sha256': hashes,
              'status': 'prototype_running', 'radius_scan_units': args.radius,
              'radius_is_exploratory_not_OEM': True,
              'selected_edges_private': [{'index': i, 'radial_sample_max': r} for i, e, r in selected],
              'source_topology': original, 'master_modified': False,
              'manufacturing_authorized': False, 'CFD_performance_proved': False,
              'complete_branch_junction_fairing_claimed': False}
    ports.save(args.output/'execution-context.json', report)
    maker, build = build_fillet(shape, [e for i, e, r in selected], args.radius, args.construction_mode)
    report['build'] = build
    if not build['done']:
        report['status'] = 'rejected_fillet_construction'
    else:
        candidate = maker.Shape()
        path = args.output/'intake-junction-prototype.brep'
        BRepTools.Write_s(candidate, str(path)); path.chmod(0o600)
        report['candidate_BRep_sha256'] = ports.sha(path)
        report['candidate_topology'] = topology(cad, candidate)
        report['candidate_BOP'] = ports.bop_check(candidate)
        reread = read_native(path)
        report['native_reread_topology'] = topology(cad, reread)
        report['native_reread_BOP'] = ports.bop_check(reread)
        generated = [f for i, e, r in selected for f in maker.Generated(e) if f.ShapeType() == TopAbs_FACE]
        report['generated_faces_count_with_history_duplicates'] = len(generated)
        report['generated_boundary_tangency_samples'] = sample_generated_tangency(cad, candidate, generated)
        report['source_bbox_private'] = ports.bbox(api, shape)
        report['candidate_bbox_private'] = ports.bbox(api, candidate)
        report['volume_adaptive_source'], report['source_volume_error_estimate'] = bounded.adaptive_volume(shape)
        report['volume_adaptive_candidate'], report['candidate_volume_error_estimate'] = bounded.adaptive_volume(candidate)
        report['topological_tolerance_max_not_increased'] = all(report['candidate_topology'][k]['tolerance_max'] <= original[k]['tolerance_max'] for k in ('faces','edges','vertices'))
        report['status'] = 'prototype_requires_section_and_protection_audit'
        report['native_reread_tolerance_max_not_increased'] = all(report['native_reread_topology'][k]['tolerance_max'] <= original[k]['tolerance_max'] for k in ('faces','edges','vertices'))
        if not report['candidate_topology']['valid'] or report['candidate_topology']['solids'] != 1 or report['candidate_BOP']['has_faulty'] or not report['topological_tolerance_max_not_increased'] or not report['native_reread_topology']['valid'] or report['native_reread_topology']['solids'] != 1 or report['native_reread_BOP']['has_faulty'] or not report['native_reread_tolerance_max_not_increased']:
            report['status'] = 'rejected_native_or_tolerance_audit'
    report['input_files_unchanged'] = all(ports.sha(p) == hashes[k] for k, p in inputs.items())
    report['wall_seconds'] = time.monotonic()-start
    ports.save(args.output/'junction-fillet-report.json', report)
    print(json.dumps({'status': report['status'], 'build': build, 'wall_seconds': report['wall_seconds']}), flush=True)
    return 2  # No prototype is a fabrication or complete-CAD acceptance.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('negative','checkpoint','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--radius', type=float, default=1.)
    parser.add_argument('--construction-mode', choices=CONSTRUCTION_MODES, default='default')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (300,305))
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
