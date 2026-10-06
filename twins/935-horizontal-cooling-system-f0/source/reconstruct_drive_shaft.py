#!/usr/bin/env python3
"""Reconstruct an acquired periodic shaft patch; no standard tooth definition."""
from pathlib import Path
import numpy as np
from run_reconstruction import require_result, save, sha
from reconstruct_hub_surfaces import fit_surface


def periodic_profiles(points, bands, candidates, harmonics=3, samples=528):
    p = np.asarray(points, float)
    if (p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all()
            or len(bands) < 3 or not np.isfinite(bands).all()
            or any(not lo < hi for lo, hi in bands) or any(b[0] < a[1] for a, b in zip(bands, bands[1:]))
            or not candidates or any(type(k) is not int or not 2 <= k <= 100 for k in candidates)
            or type(harmonics) is not int or not 1 <= harmonics <= 4
            or type(samples) is not int or samples < 4 * harmonics * max(candidates)):
        raise ValueError('Finite acquired points, ordered bands and resolved angular sampling required')
    theta = np.mod(np.arctan2(p[:, 1], p[:, 0]), 2 * np.pi)
    radius = np.linalg.norm(p[:, :2], axis=1)
    records = []
    for lo, hi in bands:
        ids = np.flatnonzero((p[:, 2] > lo) & (p[:, 2] < hi))
        if len(ids) < 100:
            raise ValueError('At least 100 acquired samples per independent axial band required')
        t, r = theta[ids], radius[ids]; scores = []
        for count in candidates:
            matrix = np.column_stack([np.ones(len(t)), np.cos(t), np.sin(t), np.cos(2*t), np.sin(2*t),
                                      np.cos(count*t), np.sin(count*t)])
            coef = np.linalg.lstsq(matrix, r, rcond=None)[0]
            scores.append({'count': count, 'rms_source_units': float(np.sqrt(np.mean((matrix @ coef-r)**2)))})
        scores.sort(key=lambda row: row['rms_source_units'])
        records.append({'axial_band_source_units': [lo, hi], 'sample_indices': ids.tolist(), 'candidate_scores': scores})
    count = records[0]['candidate_scores'][0]['count']
    if any(row['candidate_scores'][0]['count'] != count for row in records):
        raise ValueError('Periodicity disagrees across acquired axial bands; no tooth count imposed')
    frequencies = [1, 2] + [count * i for i in range(1, harmonics+1)]
    def design(t):
        return np.column_stack([np.ones(len(t))] + [f(k*t) for k in frequencies for f in (np.cos, np.sin)])
    profiles = []
    for record in records:
        ids = np.array(record['sample_indices']); t, r = theta[ids], radius[ids]
        test = (np.floor(t / (2*np.pi/count)).astype(int) % 4) == 0
        if min(test.sum(), (~test).sum()) < 50:
            raise ValueError('Insufficient whole-lobe sectors for within-scan holdout')
        matrix = design(t[~test]); coef, _, rank, _ = np.linalg.lstsq(matrix, r[~test], rcond=None)
        if rank != matrix.shape[1]:
            raise ValueError('Unresolved periodic profile coefficients')
        error = design(t[test]) @ coef - r[test]
        angles = np.linspace(0, 2*np.pi, samples, endpoint=False); fitted = design(angles) @ coef
        if fitted.min() <= 0:
            raise ValueError('Periodic radius became nonpositive')
        height = float(np.median(p[ids, 2]))
        profiles.append(np.column_stack([fitted*np.cos(angles), fitted*np.sin(angles), np.full(samples, height)]).tolist())
        angular = np.sort(t)
        gaps = np.diff(np.r_[angular, angular[0]+2*np.pi])
        record.update({'height_source_units': height, 'coefficients_source_units': coef.tolist(),
                       'frequencies': frequencies, 'train_sample_indices': ids[~test].tolist(), 'test_sample_indices': ids[test].tolist(),
                       'heldout_rms_source_units': float(np.sqrt(np.mean(error**2))),
                       'heldout_absolute_quantiles_source_units': np.quantile(np.abs(error), [.5,.95,.99,1]).tolist(),
                       'maximum_unsampled_angular_gap_deg': float(np.rad2deg(gaps.max())),
                       'acquired_sample_gap_intervals_above_3_deg':
                       [{'start_deg':float(np.rad2deg(angular[i])), 'end_deg_unwrapped':float(np.rad2deg(angular[i]+gap))}
                        for i, gap in enumerate(gaps) if gap > np.deg2rad(3)]})
    return {'observed_periodicity': count, 'bands': records, 'profiles': profiles,
            'profile_label': 'acquired_band_fit_with_periodic_interpolation_not_standard_spline',
            'test_partition': 'whole_lobes_one_in_four_within_scan_not_independent_metrology',
            'distance_definition': 'radial_to_band_model_not_bidirectional_surface_deviation',
            'axis_or_tooth_standard_verified': False}


def reconstruct(case, output):
    import trimesh
    spec = case['drive_shaft']; path = Path(spec['prepared_scan'])
    if sha(path) != spec['prepared_scan_sha256']:
        raise ValueError('Prepared drive scan hash mismatch')
    receipt = require_result(spec['surface_receipt'], spec['surface_receipt_sha256'])
    basis, origin = np.asarray(spec['seed_basis'], float), np.asarray(spec['seed_origin'], float)
    if (basis.shape != (3,3) or origin.shape != (3,) or not np.isfinite(basis).all() or not np.isfinite(origin).all()
            or not np.allclose(basis.T @ basis, np.eye(3), rtol=0, atol=1e-9)
            or not np.isclose(np.linalg.det(basis), 1, rtol=0, atol=1e-9)):
        raise ValueError('Rigid right-handed inspected seed frame required')
    raw = np.load(path); mesh = trimesh.Trimesh(raw['vertices'], raw['faces'], process=False)
    amount = spec['sample_faces']; lo, hi = spec['axial_interval_source_units']; rlo, rhi = spec['radius_window_source_units']
    limit = spec['maximum_normal_axis_abs']
    if (type(amount) is not int or not 100 <= amount <= len(mesh.faces) or not np.isfinite([lo,hi,rlo,rhi,limit]).all()
            or not lo < hi or not 0 < rlo < rhi or not 0 < limit <= 1):
        raise ValueError('Inspected finite patch bounds and face sample count required')
    ids = np.random.default_rng(spec['random_seed']).choice(len(mesh.faces), amount, replace=False)
    p, n = (mesh.triangles_center[ids]-origin) @ basis, mesh.face_normals[ids] @ basis
    radial = np.linalg.norm(p[:,:2], axis=1)
    selected = (p[:,2]>lo)&(p[:,2]<hi)&(radial>rlo)&(radial<rhi)&(np.abs(n[:,2])<limit)
    model = fit_surface(p[selected], n[selected], [0,0,0,0,spec['initial_radius_source_units']], [rlo,rhi], 'cylinder')
    axis = np.asarray(model['axis_in_seed_frame']); x = np.cross([0,1,0],axis); x /= np.linalg.norm(x)
    fitted_basis = np.column_stack([x,np.cross(axis,x),axis]); fitted_origin = np.asarray(model['origin_in_seed_frame_source_units'])
    q = (p[selected]-fitted_origin) @ fitted_basis
    result = periodic_profiles(q, spec['axial_bands_source_units'], spec['periodicity_candidates'], spec['profile_harmonics'], spec['profile_samples'])
    source_to_inspection = np.asarray(receipt['scans']['drive']['transform']['transform_source_to_normalized'])
    inspection_to_seed = np.eye(4); inspection_to_seed[:3,:3] = basis.T; inspection_to_seed[:3,3] = -basis.T @ origin
    seed_to_fitted = np.eye(4); seed_to_fitted[:3,:3] = fitted_basis.T; seed_to_fitted[:3,3] = -fitted_basis.T @ fitted_origin
    transform = seed_to_fitted @ inspection_to_seed @ source_to_inspection
    for row in result['bands']:
        for field in ('sample_indices','train_sample_indices','test_sample_indices'):
            row[field.replace('sample','face')] = ids[selected][row.pop(field)].tolist()
    for field in ('train_sample_indices','test_sample_indices'):
        model[field.replace('sample','face')] = ids[selected][model.pop(field)].tolist()
    result.update({'schema':'935-observed-drive-shaft-v1', 'status':'partial_acquired_periodic_shaft_surface_candidate',
                   'prepared_scan_sha256': spec['prepared_scan_sha256'], 'source_sha256': receipt['scans']['drive']['input_sha256'],
                   'envelope_axis_candidate':model, 'selected_face_indices':ids[selected].tolist(),
                   'transform_source_to_candidate_shaft':transform.tolist(), 'transform_candidate_shaft_to_source':np.linalg.inv(transform).tolist(),
                   'source_units':None, 'scale_verified':False, 'crop_caps_added':False,
                   'complete_shaft_reconstructed':False, 'functional_interface_verified':False, 'manufacturing_authorized':False})
    if sha(path) != spec['prepared_scan_sha256']:
        raise ValueError('Prepared drive changed during reconstruction')
    save(output/'drive-shaft-profile.json',result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,2,figsize=(12,5))
    angle = np.arctan2(q[:,1],q[:,0]); radius = np.linalg.norm(q[:,:2],axis=1)
    axes[0].scatter(q[:,0],q[:,1],s=1,c=q[:,2]);axes[0].set_aspect('equal')
    axes[1].scatter(np.rad2deg(angle),radius,s=1,c=q[:,2])
    for profile in result['profiles']:
        row=np.asarray(profile);t=np.arctan2(row[:,1],row[:,0]);order=np.argsort(t)
        axes[1].plot(np.rad2deg(t[order]),np.linalg.norm(row[order,:2],axis=1),linewidth=.8)
    axes[1].set_xlabel('candidate azimuth degrees');axes[1].set_ylabel('radius, uncalibrated source units')
    fig.suptitle('Acquired periodic shaft patch: interpolated gaps; no standard or manufacturing release')
    fig.tight_layout();fig.savefig(output/'drive-shaft-profile.png',dpi=150);plt.close(fig)
    return {'stage':'drive','status':result['status'],'profile_sha256':sha(output/'drive-shaft-profile.json'),
            'fitting_program_sha256':sha(__file__),'observed_periodicity':result['observed_periodicity'],
            'scale_verified':False,'complete_shaft_reconstructed':False}
