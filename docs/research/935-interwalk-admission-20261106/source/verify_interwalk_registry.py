"""Independently check complete registry prefixes, birth identities and trial history."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def inspect(previous,current,keys,classes,round_id,parent,census,proof,old_history,next_history):
    names={'global_pair_ids','raw_pair_keys','geometry_classes','birth_rounds','birth_parent_mesh_sha256',
           'birth_census_sha256','birth_census_proof_sha256','birth_local_pair_ids'}
    assert set(current)==names
    count=len(keys);old=0 if previous is None else len(previous['global_pair_ids']);total=old+count
    assert count>0 and np.array_equal(current['global_pair_ids'],np.arange(total))
    for key in names:
        assert current[key].shape==((total,6) if key=='raw_pair_keys' else (total,))
        if previous is not None:assert np.array_equal(previous[key],current[key][:old])
    assert np.array_equal(current['raw_pair_keys'][old:],keys) and np.array_equal(current['geometry_classes'][old:],classes)
    assert np.all(np.isin(current['geometry_classes'],[0,1])) and np.all(current['birth_rounds'][old:]==round_id)
    assert np.array_equal(current['birth_local_pair_ids'][old:],np.arange(count))
    for field,value in [('birth_parent_mesh_sha256',parent),('birth_census_sha256',census),('birth_census_proof_sha256',proof)]:assert np.all(current[field][old:]==value)
    assert not set(map(tuple,keys))&set(map(tuple,old_history))
    assert np.array_equal(next_history[:len(old_history)],old_history) and np.array_equal(next_history[len(old_history):],keys)
    assert len(np.unique(next_history,axis=0))==len(next_history)
    assert np.array_equal(next_history[1705:],current['raw_pair_keys'])
    return old,total


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','recorded','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text())
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    census=load(job['census']);proof=json.loads(Path(job['census_proof']).read_text())
    assert proof['census_independently_verified'] and proof['census_sha256']==sha(job['census']) and proof['mesh_sha256']==sha(job['mesh'])
    assert proof['job_sha256']==sha(job['census_job'])
    previous=load(job['previous_registry']) if job.get('previous_registry') else None
    registry_path=args.recorded/'private-registry.npz';next_path=args.recorded/'private-next-attempt-history.npz';registry=load(registry_path);next_history=load(next_path)['raw_pair_keys'];old_history=load(job['attempt_history'])['raw_pair_keys']
    keys=[]
    for left,right in census['selected_pair_edge_ids']:
        parts=[tuple(map(int,census['source_edge_keys'][edge])) for edge in (left,right)];parts.sort();keys.append(parts[0]+parts[1])
    keys=np.asarray(keys,dtype=np.int64).reshape(-1,6)
    old,total=inspect(previous,registry,keys,np.ones(len(census['selected_pair_edge_ids']), dtype=np.int8),job['round'],sha(job['mesh']),sha(job['census']),sha(job['census_proof']),old_history,next_history)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),registry_sha256=sha(registry_path),next_history_sha256=sha(next_path),
        census_sha256=sha(job['census']),census_proof_sha256=sha(job['census_proof']),previous_registry_pairs=old,appended_selected_pairs=len(keys),
        total_registry_pairs=total,total_attempted_raw_pairs=len(next_history),every_prior_registry_field_exact=True,global_ids_do_not_restart=True,
        registry_independently_verified=True,producer_imported=False,new_strip_kind=9,new_boundary_origin=9,legacy_patch_label_base=80000000,
        constructor_admission_is_exploratory_only=True,geometry_modified=False,physical_acceptance=False,manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
