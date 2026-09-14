#!/usr/bin/env python3
"""Witness-only countertrial: remove zero-cross-product faces, move no vertex."""
import argparse
import hashlib
import json
from pathlib import Path

from audit_mesh import sha, topology


def countertrial(mesh):
    import numpy as np
    import trimesh
    vertices, inverse = np.unique(mesh.vertices, axis=0, return_inverse=True)
    faces = inverse[mesh.faces]
    cross = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                     vertices[faces[:, 2]] - vertices[faces[:, 0]])
    # Zero tolerance, evaluated in float64. This is not a symbolic exact
    # predicate for arbitrary real coordinates. No near-zero face is removed.
    keep = np.any(cross != 0, axis=1)
    result = trimesh.Trimesh(vertices, faces[keep], process=False)
    _, counts = np.unique(np.sort(result.faces, axis=1), axis=0, return_counts=True)
    return {
        'input_faces': len(faces), 'removed_zero_cross_product_faces': int((~keep).sum()),
        'remaining_duplicate_face_groups': int(np.count_nonzero(counts > 1)),
        'vertex_displacement': 0, 'remaining_face_orientation_changed': False,
        'remaining_oriented_faces_sha256': hashlib.sha256(
            np.asarray(vertices[result.faces], dtype='<f8').tobytes()).hexdigest(),
        'audit': topology(result),
    }


def run(directory, output):
    import numpy as np
    import trimesh
    if output.exists():
        raise FileExistsError(output)
    native_path = directory / 'run-report.json'
    native = json.loads(native_path.read_text())
    if native.get('schema') != 'm64-picogk-local-junction-witness/v1' or native.get('private_head_processed') is not False:
        raise ValueError('Only a recorded synthetic witness is accepted')
    rows = {}
    for name in ('before', 'after', 'added'):
        path = directory / (name + '.stl')
        if sha(path) != native['exports'][name]['sha256']:
            raise ValueError('STL differs from recorded native output')
        rows[name] = {'source_sha256': sha(path), **countertrial(trimesh.load_mesh(path, process=False))}
    passed = all(row['audit']['strict_raw_mesh_screen_pass'] for row in rows.values())
    report = {
        'schema': 'm64-picogk-exact-zero-face-countertrial/v1',
        'native_report_sha256': sha(native_path), 'script_sha256': sha(Path(__file__)),
        'mesh_auditor_sha256': sha(Path(__file__).with_name('audit_mesh.py')),
        'numpy_version': np.__version__, 'trimesh_version': trimesh.__version__,
        'predicate': 'float64_cross_product_all_components_equal_zero_no_tolerance',
        'status': 'mesh_screen_pass' if passed else 'rejected_mesh_screen', 'meshes': rows,
        'source_files_modified': False, 'derived_meshes_written': False,
        'original_rejection_overridden': False, 'continuous_geometry_equivalence_proved': False,
        'private_head_processed': False, 'CFD_qualified': False, 'manufacturing_authorized': False,
    }
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if passed else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.directory, args.output))
