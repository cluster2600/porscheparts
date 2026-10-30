from fair import fair
from pathlib import Path
from fractions import Fraction as Q
import sys,json,numpy as np,hashlib,struct
source=Path(sys.argv[1]);audit=Path(sys.argv[2]);out=Path(sys.argv[3]);assert not out.exists();a=json.loads(audit.read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==a['input_sha256'];assert json.loads((Path(__file__).resolve().parent/'controls.json').read_text())['status']=='fixed_local_fairing_controls_passed'
with np.load(source,allow_pickle=False)as z:v=z['vertices'];f=z['triangles']
seeds=sorted({i for e in a['most_reentrant_edges']if e['normal_turn_degrees']<-45 for i in e['vertices']});assert seeds
new,meta=fair(v,f,seeds);changed=np.flatnonzero(np.any(new!=v,axis=1));bounds=[sum(abs(Q(float(new[i,k]))-Q(float(v[i,k])))for k in range(3))for i in changed];bound=max(bounds);assert bound<Q(.005)
out.mkdir();d=out/'decoded-001';d.mkdir();np.savez(d/'candidate.npz',vertices=new,triangles=f);binary=d/'candidate.meshbin';binary.write_bytes(struct.pack('<QQ',len(new),len(f))+new.astype('<f8').tobytes()+f.astype('<u8').tobytes())
meta.update(status='bounded_local_fairing_candidate_independent_checks_pending',source_sha256=a['input_sha256'],seeds=seeds,changed_vertex_ids=changed.tolist(),all_faces_unchanged=True,all_other_vertices_unchanged=True,complete_symmetric_l1_bound_rational=str(bound),complete_symmetric_bound_mm=float(bound),certificate='Exact vertex L1 distances bound both complete triangle surfaces by identical barycentric coordinates',output_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest());(out/'assessment.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:v for k,v in meta.items()if k not in ['changed_vertex_ids','seeds']}))
