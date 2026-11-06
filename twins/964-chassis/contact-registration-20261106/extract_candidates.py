#!/usr/bin/env python3
"""Preserve original boundary IDs and screen fixed nominal-size candidates privately."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(vertices, edges):
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('Expected finite Nx3 source vertices')
    if (edges.ndim != 2 or edges.shape[1] != 2 or not len(edges) or edges.dtype.kind not in 'iu'
            or edges.min() < 0 or edges.max() >= len(vertices)):
        raise ValueError('Expected original in-range integer edge endpoints')
    canonical = np.sort(edges, axis=1)
    if np.any(canonical[:, 0] == canonical[:, 1]) or len(np.unique(canonical, axis=0)) != len(edges):
        raise ValueError('Repeated or self-connected original edges')
    nodes, local = np.unique(edges, return_inverse=True)
    local = local.reshape(-1, 2)
    graph = coo_matrix((np.ones(len(edges), np.uint8), (local[:, 0], local[:, 1])),
                       shape=(len(nodes), len(nodes))).tocsr()
    count, labels = connected_components(graph, directed=False)
    degree = np.bincount(local.ravel(), minlength=len(nodes))
    rows, components, source_ids = [], [], {}
    simple_count = legacy_count = size_count = 0
    for component in range(count):
        member = labels == component
        ids = nodes[member]
        source_ids[f'component_{component}'] = ids
        simple = bool(np.all(degree[member] == 2))
        simple_count += simple
        components.append({'component_id': component, 'vertices': len(ids), 'simple_cycle': simple})
        points = vertices[ids].astype(float)
        centre = points.mean(axis=0)
        radius = np.linalg.norm(points - centre, axis=1)
        diameter = float(2 * radius.mean())
        cv = float(radius.std() / max(radius.mean(), 1e-9))
        legacy = len(ids) >= 8 and 10 < diameter < 80 and cv < .25
        legacy_count += legacy
        if not simple or not 8 <= len(ids) <= 2500:
            continue
        _, _, axes = np.linalg.svd(points - centre, full_matrices=False)
        projected = (points - centre) @ axes.T
        major, minor = sorted(np.ptp(projected[:, :2], axis=0), reverse=True)
        rms = float(np.sqrt(np.mean(projected[:, 2] ** 2)))
        size = bool(18.75 <= minor <= 31.25 and 25.5 <= major <= 42.5 and rms <= 2)
        size_count += size
        if legacy or size:
            rows.append({'component_id': component, 'vertices': len(ids), 'simple_cycle': simple,
                         'legacy_mean_radius_diameter_mm': diameter, 'legacy_radial_cv': cv,
                         'pca_major_extent_mm': float(major), 'pca_minor_extent_mm': float(minor),
                         'plane_rms_mm': rms, 'centroid_vehicle_mm': centre.tolist(),
                         'legacy_hole_like': bool(legacy), 'broad_25x34_size_candidate': size,
                         'physical_hole_identified': False})
    report = {
        'classification': 'original_open_boundary_candidates_not_identified_vehicle_holes',
        'source_open_edges': len(edges), 'boundary_graph_components': int(count),
        'simple_cycles': int(simple_count), 'branched_or_other_components': int(count - simple_count),
        'legacy_hole_like_components': int(legacy_count), 'broad_25x34_size_candidates': int(size_count),
        'screen_settings': {'minimum_points': 8, 'maximum_points_for_svd': 2500,
                            'minor_extent_mm': [18.75, 31.25], 'major_extent_mm': [25.5, 42.5],
                            'plane_rms_max_mm': 2,
                            'setting_status': 'fixed exploratory screen, not acceptance tolerances'},
        'components': components, 'candidates': rows,
        'ids_file_contents': 'All original boundary components, including rejected shapes and noncycles.',
        'new_physical_correspondences': 0, 'fit_to_nominal_frame': False,
        'geometry_modified': False, 'physical_vs_occlusion_resolved': False,
    }
    return report, source_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('vertices', 'source-open-edges', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('vertices', 'edges'):
        parser.add_argument('--' + name + '-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'work') or output.exists():
        raise ValueError('Output must be a new private directory under work/')
    pinned = {args.vertices: args.vertices_sha256, args.source_open_edges: args.edges_sha256}
    if any(digest(p) != h for p, h in pinned.items()):
        raise ValueError('Pinned original vertex/edge hash mismatch')
    vertices = np.load(args.vertices, allow_pickle=False)
    with np.load(args.source_open_edges, allow_pickle=False) as archive:
        edges = archive['source_vertex_ids']
    report, source_ids = extract(vertices, edges)
    if any(digest(p) != h for p, h in pinned.items()):
        raise ValueError('An input changed during extraction')
    report['input_sha256'] = {p.name: h for p, h in pinned.items()}
    report['extractor_sha256'] = digest(__file__)
    report['inputs_unchanged_after_run'] = True
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    ids_path = output / 'candidate-source-ids.npz'
    np.savez_compressed(ids_path, **source_ids)
    report['candidate_source_ids_sha256'] = digest(ids_path)
    (output / 'audit.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: report[k] for k in ('boundary_graph_components', 'simple_cycles',
                                            'legacy_hole_like_components', 'broad_25x34_size_candidates')}))


if __name__ == '__main__':
    main()
