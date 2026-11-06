"""Prove an unchanged terminal mesh and exhaustion of the independently checked graph."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def remaining_keys(edge_keys,eligible_pairs,history):
    attempted=set(map(tuple,history.tolist()));remaining=[]
    for a,b in eligible_pairs:
        first=tuple(map(int,edge_keys[a]));second=tuple(map(int,edge_keys[b]))
        key=first+second if first<second else second+first
        if key not in attempted:remaining.append(key)
    return np.asarray(remaining,dtype=np.int64).reshape(-1,6)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text())
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    census=load(job['census']);proof=json.loads(Path(job['census_proof']).read_text())
    assert proof['census_independently_verified'] and proof['census_sha256']==sha(job['census'])
    assert proof['mesh_sha256']==sha(job['verified_mesh'])
    prior=json.loads(Path(job['verified_mesh_proof']).read_text());assert prior['mesh_sha256']==sha(job['verified_mesh']) and prior['surface_study_checks_passed']
    construction=json.loads(Path(job['terminal_construction_report']).read_text())
    assert construction['accepted_pairs']==construction['added_triangles']==0
    assert sha(job['terminal_mesh'])==sha(job['verified_mesh'])==construction['mesh_sha256']
    assert sha(Path(job['terminal_mesh']).with_suffix('.obj'))==sha(Path(job['verified_mesh']).with_suffix('.obj'))
    registry_proof=json.loads(Path(job['registry_proof']).read_text());assert registry_proof['registry_independently_verified']
    assert registry_proof['registry_sha256']==sha(job['registry']) and registry_proof['next_history_sha256']==sha(job['next_history'])
    assert registry_proof['census_sha256']==sha(job['census'])
    history=load(job['next_history'])['raw_pair_keys'];old=census['prior_attempted_pair_keys']
    assert np.array_equal(history[:len(old)],old) and len(history)==len(old)+len(census['selected_pair_edge_ids'])
    remaining=remaining_keys(census['source_edge_keys'],census['eligible_pair_edge_ids'],history)
    assert len(remaining)==0
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),final_mesh_sha256=sha(job['verified_mesh']),
        unchanged_terminal_npz_bytes=True,unchanged_terminal_obj_bytes=True,full_geometric_proof_inherited_by_exact_byte_identity=True,
        full_mesh_checks_not_reexecuted_on_an_identical_terminal_file=True,last_full_geometric_proof_sha256=sha(job['verified_mesh_proof']),
        all_prior_registry_fields_remain_exact=registry_proof['every_prior_registry_field_exact'],attempted_raw_pairs=len(history),
        terminal_independently_verified_eligible_pairs=len(census['eligible_pair_edge_ids']),eligible_pairs_not_in_latest_history=len(remaining),
        fixed_two_class_graph_exhausted_for_unchanged_geometry=True,other_geometry_classes_not_proven_exhausted=True,
        stop_reason='no_local_geometry_in_round2_and_no_remaining_unattempted_eligible_pair',
        no_refused_pair_retried=True,physical_acceptance=False,manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
