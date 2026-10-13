"""Algebraic admission predicates and unassigned radial interface variables."""
import ast
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

w=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=Path('work/bionic-buffered-transition-20261013')
for base in ('buffered-transition','neighbour-constraints'):
    manifest=Path(f'work/bionic-airflow-delivery-20261013-{base}/file-manifest.json')
    for row in json.loads(manifest.read_text())['files']:
        assert sha(Path('work')/row['path'])==row['sha256']
s=json.loads((src/'construction.json').read_text());p=np.array(s['vertices'])
assert sha(src/'construction.json')=='ddda1839b41b7dfde9b7303d90f47e35c0ac35726f1db1278117366de71eb9e4'
helper=Path('twins/bionic-turbo-f1/evidence/airflow-conformal-local-design-20261013/verify_pyramids.py')
assert sha(helper)=='673f80a53bd03dba18820fa060c51e4cea75c660a6e546a8cda6c1e394be6c2a'
tree=ast.parse(helper.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('polygon','metrics')],type_ignores=[]),str(helper),'exec'))

ratios=s['radial_ratios'];rings=defaultdict(list);bindings=[];roundtrip=True
for i,(x,y,z) in enumerate(s['vertices']):
    radius=float(np.interp(z,s['stations_m'],s['radii_m']))
    q=math.hypot(x,y)/radius
    hits=[j for j,r in enumerate(ratios) if abs(q-r)<1e-14]
    assert len(hits)==1
    ring=hits[0];rings[ring].append(i)
    if ring in (2,3):
        var='u' if ring==2 else 'v';q0=Fraction(ratios[ring])
        # Fractions refer to the decoded binary64 values, not invented precision.
        cx,cy=Fraction(x)/q0,Fraction(y)/q0
        assert cx*q0==Fraction(x) and cy*q0==Fraction(y)
        bindings.append(dict(point=i,variable=var,x_coefficient=str(cx),y_coefficient=str(cy),z_exact=str(Fraction(z))))
assert {k:len(v) for k,v in rings.items()}=={0:1024,1:512,2:1024,3:1792,4:1792}
system={
 'source_construction_sha256':sha(src/'construction.json'),
 'unknowns':{'u':'ratio of ring 2','v':'ratio of ring 3'},
 'domain':{'strict_order':['1 < u','u < v',f'v < {Fraction(ratios[4])}']},
 'archived_regression_point':{'u':str(Fraction(ratios[2])),'v':str(Fraction(ratios[3]))},
 'selected_new_values':None,
 'fixed_point_labels':sorted(rings[0]+rings[1]+rings[4]),
 'coordinate_bindings':bindings,
 'fixed_topology_source':'construction.json blocks and walls in parent PR229 archive',
 'angle_constant':{'name':'kappa','meaning':'cos(70 degrees)^2','polynomial':'64*kappa^3 - 96*kappa^2 + 36*kappa - 3 = 0','isolating_interval':['116/1000','118/1000']},
 'internal_face_predicates':['S dot S > 0','delta dot delta > 0','D = delta dot S > 0','D^2 - kappa*(delta dot delta)*(S dot S) >= 0'],
 'cell_determinant_predicates':['m = number of internal faces','G = sum(S_f outer S_f) over internal faces','E = sum(sqrt(S_f dot S_f)) over internal faces > 0','125*m^6*det(G) - E^6 >= 0'],
 'ordered_face_pair_predicates':['delta_f = C_g - C_f != 0','L = S_f dot delta_f < 0','L^2 - (1/1000000)^2*(S_f dot S_f)*(delta_f dot delta_f) >= 0'],
 'cell_moment_definition':'Native face-vertex-mean fan centres and area vectors; signed pyramids about the mean of face centres; C=sum(V_f*(3*C_f+seed)/4)/sum(V_f), V=sum(V_f)>0. C is dependent, not free.',
 'boundary_rules':['No owner-neighbour angle on uncoupled walls','No boundary face in G or E','Keep both end stations and exact shared face cycles','Prove oriented boundary coverage and non-intersection separately for any selected new values'],
 'additional_obligations':['positive face areas and cell volumes','unchanged MRF faces and fixed boundary rings','planarity and rotational geometric balance at inherited criteria','native quality admission before solver','physical walls, layers and global rest remain unqualified'],
 'feasibility_solved':False,'candidate_created':False,'native_executed':False}

# Regress predicates at the ONLY archived point. No evaluation at other u,v.
reg=defaultdict(list);polys=[];centres=[];volumes=[];geoms=[]
for cell,b in enumerate(s['blocks']):
    n=4 if s['stages'][cell]=='buffer' else 3
    lo=b[:n];hi=b[4:4+n]
    faces=[lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)]
    for f in faces:reg[tuple(sorted(f))].append((cell,f))
    c,v,ca=metrics([[p[k] for k in f] for f in faces]);assert v>0
    polys.append(faces);centres.append(c);volumes.append(v);geoms.append(ca)
assert all(len(v) in (1,2) for v in reg.values())
kappa=math.cos(math.radians(70))**2
assert .116<kappa<.118 and abs(64*kappa**3-96*kappa**2+36*kappa-3)<1e-14
angle_rows=[];plane_rows=[];det_rows=[]
for pair in reg.values():
    if len(pair)==1:continue
    (a,f),(b,_)=pair;S=np.array(polygon([p[k] for k in f])[1]);delta=centres[b]-centres[a]
    D=float(delta@S);norm2=float(delta@delta)*float(S@S);assert D>0 and norm2>0
    residual=D*D/norm2-kappa
    angle=math.degrees(math.atan2(float(np.linalg.norm(np.cross(delta,S))),D))
    assert (residual<0)==(angle>70)
    angle_rows.append(dict(owner=a,neighbour=b,normal_sign_positive=True,scaled_cone_residual=residual,rejected=residual<0))
for cell,(faces,ca) in enumerate(zip(polys,geoms)):
    internal=[np.array(S) for f,(_,S) in zip(faces,ca) if len(reg[tuple(sorted(f))])==2]
    m=len(internal);E=math.fsum(float(np.linalg.norm(S)) for S in internal);G=sum(np.outer(S,S) for S in internal)
    detG=float(G[0]@np.cross(G[1],G[2]));assert E>0 and detG>=0
    scaled=125*m**6*detG/E**6-1
    direct=abs(float(np.linalg.det(G/(E/m)**2)))/8
    assert (scaled<0)==(direct<.001) and abs(scaled-(1000*direct-1))<1e-9
    det_rows.append(dict(cell=cell,internal_faces=m,scaled_determinant_residual=scaled,rejected=scaled<0))
    for i,(ci,S) in enumerate(ca):
        for j,(cj,_) in enumerate(ca):
            if i==j:continue
            delta=cj-ci;L=float(np.dot(S,delta));norm2=float(np.dot(S,S)*np.dot(delta,delta));assert norm2>0
            score=L/math.sqrt(norm2);scaled=L*L/norm2-1e-12
            algebraic=(L<0 and scaled>=0)
            assert algebraic==(score<=-1e-6)
            plane_rows.append(dict(cell=cell,face_i=i,face_j=j,negative_sign=L<0,scaled_plane_residual=scaled,rejected=not algebraic))
old={(int(r['owner']),int(r['neighbour'])) for r in csv.DictReader((src/'angles.csv').open()) if float(r['angle_deg'])>70}
assert old=={(r['owner'],r['neighbour']) for r in angle_rows if r['rejected']}
assert len(angle_rows)==13696 and len(det_rows)==6144 and len(plane_rows)==138240
for name,rows in [('angle-predicates.csv',angle_rows),('determinant-predicates.csv',det_rows),('plane-predicates.csv',plane_rows)]:
    with (w/name).open('x') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
(w/'system.json').write_text(json.dumps(system,indent=2)+'\n')
out=dict(source_sha256=sha(Path(__file__)),all_parent_payloads_verified=True,coordinate_bindings=len(bindings),fixed_points=len(system['fixed_point_labels']),coordinate_identity_at_archived_point_exact_rational=True,internal_face_constraints=len(angle_rows),cell_determinant_constraints=len(det_rows),ordered_plane_constraints=len(plane_rows),rejected_angles=sum(r['rejected'] for r in angle_rows),rejected_determinants=sum(r['rejected'] for r in det_rows),rejected_planes=sum(r['rejected'] for r in plane_rows),minimum_scaled_cone_residual=min(r['scaled_cone_residual'] for r in angle_rows),minimum_scaled_determinant_residual=min(r['scaled_determinant_residual'] for r in det_rows),only_archived_ratios_evaluated=True,feasibility_solved=False,candidate_created=False,native_executed=False)
(w/'readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
