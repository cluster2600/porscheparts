#!/usr/bin/env python3
"""Audit private PicoGK voxel roundtrips against the unchanged triangulated master.

Surface distances and inward normal chords are area-weighted samples of the
meshes, not certified CAD distances, minimum wall thickness, or physical tests.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from export_master import load_binary_stl, mesh_summary, sha256


def sample_surface(mesh, count, seed):
    import numpy as np
    random = np.random.default_rng(seed)
    areas = mesh.area_faces
    if not np.isfinite(areas).all() or areas.sum() <= 0:
        raise ValueError('positive_finite_mesh_area_required')
    faces = random.choice(len(areas), count, p=areas / areas.sum())
    uv = random.random((count, 2))
    reflected = uv.sum(axis=1) > 1
    uv[reflected] = 1 - uv[reflected]
    triangles = mesh.triangles[faces]
    points = (triangles[:, 0] + uv[:, :1] * (triangles[:, 1] - triangles[:, 0])
              + uv[:, 1:] * (triangles[:, 2] - triangles[:, 0]))
    return points, faces


def quantiles(values):
    import numpy as np
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {'count': 0, 'minimum': None, 'p05': None, 'p50': None, 'p95': None, 'maximum': None}
    if not np.isfinite(values).all():
        raise ValueError('finite_samples_required')
    return {'count': len(values), 'minimum': float(values.min()),
            'p05': float(np.quantile(values, .05)), 'p50': float(np.quantile(values, .5)),
            'p95': float(np.quantile(values, .95)), 'maximum': float(values.max())}


def surface_distances(source, target, count, seed):
    import numpy as np
    import trimesh
    points, _ = sample_surface(source, count, seed)
    distances = []
    for start in range(0, len(points), 512):
        _, chunk, _ = trimesh.proximity.closest_point(target, points[start:start + 512])
        distances.extend(chunk)
    return {'sampling': 'area_weighted_random_triangle_points', 'seed': seed,
            'target_distance': 'nearest_point_on_target_triangles_not_nearest_vertex',
            'distance_scan_units': quantiles(np.array(distances)),
            'continuous_Hausdorff_bound': False}


def normal_chord_screen(mesh, count, seed, threshold=1.5):
    import numpy as np
    from trimesh.ray.ray_triangle import RayMeshIntersector
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0):
        return {'status': 'not_run_invalid_oriented_closed_mesh', 'minimum_wall_thickness_proved': False}
    points, faces = sample_surface(mesh, count, seed)
    normals = mesh.face_normals[faces]
    # Stay beyond the ray library's near-surface rejection tolerance. This
    # offset remains recorded; unresolved sub-offset features are not accepted.
    epsilon = max(float(np.max(mesh.extents)) * 1e-7, 1e-5)
    origins, directions = points - epsilon * normals, -normals
    tracer = RayMeshIntersector(mesh)
    inside = mesh.contains(origins)
    valid_rays = np.flatnonzero(inside)
    chords = np.full(count, np.nan)
    exit_faces = np.full(count, -1)
    # Bound the broad-phase memory cost on the many-finned surface.
    for start in range(0, len(valid_rays), 128):
        selected = valid_rays[start:start + 128]
        locations, ray_ids, triangle_ids = tracer.intersects_location(origins[selected], directions[selected],
                                                                     multiple_hits=True)
        for location, ray_id, triangle_id in zip(locations, ray_ids, triangle_ids):
            index = selected[ray_id]
            distance = float(np.dot(location - origins[index], directions[index]))
            if triangle_id == faces[index] or distance <= epsilon:
                continue
            # An exit must face along the travel direction. Reject same-surface,
            # grazing or inward-facing hits rather than call them wall thickness.
            if float(np.dot(mesh.face_normals[triangle_id], directions[index])) <= 1e-6:
                continue
            length = distance + epsilon
            if not np.isfinite(chords[index]) or length < chords[index]:
                chords[index], exit_faces[index] = length, triangle_id
    resolved = np.isfinite(chords)
    below = resolved & (chords < threshold)
    return {
        'status': 'sampled_mesh_normal_chords_only', 'seed': seed, 'sample_count': count,
        'sampling': 'area_weighted_random_triangle_points', 'ray_origin_offset_scan_units': epsilon,
        'origins_confirmed_inside': int(inside.sum()), 'resolved_exit_chords': int(resolved.sum()),
        'unresolved_or_rejected_samples': int((~resolved).sum()),
        'chord_scan_units': quantiles(chords[resolved]), 'screening_threshold_scan_units': threshold,
        'below_threshold_samples': int(below.sum()),
        'below_threshold_fraction_of_all_samples': float(below.sum() / count),
        'below_threshold_fraction_of_resolved_samples': float(below.sum() / resolved.sum()) if resolved.any() else None,
        'mesh_smoothness_and_ray_direction_can_bias_results': True,
        'adjacent_face_hits_not_classified_as_material_webs': True,
        'minimum_wall_thickness_proved': False, 'fraction_is_not_exact_CAD_area_fraction': True,
        'manufacturing_acceptance_criterion': False,
    }


def read_mesh(path):
    import trimesh
    triangles = load_binary_stl(path)
    # Only merge identical coordinates; do not repair/reorient/decimate geometry.
    import numpy as np
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    mesh = trimesh.Trimesh(vertices=vertices, faces=inverse.reshape(-1, 3), process=False)
    return mesh, mesh_summary(triangles)


def render_comparison(master, candidate, path, resolution):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(14, 10), facecolor='#f7f7f5')
    bounds = np.array([np.minimum(master.bounds[0], candidate.bounds[0]),
                       np.maximum(master.bounds[1], candidate.bounds[1])])
    spans = bounds[1] - bounds[0]
    colors = ('#668da2', '#ba7b41')
    for index, (mesh, title) in enumerate(((master, 'Maître STEP triangulé — inchangé'),
                                         (candidate, f'Aller-retour PicoGK — voxel {resolution:g} unité'))):
        ax = fig.add_subplot(2, 2, index + 1, projection='3d')
        # Display every triangle. No image synthesis or substitute head geometry.
        light = np.array([.3, -.4, .85]); light /= np.linalg.norm(light)
        brightness = .35 + .65 * np.clip(mesh.face_normals @ light, 0, 1)
        from matplotlib.colors import to_rgb
        facecolors = brightness[:, None] * np.array(to_rgb(colors[index]))
        ax.add_collection3d(Poly3DCollection(mesh.triangles, facecolors=facecolors, edgecolors='none', rasterized=True))
        ax.set_xlim(*bounds[:, 0]); ax.set_ylim(*bounds[:, 1]); ax.set_zlim(*bounds[:, 2])
        ax.set_box_aspect(spans); ax.set_proj_type('ortho'); ax.view_init(28, -57)
        ax.set_axis_off(); ax.set_title(title)
    section_ax = fig.add_subplot(2, 1, 2)
    origin = bounds.mean(axis=0)
    for mesh, color, label, style in ((master, colors[0], 'Maître', '-'),
                                      (candidate, colors[1], 'PicoGK', '--')):
        section = mesh.section(plane_origin=origin, plane_normal=[1, 0, 0])
        if section is None:
            raise ValueError('empty_actual_mesh_section')
        for index, line in enumerate(section.discrete):
            section_ax.plot(line[:, 1], line[:, 2], color=color, ls=style, lw=1,
                            label=label if index == 0 else None)
    section_ax.set_aspect('equal'); section_ax.grid(alpha=.2); section_ax.legend()
    section_ax.set_xlabel('Y — unité du scan'); section_ax.set_ylabel('Z — unité du scan')
    section_ax.set_title('Coupe centrale réelle X constant — contours superposés')
    fig.suptitle('Culasse 4V issue du scan 935 — audit géométrique PicoGK', fontsize=16)
    fig.text(.5, .015, 'Échelle 1 unité/mm hypothétique. Aucun lissage ni nouveau conduit.\n'
             'Couleurs de repérage ; pas de champ physique ni autorisation de fabrication.', ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .065, 1, .96]); fig.savefig(path, dpi=130); plt.close(fig)
    Path(path).chmod(0o600)


def run(args):
    import numpy as np
    import trimesh
    export = json.loads(args.master_report.read_text())
    master_hash = sha256(args.master)
    if master_hash != export['mesh_sha256'] or not export['voxel_input_topology_gate_passed']:
        raise ValueError('master_export_provenance_or_topology_failed')
    resolutions = [float(value) for value, _ in args.candidate]
    if len(resolutions) != 3 or len(set(resolutions)) != 3 or any(not math.isfinite(r) or r <= 0 for r in resolutions):
        raise ValueError('exactly_three_distinct_positive_voxel_resolutions_required')
    if args.samples < 64 or args.chord_samples < 64:
        raise ValueError('at_least_64_samples_required')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    master, master_summary = read_mesh(args.master)
    report = {
        'schema': 'm64-picogk-private-roundtrip-audit/v1', 'audit_source_sha256': sha256(Path(__file__)),
        'master_export_report_sha256': sha256(args.master_report), 'master_STL_sha256': master_hash,
        'master_STEP_sha256': export['source_STEP_sha256'], 'trimesh_version': trimesh.__version__,
        'length_unit': 'scan_unit', 'millimetres_per_scan_unit_working_hypothesis': 1.0,
        'absolute_scale_certified': False, 'master_mesh': master_summary,
        'normal_chord_screen_master': normal_chord_screen(master, args.chord_samples, args.seed),
        'runs': [], 'manufacturing_authorized': False, 'engine_operation_authorized': False,
        'no_global_smoothing_or_new_design_features_requested': True,
        'surface_distances_are_to_triangulated_master_not_exact_STEP': True,
    }
    finest = None
    for resolution, filename in sorted(args.candidate, key=lambda pair: float(pair[0]), reverse=True):
        resolution = float(resolution); path = Path(filename); before = sha256(path)
        run_path = path.parent / 'run-report.json'
        run_record = json.loads(run_path.read_text())
        if (run_record.get('input_sha256') != master_hash or run_record.get('input_unchanged') is not True
                or run_record.get('transform') != 'identity'
                or not math.isclose(float(run_record['voxel_mm']), resolution, rel_tol=1e-6, abs_tol=1e-8)
                or run_record['roundtrip']['sha256'] != before
                or run_record['roundtrip']['filename'] != path.name):
            raise ValueError('candidate_run_receipt_provenance_resolution_or_frame_mismatch')
        candidate, summary = read_mesh(path)
        if run_record['roundtrip']['triangles'] != summary['triangles']:
            raise ValueError('candidate_triangle_count_does_not_match_run_receipt')
        record = {'voxel_size_scan_units': resolution, 'candidate_sha256': before,
                  'candidate_run_receipt_sha256': sha256(run_path),
                  'run_input_frame_resolution_output_verified': True, 'mesh': summary,
                  'bbox_max_absolute_delta_scan_units': float(np.abs(candidate.bounds - master.bounds).max()),
                  'relative_signed_volume_error': float((candidate.volume - master.volume) / master.volume),
                  'relative_area_error': float((candidate.area - master.area) / master.area),
                  'master_to_candidate': surface_distances(master, candidate, args.samples, args.seed),
                  'candidate_to_master': surface_distances(candidate, master, args.samples, args.seed + 1),
                  'normal_chord_screen': normal_chord_screen(candidate, args.chord_samples, args.seed),
                  'same_euler_characteristic_as_master': summary['euler_characteristic'] == master_summary['euler_characteristic'],
                  'same_component_count_as_master': summary['connected_vertex_components'] == master_summary['connected_vertex_components']}
        if sha256(path) != before:
            raise ValueError('candidate_changed_during_audit')
        report['runs'].append(record); finest = (candidate, resolution)
        print(json.dumps({'voxel_size': resolution, 'volume_relative_error': record['relative_signed_volume_error'],
                          'boundary_edges': summary['boundary_edges']}), flush=True)
    maxima = [max(row['master_to_candidate']['distance_scan_units']['maximum'],
                  row['candidate_to_master']['distance_scan_units']['maximum']) for row in report['runs']]
    volumes = [abs(row['relative_signed_volume_error']) for row in report['runs']]
    report['convergence_screen'] = {
        'resolution_order': 'coarse_to_fine', 'sampled_bidirectional_maximum_distances': maxima,
        'absolute_relative_volume_errors': volumes,
        'sampled_maximum_distance_monotone_nonincreasing': all(b <= a for a, b in zip(maxima, maxima[1:])),
        'volume_error_monotone_nonincreasing': all(b <= a for a, b in zip(volumes, volumes[1:])),
        'numerical_order_or_grid_independence_established': False,
        'functional_interface_preservation_certified': False,
    }
    if args.render:
        image = args.output / 'master-vs-finest-and-section-private.png'
        render_comparison(master, finest[0], image, finest[1])
        report['private_image_sha256'] = sha256(image)
    if sha256(args.master) != master_hash:
        raise ValueError('master_changed_during_audit')
    report['master_unchanged_after_audit'] = True
    target = args.output / 'mesh-comparison-report.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n'); target.chmod(0o600)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, required=True)
    parser.add_argument('--master-report', type=Path, required=True)
    parser.add_argument('--candidate', nargs=2, action='append', required=True, metavar=('VOXEL_SIZE', 'STL'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=4096)
    parser.add_argument('--chord-samples', type=int, default=512)
    parser.add_argument('--seed', type=int, default=917)
    parser.add_argument('--render', action='store_true')
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
