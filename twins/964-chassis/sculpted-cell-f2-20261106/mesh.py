#!/usr/bin/env python3
"""Exact canonical OCC fragments to conforming quadratic S6 midsurfaces.

Run in the retained offline Gmsh/OCC image. This exports private raw fields and
junction witnesses, never donor compatibility or manufacturing qualification.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import traceback

import gmsh
import numpy as np
import bezier
import geometry
import solve

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def transverse_resolution(control,interval,h):
    """Sample exact Bezier profiles; propagate narrow-strip resolution inside."""
    strip=control['poles_mm'][:,3*interval:3*interval+4]
    nu=len(control['u_knots'])-1
    s=np.linspace(0.,1.,33)
    B=np.stack([(1-s)**3,3*s*(1-s)**2,3*s*s*(1-s),s**3],axis=1)
    dB=np.stack([-3*(1-s)**2,3*(1-s)**2-6*s*(1-s),6*s*(1-s)-3*s*s,3*s*s],axis=1)
    widths=[];turns=[]
    for u in np.linspace(0.,float(nu),4*nu+1):
        i=min(int(u),nu-1);t=u-i
        Bu=np.array([(1-t)**3,3*t*(1-t)**2,3*t*t*(1-t),t**3])
        Q=np.einsum('i,ijc->jc',Bu,strip[3*i:3*i+4])
        profile=B@Q;tangents=dB@Q
        norms=np.linalg.norm(tangents,axis=1)
        solve.require(float(norms.min())>1e-10,'Canonical transverse profile has a degenerate tangent')
        tangents/=norms[:,None]
        widths.append(float(np.linalg.norm(np.diff(profile,axis=0),axis=1).sum()))
        turns.append(float(np.arccos(np.clip(np.sum(tangents[:-1]*tangents[1:],axis=1),-1,1)).sum()))
    required=max(2,int(np.ceil(max(turns)/(np.deg2rad(22.5)*h/120))))
    return {'sampled_minimum_transverse_arc_width_mm':min(widths),
            'sampled_maximum_transverse_tangent_turn_rad':max(turns),
            'minimum_transverse_intervals':required,'surface_target_mm':min(h,min(widths)/required),
            'U_samples':4*nu+1,'V_samples':33}


def canonical_surfaces(component,point,h):
    if component.get('type')=='planar_profile_cap':
        control=bezier.profile_bspline(component['profile_mm'])
        poles=np.asarray(control['poles_mm'])
        ids=[point(p) for p in poles]
        curve=gmsh.model.occ.addBSpline(ids,degree=3,knots=list(map(float,control['knots'])),multiplicities=list(map(int,control['multiplicities'])))
        wire=gmsh.model.occ.addCurveLoop([curve])
        return [(gmsh.model.occ.addPlaneSurface([wire]),None)]
    control=bezier.component_bspline(component);poles=control['poles_mm']
    # Keep identical analytic geometry, but expose canonical profile-turn knot
    # lines as real CAD edges. Boundary-only sizing let S6 elements span several
    # unresolved profile intervals in the preserved rejected control.
    faces=[]
    for interval in range(len(control['v_knots'])-1):
        strip=poles[:,3*interval:3*interval+4]
        ids=[point(strip[u,v]) for v in range(4) for u in range(strip.shape[0])]
        face=gmsh.model.occ.addBSplineSurface(ids,strip.shape[0],degreeU=3,degreeV=3,
            knotsU=control['u_knots'].tolist(),knotsV=control['v_knots'][interval:interval+2].tolist(),
            multiplicitiesU=control['u_multiplicities'],multiplicitiesV=[4,4])
        faces.append((face,transverse_resolution(control,interval,h)))
    return faces


def corner_normal(nodes,ids):
    points=[nodes[n] for n in ids]
    # Quadratic triangle derivatives at its reference centroid.
    dr=[-1/3,1/3,0.,0.,4/3,-4/3]
    ds=[-1/3,0.,1/3,-4/3,4/3,0.]
    a=[sum(w*p[k] for w,p in zip(dr,points)) for k in range(3)]
    b=[sum(w*p[k] for w,p in zip(ds,points)) for k in range(3)]
    return np.cross(a,b)


def make_mesh(model,model_path,output,h,fixtures,max_elements=100000):
    solve.require(h>0 and model['units']=='mm' and model['status']=='assumed','Invalid mesh scope/size')
    source_files=[model_path,Path(__file__),HERE/'bezier.py',HERE/'geometry.py']
    source_hashes={str(p):sha(p) for p in source_files}
    write(output/'preflight.json',{'classification':'predeclared_exact_surface_fragment_and_S6_mesh',
          'source_hashes':source_hashes,'h_mm':h,'gmsh_version':gmsh.__version__,
          'surface_representation':'Exact composite bicubic BSpline, no surface fitting',
          'surface_partition':'Full-U exact strips bounded by every canonical integer-V knot line',
          'interior_transverse_policy':'Per-strip intrinsic arc width divided by max(2,source profile turn/22.5deg scaled by h); no geometry/response tuning',
          'curve_resolution_policy':'At least2intervals,ceil(length/h),ceil(total_tangent_turn/(22.5deg*h/120)); curvature-size field off',
          'maximum_linear_triangles_before_order_elevation':max_elements,
          'normal_convention':'Canonical tangent-U cross tangent-V or explicit cap normal',
          'physical_validation':False})
    gmsh.initialize();gmsh.logger.start();gmsh.model.add('assumed-sculpted-F2')
    try:
        for name,value in [('General.NumThreads',1),('Geometry.Tolerance',1e-8),
                           ('Mesh.Algorithm',6),('Mesh.RecombineAll',0),
                           ('Mesh.MeshSizeMin',min(5.,h/8)),('Mesh.MeshSizeMax',h),
                           ('Mesh.MeshSizeFromCurvature',0),('Mesh.MeshSizeFromPoints',0),('Mesh.SecondOrderLinear',0)]:
            gmsh.option.setNumber(name,value)
        components=model['components'];by_name={c['name']:c for c in components}
        solve.require(len(by_name)==len(components),'Repeated canonical component names')
        points={}
        def point(p):
            key=tuple(float(x) for x in np.round(p,11))
            if key not in points:points[key]=gmsh.model.occ.addPoint(*map(float,p))
            return points[key]
        originals=[];original_owners=[];original_resolution=[]
        for component in components:
            parts=canonical_surfaces(component,point,h)
            originals.extend((2,tag) for tag,resolution in parts)
            original_owners.extend(component['name'] for tag,resolution in parts)
            original_resolution.extend(resolution for tag,resolution in parts)
        gmsh.model.occ.synchronize()
        gmsh.write(str(output/'unfragmented.brep'))
        if len(originals)>1:
            fragments,mapping=gmsh.model.occ.fragment(originals[:1],originals[1:],removeObject=True,removeTool=True)
        else:
            fragments,mapping=originals,[[originals[0]]]
        gmsh.model.occ.synchronize()
        owners=defaultdict(set);face_resolution=defaultdict(list)
        for owner,resolution,children in zip(original_owners,original_resolution,mapping):
            for dim,tag in children:
                if dim==2:
                    owners[int(tag)].add(owner)
                    if resolution is not None:face_resolution[int(tag)].append(resolution)
        faces={tag for dim,tag in fragments if dim==2}
        solve.require(faces and faces==set(owners),'Fragment ancestry is incomplete')
        solve.require(all(len(names)==1 for names in owners.values()),'Coincident area has multiple canonical owners; duplicated skins are not admitted')
        solve.require(faces=={tag for dim,tag in gmsh.model.getEntities(2)},'Unaccounted OCC surface entities')
        face_owner={tag:next(iter(names)) for tag,names in owners.items()}
        component_faces={c['name']:[tag for tag in faces if face_owner[tag]==c['name']] for c in components}
        face_curves={face:{abs(tag) for dim,tag in gmsh.model.getBoundary([(2,face)],combined=False,oriented=True) if dim==1} for face in faces}
        component_curves={name:{tag for face in tags for tag in face_curves[face]}
                          for name,tags in component_faces.items()}
        cad_joins=[]
        for join in model.get('join_contract',[]):
            solve.require('component_a' in join,'F2 CAD join contract needs component names')
            a,b=join['component_a'],join['component_b']
            solve.require(a in component_curves and b in component_curves,'Unknown intended component join')
            shared=component_curves[a]&component_curves[b]
            lengths={tag:float(gmsh.model.occ.getMass(1,tag)) for tag in shared}
            positive={tag:length for tag,length in lengths.items() if length>1e-7}
            cad_joins.append({'id':join['id'],'component_a':a,'component_b':b,
                              'shared_curve_tags':sorted(positive),'shared_curve_length_mm':sum(positive.values()),
                              'positive_length_shared_curve':bool(positive)})
        gmsh.write(str(output/'fragmented.brep'))
        write(output/'fragment-witness.json',{'geometry_sha256':sha(model_path),'faces':len(faces),
              'component_faces':component_faces,'CAD_joins':cad_joins,
              'all_required_CAD_joins_have_positive_curve':all(j['positive_length_shared_curve'] for j in cad_joins),
              'admitted_for_hypothesis_study':False,'scope':'Native face/curve witnesses only; source visual/closed-solid and FE checks remain separate'})
        solve.require(all(j['positive_length_shared_curve'] for j in cad_joins),'Intended canonical join has no finite shared OCC curve')
        for group,(name,tags) in enumerate(component_faces.items(),1):
            solve.require(tags,'Canonical component disappeared in fragmentation')
            gmsh.model.addPhysicalGroup(2,tags,group);gmsh.model.setPhysicalName(2,group,name)
        face_targets={face:min(value['surface_target_mm'] for value in values)
                      for face,values in face_resolution.items()}
        curve_targets={curve:min([h]+[face_targets.get(face,h) for face in faces if curve in face_curves[face]])
                       for curve in set.union(*component_curves.values())}
        callback_counts={}
        def size_callback(dim,tag,x,y,z,lc):
            target=face_targets.get(tag,h) if dim==2 else curve_targets.get(tag,h) if dim==1 else h
            returned=min(float(lc) if lc>0 else h,target)
            key=(int(dim),int(tag))
            if key not in callback_counts:callback_counts[key]={'dim':int(dim),'tag':int(tag),'calls':0,'minimum_returned_mm':returned,'maximum_returned_mm':returned}
            row=callback_counts[key];row['calls']+=1
            row['minimum_returned_mm']=min(row['minimum_returned_mm'],returned)
            row['maximum_returned_mm']=max(row['maximum_returned_mm'],returned)
            return returned
        gmsh.model.mesh.setSizeCallback(size_callback)
        curve_resolution=[]
        angle_limit=np.deg2rad(22.5)*h/120
        for curve in sorted(set.union(*component_curves.values())):
            lo,hi=gmsh.model.getParametrizationBounds(1,curve)
            parameters=np.linspace(float(lo[0]),float(hi[0]),129)
            tangents=np.asarray(gmsh.model.getDerivative(1,curve,parameters.tolist())).reshape(-1,3)
            lengths=np.linalg.norm(tangents,axis=1)
            solve.require(float(lengths.min())>1e-10,'Canonical boundary curve has a degenerate tangent')
            tangents/=lengths[:,None]
            total_turn=float(np.arccos(np.clip(np.sum(tangents[:-1]*tangents[1:],axis=1),-1,1)).sum())
            length=float(gmsh.model.occ.getMass(1,curve))
            intervals=max(2,int(np.ceil(length/curve_targets[curve])),int(np.ceil(total_turn/angle_limit)))
            gmsh.model.mesh.setTransfiniteCurve(curve,intervals+1)
            curve_resolution.append({'curve':curve,'length_mm':length,'sampled_total_tangent_turn_rad':total_turn,
                                     'sampling_points':129,'intervals':intervals,'angle_limit_rad':float(angle_limit),
                                     'incident_surface_target_mm':curve_targets[curve]})
        write(output/'curve-resolution.json',curve_resolution)
        surface_resolution=[]
        for face,values in face_resolution.items():
            target=min(value['surface_target_mm'] for value in values)
            surface_resolution.append({'face':face,'component':face_owner[face],
                                       'target_mm':target,'source_resolution':values})
        write(output/'surface-resolution.json',surface_resolution)
        gmsh.model.mesh.generate(2)
        write(output/'size-callback-witness.json',list(callback_counts.values()))
        linear_count=sum(len(tags) for kind,tags in zip(*gmsh.model.mesh.getElements(2)[:2]))
        write(output/'linear-mesh-resource-check.json',{'linear_triangles':linear_count,'limit':max_elements,
              'admitted_for_order_elevation':linear_count<=max_elements,'physical_validation':False})
        solve.require(linear_count<=max_elements,'Linear mesh exceeds the predeclared resource ceiling')
        gmsh.model.mesh.setOrder(2)
        gmsh.write(str(output/'source.msh'))
        node_tags,coordinates,_=gmsh.model.mesh.getNodes()
        all_nodes={int(n):list(map(float,p)) for n,p in zip(node_tags,np.asarray(coordinates).reshape(-1,3))}
        nodes,elements,component_uv={},{},{}
        max_position_error=0.;flipped=0
        for face in sorted(faces):
            name=face_owner[face];component=by_name[name]
            kinds,tags,connectivity=gmsh.model.mesh.getElements(2,face)
            for kind,ids,conn in zip(kinds,tags,connectivity):
                solve.require(int(kind)==9,'Only complete quadratic Gmsh triangle6 elements admitted')
                conn=np.asarray(conn,dtype=int).reshape(-1,6)
                used=sorted({int(n) for row in conn for n in row})
                for n in used:nodes[n]=all_nodes[n]
                if component['type']!='planar_profile_cap':
                    uv=np.asarray(gmsh.model.getParametrization(2,face,[v for n in used for v in nodes[n]])).reshape(-1,2)
                    native=np.asarray(gmsh.model.getValue(2,face,uv.ravel().tolist())).reshape(-1,3)
                    for n,(u,v),native_point in zip(used,uv,native):
                        exact=np.asarray(geometry.evaluate(component,float(u),float(v)))
                        max_position_error=max(max_position_error,float(np.linalg.norm(native_point-exact)),float(np.linalg.norm(native_point-nodes[n])))
                        component_uv[(name,n)]=[float(u),float(v)]
                for eid,row in zip(ids,conn):
                    row=list(map(int,row));centroid=np.mean([nodes[n] for n in row[:3]],axis=0)
                    if component['type']=='planar_profile_cap':
                        hint=np.asarray(component['normal_direction'],float);fiber=None
                    else:
                        u,v=map(float,gmsh.model.getParametrization(2,face,centroid.tolist()))
                        hint=geometry.normal(component,u,v)
                        fiber=geometry.tangent(component,u,v,0) if component.get('fibre_reference_method')=='canonical_longitudinal_tangent' else None
                    if np.dot(corner_normal(nodes,row),hint)<0:
                        row=[row[i] for i in [0,2,1,5,4,3]];flipped+=1
                    element={'id':int(eid),'type':'S6','nodes':row,'component':name,
                             'component_group':component['component'],'surface_id':'face_'+str(face),
                             'thickness_mm':float(component['thickness_mm']),'normal_hint':np.asarray(hint).tolist()}
                    if fiber is not None:element['fiber_reference']=np.asarray(fiber).tolist()
                    solve.require(element['id'] not in elements,'Duplicate original element identifier')
                    elements[element['id']]=element
        solve.require(max_position_error<1e-5,'Native trimmed surface or mesh nodes disagree with canonical parameterized surface')
        edge_distributions=[]
        for face in sorted(faces):
            selected=[e for e in elements.values() if e['surface_id']=='face_'+str(face)]
            edge_ids={tuple(sorted(edge[:2])) for e in selected for edge in solve.edges(e)}
            lengths=[float(np.linalg.norm(np.asarray(nodes[i])-nodes[j])) for i,j in edge_ids]
            edge_distributions.append({'face':face,'component':face_owner[face],
                 'requested_target_mm':face_targets.get(face,h),'unique_corner_edges':len(lengths),
                 'median_edge_mm':float(np.median(lengths)),'p95_edge_mm':float(np.quantile(lengths,.95)),
                 'maximum_edge_mm':max(lengths),'median_over_target':float(np.median(lengths))/face_targets.get(face,h)})
        write(output/'actual-edge-distributions.json',edge_distributions)
        component_edge_faces=defaultdict(lambda:defaultdict(list))
        for e in elements.values():
            for edge in solve.edges(e):component_edge_faces[e['component']][solve.edge_key(edge)].append(edge)
        def ends(name,end):
            component=by_name[name];solve.require(component['type']!='planar_profile_cap','Fixture end requires a canonical loft')
            target=0. if end=='start' else float(len(component['sections_mm'])-1)
            selected=[]
            for key,incident in component_edge_faces[name].items():
                edge=incident[0]
                if len(incident)==1 and all(abs(component_uv[(name,n)][0]-target)<1e-5 for n in edge):selected.append(list(edge))
            solve.require(selected,'Named canonical fixture end has no complete mesh edges: '+name+' '+end)
            return selected
        seam_checks=[]
        for name,component in by_name.items():
            if component['type']=='planar_profile_cap' or not component['closed_profile']:continue
            last=float(len(component['sections_mm'])-1);bad=[]
            for key,incident in component_edge_faces[name].items():
                if len(incident)==1:
                    uv=[component_uv[(name,n)][0] for n in incident[0]]
                    if not (all(abs(u)<1e-5 for u in uv) or all(abs(u-last)<1e-5 for u in uv)):bad.append(list(key))
            seam_checks.append({'component':name,'unintended_open_edges':len(bad),'first_original_edge_ids':bad[:5]})
        write(output/'closed-profile-seams.json',seam_checks)
        solve.require(all(x['unintended_open_edges']==0 for x in seam_checks),'Closed-profile seam remains open after native fragmentation/meshing')
        clamp_edges=[edge for selector in fixtures['clamp_component_ends'] for edge in ends(selector['component'],selector['end'])]
        edge_sets={name:[edge for selector in selectors for edge in ends(selector['component'],selector['end'])]
                   for name,selectors in fixtures['torsion_component_ends'].items()}
        floor_names=set(fixtures['bending_components'])
        solve.require(floor_names<=set(by_name),'Unknown bending floor component')
        raw={'study_id':model['study_id'],'units':'mm','status':'assumed','geometry_sha256':sha(model_path),
             'generator_sha256':sha(__file__),'bezier_source_sha256':sha(HERE/'bezier.py'),
             'nominal_h_mm':h,'nodes':nodes,'elements':list(elements.values()),
             'node_sets':{'CLAMP':sorted({n for edge in clamp_edges for n in edge})},
             'edge_sets':edge_sets,'element_sets':{'BENDING_FLOOR':[e['id'] for e in elements.values() if e['component'] in floor_names]},
             'upper_structure_components':model.get('upper_structure_components',[]),
             'join_contract':model.get('join_contract',[]),'fixture_contract':fixtures,
             'normal_orientation_reversed_to_canonical':flipped,
             'native_to_canonical_max_position_error_mm':max_position_error,
             'mechanical_faces_excluded':0,'unused_native_nonstructural_nodes_excluded':len(all_nodes)-len(nodes),
             'physical_validation':False,'manufacturing_authorized':False}
        write(output/'mesh.json',raw)
        solve.require(all(sha(p)==value for p,value in source_hashes.items()),'Mesher input changed during execution')
        logs=gmsh.logger.get();(output/'gmsh.log').write_text('\n'.join(logs)+'\n')
        report={'classification':'native_exact_fragment_to_S6_mesh_execution_not_engineering_admission',
                'geometry_sha256':sha(model_path),'mesh_sha256':sha(output/'mesh.json'),'source_hashes':source_hashes,
                'nodes':len(nodes),'elements':len(elements),'CAD_joins':cad_joins,'closed_profile_seams':seam_checks,
                'canonical_node_position_max_error_mm':max_position_error,
                'linear_triangles':linear_count,'curve_resolution_policy':'Arc length and sampled total tangent turn, not curvature sizing',
                'warnings':[line for line in logs if 'Warning' in line or 'Error' in line],
                'geometry_or_FE_admission':False,'physical_validation':False}
        write(output/'report.json',report);return report
    finally:
        if gmsh.isInitialized():
            try:(output/'gmsh.log').write_text('\n'.join(gmsh.logger.get())+'\n')
            finally:gmsh.finalize()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--fixtures',type=Path);p.add_argument('--h',type=float,default=120)
    p.add_argument('--max-elements',type=int,default=100000)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    solve.require(not args.output.exists(),'Use a fresh private output path');args.output.mkdir(parents=True)
    model=json.loads(args.model.read_text());fixtures=json.loads(args.fixtures.read_text()) if args.fixtures else model['fixture_contract']
    try:print(json.dumps(make_mesh(model,args.model,args.output,args.h,fixtures,args.max_elements)))
    except Exception as error:
        write(args.output/'failure.json',{'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),
              'source_sha256':sha(__file__),'model_sha256':sha(args.model),'physical_validation':False});raise


if __name__=='__main__':main()
