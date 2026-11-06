"""Verify a zero eligible-pair stop without inventing a second constructor run."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def inspect(census, replay, surface, topology, registry, history, mesh_sha, census_sha):
    assert replay['census_independently_verified']
    assert replay['mesh_sha256'] == surface['mesh_sha256'] == topology['mesh_sha256'] == mesh_sha
    assert replay['census_sha256'] == census_sha
    assert surface['surface_study_checks_passed'] and topology['exact_final_Euler_boundary_genus_verified']
    assert replay['eligible_pairs'] == replay['selected_pairs'] == 0
    assert census['eligible_pair_edge_ids'].shape == census['selected_pair_edge_ids'].shape == (0, 2)
    assert len(census['selected_eligible_pair_indices']) == 0
    assert np.array_equal(census['prior_attempted_pair_keys'], history)
    assert len(history) == replay['all_attempted_raw_pair_identities']
    assert len(np.unique(history, axis=0)) == len(history)
    assert np.array_equal(registry['global_pair_ids'], np.arange(len(registry['raw_pair_keys'])))
    assert np.array_equal(history[1705:], registry['raw_pair_keys'])
    return len(history), len(registry['raw_pair_keys'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    replay, surface, topology, registration = [json.loads(Path(job[name]).read_text())
        for name in ('census_proof', 'surface_proof', 'topology_proof', 'registry_proof')]
    assert replay['source_sha256'] == sha(job['census_inspector'])
    assert surface['source_sha256'] == sha(job['surface_inspector'])
    assert topology['source_sha256'] == sha(job['topology_inspector'])
    assert registration['source_sha256'] == sha(job['registry_inspector'])
    assert registration['registry_independently_verified']
    assert registration['registry_sha256'] == sha(job['registry'])
    assert registration['next_history_sha256'] == sha(job['history'])
    assert topology['full_surface_proof_sha256'] == sha(job['surface_proof'])
    census = load(job['census'])
    count, entries = inspect(census, replay, surface, topology, load(job['registry']),
        load(job['history'])['raw_pair_keys'], sha(job['mesh']), sha(job['census']))
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
        final_mesh_sha256=sha(job['mesh']), last_full_surface_proof_sha256=sha(job['surface_proof']),
        complete_pair_replay_sha256=sha(job['census_proof']),
        attempted_raw_pairs=count, immutable_registry_entries=entries,
        remaining_eligible_pairs=0, fixed_two_class_same_walk_graph_exhausted=True,
        no_second_constructor_or_second_candidate_created=True,
        other_geometry_classes_not_proven_exhausted=True,
        small_whole_loops_still_need_separate_admission=True,
        physical_acceptance=False, manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
