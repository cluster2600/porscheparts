#!/usr/bin/env python3
"""Attribute suspect private mesh wall rays to exact trimmed CAD surfaces."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--step', type=Path, required=True)
    p.add_argument('--step-sha256', required=True)
    p.add_argument('--probes', type=Path, required=True)
    p.add_argument('--probes-sha256', required=True)
    p.add_argument('--helpers', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    for path, digest in ((a.step, a.step_sha256), (a.probes, a.probes_sha256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('input hash mismatch')
    if a.output.exists():
        raise FileExistsError(a.output)
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_IN
    from OCP.gp import gp_Pnt, gp_Dir, gp_Lin
    shape, _ = read_step(a.step)
    faces = indexed(shape, TopAbs_FACE)
    intersector = IntCurvesFace_ShapeIntersector()
    intersector.Load(shape, 1e-7)
    data = np.load(a.probes)
    suspects = np.flatnonzero(data['ray'] < 1.5)
    records = []
    for index in suspects:
        point, direction = data['points'][index], -data['normals'][index]
        intersector.Perform(gp_Lin(gp_Pnt(*point), gp_Dir(*direction)), -5., 500.)
        row = {'probe_index_private': int(index), 'mesh_ray_scan_units': float(data['ray'][index])}
        if not intersector.IsDone() or intersector.NbPnt() < 2:
            row['status'] = 'unresolved_intersections'
            records.append(row)
            continue
        hits = sorted((intersector.WParameter(i), i) for i in range(1, intersector.NbPnt()+1))
        entry_t, entry_i = min(hits, key=lambda hit: abs(hit[0]))
        exits = [(t, i) for t, i in hits if t > entry_t + 1e-6]
        row['entry_offset_scan_units'] = float(entry_t)
        if abs(entry_t) > .05 or not exits:
            row['status'] = 'unresolved_entry_or_exit'
            records.append(row)
            continue
        exit_t, exit_i = exits[0]
        mid = point + direction * (.5*(entry_t+exit_t))
        classifier = BRepClass3d_SolidClassifier(shape, gp_Pnt(*mid), 1e-7)
        entry_face, exit_face = intersector.Face(entry_i), intersector.Face(exit_i)
        entry_edges, exit_edges = indexed(entry_face, TopAbs_EDGE), indexed(exit_face, TopAbs_EDGE)
        adjacent = any(exit_edges.Contains(entry_edges.FindKey(i)) for i in range(1, entry_edges.Extent()+1))
        row.update({'status': 'resolved_inside' if classifier.State() == TopAbs_IN else 'not_inside',
                    'cad_ray_scan_units': float(exit_t-entry_t),
                    'entry_face_private': faces.FindIndex(entry_face),
                    'exit_face_private': faces.FindIndex(exit_face),
                    'entry_surface': str(BRepAdaptor_Surface(entry_face).GetType()),
                    'exit_surface': str(BRepAdaptor_Surface(exit_face).GetType()),
                    'faces_share_edge': adjacent})
        records.append(row)
    resolved = [r for r in records if r['status'] == 'resolved_inside']
    summary = {'suspects': len(records), 'status_counts': dict(Counter(r['status'] for r in records)),
               'cad_rays_below_threshold': sum(r['cad_ray_scan_units'] < 1.5 for r in resolved),
               'resolved_adjacent_face_pairs': sum(r['faces_share_edge'] for r in resolved)}
    report = {'schema': 'porsche-exact-wall-ray-attribution-f54/v1',
              'step_sha256': a.step_sha256, 'probes_sha256': a.probes_sha256,
              'summary': summary, 'records_private': records,
              'absolute_scale_certified': False, 'manufacturing_authorized': False}
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
