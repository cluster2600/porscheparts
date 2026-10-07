#!/usr/bin/env python3
"""Private, restartable scan reconstruction. Usage: case.json stage NEW_OUTPUT."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'twins/993-engine-cooling-fan-system-f0/source'))
from audit_private_scan import read_obj
from prepare_private_scan import normalize
from inspect_private_interfaces import boundary_loops


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fresh(path):
    path = Path(path).resolve()
    if path.exists():
        raise ValueError('Use a new private output directory')
    for parent in path.parents:
        if (parent / '.git').exists() and path.relative_to(parent).parts[0] != 'work':
            raise ValueError('Scan derivatives must stay in ignored work/')
    path.mkdir(parents=True, mode=0o700)
    return path


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def cylinder(points, normals, window, normal_weight, trim_distance):
    """Robust geometric cylinder fit in a user-inspected seed frame, not a PCA datum."""
    import numpy as np
    from scipy.optimize import least_squares
    lo, hi = window
    radius = np.linalg.norm(points[:, :2], axis=1)
    radial_normal = np.sum(normals[:, :2] * points[:, :2], axis=1) / np.maximum(radius, 1e-30)
    selected = (radius > lo) & (radius < hi) & (np.abs(radial_normal) > .85)
    ids = np.flatnonzero(selected)
    if len(ids) < 100:
        raise ValueError('Insufficient observed cylindrical surface')
    ids = ids[np.linspace(0, len(ids) - 1, min(6000, len(ids)), dtype=int)]
    p, n = points[ids], normals[ids]

    def residual(x, p, n):
        axis = np.array([x[2], x[3], 1.]); axis /= np.linalg.norm(axis)
        d = p - [x[0], x[1], 0]
        return np.r_[np.linalg.norm(d - np.outer(d @ axis, axis), axis=1) - x[4],
                     normal_weight * (n @ axis)]

    bounds = ([-hi, -hi, -1, -1, lo * .7], [hi, hi, 1, 1, hi * 1.3])
    fit = least_squares(residual, [0, 0, 0, 0, (lo + hi) / 2], args=(p, n),
                        bounds=bounds, loss='soft_l1', f_scale=trim_distance / 2)
    inlier = np.abs(residual(fit.x, p, n)[:len(p)]) < trim_distance
    if inlier.sum() < 100 or not fit.success:
        raise ValueError('Cylinder did not converge or has insufficient inliers')
    fit = least_squares(residual, fit.x, args=(p[inlier], n[inlier]), bounds=bounds,
                        loss='soft_l1', f_scale=trim_distance / 2)
    if not fit.success:
        raise ValueError('Trimmed cylinder fit did not converge')
    axis = np.r_[fit.x[2:4], 1]; axis /= np.linalg.norm(axis)
    origin = np.r_[fit.x[:2], 0]
    x = np.cross([0, 1, 0], axis); x /= np.linalg.norm(x)
    basis = np.column_stack((x, np.cross(axis, x), axis))
    q = (p[inlier] - origin) @ basis
    angles = np.sort(np.mod(np.arctan2(q[:, 1], q[:, 0]), 2 * np.pi))
    coverage = np.rad2deg(2 * np.pi - np.max(np.diff(np.r_[angles, angles[0] + 2 * np.pi])))
    if coverage < 330:
        raise ValueError('Cylinder is a partial arc, not an axis candidate')
    radial = residual(fit.x, p[inlier], n[inlier])[:inlier.sum()]
    return origin, basis, {
        'radius_source_units': float(fit.x[4]), 'radial_rms_source_units': float(np.sqrt(np.mean(radial ** 2))),
        'angular_coverage_deg': float(coverage), 'axial_span_source_units': float(np.ptp(q[:, 2])),
        'inlier_faces': ids[inlier].tolist(), 'sampled_faces': ids.tolist(),
        'seed_window_source_units': window, 'trim_distance_source_units': trim_distance,
        'axis_in_seed_frame': axis.tolist(), 'origin_in_seed_frame': origin.tolist(),
        'status': 'observed_surface_axis_candidate_not_independently_measured_datum'}


def ordered_contours(segments, maximum_gap):
    """Keep closed sections; join only short missing links and record every link."""
    import numpy as np
    if len(segments) == 0:
        return []
    # ponytail: six decimals join coincident cut endpoints; unsuitable for micron-scale input.
    points, inv = np.unique(np.round(segments.reshape(-1, 3), 6), axis=0, return_inverse=True)
    edges = inv.reshape(-1, 2)
    adjacency = {i: [] for i in np.unique(edges)}
    for a, b in edges:
        if a == b:
            continue
        adjacency[a].append(b); adjacency[b].append(a)
    if any(len(v) > 2 for v in adjacency.values()):
        return []
    repairs = []
    endpoints = [i for i in adjacency if len(adjacency[i]) == 1]
    while len(endpoints) > 1:
        pairs = [(float(np.linalg.norm(points[a] - points[b])), a, b)
                 for j, a in enumerate(endpoints) for b in endpoints[j + 1:]]
        distance, a, b = min(pairs)
        if distance > maximum_gap:
            break
        adjacency[a].append(b); adjacency[b].append(a)
        repairs.append({'a': points[a].tolist(), 'b': points[b].tolist(), 'length_source_units': distance})
        endpoints.remove(a); endpoints.remove(b)
    remaining, contours = set(adjacency), []
    while remaining:
        start = min(remaining); pending = [start]; members = set()
        while pending:
            i = pending.pop()
            if i in members:
                continue
            members.add(i); pending.extend(adjacency[i])
        remaining -= members
        if len(members) < 20 or any(len(adjacency[i]) != 2 for i in members):
            continue
        order, prev, current = [start], start, adjacency[start][0]
        while current != start and current not in order:
            order.append(current)
            prev, current = current, next(i for i in adjacency[current] if i != prev)
        if current != start or len(order) != len(members):
            continue
        contours.append((points[order], [r for r in repairs if any(np.all(points[i] == r['a']) for i in members)]))
    return contours


def fitted_profile(points, direction, samples, smoothing):
    import numpy as np
    from scipy.interpolate import splprep, splev
    tangent = np.cross([0, 0, 1], direction)
    xy = np.column_stack((points @ tangent, points[:, 2]))
    if np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1)) < 0:
        points = points[::-1]
    points = np.roll(points, -int(np.argmin(points[:, 2])), axis=0)
    xy = np.column_stack((points @ tangent, points[:, 2]))
    xy = np.vstack((xy, xy[0]))
    spline, _ = splprep(xy.T, s=len(xy) * smoothing ** 2, per=True, k=3)
    fitted = np.array(splev(np.linspace(0, 1, samples, endpoint=False), spline)).T
    return (direction * float(np.mean(points @ direction)) +
            np.outer(fitted[:, 0], tangent) + np.outer(fitted[:, 1], [0, 0, 1]))


def contiguous_regions(blade, requested_stations):
    """Never loft across a rejected scan section; retain isolated contours separately."""
    accepted = [s for s in blade['sections'] if s['accepted']]
    spacing = min(b - a for a, b in zip(requested_stations, requested_stations[1:]))
    groups = [[]]
    for profile, section in zip(blade['profiles'], accepted):
        if groups[-1] and section['station'] - groups[-1][-1][1] > spacing * 1.01:
            groups.append([])
        groups[-1].append((profile, section['station']))
    return [{'id': f'{blade["id"]}-patch-{i:02d}', 'blade_id': blade['id'], 'phase_radians': blade['phase_radians'],
             'profiles': [row[0] for row in group], 'stations_source_units': [row[1] for row in group],
             'end_caps': 'artificial_section_crop_not_measured_surface'}
            for i, group in enumerate(groups) if len(group) >= 3]


def preflight(output):
    versions = {}
    for name in ('numpy', 'scipy', 'trimesh', 'pymeshlab', 'gmsh', 'openmdao', 'physicsnemo', 'usd-core'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    commands = {}
    for name in ('dotnet', 'ccx', 'gmsh', 'simpleFoam', 'foamRun', 'FreeCADCmd', 'docker'):
        commands[name] = shutil.which(name)
    for name in ('numpy', 'scipy', 'trimesh', 'pymeshlab', 'gmsh'):
        module = 'scipy.optimize, scipy.sparse.linalg' if name == 'scipy' else name
        check = subprocess.run([sys.executable, '-c', f'import {module}'], capture_output=True, text=True)
        versions[name + '_import_ok'] = check.returncode == 0
    return {'platform': platform.platform(), 'python': sys.version, 'logical_cpus': os.cpu_count(),
            'versions': versions, 'commands': commands, 'working_directory': str(output),
            'native_linux': platform.system() == 'Linux', 'paid_compute_started': False}


def surfaces(case, output):
    import numpy as np
    import trimesh
    from scipy.sparse import csr_array
    from scipy.sparse.csgraph import connected_components
    stations = case['rotor']['section_stations_source_units']
    if (len(stations) < 3 or stations != sorted(set(stations)) or not np.isfinite(stations).all()
            or case['rotor']['profile_samples'] < 16 or case['rotor']['maximum_section_gap_source_units'] < 0):
        raise ValueError('Finite increasing section stations and valid sampling limits required')
    if {s['id'] for s in case['scans']} != {'rotor', 'drive'} or len(case['scans']) != 2:
        raise ValueError('Exactly the original rotor and drive scans are required')
    parameters = {'schema': '935-observed-section-loft-v1', 'length_unit': 'unknown_source_unit', 'blades': [], 'regions': []}
    scans = {}
    for spec in case['scans']:
        path = Path(spec['path'])
        if sha(path) != spec['sha256']:
            raise ValueError('Original scan hash mismatch')
        v, f, ignored = read_obj(path)
        if ignored:
            raise ValueError('Position/triangle-only OBJ required')
        v, f, pose = normalize(v, f)
        mesh = trimesh.Trimesh(v, f, process=False)
        scan_out = output / spec['id']; scan_out.mkdir(mode=0o700)
        np.savez_compressed(scan_out / 'observed.npz', vertices=v, faces=f)
        edges = np.sort(mesh.edges, axis=1); unique, counts = np.unique(edges, axis=0, return_counts=True)
        loops = boundary_loops(unique[counts == 1])
        save(scan_out / 'boundaries.json', {'classification': 'unresolved_no_hole_filled', 'loops': loops})
        scans[spec['id']] = {'input_sha256': spec['sha256'], 'transform': pose,
                            'vertices': len(v), 'faces': len(f), 'boundary_edges': int((counts == 1).sum()),
                            'boundary_contours': len(loops), 'boundary_geometry': str(scan_out / 'boundaries.json')}
        if spec['id'] != 'rotor':
            continue
        origins, bases, fits = [], [], []
        for window in case['rotor']['cylinder_windows_source_units']:
            origin, basis, fit = cylinder(mesh.triangles_center, mesh.face_normals, window,
                                          case['rotor']['normal_weight'], case['rotor']['axis_trim_source_units'])
            origins.append(origin); bases.append(basis); fits.append(fit)
        origin, basis = origins[0], bases[0]
        frame = np.eye(4); frame[:3, :3] = basis.T; frame[:3, 3] = -basis.T @ origin
        source_frame = frame @ np.asarray(pose['transform_source_to_normalized'])
        v = (v - origin) @ basis
        np.savez_compressed(scan_out / 'axis-aligned.npz', vertices=v, faces=f)
        report = {'fits': fits, 'transform_source_to_candidate_axis': source_frame.tolist(),
                  'transform_candidate_axis_to_source': np.linalg.inv(source_frame).tolist(),
                  'axis_disagreement_deg': float(np.rad2deg(np.arccos(np.clip(bases[0][:, 2] @ bases[-1][:, 2], -1, 1)))),
                  'functional_datum_verified': False}
        save(scan_out / 'axis.json', report)
        radius = np.linalg.norm(v[:, :2], axis=1)
        cut = f[np.all(radius[f] > case['rotor']['segmentation_radius_source_units'], axis=1)]
        e = np.concatenate((cut[:, [0, 1]], cut[:, [1, 2]], cut[:, [2, 0]]))
        _, labels = connected_components(csr_array((np.ones(len(e)), (e[:, 0], e[:, 1])),
                                        shape=(len(v), len(v))), directed=False)
        ids, sizes = np.unique(labels[np.unique(cut)], return_counts=True)
        significant = ids[sizes >= case['rotor']['minimum_blade_vertices']]
        if not 2 <= len(significant) <= 64:
            raise ValueError('Blade regions unresolved; no count is imposed')
        phases = sorted(float(np.angle(np.mean(np.exp(1j * np.arctan2(v[labels == label, 1], v[labels == label, 0])))))
                        for label in significant)
        centre = v[f].mean(1); radial = np.linalg.norm(centre[:, :2], axis=1)
        angles = np.arctan2(centre[:, 1], centre[:, 0])
        for i, phase in enumerate(phases):
            direction = np.array([np.cos(phase), np.sin(phase), 0])
            sector = np.abs(np.angle(np.exp(1j * (angles - phase)))) < np.pi / len(phases)
            strip = trimesh.Trimesh(v, f[sector & (radial > case['rotor']['section_sector_min_radius_source_units'])], process=False)
            profiles, diagnostics = [], []
            for station in case['rotor']['section_stations_source_units']:
                segments = trimesh.intersections.mesh_plane(strip, direction, direction * station)
                contours = ordered_contours(segments, case['rotor']['maximum_section_gap_source_units'])
                if not contours:
                    diagnostics.append({'station': station, 'accepted': False, 'reason': 'open_or_branched_observed_section'})
                    continue
                contour, repairs = max(contours, key=lambda row: len(row[0]))
                fitted = fitted_profile(contour, direction, case['rotor']['profile_samples'], case['rotor']['profile_smoothing_source_units'])
                profiles.append(fitted.tolist())
                diagnostics.append({'station': station, 'accepted': True, 'acquired_cut_points': len(contour),
                                    'short_gap_interpolations': repairs, 'other_contours_not_used': len(contours) - 1})
            if len(profiles) < 3:
                raise ValueError('Insufficient observed closed blade sections; previous outputs retained')
            blade = {'id': f'blade-{i:02d}', 'phase_radians': phase, 'profiles': profiles,
                     'sections': diagnostics, 'root_and_tip_recovered': False,
                     'end_caps': 'artificial_section_crop_not_measured_surface'}
            parameters['blades'].append(blade)
            parameters['regions'].extend(contiguous_regions(blade, case['rotor']['section_stations_source_units']))
        parameters.update({'source_sha256': spec['sha256'], 'candidate_axis': report,
                           'segmentation': {'significant_regions': len(phases), 'component_sizes': sorted(sizes.tolist(), reverse=True),
                                            'discarded_fragments_preserved_in_observed_mesh': True},
                           'hub_and_back': 'observed_only_no_alignment_or_solid_reconstruction',
                           'observed_mesh': str(scan_out / 'axis-aligned.npz')})
        if sha(path) != spec['sha256']:
            raise ValueError('Original scan changed during reconstruction')
    for spec in case['scans']:
        if sha(spec['path']) != spec['sha256']:
            raise ValueError('Original scan changed during reconstruction')
    save(output / 'sections.json', parameters)
    return {'stage': 'surfaces', 'status': 'partial_observed_blade_section_reconstruction', 'scans': scans,
            'sections_sha256': sha(output / 'sections.json'), 'source_units': None,
            'scale_verified': False, 'complete_rotor_reconstructed': False, 'complete_mechanism_reconstructed': False,
            'solver_ready': False, 'physically_validated': False}


def require_result(path, expected_sha):
    path = Path(path)
    if sha(path) != expected_sha:
        raise ValueError('Upstream artifact hash mismatch')
    return json.loads(path.read_text())


def native(case, stage, output):
    """Call the qualified existing image directly; never install or rent compute."""
    settings = case['native']; image = settings['image_id']; mount = Path(settings['root']).resolve()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('An immutable local image ID is required')
    sections = Path(case['sections']).resolve()
    require_result(sections, case['sections_sha256'])

    def mapped(path):
        return '/data/' + str(Path(path).resolve().relative_to(mount))

    command = ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
               '-v', f'{mount}:/data', '-e', 'QT_QPA_PLATFORM=offscreen']
    arguments = [mapped(sections), case['sections_sha256'], str(case['assumed_mm_per_source_unit'])]
    if stage == 'picogk':
        dll = Path(settings['section_loft_dll'])
        if sha(dll) != settings['section_loft_dll_sha256']:
            raise ValueError('Qualified section loft executable hash mismatch')
        command += ['-e', 'LD_LIBRARY_PATH=/opt/picogk-native/lib:/app', '--entrypoint', '/usr/share/dotnet/dotnet', image, mapped(dll)]
        arguments.append(str(case['voxel_mm_conditional']))
    else:
        command += ['-e', 'LD_LIBRARY_PATH=/opt/freecad/usr/lib', '--entrypoint', '/opt/freecad/usr/bin/python', image,
                    mapped(Path(__file__).with_name({'cad-hub': 'build_hub_cad.py', 'cad-support': 'build_hub_cad.py', 'cad-drive': 'build_drive_cad.py'}.get(stage, 'build_section_cad.py')))]
    with (output / 'native.log').open('x') as log:
        subprocess.run(command + arguments + [mapped(output / 'artifacts')], stdout=log, stderr=subprocess.STDOUT, check=True)
    result = json.loads((output / 'artifacts/receipt.json').read_text())
    return {'stage': stage, 'image_id': image, 'native_receipt_sha256': sha(output / 'artifacts/receipt.json'),
            'sections_sha256': case['sections_sha256'], 'result': result}


def run(case_path, stage, output):
    case = json.loads(Path(case_path).read_text())
    if stage not in ('preflight', 'surfaces', 'picogk', 'cad', 'review', 'hub', 'cad-hub', 'drive', 'cad-drive', 'support', 'cad-support'):
        raise ValueError('Implemented stages: preflight, surfaces, picogk, cad, review, hub, cad-hub, drive, cad-drive, support, cad-support. Complete-reference solver inputs remain unresolved.')
    output = fresh(output)
    os.umask(0o077)
    try:
        if stage == 'preflight':
            receipt = preflight(output)
        elif stage == 'surfaces':
            receipt = surfaces(case, output)
        elif stage == 'hub':
            from reconstruct_hub_surfaces import reconstruct
            receipt = reconstruct(case, output)
        elif stage == 'drive':
            from reconstruct_drive_shaft import reconstruct
            receipt = reconstruct(case, output)
        elif stage == 'support':
            from reconstruct_support_plane import reconstruct
            receipt = reconstruct(case, output)
        elif stage in ('picogk', 'cad', 'cad-hub', 'cad-drive', 'cad-support'):
            receipt = native(case, stage, output)
        else:
            from review_reconstruction import review
            receipt = review(case_path, output / 'artifacts')
        receipt.update({'case_sha256': sha(case_path), 'program_sha256': sha(__file__), 'stage': stage,
                        'derived_geometry_private': True, 'manufacturing_authorized': False})
        save(output / 'receipt.json', receipt)
        return receipt
    except Exception as error:
        save(output / 'failure.json', {'stage': stage, 'error': type(error).__name__, 'message': str(error),
                                     'partial_outputs_retained': True})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('stage'); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    receipt = run(args.case, args.stage, args.output)
    print(f"{receipt['stage']}: private artifacts saved; functional validation remains open")
