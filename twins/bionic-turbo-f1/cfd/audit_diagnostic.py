#!/usr/bin/env python3
"""Audit diagnostic histories and distinguish relative MRF flux from wall leakage."""
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from audit_case import table, window_metrics
from check_cartesian_cells import rectangles
from prepare_case import CRITERIA, sha
from run_case import ascii_faces
from run_cartesian_pilot import verify


def ascii_list(text, vector=False):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    match = re.fullmatch(r'\s*FoamFile\s*\{[^{}]*format\s+ascii;[^{}]*\}\s*(\d+)\s*\((.*)\)\s*', text, re.S)
    if not match:
        raise ValueError('Complete ASCII list required')
    values = np.fromstring(match[2].translate(str.maketrans('()', '  ')), sep=' ')
    if values.size != int(match[1]) * (3 if vector else 1) or not np.isfinite(values).all():
        raise ValueError('List count or finite-value check failed')
    return values.reshape(-1, 3) if vector else values


def scalar_patch(text, patch, count):
    text = text[text.index('boundaryField'):]
    block = re.search(r'\b' + re.escape(patch) + r'\s*\{(.*?)\n\s*\}', text, re.S)
    if not block:
        raise ValueError('Missing field patch')
    uniform = re.search(r'\bvalue\s+uniform\s+([^;]+);', block[1])
    if uniform:
        result = np.full(count, float(uniform[1]))
    else:
        match = re.search(r'\bvalue\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;', block[1], re.S)
        if not match or int(match[1]) != count:
            raise ValueError('Missing or incomplete scalar patch')
        result = np.fromstring(match[2], sep=' ')
    if len(result) != count or not np.isfinite(result).all():
        raise ValueError('Nonfinite or incomplete boundary values')
    return result


def face_geometry(vertices):
    # A hanging midpoint changes the vertex average, not the rectangular face centroid.
    lo, hi, axis, sign, area = rectangles(np.asarray(vertices)[None, ...])
    sf = np.zeros(3)
    sf[axis[0]] = sign[0] * area[0]
    return .5 * (lo[0] + hi[0]), sf


def wall_snapshot(case, checkpoint, inputs):
    def read(name):
        path = case / name
        inputs[name] = sha(path)
        return path.read_text()
    mesh = 'constant/polyMesh/'
    points = ascii_list(read(mesh + 'points'), vector=True)
    owner = ascii_list(read(mesh + 'owner')).astype(np.int64)
    zones = read(mesh + 'cellZones')
    zone = re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)', zones, re.S)
    if not zone:
        raise ValueError('Missing rotor zone')
    cells = np.fromstring(zone[2], sep=' ', dtype=np.int64)
    if len(cells) != int(zone[1]):
        raise ValueError('Rotor zone size mismatch')
    block = re.search(r'\bstator\s*\{([^{}]*)\}', read(mesh + 'boundary'))[1]
    count = int(re.search(r'nFaces\s+(\d+)', block)[1])
    start = int(re.search(r'startFace\s+(\d+)', block)[1])
    faces = [f for i, f in enumerate(ascii_faces(read(mesh + 'faces'))) if start <= i < start + count]
    if len(faces) != count:
        raise ValueError('Incomplete boundary faces')
    cf = np.empty((count, 3)); sf = np.empty_like(cf)
    # Batch equal-length faces to keep the exhaustive check inexpensive.
    lengths = np.fromiter(map(len, faces), dtype=np.int64)
    for length in np.unique(lengths):
        ids = np.flatnonzero(lengths == length)
        for offset in range(0, len(ids), 20000):
            selected = ids[offset:offset + 20000]
            vertices = points[np.array([faces[i] for i in selected])]
            lo, hi, axis, sign, area = rectangles(vertices)
            cf[selected] = .5 * (lo + hi)
            sf[selected] = 0
            sf[selected, axis] = sign * area
    active = np.isin(owner[start:start + count], cells)
    rho = scalar_patch(read(checkpoint + '/rho'), 'stator', count)
    relative = scalar_patch(read(checkpoint + '/phi'), 'stator', count)
    omega = float(re.search(r'omega\s+constant\s+([^;]+)', read('constant/MRFProperties'))[1])
    frame = rho * np.einsum('ij,ij->i', np.cross([0, 0, omega], cf), sf) * active
    absolute = relative + frame
    return {'checkpoint': checkpoint, 'stator_faces': count, 'stator_faces_inside_MRF': int(active.sum()),
            'relative_gross_kg_s': float(abs(relative).sum()), 'frame_gross_kg_s': float(abs(frame).sum()),
            'absolute_gross_kg_s': float(abs(absolute).sum()), 'absolute_net_kg_s': float(absolute.sum()),
            'absolute_max_face_kg_s': float(abs(absolute).max()),
            'formula': 'phi_absolute = phi_relative + rho * (Omega cross Cf) dot Sf on stator faces owned by the MRF zone',
            'source_url': 'https://api.openfoam.com/2406/MRFZoneTemplates_8C_source.html'}


def history_metrics(series, omega, physical_time):
    times = [r[0] for r in series['inlet']]
    if any([r[0] for r in rows] != times for rows in series.values()):
        raise ValueError('Histories must have exactly matching times')
    if not math.isfinite(omega) or omega == 0:
        raise ValueError('Invalid rotation')
    inlet, outlet = [r[1] for r in series['inlet']], [r[1] for r in series['outlet']]
    power = [-omega * r[3] for r in series['moment']]
    energy = [a[1] + b[1] + .5 * (a[2] + b[2]) for a, b in zip(series['energy_inlet'], series['energy_outlet'])]
    window = CRITERIA['window_iterations']
    last = {'outlet_mass_flow_kg_s': outlet[-1], 'inlet_mass_flow_kg_s': inlet[-1], 'shaft_input_power_w': power[-1],
            'net_outward_total_enthalpy_flux_w': energy[-1], 'minimum_pressure_Pa': series['minima'][-1][1],
            'minimum_temperature_K': series['minima'][-1][2]}
    checks = {'positive_p_T_entire_history': all(min(r[1:]) > 0 for r in series['minima']),
              'forward_flow_last_window': all(mi < 0 and mo > 0 for mi, mo in zip(inlet[-window:], outlet[-window:]))}
    stability = {}
    if not physical_time and len(times) >= 2 * window:
        for name, values in (('outlet_mass_flow_kg_s', outlet), ('shaft_input_power_w', power)):
            stability[name] = window_metrics(values, window, CRITERIA)
        checks['stationary_observables'] = all(m['passed'] for m in stability.values())
        checks['port_mass_balance'] = all(abs(mi + mo) / max(abs(mi), abs(mo), 1e-30) <= CRITERIA['relative_mass_imbalance_max'] for mi, mo in zip(inlet[-window:], outlet[-window:]))
        checks['positive_shaft_power'] = all(p > 0 for p in power[-window:])
        checks['steady_port_energy_balance'] = all(abs(e - p) / max(abs(p), 1e-30) <= CRITERIA['relative_energy_imbalance_max'] for e, p in zip(energy[-window:], power[-window:]))
    else:
        checks['steady_state_demonstrated'] = False
    return {'samples': len(times), 'last_time_coordinate': times[-1], 'time_semantics': 'physical_seconds' if physical_time else 'pseudo_time_iterations',
            'last_sample_not_a_performance_rating': last, 'checks': checks, 'stability': stability,
            'energy_balance_note': 'Transient storage is not audited; steady work/port-energy comparison only when pseudo-time windows exist.'}


def audit(case):
    inputs = verify(case)
    manifest = json.loads((case / 'case-manifest.json').read_text())
    completion = json.loads((case / 'native-exit.json').read_text())
    log = case / 'log.transient-rhoPimpleFoam'
    if completion.get('exit_code') != 0 or not log.read_text().rstrip().endswith('End') or (case / 'rejection-reason.txt').exists():
        raise ValueError('Successful completed native run required; failure must remain rejected')
    inputs['native-exit.json'], inputs[log.name] = sha(case / 'native-exit.json'), sha(log)
    series = {}
    for key, name, width in [('inlet','mass_inlet/0/surfaceFieldValue.dat',2), ('outlet','mass_outlet/0/surfaceFieldValue.dat',2),
                            ('energy_inlet','energy_inlet/0/surfaceFieldValue.dat',3), ('energy_outlet','energy_outlet/0/surfaceFieldValue.dat',3),
                            ('moment','rotorForces/0/moment.dat',10), ('minima','scalarMinima/0/volFieldValue.dat',3)]:
        path = case / 'postProcessing' / name
        inputs[str(path.relative_to(case))] = sha(path)
        series[key] = table(path, width)
    physical = manifest.get('active_solve', {}).get('time_semantics') != 'local_pseudo_time_iterations_not_seconds'
    report = history_metrics(series, manifest['rpm'] * manifest['rotation_sign'] * math.pi / 30, physical)
    checkpoint = max((p.name for p in case.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name)), key=float)
    report['physical_wall_flux_at_last_saved_checkpoint'] = wall_snapshot(case, checkpoint, inputs)
    if any(sha(case / name) != digest for name, digest in inputs.items()):
        raise ValueError('Evidence changed during audit')
    report.update(schema='bionic-diagnostic-audit/v1', source_sha256=sha(Path(__file__)), input_sha256=inputs,
                  performance_ranking_authorized=False, engineering_validated=False, canonical_mesh_gate_passed=False,
                  status='diagnostic_evidence_only_not_performance_qualification')
    return report


if __name__ == '__main__':
    report = audit(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'samples', 'checks')}))
