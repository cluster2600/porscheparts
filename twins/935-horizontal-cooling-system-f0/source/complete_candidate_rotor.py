#!/usr/bin/env python3
"""Close a scan-based rotor hypothesis; never qualify historical fitment."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

def validate(case):
    if case.get('purpose') != 'hypothesis_screen' or case.get('scale_verified') is not False:
        raise ValueError('Only explicitly uncalibrated hypotheses are accepted')
    for name in ('scale_mm_per_source_unit', 'wall_source_units', 'back_source_units',
                 'boss_radius_source_units', 'profile_stride', 'tip_radius_source_units'):
        value = case[name]
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError('Positive finite parameter required: ' + name)
    stride = case['profile_stride']
    if not isinstance(stride, int) or 128 % stride or 128 // stride < 16:
        raise ValueError('Profile stride must preserve at least 16 contour points')
    stations = case['stations_source_units']
    if len(stations) < 3 or stations != sorted(set(stations)) or not np.isfinite(stations).all():
        raise ValueError('Finite increasing stations required')
    if not case.get('assumptions') or any(not a.get('rejection_test') for a in case['assumptions']):
        raise ValueError('Every geometric hypothesis requires a rejection test')
    if case['hub_z_source_units'][0] >= case['hub_z_source_units'][1]:
        raise ValueError('Increasing hub interval required')


def local_profile(points, phase):
    p = np.asarray(points, dtype=float)
    c, s = math.cos(phase), math.sin(phase)
    return p @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def world_profile(points, phase):
    c, s = math.cos(phase), math.sin(phase)
    return np.asarray(points) @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def completed_sections(data, case):
    """Register one acquired blade; repeat it under an explicit periodic hypothesis."""
    validate(case)
    if data['schema'] != '935-observed-section-loft-v1':
        raise ValueError('Unknown section schema')
    by_blade = {}
    for region in data['regions']:
        blade = by_blade.setdefault(region['blade_id'], {'phase': region['phase_radians'], 'profiles': {}})
        for station, row in zip(region['stations_source_units'], region['profiles'], strict=True):
            p = local_profile(row, region['phase_radians'])
            if p.shape != (128, 3) or not np.isfinite(p).all() or not np.allclose(p[:, 0], station):
                raise ValueError('Invalid acquired profile or section plane')
            if station in blade['profiles']:
                raise ValueError('Overlapping blade regions require explicit selection')
            blade['profiles'][station] = p
    reference = by_blade[case['reference_blade_id']]
    donor_stations = sorted(reference['profiles'])
    registered = {}
    previous = None
    for station in donor_stations:
        profile = reference['profiles'][station]
        if previous is not None:
            shifts = [np.roll(profile, i, axis=0) for i in range(len(profile))]
            profile = min(shifts, key=lambda p: float(np.sum((p[:,1:] - previous[:,1:]) ** 2)))
        registered[station] = profile
        previous = profile
    if len(donor_stations) < 3:
        raise ValueError('At least three reference blade sections required')
    output = []
    names = sorted(by_blade)
    for index, name in enumerate(names):
        phase = reference['phase'] + (index - names.index(case['reference_blade_id'])) * 2 * math.pi / len(by_blade)
        rows, labels = [], []
        for station in case['stations_source_units']:
            if station in registered:
                p = registered[station].copy()
                label = 'registered_acquired_reference_section' if name == case['reference_blade_id'] else 'periodic_reference_reconstruction'
            elif station < donor_stations[0] or station > donor_stations[-1]:
                nearest = donor_stations[0] if station < donor_stations[0] else donor_stations[-1]
                p, label = registered[nearest].copy(), 'constant_profile_root_or_tip_design'
            else:
                interval = next(((a, b) for a, b in zip(donor_stations, donor_stations[1:])
                                 if a <= station <= b), None)
                a, b = interval
                p = registered[a] + (registered[b] - registered[a]) * (station - a) / (b - a)
                label = 'registered_reference_linear_interpolation'
            p[:, 0] = station
            rows.append(world_profile(p[::case['profile_stride']], phase).tolist())
            labels.append({'station_source_units': station, 'classification': label})
        output.append({'id': name, 'phase_radians': phase, 'profiles': rows, 'provenance': labels})
    return output


def build(case_path, output):
    from run_reconstruction import fresh, save, sha
    from build123d import Compound, Rot, Solid, Wire, export_step, export_stl, import_step
    case = json.loads(Path(case_path).read_text())
    validate(case)
    source, hub_path = Path(case['sections_path']), Path(case['hub_surfaces_path'])
    if sha(source) != case['sections_sha256'] or sha(hub_path) != case['hub_surfaces_sha256']:
        raise ValueError('Private geometry hash mismatch')
    data, hub_data = json.loads(source.read_text()), json.loads(hub_path.read_text())
    sections = completed_sections(data, case)
    out = fresh(output)
    save(out / 'case.json', case)
    save(out / 'completed-sections.json', {'purpose': 'hypothesis_screen', 'blades': sections})
    scale = case['scale_mm_per_source_unit']
    patches = hub_data['patches']
    bore_model, wall_model = (p['models'][p['preferred_model']] for p in patches)
    bore = bore_model['radius_at_zero_source_units'] * scale
    radius = wall_model['radius_at_zero_source_units'] * scale
    z0, z1 = np.asarray(case['hub_z_source_units']) * scale
    wall, back, boss = (case[k] * scale for k in
                       ('wall_source_units', 'back_source_units', 'boss_radius_source_units'))
    if not 0 < bore < boss < radius - wall or not 0 < back < z1 - z0:
        raise ValueError('Invalid cup closure hypothesis')
    # The cup, end caps and central boss are explicit design hypotheses, not scan measurements.
    hub = Solid.make_cylinder(radius, z1 - z0).translate((0, 0, z0))
    cavity = Solid.make_cylinder(radius - wall, z1 - z0 - back).translate((0, 0, z0 + back))
    hub = hub.cut(cavity)
    hub = hub.fuse(Solid.make_cylinder(boss, z1 - z0).translate((0, 0, z0)))
    hub = hub.cut(Solid.make_cylinder(bore, z1 - z0 + 2).translate((0, 0, z0 - 1)))
    blades = []
    for blade in sections:
        if not blades:
            wires = [Wire.make_polygon(np.asarray(row) * scale, close=True) for row in blade['profiles']]
            solid = Solid.make_loft(wires, ruled=True)
            z0_blade, z1_blade = np.asarray(blade['profiles'])[:,:,2].min() * scale, np.asarray(blade['profiles'])[:,:,2].max() * scale
            tip_crop = Solid.make_cylinder(case['tip_radius_source_units'] * scale, z1_blade - z0_blade + 2 * scale).translate((0,0,z0_blade - scale))
            solid = solid & tip_crop
        else:
            angle = (blade['phase_radians'] - sections[0]['phase_radians']) * 180 / math.pi
            solid = Rot(0,0,angle) * blades[0]
        if not solid.is_valid or len(solid.solids()) != 1 or solid.volume <= 0:
            raise ValueError('Invalid completed blade: ' + blade['id'])
        blades.append(solid)
    components = Compound(children=[hub, *blades])
    export_step(components, out / 'editable-candidate-components.step')
    export_stl(components, out / 'candidate-components.stl', tolerance=.2 * scale)
    check = import_step(out / 'editable-candidate-components.step')
    if not check.is_valid or abs(check.volume - components.volume) / components.volume > 1e-6:
        raise ValueError('STEP reread failed')
    if sha(source) != case['sections_sha256'] or sha(hub_path) != case['hub_surfaces_sha256']:
        raise ValueError('Input changed during reconstruction')
    save(out / 'receipt.json', {
        'schema': '935-closed-rotor-hypothesis-v1', 'status': 'candidate_components_ready_not_assembled',
        'case_sha256': sha(case_path), 'sections_sha256': sha(source), 'hub_surfaces_sha256': sha(hub_path),
        'scale_mm_per_source_unit': scale, 'scale_verified': False,
        'blade_count': len(blades), 'solid_count': len(blades) + 1,
        'component_volume_sum_mm3_with_overlaps': components.volume,
        'STEP_reread_relative_volume_error': abs(check.volume - components.volume) / components.volume,
        'observed_profiles_resampled_stride': case['profile_stride'],
        'historical_identity_verified': False, 'manufacturing_authorized': False,
        'physical_validation': False,
        'artifacts': {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.case, args.output))
