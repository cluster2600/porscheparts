#!/usr/bin/env python3
"""Relate original boundary cycles to source surfaces without identifying parts."""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
COMPONENTS = (3, 70, 14, 85, 13, 30, 10, 61)
PINNED = {
    'vertices': ('work/964-model-year-review-20261029/replay-001/verts_vehicle.npy',
                 '201787314680bcd60fb5f9b8910e28b0025d60c380dc77fa458a41bb17942bc9'),
    'faces': ('work/964-model-year-review-20261029/replay-001/faces.npy',
              '271c4f04717be91babfebeb809de485c940dc909ec981acd857693969563b484'),
    'face_components': ('work/964-observed-boundaries-20261029/review-001/source_face_components.npy',
                        'c1e1447a3a539ab22dbb8b538c4c2c04181e64d6fec708b52969ef2ad070508b'),
    'source_open_edges': ('work/964-observed-boundaries-20261029/review-001/source_open_edges.npz',
                          '22fa12246c7bce2f092d370d77208f317761a74af4b525eeb75afcf11d4618c2'),
    'boundary_components': ('work/964-registration-20261106/reproducible-extract-001/candidate-source-ids.npz',
                            '4803252b5e4580c6e320e2f61231c53aa18a2750415f96a9305d7db5728d859a'),
}


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def edge_keys(edges, vertex_count):
    edges = np.asarray(edges)
    if (edges.ndim != 2 or edges.shape[1] != 2 or edges.dtype.kind not in 'iu'
            or not 1 <= vertex_count <= 3_037_000_499
            or (len(edges) and (edges.min() < 0 or edges.max() >= vertex_count))):
        raise ValueError('Expected in-range original integer edge IDs and safe Int64 keys')
    edges = np.sort(edges.astype(np.int64), axis=1)
    if np.any(edges[:, 0] == edges[:, 1]):
        raise ValueError('Self-connected original edge')
    return edges[:, 0] * vertex_count + edges[:, 1]


def component_incidence(faces, vertex_count, source_open_edges, boundary_components):
    """Recompute one full source component; a crop must never be supplied here."""
    faces = np.asarray(faces)
    if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or faces.dtype.kind not in 'iu':
        raise ValueError('Expected original triangular integer faces')
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    keys, counts = np.unique(edge_keys(edges, vertex_count), return_counts=True)
    source_keys = edge_keys(source_open_edges, vertex_count)
    if len(np.unique(source_keys)) != len(source_keys):
        raise ValueError('Repeated original source open edge')
    order = np.argsort(source_keys)
    boundary = keys[counts == 1]
    slots = np.searchsorted(source_keys[order], boundary)
    if np.any(slots >= len(source_keys)) or not np.array_equal(source_keys[order[slots]], boundary):
        raise ValueError('Component boundary is not an original source open edge')
    edge_rows = order[slots]
    boundary_vertices = np.unique(source_open_edges[edge_rows])
    covered, cycles, output_ids, seen_ids = [], [], {}, set()
    for name, ids in boundary_components.items():
        ids = np.asarray(ids)
        if (not name.startswith('component_') or not name[10:].isdigit() or ids.ndim != 1
                or ids.dtype.kind not in 'iu' or not len(ids) or ids.min() < 0
                or ids.max() >= vertex_count or len(np.unique(ids)) != len(ids)):
            raise ValueError('Missing, repeated or foreign original boundary IDs')
        if seen_ids.intersection(ids.tolist()):
            raise ValueError('Original vertex assigned to multiple boundary components')
        seen_ids.update(ids.tolist())
        inside = np.isin(ids, boundary_vertices)
        if not inside.any():
            continue
        if not inside.all():
            raise ValueError('Boundary component crosses the selected source surface')
        rows = edge_rows[np.isin(source_open_edges[edge_rows], ids).all(axis=1)]
        nodes, degrees = np.unique(source_open_edges[rows], return_counts=True)
        if not np.array_equal(nodes, np.sort(ids)) or not np.all(degrees == 2):
            raise ValueError('Boundary is not a complete degree-two original cycle')
        neighbours = {int(i): [] for i in ids}
        for left, right in source_open_edges[rows]:
            neighbours[int(left)].append(int(right))
            neighbours[int(right)].append(int(left))
        reached, pending = set(), [int(ids[0])]
        while pending:
            node = pending.pop()
            if node not in reached:
                reached.add(node)
                pending.extend(neighbours[node])
        if len(reached) != len(ids):
            raise ValueError('One boundary ID contains disconnected cycles')
        boundary_id = int(name[10:])
        cycles.append({'boundary_component_id': boundary_id, 'source_vertices': len(ids),
                       'source_open_edges': len(rows)})
        output_ids[f'boundary_{boundary_id}_source_vertex_ids'] = ids
        output_ids[f'boundary_{boundary_id}_source_open_edge_row_ids'] = rows
        covered.append(ids)
    if not covered or not np.array_equal(np.unique(np.concatenate(covered)), boundary_vertices):
        raise ValueError('Original boundary cycles do not exhaust the surface boundary')
    vertices = np.unique(faces)
    output_ids.update(source_vertex_ids=vertices, source_open_edge_row_ids=edge_rows)
    report = {
        'source_vertices': len(vertices), 'source_faces': len(faces),
        'source_unique_edges': len(keys), 'source_boundary_edges': len(boundary),
        'source_nonmanifold_edges': int(np.count_nonzero(counts > 2)),
        'euler_characteristic_V_minus_E_plus_F': len(vertices) - len(keys) + len(faces),
        'original_boundary_cycles': cycles,
        'observation': ('sole observed boundary of a disconnected source surface component'
                        if len(cycles) == 1 else 'multiple observed boundaries of one source surface component'),
        'physical_rim_vs_acquisition_gap': 'unresolved',
        'inner_aperture_in_surrounding_plate_identified': False,
    }
    return report, output_ids


def run(paths, output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / 'work') or output.exists():
        raise ValueError('Output must be a new private directory under work/')

    def verify_inputs():
        if any(digest(paths[name]) != expected for name, (_, expected) in PINNED.items()):
            raise ValueError('Pinned original input hash mismatch')

    verify_inputs()
    vertices = np.load(paths['vertices'], mmap_mode='r', allow_pickle=False)
    faces = np.load(paths['faces'], mmap_mode='r', allow_pickle=False)
    labels = np.load(paths['face_components'], mmap_mode='r', allow_pickle=False)
    if vertices.shape != (2_400_031, 3) or not np.isfinite(vertices).all():
        raise ValueError('Unexpected original vertex array')
    if labels.shape != (len(faces),) or labels.dtype.kind not in 'iu':
        raise ValueError('Source face-component labels do not bind the original faces')
    with np.load(paths['source_open_edges'], allow_pickle=False) as archive:
        edges = archive['source_vertex_ids']
    with np.load(paths['boundary_components'], allow_pickle=False) as archive:
        loops = {key: archive[key] for key in archive.files}
    report = {
        'classification': 'original_boundary_surface_incidence_recomputation',
        'inputs': {name: {'sha256': expected} for name, (_, expected) in PINNED.items()},
        'surface_components': {}, 'vertex_links_checked': False, 'orientability_checked': False,
        'genus_or_disk_classification_admitted': False, 'physical_identity_established': False,
        'geometry_modified': False, 'new_correspondences': 0,
    }
    artifacts = {}
    for component in COMPONENTS:
        ids = np.flatnonzero(labels == component).astype(np.int32)
        summary, data = component_incidence(faces[ids], len(vertices), edges, loops)
        data['source_face_ids'] = ids
        report['surface_components'][str(component)] = summary
        artifacts[component] = data
    verify_inputs()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.boundary-incidence-', dir=output.parent) as temporary:
        staging = Path(temporary)
        for component, data in artifacts.items():
            np.savez_compressed(staging / f'component_{component}.npz', **data)
        report['artifact_sha256'] = {p.name: digest(p) for p in staging.glob('*.npz')}
        report['author_sha256'] = digest(__file__)
        verify_inputs()
        report['inputs_unchanged_after_run'] = True
        (staging / 'audit.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        staging.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, (relative, _) in PINNED.items():
        parser.add_argument('--' + name.replace('_', '-'), type=Path, default=ROOT / relative)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run({name: getattr(args, name) for name in PINNED}, args.output)
    print(json.dumps({'selected_surface_components': len(report['surface_components']),
                      'physical_identity_established': False, 'new_correspondences': 0}))


if __name__ == '__main__':
    main()
