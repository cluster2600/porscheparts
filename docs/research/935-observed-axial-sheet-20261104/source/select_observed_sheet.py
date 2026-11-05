"""Register one acquired axial-facing sheet by a fixed geometric selection rule."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def components(faces, vertex_count):
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    keys = edges.min(1)*vertex_count+edges.max(1)
    order = np.argsort(keys, kind='stable')
    ordered = keys[order]
    uses = np.tile(np.arange(len(faces)), 3)[order]
    adjacent = ordered[1:] == ordered[:-1]
    first, second = uses[:-1][adjacent], uses[1:][adjacent]
    graph = coo_matrix((np.ones(len(first), bool), (first, second)), shape=(len(faces), len(faces))).tocsr()
    return connected_components(graph, directed=False)


def controls():
    # Two edge-connected triangles and a third with a vertex-only contact.
    faces = np.array([[0, 1, 2], [1, 3, 2], [0, 4, 5]])
    count, groups = components(faces, 6)
    checks = {'edge_pair_connected': bool(groups[0] == groups[1]),
              'vertex_only_contact_separate': bool(groups[0] != groups[2] and count == 2)}
    if not all(checks.values()):
        raise ValueError('Acquired component controls failed')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('arrays', 'partition', 'frame', 'planes', 'intersections', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing observed-sheet selection refused')
    expected = {'arrays': 'dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a',
                'partition': '5bcf58cfaa33aefaf4fcf679b4c39e30b34f033e7d21f21065b58ba909863246',
                'planes': 'd8d39fbbcb0f94cdb971d4cc51fb7b799e5441169ca473a23a923e0d43b91cb3',
                'frame': '3a5ffb7316148716b3668ec762e284feb67bda040cbda81ba7697cf39765b289',
                'intersections': '1ee2ad7b6e6fdf24b3288c78ccb9ec4952a76f2a496ff2c35f887a728913fb04'}
    for name, digest in expected.items():
        if sha(getattr(args, name)) != digest:
            raise SystemExit('Registered observed-sheet input mismatch: '+name)
    inputs = {name: sha(getattr(args, name)) for name in ('arrays', 'partition', 'frame', 'planes', 'intersections')}
    args.output.mkdir(parents=True)
    save(args.output/'plan.json', {'source_sha256': sha(__file__), 'input_sha256': inputs,
        'normal_axis': 'existing frame C; search coordinates, not an accepted physical datum',
        'normal_angle_max_degrees': 20, 'end_plane_search_margin_mm': 2,
        'region': 'existing geometric partition 0; not identified bare head',
        'connectivity': 'Shared original vertex-index edge; no spatial welding',
        'selection': 'Largest acquired area; tie by smallest source face ID; all eligible components reported',
        'maximum_native_candidate_faces': 100000, 'plane_projection_screen_mm': .01,
        'source_coordinates_modified': False, 'hidden_geometry_completed': False,
        'physical_acceptance': False, 'manufacturing_authorized': False})
    save(args.output/'controls.json', controls())
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    partition = np.load(args.partition, allow_pickle=False)
    frame = np.load(args.frame, allow_pickle=False)
    if partition.shape != (len(faces),) or not np.allclose(frame@frame.T, np.eye(3), atol=1e-12, rtol=0):
        raise ValueError('Original partition/frame shape rejected')
    planes = json.loads(args.planes.read_text())
    ends = [entry for entry in planes if entry['id'] in ('deck_candidate', 'back_face_candidate')]
    if len(ends) != 2:
        raise ValueError('Two existing end-face search references required')
    axis = frame[2]
    offsets = sorted(float(np.asarray(entry['origin_xyz_mm'])@axis) for entry in ends)
    lower, upper = offsets[0]+2, offsets[1]-2
    points = vertices[faces]
    cross = np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0])
    norm = np.linalg.norm(cross, axis=1)
    axial = points@axis
    alignment = np.divide(np.abs(cross@axis), norm, out=np.zeros(len(faces)), where=norm > 0)
    eligible = (partition == 0) & (norm > 0) & (alignment >= np.cos(np.deg2rad(20)))
    eligible &= (axial.min(1) >= lower) & (axial.max(1) <= upper)
    ids = np.flatnonzero(eligible)
    if not len(ids):
        raise ValueError('No acquired faces meet registered search rule')
    count, labels = components(faces[ids], len(vertices))
    areas = np.bincount(labels, weights=norm[ids]/2, minlength=count)
    minimum = np.full(count, len(faces), np.int64)
    np.minimum.at(minimum, labels, ids)
    counts = np.bincount(labels, minlength=count)
    chosen = int(np.lexsort((minimum, -areas))[0])
    selected = ids[labels == chosen]
    source_vertices, inverse = np.unique(faces[selected], return_inverse=True)
    local_vertices, local_faces = vertices[source_vertices], inverse.reshape(-1, 3)
    intersections = np.load(args.intersections, allow_pickle=False)
    implicated = np.intersect1d(selected, np.unique(intersections))
    duplicate_positions = len(source_vertices)-len(np.unique(local_vertices, axis=0))
    # A plane is evaluated independently of exact chart construction; it is never substituted.
    holdout = source_vertices % 5 == 0
    training = local_vertices[~holdout]
    origin = training.mean(0)
    _, _, basis = np.linalg.svd(training-origin, full_matrices=False)
    normal = basis[-1]
    distances = np.abs((local_vertices-origin)@normal)
    selected_metadata = {'component_label': chosen, 'source_faces': len(selected),
        'source_vertices': len(source_vertices), 'area_mm2': float(norm[selected].sum()/2),
        'search_C_bounds_mm': [lower, upper], 'selected_C_range_mm': [float(axial[selected].min()), float(axial[selected].max())],
        'coincident_distinct_source_vertices': duplicate_positions,
        'faces_implicated_in_original_intersection_index': len(implicated),
        'plane_training_vertices': len(training), 'plane_holdout_vertices': int(holdout.sum()),
        'plane_all_vertex_maximum_mm': float(distances.max()),
        'plane_holdout_p95_mm': float(np.quantile(distances[holdout], .95)),
        'plane_projection_screen_passed': bool(distances.max() <= .01),
        'plane_is_not_exported_or_adopted': True,
        'native_chart_size_admitted': bool(len(selected) <= 100000),
        'native_chart_defect_index_admitted': len(implicated) == 0 and duplicate_positions == 0,
        'anatomical_identity_accepted': False}
    np.savez_compressed(args.output/'selected-source.npz', vertices=local_vertices, triangles=local_faces,
                        source_vertex_ids=source_vertices, source_face_ids=selected)
    np.savez_compressed(args.output/'eligibility-provenance.npz', source_face_ids=ids, component_labels=labels)
    np.savez_compressed(args.output/'plane-diagnostic.npz', origin=origin, normal=normal,
                        source_vertex_ids=source_vertices, holdout=holdout, residuals=distances)
    save(args.output/'component-inventory.json', {'component_areas_mm2': areas.tolist(), 'component_face_counts': counts.tolist(),
        'smallest_source_face_ids': minimum.tolist()})
    report = {'source_faces': len(faces), 'source_vertices': len(vertices), 'zero_area_faces_retained_in_original': int((norm == 0).sum()),
        'eligible_faces': len(ids), 'eligible_edge_components': int(count), 'selected': selected_metadata,
        'selected_npz_sha256': sha(args.output/'selected-source.npz'),
        'source_geometry_modified': False, 'full_head_created': False,
        'functional_anatomy_identified': False, 'physical_acceptance': False, 'manufacturing_authorized': False}
    save(args.output/'selection.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
