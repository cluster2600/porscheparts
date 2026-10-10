"""Read-only STL topology and line-section diagnostics; no facet repair/export."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import trimesh
import pyvista as pv

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "baseline-fluid-004"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexed(path):
    raw = trimesh.load_mesh(path, process=False)
    v, inv = np.unique(raw.triangles.reshape(-1, 3), axis=0, return_inverse=True)
    return trimesh.Trimesh(v, inv.reshape(-1, 3), process=False, validate=False)


def edges(f):
    return np.unique(np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0, return_counts=True)


def topology(v, f):
    used = np.unique(f)
    e, count = edges(f)
    chi = len(used) - len(e) + len(f)
    boundary = e[count == 1]
    loops = 0
    regular = True
    if len(boundary):
        bv, inv = np.unique(boundary, return_inverse=True)
        be = inv.reshape(-1, 2)
        degree = np.bincount(be.ravel(), minlength=len(bv))
        regular = bool(np.all(degree == 2))
        graph = coo_matrix((np.ones(len(be)), (be[:, 0], be[:, 1])), shape=(len(bv), len(bv))).tocsr()
        loops = connected_components(graph, directed=False, return_labels=False)
    labels = np.full(len(v), -1, dtype=np.int64); labels[used] = np.arange(len(used))
    mapped = labels[e]
    graph = coo_matrix((np.ones(len(e)), (mapped[:, 0], mapped[:, 1])), shape=(len(used), len(used))).tocsr()
    components = connected_components(graph, directed=False, return_labels=False)
    genus = (2 * components - loops - chi) / 2 if regular and np.all(count <= 2) else None
    tri = v[f]
    signed = np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    return {"vertices": len(used), "edges": len(e), "faces": len(f), "euler": chi,
            "connected_components": components, "boundary_edges": len(boundary), "boundary_loops": loops,
            "regular_boundary": regular, "nonmanifold_edges": int(np.count_nonzero(count > 2)),
            "sum_genus_if_regular_orientable": genus, "signed_volume_mm3_if_closed": float(signed) if not len(boundary) else None,
            "bounds_mm": [v[used].min(axis=0).tolist(), v[used].max(axis=0).tolist()]}


def main():
    output = BASE / 'fluid-topology-diagnostic.json'
    if output.exists():
        raise ValueError('Refusing to overwrite receipt')
    names = ['fluid.stl', 'rotor-union.stl', 'compressor-wheel-source.stl', 'shaft-source.stl', 'compressor-nut-source.stl']
    result = {"status": "diagnostic_only", "mesh_modified": False, "engineering_validated": False,
              "input_sha256": {name: sha(SOURCE/name) for name in names}, "script_sha256": sha(Path(__file__)),
              "units": "mm", "meshes": {}, "source_voxel_mm": .5, "fine_background_cell_mm": .9,
              "fine_surface_cell_nominal_mm": .45}
    tracked = {}
    for name in names:
        mesh = indexed(SOURCE/name)
        groups = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1, engine='scipy')
        result['meshes'][name] = [topology(mesh.vertices, mesh.faces[group]) for group in groups]
        if name in ('fluid.stl', 'rotor-union.stl'):
            # Rotor-like shell has broad XY extent and upper end near Z31.5.
            group = next(g for g in groups if 31 < np.max(mesh.vertices[mesh.faces[g], 2]) < 32)
            tracked[name] = (mesh.vertices, mesh.faces[group])
        if name == 'fluid.stl':
            fluid = mesh
    cuts = [0, 5, 10, 15, 20, 23, 24, 24.5, 24.75, 25, 25.25, 25.5, 25.75, 26, 27, 30, 32]
    result['shell_prefix_subcomplexes'] = {}
    for name, (v, f) in tracked.items():
        prefix = []
        for z in cuts:
            selected = f[np.max(v[f, 2], axis=1) <= z]
            t = topology(v, selected)
            prefix.append({'all_face_vertices_z_at_most_mm': z, **t})
        result['shell_prefix_subcomplexes'][name] = prefix
    poly = pv.PolyData(fluid.vertices, np.column_stack([np.full(len(fluid.faces), 3), fluid.faces]).ravel())
    samples = []
    radii = [6, 8, 10, 15, 20, 25, 27, 28, 29, 29.5]
    for radius in radii:
        for degrees in np.arange(0, 360, 5):
            a = np.deg2rad(degrees)
            x, y = radius * np.cos(a), radius * np.sin(a)
            intersections, _ = poly.ray_trace([x, y, -10], [x, y, 45])
            values = np.sort(intersections[:, 2])
            values = values[np.concatenate([[True], np.diff(values) > 1e-7])]
            if len(values) % 2:
                raise ValueError(f'Odd ray crossings at {radius},{degrees}: {values}')
            intervals = values.reshape(-1, 2)
            rear = intervals[(intervals[:, 0] < -3.2) & (intervals[:, 1] < -2)]
            if len(rear) != 1:
                raise ValueError(f'Expected single rear interval at {radius},{degrees}: {intervals}')
            lower, upper = rear[0]
            samples.append({'radius_mm': radius, 'angle_deg': int(degrees), 'xy_mm': [float(x), float(y)],
                            'floor_z_mm': float(lower), 'wheel_z_mm': float(upper), 'gap_mm': float(upper-lower)})
    gap = np.array([row['gap_mm'] for row in samples])
    result['rear_passage'] = {'method': 'VTK OBBTree line intersections with the exact fluid STL; sorted crossings paired from an exterior start; repeated edge hits deduplicated at 1e-7 mm. No remeshing.',
                              'sample_count': len(samples), 'radii_mm': radii, 'angle_step_deg': 5,
                              'gap_percentiles_mm': {str(q): float(np.percentile(gap, q)) for q in [0, 5, 50, 95, 100]},
                              'minimum_sample': samples[int(np.argmin(gap))],
                              'minimum_gap_over_source_voxel': float(gap.min()/.5),
                              'minimum_gap_over_fine_surface_cell': float(gap.min()/.45),
                              'samples': samples, 'global_minimum_proven': False}
    result['limitations'] = ['Euler is calculated from exactly coincident vertex indexing without merging by tolerance or facet removal.',
                            'Prefix topology uses unmodified existing facets entirely below the cut; it localizes handles approximately, without clipped/capped meshes.',
                            'Line sampling gives observed passage thicknesses, not a proven global minimum or boundary-layer resolution.',
                            'No topology gate or mesh has been changed.']
    for name, expected in result['input_sha256'].items():
        if sha(SOURCE/name) != expected:
            raise ValueError('Source changed during diagnostic')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({'meshes': result['meshes'], 'rear_passage': {k:v for k,v in result['rear_passage'].items() if k!='samples'}}, indent=2))


if __name__ == '__main__':
    main()
