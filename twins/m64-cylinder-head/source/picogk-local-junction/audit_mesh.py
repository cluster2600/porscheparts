#!/usr/bin/env python3
"""Independent raw STL audit; exact duplicate-vertex indexing, no face removal."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def topology(mesh):
    import numpy as np
    import trimesh
    # STL repeats vertices per triangle. Only EXACTLY equal coordinates are
    # indexed together; no rounding, face removal, fixing, or smoothing.
    vertices, inverse = np.unique(mesh.vertices, axis=0, return_inverse=True)
    welded = trimesh.Trimesh(vertices, inverse[mesh.faces], process=False)
    _, counts = np.unique(welded.edges_sorted, axis=0, return_counts=True)
    zero = int(np.count_nonzero(welded.area_faces == 0))
    return {
        'faces': len(welded.faces), 'exact_unique_vertices': len(welded.vertices),
        'watertight': bool(welded.is_watertight),
        'winding_consistent': bool(welded.is_winding_consistent),
        'exact_zero_area_faces': zero,
        'boundary_edges_incidence_one': int(np.count_nonzero(counts == 1)),
        'edges_incidence_above_two': int(np.count_nonzero(counts > 2)),
        'surface_components_including_degenerate_faces': len(welded.split(only_watertight=False)),
        'components_are_not_interpreted_as_physical_voids': True,
        'signed_triangle_volume': float(welded.volume),
        'strict_raw_mesh_screen_pass': bool(welded.is_watertight and welded.is_winding_consistent and zero == 0 and welded.volume > 0),
    }


def run(directory, output):
    import numpy as np
    import trimesh
    if output.exists():
        raise FileExistsError(output)
    start = time.monotonic()
    source_report = directory/'run-report.json'
    native = json.loads(source_report.read_text())
    rows = {}
    for name in ('before', 'after', 'added'):
        path = directory/(name+'.stl')
        if sha(path) != native['exports'][name]['sha256']:
            raise ValueError('STL does not match native report')
        rows[name] = {'sha256': sha(path), **topology(trimesh.load_mesh(path, process=False))}
    residual = (rows['after']['signed_triangle_volume'] - rows['before']['signed_triangle_volume'] - rows['added']['signed_triangle_volume'])
    report = {
        'schema': 'm64-local-junction-raw-stl-audit/v1',
        'native_report_sha256': sha(source_report), 'auditor_sha256': sha(Path(__file__)),
        'numpy_version': np.__version__, 'trimesh_version': trimesh.__version__,
        'indexing': 'exact_coordinate_duplicate_vertices_only_no_rounding',
        'input_faces_removed': 0, 'source_files_modified': False,
        'meshes': rows, 'global_minus_boolean_added_volume_residual': residual,
        'volume_residual_cause_proved': False,
        'status': 'raw_mesh_screen_pass' if all(r['strict_raw_mesh_screen_pass'] for r in rows.values()) else 'rejected_raw_mesh_screen',
        'finer_resolution_executed': False, 'private_head_processed': False,
        'native_fields_serialized_to_VDB': False,
        'manufacturing_authorized': False, 'elapsed_seconds': time.monotonic()-start,
    }
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'raw_mesh_screen_pass' else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.directory, args.output))
