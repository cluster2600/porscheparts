import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
w=Path('work/carrier-interface-20261028');out=w/'cgal-ported-seams-input-002';assert not out.exists();out.mkdir();source=w/'ported-seams-002/candidate.npz';z=np.load(source);v,f=z['vertices'],z['triangles'];p=out/'ported.mesh64'
with p.open('w')as stream:
 stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')
with p.open()as stream:
 nv,nf=map(int,stream.readline().split());rv=np.loadtxt(stream,max_rows=nv);rf=np.loadtxt(stream,dtype=np.uint64)
assert np.array_equal(rv,v)and np.array_equal(rf,f);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(out/'assessment.json').write_text(json.dumps(dict(input_sha256=sha(source),output_sha256=sha(p),exact_coordinate_and_index_roundtrip=True,manufacturing_authorized=False),indent=2)+'\n')
subprocess.run([sys.executable,str(w/'cgal-self-check-002/run_check.py'),'--first',str(w/'cgal-self-inputs-001/reconstructed10.mesh64'),'--second',str(p),'--binary',str(w/'cgal-self-compile-002/output/check-hausdorff'),'--output',str(w/'cgal-ported-seams-check-002')],check=True)
