#!/usr/bin/env python3
"""Bounded concave-fillet trial on a diagnosed private transition patch.

The trial may move a local air-channel boundary. It does not replace the scan
envelope and never promotes a manufacturing or M64 fit claim.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step', type=Path, required=True)
    parser.add_argument('--patches', type=Path, required=True)
    parser.add_argument('--helpers', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--radius', type=float, default=.8)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    if not math.isfinite(args.radius) or args.radius <= 0 or args.radius > 1:
        raise ValueError('radius outside bounded trial range')
    source = json.loads(args.patches.read_text())
    if hashlib.sha256(args.step.read_bytes()).hexdigest() != source['source_sha256']['step']:
        raise ValueError('source hash mismatch')
    args.output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step, brepcheck, topology, shape_properties
    from repair_topology_f42_1 import indexed, write_step, property_delta
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_IN
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt, gp_Vec

    original = read_step(args.step)[0]
    shape = BRepBuilderAPI_Copy(original, True, False).Shape()
    faces, edges = indexed(shape, TopAbs_FACE), indexed(shape, TopAbs_EDGE)
    patch = min(source['patches_private'], key=lambda p: p['minimum_sampled_ray_scan_units'])
    candidates = {}
    for face_id in patch['face_pair_private']:
        face_edges = indexed(faces.FindKey(face_id), TopAbs_EDGE)
        for neighbor in patch['common_neighbors_private']:
            neighbor_edges = indexed(faces.FindKey(neighbor), TopAbs_EDGE)
            for j in range(1, face_edges.Extent()+1):
                edge = face_edges.FindKey(j)
                if neighbor_edges.Contains(edge):
                    candidates[edges.FindIndex(edge)] = TopoDS.Edge_s(edge)
    classifier = BRepClass3d_SolidClassifier(shape)
    rows = []
    for index, edge in candidates.items():
        curve = BRepAdaptor_Curve(edge)
        point, tangent = gp_Pnt(), gp_Vec()
        curve.D1((curve.FirstParameter()+curve.LastParameter())*.5, point, tangent)
        axis = np.array([tangent.X(), tangent.Y(), tangent.Z()])
        axis /= np.linalg.norm(axis)
        ref = np.array([0.,0.,1.]) if abs(axis[2]) < .9 else np.array([0.,1.,0.])
        u = np.cross(axis, ref); u /= np.linalg.norm(u); v = np.cross(axis, u)
        center = np.array([point.X(),point.Y(),point.Z()])
        fractions = []
        for radius in (.02, .05):
            states = []
            for angle in (np.arange(36)+.37)*2*np.pi/36:
                sample = center+radius*(u*np.cos(angle)+v*np.sin(angle))
                classifier.Perform(gp_Pnt(*sample), 1e-7)
                states.append(classifier.State() == TopAbs_IN)
            fractions.append(sum(states)/len(states))
        rows.append({'edge_id_private': index, 'sampled_solid_fractions': fractions,
                     'concave_screen': all(.55 < f < .95 for f in fractions)})
    report = {'schema': 'm64-reference-local-concave-fillet-trial/v1',
              'source_sha256': source['source_sha256']['step'],
              'patches_sha256': hashlib.sha256(args.patches.read_bytes()).hexdigest(),
              'radius_scan_units': args.radius, 'edge_diagnostics_private': rows,
              'patch_faces_private': patch['face_pair_private'], 'repair_accepted': False,
              'manufacturing_authorized': False, 'input_modified': False}
    report_path = args.output/'report.json'
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    selected = [r['edge_id_private'] for r in rows if r['concave_screen']]
    if not selected:
        report['status'] = 'rejected_no_screened_concave_junction'
    else:
        # One edge only: preserve evidence of a bounded kernel attempt.
        selected = selected[:1]
        maker = BRepFilletAPI_MakeFillet(shape)
        maker.Add(args.radius, candidates[selected[0]])
        report['selected_edges_private'] = selected
        try:
            maker.Build()
            report['kernel_done'] = maker.IsDone()
            if maker.IsDone():
                candidate = maker.Shape()
                report.update({'brepcheck': brepcheck(candidate),
                               'topology': topology(candidate),
                               'property_delta': property_delta(shape_properties(original), shape_properties(candidate))})
                if report['brepcheck']['shape_valid']:
                    path = args.output/'candidate.step'
                    write_step(candidate, path)
                    report['candidate_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                    report['status'] = 'candidate_requires_BOP_deviation_and_wall_reaudit'
                else:
                    report['status'] = 'rejected_invalid_BRep'
            else:
                report['status'] = 'rejected_kernel_not_done'
        except Exception as exc:
            report['status'] = 'rejected_kernel_exception'
            report['exception_type'] = type(exc).__name__
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
