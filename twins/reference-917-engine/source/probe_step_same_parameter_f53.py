#!/usr/bin/env python3
"""Private local SameParameter trial; tolerance changes are reported, never accepted implicitly."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--helpers', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reproject', action='store_true',
                   help='Rebuild faulty p-curves at 1e-7 before SameParameter')
    p.add_argument('--rebuild-3d', action='store_true',
                   help='Experimental reconstruction of faulty 3D edges on a private copy')
    p.add_argument('--direct-project', action='store_true',
                   help='Project via GeomProjLib without SameParameter refitting')
    p.add_argument('--projection-tolerance', type=float, choices=(1e-9, 1e-12), default=1e-9)
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step, brepcheck, shape_properties
    from repair_topology_f42_1 import indexed, property_delta, write_step
    from repair_pcurves_f42_2 import pcurve_fault_map, max_subshape_tolerance, reproject_pairs
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepLib import BRepLib
    from OCP.ShapeFix import ShapeFix_Edge
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.GeomProjLib import GeomProjLib
    from OCP.TopoDS import TopoDS
    source, _ = read_step(a.input)
    candidate = BRepBuilderAPI_Copy(source, True, False).Shape()
    faults = pcurve_fault_map(candidate)
    reprojection = None
    if a.reproject:
        reprojection = reproject_pairs(candidate,
                                      [tuple(pair) for pair in faults['face_edge_pairs_private']],
                                      1e-7)
    edges = indexed(candidate, TopAbs_EDGE)
    if a.direct_project:
        faces = indexed(candidate, TopAbs_FACE)
        for fi, ei in faults['face_edge_pairs_private']:
            face = TopoDS.Face_s(faces.FindKey(fi))
            edge = TopoDS.Edge_s(edges.FindKey(ei))
            if BRep_Tool.IsClosed_s(edge, face):
                raise ValueError('seam projection unsupported')
            start, end = BRep_Tool.Range_s(edge)
            projection = GeomProjLib.Curve2d_s(BRep_Tool.Curve_s(edge, 0., 0.),
                start, end, BRep_Tool.Surface_s(face), a.projection_tolerance)
            if projection is None:
                raise RuntimeError('direct projection failed')
            BRep_Builder().UpdateEdge(edge, projection, face, BRep_Tool.Tolerance_s(edge))
    corrections = []
    for i in sorted({pair[1] for pair in faults['face_edge_pairs_private']}):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        before = BRep_Tool.Tolerance_s(edge)
        rebuilt = None
        deviation = None
        if a.rebuild_3d:
            old_curve = BRep_Tool.Curve_s(edge, 0., 0.)
            start, end = BRep_Tool.Range_s(edge)
            BRep_Builder().UpdateEdge(edge, None, 1e-7)
            rebuilt = BRepLib.BuildCurve3d_s(edge, 1e-7)
            if not rebuilt:
                raise RuntimeError('3D reconstruction failed')
            new_curve = BRep_Tool.Curve_s(edge, 0., 0.)
            deviation = max(old_curve.Value(start + (end-start)*j/1000).Distance(
                new_curve.Value(start + (end-start)*j/1000)) for j in range(1001))
        changed = False
        if not a.direct_project:
            BRep_Builder().SameParameter(edge, False)
            changed = ShapeFix_Edge().FixSameParameter(edge, 1e-7)
        corrections.append({'edge_private': i, 'changed': changed,
                            'curve3d_rebuilt': rebuilt,
                            'sampled_same_parameter_3d_displacement': deviation,
                            'tolerance_before': before,
                            'tolerance_after': BRep_Tool.Tolerance_s(edge)})
    before_export = pcurve_fault_map(candidate)['result_count']
    out = a.output / 'candidate.step'
    write_step(candidate, out)
    reloaded, _ = read_step(out)
    report = {'schema': 'porsche-head-same-parameter-f53/v1',
              'source_sha256': a.sha256,
              'step_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
              'faults_before': faults['result_count'],
              'reprojection': reprojection,
              'direct_projection': a.direct_project,
              'requested_projection_tolerance': a.projection_tolerance if a.direct_project else None,
              'faults_before_export': before_export,
              'faults_after_roundtrip': pcurve_fault_map(reloaded)['result_count'],
              'corrections_private': corrections,
              'roundtrip_tolerances': max_subshape_tolerance(reloaded),
              'roundtrip_brepcheck': brepcheck(reloaded),
              'property_delta': property_delta(shape_properties(source), shape_properties(reloaded)),
              'surface_deviation_and_full_BOP_audit_required': True,
              'manufacturing_authorized': False}
    (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
