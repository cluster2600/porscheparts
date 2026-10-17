"""Prepare only small synthetic cap-aware fixtures; never load head geometry."""
from collections import Counter
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT/'work/962-engineering/atomic-cavity-plane-clip-prep-001/fixtures/through-hole.bin'
OLD_SHA='797faffffa12090616b2cb9587419295d3a7f0336b193953f7fc5939619b331b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def quality(p,t):
    a,b,c=[p[v] for v in t];u=sub(b,a);v=sub(c,a);n=cross(u,v)
    return 2*math.sqrt(3)*math.sqrt(dot(n,n))/(dot(u,u)+dot(v,v)+dot(sub(v,u),sub(v,u)))


def metadata(p,faces):
    rational=[tuple(F(x) for x in row) for row in p]
    counts=Counter();balance=Counter();poor=[]
    for i,t in enumerate(faces):
        a,b,c=[rational[v] for v in t];u=sub(b,a);v=sub(c,a);n=cross(u,v)
        total=dot(u,u)+dot(v,v)+dot(sub(v,u),sub(v,u))
        if not dot(n,n)>0:raise ValueError('Degenerate fixture')
        if 2523*dot(n,n)<total*total:poor.append(i)
        for a,b in zip(t,t[1:]+t[:1]):counts[tuple(sorted((a,b)))]+=1;balance[tuple(sorted((a,b)))]+=1 if a<b else -1
    if set(counts.values())!={2} or any(balance.values()):raise ValueError('Nonclosed fixture')
    volume=sum(dot(rational[a],cross(rational[b],rational[c])) for a,b,c in faces)/6
    if volume!=12 or len(p)-len(counts)+len(faces)!=0:raise ValueError('Analytic volume/Euler mismatch')
    seeds={v for i in poor for v in faces[i]}
    patch=[i for i,t in enumerate(faces) if seeds&set(t)]
    fixed=sorted({v for i,t in enumerate(faces) if i not in patch for v in t})
    cap=[i for i,t in enumerate(faces) if all(p[v][2]==0. for v in t)]
    return dict(vertices=len(p),faces=len(faces),edges=len(counts),Euler=0,exact_volume_mm3='12',
        poor_face_ids=poor,poor_cap_face_ids=sorted(set(poor)&set(cap)),poor_noncap_face_ids=sorted(set(poor)-set(cap)),
        poor_seed_vertex_ids=sorted(seeds),incident_face_ids=patch,exterior_face_ids=[i for i in range(len(faces)) if i not in patch],
        exterior_fixed_vertex_ids=fixed,cap_face_ids=cap,fixed_cap_face_ids=sorted(set(cap)-set(patch)))


def native_order_score_bounds(p,faces,members,keeper):
    rows=[]
    for i,t in enumerate(faces):
        if not set(t)&set(members) or all(p[v][2]==0. for v in t):continue
        new=tuple(keeper if v in members else v for v in t)
        if len(set(new))<3:continue
        before=cross(sub(p[t[1]],p[t[0]]),sub(p[t[2]],p[t[0]]))
        after=cross(sub(p[new[1]],p[new[0]]),sub(p[new[2]],p[new[0]]))
        if dot(before,after)<=0:return dict(eligible=False)
        values=[quality(p,order) for order in itertools.permutations(new)]
        rows.append(dict(face_id=i,minimum_over_six_orders=min(values),maximum_over_six_orders=max(values)))
    return dict(eligible=bool(rows),surviving_noncap_face_ids=[x['face_id'] for x in rows],
        score_lower=min(x['minimum_over_six_orders'] for x in rows),
        score_upper=min(x['maximum_over_six_orders'] for x in rows))


def surface_bytes(p,faces):
    return b'962SURF1'+struct.pack('<QQ',len(p),len(faces))+b''.join(struct.pack('<ddd',*x) for x in p)+b''.join(struct.pack('<QQQ',*t) for t in faces)


def split(p,faces,number):
    points=list(p)+[(i*2.**-10,-2.,0.) for i in range(number)]
    ids=list(range(16,16+number));result=[]
    for t in faces:
        oriented=next((j for j in range(3) if {t[j],t[(j+1)%3]}=={0,1}),None)
        if oriented is None:result.append(tuple(t));continue
        a,b,c=t[oriented],t[(oriented+1)%3],t[(oriented+2)%3]
        path=[a]+(ids if a==0 else list(reversed(ids)))+[b]
        result.extend((x,y,c) for x,y in zip(path,path[1:]))
    return points,result


def main():
    if sha(OLD)!=OLD_SHA:raise ValueError('Retained literal source changed')
    if (HERE/'fixtures').exists() or (HERE/'expectations.json').exists():raise FileExistsError('Preserve previous preparation')
    raw=OLD.read_bytes();nv,nf=struct.unpack_from('<QQ',raw,8)
    if (nv,nf)!=(16,32):raise ValueError('Retained prism counts changed')
    points=[(x,y,(z+1.)/2.) for x,y,z in struct.iter_unpack('<ddd',raw[24:24+24*nv])]
    faces=list(struct.iter_unpack('<QQQ',raw[24+24*nv:]));metadata(points,faces)
    reference_p,reference_f=split(points,faces,1)
    pair_p,pair_f=split(points,faces,2);triple_p,triple_f=split(points,faces,3)
    pairs={'pair':(pair_p,pair_f,[[16,17]],0),'triple':(triple_p,triple_f,[[16,17],[17,18]],0),
           'fixed-refusal':(pair_p,pair_f,[[2,3]],3),'cross-loop-refusal':(pair_p,pair_f,[[9,16]],3)}
    fixture_dir=HERE/'fixtures';fixture_dir.mkdir()
    (fixture_dir/'reference.bin').write_bytes(surface_bytes(reference_p,reference_f))
    refs=dict(schema='962-cap-aware-synthetic-fixtures/v1',source_literal=dict(relative_path=str(OLD.relative_to(ROOT)),sha256=OLD_SHA,
        explicit_fixture_only_transform='(x,y,z)->(x,y,(z+1)/2), z:-1/1->0/1; through-hole prism remains exact volume12'),
        epsilon='1/1024',reference_points=reference_p,reference_oriented_faces=reference_f,reference_topology=metadata(reference_p,reference_f),cases={})
    for name,(p,f,targets,rc) in pairs.items():
        (fixture_dir/(name+'.bin')).write_bytes(surface_bytes(p,f))
        (fixture_dir/(name+'.targets.u64')).write_bytes(b''.join(struct.pack('<QQ',*e) for e in targets))
        info=metadata(p,f);case=dict(input_file='fixtures/'+name+'.bin',targets_file='fixtures/'+name+'.targets.u64',
            input_sha256=sha(fixture_dir/(name+'.bin')),targets_sha256=sha(fixture_dir/(name+'.targets.u64')),
            input_points=p,input_oriented_faces=f,targets=targets,input_observations=info,expected_returncode=rc)
        if rc==0:
            members=sorted({v for edge in targets for v in edge});scores={str(k):native_order_score_bounds(p,f,members,k) for k in members}
            keeper=max(members)
            if not all(x['eligible'] for x in scores.values()) or not scores[str(keeper)]['score_lower']>max(x['score_upper'] for k,x in scores.items() if k!=str(keeper)):
                raise ValueError('Unique declared keeper not established across all corner orders')
            case.update(expected_keeper=keeper,group_members=members,native_score_six_order_bounds=scores,
                expected_output_origins=list(range(16))+[keeper],expected_output_vertices=17,expected_output_faces=34,
                expected_exact_volume_mm3='12',expected_cap_area_mm2='12',expected_Euler=0,expected_poor_faces=0,
                cap_triangulation='Any independently verified nonoverlapping complete annulus triangulation preserving fixed cap cells; no cocircular diagonal is guessed.')
        elif name=='fixed-refusal':
            if not set(targets[0])<=set(info['exterior_fixed_vertex_ids']):raise ValueError('Fixed refusal does not isolate fixed vertices')
            case['reason_scope']='Both target endpoints exterior-fixed; no export permitted.'
        else:
            if set(targets[0])&set(info['exterior_fixed_vertex_ids']):raise ValueError('Cross-loop fixture has an unrelated fixed conflict')
            case['reason_scope']='Existing internal cap edge joins outer/inner boundary loops; both endpoints free; no export permitted.'
        refs['cases'][name]=case
    with (HERE/'expectations.json').open('x') as s:json.dump(refs,s,indent=2,allow_nan=False);s.write('\n')
    print(json.dumps(dict(status='synthetic_literal_data_prepared_no_native',reference_volume='12',cases={k:dict(returncode=v['expected_returncode'],poor=len(v['input_observations']['poor_face_ids']),fixed_cap_cells=len(v['input_observations']['fixed_cap_face_ids'])) for k,v in refs['cases'].items()},expectations_sha256=sha(HERE/'expectations.json'))))


if __name__=='__main__':main()
