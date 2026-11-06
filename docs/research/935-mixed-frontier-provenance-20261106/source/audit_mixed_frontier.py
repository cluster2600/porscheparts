"""Recover acquired ancestry for the remaining compact nonplanar mixed borders.

This is provenance and input admissibility, never a new cap/normal/solver policy.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    source = json.loads(Path(job['ancestry_job']).read_text())
    for item in source['inputs']:
        assert sha(item['path']) == item['sha256']
    surface = json.loads(Path(source['surface_proof']).read_text())
    assert surface['surface_study_checks_passed'] and surface['mesh_sha256'] == sha(source['mesh'])
    assert surface['source_sha256'] == sha(source['surface_inspector'])
    registry_proof = json.loads(Path(source['registry_proof']).read_text())
    assert registry_proof['registry_independently_verified'] and registry_proof['registry_sha256'] == sha(source['registry'])
    assert registry_proof['source_sha256'] == sha(source['registry_inspector'])
    mesh, border, raw, registry = [dict(np.load(source[k], allow_pickle=False))
                                   for k in ('mesh', 'boundaries', 'source_arrays', 'registry')]
    assert np.array_equal(registry['global_pair_ids'], np.arange(len(registry['global_pair_ids'])))
    identity = module(source['raw_identity_inspector'], 'frozen_mixed_raw_identity')
    checker = module(source['inspector_source'], 'frozen_mixed_inferred_signature')
    producer = module(source['producer_source'], 'frozen_mixed_birth_recovery')
    identity_controls = identity.identity_controls()
    birth_sources = {}
    for item in source['birth_sources']:
        proof = json.loads(Path(item['proof']).read_text())
        assert proof['census_independently_verified'] and proof['census_sha256'] == sha(item['census'])
        assert proof['source_sha256'] == sha(item['inspector'])
        birth_sources[sha(item['census'])] = dict(census=dict(np.load(item['census'], allow_pickle=False)),
                                                 proof_hash=sha(item['proof']), birth_round=item['birth_round'],
                                                 class_policy=item['class_policy'])
    births = producer.birth_references(registry, birth_sources)
    frontier, untried, opposed, old_mesh, old_border = [dict(np.load(source[k], allow_pickle=False))
        for k in ('frontier_census', 'untried_census', 'opposed_census', 'frontier_parent_mesh', 'frontier_parent_boundaries')]
    review = json.loads(Path(job['curve_review']).read_text())
    assert len(review) == len(border['offsets'])-1 == surface['remaining_boundary_walks']
    assert np.array_equal(np.sort(border['cycle_edges']), np.arange(len(border['boundary'])))
    assert len(border['boundary']) == surface['remaining_boundary_edges']
    walk_ids, flat_edges, walk_offsets = [], [], [0]
    signatures, references, reference_offsets, measured_normals = [], [], [0], []
    counts = Counter()
    for walk, row in enumerate(review):
        assert row['curve'] == walk
        a, b = border['offsets'][walk:walk+2]
        ids = border['cycle_edges'][a:b]
        origins = set(map(int, border['edge_origin_kind'][ids]))
        assert Counter(map(str, border['edge_origin_kind'][ids])) == row['edge_origin_counts']
        nodes = border['boundary'][ids, 0]
        assert np.array_equal(border['boundary'][ids, 1], np.roll(nodes, -1))
        if 1 not in origins or origins == {1} or origins-{1, 6, 7, 8, 9}:
            continue
        p = mesh['points'][nodes]
        if not 3 <= len(ids) <= 128 or np.linalg.norm(np.ptp(p, axis=0)) > 3:
            continue
        centred = p-p.mean(axis=0)
        _, _, axes = np.linalg.svd(centred, full_matrices=False)
        residual = float(np.abs(centred@axes[-1]).max())
        assert abs(residual-row['plane_maximum_residual_nominal_mm']) < 1e-10
        if residual <= .25:
            continue
        assert row['physical_classification'] == 'unreviewed' and row['closure_authorized'] is False
        walk_ids.append(walk)
        flat_edges.extend(map(int, ids))
        walk_offsets.append(len(flat_edges))
        for edge in ids:
            pair_nodes = border['boundary'][edge]
            owner, origin = int(border['owners'][edge]), int(border['edge_origin_kind'][edge])
            face = mesh['triangles'][owner]
            assert tuple(pair_nodes) in list(zip(face, np.roll(face, -1)))
            if origin == 1:
                key, normal = identity.original_key(mesh, pair_nodes, owner, raw)
                refs = np.asarray([key])
                signature = [0, key[0], key[0], -1, -1, key[1], key[2]]
            else:
                kind, field, census = {6:(4, 'source_frontier_pair_ids', frontier),
                    7:(6, 'source_untried_pair_ids', untried), 8:(7, 'source_opposed_wall_pair_ids', opposed),
                    9:(9, 'source_continuation_pair_ids', None)}[origin]
                pair = int(mesh[field][owner])
                assert pair >= 0
                if kind == 9:
                    refs = births[pair]
                elif kind == 4:
                    selected = census['selected_pair_edge_ids'][pair]
                    refs = np.asarray([identity.original_key(old_mesh, old_border['boundary_local_nodes'][e],
                        int(old_border['boundary_face_rows'][e]), raw)[0] for e in selected])
                else:
                    refs = census['source_edge_keys'][census['selected_pair_edge_ids'][pair]]
                for original, left, right in refs:
                    triangle = raw['triangles'][original].tolist()
                    assert (left, right) in list(zip(triangle, triangle[1:]+triangle[:1]))
                signature = checker.inferred_signature(mesh, owner, pair_nodes, raw, refs, kind, pair)
                normal = np.zeros(3)
            signatures.append(signature)
            references.extend(refs)
            reference_offsets.append(len(references))
            measured_normals.append(normal)
            counts[str(origin)] += 1
    args.output.mkdir(mode=0o700, exist_ok=False)
    payload = args.output/'private-mixed-border-ancestry.npz'
    np.savez_compressed(payload, walk_ids=np.asarray(walk_ids, dtype=np.int64),
                        walk_offsets=np.asarray(walk_offsets, dtype=np.int64), flat_edge_ids=np.asarray(flat_edges, dtype=np.int64),
                        edge_signatures=np.asarray(signatures, dtype=np.int64),
                        raw_reference_offsets=np.asarray(reference_offsets, dtype=np.int64),
                        raw_owner_edge_keys=np.asarray(references, dtype=np.int64),
                        actual_acquired_normals=np.asarray(measured_normals, dtype=np.float64))
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(source['mesh']),
                  ancestry_payload_sha256=sha(payload), whole_walks=len(review), whole_boundary_edges=len(border['boundary']),
                  mixed_compact_nonplanar_walks=len(walk_ids), scoped_edges=len(flat_edges), scoped_origin_counts=dict(counts),
                  actual_acquired_border_normals=counts['1'], inferred_border_normal_measurements=0,
                  traceable_inferred_cross_edges=sum(v for k, v in counts.items() if k != '1'),
                  complete_global_registry_births_checked=len(births), reused_raw_identity_controls=identity_controls,
                  frozen_ancestry_and_signature_checker_reused=True, new_independent_ancestry_implementation_claimed=False,
                  all_scoped_anatomy_unreviewed=True, cap_input_admission=False,
                  inferred_geometric_directions_are_not_acquired_normal_evidence=True,
                  new_cap_normal_policy_defined=False, unobserved_geometry_measured=False,
                  geometry_modified=False, simulation_admitted=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
