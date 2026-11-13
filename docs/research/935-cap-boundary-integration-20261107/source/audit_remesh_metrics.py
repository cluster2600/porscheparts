"""Read-only exact quality/condition census and source attribution of the trial."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()

    def load(name):
        spec = importlib.util.spec_from_file_location('local_metric_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    io, exact, oracle, condition, bound, attribution, inspector, vectors = (load(k) for k in
        ('io', 'exact', 'oracle', 'condition', 'bound', 'attribution', 'inspector', 'vectors'))
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    controls = condition.controls(exact, oracle)
    positive = json.loads(Path(job['positive_report']).read_text())
    native = json.loads(Path(job['native_report']).read_text())
    assert positive['all_cells_positive_for_stored_binary_coordinates']
    assert positive['mesh_sha256'] == native['input_sha256'] == io.sha(job['mesh'])
    assert native['native_metrics']['minSICN']['private_indices_sha256'] == io.sha(job['native_bad'])
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells = data['nodes'], data['tets']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    with np.load(job['cavity'], allow_pickle=False) as data:
        used = np.unique(data['new_boundary']); tags = data['boundary_categories']
        assert np.array_equal(data['nodes'][used].view(np.uint64), vertices.view(np.uint64))
        assert np.array_equal(np.searchsorted(used, data['new_boundary']), faces)
    flags, values, fallback, sign_fallback = condition.classify(nodes[cells], exact, oracle)
    severe = np.flatnonzero(flags[:, condition.SEVERE_COLUMN])
    assert len(values) == len(severe)
    floor = bound.Q.from_float(.01)**3
    q_cubes = [bound.tetra_face_bound(points, vectors)['q_tet_cubed'] for points in nodes[cells]]
    bad_q = np.array([i for i, q in enumerate(q_cubes) if q < floor], dtype=np.int64)
    with np.load(job['native_bad'], allow_pickle=False) as data:
        native_bad = data['cell_ids']
    assert len(native_bad) == native['native_metrics']['minSICN']['nonpositive_or_nonfinite_cells']
    source_rows, source_tags, boundary_vertices, _, membership = attribution.surface_join(cells, faces, tags, len(nodes), inspector.records)
    cohorts = {}
    for name, ids in [('mean_ratio_below_0p01', bad_q), ('condition_at_least_1e12', severe), ('native_nonpositive_minSICN', native_bad)]:
        boundary_count = (source_rows[ids] >= 0).sum(axis=1)
        interior_count = (~boundary_vertices[ids]).sum(axis=1)
        histogram = {str(i): int((boundary_count == i).sum()) for i in range(5)}
        assert sum(histogram.values()) == len(ids)
        cohorts[name] = {'cells': len(ids), 'actual_boundary_face_count_histogram': histogram,
            'strictly_interior_vertex_count_histogram': {str(i): int((interior_count == i).sum()) for i in range(5)},
            'four_vertices_incident_to_refined_cap': int(((membership[ids] & np.uint64(2)) != 0).all(axis=1).sum()),
            'contains_generated_interior_vertex': int((cells[ids] >= len(vertices)).any(axis=1).sum()),
            'has_actual_refined_cap_face': int((source_tags[ids] == 2).any(axis=1).sum())}
    private = args.output/'private-quality-cohorts.npz'
    np.savez_compressed(private, bad_mean_ratio_cell_ids=bad_q, severe_cell_ids=severe, native_bad_cell_ids=native_bad)
    values_path = args.output/'private-exact-values.json'
    values_path.write_text(json.dumps({'minimum_q_tet_cubed': str(min(q_cubes)),
        'severe_reciprocal_frobenius_squared': {str(i): str(q) for i, q in values.items()}}, indent=2)+'\n')
    cap = faces[tags == 2]
    edges = np.unique(np.sort(cap[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0)
    lengths = np.linalg.norm(vertices[edges[:, 1]]-vertices[edges[:, 0]], axis=1)
    report = dict(schema='935-local-remesh-quality-attribution-1', source_sha256=io.sha(__file__),
        job_sha256=io.sha(args.job), input_mesh_sha256=io.sha(job['mesh']), controls=controls,
        cells_classified=len(cells), exact_mean_ratio_cubes_evaluated=len(q_cubes),
        all_cells_positive_from_independent_complete_inspection=True,
        condition_counts={key: int(value) for key, value in zip(condition.LABELS, flags.sum(axis=0))},
        exact_severe_values=len(values), condition_fallbacks=fallback, orientation_fallbacks=sign_fallback,
        minimum_mean_ratio_cubed_diagnostic=float(min(q_cubes)), cohorts=cohorts,
        source_boundary_vertices=len(vertices), generated_interior_vertices=len(nodes)-len(vertices),
        refined_cap_edge_length_quantiles_nominal_mm=dict(zip(('minimum', 'median', 'p95', 'maximum'),
            map(float, np.quantile(lengths, [0, .5, .95, 1])))),
        fixed_background_size_nominal_mm=2.,
        background_size_to_cap_median_edge_ratio=float(2./np.median(lengths)),
        tag_meaning={'0': 'unchanged_numerical_internal_interface', '1': 'unchanged_hypothesis_head_surface', '2': 'refined_construction_cap'},
        membership_is_exact_coplanarity_proof=False, sizing_or_frame_cause_proven=False,
        native_metrics_clamped_or_discarded=False, private_cohorts_sha256=io.sha(private),
        private_exact_values_sha256=io.sha(values_path), accepted_for_head_integration=False,
        head_volume_modified=False, physics_admitted=False, manufacturing_qualified=False,
        new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
