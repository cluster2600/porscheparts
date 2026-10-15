"""Transfer retained V5 solver samples, with explicit sparse-grid information loss."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulate import elements

V5_STL_SHA256 = '22e8ba507dbd91827810bda54cfee7fcfe4723f98365100e5d567cb2d0d746f0'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sparse_bins(xyz, values, pitch):
    """Keep the maximum-magnitude sample in each occupied bin, never average peaks."""
    xyz, values = np.asarray(xyz, float), np.asarray(values, float)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) == 0
            or values.ndim != 2 or len(values) != len(xyz)
            or values.shape[1] not in (1, 3) or not np.isfinite(xyz).all()
            or not np.isfinite(values).all() or not np.isfinite(pitch) or pitch <= 0):
        raise ValueError('Finite positions, scalar/vector samples and positive pitch required')
    with np.errstate(over='ignore'):
        scaled = xyz/pitch
    if not np.isfinite(scaled).all() or np.max(abs(scaled)) > 1e8:
        raise ValueError('Coordinates exceed the supported diagnostic grid range')
    indices = np.rint(scaled).astype(np.int64)
    order = np.argsort(np.linalg.norm(values, axis=1), kind='stable')
    # shortcut: sparse diagnostic binning, not FE interpolation; use a conservative
    # tensor/shape-function transfer before using these grids in a new solve.
    selected = {}
    for i in order:
        selected[tuple(indices[i])] = int(i)
    selected = np.array([selected[k] for k in sorted(selected)])
    rows = np.c_[indices[selected]*pitch, values[selected]].astype(np.float32)
    return rows, {'input_samples': len(xyz), 'occupied_bins': len(rows),
                  'discarded_colliding_samples': len(xyz)-len(rows),
                  'max_position_quantization_mm': float(np.linalg.norm(indices*pitch-xyz, axis=1).max()),
                  'original_peak_magnitude': float(np.linalg.norm(values, axis=1).max()),
                  'stored_peak_magnitude': float(np.linalg.norm(rows[:, 3:].astype(float), axis=1).max())}


def prepare(mesh_folder, stl, output):
    folder, stl, output = map(Path, (mesh_folder, stl, output))
    if sha(stl) != V5_STL_SHA256:
        raise ValueError('Expected the frozen V5 STL in the original solver frame')
    result = json.loads((folder/'combined-rigid-static.json').read_text())
    if sha(folder/'mesh.inp') != result['mesh_sha256']:
        raise ValueError('Mesh differs from the retained solve')
    if sha(folder/'combined-rigid-static.inp') != result['input_sha256']:
        raise ValueError('Solver input differs from the retained solve')
    data = np.load(folder/'combined-rigid-static.npz', allow_pickle=False)
    mesh = np.load(folder/'mesh.npz', allow_pickle=False)
    assert np.array_equal(data['tags'], mesh['tags']) and np.array_equal(data['xyz'], mesh['xyz'])
    assert np.isclose(np.linalg.norm(data['displacement'], axis=1).max(), result['displacement_max_mm'])
    assert np.isclose(data['VM'].max(), result['integration_point_VM_max_MPa'])
    connectivity = elements(folder/'mesh.inp')
    ids = np.array(sorted(connectivity))
    assert np.array_equal(np.unique(data['element_ids']), ids)
    node_index = {int(tag): i for i, tag in enumerate(data['tags'])}
    xyz = data['xyz']
    centres = np.array([xyz[[node_index[n] for n in connectivity[int(e)][:4]]].mean(0) for e in ids])
    peaks = np.full(len(ids), -np.inf)
    np.maximum.at(peaks, np.searchsorted(ids, data['element_ids']), data['VM'])
    assert np.isfinite(peaks).all() and (peaks >= 0).all()
    pitch = .5
    u, u_info = sparse_bins(data['xyz'], data['displacement'], pitch)
    vm, vm_info = sparse_bins(centres, peaks[:, None], pitch)
    assert np.isclose(vm_info['stored_peak_magnitude'], data['VM'].max(), rtol=1e-6)
    output.mkdir(parents=True, exist_ok=False)
    fields = {'voxel_mm': pitch, 'geometry_sha256': V5_STL_SHA256,
              'displacement_rows_xyz_ux_uy_uz_mm': u.tolist(),
              'element_peak_rows_xyz_mm_vm_MPa': vm.tolist()}
    (output/'samples.json').write_text(json.dumps(fields, separators=(',', ':'), allow_nan=False)+'\n')
    inputs = [stl, folder/'mesh.inp', folder/'mesh.npz', folder/'combined-rigid-static.inp',
              folder/'combined-rigid-static.npz', folder/'combined-rigid-static.json']
    receipt = {'source_geometry': 'Frozen V5 only; original XYZ frame in mm, no print transform',
               'solver_case': 'combined-rigid-static: 4000 N in -Z plus 850000 Nmm about Y',
               'source_displacement_max_mm': result['displacement_max_mm'],
               'source_integration_point_VM_max_MPa': result['integration_point_VM_max_MPa'],
               'displacement_transfer': u_info, 'stress_transfer': vm_info,
               'stress_location': 'Maximum of four integration-point von Mises values per C3D10 element, assigned to corner centroid then binned; not a stress tensor or a nodal interpolation',
               'empty_bins': 'No measurement; never interpret as zero stress or displacement',
               'collision_rule': 'Maximum magnitude sample; displacement vector direction of the selected sample retained',
               'candidate_fields_valid': False, 'new_solver_executed': False,
               'manufacturing_authorized': False,
               'inputs': {p.name: sha(p) for p in inputs}, 'samples_sha256': sha(output/'samples.json')}
    (output/'transfer.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: receipt[k] for k in ('displacement_transfer', 'stress_transfer')}))


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('Usage: prepare.py RETAINED_MESH_FOLDER ORIGINAL_V5_STL NEW_OUTPUT')
    prepare(*sys.argv[1:])
