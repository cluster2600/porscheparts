#!/usr/bin/env python3
"""Staged private trial of a localized Bernstein polynomial on the real F53 face.

No BRepFill, monomial expansion or master overwrite. Each native stage is
independently restartable and must be bounded by the caller's timeout 300.
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


def bernstein_product(a, b):
    import numpy as np
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    n,m=np.array(a.shape)-1; p,q=np.array(b.shape)-1
    out=np.zeros((n+p+1,m+q+1))
    for i in range(n+1):
        for j in range(m+1):
            for k in range(p+1):
                for l in range(q+1):
                    out[i+k,j+l]+=a[i,j]*b[k,l]*(math.comb(n,i)*math.comb(p,k)/math.comb(n+p,i+k))*(math.comb(m,j)*math.comb(q,l)/math.comb(m+q,j+l))
    return out


def bernstein_value(coefficients,u,v):
    import numpy as np
    a=np.array(coefficients,dtype=float,copy=True)
    for size in range(a.shape[0]-1,0,-1): a[:size]=(1-u)*a[:size]+u*a[1:size+1]
    a=a[0].copy()
    for size in range(a.shape[0]-1,0,-1): a[:size]=(1-v)*a[:size]+v*a[1:size+1]
    return a[0]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('surface','topology','solid','audit'))
    for name in ('source-step','trial-report','patches','search-report','attribution','probes','helpers','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--low-degree-report',type=Path)
    a=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
    a.output.mkdir(parents=True,exist_ok=True)
    report_path=a.output/(a.stage+'-report.json')
    if report_path.exists(): raise FileExistsError(report_path)
    prior=json.loads(a.trial_report.read_text()); patches=json.loads(a.patches.read_text())
    search=json.loads(a.search_report.read_text())
    if sha(a.source_step)!=prior['source_sha256']['step'] or search['input_sha256']['source']!=sha(a.source_step):
        raise ValueError('source provenance mismatch')
    for key in ('attribution','probes'):
        if sha(getattr(a,key))!=prior['source_sha256'][key]: raise ValueError(key+' provenance mismatch')
    if sha(a.patches)!=search['input_sha256']['patches'] or not search['localized_search']['sampled_amplitude_and_orientation_pass']:
        raise ValueError('localized field provenance or criteria mismatch')
    report={'schema':'m64-reference-local-bernstein-trial/v1','stage':a.stage,
            'source_sha256':prior['source_sha256'],'selected_face_private':prior['selected_face_private'],
            'probe_private':prior['probe_private'],'search_report_sha256':sha(a.search_report),
            'input_modified':False,'repair_accepted':False,'manufacturing_authorized':False}
    selected_exponents=search['localized_search']['exponents']
    if a.low_degree_report:
        low=json.loads(a.low_degree_report.read_text());selected=low['candidates'][0]
        if low['source_sha256']!=sha(a.source_step) or selected['exponents']!=[4,2,2,5] or not all(
                check['max_displacement']<=1. and check['min_orientation_ratio']>0 for check in selected['grid_checks']):
            raise ValueError('minimal-degree selection provenance or criteria mismatch')
        selected_exponents=selected['exponents'];report['low_degree_selection_sha256']=sha(a.low_degree_report)
    def save(status):
        report['status']=status
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'stage':a.stage,'status':status}),flush=True)
    save('loading')
    import numpy as np
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step,brepcheck,topology,shape_properties
    from repair_topology_f42_1 import indexed,write_step,property_delta
    from OCP.BRep import BRep_Tool,BRep_Builder
    from OCP.BRepTools import BRepTools,BRepTools_WireExplorer,BRepTools_ReShape
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Curve2d,BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_WIRE,TopAbs_SHELL,TopAbs_IN,TopAbs_ON
    from OCP.TopoDS import TopoDS,TopoDS_Face
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.Geom import Geom_BSplineSurface
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.gp import gp_Pnt,gp_Pnt2d,gp_Vec,gp_Dir,gp_Lin
    original=read_step(a.source_step)[0]
    if a.stage=='surface':
        copy=BRepBuilderAPI_Copy(original,True,False).Shape()
        faces=indexed(copy,TopAbs_FACE); face=TopoDS.Face_s(faces.FindKey(prior['selected_face_private']))
        if not face.Location().IsIdentity(): raise ValueError('located source face unsupported')
        source=BRep_Tool.Surface_s(face)
        if (source.UDegree(),source.VDegree(),source.NbUPoles(),source.NbVPoles())!=(1,1,2,2) or source.IsURational() or source.IsVRational():
            raise ValueError('source not a single nonrational bilinear patch')
        u0,u1,v0,v1=source.Bounds(); edges=[]; noniso=[]
        w=BRepTools_WireExplorer(BRepTools.OuterWire_s(face),face)
        while w.More():
            edge=w.Current(); pc=BRepAdaptor_Curve2d(edge,face)
            uv=np.array([[z.X(),z.Y()] for z in [pc.Value(float(t)) for t in np.linspace(pc.FirstParameter(),pc.LastParameter(),121)]])
            if min(np.ptp((uv-[u0,v0])/[u1-u0,v1-v0],axis=0))>1e-9: noniso.append(edge)
            edges.append(edge);w.Next()
        if len(noniso)!=1 or indexed(face,TopAbs_WIRE).Extent()!=1: raise ValueError('unsupported boundary configuration')
        neighbors=[]
        for i in range(1,faces.Extent()+1):
            if i!=prior['selected_face_private'] and indexed(faces.FindKey(i),TopAbs_EDGE).Contains(noniso[0]): neighbors.append(TopoDS.Face_s(faces.FindKey(i)))
        if len(neighbors)!=1: raise ValueError('ambiguous cylinder neighbor')
        adj=BRepAdaptor_Surface(neighbors[0])
        if adj.GetType()!=GeomAbs_Cylinder: raise ValueError('neighbor not cylinder')
        cylinder=adj.Cylinder(); loc=cylinder.Location();axis=cylinder.Axis().Direction()
        center=np.array([loc.X(),loc.Y(),loc.Z()]);axis=np.array([axis.X(),axis.Y(),axis.Z()]);radius=cylinder.Radius()
        poles=np.array([[[source.Pole(i,j).X(),source.Pole(i,j).Y(),source.Pole(i,j).Z()] for j in (1,2)] for i in (1,2)])
        radial=poles-center;radial=(radial-np.sum(radial*axis,axis=-1)[...,None]*axis)/radius
        fcoeff=-np.ones((3,3))
        for k in range(3): fcoeff+=bernstein_product(radial[:,:,k],radial[:,:,k])
        p,q,r,s=selected_exponents
        if min(p,q,r,s)<2 or max(p,q,r,s)>12: raise ValueError('exponents outside audited bounds')
        border=np.zeros((p+q+1,r+s+1));border[p,r]=1/(math.comb(p+q,p)*math.comb(r+s,r))
        amplitude=bernstein_product(border,bernstein_product(fcoeff,fcoeff))
        probe=next(row for patch in patches['patches_private'] for row in patch['probes_private'] if row['index']==prior['probe_private'])
        entry=np.array(probe['entry_xyz_scan_units']);normal=-np.array(probe['direction'])
        if abs(np.linalg.norm(normal)-1)>1e-10: raise ValueError('nonunit displacement direction')
        proj=GeomAPI_ProjectPointOnSurf(gp_Pnt(*entry),source);ut,vt=proj.LowerDistanceParameters();un,vn=(ut-u0)/(u1-u0),(vt-v0)/(v1-v0)
        ftarget=float(bernstein_value(fcoeff,un,vn));factor=un**p*(1-un)**q*vn**r*(1-vn)**s*ftarget**2
        if not math.isfinite(factor) or factor<=1e-20: raise ValueError('singular target normalization')
        amplitude*=.85/factor
        degree_u,degree_v=np.array(amplitude.shape)-1
        native_max=Geom_BSplineSurface.MaxDegree_s()
        if max(degree_u,degree_v)>native_max: raise ValueError('degree exceeds native OCCT support')
        new_poles=np.empty((*amplitude.shape,3))
        for i in range(degree_u+1):
            for j in range(degree_v+1):
                new_poles[i,j]=bernstein_value(poles,i/degree_u,j/degree_v)+amplitude[i,j]*normal
        pp=TColgp_Array2OfPnt(1,degree_u+1,1,degree_v+1)
        for i in range(degree_u+1):
            for j in range(degree_v+1): pp.SetValue(i+1,j+1,gp_Pnt(*new_poles[i,j]))
        uk,vk=TColStd_Array1OfReal(1,2),TColStd_Array1OfReal(1,2)
        um,vm=TColStd_Array1OfInteger(1,2),TColStd_Array1OfInteger(1,2)
        for index,value in enumerate((u0,u1),1):uk.SetValue(index,value);um.SetValue(index,degree_u+1)
        for index,value in enumerate((v0,v1),1):vk.SetValue(index,value);vm.SetValue(index,degree_v+1)
        surface=Geom_BSplineSurface(pp,uk,vk,um,vm,int(degree_u),int(degree_v))
        np.savez_compressed(a.output/'private-bernstein-coefficients.npz',amplitude=amplitude,poles=new_poles,fcoeff=fcoeff,source_poles=poles,uv_bounds=[u0,u1,v0,v1],target_uv=[ut,vt],normal=normal)
        report.update({'exponents':[p,q,r,s],'polynomial_bidegree':[int(degree_u),int(degree_v)],'native_max_degree':native_max,
                       'normalization_C':.85/factor,'amplitude_coeff_abs_max':float(np.max(np.abs(amplitude))),
                       'source_face_tolerance':BRep_Tool.Tolerance_s(face),'uv_domain_preserved':surface.Bounds()==source.Bounds(),
                       'coefficient_construction':'Bernstein_products_only_no_high_degree_monomial_expansion'})
        save('checking_surface_before_topology')
        boundary=[]
        for edge in edges:
            c3=BRepAdaptor_Curve(edge);c2=BRepAdaptor_Curve2d(edge,face)
            distances=[];source_distances=[];derivatives=[]
            for t in np.linspace(c3.FirstParameter(),c3.LastParameter(),121):
                uv=c2.Value(float(t));xyz=c3.Value(float(t));new=surface.Value(uv.X(),uv.Y());old=source.Value(uv.X(),uv.Y())
                distances.append(xyz.Distance(new));source_distances.append(xyz.Distance(old))
                pt0,pt1=gp_Pnt(),gp_Pnt();du0,dv0,du1,dv1=gp_Vec(),gp_Vec(),gp_Vec(),gp_Vec()
                source.D1(uv.X(),uv.Y(),pt0,du0,dv0);surface.D1(uv.X(),uv.Y(),pt1,du1,dv1)
                derivatives.append(max((du1-du0).Magnitude(),(dv1-dv0).Magnitude()))
            boundary.append({'source_edge_tolerance':BRep_Tool.Tolerance_s(edge),'source_same_parameter_distance_max':max(source_distances),
                             'candidate_same_parameter_distance_max':max(distances),'first_derivative_delta_max':max(derivatives)})
        target=entry+.85*normal
        report['boundary_samples_121']=boundary
        report['target_constraint_error']=surface.Value(ut,vt).Distance(gp_Pnt(*target))
        worst_eval=0.;worst_d=0.;min_orientation=float('inf');retained=0
        for u in np.linspace(0,1,81):
            for v in np.linspace(0,1,81):
                U,V=u0+u*(u1-u0),v0+v*(v1-v0)
                if BRepClass_FaceClassifier(face,gp_Pnt2d(U,V),1e-9).State() not in (TopAbs_IN,TopAbs_ON):continue
                retained+=1
                fvalue=float(bernstein_value(fcoeff,u,v));expected_d=.85/factor*u**p*(1-u)**q*v**r*(1-v)**s*fvalue**2
                sourcepoint=source.Value(U,V);expected=np.array([sourcepoint.X(),sourcepoint.Y(),sourcepoint.Z()])+expected_d*normal
                actual=surface.Value(U,V);worst_eval=max(worst_eval,actual.Distance(gp_Pnt(*expected)));worst_d=max(worst_d,actual.Distance(sourcepoint))
                pt0,pt1=gp_Pnt(),gp_Pnt();du0,dv0,du1,dv1=gp_Vec(),gp_Vec(),gp_Vec(),gp_Vec()
                source.D1(U,V,pt0,du0,dv0);surface.D1(U,V,pt1,du1,dv1)
                before=du0.Crossed(dv0);after=du1.Crossed(dv1)
                min_orientation=min(min_orientation,before.Dot(after)/before.SquareMagnitude())
        report['native_surface_sampled_check']={'grid_size':81,'retained_points':retained,'max_factored_vs_native_position_error':worst_eval,
                    'max_displacement':worst_d,'min_orientation_dot_ratio':min_orientation,'sampled_not_global':True}
        if (max(row['candidate_same_parameter_distance_max'] for row in boundary)>1e-5 or report['target_constraint_error']>1e-5
                or worst_eval>1e-7 or worst_d>1. or min_orientation<=0):
            save('rejected_surface_constraints_or_evaluation');return
        builder=BRep_Builder();replacement=TopoDS_Face();builder.MakeFace(replacement,surface,BRep_Tool.Tolerance_s(face))
        replacement.Orientation(face.Orientation())
        for edge in edges:
            c2=BRepAdaptor_Curve2d(edge,face)
            builder.UpdateEdge(edge,c2.Curve(),replacement,BRep_Tool.Tolerance_s(edge))
            builder.Range(edge,replacement,c2.FirstParameter(),c2.LastParameter())
        builder.Add(replacement,BRepTools.OuterWire_s(face))
        report['replacement_face_brepcheck']=brepcheck(replacement)
        if not report['replacement_face_brepcheck']['shape_valid']:save('rejected_invalid_replacement_face');return
        write_step(replacement,a.output/'private-replacement-face.step')
        report['replacement_face_sha256']=sha(a.output/'private-replacement-face.step')
        report['constraints_within_tolerance']=True
        save('surface_passed_requires_solid_checks')
    elif a.stage=='topology':
        previous=json.loads((a.output/'surface-report.json').read_text())
        if (previous['target_constraint_error']>1e-5 or max(row['candidate_same_parameter_distance_max'] for row in previous['boundary_samples_121'])>1e-5
                or previous['native_surface_sampled_check']['max_factored_vs_native_position_error']>1e-7
                or previous['native_surface_sampled_check']['max_displacement']>1.
                or previous['native_surface_sampled_check']['min_orientation_dot_ratio']<=0):
            raise ValueError('surface prerequisite failed')
        report['surface_report_sha256']=sha(a.output/'surface-report.json')
        report['coefficients_sha256']=sha(a.output/'private-bernstein-coefficients.npz')
        data=np.load(a.output/'private-bernstein-coefficients.npz');new_poles=data['poles'];degree_u,degree_v=np.array(new_poles.shape[:2])-1
        pp=TColgp_Array2OfPnt(1,degree_u+1,1,degree_v+1)
        for i in range(degree_u+1):
            for j in range(degree_v+1):pp.SetValue(i+1,j+1,gp_Pnt(*new_poles[i,j]))
        u0,u1,v0,v1=data['uv_bounds'];uk,vk=TColStd_Array1OfReal(1,2),TColStd_Array1OfReal(1,2)
        um,vm=TColStd_Array1OfInteger(1,2),TColStd_Array1OfInteger(1,2)
        for index,value in enumerate((u0,u1),1):uk.SetValue(index,value);um.SetValue(index,degree_u+1)
        for index,value in enumerate((v0,v1),1):vk.SetValue(index,value);vm.SetValue(index,degree_v+1)
        surface=Geom_BSplineSurface(pp,uk,vk,um,vm,int(degree_u),int(degree_v))
        shape=BRepBuilderAPI_Copy(original,True,False).Shape();face=TopoDS.Face_s(indexed(shape,TopAbs_FACE).FindKey(prior['selected_face_private']))
        builder=BRep_Builder();replacement=TopoDS.Face_s(face.EmptyCopied())
        builder.UpdateFace(replacement,surface,face.Location(),BRep_Tool.Tolerance_s(face))
        edges=indexed(face,TopAbs_EDGE)
        for i in range(1,edges.Extent()+1):
            edge=TopoDS.Edge_s(edges.FindKey(i));c2=BRepAdaptor_Curve2d(edge,face)
            first,last=c2.FirstParameter(),c2.LastParameter();curve=c2.Curve()
            builder.UpdateEdge(edge,curve,replacement,BRep_Tool.Tolerance_s(edge));builder.Range(edge,replacement,first,last)
        builder.Add(replacement,BRepTools.OuterWire_s(face))
        from OCP.BRepCheck import BRepCheck_Analyzer,BRepCheck_Face
        checker=BRepCheck_Analyzer(replacement,True,False,True)
        details=[]
        for i in range(1,edges.Extent()+1):
            item=TopoDS.Edge_s(edges.FindKey(i));result=checker.Result(item);result.InitContextIterator()
            contexts=[]
            while result.MoreShapeInContext():
                contexts.append([str(status) for status in result.StatusOnShape(result.ContextualShape())]);result.NextShapeInContext()
            details.append({'edge_order':i,'statuses':[str(status) for status in result.Status()],'context_statuses':contexts})
        fc=BRepCheck_Face(replacement)
        report['detailed_edge_context_statuses']=details
        report['face_checks']={'intersect_wires':str(fc.IntersectWires()),'classify_wires':str(fc.ClassifyWires()),'orientation_wires':str(fc.OrientationOfWires())}
        report['replacement_face_brepcheck']=brepcheck(replacement)
        write_step(replacement,a.output/'private-replacement-face.step')
        report['replacement_face_sha256']=sha(a.output/'private-replacement-face.step')
        if not report['replacement_face_brepcheck']['shape_valid']:save('rejected_invalid_replacement_face');return
        save('surface_passed_requires_solid_checks')
    elif a.stage=='solid':
        stage_path=a.output/('topology-report.json' if (a.output/'topology-report.json').exists() else 'surface-report.json')
        stage=json.loads(stage_path.read_text())
        if stage['status']!='surface_passed_requires_solid_checks' or sha(a.output/'private-replacement-face.step')!=stage['replacement_face_sha256']:
            raise ValueError('surface stage not accepted or hash mismatch')
        shape=BRepBuilderAPI_Copy(original,True,False).Shape();face=TopoDS.Face_s(indexed(shape,TopAbs_FACE).FindKey(prior['selected_face_private']))
        replacement=TopoDS.Face_s(indexed(read_step(a.output/'private-replacement-face.step')[0],TopAbs_FACE).FindKey(1))
        replacement.Orientation(face.Orientation())
        old_edges=indexed(face,TopAbs_EDGE);new_edges=indexed(replacement,TopAbs_EDGE)
        old_tols=sorted(BRep_Tool.Tolerance_s(TopoDS.Edge_s(old_edges.FindKey(i))) for i in range(1,old_edges.Extent()+1))
        new_tols=sorted(BRep_Tool.Tolerance_s(TopoDS.Edge_s(new_edges.FindKey(i))) for i in range(1,new_edges.Extent()+1))
        relaxed=len(old_tols)!=len(new_tols) or any(new>old for new,old in zip(new_tols,old_tols)) or BRep_Tool.Tolerance_s(replacement)>BRep_Tool.Tolerance_s(face)
        report['face_roundtrip_tolerance_check']={'source_edges':old_tols,'replacement_edges':new_tols,
                    'source_face':BRep_Tool.Tolerance_s(face),'replacement_face':BRep_Tool.Tolerance_s(replacement),'relaxed':relaxed}
        report['face_roundtrip_brepcheck']=brepcheck(replacement)
        if relaxed or not report['face_roundtrip_brepcheck']['shape_valid']:save('rejected_face_roundtrip_or_tolerance_relaxation');return
        replacer=BRepTools_ReShape();replacer.Replace(face,replacement);replaced=replacer.Apply(shape)
        save('sewing_single_face')
        sewer=BRepBuilderAPI_Sewing(1e-5);sewer.Add(replaced);sewer.Perform();sewed=sewer.SewedShape();shells=indexed(sewed,TopAbs_SHELL)
        report['sewing']={'shell_count':shells.Extent(),'free_edges':sewer.NbFreeEdges(),'multiple_edges':sewer.NbMultipleEdges()}
        if shells.Extent()!=1 or sewer.NbFreeEdges() or sewer.NbMultipleEdges():save('rejected_sewing');return
        candidate=BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shells.FindKey(1))).Solid()
        report['brepcheck']=brepcheck(candidate);report['topology']=topology(candidate)
        report['property_delta']=property_delta(shape_properties(original),shape_properties(candidate))
        if not report['brepcheck']['shape_valid']:save('rejected_invalid_solid');return
        write_step(candidate,a.output/'diagnostic-candidate.step')
        report['candidate_sha256']=sha(a.output/'diagnostic-candidate.step')
        roundtrip=read_step(a.output/'diagnostic-candidate.step')[0]
        report['roundtrip_brepcheck']=brepcheck(roundtrip)
        report['roundtrip_property_delta']=property_delta(shape_properties(candidate),shape_properties(roundtrip))
        if not report['roundtrip_brepcheck']['shape_valid']:save('rejected_invalid_roundtrip');return
        save('solid_passed_requires_independent_audit')
    else:
        stage=json.loads((a.output/'solid-report.json').read_text())
        if stage['status']!='solid_passed_requires_independent_audit' or sha(a.output/'diagnostic-candidate.step')!=stage['candidate_sha256']:
            raise ValueError('solid stage not accepted or hash mismatch')
        candidate=read_step(a.output/'diagnostic-candidate.step')[0]
        from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
        from trial_transition_filling import compare_fixed_rays
        data=np.load(a.probes);attribution=json.loads(a.attribution.read_text())
        def rays(shape):
            it=IntCurvesFace_ShapeIntersector();it.Load(shape,1e-7);classifier=BRepClass3d_SolidClassifier(shape);rows=[]
            for old in attribution['records_private']:
                i=old['probe_index_private'];point,vector=data['points'][i],-data['normals'][i]
                it.Perform(gp_Lin(gp_Pnt(*point),gp_Dir(*vector)),-2.,500.);hits=sorted(it.WParameter(k) for k in range(1,it.NbPnt()+1));intervals=[]
                for lo,hi in zip(hits,hits[1:]):
                    if hi-lo<=1e-6 or lo>.05 or hi<0:continue
                    classifier.Perform(gp_Pnt(*(point+vector*(lo+hi)*.5)),1e-7)
                    if classifier.State()==TopAbs_IN:intervals.append((lo,hi))
                row={'probe_private':i,'status':'unresolved'}
                if len(intervals)==1:row.update(status='resolved',ray_scan_units=intervals[0][1]-intervals[0][0])
                rows.append(row)
            return rows
        save('checking_fixed_rays')
        baseline,changed=rays(original),rays(candidate)
        report['baseline_fixed_rays_private']=baseline;report['candidate_fixed_rays_private']=changed
        report['paired_fixed_ray_summary']=compare_fixed_rays(baseline,changed)
        old={row['probe_private']:row for row in baseline}
        report['target_ray_private']={'source':old[prior['probe_private']],
             'candidate':next(row for row in changed if row['probe_private']==prior['probe_private'])}
        save('checking_self_intersections')
        analyzer=BOPAlgo_ArgumentAnalyzer();analyzer.SetShape1(candidate);analyzer.SelfInterMode=True;analyzer.StopOnFirstFaulty=True;analyzer.Perform()
        report['self_intersection_check']={'has_faulty':analyzer.HasFaulty(),'status_counts':dict(Counter(str(row.GetCheckStatus()) for row in analyzer.GetCheckResult()))}
        report['candidate_sha256']=sha(a.output/'diagnostic-candidate.step')
        report['master_hash_unchanged']=sha(a.source_step)==prior['source_sha256']['step']
        if analyzer.HasFaulty() or report['paired_fixed_ray_summary'].get('decreased',0):save('rejected_intersections_or_decreased_ray')
        else:save('local_candidate_passed_sampled_checks_not_manufacturing_release')


if __name__=='__main__': main()
