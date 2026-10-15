"""Exact coefficient cancellations, source correspondence and analytic controls."""
import hashlib,json,tarfile
from fractions import Fraction as F
from pathlib import Path
from collections import defaultdict
from centred import I,b,face,cell

def main():
 w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
 assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
 member='OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshTools.C'
 with tarfile.open(archive) as t:data=t.extractfile(member).read()
 assert hashlib.sha256(data).hexdigest()=='db2868dc5ccb66f8e3e8c4b919afb8abf8bb3b0fc290c704f9ad4c65b645a712'
 source=data.decode()
 tokens=['sumAc += a*c;','fCtrs[facei] = (1.0/3.0)*sumAc/sumA;','solveScalar pyr3Vol = fA & (fc - cEst[own[facei]]);','solveVector pc = (3.0/4.0)*fc + (1.0/4.0)*cEst[own[facei]];','cellCtrs[own[facei]] += pyr3Vol*pc;','cellCtrs[celli] /= cellVols[celli];']
 assert all(x in source for x in tokens)
 identities=[]
 # Expand both numerator expressions in independent formal weight/coordinate symbols.
 for n in (3,4):
  terms=defaultdict(F)
  for i in range(n):
   for symbol in ('a'+str(i),'a'+str((i+1)%n)):
    terms[(i,symbol)]+=1;terms[(i,symbol)]-=1
   terms[(i,'c')]+=1;terms[(i,'c')]+=2;terms[(i,'c')]-=3
  assert all(x==0 for x in terms.values());identities.append(dict(kind='face',terms=n,zero_coefficients=len(terms)))
 for n in (5,6):
  terms=defaultdict(F)
  for i in range(n):
   terms[(i,'f'+str(i))]+=3;terms[(i,'f'+str(i))]-=3
   terms[(i,'s')]+=1;terms[(i,'s')]+=3;terms[(i,'s')]-=4
  assert all(x==0 for x in terms.values());identities.append(dict(kind='cell',terms=n,zero_coefficients=len(terms)))
 # Signed weights are permitted by the identity; these are algebraic references, not candidate geometry.
 for weights in ((F(-2),F(3),F(4)),(F(1,3),F(-1,5),F(7,11))):
  values=(F(2),F(-5),F(3));seed=F(7,13);V=sum(weights)
  assert sum(v*(3*c+seed)/4 for v,c in zip(weights,values))/V == seed+3*sum(v*(c-seed) for v,c in zip(weights,values))/(4*V)
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
 controls=[]
 for scale in (F(1),F(1,1000),F(1,1000000)):
  for kind in ('cube','pyramid'):
   vertices=((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)) if kind=='cube' else ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(F(1,2),F(1,2),1))
   fs=templates if kind=='cube' else ((0,3,2,1),(0,1,4),(1,2,4),(2,3,4),(3,0,4))
   points=[[I(scale*x) for x in p] for p in vertices];polygons=[[points[i] for i in f] for f in fs]
   expected=[scale/2,scale/2,scale/(2 if kind=='cube' else 4)];volume=scale**3/(1 if kind=='cube' else 3)
   for facefn,cellfn in ((face,cell),(b.face,b.cell)):
    c,V=cellfn([facefn(q) for q in polygons])
    assert F(V.lo,b.Q)<=volume<=F(V.hi,b.Q)
    assert all(F(x.lo,b.Q)<=e<=F(x.hi,b.Q) for x,e in zip(c,expected))
   # Warped symmetric quadrilateral: equal fan weights, centre zero, area (0,0,4s^2).
   saddle=[[I(scale*x) for x in p] for p in ((-1,-1,1),(1,-1,-1),(1,1,1),(-1,1,-1))]
   cf,S=face(saddle)
   assert all(x.lo<=0<=x.hi for x in cf)
   assert all(F(x.lo,b.Q)<=e<=F(x.hi,b.Q) for x,e in zip(S,(0,0,4*scale**2)))
   controls.append(dict(kind=kind,scale=str(scale)))
 out=dict(source_sha256=sha(Path(__file__)),implementation_sha256=sha(w/'centred.py'),official_archive_sha256=sha(archive),official_member=member,official_member_sha256=hashlib.sha256(data).hexdigest(),coefficient_identities=identities,signed_weight_references=2,analytic_cells=controls,warped_face_scales=3,formula_scope='exact_non_degenerate_moment_expressions_not_floating_OpenFOAM_execution',candidate_created=False)
 (w/'identity-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
