#!/usr/bin/env python3
"""Recover one 935 tip from closed scan cuts; preserve the existing reference."""
import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

from complete_candidate_rotor import local_profile, world_profile
from run_reconstruction import fitted_profile, fresh, ordered_contours, save, sha


def correct(reference, blade_id, acquired, repaired=None):
    result = copy.deepcopy(reference)
    blades = result['blades']
    if len(blades) != 9 or len({b['id'] for b in blades}) != 9:
        raise ValueError('Nine distinct reference blades required')
    blade = next(b for b in blades if b['id'] == blade_id)
    phase = blade['phase_radians']
    if len(blade['profiles']) != len(blade['provenance']) or len(blade['profiles']) != len(blade['stations_source_units']):
        raise ValueError('Reference section lengths differ')
    anchors = {float(s): np.asarray(p) for s, p, label in zip(blade['stations_source_units'], blade['profiles'], blade['provenance'])
               if label['classification'] == 'registered_acquired_reference_section'}
    boundary = max(anchors)
    if len(acquired) < 3 or min(acquired) <= boundary:
        raise ValueError('Three new acquired tip sections beyond the existing interval required')
    repaired = repaired or {}
    if set(acquired) & set(repaired) or any(s <= boundary or s >= max(acquired) for s in repaired):
        raise ValueError('Repaired sections must lie between old and new acquired anchors')
    profiles_by_station = {**acquired, **{s: row['profile'] for s, row in repaired.items()}}
    previous = local_profile(anchors[boundary], phase)
    for station, profile in sorted(profiles_by_station.items()):
        points = local_profile(profile, phase)
        if points.shape != (128, 3) or not np.isfinite(points).all() or not np.allclose(points[:, 0], station, rtol=0, atol=1e-6):
            raise ValueError('Finite 128-point section in its declared plane required')
        points[:, 0] = station
        points = min((np.roll(points, i, axis=0) for i in range(128)),
                     key=lambda p: float(np.sum((p[:, 1:] - previous[:, 1:])**2)))
        anchors[station] = world_profile(points, phase)
        previous = points
    terminal = max(acquired)
    stations = sorted({s for s in blade['stations_source_units'] if s <= terminal} | set(profiles_by_station))
    old = {s: (p, label) for s, p, label in zip(blade['stations_source_units'], blade['profiles'], blade['provenance'])}
    profiles, provenance = [], []
    for station in stations:
        if station <= boundary:
            profile, label = old[station]
        elif station in acquired:
            profile = anchors[station].tolist()
            label = {'station_source_units': station, 'classification': 'registered_acquired_reference_section',
                     'recovery': 'own_connected_blade_closed_cut_no_gap_bridge'}
        elif station in repaired:
            profile = anchors[station].tolist()
            label = {'station_source_units': station, 'classification': 'own_observed_arcs_with_local_gap_chords',
                     'repairs': repaired[station]['links'], 'gap_surfaces_are_measured': False}
        else:
            a = max(s for s in anchors if s < station); b = min(s for s in anchors if s > station)
            p = local_profile(anchors[a], phase) + (local_profile(anchors[b], phase) - local_profile(anchors[a], phase)) * ((station-a)/(b-a))
            p[:, 0] = station; profile = world_profile(p, phase).tolist()
            label = {'station_source_units': station, 'classification': 'own_acquired_anchor_interpolation_tip_repair',
                     'anchor_stations_source_units': [a, b], 'observed_open_arcs_not_promoted_to_closed_sections': True}
        profiles.append(profile); provenance.append(label)
    blade.update(stations_source_units=stations, profiles=profiles, provenance=provenance)
    result['regions'] = copy.deepcopy(blades)
    for old_blade, new_blade in zip(reference['blades'], blades):
        if old_blade['id'] != blade_id and old_blade != new_blade:
            raise ValueError('Untargeted blade changed')
    for station, points in anchors.items():
        if station <= boundary and not np.array_equal(points, np.asarray(blade['profiles'][stations.index(station)])):
            raise ValueError('An existing acquired profile changed')
    return result


def prepare(case_path, output):
    import trimesh
    from scipy.sparse import csr_array
    from scipy.sparse.csgraph import connected_components
    case = json.loads(Path(case_path).read_text())
    if case['purpose'] != 'hypothesis_screen' or case['scale_verified'] is not False:
        raise ValueError('Uncalibrated hypothesis required')
    source, observed = Path(case['reference_sections_path']), Path(case['observed_mesh_path'])
    if sha(source) != case['reference_sections_sha256'] or sha(observed) != case['observed_mesh_sha256']:
        raise ValueError('Private input hash mismatch')
    reference = json.loads(source.read_text())
    data = np.load(observed); vertices, faces = data['vertices'], data['faces']
    radius, minimum, margin = (case[k] for k in ('segmentation_radius_source_units', 'minimum_blade_vertices', 'terminal_margin_source_units'))
    if any(isinstance(x, bool) or not math.isfinite(x) or x <= 0 for x in (radius, minimum, margin)):
        raise ValueError('Positive finite segmentation and terminal bounds required')
    cut = faces[np.all(np.linalg.norm(vertices[faces][..., :2], axis=2) > radius, axis=1)]
    edges = np.concatenate([cut[:, [0,1]], cut[:, [1,2]], cut[:, [2,0]]])
    _, labels = connected_components(csr_array((np.ones(len(edges)), (edges[:,0], edges[:,1])), shape=(len(vertices), len(vertices))), directed=False)
    ids, sizes = np.unique(labels[np.unique(cut)], return_counts=True)
    regions = sorted((float(np.angle(np.mean(np.exp(1j*np.arctan2(vertices[labels == label,1], vertices[labels == label,0]))))), int(label))
                     for label in ids[sizes >= minimum])
    if len(regions) != 9:
        raise ValueError('Nine observed connected blade regions required')
    blade = next(b for b in reference['blades'] if b['id'] == case['blade_id'])
    phase = blade['phase_radians']
    matches = [label for angle, label in regions if abs(angle-phase) < 1e-10]
    if len(matches) != 1:
        raise ValueError('Reference blade must match one independently segmented scan region')
    selection = np.all(labels[faces] == matches[0], axis=1)
    direction = np.array([np.cos(phase), np.sin(phase), 0])
    maximum = float((vertices[np.unique(faces[selection])] @ direction).max())
    terminal = maximum - margin
    requested = sorted(set(case['new_acquired_stations_source_units'] + [terminal]))
    if len(requested) != 3 or requested[-2] >= terminal:
        raise ValueError('Two acquired stations and a bounded terminal cut required')
    mesh = trimesh.Trimesh(vertices, faces[selection], process=False)
    repaired_stations = case['repair_stations_source_units']
    gap_bound = case['maximum_repair_gap_source_units']
    if repaired_stations != sorted(set(repaired_stations)) or not math.isfinite(gap_bound) or gap_bound <= 0:
        raise ValueError('Distinct repaired stations and a positive gap bound required')
    acquired, repaired, cuts = {}, {}, {}
    for station in sorted(requested + repaired_stations):
        segments = trimesh.intersections.mesh_plane(mesh, direction, direction*station)
        contours = ordered_contours(segments, gap_bound if station in repaired_stations else 0)
        if len(contours) != 1 or (contours[0][1] and station not in repaired_stations):
            raise ValueError('Exactly one contour with explicitly authorized local repairs required')
        points, links = contours[0]
        if station in repaired_stations:
            observed_points = set(map(tuple, np.unique(np.round(segments.reshape(-1,3),6), axis=0)))
            if observed_points != set(map(tuple, points)) or not links:
                raise ValueError('Every observed cut endpoint must be retained in the repaired contour')
            bridge_edges = {frozenset((tuple(r['a']), tuple(r['b']))) for r in links}
            dense = []
            for a, b in zip(points, np.roll(points, -1, axis=0)):
                count = max(1, math.ceil(np.linalg.norm(b-a)/.25)) if frozenset((tuple(a),tuple(b))) in bridge_edges else 1
                dense.extend(a + (b-a)*i/count for i in range(count))
            points = np.asarray(dense)
        # shortcut: a terminal section crop remains artificial; replace it when a complete tip surface is qualified.
        profile = fitted_profile(points, direction, 128, case['profile_smoothing_source_units'])
        if station in repaired_stations:
            repaired[station] = {'profile':profile, 'links':links}
        else:
            acquired[station] = profile
        cuts[station] = segments
    result = correct(reference, case['blade_id'], acquired, repaired)
    out = fresh(output); save(out/'case.json', case)
    for station, segments in cuts.items():
        profile = acquired[station] if station in acquired else repaired[station]['profile']
        np.savez_compressed(out/f'cut-{station:.12g}.npz', segments=segments, fitted=profile)
    result.update(classification='own_scan_tip_recovered_with_labelled_local_gap_chords',
                  parent_sections_sha256=sha(source), tip_recovery_case_sha256=sha(case_path), scale_verified=False)
    save(out/'sections.json', result)
    if sha(source) != case['reference_sections_sha256'] or sha(observed) != case['observed_mesh_sha256']:
        raise ValueError('Input changed during recovery')
    save(out/'receipt.json', {'classification':result['classification'], 'blade_id':case['blade_id'],
        'parent_sections_sha256':sha(source), 'observed_mesh_sha256':sha(observed), 'sections_sha256':sha(out/'sections.json'),
        'recovered_stations_source_units':requested, 'observed_terminal_vertex_station_source_units':maximum,
        'locally_repaired_stations':{str(s): row['links'] for s,row in repaired.items()},
        'maximum_repair_gap_source_units':gap_bound, 'every_observed_cut_endpoint_retained':True,
        'artificial_terminal_crop_margin_source_units':margin, 'terminal_cap_is_measured':False,
        'untargeted_blades_unchanged':True, 'existing_acquired_profiles_unchanged':True,
        'physical_validation':False, 'scale_verified':False, 'manufacturing_authorized':False})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('new_output', type=Path)
    args = parser.parse_args(); print(prepare(args.case, args.new_output))
