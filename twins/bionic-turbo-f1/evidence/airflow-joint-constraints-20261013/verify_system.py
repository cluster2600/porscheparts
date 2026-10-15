"""Independent binding checks and predicate verification with rational identities."""
import ast,csv,hashlib,json,math
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
import numpy as np

w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
system=json.loads((w/'system.json').read_text())
source=Path('work/bionic-buffered-transition-20261013/construction.json')
assert sha(source)==system['source_construction_sha256']
s=json.loads(source.read_text());p=np.array(s['vertices'])
for label in ('buffered-transition','neighbour-constraints'):
    for row in json.loads(Path(f'work/bionic-airflow-delivery-20261013-{label}/file-manifest.json').read_text())['files']:
        assert sha(Path('work')/row['path'])==row['sha256']
fixed=set(system['fixed_point_labels']);seen=set()
for b in system['coordinate_bindings']:
    i=b['point'];assert i not in seen and i not in fixed;seen.add(i)
    q=F(system['archived_regression_point'][b['variable']])
    assert F(b['x_coefficient'])*q==F(s['vertices'][i][0])
    assert F(b['y_coefficient'])*q==F(s['vertices'][i][1])
    assert F(b['z_exact'])==F(s['vertices'][i][2])
    rr=math.hypot(*s['vertices'][i][:2])/float(np.interp(s['vertices'][i][2],s['stations_m'],s['radii_m']))
    assert abs(rr-float(q))<1e-14
assert fixed|seen==set(range(len(p))) and len(fixed)==3328 and len(seen)==2816
assert system['selected_new_values'] is None and not system['feasibility_solved']
# Rational isolation: polynomial strictly increasing on [a,b].
a,b=F(116,1000),F(118,1000)
poly=lambda t:64*t**3-96*t**2+36*t-3
assert poly(a)<0<poly(b) and 36-192*b>0
assert 1/(8*F(1,1000))==125
# Exact determinant scaling identity with independent scalar matrix operations.
def det(g):
    return g[0][0]*(g[1][1]*g[2][2]-g[1][2]*g[2][1])-g[0][1]*(g[1][0]*g[2][2]-g[1][2]*g[2][0])+g[0][2]*(g[1][0]*g[2][1]-g[1][1]*g[2][0])
references=[[(1,0,0),(0,1,0),(0,0,1)],[(1,0,0),(0,1,0),(0,0,1),(3,4,0)],[(1,0,0),(0,1,0),(1,1,0)]]
identity_checks=0
for vectors in references:
    # The third degenerate reference uses a norm sqrt(2); replace it by (1,0,0)
    # so E is rational while retaining exact rank deficiency.
    if len(vectors)==3 and vectors[-1]==(1,1,0):vectors=vectors[:-1]+[(1,0,0)]
    for scale in (F(1),F(1,1000),F(1,1000000)):
        v=[[F(x)*scale for x in row] for row in vectors];m=len(v)
        E=sum(F(math.isqrt(sum(x*x for x in row)))*scale for row in vectors)
        G=[[sum(row[i]*row[j] for row in v) for j in range(3)] for i in range(3)]
        direct=det([[x/(E/m)**2 for x in row] for row in G])/8
        assert 125*m**6*det(G)/E**6-1==1000*direct-1
        identity_checks+=1
# Squaring alone cannot admit reversed normals or positive plane scores.
assert not (F(-1)>0 and F(1)-b>=0)
assert not (F(1)<0 and F(1)-F(1,1000000)**2>=0)
helper=Path('twins/bionic-turbo-f1/evidence/airflow-neighbour-constraints-20261013/verify_neighbours.py')
assert sha(helper)=='c98cbf017a3647fc7447e5871e26684dc3d596016168bb6b0143f2c5bd16de6c'
tree=ast.parse(helper.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('face_moments','tetra_moments')],type_ignores=[]),str(helper),'exec'))
raw=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
registry=defaultdict(list);polys=[];centres=[];geoms=[]
for cell,block in enumerate(s['blocks']):
    faces=[]
    for template in raw:
        face=[]
        for k in template:
            if not face or face[-1]!=block[k]:face.append(block[k])
        if face[-1]==face[0]:face.pop()
        if len(face)<3:continue
        faces.append(face);registry[tuple(sorted(face))].append((cell,face))
    ids=sorted(set(block));mapping={v:i for i,v in enumerate(ids)}
    c,v=tetra_moments(p[ids],[[mapping[x] for x in f] for f in faces]);assert v>0
    polys.append(faces);centres.append(c);geoms.append([face_moments(p[f]) for f in faces])
rows={(int(r['owner']),int(r['neighbour'])):r for r in csv.DictReader((w/'angle-predicates.csv').open())};n=0;rejected=0
for pair in registry.values():
    if len(pair)==1:continue
    (owner,face),(neighbour,_)=pair
    key=(owner,neighbour);r=rows[key];S=face_moments(p[face])[1];delta=centres[neighbour]-centres[owner];D=float(S@delta)
    assert D>0
    ratio=D*D/float(S@S)/float(delta@delta)
    # Conservative isolating interval, no transcendental angle evaluation.
    assert ratio<float(a) or ratio>float(b)
    bad=ratio<float(a);assert bad==(r['rejected']=='True');rejected+=bad;n+=1
assert n==len(rows)==13696 and rejected==1024
dr=list(csv.DictReader((w/'determinant-predicates.csv').open()));pr=iter(csv.DictReader((w/'plane-predicates.csv').open()));count=0
for cell,(faces,ca) in enumerate(zip(polys,geoms)):
    areas=[S for f,(_,S) in zip(faces,ca) if len(registry[tuple(sorted(f))])==2];E=sum(float(np.linalg.norm(x)) for x in areas);m=len(areas)
    G=sum(np.outer(S,S) for S in areas);residual=125*m**6*float(G[0]@np.cross(G[1],G[2]))/E**6-1
    assert int(dr[cell]['cell'])==cell and int(dr[cell]['internal_faces'])==m
    assert abs(residual-float(dr[cell]['scaled_determinant_residual']))<1e-9 and (residual<0)==(dr[cell]['rejected']=='True')
    # Primary and secondary enumerate faces differently; compare the full sorted
    # collection per cell instead of treating local face numbers as global labels.
    expected=[]
    for i,(ci,S) in enumerate(ca):
        for j,(cj,_) in enumerate(ca):
            if i==j:continue
            d=cj-ci;L=float(S@d);q=L*L/float(S@S)/float(d@d)-1e-12
            expected.append((L<0,q,not(L<0 and q>=0)))
    actual=[]
    for _ in expected:
        r=next(pr);assert int(r['cell'])==cell;actual.append((r['negative_sign']=='True',float(r['scaled_plane_residual']),r['rejected']=='True'));count+=1
    expected.sort();actual.sort()
    assert all(x[0]==y[0] and x[2]==y[2] and abs(x[1]-y[1])<1e-10 for x,y in zip(expected,actual))
assert next(pr,None) is None and count==138240
out=dict(reader_sha256=sha(Path(__file__)),all_source_payloads_verified=True,all_bindings_verified=True,exact_rational_determinant_identity_checks=identity_checks,kappa_root_isolated_rationally=True,angle_classification_without_acos_atan=True,angle_faces=n,rejected_angles=rejected,cell_determinants=len(dr),ordered_plane_pairs=count,only_archived_ratios_evaluated=True,feasibility_solved=False,candidate_created=False,native_executed=False)
(w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
