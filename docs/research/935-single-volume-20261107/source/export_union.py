"""Admit the independently checked union, classify its shells and export exact 3MF."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']

    def module(key):
        spec = importlib.util.spec_from_file_location(key, job[key])
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result

    raw = json.loads(Path(job['geometry_report']).read_text())
    provenance = json.loads(Path(job['provenance_report']).read_text())
    proof = json.loads(Path(job['contacts']).read_text())
    mesh_hash = sha(job['candidate'])
    assert mesh_hash == raw['input_sha256'] == provenance['candidate_sha256']
    for key in ('zero_area_triangles', 'open_edges', 'nonmanifold_edges', 'inconsistently_oriented_edges'):
        assert raw[key] == 0
    assert raw['vertex_manifold'] and raw['signed_volume_mm3'] > 0
    assert provenance['containment_passed'] and provenance['all_output_triangles_checked'] == raw['triangles']
    data = dict(np.load(job['candidate'], allow_pickle=False))
    v, f = data['vertices'], data['triangles']
    assert len(v) == raw['vertices'] and len(f) == raw['triangles']
    pairs = np.load(job['pairs'], allow_pickle=False)
    assert len(pairs) == raw['intersection_pairs'] == proof['raw_reported_pairs']
    assert proof['source_sha256'] == sha(job['contact_source']) and proof['unresolved_pairs'] == 0
    contacts = module('contact_source')
    contacts.controls()
    assert len(proof['private_pair_proofs']) == len(pairs)
    for pair, row in zip(pairs, proof['private_pair_proofs']):
        assert list(map(int, pair)) == row['triangle_pair']
        actual = contacts.prove(v, f, *map(int, pair))
        assert actual is not None and actual == row['proof']
    validator = module('validator_source')
    validator.shell_controls()
    graph = coo_matrix((np.ones(2*len(f), dtype=bool),
                        (f[:, [0, 1]].ravel(), f[:, [1, 2]].ravel())), shape=(len(v), len(v))).tocsr()
    count, labels = connected_components(graph, directed=False)
    del graph
    assert count == raw['connected_components'] and len(np.unique(f)) == len(v)
    shell = validator.classify_shells(v, f, labels)
    args.output.mkdir(mode=0o700, exist_ok=False)
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), candidate_sha256=mesh_hash,
                  raw_geometry_report_sha256=sha(job['geometry_report']),
                  exact_contact_proof_sha256=sha(job['contacts']), provenance_report_sha256=sha(job['provenance_report']),
                  raw_predicate_intersection_pairs=len(pairs), proved_shared_simplex_contacts=len(pairs),
                  proper_nonadjacent_intersection_pairs=0, solid_shell_classification=shell,
                  enclosed_voids_filled=False, geometry_modified=False,
                  machine_job=False, manufacturing_qualified=False, engine_qualified=False)
    if shell['one_material_body']:
        target = args.output/'935-supported-single-volume-hypotheses-mm.3mf'
        validator.write_3mf(target, v, f)
        report.update(three_mf_sha256=sha(target), every_coordinate_index_and_unit_roundtrips_exact=True,
                      digital_geometry_and_export_gate_passed=True)
    else:
        report['digital_geometry_and_export_gate_passed'] = False
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report['seconds'] = time.monotonic()-began
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
