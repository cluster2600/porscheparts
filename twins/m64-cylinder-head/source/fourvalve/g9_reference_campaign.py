#!/usr/bin/env python3
"""Fresh G8 deck replay and mesh extension, cross-checked with CUDA FP64 CG.

Not an assembled head, hot-material qualification, or manufacturing release.
Historical evidence is read-only; all output goes to a new private directory.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import g8_pilot as g8
import g8_matrix_benchmark as bench


def deck(text):
    """Strictly scoped to G8's one-step homogeneous-support linear decks."""
    if (text.count('*STEP\n') != 1 or text.count('*STATIC\n') != 1
            or text.count('*BOUNDARY\nSUPPORT,1,3\n') != 1):
        raise ValueError('requires one G8 static step and fixed SUPPORT')
    points, loads, support, mode = {}, {}, set(), ''
    for line in text.splitlines():
        if line.startswith('*'):
            mode = line
        elif line.strip():
            fields = line.split(',')
            if mode == '*NODE':
                n = int(fields[0])
                if n in points or len(fields) != 4:
                    raise ValueError('duplicate or malformed node')
                points[n] = np.array(list(map(float, fields[1:])))
            elif mode == '*NSET,NSET=SUPPORT':
                support.update(int(v) for v in fields if v.strip())
            elif mode == '*CLOAD':
                n, d, force = int(fields[0]), int(fields[1]), float(fields[2])
                if d not in (1, 2, 3) or (n, d) in loads:
                    raise ValueError('invalid or duplicate load DOF')
                loads[n, d] = force
    if (not support or not points or not loads or not support <= points.keys()
            or any(n not in points or n in support for n, _ in loads)
            or not np.isfinite(list(points.values())).all()
            or not np.isfinite(list(loads.values())).all()):
        raise ValueError('invalid nodes, loads, or supports')
    return points, loads, support


def rhs_for(mapping, loads):
    if not set(loads) <= set(mapping):
        raise ValueError('load omitted from free DOF map')
    rhs = np.array([loads.get(key, 0.) for key in mapping])
    if not np.linalg.norm(rhs) > 0:
        raise ValueError('zero RHS')
    return rhs


def ccx(case, name):
    start = time.monotonic()
    with (case / (name + '.log')).open('x') as log:
        done = subprocess.run(['ccx', name], cwd=case, stdout=log, stderr=subprocess.STDOUT,
                              timeout=900, env=dict(os.environ, OMP_NUM_THREADS='4', CCX_NPROC_STIFFNESS='4'))
    if done.returncode or '*ERROR' in (case / (name + '.log')).read_text():
        raise ValueError('CalculiX failed: ' + str(case / name))
    return time.monotonic() - start


def mechanics(case, name, points, loads, support):
    dat = case / (name + '.dat')
    u, rf = g8.vectors(dat, 'displacements ('), g8.vectors(dat, 'forces (')
    if set(u) != set(points) or set(rf) != support:
        raise ValueError('incomplete direct output')
    applied = defaultdict(lambda: np.zeros(3))
    for (n, d), f in loads.items():
        applied[n][d-1] += f
    force = sum(applied.values(), np.zeros(3))
    scale = np.linalg.norm(force)
    if not scale > 0:
        raise ValueError('unsupported self-equilibrated load case')
    force_error = np.linalg.norm(sum(rf.values(), np.zeros(3)) + force) / scale
    moment = sum((np.cross(points[n], f) for n, f in applied.items()), np.zeros(3))
    rm = sum((np.cross(points[n], f) for n, f in rf.items()), np.zeros(3))
    moment_error = np.linalg.norm(moment + rm) / (scale * 100)
    stress, displacement = g8.parse_dat(dat)
    if not np.isfinite(stress + displacement).all():
        raise ValueError('nonfinite stress/displacement')
    journals = {}
    for side, sign in (('intake', -1), ('exhaust', 1)):
        selected = {n: np.linalg.norm(f) for n, f in applied.items() if points[n][0] * sign > 0}
        if selected:
            journals[side] = (sum((f*np.array(u[n]) for n, f in selected.items()), np.zeros(3)) / sum(selected.values())).tolist()
    return u, {'force_balance_relative_error': float(force_error),
               'moment_balance_F_times_100mm_error': float(moment_error),
               'equilibrium_passed': bool(force_error <= 1e-4 and moment_error <= 1e-4),
               'maximum_displacement_mm': max(displacement),
               'von_Mises_p95_MPa': g8.percentile(stress, .95),
               'von_Mises_max_MPa': max(stress), 'journal_weighted_displacement_mm': journals}


def audit(case, names, legacy, backend):
    text = (case / (names[0] + '.inp')).read_text()
    points, _, support = deck(text)
    prefix = text.split('*STEP\n')[0]
    # Density is used only for the discarded mass matrix, not elastic K.
    with (case / 'matrix.inp').open('x') as stream:
        stream.write(prefix.replace('*SOLID SECTION', '*DENSITY\n2.7e-9\n*SOLID SECTION')
                     + '*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
    export_seconds = ccx(case, 'matrix')
    matrix, mapping = bench.read_matrix(case / 'matrix.sti', case / 'matrix.dof', points, support)
    rows = []
    for name in names:
        current = (case / (name + '.inp')).read_text()
        if current.split('*STEP\n')[0] != prefix:
            raise ValueError('load cases do not share stiffness geometry/material')
        _, loads, fixed = deck(current)
        if fixed != support:
            raise ValueError('support changed between load cases')
        reference, mechanical = mechanics(case, name, points, loads, support)
        rhs = rhs_for(mapping, loads)
        u, timing = bench.solve(matrix, rhs, backend, max_seconds=300)
        residual = float(np.linalg.norm(matrix @ u - rhs) / np.linalg.norm(rhs))
        agreement = bench.comparison(matrix, rhs, mapping, u, reference)
        old = legacy / case.name / (name + '.dat')
        # An OOM case may leave a partial DAT. Only the nine pinned records are references.
        historical = None
        if (case.name, name) in HISTORICAL:
            historical = {'dat_sha256': g8.sha256(old), **bench.comparison(
                matrix, rhs, mapping, u, g8.vectors(old, 'displacements ('))}
        passed = bool(timing['info'] == 0 and np.isfinite(u).all() and residual <= 1e-8
                      and mechanical['equilibrium_passed']
                      and agreement['max_nodal_difference_over_max_reference_U'] <= 1e-4
                      and agreement['printed_dat_relative_residual'] <= agreement['printed_dat_rounding_residual_bound'])
        if case.name == 'witness-2.0':
            analytic = 1000*40**3/(3*g8.E*(10**4/12)) + 1000*40/((5/6)*(g8.E/(2*(1+g8.NU)))*100)
            numeric = sum(f*reference[n][0] for (n, _), f in loads.items()) / sum(loads.values())
            mechanical['beam_plus_shear_reference_mm'] = analytic
            mechanical['beam_reference_relative_error'] = abs(numeric/analytic-1)
            passed = passed and mechanical['beam_reference_relative_error'] <= .05
        row = {'case': case.name, 'direction': name, 'nodes': len(points), 'free_dofs': len(mapping),
               'matrix_nnz': matrix.nnz, 'numerical_crosscheck_passed': passed,
               'export_seconds': export_seconds, 'relative_residual': residual,
               'solver': timing, 'fresh_direct': agreement, 'historical_comparison': historical,
               'mechanics': mechanical, 'hashes': {p.name: g8.sha256(p) for p in
                   (case/(name+'.inp'), case/(name+'.dat'), case/'matrix.inp', case/'matrix.sti', case/'matrix.dof')}}
        rows.append(row)
        print(json.dumps({'case': case.name, 'direction': name, 'passed': passed,
                          'max_U_mm': mechanical['maximum_displacement_mm']}), flush=True)
        if not passed:
            break
    return rows


RECEIPT = g8.REPO / 'twins/m64-cylinder-head/evidence/g8-carrier-pilot-20260925/direct.partial.json'
HISTORICAL = {(r['component']+'-'+str(r['mesh']['size_mm']), name): r['files_sha256']
              for r in json.loads(RECEIPT.read_text())['cases'] for name in r['solutions']}


def run(args):
    # Check all old evidence BEFORE launching any solve; never overwrite it.
    for (folder, name), hashes in HISTORICAL.items():
        for suffix in ('.inp', '.dat'):
            path = args.legacy / folder / (name + suffix)
            if g8.sha256(path) != hashes[name + suffix]:
                raise ValueError('historical input fingerprint mismatch: ' + str(path))
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'classification': 'G9_isolated_components_reference_requalification',
              'manufacturing_authorized': False, 'engine_start_authorized': False,
              'assembled_stiffness_qualified': False, 'hot_material_qualified': False,
              'source_sha256': g8.sha256(Path(__file__)), 'cases': [], 'complete': False}
    for component in ('witness', 'central_diaphragm', 'carrier_base_p'):
        for size in ((2.,) if component == 'witness' else (3., 2., 1.5)):
            case = args.output / (component + '-' + str(size))
            case.mkdir()
            names = ('x',) if component == 'witness' else ('x', 'minus_z')
            if component == 'carrier_base_p' and size == 1.5:
                baseline = json.loads(g8.BASELINE.read_text())
                for path, expected in baseline['source_sha256'].items():
                    if g8.sha256(g8.REPO / path) != expected:
                        raise ValueError('G7 source fingerprint mismatch: ' + path)
                if g8.sha256(args.cad / 'carrier_base_p.step') != baseline['files_sha256']['carrier_base_p.step']:
                    raise ValueError('G7 STEP fingerprint mismatch')
                p = baseline['values']
                axes = {s: g8.rocker_geometry.frame(p, s, 1)[0] for s in ('intake', 'exhaust')}
                forces = {s: max(r['G7_shaft_only']['outer_rib_reaction_N'] for r in baseline['screens']['shaft_comparison'] if r['side'] == s) for s in axes}
                points, elements, support, weights, mesh = g8.mesh(args.cad / 'carrier_base_p.step', size, p, axes, component, case)
                for name, direction in (('x', [1, 0, 0]), ('minus_z', [0, 0, -1])):
                    g8.solve(case, points, elements, support, weights, forces, direction, name)
                (case / 'mesh-info.json').write_text(json.dumps(mesh, indent=2))
            else:
                for name in names:
                    source = args.legacy / case.name / (name + '.inp')
                    if source.exists():
                        shutil.copyfile(source, case / source.name)
                    else:
                        if (component, size, name) != ('carrier_base_p', 2., 'minus_z'):
                            raise ValueError('unexpected missing deck')
                        text = (case / 'x.inp').read_text()
                        _, loads, _ = deck(text)
                        if any(d != 1 or f <= 0 for (_, d), f in loads.items()):
                            raise ValueError('expected positive x loads')
                        before, rest = text.split('*CLOAD\n')
                        after = rest[rest.index('*NODE PRINT'):]
                        (case / 'minus_z.inp').write_text(before + '*CLOAD\n' + ''.join(f'{n},3,{-f:.12g}\n' for (n, _), f in loads.items()) + after)
                    ccx(case, name)
            rows = audit(case, names, args.legacy, args.backend)
            report['cases'].extend(rows)
            (args.output / 'report.partial.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
            if not all(r['numerical_crosscheck_passed'] for r in rows):
                return 1
    report['complete'] = len(report['cases']) == 13
    (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy', type=Path, required=True)
    parser.add_argument('--cad', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('cpu', 'cuda'), default='cuda')
    raise SystemExit(run(parser.parse_args()))
