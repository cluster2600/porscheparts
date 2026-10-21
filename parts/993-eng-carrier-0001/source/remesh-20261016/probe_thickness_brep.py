"""Check selected existing ray-map locations against exact STEP inward normals."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build123d import Face, import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt


def run(step, localisation, output, expected_step_sha256):
    step, localisation, output = map(Path, (step, localisation, output))
    digest = hashlib.sha256(step.read_bytes()).hexdigest()
    if digest != expected_step_sha256:
        raise ValueError('Exact STEP hash mismatch')
    if output.exists():
        raise ValueError('Fresh output file required')
    body = import_step(step)
    shell = body.shells()[0].wrapped
    body_faces = list(body.faces())
    def face_info(face):
        wrapped = Face(face)
        bounds = wrapped.bounding_box()
        return {'STEP_face_index_zero_based': next((i for i, item in enumerate(body_faces) if item.wrapped.IsSame(face)), None),
                'surface_type': str(BRepAdaptor_Surface(face, True).GetType()),
                'surface_area_mm2': wrapped.area, 'bounds_mm': [list(bounds.min), list(bounds.max)]}
    report = {'STEP_sha256': digest,
              'localisation_sha256': hashlib.sha256(localisation.read_bytes()).hexdigest(),
              'method': 'nearest exact shell face; inward analytic surface normal; next shell intersection in (1e-5, 6] mm',
              'scope': 'Selected diagnostic probes, not a global minimum-thickness certificate',
              'probes': []}
    for source in json.loads(localisation.read_text())['mesh_face_probes']:
        row = dict(source)
        query = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*source['centroid_mm'])).Shape(), shell)
        query.Perform()
        row['mesh_centroid_distance_to_exact_shell_mm'] = query.Value()
        try:
            point = query.PointOnShape2(1)
            face = TopoDS.Face_s(query.SupportOnShape2(1))
            u, v = query.ParOnFaceS2(1)
            props = BRepLProp_SLProps(BRepAdaptor_Surface(face, True), u, v, 1, 1e-9)
            if not props.IsNormalDefined():
                raise ValueError('Analytic normal undefined')
            normal = np.array(props.Normal().Coord())
            if normal @ source['outward_normal'] < 0:
                normal = -normal
            row['normal_alignment_to_mesh'] = float(normal @ source['outward_normal'])
            ray = IntCurvesFace_ShapeIntersector()
            ray.Load(shell, 1e-8)
            ray.Perform(gp_Lin(point, gp_Dir(*(-normal))), 1e-5, 6.)
            hits = [(ray.WParameter(i), i) for i in range(1, ray.NbPnt() + 1) if ray.WParameter(i) > 1e-5]
            row.update(exact_surface_point_mm=list(point.Coord()), exact_outward_normal=normal.tolist(),
                       exact_inward_normal_ray_mm=min(hits)[0] if hits else None,
                       source_exact_face=face_info(face),
                       status='measured' if hits else 'no_intersection_within_6_mm')
            if hits:
                _, index = min(hits)
                row.update(opposite_exact_point_mm=list(ray.Pnt(index).Coord()), opposite_exact_face=face_info(ray.Face(index)))
        except (ValueError, RuntimeError) as error:
            row.update(status='unmeasured', reason=str(error))
        report['probes'].append(row)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'localisation', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--expected-step-sha256', required=True)
    args = parser.parse_args()
    run(args.step, args.localisation, args.output, args.expected_step_sha256)
