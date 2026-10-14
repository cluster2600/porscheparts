"""Independent tetrahedral moments, diagonal face normals and incidence readback."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

w = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
src = Path('work/bionic-buffered-transition-20261013')
for row in json.loads(Path('work/bionic-airflow-delivery-20261013-buffered-transition/file-manifest.json').read_text())['files']:
    assert sha(Path('work')/row['path']) == row['sha256']
s = json.loads((src/'construction.json').read_text())
p = np.array(s['vertices'])


def face_moments(q):
    # Triangulate about vertex zero, distinct from the native vertex-mean fan.
    vectors = [np.cross(q[j]-q[0], q[j+1]-q[0])/2 for j in range(1,len(q)-1)]
    sizes = [float(np.linalg.norm(v)) for v in vectors]
    normal = sum(vectors)
    assert all(float(v@normal)>0 for v in vectors)
    centre = sum(a*(q[0]+q[j+1]+q[j+2])/3 for j,a in enumerate(sizes))/sum(sizes)
    return centre, normal


def tetra_moments(points, faces):
    anchor = points.mean(axis=0)
    volumes, moments = [], []
    for face in faces:
        q = points[face]-anchor
        for j in range(1,len(q)-1):
            volume = float(np.dot(q[0],np.cross(q[j],q[j+1])))/6
            volumes.append(volume)
            moments.append(volume*(q[0]+q[j]+q[j+1])/4)
    total = math.fsum(volumes)
    assert total>0
    return anchor+sum(moments)/total, total


raw = ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
cube = np.array([(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)],float)
for scale in (1.,1e-3,1e-6):
    c,v=tetra_moments(cube*scale,[list(f) for f in raw])
    assert np.max(abs(c-scale*.5))<scale*1e-14 and abs(v/scale**3-1)<1e-14
tet = np.array([(0,0,0),(1,0,0),(0,1,0),(0,0,1)],float)
c,v=tetra_moments(tet,[[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
assert np.max(abs(c-.25))<1e-14 and abs(v-1/6)<1e-14

registry=defaultdict(list);polys=[];centres=[];volumes=[];geometry=[]
for cell,b in enumerate(s['blocks']):
    faces=[]
    for template in raw:
        f=[]
        for k in template:
            if not f or f[-1]!=b[k]:f.append(b[k])
        if f[-1]==f[0]:f.pop()
        if len(f)<3:continue
        assert len(set(f))==len(f)
        faces.append(f);registry[tuple(sorted(f))].append((cell,f))
    ids=sorted(set(b));remap={k:i for i,k in enumerate(ids)}
    c,v=tetra_moments(p[ids],[[remap[k] for k in f] for f in faces])
    centres.append(c);volumes.append(v);polys.append(faces)
    geometry.append([face_moments(p[f]) for f in faces])
assert all(len(pair) in (1,2) for pair in registry.values())
boundary={key for key,pair in registry.items() if len(pair)==1}
assert boundary=={tuple(sorted(set(f))) for f in s['walls']}
cell_rows=list(csv.DictReader((w/'cells.csv').open()))
assert [int(r['cell']) for r in cell_rows]==list(range(len(polys)))
det_errors=[];score_errors=[];volume_errors=[]
for i,(r,faces,ca) in enumerate(zip(cell_rows,polys,geometry)):
    assert r['stage']==s['stages'][i]
    eligible=[area for f,(_,area) in zip(faces,ca) if len(registry[tuple(sorted(f))])==2]
    mean=math.fsum(float(np.linalg.norm(a)) for a in eligible)/len(eligible)
    tensor=sum(np.outer(a,a) for a in eligible)/mean**2
    determinant=abs(float(tensor[0]@np.cross(tensor[1],tensor[2])))/8
    score=max(float((d-c)@a/np.linalg.norm(d-c)/np.linalg.norm(a)) for k,(c,a) in enumerate(ca) for j,(d,_) in enumerate(ca) if j!=k)
    closure=[]
    for name,z in [('lower',s['stations_m'][0]),('upper',s['stations_m'][-1])]:
        if any(tuple(sorted(f)) in boundary and all(p[k,2]==z for k in f) for f in faces):closure.append(name)
    assert r['closure']==('+'.join(closure) or 'none') and int(r['internal_faces'])==len(eligible)
    det_errors.append(abs(determinant-float(r['determinant'])))
    score_errors.append(abs(score-float(r['plane_score'])))
    volume_errors.append(abs(volumes[i]/float(r['volume_m3'])-1))
    assert (determinant<.001)==(float(r['determinant'])<.001)
    assert (score>-1e-6)==(float(r['plane_score'])>-1e-6)
face_rows=list(csv.DictReader((w/'faces.csv').open()))
expected={tuple(sorted([x[0] for x in pair])):pair for pair in registry.values() if len(pair)==2}
assert len(expected)==len(face_rows)==13696
angle_errors=[];normal_errors=[];tangent_errors=[];margin_errors=[];seen=set()
for r in face_rows:
    a,b=int(r['owner']),int(r['neighbour']);key=tuple(sorted((a,b)));assert key not in seen;seen.add(key)
    pair=expected[key];f=next(f for cell,f in pair if cell==a)
    normal=face_moments(p[f])[1];normal/=np.linalg.norm(normal)
    delta=centres[b]-centres[a];dn=float(delta@normal);dt=float(np.linalg.norm(np.cross(delta,normal)))
    assert dn>0 and r['family']=='/'.join(sorted((s['stages'][a],s['stages'][b])))
    angle=math.degrees(math.atan2(dt,dn));margin=math.tan(math.radians(70))*dn-dt
    angle_errors.append(abs(angle-float(r['angle_deg'])))
    normal_errors.append(abs(dn-float(r['normal_m'])))
    tangent_errors.append(abs(dt-float(r['tangential_m'])))
    margin_errors.append(abs(margin-float(r['margin_m'])))
    assert (margin<0)==(float(r['margin_m'])<0)
assert seen==set(expected)
assert max(angle_errors)<1e-9 and max(det_errors)<1e-10 and max(score_errors)<1e-10 and max(volume_errors)<1e-11
out=dict(reader_sha256=sha(Path(__file__)),analytic_cube_and_tetrahedron_checks=True,all_source_payloads_verified=True,all_cell_and_internal_face_rows_checked=True,cells=len(cell_rows),internal_faces=len(face_rows),boundary_faces=len(boundary),max_angle_difference_deg=max(angle_errors),max_normal_difference_m=max(normal_errors),max_tangent_difference_m=max(tangent_errors),max_margin_difference_m=max(margin_errors),max_determinant_difference=max(det_errors),max_plane_score_difference=max(score_errors),max_volume_relative_difference=max(volume_errors),volume_m3=math.fsum(volumes),new_candidate=False,native_executed=False,accepted=False)
(w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
