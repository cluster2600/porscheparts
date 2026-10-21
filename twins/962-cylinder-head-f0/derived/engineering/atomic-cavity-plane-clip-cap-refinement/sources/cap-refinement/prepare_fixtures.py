"""Write four literal synthetic cap inputs only; never execute the C++ refiner."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
OUT=HERE/'fixtures'
if OUT.exists() or OUT.is_symlink():
    raise ValueError('Preserve existing fixture data')

def annulus(r=2,midpoints=False):
    corners=[(-r,-r),(r,-r),(r,r),(-r,r)]
    inner=[(-1,-1),(1,-1),(1,1),(-1,1)]
    if not midpoints:
        points=[(*p,0) for p in corners+inner]
        faces=[]
        for i in range(4):
            j=(i+1)%4
            faces.extend([(i,4+j,j),(i,4+i,4+j)])
    else:
        outer=[]
        for i,p in enumerate(corners):
            q=corners[(i+1)%4]
            outer.extend([p,((p[0]+q[0])//2,(p[1]+q[1])//2)])
        points=[(*p,0) for p in outer+inner];faces=[]
        for i in range(4):
            a=2*i;m=a+1;b=2*((i+1)%4);u=8+i;v=8+(i+1)%4
            faces.extend([(a,u,m),(m,u,v),(m,v,b)])
    return points,faces

def inspect(points,faces):
    chain={};edges={};links=set();area=F(0);poor=[]
    for fid,t in enumerate(faces):
        a,b,c=[tuple(map(F,points[v][:2])) for v in t]
        det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if det>=0:raise ValueError('Literal winding')
        area-=det/2
        lengths=[sum((p[k]-q[k])**2 for k in (0,1))for p,q in [(a,b),(b,c),(c,a)]]
        if 2523*det*det<sum(lengths)**2:poor.append(fid)
        for i,x in enumerate(t):
            y=t[(i+1)%3];edge=tuple(sorted((x,y)));edges[edge]=edges.get(edge,0)+1
            chain[edge]=chain.get(edge,0)+(1 if x<y else-1)
            links.add(x)
    boundary={e:w for e,w in chain.items()if w}
    assert all(n in (1,2)for n in edges.values())and all(abs(x)==1for x in boundary.values())
    assert len(points)-len(edges)+len(faces)==0and len(links)==len(points)and len(boundary)==len(points)
    return dict(vertices=len(points),faces=len(faces),Euler=0,cap_area_mm2=str(area),
                oriented_boundary_edges=[[*e,w]for e,w in sorted(boundary.items())],
                strict_exact_poor_face_ids=poor)

def surface(points,faces):
    return b'962SURF1'+struct.pack('<QQ',len(points),len(faces))+b''.join(struct.pack('<ddd',*p)for p in points)+b''.join(struct.pack('<QQQ',*f)for f in faces)
ordinary=annulus()
attempt=annulus(8,True)
cases={
 'ordinary':(ordinary,[(0,0)],[5],dict(intended_returncode=0,Steiner_insertion_required=False)),
 'interior-attempt':(attempt,[(0,0)],[6],dict(intended_returncode=None,allowed_declared_geometric_outcomes=[0,3],
     actual_Steiner_insertion_count=None,
     expectation='A refinement request is intended; no actual insertion or quality success is assumed. Preserve zero-insertion and refusal outcomes.')),
 'invalid-fixed-association':(ordinary,[(0,0)],[8],dict(intended_returncode=3,expected_stage='original_annular_cap',no_exports=True)),
 'mapped-loop-refusal':(ordinary,[(0,0),(1,0),(3,0)],[5],dict(intended_returncode=3,expected_stage='mapped_annulus',no_exports=True))
}
OUT.mkdir();records={}
for name,((points,faces),mapping,fixed,expectation)in cases.items():
    data={name+'.bin':surface(points,faces),
          name+'.map.u64':b''.join(struct.pack('<QQ',*row)for row in mapping),
          name+'.fixed.u64':b''.join(struct.pack('<Q',x)for x in fixed)}
    for filename,content in data.items():
        with(OUT/filename).open('xb')as f:f.write(content)
    records[name]=dict(input=inspect(points,faces),map_rows=mapping,
        map_identity_rows=sum(a==b for a,b in mapping),map_nonidentity_rows=sum(a!=b for a,b in mapping),fixed_face_ids=fixed,
        expected=expectation,files={n:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())for n,v in data.items()},
        literal_points_mm=points,literal_oriented_faces=faces,
        positive_output_checks='All original boundary coordinates and segments exact; exact fixed cell; new points interior with sentinel; complete negative-Z annular domain and quality. No guessed CDT diagonal or new-point count.')
assert records['ordinary']['input']['cap_area_mm2']=='12'
assert records['interior-attempt']['input']['cap_area_mm2']=='252'
with(HERE/'fixture-expectations.json').open('x')as f:
    json.dump(dict(schema='962-cap-refinement-literal-fixtures/v1',cases=records,
        native_execution_performed=False,claimed_Steiner_success=False,
        ordinary_source_fixture_not_head_metrology=True),f,indent=2);f.write('\n')
print('Wrote literal fixture data only; C++ and unit/native tests remain unrun.')
