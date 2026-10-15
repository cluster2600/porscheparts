#!/usr/bin/env python3
"""Audit the complete conditional 935 hexahedral solve and export sparse fields."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np

from run_reconstruction import ROOT, fresh, save, sha

sys.path.insert(0, str(ROOT / 'twins/fan-alloy-comparison-f0/source'))
from compare_alloys import static_results


def assess(prepared, solved, output):
    prepared, solved = Path(prepared), Path(solved)
    receipt = json.loads((prepared / 'receipt.json').read_text())
    case = json.loads((prepared / 'case.json').read_text())
    if case['purpose'] != 'hypothesis_screen' or case['scale_verified'] is not False:
        raise ValueError('Uncalibrated hypothesis required')
    deck_hash = receipt['deck_sha256']
    if sha(prepared / 'rotor.inp') != deck_hash or (solved / 'ccx.exit').read_text().strip() != '0':
        raise ValueError('Pinned prepared deck and successful execution required')
    if sha(solved / 'ccx.log') != sha(solved / 'log.rotor'):
        raise ValueError('Parser log alias differs from the original solver log')
    result = static_results(solved, deck_hash)
    grid_path = ROOT / Path(case['grid_path']).relative_to('/repo')
    if sha(grid_path) != case['grid_sha256']:
        raise ValueError('Grid changed')
    grid = json.loads(grid_path.read_text())
    if grid['input_sha256'] != receipt['geometry_sha256']:
        raise ValueError('Geometry and grid differ')
    centres = (np.asarray(grid['cells'], dtype=float) + .5) * grid['pitch_mm']
    count = result['elements']
    if count != len(centres) or receipt['C3D8_elements'] != count:
        raise ValueError('Element coverage differs from preparation')
    xyz = np.zeros((result['nodes'] + 1, 3)); active = False
    for line in (solved / 'rotor.inp').read_text().splitlines():
        if line.startswith('*'):
            active = line == '*NODE'
        elif active:
            row = line.split(','); xyz[int(row[0])] = list(map(float, row[1:]))
    displacement, reactions = {}, {}
    peak = np.zeros(count); gauss_mask = np.zeros(count, dtype=np.uint16)
    active = ''
    for line in (solved / 'rotor.dat').read_text().splitlines():
        if 'forces (fx,fy,fz)' in line and 'total force' not in line:
            active = 'reaction'; continue
        if 'displacements (vx,vy,vz)' in line:
            active = 'displacement'; continue
        if 'stresses (elem, integ.pnt.' in line:
            active = 'stress'; continue
        row = line.split()
        if not row or not row[0].isdigit():
            continue
        if active in ('reaction', 'displacement') and len(row) == 4:
            target = reactions if active == 'reaction' else displacement
            node = int(row[0])
            if node in target or not 1 <= node < len(xyz):
                raise ValueError('Duplicate or unexpected node result')
            target[node] = np.asarray(list(map(float, row[1:])))
        elif active == 'stress' and len(row) == 8:
            element, point = int(row[0]) - 1, int(row[1])
            if not 0 <= element < count or not 1 <= point <= 8 or gauss_mask[element] & (1 << (point - 1)):
                raise ValueError('Duplicate or unexpected integration point')
            gauss_mask[element] |= 1 << (point - 1)
            xx, yy, zz, xy, xz, yz = map(float, row[2:])
            if not all(math.isfinite(x) for x in (xx, yy, zz, xy, xz, yz)):
                raise ValueError('Nonfinite integration point stress')
            peak[element] = max(peak[element], math.sqrt(.5*((xx-yy)**2+(yy-zz)**2+(zz-xx)**2) + 3*(xy*xy+xz*xz+yz*yz)))
    if (np.any(gauss_mask != 255) or len(displacement) != result['nodes'] or
            len(reactions) != receipt['clamped_bore_nodes']):
        raise ValueError('Complete eight-point stress, displacement and bore reaction coverage required')
    if not np.isfinite(np.concatenate([peak, *displacement.values(), *reactions.values()])).all():
        raise ValueError('Nonfinite results')
    cards = ROOT / 'twins/935-horizontal-cooling-system-f0/vast-omniverse-screen/materials.json'
    if sha(cards) != receipt['material_cards_sha256']:
        raise ValueError('Material cards changed')
    material = next(c for c in json.loads(cards.read_text())['materials'] if c['id'] == case['material_id'])
    mass_per_element = material['density_g_cm3'] * 1e-9 * grid['pitch_mm']**3
    force = mass_per_element * (case['rotor_rpm'] * math.pi/30)**2 * centres
    force[:, 2] = 0
    reaction = np.sum(list(reactions.values()), axis=0)
    moment = np.sum([np.cross(xyz[node], value) for node, value in reactions.items()], axis=0)
    force_error = float(np.linalg.norm(reaction + force.sum(axis=0)) / np.linalg.norm(np.abs(force).sum(axis=0)))
    body_moments = np.cross(centres, force)
    moment_error = float(np.linalg.norm(moment + body_moments.sum(axis=0)) / max(np.linalg.norm(np.abs(body_moments).sum(axis=0)), 1e-30))
    away = np.linalg.norm(centres[:, :2], axis=1) >= 25
    result.update(classification='conditional_nine_blade_centrifugal_screen',
        geometry_sha256=receipt['geometry_sha256'], grid_sha256=case['grid_sha256'], material_id=case['material_id'],
        pitch_mm=grid['pitch_mm'], rotor_rpm=case['rotor_rpm'],
        element_peak_p95_outside_r25_MPa=float(np.percentile(peak[away], 95)),
        relative_force_balance_error=force_error, relative_moment_balance_error=moment_error,
        reaction_balance_pass=force_error < 1e-5 and moment_error < 1e-5,
        conditional_grid_mass_kg=mass_per_element * count * 1000,
        grid_volume_relative_error=receipt['CAD_volume_relative_error'],
        poisson_ratio_assumed=.33, pressure_or_thermal_loads=False, material_process_qualified=False,
        scale_verified=False, mesh_convergence_established=False, allowable_speed_or_fatigue_validated=False,
        manufacturing_authorized=False, physical_validation=False)
    out = fresh(output)
    for name, rows in [('node-displacement.csv', ([*xyz[node], *displacement[node]] for node in sorted(displacement))),
                       ('element-peak-stress.csv', ([*centre, stress] for centre, stress in zip(centres, peak)))]:
        with (out / name).open('w') as stream:
            writer = csv.writer(stream); writer.writerows(rows)
    result['sparse_csv_sha256'] = {name: sha(out / name) for name in ('node-displacement.csv', 'element-peak-stress.csv')}
    save(out / 'assessment.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'solved', 'new_output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.prepared, args.solved, args.new_output), indent=2))
