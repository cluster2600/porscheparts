#!/usr/bin/env python3
"""Independent private checks of scan/loft deviation and PicoGK convergence."""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from run_reconstruction import fresh, require_result, save, sha
from photo_guided_surface_repair import pymeshlab_topology_audit


def sample(mesh, count, seed):
    rng = np.random.default_rng(seed)
    ids = rng.choice(len(mesh.faces), count, p=mesh.area_faces / mesh.area)
    uv = rng.random((count, 2)); flip = uv.sum(1) > 1; uv[flip] = 1 - uv[flip]
    t = mesh.triangles[ids]
    return t[:, 0] + uv[:, :1] * (t[:, 1] - t[:, 0]) + uv[:, 1:] * (t[:, 2] - t[:, 0])


def distances(source, target, count, seed, output=None):
    points = sample(source, count, seed)
    closest, distance, faces = trimesh.proximity.closest_point(target, points)
    if output is not None:
        np.savez_compressed(output, points=points, closest=closest, distance=distance, target_face_indices=faces)
    return {'samples': count, 'seed': seed, 'rms_source_units': float(np.sqrt(np.mean(distance ** 2))),
            'percentiles_source_units': np.quantile(distance, [.5, .95, .99, 1]).tolist(),
            'method': 'area_uniform_independent_points_to_triangles_not_nearest_vertices'}


def properties(mesh):
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError('Closed positive consistently oriented mesh required for volume/inertia')
    p = mesh.mass_properties; c, volume = p['center_mass'], float(p['volume'])
    inertia = p['inertia'] + volume * (np.dot(c, c) * np.eye(3) - np.outer(c, c))
    return {'conditional_volume_mm3': volume, 'conditional_volume_inertia_about_axis_origin_mm5': inertia.tolist(),
            'principal_volume_inertias_mm5': np.linalg.eigvalsh(inertia).tolist(),
            'conditional_centroid_mm': c.tolist(), 'triangles': len(mesh.faces)}


def render(observed, parameters, loft, report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import pymeshlab
    previews = pymeshlab.MeshSet(); previews.add_mesh(pymeshlab.Mesh(observed.vertices, observed.faces))
    previews.apply_filter('meshing_decimation_quadric_edge_collapse', targetfacenum=50000, preservenormal=True, preserveboundary=True)
    preview = previews.current_mesh(); triangles = preview.vertex_matrix()[preview.face_matrix()]
    fitted = loft.triangles
    fig = plt.figure(figsize=(15, 8))
    for i, (el, az) in enumerate(((65, 15), (5, 15), (-65, 15), (5, 105))):
        ax = fig.add_subplot(2, 2, i + 1, projection='3d')
        ax.add_collection3d(Poly3DCollection(triangles, facecolor=(.47, .57, .63, .27), linewidths=0))
        ax.add_collection3d(Poly3DCollection(fitted, facecolor=(.94, .42, .10, 1), linewidths=0))
        ax.set_xlim(-150, 150); ax.set_ylim(-150, 150); ax.set_zlim(-55, 65)
        ax.set_box_aspect([300, 300, 120]); ax.view_init(el, az); ax.set_axis_off()
    fig.suptitle('935: measured scan in grey; fitted blade regions in orange\nRoots, tips, hub and misregistered back remain unreconstructed; units uncalibrated')
    fig.tight_layout(); fig.savefig(output / 'scan-loft-overlay.png', dpi=150); plt.close(fig)
    fig, axs = plt.subplots(3, 3, figsize=(15, 12))
    for ax, blade in zip(axs.flat, parameters['blades']):
        phase = blade['phase_radians']; tangent = np.array([-np.sin(phase), np.cos(phase), 0])
        for j, row in enumerate(blade['profiles']):
            if j % 3 == 0:
                row = np.array(row); ax.plot(row @ tangent, row[:, 2], linewidth=.7)
        ax.set_title(blade['id'] + ': cropped fitted sections'); ax.set_aspect('equal'); ax.grid(alpha=.2)
        ax.set_xlabel('tangential source coordinate'); ax.set_ylabel('axial source coordinate')
    fig.tight_layout(); fig.savefig(output / 'blade-sections.png', dpi=140); plt.close(fig)
    from matplotlib.colors import LogNorm
    samples = [np.load(p) for p in output.glob('*-scan-to-loft.npz')]
    points = np.concatenate([s['points'] for s in samples]); error = np.concatenate([s['distance'] for s in samples])
    fig, axs = plt.subplots(1, 3, figsize=(16, 6))
    for ax, (a, b) in zip(axs, ((0, 1), (0, 2), (1, 2))):
        ax.scatter(observed.vertices[::30, a], observed.vertices[::30, b], s=.1, color='#bfc8cd', alpha=.4)
        colored = ax.scatter(points[:, a], points[:, b], c=np.maximum(error, 1e-6), s=2,
                             cmap='turbo', norm=LogNorm(vmin=.001, vmax=max(1., float(error.max()))))
        ax.set_aspect('equal'); ax.set_xlabel(f'candidate axis coordinate {a}'); ax.set_ylabel(f'coordinate {b}')
    fig.colorbar(colored, ax=axs.tolist(), label='point-to-triangle distance, uncalibrated source units')
    fig.suptitle('Acquired zones: independent scan-to-loft distance samples; crop caps excluded')
    fig.savefig(output / 'deviation-map.png', dpi=150); plt.close(fig)
    boundaries = json.loads((Path(parameters['observed_mesh']).parent / 'boundaries.json').read_text())['loops']
    fig, axs = plt.subplots(1, 3, figsize=(16, 6))
    for ax, (a, b) in zip(axs, ((0, 1), (0, 2), (1, 2))):
        ax.scatter(observed.vertices[::30, a], observed.vertices[::30, b], s=.1, color='#bfc8cd')
        for loop in boundaries:
            p = observed.vertices[loop['original_vertex_indices']]
            ax.plot(p[:, a], p[:, b], color='#ce3434', linewidth=.6)
        ax.set_aspect('equal')
    fig.suptitle('All raw scan boundaries: unresolved coverage/functional classification; no hole filled')
    fig.tight_layout(); fig.savefig(output / 'unresolved-boundaries.png', dpi=150); plt.close(fig)
    raw = np.load(Path(parameters['observed_mesh']).with_name('observed.npz'))
    centres = raw['vertices'][raw['faces']].mean(1)
    fig, axs = plt.subplots(2, 2, figsize=(12, 9))
    for row, fit in enumerate(parameters['candidate_axis']['fits']):
        axis = np.array(fit['axis_in_seed_frame']); x = np.cross([0, 1, 0], axis); x /= np.linalg.norm(x)
        basis = np.column_stack((x, np.cross(axis, x), axis))
        p = (centres[fit['inlier_faces']] - fit['origin_in_seed_frame']) @ basis
        radius = fit['radius_source_units']; angle = np.linspace(0, 2 * np.pi, 361)
        axs[row, 0].scatter(p[:, 0], p[:, 1], s=1, label='observed cylinder candidates')
        axs[row, 0].plot(radius * np.cos(angle), radius * np.sin(angle), color='#e76f00', label='robust fit')
        axs[row, 0].set_aspect('equal'); axs[row, 0].legend(); axs[row, 0].set_xlabel('local x, source units')
        axs[row, 0].set_ylabel('local y, source units')
        axs[row, 1].scatter(p[:, 2], np.linalg.norm(p[:, :2], axis=1) - radius, s=1)
        axs[row, 1].axhline(0, color='#e76f00'); axs[row, 1].set_xlabel('axial position, source units')
        axs[row, 1].set_ylabel('radial residual, source units')
    fig.suptitle('Hub: acquired cylindrical patches and residuals\nIndependent candidate axes; no functional datum or back alignment accepted')
    fig.tight_layout(); fig.savefig(output / 'hub-sections.png', dpi=150); plt.close(fig)
    raw = np.load(Path(parameters['observed_mesh']).parents[1] / 'drive/observed.npz')
    previews = pymeshlab.MeshSet(); previews.add_mesh(pymeshlab.Mesh(raw['vertices'], raw['faces']))
    previews.apply_filter('meshing_decimation_quadric_edge_collapse', targetfacenum=50000, preservenormal=True, preserveboundary=True)
    m = previews.current_mesh(); triangles = m.vertex_matrix()[m.face_matrix()]
    limits = np.column_stack((raw['vertices'].min(0), raw['vertices'].max(0)))
    fig = plt.figure(figsize=(15, 5))
    for i, (el, az) in enumerate(((30, 30), (30, 120), (-30, 30))):
        ax = fig.add_subplot(1, 3, i + 1, projection='3d')
        ax.add_collection3d(Poly3DCollection(triangles, facecolor=(.47, .57, .63, 1), linewidths=0))
        ax.set_xlim(*limits[0]); ax.set_ylim(*limits[1]); ax.set_zlim(*limits[2])
        ax.set_box_aspect(np.diff(limits).ravel()); ax.view_init(el, az); ax.set_axis_off()
    fig.suptitle('935 drive: acquired exterior in inspection pose\nMechanical components, hidden internals and assembly datums unresolved')
    fig.tight_layout(); fig.savefig(output / 'drive-coverage.png', dpi=150); plt.close(fig)


def review(case_path, output):
    case = json.loads(Path(case_path).read_text()); output = fresh(output)
    parameters = require_result(case['sections'], case['sections_sha256'])
    raw = np.load(parameters['observed_mesh']); observed = trimesh.Trimesh(raw['vertices'], raw['faces'], process=False)
    runs = [require_result(Path(p) / 'receipt.json', expected) for p, expected in case['picogk_runs']]
    if len(runs) != 3 or any(r['sections_sha256'] != case['sections_sha256'] for r in runs):
        raise ValueError('Three runs must reference exactly the same fitted sections')
    scales = [r['assumed_mm_per_source_unit'] for r in runs]; steps = [r['voxel_size_mm_conditional'] for r in runs]
    if len(set(scales)) != 1 or not np.allclose(np.array(steps[:-1]) / steps[1:], 2):
        raise ValueError('Common conditional scale and three halved resolutions required')
    base_path = Path(case['picogk_runs'][0][0]) / 'section-lofts.stl'
    if sha(base_path) != runs[0]['section_lofts_sha256']:
        raise ValueError('Section loft mesh differs from runtime receipt')
    base = trimesh.load(base_path, force='mesh', process=True)
    loft = trimesh.Trimesh(base.vertices / scales[0], base.faces, process=False)
    deviations = []
    for i, blade in enumerate(parameters['regions']):
        phase = blade['phase_radians']; normal = np.array([np.cos(phase), np.sin(phase), 0])
        profiles = np.array(blade['profiles']); lo = np.mean(profiles[0] @ normal) + 1; hi = np.mean(profiles[-1] @ normal) - 1
        meshes = []
        for m in (observed, loft):
            p = m.triangles_center; angle = np.arctan2(p[:, 1], p[:, 0])
            selected = ((p @ normal > lo) & (p @ normal < hi) &
                        (np.abs(np.angle(np.exp(1j * (angle - phase)))) < np.pi / len(parameters['blades'])))
            meshes.append(trimesh.Trimesh(m.vertices, m.faces[selected], process=False))
        deviations.append({'id': blade['id'], 'crop_caps_excluded_margin_source_units': 1,
                           'scan_to_loft': distances(meshes[0], meshes[1], 1000, 42 + i, output / f'{blade["id"]}-scan-to-loft.npz'),
                           'loft_to_scan': distances(meshes[1], meshes[0], 1000, 142 + i, output / f'{blade["id"]}-loft-to-scan.npz')})
    levels = []
    for (folder, _), run in zip(case['picogk_runs'], runs):
        path = Path(folder) / 'voxel-blade-regions.stl'
        if sha(path) != run['output_sha256']:
            raise ValueError('PicoGK mesh differs from runtime receipt')
        mesh = trimesh.load(path, force='mesh', process=True)
        levels.append({'voxel_mm_conditional': run['voxel_size_mm_conditional'], **properties(mesh)})
    volume_delta = abs(levels[-1]['conditional_volume_mm3'] / levels[-2]['conditional_volume_mm3'] - 1)
    inertia_delta = float(np.max(np.abs(np.array(levels[-1]['principal_volume_inertias_mm5']) /
                                                 levels[-2]['principal_volume_inertias_mm5'] - 1)))
    report = {'status': 'partial_blade_region_review_not_complete_reference', 'sections_sha256': case['sections_sha256'],
              'base_loft_topology': pymeshlab_topology_audit(base_path), 'levels': levels, 'deviations': deviations,
              'last_two_volume_relative_change': volume_delta, 'last_two_inertia_relative_change': inertia_delta,
              'partial_region_discretization_under_one_percent': bool(max(volume_delta, inertia_delta) < .01),
              'source_unit': None, 'scale_verified': False, 'whole_rotor_mass_available': False,
              'whole_rotor_geometry_gate_passed': False, 'assembly_validated': False,
              'CFD_run': False, 'mechanical_solve_run': False, 'surrogate_training_run': False,
              'physically_validated': False, 'manufacturing_authorized': False}
    save(output / 'review.json', report)
    render(observed, parameters, loft, report, output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); review(args.case, args.output)
    print('Private bidirectional deviation and convergence review saved; complete rotor validation remains open')
