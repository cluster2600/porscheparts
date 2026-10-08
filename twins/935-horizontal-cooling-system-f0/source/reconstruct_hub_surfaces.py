#!/usr/bin/env python3
"""Fit bounded observed hub patches; within-scan holdout is not metrology."""
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from run_reconstruction import require_result, save, sha


def fit_surface(points, normals, initial, radius_window, kind, normal_weight=2., robust_scale=.3):
    p, n, x0 = np.asarray(points, float), np.asarray(normals, float), np.asarray(initial, float)
    window = np.asarray(radius_window, float)
    if (p.ndim != 2 or p.shape[1] != 3 or n.shape != p.shape or len(p) < 100
            or x0.shape != (5,) or not np.isfinite(p).all() or not np.isfinite(n).all()
            or not np.isfinite(x0).all() or kind not in ('cylinder', 'cone')
            or window.shape != (2,) or not np.isfinite(window).all() or not 0 < window[0] < window[1]
            or not np.isfinite([normal_weight, robust_scale]).all() or normal_weight <= 0 or robust_scale <= 0):
        raise ValueError('Finite surface samples, valid seed and positive fitting scales required')
    axis = np.r_[x0[2:4], 1.]; axis /= np.linalg.norm(axis)
    x = np.cross([0, 1, 0], axis); x /= np.linalg.norm(x)
    q = p - [x0[0], x0[1], 0]
    angle = np.mod(np.arctan2(q @ np.cross(axis, x), q @ x), 2 * np.pi)
    test = (np.floor(angle / np.deg2rad(10)).astype(int) % 4) == 0
    if min(test.sum(), (~test).sum()) < 50:
        raise ValueError('Insufficient independent angular sectors for within-scan holdout')

    def residual(parameters, p, n):
        a = np.r_[parameters[2:4], 1.]; a /= np.linalg.norm(a)
        d = p - [parameters[0], parameters[1], 0]; h = d @ a
        radial = d - np.outer(h, a); r = np.linalg.norm(radial, axis=1)
        slope = parameters[5] if kind == 'cone' else 0.
        return r - parameters[4] - slope * h, n @ a + slope * np.sum(n * radial / np.maximum(r[:, None], 1e-15), axis=1)

    lo, hi = radius_window
    lower, upper = [-hi, -hi, -1, -1, lo * .7], [hi, hi, 1, 1, hi * 1.3]
    if kind == 'cone':
        x0 = np.r_[x0, 0.]; lower += [-1]; upper += [1]
    def objective(parameters):
        distance, normal = residual(parameters, p[~test], n[~test])
        return np.r_[distance, normal_weight * normal]
    fit = least_squares(objective, x0, bounds=(lower, upper), loss='soft_l1', f_scale=robust_scale, max_nfev=1000)
    if not fit.success:
        raise ValueError('Observed surface model did not converge')
    a = np.r_[fit.x[2:4], 1.]; a /= np.linalg.norm(a)
    origin = np.r_[fit.x[:2], 0]; height = (p - origin) @ a
    slope = float(fit.x[5]) if kind == 'cone' else 0.
    error = residual(fit.x, p[test], n[test])[0] / np.sqrt(1 + slope ** 2)
    angular_gap = float(np.rad2deg(np.max(np.diff(np.r_[np.sort(angle), np.min(angle) + 2 * np.pi]))))
    return {'type': kind, 'origin_in_seed_frame_source_units': origin.tolist(), 'axis_in_seed_frame': a.tolist(),
            'radius_at_zero_source_units': float(fit.x[4]), 'radius_slope': slope,
            'axial_span_source_units': [float(height.min()), float(height.max())],
            'heldout_rms_source_units': float(np.sqrt(np.mean(error ** 2))),
            'heldout_absolute_quantiles_source_units': np.quantile(np.abs(error), [.5, .95, .99, 1]).tolist(),
            'test_sample_indices': np.flatnonzero(test).tolist(), 'train_sample_indices': np.flatnonzero(~test).tolist(),
            'maximum_unsampled_angular_gap_deg': angular_gap,
            'distance_definition': 'normal_distance_to_infinite_analytic_surface_crop_edges_excluded',
            'normal_weight_source_units': normal_weight, 'robust_scale_source_units': robust_scale,
            'functional_datum_verified': False}


def reconstruct(case, output):
    import trimesh
    params = require_result(case['sections'], case['sections_sha256'])
    folder = Path(params['observed_mesh']).parent
    raw_path = folder / 'observed.npz'; raw_hash = sha(raw_path)
    raw = np.load(raw_path); mesh = trimesh.Trimesh(raw['vertices'], raw['faces'], process=False)
    specifications = case['hub_surface_selections']; seeds = params['candidate_axis']['fits']
    if len(specifications) != len(seeds):
        raise ValueError('Each observed hub seed requires an explicit private patch selection')
    patches = []
    for i, (selection, seed) in enumerate(zip(specifications, seeds)):
        ids = np.array(seed['sampled_faces']); p, n = mesh.triangles_center[ids], mesh.face_normals[ids]
        axis = np.array(seed['axis_in_seed_frame']); height = (p - seed['origin_in_seed_frame']) @ axis
        lo, hi = selection['axial_interval_source_units']; normal_limit = selection['maximum_normal_axis_abs']
        if not np.isfinite([lo, hi, normal_limit]).all() or lo >= hi or not 0 < normal_limit <= 1:
            raise ValueError('Valid inspected axial window and normal limit required')
        selected = (height > lo) & (height < hi) & (np.abs(n @ axis) < normal_limit)
        initial = np.r_[seed['origin_in_seed_frame'][:2], axis[:2] / axis[2], seed['radius_source_units']]
        models = [fit_surface(p[selected], n[selected], initial, seed['seed_window_source_units'], kind,
                              case['hub_normal_weight'], case['hub_robust_scale_source_units']) for kind in ('cylinder', 'cone')]
        # Prefer the more complex cone only when BOTH held-out RMS and P95 improve.
        preferred = int(models[1]['heldout_rms_source_units'] < models[0]['heldout_rms_source_units'] and
                        models[1]['heldout_absolute_quantiles_source_units'][1] < models[0]['heldout_absolute_quantiles_source_units'][1])
        for model in models:
            model['test_face_indices'] = ids[selected][model.pop('test_sample_indices')].tolist()
            model['train_face_indices'] = ids[selected][model.pop('train_sample_indices')].tolist()
        patches.append({'id': f'hub-patch-{i:02d}', 'selection': selection,
                        'selected_face_indices': ids[selected].tolist(), 'excluded_seed_face_indices': ids[~selected].tolist(),
                        'models': models, 'preferred_model': preferred,
                        'surface_label': 'analytic_fit_of_acquired_patch_with_angular_interpolation',
                        'unobserved_crop_caps_added': False, 'exact_component_identity': None})
    receipt = require_result(Path(case['sections']).with_name('receipt.json'), case['surface_receipt_sha256'])
    source_to_seed = np.asarray(receipt['scans']['rotor']['transform']['transform_source_to_normalized'])
    source_to_rotor = np.asarray(params['candidate_axis']['transform_source_to_candidate_axis'])
    result = {'schema': '935-observed-hub-surfaces-v1', 'status': 'bounded_analytic_surface_candidates_not_complete_hub',
              'sections_sha256': case['sections_sha256'], 'observed_mesh_sha256': raw_hash,
              'source_sha256': params['source_sha256'], 'patches': patches,
              'transform_seed_to_rotor_candidate_frame': (source_to_rotor @ np.linalg.inv(source_to_seed)).tolist(),
              'test_partition': 'one_10_degree_sector_per_40_degrees_within_scan_not_independent_metrology',
              'source_units': None, 'scale_verified': False, 'complete_hub_reconstructed': False,
              'complete_system_reconstructed': False, 'manufacturing_authorized': False}
    if sha(raw_path) != raw_hash:
        raise ValueError('Observed mesh changed during hub reconstruction')
    save(output / 'hub-surfaces.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(patches), 2, figsize=(12, 5 * len(patches)), squeeze=False)
    for row, patch in enumerate(patches):
        points = mesh.triangles_center[patch['selected_face_indices']]
        preferred = patch['models'][patch['preferred_model']]
        for model in patch['models']:
            a = np.array(model['axis_in_seed_frame']); d = points - model['origin_in_seed_frame_source_units']; h = d @ a
            r = np.linalg.norm(d - np.outer(h, a), axis=1); order = np.argsort(h)
            if model is preferred:
                axes[row, 0].scatter(h, r, s=1, color='grey', label='acquired points in preferred frame')
                axes[row, 0].plot(h[order], model['radius_at_zero_source_units'] + model['radius_slope'] * h[order], label='preferred ' + model['type'])
            test = np.isin(patch['selected_face_indices'], model['test_face_indices'])
            axes[row, 1].scatter(h[test], (r[test] - model['radius_at_zero_source_units'] - model['radius_slope'] * h[test]) / np.sqrt(1 + model['radius_slope'] ** 2), s=2, label=model['type'] + ' held-out sectors')
        axes[row, 0].set_title(patch['id'] + ': bounded acquired patch')
        for ax in axes[row]: ax.legend(); ax.set_xlabel('fitted local axial coordinate, source units')
        axes[row, 0].set_ylabel('radius, source units'); axes[row, 1].set_ylabel('normal residual, source units')
    fig.suptitle('Bounded hub surface fits: within-scan comparison; no verified interface')
    fig.tight_layout(); fig.savefig(output / 'hub-model-comparison.png', dpi=150); plt.close(fig)
    return {'stage': 'hub', 'status': result['status'], 'hub_surfaces_sha256': sha(output / 'hub-surfaces.json'),
            'fitting_program_sha256': sha(__file__), 'observed_mesh_sha256': raw_hash,
            'complete_hub_reconstructed': False, 'scale_verified': False}
