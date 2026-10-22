"""Restore two original wall facets by moving only the added Steiner point inside."""
from fractions import Fraction
import json
from pathlib import Path
import shutil
import signal

import numpy as np
from import_conforming_volume import table, exact_orientation
from optimize_interior_stars import kernel_target
from rebuild_fluid_edge_stars import outer_oriented
import reconnect_fluid_tetrahedra as base
from prepare_conforming_surface import sha


def cone(points, faces, seeds):
    ids = np.unique(faces)
    local_faces = np.searchsorted(ids, faces)
    children = np.column_stack([np.full(len(faces), len(ids)), local_faces])
    origin = points[ids].mean(axis=0)
    scale = np.ptp(points[ids], axis=0).max()
    assert np.isfinite(scale) and scale > 0
    for seed in [origin, *seeds]:
        v = np.vstack([points[ids], seed])
        proof = exact_orientation(v, children)
        if proof['negative'] or proof['zero']:
            continue
        target = kernel_target((v - origin) / scale, children, len(ids))
        if target is None:
            continue
        target = origin + scale * target
        proof = exact_orientation(np.vstack([points[ids], target]), children)
        if not proof['negative'] and not proof['zero']:
            assert np.array_equal(base.outer_faces(children), np.sort(local_faces, axis=1)[np.lexsort(np.sort(local_faces, axis=1).T[::-1])])
            return target, proof
    raise ValueError('No strictly positive exact kernel cone found')


if __name__ == '__main__':
    signal.alarm(300)
    unit = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    _, control = cone(unit, np.array(base.FACE_NODES), [])
    assert Fraction(control['signed_volume_exact']) == Fraction(1, 6)
    p = Path('/home/lolman/935-reference-fluid-wall-20261022')
    meshed, prepared, out = p / 'tetgen-001', p / 'prepared-001', p / 'restored-001'
    assert not out.exists()
    parent = json.loads((meshed / 'execution.json').read_text())
    proof = json.loads((prepared / 'receipt.json').read_text())
    assert parent['exit'] == 0 and parent['input_smesh_sha256'] == sha(prepared / 'fluid.smesh')
    for name, expected in proof['output_sha256'].items():
        assert sha(prepared / name) == expected
    diagnosis_path = p / 'added-boundary-point-diagnosis-001.json'
    diagnosis = json.loads(diagnosis_path.read_text())
    assert diagnosis['new_boundary_point'] == 445308 and diagnosis['edge'] == [57964, 57968]
    v = table(meshed / 'fluid.1.node', 'node')
    cells = table(meshed / 'fluid.1.ele', 'ele')
    before_hashes = {name: sha(meshed / name) for name in ['fluid.1.node', 'fluid.1.ele', 'fluid.1.face', 'execution.json']}
    assert len(v) <= 1_000_000 and len(cells) <= 10_000_000
    with np.load(prepared / 'boundary.npz') as z:
        reference, boundary, markers = (z[k] for k in ['vertices', 'triangles', 'markers'])
    assert np.array_equal(v[:len(reference)], reference)
    node = diagnosis['new_boundary_point']
    star = np.flatnonzero(np.any(cells == node, axis=1))
    assert star.tolist() == diagnosis['incident_cell_ids'] and cells[star].tolist() == diagnosis['incident_cells']
    old_cavity = outer_oriented(cells[star])
    removed = old_cavity[np.any(old_cavity == node, axis=1)]
    assert len(removed) == 4
    desired = np.vstack([old_cavity[~np.any(old_cavity == node, axis=1)], diagnosis['old_faces']])
    expected_faces = {tuple(sorted(f)) for f in boundary}
    assert all(tuple(sorted(f)) in expected_faces for f in diagnosis['old_faces'])
    centres = v[cells[star]].mean(axis=1)
    seeds = [v[node] + (c - v[node]) * weight for c in centres for weight in [1., .1, .01, .001]]
    target, local_proof = cone(v, desired, seeds)
    children = np.column_stack([np.full(len(desired), node), desired])
    kept = np.ones(len(cells), dtype=bool)
    kept[star] = False
    replacement = np.vstack([cells[kept], children])
    original_node = v[node].copy()
    v[node] = target
    assert np.array_equal(v[:len(reference)], reference) and node not in np.unique(boundary)
    out.mkdir(mode=0o700)
    shutil.copyfile(prepared / 'fluid.smesh', out / 'fluid.smesh')
    for suffix, values, header, fmt in [
        ('node', v, f'{len(v)} 3 0 0', ['%d', '%.17g', '%.17g', '%.17g']),
        ('ele', replacement, f'{len(replacement)} 4 0', '%d'),
        ('face', np.column_stack([boundary, markers]), f'{len(boundary)} 1', '%d'),
    ]:
        with (out / f'fluid.1.{suffix}').open('x') as stream:
            stream.write(header + '\n')
            np.savetxt(stream, np.column_stack([np.arange(len(values)), values]), fmt=fmt)
    assert all(sha(meshed / n) == h for n, h in before_hashes.items())
    record = {'status': 'reference_edge_restored_pending_complete_volume_and_native_quality_audits', 'source_sha256': sha(__file__), 'helper_sha256': {n: sha(Path(__import__(n).__file__)) for n in ['import_conforming_volume', 'optimize_interior_stars', 'rebuild_fluid_edge_stars', 'reconnect_fluid_tetrahedra']}, 'parent_execution_sha256': sha(meshed / 'execution.json'), 'parent_output_sha256': before_hashes, 'diagnosis_sha256': sha(diagnosis_path), 'prepared_receipt_sha256': sha(prepared / 'receipt.json'), 'input_smesh_sha256': sha(prepared / 'fluid.smesh'), 'input_file_unchanged': sha(out / 'fluid.smesh') == sha(prepared / 'fluid.smesh'), 'exit': 0, 'stop_reason': None, 'original_input_coordinates_unchanged': True, 'original_boundary_triangles_and_markers_restored': True, 'removed_cells': len(star), 'replacement_cells': len(children), 'tetrahedra': len(replacement), 'moved_added_Steiner_point': node, 'old_Steiner_coordinates_m': original_node.tolist(), 'new_interior_coordinates_m': target.tolist(), 'new_cavity_exact_orientation': local_proof, 'analytic_unit_cone_volume_exact': control['signed_volume_exact'], 'output_sha256': {f'fluid.1.{s}': sha(out / f'fluid.1.{s}') for s in ['node', 'ele', 'face']}, 'CFD_accepted': False, 'manufacturing_authorized': False}
    (out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
