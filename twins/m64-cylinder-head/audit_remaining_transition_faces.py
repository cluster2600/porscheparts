#!/usr/bin/env python3
"""Read-only feasibility audit of the four remaining known weak rays."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','patches','attribution','completed-audit','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    patches=json.loads(a.patches.read_text());attribution=json.loads(a.attribution.read_text());completed=json.loads(a.completed_audit.read_text())
    if sha(a.source_step)!=patches['source_sha256']['step'] or sha(a.attribution)!=patches['source_sha256']['attribution'] or completed['source_sha256']!=patches['source_sha256']:
        raise ValueError('provenance mismatch')
    import numpy as np
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
    from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve2d
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_WIRE
    from OCP.TopoDS import TopoDS
    from OCP.GeomAbs import GeomAbs_Cylinder,GeomAbs_Plane
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.gp import gp_Pnt
    shape=read_step(a.source_step)[0];faces=indexed(shape,TopAbs_FACE);global_edges=indexed(shape,TopAbs_EDGE);adjacency={}
    for i in range(1,faces.Extent()+1):
        edges=indexed(faces.FindKey(i),TopAbs_EDGE)
        for j in range(1,edges.Extent()+1):adjacency.setdefault(global_edges.FindIndex(edges.FindKey(j)),[]).append(i)
    records={row['probe_index_private']:row for row in attribution['records_private']}
    rays={row['probe_private']:row for row in completed['candidate_fixed_rays_private']};rows=[]
    for patch in patches['patches_private']:
        for probe in patch['probes_private']:
            if probe['index']==completed['probe_private']:continue
            prior=records[probe['index']];face_id=prior['entry_face_private'];face=TopoDS.Face_s(faces.FindKey(face_id));s=BRep_Tool.Surface_s(face);adaptor=BRepAdaptor_Surface(face)
            row={'probe_private':probe['index'],'entry_face_private':face_id,'exit_face_private':prior['exit_face_private'],
                 'remaining_ray':rays[probe['index']],'surface_type':str(adaptor.GetType()),'native_surface_class':s.DynamicType().Name(),
                 'wire_count':indexed(face,TopAbs_WIRE).Extent(),'boundary_private':[]}
            if s.DynamicType().Name()!='Geom_BSplineSurface':rows.append(row);continue
            row.update(degrees=[s.UDegree(),s.VDegree()],pole_counts=[s.NbUPoles(),s.NbVPoles()],rational=s.IsURational() or s.IsVRational())
            u0,u1,v0,v1=s.Bounds();project=GeomAPI_ProjectPointOnSurf(gp_Pnt(*probe['entry_xyz_scan_units']),s);ut,vt=project.LowerDistanceParameters()
            target=s.Value(ut,vt);row['target_projection_error']=project.LowerDistance();row['target_uv_normalized_private']=[(ut-u0)/(u1-u0),(vt-v0)/(v1-v0)]
            w=BRepTools_WireExplorer(BRepTools.OuterWire_s(face),face)
            while w.More():
                edge=w.Current();pc=BRepAdaptor_Curve2d(edge,face)
                uv=[pc.Value(float(t)) for t in np.linspace(pc.FirstParameter(),pc.LastParameter(),121)]
                arr=np.array([[point.X(),point.Y()] for point in uv]);span=np.ptp((arr-[u0,v0])/[u1-u0,v1-v0],axis=0)
                boundary={'iso_u':bool(span[0]<=1e-9),'iso_v':bool(span[1]<=1e-9),'pcurve_type':str(pc.GetType())}
                if min(span)>1e-9:
                    ids=[i for i in adjacency[global_edges.FindIndex(edge)] if i!=face_id]
                    boundary['neighbor_faces_private']=ids
                    if len(ids)==1:
                        neighbor=BRepAdaptor_Surface(TopoDS.Face_s(faces.FindKey(ids[0])));boundary['neighbor_type']=str(neighbor.GetType())
                        if neighbor.GetType()==GeomAbs_Cylinder:
                            cyl=neighbor.Cylinder();loc=cyl.Location();axis=cyl.Axis().Direction();center=np.array([loc.X(),loc.Y(),loc.Z()]);n=np.array([axis.X(),axis.Y(),axis.Z()])
                            def implicit(point):
                                z=np.array([point.X(),point.Y(),point.Z()])-center;z-=n*np.dot(z,n);return float(np.dot(z,z)/cyl.Radius()**2-1)
                            boundary['implicit_definition']='cylinder_squared_radial_distance_over_radius_squared_minus_one'
                        elif neighbor.GetType()==GeomAbs_Plane:
                            plane=neighbor.Plane();aa,bb,cc,dd=plane.Coefficients()
                            def implicit(point):return aa*point.X()+bb*point.Y()+cc*point.Z()+dd
                            boundary['implicit_definition']='plane_signed_distance_scan_units'
                        else:implicit=None
                        if implicit:
                            boundary['max_abs_implicit_on_121_boundary_points']=max(abs(implicit(s.Value(point.X(),point.Y()))) for point in uv)
                            boundary['implicit_at_target']=implicit(target)
                row['boundary_private'].append(boundary);w.Next()
            rows.append(row)
    result={'schema':'m64-reference-remaining-transition-readonly-feasibility/v1','source_sha256':sha(a.source_step),
            'completed_candidate_sha256':completed['candidate_sha256'],'completed_audit_sha256':sha(a.completed_audit),
            'remaining_probe_count':len(rows),'unique_entry_face_count':len({row['entry_face_private'] for row in rows}),
            'probes_private':rows,'new_geometry_constructed':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report_sha256':sha(a.output),'remaining_probe_count':len(rows),'probes_private':rows},indent=2))


if __name__=='__main__':main()
