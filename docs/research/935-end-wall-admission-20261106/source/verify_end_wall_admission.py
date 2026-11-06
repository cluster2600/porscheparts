"""Independently replay scoped end-wall ancestry, exact projection and signed screen."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def simple(points):
    def determinant(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def between(a,b,p):return determinant(a,b,p)==0 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
    n=len(points)
    if len(set(points))!=n:return False
    for i in range(n):
        a,b,c=points[i-1],points[i],points[(i+1)%n]
        if determinant(a,b,c)==0 and not between(a,c,b):return False
    for i in range(n):
        a,b=points[i],points[(i+1)%n]
        for j in range(i+1,n):
            if j==i+1 or i==0 and j==n-1:continue
            c,d=points[j],points[(j+1)%n]
            signs=[determinant(a,b,c),determinant(a,b,d),determinant(c,d,a),determinant(c,d,b)]
            if signs[0]*signs[1]<0 and signs[2]*signs[3]<0:return False
            if any((between(a,b,c),between(a,b,d),between(c,d,a),between(c,d,b))):return False
    return True


def inspect(points,positions,normals,owners,limits):
    reasons=[];local=points-np.mean(points,axis=0);_,values,basis=np.linalg.svd(local,full_matrices=False)
    rank=np.count_nonzero(values>values.max()*max(points.shape)*np.finfo(float).eps)
    normal=basis[-1].copy();residual=max(abs(local@normal));span=np.linalg.norm(points.max(axis=0)-points.min(axis=0))
    if not limits['min_edges']<=len(points)<=limits['max_edges']:reasons.append('edge_count')
    if rank<2:reasons.append('rank_below_two')
    if span>limits['max_diagonal_nominal_mm']:reasons.append('diagonal')
    if residual>limits['max_plane_residual_nominal_mm']:reasons.append('planarity')
    if len(set(map(tuple,points)))!=len(points):reasons.append('repeated_source_coordinate')
    if not reasons:
        coordinates=[tuple(Fraction(float(x)) for x in p) for p in points]
        area=[sum(u[(axis+1)%3]*v[(axis+2)%3]-u[(axis+2)%3]*v[(axis+1)%3] for u,v in zip(coordinates,coordinates[1:]+coordinates[:1])) for axis in range(3)]
        axis=max(range(3),key=lambda i:abs(area[i]));other=[i for i in range(3) if i!=axis]
        if area[axis]==0 or not simple([tuple(p[i] for i in other) for p in coordinates]):reasons.append('non_simple_or_zero_exact_projection')
    if len(set(map(int,owners)))<limits['min_distinct_acquired_owners']:reasons.append('insufficient_distinct_actual_acquired_owners')
    orientation=sum((np.cross(local[i],local[(i+1)%len(points)]) for i in range(len(points))),start=np.zeros(3))
    if np.dot(normal,orientation)>0:normal=-normal
    dots=[]
    for index,source_normal in zip(positions,normals):
        tangent=points[(int(index)+1)%len(points)]-points[int(index)];length=np.linalg.norm(tangent)
        if length==0:reasons.append('missing_or_zero_acquired_edge');continue
        binormal=np.cross(tangent/length,source_normal);norm=np.linalg.norm(binormal)
        if norm==0:reasons.append('zero_acquired_edge_binormal');continue
        dots.append(float(np.dot(binormal/norm,normal)))
    if not len(positions):reasons.append('missing_or_zero_acquired_edge')
    if dots:
        if min(dots)<=0:reasons.append('nonpositive_acquired_edge_binormal')
        if np.quantile(dots,.1)<limits['minimum_acquired_binormal_signed_p10']:reasons.append('acquired_edge_binormal_cone')
    return reasons


def controls(limits):
    p=np.array([[.2,0.,.1],[.2,.2,.1],[.2,.2,-.1],[.2,0.,-.1]])
    normals=np.array([[0.,0.,1.],[0.,0.,-1.]])
    assert not inspect(p,[0,2],normals,[10,11],limits)
    assert not inspect(p+[.5,-.25,.1],[0,2],normals,[10,11],limits)
    assert 'nonpositive_acquired_edge_binormal' in inspect(p[[0,3,2,1]],[1,3],-normals[::-1],[11,10],limits)
    assert 'insufficient_distinct_actual_acquired_owners' in inspect(p,[0],normals[:1],[10],limits)
    assert 'insufficient_distinct_actual_acquired_owners' in inspect(p,[0,2],normals,[10,10],limits)
    assert 'missing_or_zero_acquired_edge' in inspect(p,[],np.empty((0,3)),[],limits)
    assert 'nonpositive_acquired_edge_binormal' in inspect(p,[0,2],-normals,[10,11],limits)
    assert 'acquired_edge_binormal_cone' in inspect(p,[0,2],np.array([[.8,0.,.6],[-.8,0.,-.6]]),[10,11],limits)
    assert 'non_simple_or_zero_exact_projection' in inspect(p[[0,2,1,3]],[0,2],normals,[10,11],limits)
    assert 'repeated_source_coordinate' in inspect(p[[0,1,2,0]],[0,1],normals,[10,11],limits)
    assert 'diagonal' in inspect(p*20,[0,2],normals,[10,11],limits)
    curve=np.c_[np.zeros(129),np.cos(np.arange(129)*2*np.pi/129),np.sin(np.arange(129)*2*np.pi/129)]
    assert 'edge_count' in inspect(curve,[0,64],normals,[10,11],limits)
    assert 'rank_below_two' in inspect(np.array([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]]),[0,1],normals,[10,11],limits)
    assert 'planarity' in inspect(np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]),[0,2],normals,[10,11],limits)
    assert not simple([(Fraction(0),Fraction(0)),(Fraction(1),Fraction(1)),(Fraction(0),Fraction(1)),(Fraction(1),Fraction(0))])
    assert not simple([(Fraction(0),Fraction(0)),(Fraction(2),Fraction(0)),(Fraction(1),Fraction(0)),(Fraction(0),Fraction(1))])
    return 16


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','admission','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();started=time.monotonic();job=json.loads(args.job.read_text())
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    decisions=json.loads((args.admission/'private-all-walk-decisions.json').read_text());saved=load(args.admission/'private-acquired-owner-references.npz')
    mesh,boundary,raw,previous,old_mesh,old_border,frontier,untried,opposed=map(load,
        (job['mesh'],job['boundaries'],job['source_arrays'],job['immediate_parent_mesh'],job['frontier_parent_mesh'],job['frontier_parent_boundaries'],job['frontier_census'],job['untried_census'],job['opposed_census']))
    identity=module(job['raw_identity_inspector'],'scalar_end_wall_identity');control_count=controls(job['limits']);identity_count=identity.identity_controls()
    nv=len(mesh['points']);parent_faces=previous['triangles']
    parent_edges=np.concatenate([parent_faces[:,[0,1]],parent_faces[:,[1,2]],parent_faces[:,[2,0]]])
    codes=np.minimum(parent_edges[:,0],parent_edges[:,1])*nv+np.maximum(parent_edges[:,0],parent_edges[:,1])
    new_ids=np.flatnonzero(boundary['edge_origin_kind']==8);new_edges=boundary['boundary'][new_ids];new_codes=new_edges.min(axis=1)*nv+new_edges.max(axis=1)
    assert not np.isin(new_codes,codes).any();del previous,parent_edges,codes
    selected=[];scoped=[];signatures=np.full((len(boundary['boundary']),7),-1,dtype=np.int64);references=[];offsets=[0];normals=np.zeros((len(signatures),3));cache={}
    for curve in range(len(boundary['offsets'])-1):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];origins=set(map(int,boundary['edge_origin_kind'][ids]))
        if 8 in origins and not origins-{1,6,7,8}:scoped.append(curve)
    scope_edges=set(int(edge) for curve in scoped for edge in boundary['cycle_edges'][boundary['offsets'][curve]:boundary['offsets'][curve+1]])
    for edge,(nodes,owner,origin) in enumerate(zip(boundary['boundary'],boundary['owners'],boundary['edge_origin_kind'])):
        refs=[]
        if edge in scope_edges:
            face_nodes=mesh['triangles'][owner];assert tuple(map(int,nodes)) in list(zip(map(int,face_nodes),map(int,np.roll(face_nodes,-1))))
            if origin==1:
                key,normals[edge]=identity.original_key(mesh,nodes,owner,raw);refs=[key];signatures[edge]=[0,key[0],key[0],-1,-1,key[1],key[2]]
            else:
                kind,field,census={6:(4,'source_frontier_pair_ids',frontier),7:(6,'source_untried_pair_ids',untried),8:(7,'source_opposed_wall_pair_ids',opposed)}[int(origin)]
                assert mesh['inferred_surface_kind'][owner]==kind and mesh['original_face_ids'][owner]==-1
                pair=int(mesh[field][owner]);assert pair>=0
                if (kind,pair) not in cache:
                    source_edges=census['selected_pair_edge_ids'][pair]
                    if kind==4:keys=[identity.original_key(old_mesh,old_border['boundary_local_nodes'][row],old_border['boundary_face_rows'][row],raw)[0] for row in source_edges]
                    else:keys=census['source_edge_keys'][source_edges]
                    cache[kind,pair]=np.asarray(keys,dtype=np.int64)
                refs=cache[kind,pair];quad_nodes=[int(refs[0,1]),int(refs[0,2]),int(refs[1,1]),int(refs[1,2])];quad=raw['vertices'][quad_nodes]
                assert len(set(map(tuple,quad)))==4
                local=[]
                for point in mesh['points'][face_nodes]:
                    matches=np.flatnonzero(np.all(quad==point,axis=1));assert len(matches)==1;local.append(int(matches[0]))
                direction=set(zip(local,local[1:]+local[:1]));observed_sides=0
                for a,b in [(0,1),(2,3)]:
                    if a in local and b in local:assert (b,a) in direction;observed_sides+=1
                assert observed_sides==1
                endpoints=[]
                for node in nodes:
                    matches=np.flatnonzero(np.all(quad==mesh['points'][node],axis=1));assert len(matches)==1;endpoints.append(quad_nodes[int(matches[0])])
                signatures[edge]=[kind,pair,int(refs[0,0]),int(refs[1,0]),-1,*endpoints]
        references.extend(refs);offsets.append(len(references))
    assert np.array_equal(offsets,saved['offsets']) and np.array_equal(np.asarray(references).reshape(-1,3),saved['raw_owner_edge_keys'])
    assert np.array_equal(signatures,saved['edge_signatures']) and np.array_equal(normals,saved['actual_acquired_normals'])
    assert len(decisions)==len(boundary['offsets'])-1
    for curve,row in enumerate(decisions):
        assert row['curve']==curve and row['eligible_scope']==(curve in scoped)
        if curve not in scoped:assert not row['admitted'];continue
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];nodes=boundary['boundary'][ids,0]
        acquired=np.flatnonzero(boundary['edge_origin_kind'][ids]==1);owner_ids=mesh['original_face_ids'][boundary['owners'][ids[acquired]]]
        reasons=inspect(mesh['points'][nodes],acquired,normals[ids[acquired]],owner_ids,job['limits'])
        assert set(reasons)==set(row['reasons']) and (not reasons)==row['admitted']
        sequence=[tuple(map(int,x)) for x in signatures[ids]];canonical=min(tuple(sequence[i:]+sequence[:i]) for i in range(len(sequence)))
        digest=hashlib.sha256(json.dumps(canonical,separators=(',',':')).encode()).hexdigest();assert digest==row['directed_source_cycle_sha256']
        if not reasons:selected.append(curve)
    assert np.array_equal(selected,np.load(args.admission/'private-admitted-walk-ids.npy',allow_pickle=False))
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),complete_walk_denominator=len(decisions),new_wall_border_walks=len(scoped),scoped_edges=len(scope_edges),admitted_trials=len(selected),new_cross_edges_independently_absent_from_all_parent_faces=len(new_ids),signed_source_projection_controls_passed=control_count,raw_identity_controls_passed=identity_count,all_scoped_raw_ancestry_signatures_and_cycle_identities_verified=True,all_walk_decisions_independently_replayed=True,admission_independently_verified=True,producer_imported=False,inferred_normals_used_as_acquired_evidence=False,geometry_modified=False,physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
