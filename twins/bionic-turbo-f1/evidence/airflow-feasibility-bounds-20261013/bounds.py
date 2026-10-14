"""Outward dyadic interval exclusions; no pointwise ratio search."""
import csv, hashlib, json, math
from fractions import Fraction as F
from collections import defaultdict, Counter
from pathlib import Path

BITS=160; Q=1<<BITS
class I:
    def __init__(self,lo,hi=None,raw=False):
        if raw:self.lo,self.hi=lo,hi
        else:
            f=F(lo);self.lo=f.numerator*Q//f.denominator;self.hi=-((-f.numerator*Q)//f.denominator)
        assert self.lo<=self.hi
    def __add__(a,b):
        b=cv(b);return I(a.lo+b.lo,a.hi+b.hi,True)
    __radd__=__add__
    def __neg__(a):return I(-a.hi,-a.lo,True)
    def __sub__(a,b):return a+-cv(b)
    def __rsub__(a,b):return cv(b)+-a
    def __mul__(a,b):
        b=cv(b);p=[x*y for x in (a.lo,a.hi) for y in (b.lo,b.hi)]
        return I(min(p)//Q,-((-max(p))//Q),True)
    __rmul__=__mul__
    def __truediv__(a,b):
        b=cv(b)
        if b.lo<=0<=b.hi:raise ZeroDivisionError
        p=[F(x*Q,y) for x in (a.lo,a.hi) for y in (b.lo,b.hi)]
        return I(math.floor(min(p)),math.ceil(max(p)),True)
    def sq(a):
        p=[a.lo*a.lo,a.hi*a.hi];lo=0 if a.lo<=0<=a.hi else min(p)
        return I(lo//Q,-((-max(p))//Q),True)
    def root(a):
        if a.hi<0:raise ValueError('negative norm')
        lo=math.isqrt(max(0,a.lo)*Q);n=a.hi*Q;hi=math.isqrt(n)
        return I(lo,hi+(hi*hi<n),True)
    def pair(a):return [str(F(a.lo,Q)),str(F(a.hi,Q))]
def cv(x):return x if isinstance(x,I) else I(x)
def plus(a,b):return [x+y for x,y in zip(a,b)]
def minus(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,t):return [x*t for x in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):return sum(x.sq() for x in a).root()
def mean(a):return [sum(x[k] for x in a)/len(a) for k in range(3)]
def face(q):
    seed=mean(q);area=[I(0) for _ in range(3)];moment=area[:];weight=I(0)
    for a,b in zip(q,q[1:]+q[:1]):
        cr=cross(minus(b,a),minus(seed,a));mag=norm(cr)
        area=plus(area,cr);weight+=mag
        moment=plus(moment,mul(plus(plus(a,b),seed),mag/3))
    if weight.lo<=0:raise ZeroDivisionError
    return [x/weight for x in moment],mul(area,F(1,2))
def cell(geoms):
    seed=mean([c for c,a in geoms]);vol=I(0);mom=[I(0) for _ in range(3)]
    for c,a in geoms:
        v=dot(a,minus(c,seed))/3;vol+=v;mom=plus(mom,mul(plus(mul(c,3),seed),v/4))
    if vol.lo<=0:raise ZeroDivisionError
    return [x/vol for x in mom],vol
def determinant(areas):
    m=len(areas);E=sum(norm(a) for a in areas)
    if E.lo<=0:raise ZeroDivisionError
    g=[[sum(a[i]*a[j] for a in areas) for j in range(3)] for i in range(3)]
    det=dot(g[0],cross(g[1],g[2]));e2=E.sq();e6=e2*e2*e2
    return 125*m**6*det/e6-1

def main():
    w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    dependencies={}
    for name in ('buffered-transition','neighbour-constraints','joint-constraints'):
        p=Path(f'work/bionic-airflow-delivery-20261013-{name}/file-manifest.json')
        dependencies[str(p)]=sha(p)
        for r in json.loads(p.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
    sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
    s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text())
    u=F(sy['archived_regression_point']['u']);end=F(s['radial_ratios'][-1])
    bindings={r['point']:r for r in sy['coordinate_bindings']};variable={i for i,r in bindings.items() if r['variable']=='v'}
    faces=[];registry=defaultdict(list)
    for c,b in enumerate(s['blocks']):
        n=4 if s['stages'][c]=='buffer' else 3;lo,hi=b[:n],b[4:4+n]
        fs=[lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)]
        faces.append(fs)
        for f in fs:registry[tuple(sorted(f))].append((c,f))
    changing=[bool(set(b)&variable) for b in s['blocks']]
    fixed_pairs=[];moving_pairs=[]
    for pairs in registry.values():
        if len(pairs)==2:(moving_pairs if any(changing[c] for c,f in pairs) else fixed_pairs).append(pairs)
    assert sum(not x for x in changing)==2304 and len(fixed_pairs)==4224 and len(moving_pairs)==9472
    assert all(not changing[c] for pairs in fixed_pairs for c,f in pairs)
    mrf=[pairs for pairs in registry.values() if len(pairs)==2 and s['rotating'][pairs[0][0]]!=s['rotating'][pairs[1][0]]]
    assert len(mrf)==384 and all(not changing[c] for pairs in mrf for c,f in pairs)
    rows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/faces.csv').open()))
    grouped=defaultdict(list)
    for r in rows:
        if r['family']=='axial/axial' and float(r['margin_m'])<0:grouped[int(r['owner'])//2048].append(r)
    selected=[]
    for interval,rr in sorted(grouped.items()):
        r=min(rr,key=lambda r:(float(r['margin_m']),int(r['owner']),int(r['neighbour'])))
        a,b=int(r['owner']),int(r['neighbour'])
        f=next(f for f in faces[a] if any(c==b for c,_ in registry[tuple(sorted(f))]))
        selected.append(dict(kind='angle',owner=a,neighbour=b,face=f,interval=interval))
    rows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/cells.csv').open()))
    for stage in ('axial','buffer'):
        for closure in ('lower','upper'):
            r=min((r for r in rows if r['stage']==stage and r['closure']==closure),key=lambda r:(float(r['determinant']),int(r['cell'])))
            selected.append(dict(kind='determinant',cell=int(r['cell']),stage=stage,closure=closure))
    assert len(selected)==6
    # Exact root bracket; polynomial monotonicity verified on initial enclosure.
    poly=lambda k:64*k**3-96*k**2+36*k-3
    kl,kh=F(116,1000),F(118,1000);assert poly(kl)<0<poly(kh) and 36-192*kh>0
    for _ in range(80):
        mid=(kl+kh)/2
        if poly(mid)<0:kl=mid
        else:kh=mid
    kap=I(I(kl).lo,I(kh).hi,True)
    needed=sorted({x for r in selected for x in ([r['owner'],r['neighbour']] if r['kind']=='angle' else [r['cell']])})
    # Cell-local translations reduce interval dependency without changing moments.
    def point(i,v):
        r=bindings.get(i)
        if r:
            t=I(u) if r['variable']=='u' else v
            return [I(F(r['x_coefficient']))*t,I(F(r['y_coefficient']))*t,I(F(r['z_exact']))]
        return [I(F(x)) for x in s['vertices'][i]]
    def evaluate(l,h):
        v=I(I(l).lo,I(h).hi,True);geo={};cs={};vs={};origins={}
        for c in needed:
            origin=[I(F(x)) for x in s['vertices'][s['blocks'][c][0]]];origins[c]=origin
            try:
                geo[c]=[face([minus(point(i,v),origin) for i in f]) for f in faces[c]]
                centre,volume=cell(geo[c]);cs[c]=plus(centre,origin);vs[c]=volume
            except ZeroDivisionError:pass
        results=[]
        for r in selected:
            try:
                if r['kind']=='angle':
                    a,b=r['owner'],r['neighbour'];delta=minus(cs[b],cs[a]);S=geo[a][faces[a].index(r['face'])][1]
                    d=dot(delta,S);den=dot(delta,delta)*dot(S,S)
                    if den.lo<=0:raise ZeroDivisionError
                    res=d.sq()/den-kap
                    status='excluded' if d.hi<=0 or res.hi<0 else ('selected_pass' if d.lo>0 and res.lo>=0 else 'unknown')
                    results.append(dict(status=status,D=d.pair(),residual=res.pair()))
                else:
                    c=r['cell'];assert c in cs
                    a=[geom[1] for f,geom in zip(faces[c],geo[c]) if len(registry[tuple(sorted(f))])==2]
                    res=determinant(a);status='excluded' if res.hi<0 else ('selected_pass' if res.lo>=0 else 'unknown')
                    results.append(dict(status=status,residual=res.pair()))
            except (ZeroDivisionError,KeyError,AssertionError):results.append(dict(status='unknown',reason='enclosure_contains_singular_geometry'))
        return results
    leaves=[];visits=0
    def visit(l,h,depth):
        nonlocal visits
        visits+=1;rr=evaluate(l,h)
        if any(r['status']=='excluded' for r in rr):status='excluded'
        elif all(r['status']=='selected_pass' for r in rr):status='selected_subset_only'
        elif depth==12:status='unresolved'
        else:
            mid=(l+h)/2;visit(l,mid,depth+1);visit(mid,h,depth+1);return
        leaves.append(dict(lower=str(l),upper=str(h),depth=depth,status=status,checks=rr))
    visit(u,end,0)
    assert visits<=8191 and leaves[0]['lower']==str(u) and leaves[-1]['upper']==str(end)
    assert all(a['upper']==b['lower'] for a,b in zip(leaves,leaves[1:]))
    out=dict(bits=BITS,max_depth=12,visited=visits,domain=[str(u),str(end)],u=str(u),kappa=[str(kl),str(kh)],selected=selected,leaves=leaves,feasible_solution=False,candidate_created=False,native_executed=False)
    (w/'certificate.json').write_text(json.dumps(out,indent=2)+'\n')
    counts=Counter(r['status'] for r in leaves);widths={k:str(sum((F(r['upper'])-F(r['lower']) for r in leaves if r['status']==k),F(0))/(end-u)) for k in counts}
    dependency=dict(fixed_cells=2304,variable_cells=sum(changing),fixed_angles=len(fixed_pairs),variable_angles=len(moving_pairs),fixed_mrf_angles=384,variable_points=len(variable),fixed_points=len(s['vertices'])-len(variable),constant_planes=sum(len(f)*(len(f)-1) for c,f in enumerate(faces) if not changing[c]),variable_planes=sum(len(f)*(len(f)-1) for c,f in enumerate(faces) if changing[c]))
    summary=dict(dependencies=dependencies,source_sha256=sha(Path(__file__)),certificate_sha256=sha(w/'certificate.json'),slice_dependencies=dependency,visited=visits,leaf_counts=dict(counts),relative_widths=widths,all_other_constraints_unresolved=True,feasible_solution=False,new_ratio_selected=False)
    (w/'readback.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
