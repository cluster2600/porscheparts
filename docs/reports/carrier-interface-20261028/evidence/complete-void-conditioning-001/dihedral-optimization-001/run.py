from optimize import optimize
from pathlib import Path
from fractions import Fraction as Q
import numpy as np,json,hashlib,struct,sys,time
source=Path(sys.argv[1]);audit=Path(sys.argv[2]);out=Path(sys.argv[3]);assert not out.exists();root=Path(__file__).resolve().parent;start=time.monotonic()
assert json.loads((root/'controls.json').read_text())['status']=='signed_dihedral_controls_passed'
a=json.loads(audit.read_text());sourcehash=hashlib.sha256(source.read_bytes()).hexdigest();assert sourcehash==a['input_sha256']
severe=[e['vertices']for e in a['most_reentrant_edges']if e['normal_turn_degrees']<-45];assert len(severe)==a['reentrant_edges_above_degrees']['45'];seeds=sorted({i for edge in severe for i in edge})
with np.load(source,allow_pickle=False)as z:v=z['vertices'];f=z['triangles']
h=hashlib.sha256(struct.pack('<QQ',len(v),len(f)));h.update(v.astype('<f8').tobytes());h.update(f.astype('<u8').tobytes());sourcebinaryhash=h.hexdigest()
receipt=json.loads((source.parent.parent/'proof-terminal.json').read_text());assert receipt['returncode']==0 and receipt['candidate_sha256']==sourcebinaryhash
assert json.loads((source.parent/'independent-domain.json').read_text())['status']=='complete_strict_domain_containment_passed'
new,meta=optimize(v,f,seeds);assert meta['initial_patch_edges_above45']==len(severe);assert abs(meta['initial_patch_maximum_degrees']+a['most_reentrant_edges'][0]['normal_turn_degrees'])<1e-6
changed=np.flatnonzero(np.any(new!=v,axis=1));squared=max(sum((Q(float(new[i,k]))-Q(float(v[i,k])))**2 for k in range(3))for i in changed);assert squared<Q('0.005')**2
bound=float(np.nextafter(np.sqrt(np.nextafter(float(squared),np.inf)),np.inf));assert bound<.005
out.mkdir();d=out/'decoded-001';d.mkdir();np.savez(d/'candidate.npz',vertices=new,triangles=f);binary=d/'candidate.meshbin';binary.write_bytes(struct.pack('<QQ',len(new),len(f))+new.astype('<f8').tobytes()+f.astype('<u8').tobytes())
meta.update(status='direct_dihedral_candidate_independent_checks_pending',elapsed_seconds=time.monotonic()-start,source_npz_sha256=sourcehash,source_binary_sha256=sourcebinaryhash,source_domain_status='complete_strict_domain_containment_passed',changed_vertices=len(changed),all_triangle_indices_unchanged=True,maximum_squared_displacement_rational=str(squared),complete_symmetric_surface_bound_mm=bound,certificate='Exact squared Euclidean vertex displacements are strictly below decimal 0.005 mm squared. Identical triangle barycentric coordinates pair both complete surfaces.',output_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),output_npz_sha256=hashlib.sha256((d/'candidate.npz').read_bytes()).hexdigest(),method_sources={name:hashlib.sha256((root/name).read_bytes()).hexdigest()for name in ['optimize.py','run.py','controls.py']});(out/'assessment.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:v for k,v in meta.items()if k!='history'}))
