#!/usr/bin/env python3
"""Summarize native rotating-mode or elastic eigenstrain receipts without qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

from prepare_engineering_sensitivities import parse_mesh


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def completed(case):
    log = (case / 'log.ccx').read_text()
    if 'Job finished' not in log or '*ERROR' in log:
        raise ValueError('Native solver completion required')
    version = re.search(r'Version ([0-9.]+)', log)
    elapsed = re.search(r'Total CalculiX Time:\s*([0-9.]+)', log)
    return {'solver': 'CalculiX', 'version': version[1] if version else None,
            'elapsed_solver_seconds': float(elapsed[1]) if elapsed else None}


def displacement_blocks(path):
    blocks, active, values = [], False, {}
    with path.open() as stream:
        for line in stream:
            if line.startswith(' -4'):
                active = 'DISP' in line
                values = {}
            elif active and line.startswith(' -1'):
                tag = int(line[3:13])
                if tag in values:
                    raise ValueError('Duplicate displacement node')
                values[tag] = np.array([float(line[i:i+12]) for i in (13, 25, 37)])
            elif active and line.startswith(' -3'):
                blocks.append(values)
                active = False
    return blocks


def stress_blocks(path):
    blocks, current = [], None
    with path.open() as stream:
        for line in stream:
            if 'stresses (elem, integ.pnt.,sxx' in line:
                current = {}
                blocks.append(current)
                continue
            fields = line.split()
            if current is None or len(fields) != 8:
                continue
            try:
                element, ip = map(int, fields[:2])
                tensor = np.array(list(map(float, fields[2:])))
            except ValueError:
                continue
            if (element, ip) in current or not np.isfinite(tensor).all():
                raise ValueError('Duplicate or nonfinite integration point stress')
            current[element, ip] = tensor
    return blocks


def von_mises(tensor):
    x, y, z, xy, xz, yz = np.asarray(tensor).T
    return np.sqrt(.5 * ((x-y)**2 + (y-z)**2 + (z-x)**2) + 3*(xy**2+xz**2+yz**2))


def modes(root):
    prep = json.loads((root / 'preparation.json').read_text())
    result = []
    for spec in prep['cases']:
        case = root / spec['case']
        if sha(case / 'rotor.inp') != spec['deck_sha256']:
            raise ValueError('Modal deck changed after preparation')
        receipt = completed(case)
        chunks = (case / 'rotor.dat').read_text().split('E I G E N V A L U E   O U T P U T')[1:]
        if len(chunks) != (2 if spec['coriolis_requested'] else 1):
            raise ValueError('Missing or extra requested eigenvalue blocks')
        tables = []
        for index, chunk in enumerate(chunks):
            chunk = chunk.split('P A R T I C I P A T I O N')[0]
            table = []
            for line in chunk.splitlines():
                fields = line.split()
                expected = 5 if index == 0 else 4
                if len(fields) != expected or not fields[0].isdigit():
                    continue
                values = list(map(float, fields[1:]))
                angular, hz, imaginary = values[-3:]
                if not all(math.isfinite(v) for v in values) or angular <= 0 or hz <= 0:
                    raise ValueError('Invalid eigenvalue')
                if not math.isclose(angular, 2*math.pi*hz, rel_tol=1e-6):
                    raise ValueError('Eigenfrequency units mismatch')
                table.append({'output_order': int(fields[0]), 'frequency_hz': hz,
                              'angular_frequency_rad_s': angular, 'imaginary_rad_s': imaginary})
            if [v['output_order'] for v in table] != list(range(1, spec['requested_modes'] + 1)):
                raise ValueError('Incomplete mode table')
            tables.append(table)
        result.append({**spec, **receipt, 'prestressed_or_stationary_modes': tables[0],
                       'coriolis_modes': tables[1] if len(tables) > 1 else None,
                       'file_sha256': {name: sha(case/name) for name in ['rotor.inp','rotor.dat','log.ccx']}})
    return {'status': 'completed_fixed_bore_rotating_modal_sensitivity', 'cases': result,
            'assumptions': prep, 'mode_tracking_performed': False,
            'mesh_independence': False, 'physical_attachment_validated': False,
            'validated_campbell_diagram': False, 'safe_speed_rpm': None,
            'fatigue_life': None, 'manufacturing_authorized': False}


def eigenstrain(case):
    prep = json.loads((case / 'preparation.json').read_text())
    if sha(case/'rotor.inp') != prep['deck_sha256']:
        raise ValueError('Eigenstrain deck changed after preparation')
    nodes, elements = parse_mesh((case/'rotor.inp').read_text())
    displacements = displacement_blocks(case/'rotor.frd')
    stresses = stress_blocks(case/'rotor.dat')
    if len(displacements) != 2 or len(stresses) != 2:
        raise ValueError('Attached and released native fields required')
    expected = {(e, ip) for e in elements for ip in range(1, 5)}
    summaries = []
    for name, disp, stress in zip(['attached','released'], displacements, stresses):
        if set(disp) != set(nodes) or set(stress) != expected:
            raise ValueError('Native field coverage incomplete')
        tags = sorted(disp)
        u = np.array([disp[i] for i in tags])
        if not np.isfinite(u).all():
            raise ValueError('Nonfinite displacement')
        ip = sorted(stress)
        vm = von_mises(np.array([stress[i] for i in ip]))
        peak = ip[int(vm.argmax())]
        original = np.array([nodes[i] for i in tags])
        summaries.append({'state': name, 'nodes': len(tags), 'integration_points': len(ip),
                          'maximum_displacement_mm': float(np.linalg.norm(u,axis=1).max()),
                          'displacement_component_ranges_mm': np.ptp(u,axis=0).tolist(),
                          'maximum_radial_change_mm': float(np.max(np.abs(np.linalg.norm((original+u)[:,:2],axis=1)-np.linalg.norm(original[:,:2],axis=1)))),
                          'von_mises_max_MPa': float(vm.max()), 'von_mises_p99_MPa': float(np.quantile(vm,.99)),
                          'peak_element_and_ip': list(peak),
                          'peak_element_corner_centroid_mm': np.mean([nodes[i] for i in elements[peak[0]][:4]],axis=0).tolist()})
    release = np.array([displacements[1][i]-displacements[0][i] for i in sorted(nodes)])
    return {'status': 'completed_uncalibrated_elastic_eigenstrain_support_release',
            **completed(case), 'assumptions': prep, 'states': summaries,
            'maximum_release_displacement_mm': float(np.linalg.norm(release,axis=1).max()),
            'process_calibrated': False, 'distortion_prediction_qualified': False,
            'mesh_independence': False, 'manufacturing_authorized': False,
            'file_sha256': {name: sha(case/name) for name in ['rotor.inp','rotor.dat','rotor.frd','preparation.json','log.ccx']}}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('study', choices=['modes','eigenstrain'])
    p.add_argument('case', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args()
    value = modes(a.case) if a.study == 'modes' else eigenstrain(a.case)
    with a.output.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False); stream.write('\n')
    print('Native fields summarized; physical/process qualification remains open')
