"""Apply a SHA-pinned explicit branch-node plan; invalidate changed parent claims.

This is a proposed geometric repair, never a zero-area/zero-displacement claim.
Global exact intersections/topology and original-bound composed drift are gates.
"""
import argparse,hashlib,json,shutil
from fractions import Fraction as Q
from pathlib import Path
import numpy as np

def repair(input_path,original_float,plan_path,output):
    input_path,original_float,plan_path,output=map(lambda p:Path(p).resolve(),[input_path,original_float,plan_path,output])
    assert not output.exists();output.mkdir(parents=True)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    source=Path(__file__).resolve();shutil.copyfile(source,output/source.name);shutil.copyfile(plan_path,output/'plan.json')
    before={str(p):sha(p) for p in [input_path,original_float,plan_path,source,output/source.name,output/'plan.json']}
    plan=json.loads(plan_path.read_text());assert sha(input_path)==plan['input_sha256'] and sha(original_float)==plan['original_float_sha256']
    d=np.load(input_path,allow_pickle=False);origin=np.load(original_float,allow_pickle=False);v=d['vertices'];f=d['faces']
    assert v.dtype==np.float64 and f.dtype==np.int64
    remap=np.arange(len(v));keys=set(row['source'] for row in plan['vertex_maps'])
    for row in plan['vertex_maps']:
        s,t=row['source'],row['target'];assert t not in keys and s!=t
        assert np.array_equal(v[s],row['source_coordinates']) and np.array_equal(v[t],row['target_coordinates'])
        remap[s]=t
    mapped=remap[f];changed=np.any(mapped!=f,axis=1)
    keep=(mapped[:,0]!=mapped[:,1])&(mapped[:,1]!=mapped[:,2])&(mapped[:,2]!=mapped[:,0])
    kept=np.flatnonzero(keep);used,inverse=np.unique(mapped[keep],return_inverse=True);faces=inverse.reshape(-1,3)
    arrays={'vertices':v[used],'faces':faces,'repair_input_face':kept,'repair_changed_face':changed[keep]}
    raw_face=d['autorefine_input_face'][kept];assert raw_face.min()>=0 and raw_face.max()<len(origin['faces'])
    arrays['historical_snap_input_face']=raw_face
    for name in ['source_face','source']:
        arrays['historical_'+name]=d[name][kept];arrays[name]=d[name][kept].copy();arrays[name][changed[keep]]=-1
    old_offsets=origin['all_parent_offsets'];old_parents=origin['all_parent_faces']
    assert np.all(old_offsets[1:]>old_offsets[:-1]) and old_offsets[0]==0 and old_offsets[-1]==len(old_parents)
    rows=[old_parents[int(old_offsets[i]):int(old_offsets[i+1])] for i in raw_face]
    historical_counts=[len(row) for row in rows]
    arrays['historical_parent_offsets']=np.concatenate([[0],np.cumsum(historical_counts)])
    arrays['historical_parent_faces']=np.concatenate(rows)
    valid=[row if not altered else np.empty(0,dtype=np.int64) for row,altered in zip(rows,changed[keep])]
    arrays['all_parent_offsets']=np.concatenate([[0],np.cumsum([len(row) for row in valid])])
    arrays['all_parent_faces']=np.concatenate(valid)
    # The old producer map is only a native distance-search hint. It is not
    # asserted as geometric containment or an anchor for changed triangles.
    np.savetxt(output/'distance-search-hints.txt',raw_face,fmt='%d')
    np.savez_compressed(output/'result.npz',**arrays)
    deleted=[]
    for i in np.flatnonzero(~keep):
        a,b,c=[[Q.from_float(float(x)) for x in p] for p in v[f[i]]];u=[x-y for x,y in zip(b,a)];w=[x-y for x,y in zip(c,a)]
        cross=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
        deleted.append({'input_face':int(i),'area_squared_exact':str(sum(x*x for x in cross)/4),'was_positive_area':any(cross)})
    assert all(sha(p)==value for p,value in before.items())
    result={'schema':'explicit-local-sheet-repair-candidate-v1','status':'candidate_not_admitted','input_sha256':sha(input_path),
        'original_float_sha256':sha(original_float),'plan_sha256':sha(plan_path),'inputs_sha256':before,'result_sha256':sha(output/'result.npz'),
        'original_vertices':len(v),'vertices':len(used),'original_faces':len(f),'faces':len(faces),'retained_changed_faces':int(changed[keep].sum()),
        'removed_microtriangles':deleted,'positive_area_change_claimed_zero':False,'coordinate_changes':'Only explicit planned source indices reassigned to existing target coordinates; all retained coordinates are input coordinates.',
        'changed_face_positive_parent_claims_invalidated':True,'historical_full_CSR_retained_separately':True,
        'parent_scope':'Unmodified faces retain prior producer lineage. Changed faces have source/source_face=-1 and empty positive parent CSR; their historical rows are search/provenance hints only, not containment or anchor evidence.',
        'identities_unchanged':True,'required_gates':plan['admission']}
    (output/'assessment.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','result_sha256','retained_changed_faces','faces','vertices']}));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['input','original_float','plan','output']:p.add_argument(n,type=Path)
    a=p.parse_args();repair(a.input,a.original_float,a.plan,a.output)
