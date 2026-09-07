#!/usr/bin/env python3
"""One reversible BRepFill_Filling trial with fixed boundary edges and one point.

Private research geometry only. A successful kernel build is not an accepted
repair: all checks and the retained scan contour still require explicit audit.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys


def compare_fixed_rays(baseline, candidate, tolerance=1e-5):
    """Compare identical ray algorithms, never infer gain from resolution count."""
    if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('invalid ray comparison tolerance')
    for row in (*baseline, *candidate):
        if row.get('status') not in ('resolved', 'unresolved'):
            raise ValueError('unknown ray status')
        if row['status'] == 'resolved':
            length = row.get('ray_scan_units')
            if (isinstance(length, bool) or not isinstance(length, (int, float))
                    or not math.isfinite(length) or length <= 0):
                raise ValueError('invalid resolved ray length')
    old = {r['probe_private']: r for r in baseline}
    if (len(old) != len(baseline) or len(candidate) != len(baseline)
            or {r['probe_private'] for r in candidate} != set(old)):
        raise ValueError('ray identity mismatch')
    counts = Counter()
    for row in candidate:
        previous = old[row['probe_private']]
        if row['status'] != 'resolved' or previous['status'] != 'resolved':
            counts['not_paired_resolved'] += 1
        else:
            delta = row['ray_scan_units']-previous['ray_scan_units']
            counts['increased' if delta > tolerance else 'decreased' if delta < -tolerance
                   else 'unchanged_within_tolerance'] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'patches', 'attribution', 'probes', 'helpers', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--displacement', type=float, default=.85)
    parser.add_argument('--refined', action='store_true')
    parser.add_argument('--extra-refined', action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.displacement) or not 0 < args.displacement <= 1:
        raise ValueError('displacement outside bounded trial range')
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    patches = json.loads(args.patches.read_text())
    for name in ('step', 'attribution', 'probes'):
        if hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() != patches['source_sha256'][name]:
            raise ValueError(name+' provenance mismatch')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'm64-reference-local-transition-filling-trial/v1',
              'source_sha256': patches['source_sha256'],
              'local_displacement_scan_units': args.displacement,
              'input_modified': False, 'repair_accepted': False,
              'manufacturing_authorized': False, 'stage': 'loading'}
    def save(stage):
        report['stage'] = stage
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'stage': stage}), flush=True)
    save('loading')
    import numpy as np
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step, brepcheck, topology, shape_properties
    from repair_topology_f42_1 import indexed, write_step, property_delta
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer, BRepTools_ReShape
    from OCP.BRepFill import BRepFill_Filling
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.GeomAbs import GeomAbs_C0
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SHELL, TopAbs_EDGE, TopAbs_IN, TopAbs_OUT, TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.GeomLProp import GeomLProp_SLProps
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.gp import gp_Pnt, gp_Dir, gp_Lin

    original = read_step(args.step)[0]
    shape = BRepBuilderAPI_Copy(original, True, False).Shape()
    faces = indexed(shape, TopAbs_FACE)
    patch = min(patches['patches_private'], key=lambda p: p['minimum_sampled_ray_scan_units'])
    probe = min(patch['probes_private'], key=lambda p: p['cad_ray_scan_units'])
    attribution = json.loads(args.attribution.read_text())
    old = next(r for r in attribution['records_private'] if r['probe_index_private'] == probe['index'])
    face = TopoDS.Face_s(faces.FindKey(old['entry_face_private']))
    entry = np.array(probe['entry_xyz_scan_units'])
    direction = np.array(probe['direction'])
    target = entry-args.displacement*direction
    classifier = BRepClass3d_SolidClassifier(shape)
    classifier.Perform(gp_Pnt(*target), 1e-7)
    report.update({'selected_face_private': old['entry_face_private'],
                   'probe_private': probe['index'], 'target_private': target.tolist(),
                   'target_classification': str(classifier.State()),
                   'point_moves_into_existing_solid': classifier.State() == TopAbs_IN})
    if classifier.State() != TopAbs_OUT:
        save('rejected_target_not_outside_original'); return
    parameters = ({'Tol2d':1e-8, 'Tol3d':1e-8, 'NbPtsOnCur':75, 'NbIter':5,
                   'MaxDeg':12, 'MaxSegments':48} if args.refined else
                  {'Tol2d':1e-7, 'Tol3d':1e-6, 'NbPtsOnCur':30, 'NbIter':3})
    if args.extra_refined:
        parameters = {'Tol2d':1e-9, 'Tol3d':1e-9, 'NbPtsOnCur':120, 'NbIter':6,
                      'MaxDeg':14, 'MaxSegments':96}
    report['filling_parameters'] = parameters
    filler = BRepFill_Filling(**parameters)
    wire = BRepTools.OuterWire_s(face)
    explorer = BRepTools_WireExplorer(wire, face)
    boundary_constraints = []
    boundary_edges = []
    while explorer.More():
        boundary_edges.append(explorer.Current())
        boundary_constraints.append(filler.Add(explorer.Current(), GeomAbs_C0, True))
        explorer.Next()
    if len(boundary_constraints) != indexed(face, TopAbs_EDGE).Extent():
        save('rejected_inner_wire_or_duplicate_edge'); return
    point_constraint = filler.Add(gp_Pnt(*target))
    report['boundary_constraint_count'] = len(boundary_constraints)
    save('building_filling')
    try:
        filler.Build()
        report['filling_done'] = filler.IsDone()
        if not filler.IsDone():
            save('rejected_filling_not_done'); return
        save('extracting_filled_face')
        new_face = filler.Face()
        save('measuring_filled_face_constraints')
        # Measure source curves and point against the built surface directly;
        # do not depend on the runtime's undocumented G0Error index mapping.
        point_projection = GeomAPI_ProjectPointOnSurf(gp_Pnt(*target), BRep_Tool.Surface_s(new_face))
        boundary_errors = []
        boundary_samples = 121 if args.extra_refined else 31
        for edge in boundary_edges:
            curve = BRepAdaptor_Curve(edge)
            distances = []
            for parameter in np.linspace(curve.FirstParameter(), curve.LastParameter(), boundary_samples):
                projector = GeomAPI_ProjectPointOnSurf(curve.Value(float(parameter)), BRep_Tool.Surface_s(new_face))
                distances.append(projector.LowerDistance())
            boundary_errors.append(max(distances))
        report['constraint_error'] = {'boundary_sample_count_per_edge': boundary_samples,
                    'boundary_max_sample_distance': boundary_errors,
                    'point_surface_distance': point_projection.LowerDistance()}
        write_step(new_face, args.output/'private-replacement-face.step')
        report['replacement_face_brepcheck'] = brepcheck(new_face)
        report['constraints_within_tolerance'] = (max(boundary_errors) <= 1e-5 and
                             report['constraint_error']['point_surface_distance'] <= 1e-5)
        if not report['constraints_within_tolerance']:
            # Do not weaken acceptance. Continue only to diagnose whether this
            # already rejected face can close the shell and what it does to rays.
            save('rejected_constraints_continuing_diagnostic_checks')
        if not report['replacement_face_brepcheck']['shape_valid']:
            save('rejected_invalid_replacement_face'); return
        def outward_normal(item, point):
            surface = BRep_Tool.Surface_s(item)
            projector = GeomAPI_ProjectPointOnSurf(gp_Pnt(*point), surface)
            u, v = projector.LowerDistanceParameters()
            props = GeomLProp_SLProps(surface, u, v, 1, 1e-8)
            normal = props.Normal()
            value = np.array([normal.X(),normal.Y(),normal.Z()])
            return -value if item.Orientation() == TopAbs_REVERSED else value
        if np.dot(outward_normal(face, entry), outward_normal(new_face, target)) < 0:
            new_face.Reverse()
        replacer = BRepTools_ReShape(); replacer.Replace(face, new_face)
        replaced = replacer.Apply(shape)
        save('sewing_replacement')
        sewer = BRepBuilderAPI_Sewing(1e-5)
        sewer.Add(replaced); sewer.Perform()
        sewed = sewer.SewedShape()
        shells = indexed(sewed, TopAbs_SHELL)
        report['sewing'] = {'free_edges': sewer.NbFreeEdges(),
                            'multiple_edges': sewer.NbMultipleEdges(), 'shell_count': shells.Extent()}
        if shells.Extent() != 1 or sewer.NbFreeEdges() or sewer.NbMultipleEdges():
            save('rejected_sewing_not_one_closed_shell'); return
        candidate = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shells.FindKey(1))).Solid()
        report['brepcheck'] = brepcheck(candidate)
        report['topology'] = topology(candidate)
        report['property_delta'] = property_delta(shape_properties(original), shape_properties(candidate))
        if not report['brepcheck']['shape_valid']:
            save('rejected_invalid_candidate'); return
        path = args.output/'diagnostic-candidate.step'; write_step(candidate, path)
        candidate = read_step(path)[0]
        report['candidate_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['roundtrip_brepcheck'] = brepcheck(candidate)
        save('reauditing_42_fixed_rays')
        data = np.load(args.probes)
        def measure_rays(shape_to_measure):
            intersector = IntCurvesFace_ShapeIntersector(); intersector.Load(shape_to_measure, 1e-7)
            classifier = BRepClass3d_SolidClassifier(shape_to_measure)
            rows = []
            for prior in attribution['records_private']:
                i = prior['probe_index_private']; point, vector = data['points'][i], -data['normals'][i]
                intersector.Perform(gp_Lin(gp_Pnt(*point), gp_Dir(*vector)), -2., 500.)
                hits = sorted(intersector.WParameter(k) for k in range(1, intersector.NbPnt()+1))
                intervals = []
                for a, b in zip(hits, hits[1:]):
                    if b-a <= 1e-6 or a > .05 or b < 0: continue
                    classifier.Perform(gp_Pnt(*(point+vector*(a+b)*.5)), 1e-7)
                    if classifier.State() == TopAbs_IN: intervals.append((a,b))
                row = {'probe_private': i, 'prior_ray_scan_units': prior.get('cad_ray_scan_units'), 'status':'unresolved'}
                if len(intervals) == 1:
                    row.update({'status':'resolved', 'ray_scan_units': intervals[0][1]-intervals[0][0],
                                'entry_shift_scan_units': intervals[0][0]})
                rows.append(row)
            return rows
        baseline_rows = measure_rays(original)
        rows = measure_rays(candidate)
        report['baseline_fixed_rays_private'] = baseline_rows
        report['fixed_rays_private'] = rows
        report['fixed_ray_summary'] = dict(Counter(r['status'] for r in rows))
        report['paired_fixed_ray_summary'] = compare_fixed_rays(baseline_rows, rows)
        save('checking_self_intersections')
        analyzer = BOPAlgo_ArgumentAnalyzer(); analyzer.SetShape1(candidate)
        analyzer.SelfInterMode = True; analyzer.StopOnFirstFaulty = True; analyzer.Perform()
        report['self_intersection_check'] = {'has_faulty': analyzer.HasFaulty(),
            'status_counts': dict(Counter(str(r.GetCheckStatus()) for r in analyzer.GetCheckResult()))}
        if analyzer.HasFaulty():
            save('rejected_self_intersection')
        elif not report['constraints_within_tolerance']:
            save('rejected_boundary_constraints_despite_diagnostic_checks')
        else:
            save('candidate_requires_full_deviation_thickness_and_CHT')
    except Exception as exc:
        report['exception_type'] = type(exc).__name__
        report['exception_message'] = str(exc)[:200]
        save('rejected_kernel_exception')


if __name__ == '__main__':
    main()
