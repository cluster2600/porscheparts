"""Append independently selected raw pairs before trials, with immutable global IDs."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


FIELDS=('global_pair_ids','raw_pair_keys','geometry_classes','birth_rounds',
        'birth_parent_mesh_sha256','birth_census_sha256','birth_census_proof_sha256','birth_local_pair_ids')


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def append(previous,keys,classes,round_id,parent_sha,census_sha,proof_sha):
    count=len(keys);assert count>0 and keys.shape==(count,6) and classes.shape==(count,)
    if previous is None:
        previous={name:np.empty((0,6) if name=='raw_pair_keys' else (0,),dtype='U64' if name.endswith('sha256') else np.int64) for name in FIELDS}
    assert set(previous)==set(FIELDS);offset=len(previous['global_pair_ids'])
    assert np.array_equal(previous['global_pair_ids'],np.arange(offset))
    new=dict(global_pair_ids=np.arange(offset,offset+count),raw_pair_keys=keys,geometry_classes=classes,
        birth_rounds=np.full(count,round_id),birth_parent_mesh_sha256=np.full(count,parent_sha,dtype='U64'),
        birth_census_sha256=np.full(count,census_sha,dtype='U64'),birth_census_proof_sha256=np.full(count,proof_sha,dtype='U64'),birth_local_pair_ids=np.arange(count))
    return {name:np.concatenate((previous[name],new[name])) for name in FIELDS}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text())
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['census_proof']).read_text());assert proof['census_independently_verified'] and proof['census_sha256']==sha(job['census']) and proof['mesh_sha256']==sha(job['mesh'])
    assert proof['job_sha256']==sha(job['census_job'])
    census=load(job['census']);history=load(job['attempt_history'])['raw_pair_keys'];previous=load(job['previous_registry']) if job.get('previous_registry') else None
    keys=[]
    for left,right in census['selected_pair_edge_ids']:
        a=tuple(map(int,census['source_edge_keys'][left]));b=tuple(map(int,census['source_edge_keys'][right]));keys.append(a+b if a<b else b+a)
    keys=np.asarray(keys,dtype=np.int64).reshape(-1,6);assert len(keys)>0
    assert not set(map(tuple,keys))&set(map(tuple,history)) and len(np.unique(keys,axis=0))==len(keys)
    registry=append(previous,keys,np.ones(len(census['selected_pair_edge_ids']), dtype=np.int8),job['round'],sha(job['mesh']),sha(job['census']),sha(job['census_proof']))
    next_history=np.r_[history,keys];assert len(np.unique(next_history,axis=0))==len(next_history)
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-registry.npz',**registry)
    np.savez_compressed(args.output/'private-next-attempt-history.npz',raw_pair_keys=next_history)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),registry_sha256=sha(args.output/'private-registry.npz'),
        next_history_sha256=sha(args.output/'private-next-attempt-history.npz'),previous_registry_pairs=len(registry['global_pair_ids'])-len(keys),
        appended_selected_pairs=len(keys),total_registry_pairs=len(registry['global_pair_ids']),total_attempted_raw_pairs=len(next_history),
        selected_pairs_recorded_before_constructor=True,refusals_will_not_be_removed_from_history=True,registry_pending_independent_check=True,
        geometry_modified=False,physical_acceptance=False,manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
