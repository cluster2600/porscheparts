#!/usr/bin/env python3
"""Adaptively interpolate cylinder p-curves on a private copy, then audit STEP."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--helpers', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-partial', action='store_true',
                   help='Leave unsupported surfaces untouched and report remaining faults')
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step, brepcheck, topology, shape_properties
    from repair_pcurves_f42_2 import pcurve_fault_map
    from repair_topology_f42_1 import indexed, write_step, property_delta
    from OCP.BRep import BRep_Tool, BRep_Builder
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.ElSLib import ElSLib
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.Geom2dAPI import Geom2dAPI_Interpolate
    from OCP.TColgp import TColgp_HArray1OfPnt2d
    from OCP.TColStd import TColStd_HArray1OfReal
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
    from OCP.TopoDS import TopoDS

    original, _ = read_step(a.input)
    shape = BRepBuilderAPI_Copy(original, True, False).Shape()
    faults = pcurve_fault_map(shape)
    faces, edges = indexed(shape, TopAbs_FACE), indexed(shape, TopAbs_EDGE)
    records = []
    skipped = []
    for fi, ei in faults['face_edge_pairs_private']:
        face, edge = TopoDS.Face_s(faces.FindKey(fi)), TopoDS.Edge_s(edges.FindKey(ei))
        if BRepAdaptor_Surface(face).GetType() != GeomAbs_Cylinder or BRep_Tool.IsClosed_s(edge, face):
            if a.allow_partial:
                skipped.append([fi, ei])
                continue
            raise ValueError('only non-seam cylindrical faults supported')
        surface = BRep_Tool.Surface_s(face)
        cylinder = surface.Cylinder()
        curve = BRep_Tool.Curve_s(edge, 0., 0.)
        old_pcurve = BRep_Tool.CurveOnSurface_s(edge, face, 0., 0.)
        start, end = BRep_Tool.Range_s(edge)
        parameters = [start + (end-start)*i/32 for i in range(33)]
        for iteration in range(12):
            points = TColgp_HArray1OfPnt2d(1, len(parameters))
            params = TColStd_HArray1OfReal(1, len(parameters))
            for i, t in enumerate(parameters, 1):
                u, v = ElSLib.Parameters_s(cylinder, curve.Value(t))
                u += 2*math.pi*round((old_pcurve.Value(t).X()-u)/(2*math.pi))
                points.SetValue(i, gp_Pnt2d(u, v))
                params.SetValue(i, t)
            interpolator = Geom2dAPI_Interpolate(points, params, False, 1e-12)
            interpolator.Perform()
            if not interpolator.IsDone():
                raise RuntimeError('interpolation failed')
            result = interpolator.Curve()
            errors, extra = [], []
            for lo, hi in zip(parameters, parameters[1:]):
                for fraction in (0.25, 0.5, 0.75):
                    t = lo+(hi-lo)*fraction
                    uv = result.Value(t)
                    distance = curve.Value(t).Distance(surface.Value(uv.X(), uv.Y()))
                    errors.append(distance)
                    if distance > 8e-8:
                        extra.append(t)
            if not extra:
                break
            parameters = sorted(set(parameters + extra))
            if len(parameters) > 12000:
                raise RuntimeError('adaptive point budget exceeded')
        else:
            raise RuntimeError('adaptive error target not achieved')
        BRep_Builder().UpdateEdge(edge, result, face, BRep_Tool.Tolerance_s(edge))
        records.append({'face_private': fi, 'edge_private': ei, 'points': len(parameters),
                        'iterations': iteration+1, 'held_out_sampled_max_error': max(errors)})
    before = pcurve_fault_map(shape)['result_count']
    out = a.output / 'candidate.step'
    write_step(shape, out)
    reloaded, _ = read_step(out)
    report = {'schema': 'porsche-cylinder-pcurves-adaptive-f53/v1',
              'source_sha256': a.sha256, 'step_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
              'repairs_private': records, 'faults_before_export': before,
              'unsupported_pairs_private': skipped,
              'faults_after_roundtrip': pcurve_fault_map(reloaded)['result_count'],
              'brepcheck': brepcheck(reloaded), 'topology': topology(reloaded),
              'property_delta': property_delta(shape_properties(original), shape_properties(reloaded)),
              'manufacturing_authorized': False,
              'full_BOP_and_surface_audit_required': True}
    (a.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 2 if before or report['faults_after_roundtrip'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
