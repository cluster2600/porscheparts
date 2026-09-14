#!/usr/bin/env python3
"""Audit private PicoGK voxel roundtrips against the unchanged triangulated master.

Surface distances and inward normal chords are area-weighted samples of the
meshes, not certified CAD distances, minimum wall thickness, or physical tests.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time

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


def surface_distances(source, target, count, seed, chunk_size=32):
    import numpy as np
    import trimesh
    points, _ = sample_surface(source, count, seed)
    distances = []
    validate_chunk_size(chunk_size)
    for start in range(0, len(points), chunk_size):
        _, chunk, _ = trimesh.proximity.closest_point(target, points[start:start + chunk_size])
        distances.extend(chunk)
    return {'sampling': 'area_weighted_random_triangle_points', 'seed': seed,
            'target_distance': 'nearest_point_on_target_triangles_not_nearest_vertex',
            'distance_scan_units': quantiles(np.array(distances)),
            'continuous_Hausdorff_bound': False}


def validate_chunk_size(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 512:
        raise ValueError('query_chunk_size_must_be_integer_1_to_512')


class BoundedRayIntersector:
    """Bound triangle broad-phase batches, retaining global ray identifiers.

    contains_points still sees all points together, including its original
    forward/backward parity logic; only its spatial queries split.
    This bounds query batches, not the in-memory mesh or spatial index itself.
    """
    def __init__(self, mesh, chunk_size):
        from trimesh.ray.ray_triangle import RayMeshIntersector
        validate_chunk_size(chunk_size)
        self.mesh, self.chunk_size = mesh, chunk_size
        self.tracer = RayMeshIntersector(mesh)

    def intersects_location(self, origins, directions, multiple_hits=True):
        import numpy as np
        locations, rays, faces = [], [], []
        for start in range(0, len(origins), self.chunk_size):
            point, ray, face = self.tracer.intersects_location(
                origins[start:start + self.chunk_size], directions[start:start + self.chunk_size],
                multiple_hits=multiple_hits)
            locations.append(point); rays.append(ray + start); faces.append(face)
        if not locations:
            return np.empty((0, 3)), np.empty(0, dtype=int), np.empty(0, dtype=int)
        return np.concatenate(locations), np.concatenate(rays), np.concatenate(faces)


def seeded_contains_points(tracer, points, seed):
    """Keep Trimesh's parity/free-space policy but seed its one fallback ray.

    Trimesh 5.1.0's contains_points draws an unseeded random direction when
    forward/backward parity disagrees and both rays hit. Explicit directions
    disable that internal retry. The recording adapter observes those same
    counts, then performs at most one locally seeded retry with the same API.
    No global RNG state, library code or acceptance threshold is modified.
    """
    import numpy as np
    from trimesh.bounds import contains as bounds_contains
    from trimesh.ray.ray_util import contains_points

    def classify(subset, direction):
        class RecordingIntersector:
            mesh = tracer.mesh
            hit_counts = None

            def intersects_location(self, origins, directions, multiple_hits=True):
                result = tracer.intersects_location(origins, directions, multiple_hits=multiple_hits)
                self.hit_counts = np.bincount(result[1], minlength=len(origins)).reshape(2, -1)
                return result

        recording = RecordingIntersector()
        inside = contains_points(recording, subset, check_direction=direction)
        unresolved = np.zeros(len(subset), dtype=bool)
        if recording.hit_counts is not None:
            hits = recording.hit_counts
            aabb = bounds_contains(tracer.mesh.bounds, subset)
            if hits.shape[1] != int(aabb.sum()):
                raise ValueError('trimesh_contains_bidirectional_query_contract_changed')
            unresolved[aabb] = ((hits[0] % 2 != hits[1] % 2) & (hits > 0).all(axis=0))
        return inside, unresolved

    inside, broken = classify(points, np.array([0.4395064455, 0.617598629942, 0.652231566745]))
    fallback_direction = None
    rejected = 0
    if broken.any():
        direction = np.random.default_rng(seed).random(3) - 0.5
        direction /= np.linalg.norm(direction)
        fallback_direction = direction.tolist()
        inside[broken], unresolved = classify(points[broken], direction)
        rejected = int(unresolved.sum())
    return inside, {
        'policy': 'trimesh_bidirectional_parity_single_locally_seeded_fallback',
        'fallback_seed': seed, 'fallback_rng': 'numpy_default_rng',
        'fallback_direction': fallback_direction, 'fallback_samples': int(broken.sum()),
        'samples_still_ambiguous_after_fallback_rejected': rejected,
    }


def normal_chord_screen(mesh, count, seed, threshold=1.5, chunk_size=32):
    import numpy as np
    validate_chunk_size(chunk_size)
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0):
        return {'status': 'not_run_invalid_oriented_closed_mesh', 'minimum_wall_thickness_proved': False}
    points, faces = sample_surface(mesh, count, seed)
    normals = mesh.face_normals[faces]
    # Stay beyond the ray library's near-surface rejection tolerance. This
    # offset remains recorded; unresolved sub-offset features are not accepted.
    epsilon = max(float(np.max(mesh.extents)) * 1e-7, 1e-5)
    origins, directions = points - epsilon * normals, -normals
    tracer = BoundedRayIntersector(mesh, chunk_size)
    inside, contains_evidence = seeded_contains_points(tracer, origins, seed)
    valid_rays = np.flatnonzero(inside)
    chords = np.full(count, np.nan)
    exit_faces = np.full(count, -1)
    # Bound the broad-phase memory cost on the many-finned surface.
    for start in range(0, len(valid_rays), chunk_size):
        selected = valid_rays[start:start + chunk_size]
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
        'inside_test': contains_evidence,
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
    # Finish topology temporaries before allocating a second welded mesh and
    # its ray/proximity caches. No two resolutions coexist in an audit worker.
    summary = mesh_summary(triangles)
    # Only merge identical coordinates; do not repair/reorient/decimate geometry.
    import numpy as np
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    mesh = trimesh.Trimesh(vertices=vertices, faces=inverse.reshape(-1, 3), process=False)
    return mesh, summary


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


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def atomic_private_json(path, value):
    """Publish a complete private checkpoint, never a partly written JSON."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def candidate_provenance(resolution, path, master_hash):
    path = Path(path)
    before = sha256(path)
    run_path = path.parent / 'run-report.json'
    run_hash = sha256(run_path)
    record = json.loads(run_path.read_text())
    if (record.get('input_sha256') != master_hash or record.get('input_unchanged') is not True
            or record.get('transform') != 'identity'
            or not math.isclose(float(record['voxel_mm']), resolution, rel_tol=1e-6, abs_tol=1e-8)
            or record['roundtrip']['sha256'] != before
            or record['roundtrip']['filename'] != path.name):
        raise ValueError('candidate_run_receipt_provenance_resolution_or_frame_mismatch')
    if sha256(run_path) != run_hash:
        raise ValueError('candidate_receipt_changed_during_read')
    return {'voxel_size_scan_units': resolution, 'candidate_sha256': before,
            'candidate_run_receipt_sha256': run_hash,
            'expected_triangles': record['roundtrip']['triangles']}


def make_context(args):
    export = json.loads(args.master_report.read_text())
    master_hash = sha256(args.master)
    if master_hash != export['mesh_sha256'] or not export['voxel_input_topology_gate_passed']:
        raise ValueError('master_export_provenance_or_topology_failed')
    resolutions = [float(value) for value, _ in args.candidate]
    if len(resolutions) != 3 or len(set(resolutions)) != 3 or any(not math.isfinite(r) or r <= 0 for r in resolutions):
        raise ValueError('exactly_three_distinct_positive_voxel_resolutions_required')
    if args.samples < 64 or args.chord_samples < 64:
        raise ValueError('at_least_64_samples_required')
    chunk = getattr(args, 'query_chunk_size', 32)
    validate_chunk_size(chunk)
    candidates = [candidate_provenance(float(resolution), filename, master_hash)
                  for resolution, filename in sorted(args.candidate, key=lambda pair: float(pair[0]), reverse=True)]
    return {
        'schema': 'm64-picogk-audit-checkpoint-context/v1',
        'audit_source_sha256': sha256(Path(__file__)),
        'export_source_sha256': sha256(Path(__file__).with_name('export_master.py')),
        'master_export_report_sha256': sha256(args.master_report), 'master_STL_sha256': master_hash,
        'master_STEP_sha256': export['source_STEP_sha256'], 'candidates': candidates,
        'settings': {'samples': args.samples, 'chord_samples': args.chord_samples,
                     'seed': args.seed, 'query_chunk_size': chunk, 'render': args.render},
        'runtime': {'python': platform.python_version(),
                    **{name: importlib.metadata.version(name) for name in ('numpy', 'trimesh', 'scipy', 'rtree')}},
    }


def write_checkpoint(path, context, key, result):
    atomic_private_json(path, {'schema': 'm64-picogk-private-audit-checkpoint/v1',
                               'context_sha256': json_hash(context), 'key': key,
                               'status': 'complete', 'result_sha256': json_hash(result), 'result': result})


def read_checkpoint(path, context, key):
    path = Path(path)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('private_regular_checkpoint_required')
    record = json.loads(path.read_text())
    if (record.get('schema') != 'm64-picogk-private-audit-checkpoint/v1'
            or record.get('context_sha256') != json_hash(context)
            or record.get('key') != key or record.get('status') != 'complete'
            or record.get('result_sha256') != json_hash(record.get('result'))):
        raise ValueError('checkpoint_binding_status_or_integrity_mismatch')
    return record['result']


def audit_worker(args, expected_context, index):
    """One resolution per spawn: native caches and mesh arrays die at exit."""
    import numpy as np
    started = time.monotonic()
    if make_context(args) != expected_context:
        raise ValueError('audit_inputs_or_code_changed_before_worker')
    context = expected_context
    chunk = context['settings']['query_chunk_size']
    master, master_summary = read_mesh(args.master)
    if index is None:
        result = {'master_mesh': master_summary,
                  'normal_chord_screen_master': normal_chord_screen(
                      master, args.chord_samples, args.seed, chunk_size=chunk)}
        key = 'master'
    else:
        expected = context['candidates'][index]
        resolution, filename = sorted(args.candidate, key=lambda pair: float(pair[0]), reverse=True)[index]
        path = Path(filename)
        candidate, summary = read_mesh(path)
        if expected['expected_triangles'] != summary['triangles']:
            raise ValueError('candidate_triangle_count_does_not_match_run_receipt')
        result = {'voxel_size_scan_units': float(resolution), 'candidate_sha256': expected['candidate_sha256'],
                  'candidate_run_receipt_sha256': expected['candidate_run_receipt_sha256'],
                  'run_input_frame_resolution_output_verified': True, 'mesh': summary,
                  'bbox_max_absolute_delta_scan_units': float(np.abs(candidate.bounds - master.bounds).max()),
                  'relative_signed_volume_error': float((candidate.volume - master.volume) / master.volume),
                  'relative_area_error': float((candidate.area - master.area) / master.area),
                  'master_to_candidate': surface_distances(master, candidate, args.samples, args.seed, chunk),
                  'candidate_to_master': surface_distances(candidate, master, args.samples, args.seed + 1, chunk),
                  'normal_chord_screen': normal_chord_screen(candidate, args.chord_samples, args.seed, chunk_size=chunk),
                  'same_euler_characteristic_as_master': summary['euler_characteristic'] == master_summary['euler_characteristic'],
                  'same_component_count_as_master': summary['connected_vertex_components'] == master_summary['connected_vertex_components']}
        if args.render and index == 2:
            image = args.output / 'master-vs-finest-and-section-private.png'
            render_comparison(master, candidate, image, float(resolution))
            result['private_image_sha256'] = sha256(image)
        key = f'candidate-{index}'
    if make_context(args) != context:
        raise ValueError('audit_inputs_or_code_changed_during_worker')
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result['worker_execution'] = {
        'process_id_private': os.getpid(), 'elapsed_seconds': time.monotonic() - started,
        'peak_resident_memory_bytes': int(peak_rss if sys.platform == 'darwin' else peak_rss * 1024),
        'query_batch_limit': chunk, 'mesh_and_spatial_index_memory_not_hard_capped': True,
    }
    write_checkpoint(args.output / f'{key}-checkpoint.json', context, key, result)


def launch_worker(args, context, index):
    process = multiprocessing.get_context('spawn').Process(target=audit_worker, args=(args, context, index))
    process.start()
    try:
        process.join()
    except BaseException:
        process.terminate(); process.join()
        raise
    if process.exitcode != 0:
        raise RuntimeError(f'audit_worker_failed_index_{index}_exit_{process.exitcode}')


def run(args):
    import fcntl
    context = make_context(args)
    if args.output.exists():
        if not getattr(args, 'resume', False):
            raise FileExistsError(args.output)
        if args.output.is_symlink() or args.output.stat().st_mode & 0o077:
            raise ValueError('private_output_directory_required')
        if json.loads((args.output / 'audit-context.json').read_text()) != context:
            raise ValueError('resume_context_mismatch_inputs_settings_runtime_or_code')
    else:
        args.output.mkdir(parents=True, mode=0o700)
        atomic_private_json(args.output / 'audit-context.json', context)
    descriptor = os.open(args.output / '.audit.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('audit_output_is_locked_by_a_live_process') from error
        return run_checkpoints(args, context)
    finally:
        os.close(descriptor)


def run_checkpoints(args, context):
    records = {}
    status = {'schema': 'm64-picogk-private-audit-status/v1', 'context_sha256': json_hash(context),
              'status': 'incomplete', 'completed_checkpoints': [], 'manufacturing_authorized': False}
    atomic_private_json(args.output / 'audit-status.json', status)
    try:
        for index in (None, 0, 1, 2):
            key = 'master' if index is None else f'candidate-{index}'
            checkpoint = args.output / f'{key}-checkpoint.json'
            reused = checkpoint.exists()
            if not reused:
                launch_worker(args, context, index)
            records[key] = read_checkpoint(checkpoint, context, key)
            status['completed_checkpoints'].append(key)
            atomic_private_json(args.output / 'audit-status.json', status)
            print(json.dumps({'checkpoint': key, 'reused': reused, 'status': 'complete'}), flush=True)
        if make_context(args) != context:
            raise ValueError('audit_inputs_or_code_changed_before_report')
    except BaseException:
        status['status'] = 'failed_or_interrupted'
        atomic_private_json(args.output / 'audit-status.json', status)
        raise
    report = {
        'schema': 'm64-picogk-private-roundtrip-audit/v2', 'audit_complete': True,
        'checkpoint_context_sha256': json_hash(context), 'audit_source_sha256': context['audit_source_sha256'],
        'master_export_report_sha256': context['master_export_report_sha256'],
        'master_STL_sha256': context['master_STL_sha256'], 'master_STEP_sha256': context['master_STEP_sha256'],
        'trimesh_version': context['runtime']['trimesh'], 'audit_settings': context['settings'],
        'length_unit': 'scan_unit', 'millimetres_per_scan_unit_working_hypothesis': 1.0,
        'absolute_scale_certified': False, **records['master'],
        'runs': [records[f'candidate-{index}'] for index in range(3)],
        'manufacturing_authorized': False, 'engine_operation_authorized': False,
        'no_global_smoothing_or_new_design_features_requested': True,
        'surface_distances_are_to_triangulated_master_not_exact_STEP': True,
    }
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
        if sha256(image) != report['runs'][-1]['private_image_sha256']:
            raise ValueError('private_render_hash_mismatch')
        report['private_image_sha256'] = sha256(image)
    report['master_unchanged_after_audit'] = True
    target = args.output / 'mesh-comparison-report.json'
    atomic_private_json(target, report)
    status['status'] = 'complete'; status['report_sha256'] = sha256(target)
    atomic_private_json(args.output / 'audit-status.json', status)
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
    parser.add_argument('--query-chunk-size', type=int, default=32,
                        help='Maximum ray/proximity query batch, 1–512; not a whole-process RAM limit')
    parser.add_argument('--resume', action='store_true',
                        help='Reuse complete checkpoints only when all inputs, code, runtime and settings match')
    parser.add_argument('--render', action='store_true')
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
