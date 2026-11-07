"""Check the complete accepted peel chain against one immutable numerical parent."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def kept_rows(count, removed):
    assert count > 0 and removed.ndim == 1 and removed.dtype.kind in 'iu'
    assert np.all((removed >= 0) & (removed < count))
    assert len(np.unique(removed)) == len(removed)
    keep = np.ones(count, dtype=bool)
    keep[removed] = False
    return np.flatnonzero(keep)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    first = kept_rows(5, np.array([1, 3]))
    assert np.array_equal(first, [0, 2, 4])
    assert np.array_equal(first[kept_rows(len(first), np.array([1]))], [0, 4])
    for invalid in (np.array([1, 1]), np.array([-1]), np.array([5]), np.array([1.5])):
        try:
            kept_rows(5, invalid)
        except AssertionError:
            pass
        else:
            raise AssertionError('Invalid deletion mapping admitted')
    assert sha(job['parent']) == 'd618763474f2eeb7bf680ce18f6f2efce22795e538263b7dfc639ffb68be62c5'
    assert sha(job['interval_helper']) == 'b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71'
    spec = importlib.util.spec_from_file_location('chain_fraction_determinants', job['interval_helper'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    determinant_controls = helper.controls()
    with np.load(job['parent'], allow_pickle=False) as data:
        original_nodes, original_cells, previous_faces = data['nodes'], data['tets'], data['boundary']
    retained = np.arange(len(original_cells))
    removed_original, exact_loss, certified_loss, summaries = [], Fraction(0), Fraction(0), []
    previous_sha = sha(job['parent'])
    for number, row in enumerate(job['rounds'], 1):
        proof, volume, surface, condition, native = (
            json.loads(Path(row[key]).read_text())
            for key in ('proof', 'volume_report', 'surface_report', 'condition_report', 'native_report'))
        candidate_sha, surface_sha = sha(row['candidate']), sha(row['surface'])
        assert proof['source_sha256'] == sha(row['verifier_source'])
        assert condition['source_sha256'] == sha(row['condition_source'])
        assert volume['source_sha256'] == sha(job['interval_helper'])
        assert native['source_sha256'] == 'e9a4b8cb0805ddaa779f307ba7c0b89c17a679a3915028487a28879a73ecf484'
        assert proof['input_mesh_sha256'] == previous_sha == condition['parent_mesh_sha256']
        assert proof['candidate_volume_sha256'] == volume['mesh_sha256'] == condition['input_mesh_sha256'] == native['input_sha256'] == candidate_sha
        assert proof['candidate_surface_sha256'] == volume['surface_sha256'] == surface['input_sha256'] == surface_sha
        assert native['input_report_sha256'] == sha(row['volume_report'])
        assert native['msh_sha256'] == sha(row['native_mesh'])
        assert surface['three_mf_sha256'] == sha(row['checker_three_mf'])
        assert surface['three_mf_all_coordinates_and_indices_roundtrip_exact']
        assert surface['geometry_export_gate_passed']
        assert volume['all_cells_positive_for_stored_binary_coordinates'] and volume['actual_complete_boundary_and_orientation_exact']
        assert native['native_import_all_arrays_exact'] and native['native_readback_all_arrays_exact']
        assert condition['fresh_counts_equal_independent_exact_deletion_prediction']
        assert not proof['physics_admitted'] and not native['physics_admitted']
        removed = np.load(row['removed'], allow_pickle=False)
        assert len(removed) == proof['removed_tetrahedra'] == condition['removed_cells'] > 0
        next_kept = kept_rows(len(retained), removed)
        with np.load(row['proposal'], allow_pickle=False) as data:
            assert np.array_equal(np.sort(data['cell_ids']), removed)
            changed_rows = data['source_surface_face_ids'].reshape(-1)
        original_ids = retained[removed]
        assert len(np.unique(original_ids)) == len(original_ids)
        removed_original.extend(map(int, original_ids))
        for cell in original_cells[original_ids]:
            determinant = helper.exact_determinant(original_nodes[cell])
            assert determinant > 0
            exact_loss += determinant/6
        certified_loss += Fraction(*map(int, proof['exact_material_loss_fraction']))
        retained = retained[next_kept]
        assert volume['tetrahedra'] == native['tetrahedra'] == proof['retained_tetrahedra'] == len(retained)
        with np.load(row['candidate'], allow_pickle=False) as data:
            nodes, cells, faces = data['nodes'], data['tets'], data['boundary']
        assert np.array_equal(nodes.view(np.uint64), original_nodes.view(np.uint64))
        assert np.array_equal(cells, original_cells[retained])
        assert faces.shape == previous_faces.shape and len(faces) == volume['boundary_faces']
        assert changed_rows.dtype.kind in 'iu'
        assert len(changed_rows) == len(np.unique(changed_rows)) == 2*len(removed)
        assert np.all((changed_rows >= 0) & (changed_rows < len(previous_faces)))
        untouched = np.ones(len(previous_faces), dtype=bool)
        untouched[changed_rows] = False
        assert np.array_equal(faces[untouched], previous_faces[untouched])
        with np.load(row['surface'], allow_pickle=False) as data:
            assert np.array_equal(data['triangles'], faces)
            assert np.array_equal(data['vertices'].view(np.uint64), nodes[:len(data['vertices'])].view(np.uint64))
        previous_faces = faces
        previous_sha = candidate_sha
        summaries.append(dict(round=number, removed_cells=len(removed), retained_cells=len(retained),
                              candidate_sha256=candidate_sha, surface_sha256=surface_sha,
                              severe_cells=condition['counts_kappa_F_at_least']['1e12'],
                              nonpositive_native_shape_cells=native['native_metrics']['minSICN']['nonpositive_or_nonfinite_cells']))
        del nodes, cells
    assert len(set(removed_original)) == len(removed_original)
    assert len(original_cells)-len(retained) == len(removed_original)
    assert exact_loss == certified_loss
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.save(args.output/'private-original-removed-cell-ids.npy', np.asarray(removed_original, dtype=np.int64))
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), rounds=summaries,
                  cumulative_removed_cells=len(removed_original), original_cells=len(original_cells),
                  final_cells=len(retained), every_coordinate_bit_matches_one_immutable_parent=True,
                  every_final_tetrahedron_tuple_matches_parent_subset=True, each_surface_change_confined_to_certified_rows=True,
                  all_report_and_actual_artifact_identities_cross_checked=True,
                  exact_cumulative_loss_independently_recomputed=True,
                  exact_loss_fraction=[str(exact_loss.numerator), str(exact_loss.denominator)],
                  literal_mapping_and_duplicate_range_dtype_refusal_controls_passed=True,
                  exact_determinant_controls=determinant_controls,
                  geometry_modified_by_this_audit=False, field_solve_executed=False, physics_admitted=False,
                  manufacturing_qualified=False, new_paid_compute_usd=0)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
