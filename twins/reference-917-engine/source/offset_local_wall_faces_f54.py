#!/usr/bin/env python3
"""Trial outward offsets on exact-CAD suspect nonadjacent BSpline face pairs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--step', type=Path, required=True)
    p.add_argument('--rays', type=Path, required=True)
    p.add_argument('--helpers', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--intersection-join', action='store_true')
    a = p.parse_args()
    rays = json.loads(a.rays.read_text())
    source_hash = hashlib.sha256(a.step.read_bytes()).hexdigest()
    if source_hash != rays['step_sha256']:
        raise ValueError('ray attribution does not match STEP')
    ids = sorted({r[key] for r in rays['records_private']
                  if r['status'] == 'resolved_inside' and not r['faces_share_edge']
                  and r['cad_ray_scan_units'] < 1.5
                  for key in ('entry_face_private', 'exit_face_private')})
    if not ids:
        raise ValueError('no qualified local face targets')
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step, brepcheck, topology, shape_properties
    from repair_topology_f42_1 import indexed, write_step, property_delta
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepOffset import BRepOffset_MakeOffset
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_BSplineSurface, GeomAbs_Intersection
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    original, _ = read_step(a.step)
    shape = BRepBuilderAPI_Copy(original, True, False).Shape()
    faces = indexed(shape, TopAbs_FACE)
    maker = BRepOffset_MakeOffset()
    if a.intersection_join:
        maker.Initialize(shape, 0., 1e-7, Intersection=True, Join=GeomAbs_Intersection)
    else:
        maker.Initialize(shape, 0., 1e-7)
    for index in ids:
        face = TopoDS.Face_s(faces.FindKey(index))
        if BRepAdaptor_Surface(face).GetType() != GeomAbs_BSplineSurface:
            raise ValueError('non-BSpline target rejected')
        maker.SetOffsetOnFace(face, .5)
    report = {'schema': 'porsche-local-wall-offset-trial-f54/v1',
              'source_sha256': source_hash,
              'attribution_sha256': hashlib.sha256(a.rays.read_bytes()).hexdigest(),
              'faces_private': ids, 'offset_scan_units': .5,
              'intersection_join': a.intersection_join,
              'manufacturing_authorized': False, 'accepted': False}
    try:
        maker.MakeOffsetShape()
        report['kernel_done'] = maker.IsDone()
        report['kernel_error'] = str(maker.Error())
        if maker.IsDone():
            candidate = maker.Shape()
            path = a.output / 'candidate.step'
            write_step(candidate, path)
            reloaded, _ = read_step(path)
            report.update({'step_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'brepcheck': brepcheck(reloaded), 'topology': topology(reloaded),
                           'property_delta': property_delta(shape_properties(original), shape_properties(reloaded)),
                           'full_BOP_thickness_fit_and_cooling_audits_required': True})
    finally:
        (a.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report.get('kernel_done') else 2


if __name__ == '__main__':
    raise SystemExit(main())
