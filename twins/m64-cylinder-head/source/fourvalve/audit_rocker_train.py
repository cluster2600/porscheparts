#!/usr/bin/env python3
"""Audit cinématique G5 : loi -> profil de came -> levée retrouvée, puis contrôles CAO.

Usage : audit_rocker_train.py G4_CANDIDATE.json NEW_OUTPUT_DIRECTORY
"""
import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import assembly
import cadquery as cq
import checks
import components as comp
import kinematics as kin
import layout
import numpy as np
import provenance
import rocker_geometry as rg
import rocker_train as rt


def audit(candidate, out):
    out.mkdir(parents=True, exist_ok=False)
    p = json.loads(candidate.read_text())['values']
    extra = HERE / 'params-rockers/rocker_train.json'
    for name, row in json.loads(extra.read_text())['parameters'].items():
        provenance.verify_provenance(name, row, {})
        p[name] = row['value']
    rows, summary = checks.evaluate(p, .5, force_cycle=True)
    numerics = {}
    laws = kin.cam_laws(p)[0]
    phases = {0.0, 90.0, 180.0, 360.0, 540.0, 630.0, 719.0}
    for side in layout.SIDES:
        convergence = []
        phi = np.arange(.37, 720, 3.0)  # hors des sommets du profil
        target = rg.state(p, side, phi)
        for step in (2.0, 1.0, .5):
            profile = rg.profile(p, side, step)
            recovered = rg.recover_valve_lift(p, side, phi, profile['points'])
            centres = target['roller'] - [p['rocker_cam_arm'], p['cam_base_circle_radius'] + p['rocker_roller_radius']]
            distance = rg.point_to_polygon_distance(rg.rotate(centres, -np.radians(phi / 2)), profile['points'])
            convergence.append({'crank_step_deg': step, 'vertices': len(profile['points']),
                                'maximum_recovered_lift_error_mm': float(np.max(abs(recovered - target['valve_lift_mm']))),
                                'maximum_global_contact_error_mm': float(np.max(abs(distance - p['rocker_roller_radius'])))})
        fine = profile
        phases.update([math.degrees(laws[side].centreline_rad), float(fine['phi_deg'][np.argmax(fine['pressure_deg'])])])
        radii = -1 / fine['pitch_curvature'][fine['pitch_curvature'] < 0]
        numerics[side] = {'convergence': convergence, 'maximum_pressure_angle_deg': float(max(fine['pressure_deg'])),
                          'maximum_swing_deg': float(np.degrees(max(fine['state']['beta']))),
                          'maximum_tip_walk_mm': float(max(fine['state']['tip_walk_mm'])),
                          'minimum_convex_pitch_radius_mm': float(min(radii)),
                          'tip_radius_mm': p['guide_bore_diameter'] / 2 - .02}
        numerics[side]['cam_body_clearances'] = rg.cam_body_clearances(p, fine)
        np.savetxt(out / f'cam-profile-{side}.csv', np.column_stack((fine['phi_deg'] / 2, fine['points'])),
                   delimiter=',', header='cam_angle_deg,x_mm,z_mm', comments='', fmt='%.9f')
    arm_screen = []
    for a, b in ((35, 21), (35, 23), (40, 23), (40, 24), (40, 25), (45, 24)):
        q = dict(p, rocker_valve_arm=a, rocker_cam_arm=b)
        arm_screen.append({'valve_arm_mm': a, 'cam_arm_mm': b,
                          'clearances': {s: rg.cam_body_clearances(q, rg.profile(q, s)) for s in layout.SIDES}})
    print(json.dumps({'numerics': numerics, 'phases': sorted(phases)}), flush=True)
    head = comp.head(p)
    native = []
    for phi in sorted(phases):
        for side in layout.SIDES:
            cam = rt.camshaft(p, side, phi)
            state = rg.state(p, side, phi)
            lift = float(state['valve_lift_mm'][0])
            expected_gap = max(state['lash_mm'] - float(state['gross_displacement_mm'][0]), 0)
            for sy in (1, -1):
                pieces = rt.moving_parts(p, side, sy, phi)
                valve, spring, retainer = comp.valve(p, side, sy, lift), comp.spring(p, side, sy, lift), comp.retainer(p, side, sy, lift)
                overlaps = {f'rocker/{n}': pieces['rocker'].intersect(s).Volume() for n, s in
                            [('head', head), ('cam', cam), ('roller', pieces['roller']), ('valve', valve), ('spring', spring), ('retainer', retainer)]}
                overlaps['roller/cam'] = pieces['roller'].intersect(cam).Volume()
                cam_gap = assembly.brep_distance(cam, pieces['roller'])
                tip_gap = assembly.brep_distance(pieces['rocker'], valve)
                valid = all(assembly.brep_valid(s) for s in [cam, *pieces.values()])
                native.append({'phi_deg': phi, 'side': side, 'sy': sy, 'brep_valid': valid,
                               'cam_roller_gap_mm': cam_gap, 'rocker_valve_gap_mm': tip_gap,
                               'expected_lash_gap_mm': expected_gap, 'overlap_mm3': overlaps,
                               'passed': bool(valid and cam_gap <= .001 and abs(tip_gap - expected_gap) <= .001
                                              and max(abs(v) for v in overlaps.values()) <= .001)})
        print(json.dumps({'native_phase_finished': phi}), flush=True)
    shapes = assembly.parts(p, 0)
    half = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, p['intake_valve_y'], -500))
    section = cq.Compound.makeCompound([s.cut(half) for s in shapes.values()]).rotate((0, 0, 0), (1, 0, 0), -90)
    cq.exporters.export(cq.Workplane().add(section), str(out / 'rocker-train-section.svg'),
                        opt={'projectionDir': (0, 0, -1), 'showHidden': False, 'strokeWidth': .15,
                             'width': 1100, 'height': None, 'marginLeft': 20, 'marginTop': 20})
    svg = out / 'rocker-train-section.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    assembly._export([s for n, s in shapes.items() if n.startswith(('rocker_', 'roller_'))], out / 'rockers-rollers-and-shafts.step')
    (out / 'candidate.json').write_text(json.dumps({'values': p, 'manufacturing_authorized': False}, indent=2) + '\n')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {'artifact': 'm64_g5_articulated_rocker_audit', 'manufacturing_authorized': False,
              'engine_start_authorized': False, 'master_geometry': False, 'status': 'kinematic_candidate_not_dynamic_validation',
              'geometry_checks': rows, 'geometry_summary': summary, 'numerics': numerics, 'native_checks': native,
              'bounded_arm_screen_not_global_optimum': arm_screen,
              'all_native_contact_samples_passed': all(r['passed'] for r in native),
              'assembly_brep_validity': {n: assembly.brep_valid(s) for n, s in shapes.items()},
              'numerical_tolerances': {'distance_mm': .001, 'overlap_volume_mm3': .001, 'manufacturing_tolerances': False},
              'candidate_sha256': sha(candidate), 'rocker_parameters_sha256': sha(extra),
              'valvetrain_law_sha256': sha(layout.REPO_VALVETRAIN),
              'source_sha256': {str(f.relative_to(HERE)): sha(f) for f in
                               sorted(list(HERE.glob('*.py')) + list((HERE / 'cad').glob('*.py')))},
              'files_sha256': {f.name: sha(f) for f in sorted(out.iterdir())},
              'environment': {'python': platform.python_version(), 'cadquery': cq.__version__, 'numpy': np.__version__},
              'method_source': 'https://www.cs.cmu.edu/~rapidproto/mechanisms/chpt6.html',
              'limitations': ['rigid kinematics with assumed cold lash, not a hydraulic lash adjuster',
                              'carrier, bearings, fastener access and lubrication not designed',
                              'no inertia, spring surge, Hertz stress, wear or fatigue qualification',
                              'native collision checks are discrete samples, not continuous collision detection',
                              'head remains a synthetic candidate, not certified M64 geometry',
                              'no CFD/CHT, hot material card or qualified additive manufacturing process']}
    (out / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'native_passed': result['all_native_contact_samples_passed'], 'cases': len(native)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.candidate, args.output)
