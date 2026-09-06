#!/usr/bin/env python3
"""Inspect faulty STEP edge/surface pairs without modifying the input geometry."""
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
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    if a.output.exists():
        raise ValueError('output already exists')
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from repair_pcurves_f42_2 import pcurve_fault_map, pair_chord_deviation
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    shape, roots = read_step(a.input)
    faults = pcurve_fault_map(shape)
    faces, edges = indexed(shape, TopAbs_FACE), indexed(shape, TopAbs_EDGE)
    details = []
    for pair in faults['face_edge_pairs_private']:
        face = TopoDS.Face_s(faces.FindKey(pair[0]))
        edge = TopoDS.Edge_s(edges.FindKey(pair[1]))
        details.append({
            'pair_private': pair,
            'surface_type': str(BRepAdaptor_Surface(face).GetType()),
            'curve_type': str(BRepAdaptor_Curve(edge).GetType()),
            'seam': BRep_Tool.IsClosed_s(edge, face),
            'same_parameter': BRep_Tool.SameParameter_s(edge),
            'edge_tolerance_scan_units': BRep_Tool.Tolerance_s(edge),
            'face_tolerance_scan_units': BRep_Tool.Tolerance_s(face),
            'sampled_deviation': pair_chord_deviation(shape, tuple(pair), 1001),
        })
    report = {'schema': 'porsche-head-step-fault-inspection-f53/v1',
              'source_sha256': a.sha256, 'roots': roots,
              'faults': faults, 'details_private': details,
              'geometry_modified': False}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'fault_count': faults['result_count'], 'details': details}))


if __name__ == '__main__':
    main()
