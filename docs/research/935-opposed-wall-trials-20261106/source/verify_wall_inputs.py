"""Independently check every wall owner/mask and exercise native refusal controls."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as values:
        return {key: values[key] for key in values.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def mask_matches(faces, corners, mask):
    # Independent Boolean membership, without the producer's sorted-corner index.
    expected = np.flatnonzero(np.isin(faces, corners).any(axis=1))
    return np.array_equal(mask, expected)


def controls(job):
    constructor = module(job['constructor_source'], 'wall_constructor_controls')
    native = module(job['intersection_helper'], 'wall_native_controls')
    fans = module(job['fan_helper'], 'wall_fan_controls')
    topology = module(job['boundary_helper'], 'wall_control_topology')
    points = np.array([[0.,0.,.1],[.2,0.,.1],[.2,0.,-.1],[0.,0.,-.1],
                       [0.,.2,.1],[.2,.2,-.1],[0.,-.2,.1]])
    faces = np.array([[0,1,4],[2,3,5]])
    patch = np.array([[1,0,3],[1,3,2]])
    all_edges, order, first, codes, uses = topology.table(faces, len(points))
    boundary = dict(edge_origin_kind=np.ones(len(all_edges), dtype=np.int8))
    sorter = np.argsort(codes)
    def admit(triangles, counts=uses):
        return constructor.incidence_changes(triangles, len(points), codes, counts,
            all_edges[order[first]], codes[sorter], sorter, boundary, np.zeros(len(all_edges), dtype=int), 0)
    assert admit(patch) is not None
    assert admit(patch[:, ::-1]) is None
    assert admit(np.r_[patch, patch]) is None
    counts = uses.copy(); counts[np.flatnonzero(codes == 1)[0]] = 2
    assert admit(patch, counts) is None
    local = np.r_[faces, patch]
    conflicts, _, excluded = native.detect(points, local)
    assert len(conflicts) == len(excluded) == 0
    result, _ = fans.vertex_fans(local, len(points))
    assert np.all(result[:6] == 1)
    corners = [0,1,2,3]
    assert mask_matches(faces, corners, np.array([0,1]))
    assert not mask_matches(faces, corners, np.array([0]))
    assert not mask_matches(faces, corners, np.array([0,1,1]))
    # Adding a touching face must make an old incomplete halo fail.
    changed = np.r_[faces, [[1,0,6]]]
    assert not mask_matches(changed, corners, np.array([0,1]))
    return 9


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'admission', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(); started = time.monotonic(); job = json.loads(args.job.read_text())
    for entry in job['inputs']:
        assert sha(entry['path']) == entry['sha256']
    before = sha(args.admission)
    mesh, boundary, raw, census, admitted = map(load,
        (job['mesh'], job['boundaries'], job['source_arrays'], job['census'], args.admission))
    identity = module(job['raw_identity_inspector'], 'wall_independent_raw_identity')
    geometry = module(job['pair_inspector'], 'wall_independent_geometry')
    counts = controls(job); wall_controls = geometry.controls(job['limits']); identity_controls = identity.identity_controls()
    pairs = census['selected_pair_edge_ids']; edges = boundary['boundary_local_nodes']; owners = boundary['boundary_face_rows']
    assert np.array_equal(admitted['pair_ids'], np.arange(len(pairs)))
    assert np.array_equal(admitted['pair_edge_ids'], pairs)
    selected = np.unique(pairs); assert np.array_equal(admitted['selected_edge_ids'], selected)
    normals = np.zeros((len(edges),3))
    # Independently reindex every directed parent edge and confirm its only owner.
    directed = mesh['triangles'][:, [[0,1],[1,2],[2,0]]].reshape(-1,2)
    nv = len(mesh['points']); codes = directed.min(axis=1)*nv+directed.max(axis=1)
    order = np.argsort(codes, kind='stable'); sorted_codes = codes[order]
    for index, edge in enumerate(selected):
        key, normals[edge] = identity.original_key(mesh, edges[edge], owners[edge], raw)
        assert np.array_equal(key, admitted['source_edge_keys'][index])
        assert np.array_equal(key, census['source_edge_keys'][edge])
        assert np.array_equal(normals[edge], admitted['source_owner_normals'][index])
        code = min(edges[edge])*nv+max(edges[edge]); lo = np.searchsorted(sorted_codes, code); hi = np.searchsorted(sorted_codes, code, side='right')
        assert hi-lo == 1 and order[lo]//3 == owners[edge]
        assert np.array_equal(directed[order[lo]], edges[edge]) and boundary['edge_origin_kind'][edge] == 1
    del directed, codes, order, sorted_codes
    assert admitted['halo_offsets'][0] == 0 and admitted['halo_offsets'][-1] == len(admitted['halo_face_rows'])
    assert len(admitted['halo_offsets']) == len(pairs)+1
    for pair_id, (left,right) in enumerate(pairs):
        reason, result = geometry.inspect_pair(mesh['points'], edges, normals, left, right, job['limits'])
        assert reason == 'eligible' and np.array_equal(result[0], admitted['diagonal_flags'][pair_id])
        lo, hi = admitted['halo_offsets'][pair_id:pair_id+2]
        assert mask_matches(mesh['triangles'], edges[[left,right]].ravel(), admitted['halo_face_rows'][lo:hi])
    assert sha(args.admission) == before
    for entry in job['inputs']:
        assert sha(entry['path']) == entry['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  census_sha256=sha(job['census']), admission_sha256=before,
                  selected_pairs=len(pairs), raw_acquired_edge_owners_verified=len(selected),
                  complete_masks_independently_verified=len(pairs), native_mask_and_incidence_controls_passed=counts,
                  opposed_geometry_controls_passed=wall_controls, raw_identity_controls_passed=identity_controls,
                  producer_imported=False, construction_inputs_independently_verified=True,
                  construction_admission_only_for_declared_exploratory_hypothesis=True,
                  physical_orientation_or_anatomy_certified=False, physical_acceptance=False,
                  manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
