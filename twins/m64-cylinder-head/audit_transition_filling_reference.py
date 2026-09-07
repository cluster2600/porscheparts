#!/usr/bin/env python3
"""Independent paired-ray, dense-edge and parameter audit of a private trial."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','candidate-step','replacement-face','trial-report','attribution','probes','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--replacement-face-sha256',required=True)
    a = p.parse_args()
    if a.output.exists(): raise FileExistsError(a.output)
    os.sched_setaffinity(0,[min(os.sched_getaffinity(0))])
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    r = json.loads(a.trial_report.read_text())
    hashes = {name:digest(getattr(a,name)) for name in
              ('source_step','candidate_step','replacement_face','trial_report','attribution','probes')}
    for name, expected in (('source_step',r['source_sha256']['step']),
            ('candidate_step',r['candidate_sha256']),('replacement_face',a.replacement_face_sha256),
            ('attribution',r['source_sha256']['attribution']),('probes',r['source_sha256']['probes'])):
        if hashes[name] != expected: raise ValueError(name+' hash mismatch')
    import numpy as np
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Curve2d
    from OCP.TopAbs import TopAbs_FACE,TopAbs_IN
    from OCP.TopoDS import TopoDS
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.gp import gp_Pnt,gp_Dir,gp_Lin
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    original = read_step(a.source_step)[0]
    candidate = read_step(a.candidate_step)[0]
    source_face = TopoDS.Face_s(indexed(original,TopAbs_FACE).FindKey(r['selected_face_private']))
    replacement = TopoDS.Face_s(indexed(read_step(a.replacement_face)[0],TopAbs_FACE).FindKey(1))
    surface = BRep_Tool.Surface_s(source_face)
    u0,u1,v0,v1 = surface.Bounds()
    edges, params = [], []
    w = BRepTools_WireExplorer(BRepTools.OuterWire_s(source_face),source_face)
    while w.More():
        edge = w.Current(); curve = BRepAdaptor_Curve(edge)
        points = [curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(),curve.LastParameter(),121)]
        errors = [max(GeomAPI_ProjectPointOnSurf(point,BRep_Tool.Surface_s(face)).LowerDistance()
                      for point in points) for face in (source_face,replacement)]
        edges.append({'source_edge_tolerance':BRep_Tool.Tolerance_s(edge),
                      'source_max_distance':errors[0],'replacement_max_distance':errors[1]})
        curve2d = BRepAdaptor_Curve2d(edge,source_face)
        uv = [curve2d.Value(float(t)) for t in np.linspace(curve2d.FirstParameter(),curve2d.LastParameter(),121)]
        du = float(np.ptp([point.X() for point in uv])); dv = float(np.ptp([point.Y() for point in uv]))
        params.append({'pcurve_type':str(curve2d.GetType()),
                       'u_span_fraction':du/(u1-u0),'v_span_fraction':dv/(v1-v0),
                       'iso_u_screen':du<1e-9*max(1,abs(u1-u0)),
                       'iso_v_screen':dv<1e-9*max(1,abs(v1-v0))})
        w.Next()
    attribution = json.loads(a.attribution.read_text()); data = np.load(a.probes)
    def measure(shape):
        it = IntCurvesFace_ShapeIntersector(); it.Load(shape,1e-7)
        classifier = BRepClass3d_SolidClassifier(shape); rows = []
        for prior in attribution['records_private']:
            i = prior['probe_index_private']; point,vector = data['points'][i],-data['normals'][i]
            it.Perform(gp_Lin(gp_Pnt(*point),gp_Dir(*vector)),-2.,500.)
            hits = sorted(it.WParameter(k) for k in range(1,it.NbPnt()+1)); intervals = []
            for lo,hi in zip(hits,hits[1:]):
                if hi-lo<=1e-6 or lo>.05 or hi<0: continue
                classifier.Perform(gp_Pnt(*(point+vector*(lo+hi)*.5)),1e-7)
                if classifier.State()==TopAbs_IN: intervals.append((lo,hi))
            row = {'probe_private':i,'status':'unresolved'}
            if len(intervals)==1: row.update(status='resolved',ray_scan_units=intervals[0][1]-intervals[0][0])
            rows.append(row)
        return rows
    baseline_rows,candidate_rows = measure(original),measure(candidate)
    old = {row['probe_private']:row for row in baseline_rows}; counts = Counter(); changes = []
    for row in candidate_rows:
        previous = old[row['probe_private']]
        if row['status']!='resolved' or previous['status']!='resolved':
            counts['not_paired_resolved']+=1; continue
        delta = row['ray_scan_units']-previous['ray_scan_units']
        counts['increased' if delta>1e-5 else 'decreased' if delta< -1e-5 else 'unchanged_within_tolerance']+=1
        if abs(delta)>1e-5: changes.append({'probe_private':row['probe_private'],
                    'baseline':previous['ray_scan_units'],'candidate':row['ray_scan_units'],'delta':delta})
    report = {'schema':'m64-reference-independent-filling-audit/v1','input_sha256':hashes,
              'boundary_sample_count_per_edge':121,
              'source_face_tolerance':BRep_Tool.Tolerance_s(source_face),
              'replacement_face_tolerance':BRep_Tool.Tolerance_s(replacement),
              'edge_comparison':edges,'paired_fixed_ray_summary':dict(counts),
              'baseline_fixed_rays_private':baseline_rows,'candidate_fixed_rays_private':candidate_rows,
              'changes_private':changes,
              'parameter_audit':{'u_degree':surface.UDegree(),'v_degree':surface.VDegree(),
                   'u_poles':surface.NbUPoles(),'v_poles':surface.NbVPoles(),
                   'original_interior_poles':max(0,surface.NbUPoles()-2)*max(0,surface.NbVPoles()-2),
                   'pcurves':params,'all_anchors_isoparametric_screen':all(p['iso_u_screen'] or p['iso_v_screen'] for p in params)},
              'master_modified':False,'repair_accepted':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output_sha256':digest(a.output),'paired_fixed_ray_summary':dict(counts),
                      'source_edge_distance_max':max(x['source_max_distance'] for x in edges),
                      'replacement_edge_distance_max':max(x['replacement_max_distance'] for x in edges),
                      'all_anchors_isoparametric_screen':report['parameter_audit']['all_anchors_isoparametric_screen']}))


if __name__=='__main__': main()
