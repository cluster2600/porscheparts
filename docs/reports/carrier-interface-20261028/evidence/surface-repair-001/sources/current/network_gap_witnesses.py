"""Disprove a 1 mm network-separation target using exact rational witnesses.

Sampling finds candidates; Fraction arithmetic verifies distance on the actual
binary64 point/triangle. Absence of a witness does not certify a minimum gap.
"""
import argparse,hashlib,json,math,signal,time
from fractions import Fraction
from pathlib import Path
import numpy as np


def exact_squared_distance(point,triangle):
    p=[Fraction.from_float(float(x))for x in point]
    t=[[Fraction.from_float(float(x))for x in row]for row in triangle]
    dot=lambda u,v:sum(a*b for a,b in zip(u,v))
    sub=lambda u,v:[a-b for a,b in zip(u,v)]
    distances=[]
    for i in range(3):
        edge=sub(t[(i+1)%3],t[i]);offset=sub(p,t[i]);den=dot(edge,edge)
        fraction=min(Fraction(1),max(Fraction(0),dot(offset,edge)/den))if den else Fraction(0)
        residual=[a-fraction*b for a,b in zip(offset,edge)];distances.append(dot(residual,residual))
    u=sub(t[1],t[0]);v=sub(t[2],t[0]);w=sub(p,t[0]);uu=dot(u,u);vv=dot(v,v);uv=dot(u,v);den=uu*vv-uv*uv
    if den:
        b1=(dot(w,u)*vv-dot(w,v)*uv)/den;b2=(dot(w,v)*uu-dot(w,u)*uv)/den
        if b1>=0 and b2>=0 and b1+b2<=1:
            residual=[a-b1*b-b2*c for a,b,c in zip(w,u,v)];distances.append(dot(residual,residual))
    return min(distances)


def phase_boundary_bound(vertices,faces,sign,pitch):
    """Screen all faces using a global gradient and second-order Taylor bound.

    Cauchy gives |grad(phi)| <= sqrt(3)*k. The symmetric Hessian has
    operator norm <= 4*k^2. On a triangle of diameter d, interpolation
    error is at most (4*k^2)*d^2/6. Numerical evaluation is not interval proof.
    """
    assert sign in [-1,1] and math.isfinite(pitch) and pitch>0
    k=2*math.pi/pitch;gradient=math.sqrt(3)*k;required=gradient/2
    pending=np.asarray(vertices,dtype=float)[faces];evaluated=0;lower=float('inf')
    for depth in range(11):
        evaluated+=len(pending)
        if evaluated>1000000:break
        q=pending*k
        phi=sign*(np.sin(q[:,:,0])*np.cos(q[:,:,1])+np.sin(q[:,:,1])*np.cos(q[:,:,2])+np.sin(q[:,:,2])*np.cos(q[:,:,0]))
        if phi.min()<required+1e-10:break
        diameter2=np.maximum.reduce([np.sum((pending[:,i]-pending[:,j])**2,axis=1)for i,j in [(0,1),(1,2),(2,0)]])
        bounds=phi.min(1)-(4*k*k)*diameter2/6-1e-10;accepted=bounds>=required
        if accepted.any():lower=min(lower,float(bounds[accepted].min()))
        if accepted.all():
            return dict(passed=True,minimum_signed_phi_lower_bound=lower,gradient_bound_per_mm=gradient,
                        evaluated_triangles=evaluated,subdivision_depth=depth,formal_interval_certificate=False)
        t=pending[~accepted];a,b,c=t[:,0],t[:,1],t[:,2];ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
        pending=np.concatenate([np.stack(s,axis=1)for s in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]])
    return dict(passed=False,evaluated_triangles=evaluated,subdivision_depth=depth,
                formal_interval_certificate=False,reason='Sufficient phase bound or fixed resource limit not satisfied')


def main():
    import igl
    from finite_gyroid_voids import triangle_witness_distance
    p=argparse.ArgumentParser(__doc__);p.add_argument('--networks',type=Path,nargs=4,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();a.output.mkdir();signal.alarm(180);start=time.monotonic();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
    contract=dict(scope=__doc__,minimum_cross_network_separation_mm=1.,maximum_seconds=180,
                  process_reference='https://www.materialise.com/es/academy/industrial/design-am/titanium',
                  source_sha256=sha(Path(__file__)),manufacturing_authorized=False)
    (a.output/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    for rank,directory in enumerate(a.networks):
        metadata=directory/'assessment.json';r=json.loads(metadata.read_text());assert r['rank']==rank and not r['manufacturing_authorized']
        selected={s['file']:s for s in r['selected']};data=[];identities={str(metadata):sha(metadata)}
        for name in ['positive.npz','negative.npz']:
            path=directory/name;assert sha(path)==selected[name]['sha256'];z=np.load(path)
            vertices=np.array(z['vertices']);faces=np.array(z['triangles'],dtype=np.int64)
            assert vertices.ndim==2 and vertices.shape[1]==3 and np.isfinite(vertices).all()
            assert faces.ndim==2 and faces.shape[1]==3 and faces.min()>=0 and faces.max()<len(vertices)
            assert len(np.unique(faces))==len(vertices)
            data.append((vertices,faces));identities[str(path)]=sha(path)
        witnesses=[]
        for direction in [0,1]:
            points,_=data[direction];target,faces=data[1-direction]
            d,index,_=igl.point_mesh_squared_distance(points,target,faces);candidates=np.argsort(d)[:32]
            triangles=target[faces[index[candidates]]];distances=triangle_witness_distance(points[candidates],triangles)
            best=int(distances.argmin());point=int(candidates[best]);tri=triangles[best]
            exact=exact_squared_distance(points[point],tri)
            witnesses.append(dict(source_network='positive'if direction==0 else'negative',source_vertex=point,
                                  target_face=int(index[point]),source_point_mm=points[point].tolist(),target_triangle_mm=tri.tolist(),
                                  independent_triangle_witness_distance_mm=float(distances[best]),
                                  exact_squared_distance_mm2=str(exact),exact_below_one_mm=exact<Fraction(1),
                                  displayed_distance_mm=math.sqrt(float(exact))))
        winner=min(witnesses,key=lambda r:Fraction(r['exact_squared_distance_mm2']))
        phase=[phase_boundary_bound(v,f,sign,r['pitch_mm'])for (v,f),sign in zip(data,[1,-1])]
        supported=all(b['passed']for b in phase)
        separation_bound=sum(b['minimum_signed_phi_lower_bound']for b in phase)/phase[0]['gradient_bound_per_mm']if supported else None
        rows.append(dict(rank=rank,pitch_mm=r['pitch_mm'],witness=winner,
                         separation_target_disproved=winner['exact_below_one_mm'],phase_boundary_checks=phase,
                         whole_boundary_separation_lower_bound_mm=separation_bound,phase_bound_supports_one_mm=supported,input_sha256=identities))
        print(json.dumps(dict(rank=rank,distance_upper_bound_mm=winner['displayed_distance_mm'],target_disproved=winner['exact_below_one_mm'])),flush=True)
    report=dict(status='exact_cross_network_distance_witnesses_verified',regions=rows,
                separation_target_disproved=any(r['separation_target_disproved']for r in rows),
                phase_bound_supports_one_mm=all(r['phase_bound_supports_one_mm']for r in rows),
                minimum_distance_certified=False,elapsed_seconds=time.monotonic()-start,
                source_sha256=sha(Path(__file__)),manufacturing_authorized=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0)


if __name__=='__main__':main()
