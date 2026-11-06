"""Independently rejoin original positive-edge components and source sections.

Uses endpoint dictionaries/disjoint sets instead of the producer's packed-edge
sparse graph, a separate signed-error bound with rational fallback, and a 3D
vector-area calculation. Rational planar predicates reject crossed/backtracking
or overlapping proposed section loops. No anatomical identity is inferred.
"""
import argparse
from collections import Counter,defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
    return h.hexdigest()


def signed(vertices,plane):
    product=vertices*plane[:3]
    value=((product[:,0]+product[:,1])+product[:,2])+plane[3]
    epsilon=np.finfo(float).eps
    error=16*epsilon/(1-16*epsilon)*(np.abs(product).sum(axis=1)+abs(plane[3]))+16*np.nextafter(0.,1.)
    result=np.where(value>error,1,np.where(value<-error,-1,0)).astype(np.int8)
    unknown=np.flatnonzero(result==0);n=list(map(F.from_float,map(float,plane)))
    for i in unknown:
        q=sum((F.from_float(float(vertices[i,j]))*n[j] for j in range(3)),n[3]);result[i]=(q>0)-(q<0)
    return result,len(unknown)


class Sets:
    def __init__(self,n):self.parent=list(range(n));self.size=[1]*n
    def find(self,a):
        while self.parent[a]!=a:self.parent[a]=self.parent[self.parent[a]];a=self.parent[a]
        return a
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a==b:return
        if self.size[a]<self.size[b]:a,b=b,a
        self.parent[b]=a;self.size[a]+=self.size[b]


def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on_segment(a,b,c):
    return orient(a,b,c)==0 and all(min(a[j],b[j])<=c[j]<=max(a[j],b[j]) for j in range(2))


def intersect(a,b,c,d):
    x,y,z,w=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if (x>0)!=(y>0) and (z>0)!=(w>0) and all(v!=0 for v in (x,y,z,w)):return True
    return (x==0 and on_segment(a,b,c)) or (y==0 and on_segment(a,b,d)) or (z==0 and on_segment(c,d,a)) or (w==0 and on_segment(c,d,b))


def simple(p):
    n=len(p)
    if n<3 or len(set(p))!=n:return False
    for i in range(n):
        a,b,c=p[i-1],p[i],p[(i+1)%n]
        if orient(a,b,c)==0 and sum((b[j]-a[j])*(c[j]-b[j]) for j in range(2))<=0:return False
    for i in range(n):
        for j in range(i+2,n):
            if i==0 and j==n-1:continue
            if intersect(p[i],p[(i+1)%n],p[j],p[(j+1)%n]):return False
    return True


def inside(q,p):
    winding=0
    for a,b in zip(p,p[1:]+p[:1]):
        if on_segment(a,b,q):return True
        if a[1]<=q[1]<b[1] and orient(a,b,q)>0:winding+=1
        if b[1]<=q[1]<a[1] and orient(a,b,q)<0:winding-=1
    return winding!=0


def overlap(p,q):
    if any(intersect(a,b,c,d) for a,b in zip(p,p[1:]+p[:1]) for c,d in zip(q,q[1:]+q[:1])):return True
    return inside(p[0],q) or inside(q[0],p)


def controls():
    square=[(F(0),F(0)),(F(1),F(0)),(F(1),F(1)),(F(0),F(1))]
    bow=[square[i] for i in (0,2,1,3)];assert simple(square) and not simple(bow)
    assert not simple([(F(0),F(0)),(F(2),F(0)),(F(1),F(0)),(F(1),F(1))])
    inner=[(F(1,4)+x/4,F(1,4)+y/4) for x,y in square]
    away=[(x+2,y) for x,y in square]
    assert overlap(square,inner) and not overlap(square,away)
    v=np.array([[1.,1.,2.**-100],[1.,1.,-2.**-100],[1.,1.,0.]])
    s,_=signed(v,np.array([1.,-1.,1.,0.]));assert s.tolist()==[1,-1,0]
    return dict(exact_simple_and_bowtie_controls=True,collinear_backtracking_refused=True,
                nested_section_domains_overlap=True,disjoint_domains_separate=True,severe_cancellation_signed_exactly=True)


def inspect(vertices,faces,ids,plane,producer,private):
    direction,fallback=signed(vertices,plane);used=np.unique(faces[ids]);zeros=used[direction[used]==0]
    if len(zeros):
        assert not producer['admitted'] and producer['reason']=='exact_source_vertex_on_plane'
        return dict(plane_admitted=False,on_plane_vertices=len(zeros),proposals=[]),[]
    assert producer['admitted']
    active=ids[(direction[faces[ids]]>0).any(axis=1)];assert np.array_equal(active,private['active_source_face_ids'])
    sets=Sets(len(active));owners={};uses=Counter();segments={};vertex_count=len(vertices)
    for row,face_id in enumerate(active):
        tri=list(map(int,faces[face_id]));cross=[]
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            edge=(min(a,b),max(a,b))
            if direction[a]>0 or direction[b]>0:
                uses[edge]+=1;assert uses[edge]<=2
                if edge in owners:sets.join(row,owners[edge])
                else:owners[edge]=row
            if direction[a]!=direction[b]:cross.append(edge[0]*vertex_count+edge[1])
        if cross:assert len(cross)==2;segments[int(face_id)]=tuple(sorted(cross))
    roots=[sets.find(i) for i in range(len(active))];labels=private['active_component_labels']
    left={};right={}
    for a,b in zip(roots,map(int,labels)):
        assert left.setdefault(a,b)==b and right.setdefault(b,a)==a
    assert len(left)==producer['positive_surface_components']
    source_segments={int(i):tuple(sorted(map(int,p))) for i,p in zip(private['section_source_face_ids'],private['section_edge_codes'])}
    assert segments==source_segments
    component_members=defaultdict(list);component_segments=defaultdict(list)
    for row,face_id in enumerate(active):
        key=roots[row];component_members[key].append(int(face_id))
        if int(face_id) in segments:component_segments[key].append(int(face_id))
    exact={};rounded={};n=list(map(F.from_float,map(float,plane)))
    for key in set(x for pair in segments.values() for x in pair):
        a,b=divmod(key,vertex_count);va=list(map(F.from_float,map(float,vertices[a])));vb=list(map(F.from_float,map(float,vertices[b])))
        da=sum((va[j]*n[j] for j in range(3)),n[3]);db=sum((vb[j]*n[j] for j in range(3)),n[3])
        assert da*db<0
        point=tuple((da*vb[j]-db*va[j])/(da-db) for j in range(3));assert sum((point[j]*n[j] for j in range(3)),n[3])==0
        exact[key]=point;rounded[key]=np.array(list(map(float,point)))
    keys=private['cut_edge_codes'];assert np.array_equal(keys,np.array(sorted(exact)))
    assert np.array_equal(private['rounded_source_edge_intersections'],np.array([rounded[int(k)] for k in keys]).reshape(-1,3))
    normal=plane[:3];norm=math.sqrt(math.fsum(float(x*x) for x in normal));drop=int(np.argmax(np.abs(normal)));axes=[j for j in range(3) if j!=drop]
    proposals=[];records=[];max_delta=0.
    for record in producer['regions']:
        label=record['component'];root=right[label];members=np.array(component_members[root],dtype=np.int64)
        assert len(members)==record['source_faces'] and np.array_equal(members,private['component_'+str(label)+'_source_faces'])
        adjacency=defaultdict(set);node_uses=Counter();edge_set=set()
        for face_id in component_segments[root]:
            a,b=segments[face_id];adjacency[a].add(b);adjacency[b].add(a);node_uses[a]+=1;node_uses[b]+=1
            assert (a,b) not in edge_set;edge_set.add((a,b))
        regular=bool(adjacency) and all(node_uses[x]==2 and len(adjacency[x])==2 for x in adjacency)
        assert regular==record['section_graph_closed']
        groups=[];remaining=set(adjacency)
        if regular:
            while remaining:
                group=set();pending=[min(remaining)]
                while pending:
                    a=pending.pop()
                    if a in group:continue
                    group.add(a);pending.extend(adjacency[a]-group)
                remaining-=group;groups.append(group)
            assert len(groups)==record['section_loops']
        observed=[];seen_groups=[]
        for loop_id in range(len(groups)):
            loop=list(map(int,private['component_'+str(label)+'_loop_'+str(loop_id)+'_edge_codes']))
            assert len(loop)==len(set(loop))
            assert all(tuple(sorted((a,b))) in edge_set for a,b in zip(loop,loop[1:]+loop[:1]))
            group=set(loop);assert sum(group==g for g in groups)==1 and not any(group==g for g in seen_groups)
            seen_groups.append(group);observed.append(loop)
        selected=False;area=perimeter=circularity=None
        vv=vertices[np.unique(faces[members])];value=((vv[:,0]*normal[0]+vv[:,1]*normal[1])+vv[:,2]*normal[2])+plane[3]
        extent=float(value.max()/norm);max_delta=max(max_delta,abs(extent-record['outward_extension_nominal_mm']))
        if regular and len(groups)==1:
            loop=observed[0];p=np.array([rounded[k] for k in loop]);q=p-p[0]
            vector=np.cross(q,np.roll(q,-1,axis=0)).sum(axis=0)/2;area=float(np.linalg.norm(vector))
            perimeter=math.fsum(math.dist(a,b) for a,b in zip(p,np.roll(p,-1,axis=0)));circularity=4*math.pi*area/perimeter**2
            for key,value in [('area_nominal_mm2',area),('perimeter_nominal_mm',perimeter),('circularity',circularity)]:max_delta=max(max_delta,abs(value-record[key]))
            margins=[abs(area-10),abs(area-150),abs(circularity-.7),abs(extent-5)]
            selected=bool(min(margins)>1e-8 and np.all(np.linalg.norm(np.roll(p,-1,axis=0)-p,axis=1)>0)
                          and 10<=area<=150 and circularity>=.7 and extent>=5)
        assert selected==record['selected_provisional_region']
        if selected:
            polygon=[tuple(exact[k][j] for j in axes) for k in observed[0]];admitted=simple(polygon)
            proposals.append(dict(component=label,source_face_ids=members,loop=observed[0],exact_polygon=polygon,
                                  section_points=np.array([rounded[k] for k in observed[0]]),plane=plane,
                                  admitted=admitted,reason='simple_source_supported_section' if admitted else 'source_section_self_contact_or_overlap'))
        records.append(dict(component=label,source_faces=len(members),source_graph_and_section_verified=True,
                            selected_by_unchanged_classifier=selected))
    assert max_delta<1e-8
    for i,a in enumerate(proposals):
        for b in proposals[i+1:]:
            if a['admitted'] and b['admitted'] and overlap(a['exact_polygon'],b['exact_polygon']):
                a.update(admitted=False,reason='overlapping_source_section_domains');b.update(admitted=False,reason='overlapping_source_section_domains')
    public=[{k:v for k,v in p.items() if k in ('component','admitted','reason')} for p in proposals]
    return dict(plane_admitted=True,all_original_active_faces_rejoined=len(active),whole_component_partition_bijection=True,
                original_section_segments_rejoined=len(segments),exact_source_edge_intersections=len(exact),fraction_fallbacks=fallback,
                maximum_independent_metric_difference=max_delta,regions=records,proposals=public),proposals


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','producer','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();spec=json.loads(args.job.read_text());args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    for item in spec['inputs']:assert sha(item['path'])==item['sha256']
    checks=controls();source=json.loads((args.producer/'report.json').read_text())
    assert source['job_sha256']==sha(args.job) and source['original_data_unchanged']
    with np.load(spec['arrays'],allow_pickle=False) as p:vertices,faces=p['vertices'],p['triangles']
    with np.load(spec['admission'],allow_pickle=False) as p:ids=p['admitted_source_face_ids'];quarantine=p['quarantined_source_face_ids']
    planes=json.loads(Path(spec['planes']).read_text());records=[];regions=[]
    for index,plane in enumerate(planes):
        with np.load(args.producer/('private-plane-'+str(index)+'.npz'),allow_pickle=False) as p:private={k:p[k] for k in p.files}
        report,proposals=inspect(vertices,faces,ids,np.array(plane['keep_negative_halfspace_coefficients']),source['planes'][index],private)
        records.append(dict(plane=index,**report))
        for proposal in proposals:proposal['plane_index']=index;regions.append(proposal)
    for i,a in enumerate(regions):
        for b in regions[i+1:]:
            if a['admitted'] and b['admitted'] and a['plane_index']!=b['plane_index'] and np.intersect1d(a['source_face_ids'],b['source_face_ids']).size:
                a.update(admitted=False,reason='source_regions_overlap_across_planes');b.update(admitted=False,reason='source_regions_overlap_across_planes')
    role=np.full(len(faces),-2,dtype=np.int16);role[ids]=0;transition_owner=np.full(len(faces),-1,dtype=np.int16);delivered=[]
    for region in regions:
        if not region['admitted']:continue
        index=len(delivered)+1;members=region['source_face_ids'];direction,_=signed(vertices,region['plane'])
        strict=(direction[faces[members]]>0).all(axis=1);outside=members[strict];transition=members[~strict]
        assert np.all(role[members]==0);role[outside]=index;role[transition]=-1;transition_owner[transition]=index
        points_path=args.output/('private-region-'+str(index)+'.npz')
        np.savez_compressed(points_path,source_face_ids=members,fully_outward_source_face_ids=outside,transition_source_face_ids=transition,
                            section_edge_codes=np.array(region['loop'],dtype=np.int64),rounded_section_points=region['section_points'])
        delivered.append(dict(region=index,plane=region['plane_index'],component=region['component'],source_faces=len(members),
                              fully_outward_faces=len(outside),transition_faces=len(transition),section_nodes=len(region['loop']),
                              private_region_sha256=sha(points_path),anatomical_identity_accepted=False))
    assert np.all(role[quarantine]==-2) and np.array_equal(np.flatnonzero(role!=-2),ids)
    np.savez_compressed(args.output/'private-source-partition.npz',original_face_roles=role,transition_region=transition_owner)
    keep=np.flatnonzero((role==0)|(role==-1));used,index=np.unique(faces[keep],return_inverse=True)
    body=args.output/'retained-source-surface.npz';np.savez_compressed(body,vertices=vertices[used],triangles=index.reshape(-1,3),source_vertex_ids=used,source_face_ids=keep)
    with np.load(body,allow_pickle=False) as p:
        assert np.array_equal(p['vertices'],vertices[p['source_vertex_ids']])
        assert np.array_equal(p['source_vertex_ids'][p['triangles']],faces[p['source_face_ids']])
    for item in spec['inputs']:assert sha(item['path'])==item['sha256']
    report=dict(source_sha256=sha(__file__),producer_report_sha256=sha(args.producer/'report.json'),job_sha256=sha(args.job),controls=checks,
                planes=records,regions=delivered,all_acquired_faces_accounted=len(faces),retained_source_faces=len(keep),
                transition_faces_retained=int(np.count_nonzero(role==-1)),proposed_removed_source_faces=int(np.count_nonzero(role>0)),
                quarantined_faces_retained_in_original=len(quarantine),retained_geometry_exact_original_triangles=True,
                source_points_or_triangles_clipped_or_capped=False,retained_surface_sha256=sha(body),
                full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('planes','regions')}))


if __name__=='__main__':main()
