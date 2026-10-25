"""Optimize an imported T4 volume; independently require its complete boundary unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boundary_coordinates(vertices, faces):
    triangles = vertices[faces]
    # Canonical coordinates survive node renumbering, but never geometric movement.
    return sorted(tuple(sorted(map(tuple, triangle))) for triangle in triangles)


def optimize(vertices, cells, faces, method):
    import gmsh
    if gmsh.__version__ != '4.15.2':
        raise ValueError('Pinned Gmsh 4.15.2 required')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 2)
        gmsh.model.add('retained-carrier-volume')
        gmsh.model.addDiscreteEntity(2, 1)
        gmsh.model.addDiscreteEntity(3, 1, [1])
        gmsh.model.mesh.addNodes(3, 1, np.arange(1, len(vertices)+1), vertices.ravel())
        gmsh.model.mesh.addElementsByType(1, 2, [], (faces+1).ravel())
        gmsh.model.mesh.addElementsByType(1, 4, [], (cells+1).ravel())
        gmsh.model.mesh.reclassifyNodes()
        gmsh.model.mesh.optimize(method, force=True, niter=3, dimTags=[(3, 1)])
        tags, coordinates, _ = gmsh.model.mesh.getNodes()
        lookup = np.full(int(max(tags))+1, -1, dtype=np.int64)
        lookup[tags] = np.arange(len(tags))
        _, tetrahedra = gmsh.model.mesh.getElementsByType(4, 1)
        _, boundary = gmsh.model.mesh.getElementsByType(2, 1)
        return np.asarray(coordinates).reshape(-1, 3), lookup[tetrahedra].reshape(-1, 4), lookup[boundary].reshape(-1, 3)
    finally:
        gmsh.finalize()


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--mesh', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--method', choices=['default', 'Netgen', 'Relocate3D'], required=True)
    a = p.parse_args()
    if a.output.exists() or sha(a.mesh) != a.expected_sha256:
        raise ValueError('Fresh output and exact input identity required')
    with np.load(a.mesh, allow_pickle=False) as data:
        v, t, f = (data[k].copy() for k in ['vertices', 'tetrahedra', 'boundary'])
    if v.ndim != 2 or v.shape[1] != 3 or t.ndim != 2 or t.shape[1] != 4 or f.ndim != 2 or f.shape[1] != 3 or not np.isfinite(v).all():
        raise ValueError('Complete finite T4 volume required')
    if t.min() < 0 or f.min() < 0 or max(t.max(), f.max()) >= len(v):
        raise ValueError('Invalid indexed volume')
    a.output.mkdir(parents=True)
    start = time.monotonic()
    vertices, cells, faces = optimize(v, t, f, '' if a.method == 'default' else a.method)
    same = boundary_coordinates(v, f) == boundary_coordinates(vertices, faces)
    positive = bool(np.all(np.linalg.det(np.stack([vertices[cells[:, j]]-vertices[cells[:, 0]] for j in (1, 2, 3)], axis=2)) > 0))
    target = a.output/'volume.npz'
    np.savez_compressed(target, vertices=vertices, tetrahedra=cells, boundary=faces)
    used = np.unique(faces)
    mapping = np.full(len(vertices), -1, dtype=np.int64)
    mapping[used] = np.arange(len(used))
    surface = a.output/'boundary.mesh64'
    with surface.open('w') as stream:
        stream.write(f'{len(used)} {len(faces)}\n')
        np.savetxt(stream, vertices[used], fmt='%.17g')
        np.savetxt(stream, mapping[faces], fmt='%d')
    report = dict(status='boundary_preserving_float_checkpoint' if same and positive else 'optimization_refused',
                  gmsh_version='4.15.2', method=a.method, iterations_requested=3, threads_requested=2,
                  input_nodes=len(v), input_cells=len(t), output_nodes=len(vertices), output_cells=len(cells),
                  exact_boundary_coordinate_and_triangle_identity=same, positive_float_determinants=positive,
                  elapsed_seconds=time.monotonic()-start, mechanical_mesh_admitted=False,
                  pending=['independent exact orientation, indexed boundary and connectivity audit', 'complete quality comparison', 'new mechanical fields'],
                  source_sha256={str(a.mesh):sha(a.mesh), str(Path(__file__)):sha(Path(__file__))},
                  output_sha256={x.name:sha(x) for x in [target, surface]})
    (a.output/'assessment.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 0 if same and positive else 2


if __name__ == '__main__':
    raise SystemExit(main())
