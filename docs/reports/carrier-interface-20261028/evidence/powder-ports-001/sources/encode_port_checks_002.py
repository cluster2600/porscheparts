import gzip,hashlib,json
from pathlib import Path
import numpy as np
w=Path('work/carrier-interface-20261028');out=w/'cgal-port-inputs-001';assert not out.exists();out.mkdir();records={};sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v,f):
 p=out/(name+'.mesh64')
 with p.open('w')as stream:
  stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')
 with p.open()as stream:
  nv,nf=map(int,stream.readline().split());rv=np.loadtxt(stream,max_rows=nv);rf=np.loadtxt(stream,dtype=np.uint64)
 assert nv==len(v)and nf==len(f)and np.array_equal(rv,v)and np.array_equal(rf,f);records[name]=dict(sha256=sha(p),vertices=nv,triangles=nf,exact_binary64_and_index_roundtrip=True)
voids=[];tools=[]
for i in range(8):
 rank=i//2;sign='positive'if i%2==0 else'negative';z=np.load(w/f'meshlib-seed-p10-r{rank}-h0125-004/{sign}.npz');voids.append((z['vertices'],z['triangles']));z=np.load(w/f'ported-carrier-001/tool-{i}.npz');tools.append((z['vertices'],z['triangles']));write(f'tool-{i}',*tools[-1]);write(f'own-{i}',*voids[-1]);z=np.load(w/f'ported-carrier-001/frustum-{i}.npz');write(f'frustum-{i}',z['vertices'],z['triangles'])
for roster,name in [(voids,'other-voids'),(tools,'other-tools')]:
 for i in range(8):
  vertices=[];faces=[];offset=0
  for j,(v,f)in enumerate(roster):
   if j==i:continue
   vertices.append(v);faces.append(f+offset);offset+=len(v)
  write(f'{name}-{i}',np.vstack(vertices),np.vstack(faces))
z=np.load(w/'ported-seams-002/candidate.npz');write('ported-seams',z['vertices'],z['triangles']);reference=Path('parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/picogk-R2-study/surface.mesh64.gz');raw=gzip.decompress(reference.read_bytes());assert hashlib.sha256(raw).hexdigest()=='396161993b35f708fdd1e527f875aff60daf8c79031dc9a39c42891a9c1ae1a0';(out/'reference.mesh64').write_bytes(raw);records['reference']=dict(sha256=sha(out/'reference.mesh64'),exact_frozen_reference_bytes=True)
for r in json.loads((w/'powder-port-routing-003/assessment.json').read_text())['selected']:
 values=np.array(r['start_mm']+r['direction']+[r['flare_length_mm'],r['length_mm']]);p=out/f"params-{r['network']}.txt";np.savetxt(p,values[None,:],fmt='%.17g');assert np.array_equal(np.loadtxt(p),values)
(out/'assessment.json').write_text(json.dumps(dict(scope='Exact transports for independent port checks',files=records,manufacturing_authorized=False),indent=2)+'\n');print(json.dumps(dict(exact_transports=len(records))))
