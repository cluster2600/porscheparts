"""Additional fixed-current-case proof; original numerical gates remain mandatory."""
import hashlib,json
from fractions import Fraction as Q
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def metadata(plan,template):
 need(plan['current_event_proof']==template['plan']['current_event_proof'],'Foreign current event proof')
 need(plan['vertex_maps']==template['plan']['vertex_maps'],'Current fixed vertex map differs')
 need(plan['identity_rebinding']['canonical_arrays_sha256']==template['canonical_arrays_sha256'],'Current canonical authority differs')
 need(plan['frozen_shape_drift_limit_mm']==template['plan']['frozen_shape_drift_limit_mm'],'Original bound changed')
 need(plan['current_event_proof']['retained_changed_face_count']==4,'Fixed current24af four-unknown authority required')
def verify(np,first,patch,raw,plan,first_path,raw_path,template_path,template_sha256):
 need(sha(template_path)==template_sha256,'Current template changed');template=json.loads(Path(template_path).read_text());metadata(plan,template)
 need(plan['identity_rebinding']['template_sha256']==template_sha256,'Wrong template source')
 need(sha(first_path)==plan['input_sha256']==template['plan']['input_sha256'] and sha(raw_path)==plan['original_float_sha256']==template['plan']['original_float_sha256'],'Current mesh bytes differ')
 # The unchanged original canonical-array formula, with NumPy passed explicitly.
 def arrays_identity(path):
    """All arrays, names, dtypes, shapes and C-order bytes; independent of ZIP order."""
    digest = hashlib.sha256()
    with np.load(path, allow_pickle=False) as archive:
        for name in sorted(archive.files):
            array = archive[name]
            if array.dtype.hasobject:
                raise ValueError('Object arrays are forbidden')
            header = json.dumps([name, array.dtype.str, list(array.shape)], separators=(',', ':')).encode()
            payload = np.ascontiguousarray(array).tobytes()
            digest.update(len(header).to_bytes(8, 'big')); digest.update(header)
            digest.update(len(payload).to_bytes(8, 'big')); digest.update(payload)
    return digest.hexdigest()
 for role,path in [('first_snap',first_path),('original_raw',raw_path)]:need(arrays_identity(path)==template['canonical_arrays_sha256'][role],'Whole current arrays differ')
 v,f=first['vertices'],first['faces'];need(v.dtype==np.float64 and f.dtype==np.int64,'Current array types differ')
 mapping=np.arange(len(v));sources={row['source'] for row in plan['vertex_maps']}
 for row in plan['vertex_maps']:
  source,target=row['source'],row['target'];need(0<=source<len(v) and 0<=target<len(v) and source!=target and target not in sources,'Invalid current map')
  need(np.array_equal(v[source],row['source_coordinates']) and np.array_equal(v[target],row['target_coordinates']),'Current event coordinates differ');mapping[source]=target
 mapped=mapping[f];changed=np.any(mapped!=f,axis=1);keep=(mapped[:,0]!=mapped[:,1])&(mapped[:,1]!=mapped[:,2])&(mapped[:,2]!=mapped[:,0]);kept=np.flatnonzero(keep);used,inverse=np.unique(mapped[keep],return_inverse=True)
 proof=plan['current_event_proof'];need(np.flatnonzero(changed).tolist()==proof['changed_input_face_ids'],'Incomplete current changed-face ledger')
 need(np.flatnonzero(~keep).tolist()==[x['input_face'] for x in proof['deleted_positive_area_faces']],'Deleted-face ledger differs')
 need(np.flatnonzero(changed&keep).tolist()==proof['retained_changed_input_face_ids'],'Current unknown-face ledger differs')
 need(np.array_equal(patch['repair_input_face'],kept) and np.array_equal(patch['vertices'],v[used]) and np.array_equal(patch['faces'],inverse.reshape(-1,3)) and np.array_equal(patch['repair_changed_face'],changed[keep]),'Candidate is not exactly the prescribed fixed remap')
 for row in proof['deleted_positive_area_faces']:
  a,b,c=[[Q.from_float(float(x)) for x in point] for point in v[f[row['input_face']]]];u=[y-x for x,y in zip(a,b)];w=[y-x for x,y in zip(a,c)];cross=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];area2=sum(x*x for x in cross)/4
  need(area2==Q(row['area_squared_exact']) and area2>0 and row['was_positive_area'] is True,'Deleted positive-area evidence differs')
 changed_kept=changed[keep];need(int(changed_kept.sum())==4,'Current unknown count differs')
 for key in ['source','source_face']:need(np.all(patch[key][changed_kept]==-1),'Changed face retained positive source attribution')
 offsets,parents=patch['all_parent_offsets'],patch['all_parent_faces'];need(len(offsets)==len(kept)+1,'Changed CSR shape differs')
 for i in np.flatnonzero(changed_kept):need(offsets[i]==offsets[i+1],'Changed face retained positive CSR')
 return True
