"""Independently count passages and compare protected triangles after native root additions."""
import json
import numpy as np
import trimesh
from locate_surface_cycles import surface_cycles
from run_reconstruction import ROOT, fresh, save, sha


def triangle_keys(triangles):
    order = np.lexsort((triangles[:, :, 2], triangles[:, :, 1], triangles[:, :, 0]), axis=1)
    rows = np.ascontiguousarray(triangles[np.arange(len(triangles))[:, None], order].reshape(-1, 9))
    return np.sort(rows.view(np.dtype((np.void, rows.dtype.itemsize*9))).ravel())


control = np.array([[[0., 0, 0], [1, 0, 0], [0, 1, 0]], [[1., 0, 0], [1, 1, 0], [0, 1, 0]]])
assert np.array_equal(triangle_keys(control), triangle_keys(control[::-1, ::-1]))
changed = control.copy(); changed[0, 0, 2] = .01
assert not np.array_equal(triangle_keys(control), triangle_keys(changed))
phase = ROOT/'work/935-snap-resume-20261025'; parent = phase/'root-screen-001'
proof = json.loads((parent/'receipt.json').read_text())
execution = json.loads((phase/'root-screen-execution.json').read_text())
assert execution['exit'] == 0 and execution['inputs_unchanged'] and proof['input_sha256'] == 'f32bbabab3e5f7d9ca7c5283d18703cfe7cedbd3eb2c72a57a1c222c0a9df1e5'
out = fresh(phase/'root-audit-001'); baseline = None; results = []
for variant in proof['variants']:
    path = parent/variant['mesh']['file']; expected = variant['mesh']['sha256']
    assert sha(path) == expected
    mesh = trimesh.load_mesh(path, process=False)
    vertices, inverse = np.unique(mesh.vertices, axis=0, return_inverse=True)
    faces = inverse[mesh.faces]
    cycles, topology = surface_cycles(vertices, faces)
    tri = vertices[faces]; radii = np.linalg.norm(tri[:, :, :2], axis=2)
    protected = {name: triangle_keys(tri[mask]) for name, mask in
                 [('acquired_region_r98', radii.max(axis=1) >= 98), ('bore_region_r24', radii.min(axis=1) <= 24)]}
    if baseline is None: baseline = protected
    unchanged = {name: np.array_equal(values, baseline[name]) for name, values in protected.items()}
    volume = float(np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()/6)
    assert all(unchanged.values()) and volume > 0 and sha(path) == expected
    np.savez_compressed(out/(path.stem+'.npz'), vertices=vertices, faces=faces,
                        **{f'cycle_{i:02d}': cycle for i, cycle in enumerate(cycles)})
    results.append(dict(closing_radius_source_units=variant['closing_radius_mm'], input_sha256=expected,
                        **topology, protected_triangle_identity_to_revoxelized_baseline=unchanged,
                        protected_triangles={k: len(v) for k, v in protected.items()},
                        volume_source_units_cubed=volume,
                        indexed_npz_sha256=sha(out/(path.stem+'.npz'))))
    print(json.dumps(results[-1]), flush=True)
save(out/'assessment.json', dict(source_sha256=sha(__file__), helper_sha256=sha(ROOT/'twins/935-horizontal-cooling-system-f0/source/locate_surface_cycles.py'),
     native_receipt_sha256=sha(parent/'receipt.json'), variants=results,
     reference='new zero-closing revoxelization; not original PicoGK triangles or measured hardware',
     self_intersection_certificate_pending=True, complete_original_surface_bound_pending=True,
     scale_verified=False, CFD_accepted=False, manufacturing_authorized=False))
