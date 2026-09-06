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
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step, brepcheck, shape_properties
    from repair_topology_f42_1 import indexed, property_delta, write_step
    from repair_pcurves_f42_2 import pcurve_fault_map, max_subshape_tolerance
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.ShapeFix import ShapeFix_Edge
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    source, _ = read_step(a.input)
    candidate = BRepBuilderAPI_Copy(source, True, False).Shape()
    faults = pcurve_fault_map(candidate)
    edges = indexed(candidate, TopAbs_EDGE)
    corrections = []
    for i in sorted({pair[1] for pair in faults['face_edge_pairs_private']}):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        before = BRep_Tool.Tolerance_s(edge)
        BRep_Builder().SameParameter(edge, False)
        changed = ShapeFix_Edge().FixSameParameter(edge, 1e-7)
        corrections.append({'edge_private': i, 'changed': changed,
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
