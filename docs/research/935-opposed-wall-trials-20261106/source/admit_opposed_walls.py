"""Bind exploratory opposed-wall inputs to raw owners and complete incident masks."""
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


def incident_masks(faces, corners):
    """Recover every original incident row; masks are sorted and duplicate-free."""
    nodes = faces.ravel(); rows = np.repeat(np.arange(len(faces)), 3)
    order = np.argsort(nodes, kind='stable'); sorted_nodes = nodes[order]
    offsets = [0]; masks = []
    for selected in corners:
        halo = []
        for node in np.unique(selected):
            lo = np.searchsorted(sorted_nodes, node, side='left')
            hi = np.searchsorted(sorted_nodes, node, side='right')
            halo.extend(rows[order[lo:hi]])
        halo = np.unique(halo); masks.extend(halo); offsets.append(len(masks))
    return np.asarray(offsets, dtype=np.int64), np.asarray(masks, dtype=np.int64)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); started = time.monotonic(); job = json.loads(args.job.read_text())
    assert job['schema'] == '935-opposed-wall-trials-1'
    assert job['assumption_accepted_for_exploratory_construction_only'] is True
    assert not job['physical_acceptance'] and not job['manufacturing_authorized']
    for entry in job['inputs']:
        assert sha(entry['path']) == entry['sha256']
    proof = json.loads(Path(job['parent_proof']).read_text())
    pair_proof = json.loads(Path(job['pair_verification']).read_text())
    assert proof['mesh_sha256'] == sha(job['mesh']) and proof['surface_study_checks_passed']
    assert pair_proof['mesh_sha256'] == sha(job['mesh'])
    assert pair_proof['census_sha256'] == sha(job['census']) and pair_proof['census_independently_verified']
    assert pair_proof['constructor_admission_granted'] is False
    mesh, boundary, raw, census = map(load, (job['mesh'], job['boundaries'], job['source_arrays'], job['census']))
    identity = module(job['raw_identity_inspector'], 'wall_raw_identity')
    geometry = module(job['pair_inspector'], 'wall_scalar_admission')
    pairs = census['selected_pair_edge_ids']; edges = boundary['boundary_local_nodes']
    owners = boundary['boundary_face_rows']; selected = np.unique(pairs)
    assert len(selected) == 2*len(pairs)
    assert np.all(boundary['edge_origin_kind'][selected] == 1)
    assert np.all(mesh['inferred_surface_kind'][owners[selected]] == 0)
    keys = np.full((len(edges), 3), -1, dtype=np.int64); normals = np.zeros((len(edges), 3))
    for edge in selected:
        keys[edge], normals[edge] = identity.original_key(mesh, edges[edge], owners[edge], raw)
        assert np.array_equal(keys[edge], census['source_edge_keys'][edge])
    flags = []
    for pair_id, (left, right) in enumerate(pairs):
        reason, result = geometry.inspect_pair(mesh['points'], edges, normals, left, right, job['limits'])
        assert reason == 'eligible'; flags.append(result[0])
        curve = census['selected_pair_curve_ids'][pair_id]
        assert census['edge_curve_ids'][left] == census['edge_curve_ids'][right] == curve
    flags = np.asarray(flags, dtype=bool)
    assert np.array_equal(flags, census['eligible_pair_diagonal_flags'][census['selected_eligible_pair_indices']])
    corners = edges[pairs].reshape(-1, 4)
    assert np.all(boundary['all_used_vertex_fans'][np.unique(corners)] == 1)
    offsets, masks = incident_masks(mesh['triangles'], corners)
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output/'private-construction-admission.npz'
    np.savez_compressed(target, pair_ids=np.arange(len(pairs)), pair_edge_ids=pairs,
                        source_edge_keys=keys[selected], selected_edge_ids=selected,
                        source_owner_normals=normals[selected], diagonal_flags=flags,
                        halo_offsets=offsets, halo_face_rows=masks)
    for entry in job['inputs']:
        assert sha(entry['path']) == entry['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
                  mesh_sha256=sha(job['mesh']), census_sha256=sha(job['census']),
                  admission_sha256=sha(target), proposed_pairs=len(pairs),
                  raw_acquired_edges_recovered=len(selected), complete_incident_masks=len(pairs),
                  incident_mask_face_rows=len(masks),
                  admission_pending_independent_verification=True,
                  assumption='Raw acquired owner windings are provisionally outward; exploratory construction only',
                  geometry_modified=False, physical_acceptance=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
