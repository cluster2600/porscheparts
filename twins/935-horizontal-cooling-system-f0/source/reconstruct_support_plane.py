#!/usr/bin/env python3
"""Fit a support inspection plane and an optional bounded acquired bore arc."""
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from run_reconstruction import require_result, save, sha


def fit_plane(points, initial, tile_width, robust_scale):
    p, seed = np.asarray(points, float), np.asarray(initial, float)
    if (p.ndim != 2 or p.shape[1] != 3 or len(p) < 200 or seed.shape != (3,)
            or not np.isfinite(p).all() or not np.isfinite(seed).all()
            or not np.isfinite([tile_width, robust_scale]).all() or min(tile_width, robust_scale) <= 0):
        raise ValueError('Finite local plane samples, seed and positive fitting scales required')
    tiles = np.floor(p[:, [0, 2]] / tile_width).astype(np.int64)
    test = (tiles[:, 0] + 2 * tiles[:, 1]) % 4 == 0
    if min(test.sum(), (~test).sum()) < 50:
        raise ValueError('Insufficient spatial tiles for within-scan holdout')
    center = p[~test].mean(axis=0); q = p - center
    design = np.column_stack((q[~test, 0], q[~test, 2], np.ones((~test).sum())))
    if np.linalg.matrix_rank(design) != 3:
        raise ValueError('Plane samples are collinear')
    def residual(x, pts):
        return (pts[:, 1] - x[0]*pts[:, 0] - x[1]*pts[:, 2] - x[2]) / np.sqrt(1 + x[0]**2 + x[1]**2)
    fit = least_squares(lambda x: residual(x, q[~test]),
        [seed[0], seed[1], seed[0]*center[0] + seed[1]*center[2] + seed[2] - center[1]],
        loss='soft_l1', f_scale=robust_scale, max_nfev=1000)
    if not fit.success:
        raise ValueError('Local plane fit did not converge')
    normal = np.array([-fit.x[0], 1., -fit.x[1]]); normal /= np.linalg.norm(normal)
    origin = center + normal * fit.x[2] / np.sqrt(1 + fit.x[0]**2 + fit.x[1]**2)
    u = np.array([1., 0., 0.]) - normal[0]*normal; u /= np.linalg.norm(u)
    basis = np.column_stack((u, np.cross(normal, u), normal))
    coordinates = (p - origin) @ basis; lo, hi = coordinates[:, :2].min(axis=0), coordinates[:, :2].max(axis=0)
    corners = np.array([[lo[0],lo[1],0],[hi[0],lo[1],0],[hi[0],hi[1],0],[lo[0],hi[1],0]]) @ basis.T + origin
    errors = residual(fit.x, q[test])
    return {'type': 'plane', 'origin_source_units': origin.tolist(), 'normal': normal.tolist(),
            'basis': basis.tolist(), 'inspection_crop_corners_source_units': corners.tolist(),
            'crop_is_part_boundary': False, 'functional_datum_verified': False,
            'heldout_rms_source_units': float(np.sqrt(np.mean(errors**2))),
            'heldout_absolute_quantiles_source_units': np.quantile(np.abs(errors), [.5,.95,.99,1]).tolist(),
            'test_sample_indices': np.flatnonzero(test).tolist(), 'train_sample_indices': np.flatnonzero(~test).tolist()}


def reconstruct(case, output):
    import trimesh
    settings = case['support_plane']; source = Path(settings['prepared_scan'])
    if sha(source) != settings['prepared_scan_sha256']:
        raise ValueError('Prepared support scan hash mismatch')
    receipt = require_result(settings['surface_receipt'], settings['surface_receipt_sha256'])
    raw = np.load(source); mesh = trimesh.Trimesh(raw['vertices'], raw['faces'], process=False)
    if (len(mesh.vertices) != receipt['scans']['drive']['vertices']
            or len(mesh.faces) != receipt['scans']['drive']['faces'] or not np.isfinite(mesh.vertices).all()):
        raise ValueError('Prepared scan disagrees with the upstream receipt')
    p = mesh.triangles_center; box = np.asarray(settings['bounding_box_source_units'], float)
    seed = np.asarray(settings['seed_plane_y_from_x_z'], float); band = settings['maximum_seed_distance_source_units']
    if (box.shape != (2,3) or seed.shape != (3,) or not np.isfinite(box).all()
            or not np.isfinite(seed).all() or np.any(box[0] >= box[1]) or not np.isfinite(band) or band <= 0):
        raise ValueError('Valid inspected bounding box, plane seed and positive selection band required')
    candidates = np.flatnonzero(np.all((p > box[0]) & (p < box[1]), axis=1))
    distance = (p[candidates,1] - seed[0]*p[candidates,0] - seed[1]*p[candidates,2] - seed[2]) / np.sqrt(1 + seed[0]**2 + seed[1]**2)
    ids = candidates[np.abs(distance) < band]
    model = fit_plane(p[ids], seed, settings['holdout_tile_width_source_units'], settings['robust_scale_source_units'])
    for role in ('test', 'train'):
        model[role + '_face_indices'] = ids[model.pop(role + '_sample_indices')].tolist()
    patches = [{'id': 'support-plane-00', 'preferred_model': 0, 'models': [model],
                'surface_label': 'inspection_reference_plane_with_artificial_crop_not_material_surface'}]
    bore = settings.get('bore_patch')
    if bore:
        from reconstruct_hub_surfaces import fit_surface
        origin, basis = np.asarray(bore['seed_origin'], float), np.asarray(bore['seed_basis'], float)
        span, window = np.asarray(bore['axial_interval_source_units'], float), np.asarray(bore['radius_window_source_units'], float)
        limit = bore['maximum_normal_axis_abs']
        if (origin.shape != (3,) or basis.shape != (3,3) or not np.isfinite(origin).all()
                or not np.isfinite(basis).all() or not np.allclose(basis.T @ basis, np.eye(3), atol=1e-8, rtol=0)
                or np.linalg.det(basis) < .999999 or span.shape != (2,) or not np.isfinite(span).all() or span[0] >= span[1]
                or window.shape != (2,) or not np.isfinite(window).all() or not 0 < window[0] < window[1]
                or not np.isfinite(limit) or not 0 < limit <= 1):
            raise ValueError('Valid inspected rigid bore frame and patch limits required')
        local = (p-origin) @ basis; normals = mesh.face_normals @ basis; radius = np.linalg.norm(local[:,:2],axis=1)
        bore_ids = np.flatnonzero((local[:,2]>span[0]) & (local[:,2]<span[1]) & (radius>window[0])
                                 & (radius<window[1]) & (np.abs(normals[:,2])<limit))
        models = []
        for kind in ('cylinder','cone'):
            fitted = fit_surface(local[bore_ids], normals[bore_ids], [0,0,0,0,bore['initial_radius_source_units']],
                                 window, kind, bore['normal_weight'], bore['robust_scale_source_units'])
            a = np.array(fitted['axis_in_seed_frame']); u = np.cross([0,1,0],a); u /= np.linalg.norm(u); v = np.cross(a,u)
            q = local[bore_ids] - fitted['origin_in_seed_frame_source_units']
            angle = np.sort(np.mod(np.arctan2(q@v,q@u),2*np.pi)); gaps = np.diff(np.r_[angle,angle[0]+2*np.pi])
            largest = int(np.argmax(gaps)); start = angle[(largest+1)%len(angle)]
            fitted['angular_extent_deg'] = float(np.rad2deg(2*np.pi-gaps[largest]))
            fitted['maximum_unsampled_fitted_angular_gap_deg'] = float(np.rad2deg(gaps[largest]))
            fitted['radial_start_direction'] = (basis @ (u*np.cos(start)+v*np.sin(start))).tolist()
            fitted['fitting_frame_origin'] = origin.tolist(); fitted['fitting_frame_basis'] = basis.tolist()
            fitted['axis_in_seed_frame'] = (basis @ a).tolist()
            fitted['origin_in_seed_frame_source_units'] = (origin + basis @ np.asarray(fitted['origin_in_seed_frame_source_units'])).tolist()
            for role in ('test','train'):
                fitted[role+'_face_indices'] = bore_ids[fitted.pop(role+'_sample_indices')].tolist()
            models.append(fitted)
        preferred = int(models[1]['heldout_rms_source_units'] < models[0]['heldout_rms_source_units'] and
                        models[1]['heldout_absolute_quantiles_source_units'][1] < models[0]['heldout_absolute_quantiles_source_units'][1])
        patches.append({'id': 'support-bore-arc-00', 'preferred_model': preferred, 'models': models,
                        'selected_face_indices': bore_ids.tolist(), 'selection': bore,
                        'surface_label': 'analytic_fit_of_acquired_bore_wall_arc_crop_edges_not_measured_part_boundaries'})
        np.savez_compressed(output/'bore-wall.npz', points=p[bore_ids], face_indices=bore_ids)
    result = {'schema': '935-observed-support-surfaces-v1', 'status': 'local_support_candidates_not_complete_support',
              'source_sha256': receipt['scans']['drive']['input_sha256'],
              'prepared_scan_sha256': settings['prepared_scan_sha256'], 'surface_receipt_sha256': settings['surface_receipt_sha256'],
              'source_pose_transform': receipt['scans']['drive']['transform'],
              'selection': settings, 'selected_face_indices': ids.tolist(),
              'excluded_candidate_face_indices': candidates[np.abs(distance) >= band].tolist(),
              'transform_patch_to_candidate_frame': np.eye(4).tolist(),
              'patches': patches,
              'test_partition': 'plane_spatial_tiles_and_bore_angular_sectors_within_same_scan_not_independent_metrology',
              'source_units': None, 'scale_verified': False, 'complete_holes_reconstructed': False,
              'complete_system_reconstructed': False, 'manufacturing_authorized': False}
    if sha(source) != settings['prepared_scan_sha256']:
        raise ValueError('Prepared scan changed during plane fitting')
    save(output/'support-surfaces.json', result)
    np.savez_compressed(output/'selected.npz', points=p[ids], face_indices=ids,
                        signed_plane_residuals=(p[ids]-model['origin_source_units']) @ model['normal'])
    return {'stage': 'support', 'status': result['status'], 'support_surfaces_sha256': sha(output/'support-surfaces.json'),
            'fitting_program_sha256': sha(__file__), 'selected_faces': len(ids), 'functional_datum_verified': False}
