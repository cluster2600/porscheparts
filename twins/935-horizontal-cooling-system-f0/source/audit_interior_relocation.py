#!/usr/bin/env python3
"""Independently audit an interior-node relocation without changing its boundary."""
import argparse
import json
from pathlib import Path
import shutil
import time

import numpy as np

from import_conforming_volume import ROOT, exact_orientation, helper
from prepare_conforming_surface import sha


def fixed_geometry(parent, candidate):
    v, cells, boundary = (parent[k] for k in ('vertices', 'tetrahedra', 'boundary'))
    xyz, new_cells, new_boundary = (candidate[k] for k in ('vertices', 'tetrahedra', 'boundary'))
    if (xyz.shape != v.shape or not np.isfinite(xyz).all()
            or not np.array_equal(new_cells, cells) or not np.array_equal(new_boundary, boundary)):
        raise ValueError('Finite matching nodes and unchanged connectivity required')
    fixed = np.unique(boundary)
    if not np.array_equal(xyz[fixed], v[fixed]):
        raise ValueError('Every certified boundary coordinate must remain exact')
    return dict(boundary_coordinates_exactly_preserved=True, connectivity_exactly_preserved=True,
                moved_interior_nodes=int(np.any(xyz != v, axis=1).sum()),
                maximum_interior_shift_native_units=float(np.linalg.norm(xyz - v, axis=1).max()))


def audit(parent, optimized, output):
    parent, optimized, output = map(Path, (parent, optimized, output))
    if output.exists() or not output.parent.is_dir():
        raise ValueError('Fresh private output required')
    for folder in output.resolve().parents:
        if (folder / '.git').exists() and output.resolve().relative_to(folder).parts[0] != 'work':
            raise ValueError('Private work/ output required')
    start = time.monotonic()
    baseline = json.loads((parent / 'assessment.json').read_text())
    proposal = json.loads((optimized / 'assessment.json').read_text())
    execution = json.loads((optimized / 'execution.json').read_text())
    parent_hash, candidate_hash = sha(parent / 'volume.npz'), sha(optimized / 'volume.npz')
    workers = {'Relocate3D': 'relocate_conforming_volume.py',
               'StarKernelLinearProgram': 'optimize_interior_stars.py'}
    if proposal.get('optimizer') not in workers:
        raise ValueError('Known interior optimizer required')
    worker = Path(__file__).with_name(workers[proposal['optimizer']])
    if (baseline['schema'] != '935-conforming-volume-audit-v1'
            or baseline['status'] != 'topology_and_exact_orientation_passed'
            or baseline['volume_npz_sha256'] != parent_hash or baseline['scale_verified'] is not False
            or proposal['status'] != 'interior_relocated_not_audited'
            or proposal['source_sha256'] != sha(worker) or proposal['volume_npz_sha256'] != candidate_hash
            or proposal['input_sha256'] != parent_hash or execution['input_sha256'] != parent_hash
            or execution['exit'] != 0 or execution['stop_reason'] is not None
            or execution['worker_sha256'] != sha(worker)
            or proposal['mechanical_mesh_admitted'] is not False
            or proposal['manufacturing_authorized'] is not False):
        raise ValueError('Matching completed relocation and audited parent required')
    paths = [parent / 'assessment.json', parent / 'volume.npz', optimized / 'assessment.json',
             optimized / 'execution.json', optimized / 'volume.npz']
    before = {str(p): sha(p) for p in paths}
    with np.load(parent / 'volume.npz', allow_pickle=False) as old, np.load(optimized / 'volume.npz', allow_pickle=False) as new:
        identity = fixed_geometry(old, new)
        vertices, cells, boundary = (new[k].copy() for k in ('vertices', 'tetrahedra', 'boundary'))
    checker = ROOT / 'twins/m64-cylinder-head/source/wholebody/audit_indexed_tetrahedra.py'
    output.mkdir(mode=0o700)
    metrics = helper(checker, '_935_relocated_connectivity').connectivity_metrics(vertices, cells, boundary)
    exact = exact_orientation(vertices, cells, output / 'progress.json')
    same_volume = exact['signed_volume_exact'] == baseline['exact_orientation']['signed_volume_exact']
    all_used = len(np.unique(cells)) == len(vertices)
    passed = (not exact['negative'] and not exact['zero'] and same_volume and all_used
              and metrics['tetra_connected_components'] == 1 and metrics['boundary_matches']
              and not metrics['nonmanifold_faces'] and not metrics['repeated_node_tetrahedra'])
    shutil.copyfile(optimized / 'volume.npz', output / 'volume.npz')
    if any(sha(Path(p)) != value for p, value in before.items()):
        raise ValueError('Input changed during independent audit')
    report = dict(schema='935-conforming-volume-audit-v1',
                  status='topology_and_exact_orientation_passed' if passed else 'volume_refused',
                  derivation='interior_node_relocation_boundary_and_connectivity_unchanged',
                  source_sha256=sha(__file__), helper_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                      (checker, Path(__file__).with_name('import_conforming_volume.py'),
                       Path(__file__).with_name('prepare_conforming_surface.py'))},
                  geometry_sha256=baseline['geometry_sha256'], prepared_receipt_sha256=baseline['prepared_receipt_sha256'],
                  parent_volume_audit_sha256=sha(parent / 'assessment.json'), parent_volume_npz_sha256=parent_hash,
                  optimizer_assessment_sha256=sha(optimized / 'assessment.json'),
                  optimizer_execution_sha256=sha(optimized / 'execution.json'),
                  vertices=len(vertices), tetrahedra=len(cells), boundary_triangles=len(boundary),
                  exact_boundary_coordinate_triangle_bijection=True, relocation=identity,
                  indexed_connectivity=metrics, exact_orientation=exact, exact_volume_matches_parent=same_volume,
                  all_nodes_used=all_used, volume_npz_sha256=candidate_hash, elapsed_s=time.monotonic() - start,
                  source_unit='uncalibrated_scan_unit', scale_verified=False, quality_screen_completed=False,
                  mechanical_mesh_admitted=False, manufacturing_authorized=False)
    (output / 'assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    return passed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'optimized', 'new_output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.parent, args.optimized, args.new_output) else 2)
