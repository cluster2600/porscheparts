#!/usr/bin/env python3
"""Compare fixed private wall rays against candidate and retained source envelope.

This is a source-attribution audit, never a minimum-thickness or fit release.
Distances are in uncertified scan units. No geometry is modified.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys


def classify_origin(candidate, envelope_intervals, tolerance=1e-4):
    """Require interval containment; distinguish inherited and cut-created ends."""
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('invalid tolerance')
    start, end = candidate
    if not all(math.isfinite(x) for x in candidate) or end <= start:
        raise ValueError('invalid candidate interval')
    containing = [(a, b) for a, b in envelope_intervals
                  if a <= start + tolerance and b >= end - tolerance]
    if len(containing) != 1:
        return {'origin': 'unresolved_envelope_containment'}
    a, b = containing[0]
    same_start = abs(a-start) <= tolerance
    same_end = abs(b-end) <= tolerance
    return {'origin': 'inherited_envelope' if same_start and same_end
            else 'candidate_cut_boundary',
            'entry_inherited': same_start, 'exit_inherited': same_end,
            'envelope_ray_scan_units': b-a,
            'envelope_interval_scan_units_private': [a, b]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'envelope', 'probes', 'attribution'):
        parser.add_argument('--'+name, type=Path, required=True)
        parser.add_argument('--'+name+'-sha256', required=True)
    parser.add_argument('--helpers', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for name in ('step', 'envelope', 'probes', 'attribution'):
        if hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() != getattr(args, name+'_sha256'):
            raise ValueError(name+' hash mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    source = json.loads(args.attribution.read_text())
    if source['step_sha256'] != args.step_sha256 or source['probes_sha256'] != args.probes_sha256:
        raise ValueError('attribution provenance mismatch')
    import numpy as np
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt, gp_Dir, gp_Lin

    shapes = [read_step(path)[0] for path in (args.step, args.envelope)]
    intersectors = []
    classifiers = [BRepClass3d_SolidClassifier(shape) for shape in shapes]
    for shape in shapes:
        intersector = IntCurvesFace_ShapeIntersector()
        intersector.Load(shape, 1e-7)
        intersectors.append(intersector)

    def intervals(index, point, direction):
        intersector = intersectors[index]
        intersector.Perform(gp_Lin(gp_Pnt(*point), gp_Dir(*direction)), -500., 500.)
        if not intersector.IsDone():
            return []
        hits = sorted(intersector.WParameter(i) for i in range(1, intersector.NbPnt()+1))
        unique = []
        for hit in hits:
            if not unique or hit-unique[-1] > 1e-6:
                unique.append(hit)
        result = []
        for a, b in zip(unique, unique[1:]):
            mid = point + direction * ((a+b)*.5)
            classifiers[index].Perform(gp_Pnt(*mid), 1e-7)
            if classifiers[index].State() == TopAbs_IN:
                result.append((a, b))
        return result

    data = np.load(args.probes)
    rows = []
    for old in source['records_private']:
        row = {'probe_index_private': old['probe_index_private'],
               'prior_status': old['status'], 'origin': 'prior_unresolved'}
        if old['status'] == 'resolved_inside':
            i = old['probe_index_private']
            point, direction = data['points'][i], -data['normals'][i]
            expected = (old['entry_offset_scan_units'],
                        old['entry_offset_scan_units']+old['cad_ray_scan_units'])
            candidates = [pair for pair in intervals(0, point, direction)
                          if max(abs(a-b) for a, b in zip(pair, expected)) <= 1e-5]
            if len(candidates) != 1:
                row['origin'] = 'candidate_reproduction_failed'
            else:
                row.update(classify_origin(candidates[0], intervals(1, point, direction)))
                row['candidate_ray_scan_units'] = candidates[0][1]-candidates[0][0]
                row['faces_share_edge'] = old['faces_share_edge']
        rows.append(row)
    summary = {'probe_count': len(rows),
               'origin_counts': dict(Counter(row['origin'] for row in rows)),
               'nonadjacent_origin_counts': dict(Counter(row['origin'] for row in rows
                                                        if row.get('faces_share_edge') is False))}
    report = {'schema': 'm64-reference-wall-origin/v1',
              'source_sha256': {name: getattr(args, name+'_sha256')
                                for name in ('step', 'envelope', 'probes', 'attribution')},
              'summary': summary, 'records_private': rows,
              'input_geometry_modified': False,
              'classification': '935_scan_derived_research_reference_not_M64_fitment',
              'minimum_wall_verified': False, 'absolute_scale_certified': False,
              'manufacturing_authorized': False}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
