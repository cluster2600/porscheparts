"""Independent Fraction interval replay of every certified leaf; no ratio sampling."""
import csv,hashlib,json,math
from fractions import Fraction as F
from collections import defaultdict,Counter
from pathlib import Path

P=1<<192
class R:
    def __init__(self,a,b=None):
        a=F(a);b=a if b is None else F(b)
        self.a=F(math.floor(a*P),P);self.b=F(math.ceil(b*P),P)
        assert self.a<=self.b
    def __add__(x,y):
        y=r(y);return R(x.a+y.a,x.b+y.b)
    __radd__=__add__
    def __neg__(x):return R(-x.b,-x.a)
    def __sub__(x,y):return x+-r(y)
    def __rsub__(x,y):return r(y)+-x
    def __mul__(x,y):
        y=r(y);v=[a*b for a in (x.a,x.b) for b in (y.a,y.b)];return R(min(v),max(v))
    __rmul__=__mul__
    def __truediv__(x,y):
        y=r(y);assert not y.a<=0<=y.b
        return x*R(1/y.b,1/y.a)
    def square(x):
        return R(0 if x.a<=0<=x.b else min(x.a*x.a,x.b*x.b),max(x.a*x.a,x.b*x.b))
    def sqrt(x):
        assert x.b>=0
        # Floor(sqrt(n/d)*P) = isqrt(floor(n*P^2/d)).
        a=max(F(0),x.a);lo=math.isqrt(a.numerator*P*P//a.denominator)
        hi=math.isqrt(x.b.numerator*P*P//x.b.denominator)
        return R(F(lo,P),F(hi+(F(hi*hi,P*P)<x.b),P))
def r(x):return x if isinstance(x,R) else R(x)
def vadd(a,b):return [a[i]+b[i] for i in range(3)]
def vsub(a,b):return [a[i]-b[i] for i in range(3)]
def scale(a,b):return [x*b for x in a]
def inner(a,b):return sum(a[i]*b[i] for i in range(3))
def vector(a,b):return [a[(i+1)%3]*b[(i+2)%3]-a[(i+2)%3]*b[(i+1)%3] for i in range(3)]
def length(a):return sum(x.square() for x in a).sqrt()
def average(q):return [sum(p[i] for p in q)/len(q) for i in range(3)]
def polygon(q):
    centre=average(q);vectors=[];weights=[];centroids=[]
    for j in range(len(q)):
        a=q[j];b=q[(j+1)%len(q)]
        vectors.append(vector(vsub(b,a),vsub(centre,a)))
        weights.append(length(vectors[-1]));centroids.append(scale(vadd(vadd(a,b),centre),F(1,3)))
    total=sum(weights);assert total.a>0
    area=[sum(v[i] for v in vectors)/2 for i in range(3)]
    cf=[sum(weight*c[i] for weight,c in zip(weights,centroids))/total for i in range(3)]
    return cf,area

def native_moments(polygons):
    geometry=[polygon(q) for q in polygons];origin=average([g[0] for g in geometry])
    weights=[inner(area,vsub(cf,origin))/3 for cf,area in geometry]
    V=sum(weights);assert V.a>0
    centre=[sum(weight*(origin[i]+3*cf[i])/4 for weight,(cf,_) in zip(weights,geometry))/V for i in range(3)]
    return centre,V,geometry

def det_residual(areas):
    E=sum(length(a) for a in areas);assert E.a>0
    M=[[sum(a[i]*a[j] for a in areas) for j in range(3)] for i in range(3)]
    det=sum(M[0][j]*(M[1][(j+1)%3]*M[2][(j+2)%3]-M[1][(j+2)%3]*M[2][(j+1)%3]) for j in range(3))
    # Normalize each entry first; algebraically identical but different evaluation.
    scale6=E.square()*E.square()*E.square()
    return det*(125*len(areas)**6)/scale6-1

def main():
    w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    cert=json.loads((w/'certificate.json').read_text());report=json.loads((w/'readback.json').read_text())
    for path,digest in report['dependencies'].items():
        path=Path(path);assert sha(path)==digest
        for entry in json.loads(path.read_text())['files']:assert sha(Path('work')/entry['path'])==entry['sha256']
    sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
    s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text())
    u=F(cert['u']);assert u==F(sy['archived_regression_point']['u'])
    lo,hi=map(F,cert['domain']);assert lo==u and hi==F(s['radial_ratios'][-1])
    kl,kh=map(F,cert['kappa']);poly=lambda k:64*k**3-96*k**2+36*k-3
    assert F(116,1000)<=kl<kh<=F(118,1000) and poly(kl)<0<poly(kh) and 36-192*kh>0
    kappa=R(kl,kh)
    bindings={b['point']:b for b in sy['coordinate_bindings']}
    variable={i for i,b in bindings.items() if b['variable']=='v'}
    templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
    faces=[];reg=defaultdict(list)
    for c,block in enumerate(s['blocks']):
        row=[]
        for t in templates:
            f=[]
            for j in t:
                if not f or f[-1]!=block[j]:f.append(block[j])
            if f[-1]==f[0]:f.pop()
            if len(f)<3:continue
            row.append(f);reg[tuple(sorted(f))].append((c,f))
        faces.append(row)
    static=[not any(i in variable for i in b) for b in s['blocks']]
    assert sum(static)==2304 and len(variable)==1792
    assert sum(len(p)==2 and all(static[c] for c,f in p) for p in reg.values())==4224
    assert all(all(static[c] for c,f in p) for p in reg.values() if len(p)==2 and s['rotating'][p[0][0]]!=s['rotating'][p[1][0]])
    # Recover deterministic selection from archived CSVs, not certificate choices.
    fr=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/faces.csv').open()))
    for chosen in cert['selected'][:2]:
        options=[x for x in fr if x['family']=='axial/axial' and float(x['margin_m'])<0 and int(x['owner'])//2048==chosen['interval']]
        x=min(options,key=lambda x:(float(x['margin_m']),int(x['owner']),int(x['neighbour'])))
        assert (int(x['owner']),int(x['neighbour']))==(chosen['owner'],chosen['neighbour'])
        pair=reg[tuple(sorted(chosen['face']))];assert {c for c,f in pair}=={chosen['owner'],chosen['neighbour']}
    cr=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/cells.csv').open()))
    for chosen in cert['selected'][2:]:
        x=min((x for x in cr if x['stage']==chosen['stage'] and x['closure']==chosen['closure']),key=lambda x:(float(x['determinant']),int(x['cell'])))
        assert int(x['cell'])==chosen['cell']
    # Analytic cube at three scales and exact elementary interval inclusions.
    analytic=0
    for size in (F(1),F(1,1000),F(1,1000000)):
        verts=[[R(size*x),R(size*y),R(size*z)] for x,y,z in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))]
        c,V,g=native_moments([[verts[j] for j in t] for t in templates])
        assert V.a<=size**3<=V.b and all(x.a<=size/2<=x.b for x in c);analytic+=1
    for a,b in ((F(-3),F(2)),(F(1,3),F(2,3)),(F(1,10**15),F(2,10**15))):
        x=R(a,b);sq=x.square();root=sq.sqrt()
        assert sq.a<=min(a*a,b*b) and sq.b>=max(a*a,b*b)
        assert root.a*root.a<=sq.a and root.b*root.b>=sq.b;analytic+=1
    # No new v point. Every replay takes the full certified box.
    def point(i,v):
        b=bindings.get(i)
        if not b:return [R(F(x)) for x in s['vertices'][i]]
        t=R(u) if b['variable']=='u' else v
        return [R(F(b['x_coefficient']))*t,R(F(b['y_coefficient']))*t,R(F(b['z_exact']))]
    def replay(chosen,a,b):
        v=R(a,b);cells=[chosen['owner'],chosen['neighbour']] if chosen['kind']=='angle' else [chosen['cell']]
        data={}
        for c in cells:
            anchor=[R(F(x)) for x in s['vertices'][s['blocks'][c][0]]]
            centre,V,geometry=native_moments([[vsub(point(i,v),anchor) for i in f] for f in faces[c]])
            data[c]=(vadd(centre,anchor),geometry)
        if chosen['kind']=='determinant':
            c=chosen['cell'];areas=[g[1] for f,g in zip(faces[c],data[c][1]) if len(reg[tuple(sorted(f))])==2]
            return None,det_residual(areas)
        c,d=chosen['owner'],chosen['neighbour'];key=tuple(sorted(chosen['face']))
        S=next(g[1] for f,g in zip(faces[c],data[c][1]) if tuple(sorted(f))==key)
        delta=vsub(data[d][0],data[c][0]);D=inner(delta,S)
        denominator=sum(x.square() for x in delta)*sum(x.square() for x in S)
        assert denominator.a>0
        return D,D.square()/denominator-kappa
    end=lo;counts=Counter();verified_claims=0
    for leaf in cert['leaves']:
        a,b=F(leaf['lower']),F(leaf['upper']);assert a==end and a<b;end=b
        depth=leaf['depth'];assert 0<=depth<=12 and (b-a)==(hi-lo)/2**depth
        assert ((a-lo)/(hi-lo)*2**depth).denominator==1
        counts[leaf['status']]+=1
        if leaf['status']=='excluded':
            witness=next(i for i,x in enumerate(leaf['checks']) if x['status']=='excluded')
            D,res=replay(cert['selected'][witness],a,b)
            assert (D is not None and D.b<=0) or res.b<0;verified_claims+=1
        elif leaf['status']=='selected_subset_only':
            for chosen in cert['selected']:
                D,res=replay(chosen,a,b);assert res.a>=0 and (D is None or D.a>0);verified_claims+=1
        else:assert leaf['status']=='unresolved' and depth==12
    assert end==hi and dict(counts)==report['leaf_counts']
    out=dict(source_sha256=sha(Path(__file__)),certificate_sha256=sha(w/'certificate.json'),fraction_interval_bits=192,analytic_checks=analytic,all_leaf_coverage_verified=True,all_exclusion_and_selected_pass_claims_verified=verified_claims,leaf_counts=dict(counts),new_point_evaluated=False,solution_accepted=False,geometry_and_remaining_constraints_unresolved=True)
    (w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
