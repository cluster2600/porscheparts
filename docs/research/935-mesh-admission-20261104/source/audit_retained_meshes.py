"""Read-only audit of recovered study meshes; never runs or admits a solver."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def tetra_metrics(points):
    a, b, c = (points[:, i] - points[:, 0] for i in (1, 2, 3))
    det = np.einsum('ij,ij->i', a, np.cross(b, c))
    edge_sum = sum(np.sum((points[:, i] - points[:, j]) ** 2, axis=1)
                   for i in range(4) for j in range(i))
    quality = np.divide(12 * (np.abs(det) / 2) ** (2 / 3), edge_sum,
                        out=np.zeros_like(det), where=edge_sum > 0)
    return det / 6, quality


def controls():
    regular = np.array([[0, 0, 0], [1, 0, 0], [.5, np.sqrt(3)/2, 0],
                        [.5, np.sqrt(3)/6, np.sqrt(2/3)]], dtype=float)
    v, q = tetra_metrics(regular[None])
    assert np.allclose(v, np.sqrt(2)/12) and np.allclose(q, 1)
    inverted = regular[[1, 0, 2, 3]]
    vi, qi = tetra_metrics(inverted[None])
    assert np.allclose(vi, -v) and np.allclose(qi, q)
    flat = regular.copy(); flat[3, 2] = 0
    vf, qf = tetra_metrics(flat[None]); assert vf[0] == 0 and qf[0] == 0
    vt, qt = tetra_metrics((regular * 17 + [103, -45, 7])[None])
    assert np.allclose(vt, v * 17**3) and np.allclose(qt, q)
    return {'regular_analytic_volume_and_unit_quality': True,
            'inversion_preserves_shape_but_reverses_signed_volume': True,
            'coplanar_element_zero_volume_and_quality': True,
            'translation_and_scale_invariance': True}


def audit(path):
    with np.load(path, allow_pickle=False) as arrays:
        nodes, tets, boundary = (arrays[k] for k in ('nodes', 'tets', 'boundary'))
    assert nodes.ndim == 2 and nodes.shape[1] == 3 and np.isfinite(nodes).all()
    assert tets.ndim == 2 and tets.shape[1] == 4
    assert boundary.ndim == 2 and boundary.shape[1] == 3
    for indices in (tets, boundary):
        assert np.issubdtype(indices.dtype, np.integer)
        assert indices.min() >= 0 and indices.max() < len(nodes)
    boundary_node = np.zeros(len(nodes), dtype=bool)
    boundary_node[np.unique(boundary)] = True
    quality = np.empty(len(tets)); volume = np.empty(len(tets))
    touches = np.empty(len(tets), dtype=bool)
    for start in range(0, len(tets), 100000):
        end = min(start + 100000, len(tets)); cells = tets[start:end]
        volume[start:end], quality[start:end] = tetra_metrics(nodes[cells])
        touches[start:end] = boundary_node[cells].any(axis=1)
    surface_hash = hashlib.sha256(); surface_quality = np.empty(len(boundary))
    for start in range(0, len(boundary), 100000):
        end = min(start + 100000, len(boundary)); p = nodes[boundary[start:end]]
        surface_hash.update(np.asarray(p, dtype='<f8').tobytes())
        a, b = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
        twice_area = np.linalg.norm(np.cross(a, b), axis=1)
        edge_sum = np.sum(a*a + b*b + (a-b)**2, axis=1)
        surface_quality[start:end] = np.divide(2*np.sqrt(3)*twice_area, edge_sum,
                                               out=np.zeros_like(edge_sum), where=edge_sum > 0)
    quantiles = [0, .001, .01, .05, .5, 1]
    bins = []
    for limit in (.01, .1):
        bad = quality < limit; interior = ~touches
        bins.append({'mean_ratio_below': limit, 'count': int(bad.sum()),
                     'fraction': float(bad.mean()),
                     'absolute_volume_fraction': float(np.abs(volume[bad]).sum()/np.abs(volume).sum()),
                     'bad_touching_any_boundary_node': int((bad & touches).sum()),
                     'boundary_touching_cell_bad_fraction': float(bad[touches].mean()),
                     'interior_cell_bad_fraction': float(bad[interior].mean()) if interior.any() else None})
    return {'input_sha256': digest(path), 'nodes': len(nodes), 'tetrahedra': len(tets),
            'boundary_triangles': len(boundary), 'boundary_nodes': int(boundary_node.sum()),
            'ordered_boundary_xyz_sha256': surface_hash.hexdigest(),
            'signed_volume_mm3': float(volume.sum()),
            'nonpositive_tetrahedra': int((volume <= 0).sum()),
            'quantile_probabilities': quantiles,
            'tetra_mean_ratio_quantiles': np.quantile(quality, quantiles).tolist(),
            'triangle_shape_quality_quantiles': np.quantile(surface_quality, quantiles).tolist(),
            'zero_area_boundary_triangles': int((surface_quality <= 0).sum()),
            'diagnostic_bins': bins,
            'touch_definition': 'At least one vertex belongs to the supplied surface; not an exact boundary-face adjacency classification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args(); checks = controls()
    if args.self_test:
        print(json.dumps(checks)); return
    if not args.root or not args.output:
        parser.error('--root and --output are required')
    if args.output.exists():
        raise SystemExit('Refusing to overwrite an existing audit.')
    manifest_path = args.root / 'science-recovery-manifest.json'
    manifest = json.loads(manifest_path.read_text())['files']; results = {}
    for name in ('coarse-tet', 'intermediate-tet', 'fine-interior-tet'):
        rel = name + '/solid.npz'; path = args.root / rel
        if digest(path) != manifest[rel]['sha256']:
            raise SystemExit('Recovered input checksum mismatch: ' + rel)
        results[name] = audit(path)
    same = len({r['ordered_boundary_xyz_sha256'] for r in results.values()}) == 1
    report = {'scope': 'Read-only retained study-mesh admission audit',
              'manifest_sha256': digest(manifest_path), 'controls': checks, 'meshes': results,
              'all_three_ordered_surfaces_identical': same,
              'quality_metric': '12*(3*absolute_volume)^(2/3) / sum(six_edge_lengths_squared); regular tetrahedron = 1. Not Gmsh minSICN.',
              'threshold_scope': '0.01 and 0.1 are diagnostic bins, not engineering acceptance tolerances.',
              'geometry_admissibility': 'Closed reconstructed assembly under explicit hypotheses, with inferred closures and unresolved thin regions; not an accepted bare-head domain.',
              'engineering_mesh_accepted': False, 'physical_geometry_accepted': False,
              'manufacturing_authorized': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'output': str(args.output), 'same_surface': same,
                      'cell_counts': [r['tetrahedra'] for r in results.values()]}))


if __name__ == '__main__':
    main()
