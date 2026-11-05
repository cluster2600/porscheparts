"""Read-only Open3D vertex/edge topology check, independent of remeshing."""
import argparse
import json
from pathlib import Path
import numpy as np
import open3d as o3d


def mesh(v, f):
    return o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v),
                                     o3d.utility.Vector3iVector(f))


def controls():
    v = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,1]], float)
    f = np.array([[0,2,1], [0,1,3], [0,3,2], [1,2,3]], np.int32)
    normal = mesh(v, f)
    pinched = mesh(np.vstack((v, -v[1:])), np.vstack((f, np.where(f == 0, 0, f+3))))
    if not normal.is_vertex_manifold() or pinched.is_vertex_manifold():
        raise SystemExit('Vertex manifold controls failed.')
    if not pinched.is_edge_manifold(allow_boundary_edges=False):
        raise SystemExit('Pinched-vertex control must have manifold edges.')
    return {'closed_tetrahedron_accepted': True,
            'closed_edge_manifold_pinched_vertex_rejected': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args(); checked = controls()
    if args.self_test:
        print(json.dumps(checked)); return
    if not args.input: parser.error('input is required')
    with np.load(args.input, allow_pickle=False) as a:
        v, f = a['vertices'], a['triangles']
    m = mesh(v, f)
    _, counts, _ = m.cluster_connected_triangles()
    result = {'open3d_version': o3d.__version__, 'controls': checked,
              'vertices': len(v), 'triangles': len(f),
              'arrays_preserved': bool(np.array_equal(v, np.asarray(m.vertices)) and
                                       np.array_equal(f, np.asarray(m.triangles))),
              'vertex_manifold': m.is_vertex_manifold(),
              'closed_edge_manifold': m.is_edge_manifold(allow_boundary_edges=False),
              'orientable': m.is_orientable(),
              'euler_characteristic': m.euler_poincare_characteristic(),
              'edge_connected_components': len(counts)}
    print(json.dumps(result))
    if not all(result[k] for k in ('arrays_preserved', 'vertex_manifold', 'closed_edge_manifold', 'orientable')):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
