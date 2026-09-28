#!/usr/bin/env python3
"""Bounded G11 isolated-support campaign. No assembly or manufacturing release."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import numpy as np
import g8_pilot as g8
import g9_reference_campaign as g9

SIDES = ('intake', 'exhaust')
DIRECTIONS = (('x', [1, 0, 0]), ('minus_z', [0, 0, -1]))


def publish(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_hashes():
    return {Path(m.__file__).name: g8.sha256(Path(m.__file__))
            for m in (sys.modules[__name__], g8, g9, g9.bench)}


def inputs(path):
    receipt = json.loads(path.read_text())
    baseline = json.loads(g8.BASELINE.read_text())
    if receipt.get('complete') is not True or receipt['baseline_sha256'] != g8.sha256(g8.BASELINE):
        raise ValueError('complete CAD receipt and unchanged G7 baseline required')
    if receipt['source_sha256'] != g8.sha256(Path(__file__).with_name('g11_cad.py')):
        raise ValueError('CAD producer fingerprint mismatch')
    if receipt['values'] != baseline['values']:
        raise ValueError('baseline axes/material geometry parameters changed')
    for name, expected in baseline['source_sha256'].items():
        if g8.sha256(g8.REPO / name) != expected:
            raise ValueError('G7 source fingerprint mismatch: ' + name)
    expected = {f'outer_d{d}_w{w}' for d in (18, 24, 30) for w in (18, 24, 30)}
    expected |= {f'centre_w{w}' for w in (10, 11, 12)}
    variants = receipt['variants']
    if len(variants) != 12 or {v['id'] for v in variants} != expected:
        raise ValueError('expected exactly the agreed twelve unique variants')
    for v in variants:
        component = 'carrier_base_p' if v['id'].startswith('outer_') else 'central_diaphragm'
        width = 8. if component == 'carrier_base_p' else float(v['id'].split('_w')[1])
        if v['component'] != component or v['journal_width_mm'] != width:
            raise ValueError('component or journal width differs from declared design')
        outer = component == 'carrier_base_p'
        parameters = {'bridge_depth_mm': int(v['id'].split('_')[1][1:]) if outer else 18,
                      'bridge_x_width_mm': int(v['id'].split('_w')[1]) if outer else 18,
                      'centre_wall_mm': 10 if outer else width}
        if v['parameters'] != parameters:
            raise ValueError('variant ID and design parameters disagree')
        if type(v['cad_accepted']) is not bool:
            raise ValueError('CAD gate must be explicit boolean')
        if v['cad_accepted']:
            step = (path.parent / v['step']).resolve()
            if (not step.is_relative_to(path.parent.resolve()) or step.suffix != '.step'
                    or g8.sha256(step) != v['step_sha256']
                    or not math.isfinite(v['volume_mm3']) or v['volume_mm3'] <= 0
                    or v['rejections']):
                raise ValueError('invalid accepted STEP, volume, or CAD rejection state')
    return receipt, baseline


def journal_interval(p, side, component, width):
    centre = 0. if component == 'central_diaphragm' else p[side+'_valve_y'] + p['rocker_width']/2 + 1. + 4.
    return centre-width/2, centre+width/2


def is_journal(corners, surface_type, axis, radius, interval):
    lo, hi = interval
    return (surface_type == 'Cylinder'
            and np.all(np.abs(np.hypot(corners[:, 0]-axis[0], corners[:, 2]-axis[2])-radius) < 1e-5)
            and np.min(corners[:, 1]) >= lo-1e-5 and np.max(corners[:, 1]) <= hi+1e-5)


def mesh(step, size, p, variant, case):
    """G8 quadratic mesh method, but select the declared bearing axial band.

    Wider central walls must not inherit G8's hardcoded 10 mm area check.
    The outer bridge is not allowed to masquerade as an enlarged journal.
    """
    import gmsh
    axes = {s: g8.rocker_geometry.frame(p, s, 1)[0] for s in SIDES}
    width = variant['journal_width_mm']
    radius = p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 4)
        gmsh.merge(str(step))
        if len(gmsh.model.getEntities(3)) != 1:
            raise ValueError('one BRep solid required')
        for key, value in {'MeshSizeMin': size, 'MeshSizeMax': size, 'ElementOrder': 2,
                           'SecondOrderLinear': 1, 'Algorithm3D': 10}.items():
            gmsh.option.setNumber('Mesh.'+key, value)
        gmsh.model.mesh.generate(3)
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        points = {int(n): tuple(map(float, q)) for n, q in zip(tags, xyz.reshape(-1, 3))}
        types, tags, conn = gmsh.model.mesh.getElements(3)
        if list(types) != [11]:
            raise ValueError('quadratic tetrahedra required')
        elements = [(int(n), g8.ccx_tetra10(list(map(int, q)))) for n, q in zip(tags[0], conn[0].reshape(-1, 10))]
        ip, _ = gmsh.model.mesh.getIntegrationPoints(11, 'Gauss4')
        _, det, _ = gmsh.model.mesh.getJacobians(11, ip)
        if not np.isfinite(det).all() or min(det) <= 0:
            raise ValueError('invalid element Jacobian')
        support, zones = set(), {s: [] for s in SIDES}
        for _, surface in gmsh.model.getEntities(2):
            types, _, conn = gmsh.model.mesh.getElements(2, surface)
            if list(types) != [9]:
                raise ValueError('quadratic boundary triangles required')
            triangles = conn[0].reshape(-1, 6)
            corners = np.array([points[int(n)] for t in triangles for n in t[:3]])
            if np.all(np.abs(corners[:, 2]-p['carrier_face_height']) < 1e-5):
                support.update(map(int, triangles.flat))
            for side, axis in axes.items():
                if is_journal(corners, gmsh.model.getType(2, surface), axis, radius,
                              journal_interval(p, side, variant['component'], width)):
                    zones[side].extend(triangles)
        weights, areas, intervals = {}, {}, {}
        for side, triangles in zones.items():
            weights[side], areas[side] = g8.surface_weights(triangles, points)
            y = [points[int(n)][1] for triangle in triangles for n in triangle[:3]]
            intervals[side] = [min(y), max(y)]
            if (support.intersection(weights[side])
                    or not .85 < areas[side]/(2*math.pi*radius*width) < 1.01
                    or not np.allclose(intervals[side], journal_interval(p, side, variant['component'], width), atol=1e-5, rtol=0)):
                raise ValueError('journal area/axial extent or load/support integrity failed')
        if len(support) < 6:
            raise ValueError('insufficient fixed-foot nodes')
        gmsh.write(str(case/'mesh.msh'))
        return points, elements, sorted(support), weights, {
            'size_mm': size, 'nodes': len(points), 'elements': len(elements),
            'fixed_nodes': len(support), 'surface_area_mm2': areas,
            'journal_axial_interval_mm': intervals, 'nominal_journal_width_mm': width,
            'minimum_Gauss4_Jacobian_mm3': float(min(det)), 'gmsh_version': gmsh.__version__}
    finally:
        gmsh.finalize()


def forces(baseline, component):
    field, factor = ('centre_wall_reaction_per_bay_N', 2) if component == 'central_diaphragm' else ('outer_rib_reaction_N', 1)
    return {s: factor*max(r['G7_shaft_only'][field] for r in baseline['screens']['shaft_comparison'] if r['side'] == s) for s in SIDES}


def worker(args):
    if sys.platform != 'linux':
        raise ValueError('campaign worker requires native Linux')
    receipt, baseline = inputs(args.cad)
    variant = next(v for v in receipt['variants'] if v['id'] == args.worker)
    if not variant['cad_accepted']:
        raise ValueError('CAD-rejected variant cannot enter solver')
    args.output.mkdir(parents=True, exist_ok=False)
    p, e, s, w, info = mesh(args.cad.parent/variant['step'], args.mesh, receipt['values'], variant, args.output)
    loads = forces(baseline, variant['component'])
    for name, direction in DIRECTIONS:
        g8.solve(args.output, p, e, s, w, loads, direction, name)
    # Unique G11 attempt names cannot collide with any historical G8 key.
    if any((args.output.name, n) in g9.HISTORICAL for n, _ in DIRECTIONS):
        raise ValueError('G11 case aliases historical evidence')
    rows = g9.audit(args.output, tuple(n for n, _ in DIRECTIONS), args.output, args.backend)
    result = {'id': variant['id'], 'component': variant['component'], 'mesh': info,
              'backend': args.backend,
              'cad_receipt_sha256': g8.sha256(args.cad), 'step_sha256': variant['step_sha256'],
              'source_sha256': source_hashes(), 'volume_mm3': variant['volume_mm3'],
              'journal_forces_N': loads, 'cases': rows,
              'artifact_bytes': sum(f.stat().st_size for f in args.output.iterdir() if f.is_file()),
              'worker_peak_RSS_MiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
              'maximum_child_RSS_MiB_not_sum': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024,
              'complete': len(rows) == 2, 'manufacturing_authorized': False,
              'engine_start_authorized': False, 'assembled_stiffness_qualified': False,
              'hashes': {f.name: g8.sha256(f) for f in sorted(args.output.iterdir()) if f.is_file()}}
    publish(args.output/'result.json', result)


def qualified_rows(result):
    rows = result['cases']
    return (result.get('complete') is True and len(rows) == 2
            and {r['direction'] for r in rows} == {'x', 'minus_z'}
            and all(r['numerical_crosscheck_passed'] and r['mechanics']['equilibrium_passed'] for r in rows))


def motion(result):
    values = [math.hypot(*r['mechanics']['journal_weighted_displacement_mm'][side]) for r in result['cases'] for side in SIDES]
    if not values or not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError('invalid journal motion')
    return max(values)


def assessment(medium, fine):
    changes = []
    if not qualified_rows(medium) or not qualified_rows(fine):
        return {'accepted': False, 'reason': 'numerical_crosscheck_failed'}
    for a, b in zip(sorted(medium['cases'], key=lambda r: r['direction']), sorted(fine['cases'], key=lambda r: r['direction'])):
        ma, mb = a['mechanics'], b['mechanics']
        uchange = max(math.dist(ma['journal_weighted_displacement_mm'][s], mb['journal_weighted_displacement_mm'][s]) /
                      math.hypot(*mb['journal_weighted_displacement_mm'][s]) for s in SIDES)
        stress = mb['von_Mises_p95_MPa']
        schange = abs(ma['von_Mises_p95_MPa']-stress)/stress if stress > 0 else math.inf
        if not all(math.isfinite(v) for v in (uchange, schange)):
            raise ValueError('invalid convergence observable')
        changes.append({'direction': b['direction'], 'journal_vector_relative_change': uchange, 'stress_p95_relative_change': schange})
    stable = all(r['journal_vector_relative_change'] <= .01 and r['stress_p95_relative_change'] <= .05 for r in changes)
    return {'accepted': stable and motion(fine) <= .04, 'selected_observables_stabilized': stable,
            'working_motion_screen_passed': motion(fine) <= .04, 'design_margin_target_passed': motion(fine) <= .035,
            'maximum_journal_motion_mm': motion(fine), 'comparisons': changes}


def verify_result(path, expected, cad_hash, variant, size, backend):
    if g8.sha256(path) != expected:
        raise ValueError('checkpoint result fingerprint mismatch')
    result = json.loads(path.read_text())
    if result['cad_receipt_sha256'] != cad_hash or result['source_sha256'] != source_hashes():
        raise ValueError('checkpoint inputs changed')
    if (result['id'] != variant['id'] or result['component'] != variant['component']
            or result['step_sha256'] != variant['step_sha256'] or result['mesh']['size_mm'] != size
            or result['backend'] != backend or any(r['solver']['backend'] != backend for r in result['cases'])):
        raise ValueError('checkpoint variant, mesh, STEP, or backend binding changed')
    for name, digest in result['hashes'].items():
        if Path(name).name != name or g8.sha256(path.parent/name) != digest:
            raise ValueError('checkpoint artifact changed')
    return result


def run(args):
    receipt, _ = inputs(args.cad)
    args.output.mkdir(parents=True, exist_ok=True)
    identity = {'cad_receipt_sha256': g8.sha256(args.cad), 'source_sha256': source_hashes(), 'backend': args.backend}
    identity_path = args.output/'identity.json'
    if identity_path.exists():
        if json.loads(identity_path.read_text()) != identity:
            raise ValueError('resume identity differs')
    else:
        if any(args.output.iterdir()):
            raise ValueError('new campaign output must be empty')
        publish(identity_path, identity)
    checkpoints = sorted(args.output.glob('checkpoint-*.json'))
    records = json.loads(checkpoints[-1].read_text())['records'] if checkpoints else []
    variants = {v['id']: v for v in receipt['variants']}
    results = {}
    for record in records:
        if record['status'] == 'completed':
            path = (args.output/record['path']).resolve()
            if not path.is_relative_to(args.output.resolve()):
                raise ValueError('checkpoint path outside campaign')
            results[record['id'], record['size_mm']] = verify_result(path, record['sha256'], identity['cad_receipt_sha256'],
                variants[record['id']], record['size_mm'], args.backend)

    def execute(ident, size):
        if any(r['id'] == ident and r['size_mm'] == size for r in records):
            return True
        if time.time()+args.case_timeout+args.reserve_seconds > args.deadline:
            return False
        base = f'{ident}-{size:g}-attempt'
        number = 1
        while (args.output/f'{base}{number}').exists() or (args.output/f'{base}{number}.log').exists():
            number += 1
        case = args.output/f'{base}{number}'
        command = [sys.executable, str(Path(__file__).resolve()), '--cad', str(args.cad.resolve()),
                   '--output', str(case.resolve()), '--backend', args.backend, '--worker', ident, '--mesh', str(size)]
        start = time.monotonic()
        with (args.output/f'{case.name}.log').open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                returncode = process.wait(timeout=args.case_timeout)
                status = 'completed' if returncode == 0 and (case/'result.json').exists() else 'failed'
            except subprocess.TimeoutExpired:
                status, returncode = 'timeout', None
            finally:
                # Includes SIGTERM/KeyboardInterrupt: detached workers must not outlive their controller.
                # Also reap descendants if the worker itself failed or was killed by OOM.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        record = {'id': ident, 'size_mm': size, 'status': status, 'returncode': returncode, 'wall_seconds': time.monotonic()-start}
        if status == 'completed':
            path = case/'result.json'
            record.update(path=str(path.relative_to(args.output)), sha256=g8.sha256(path))
            results[ident, size] = verify_result(path, record['sha256'], identity['cad_receipt_sha256'], variants[ident], size, args.backend)
        records.append(record)
        publish(args.output/f'checkpoint-{len(records):04d}.json', {'records': records})
        print(json.dumps(record), flush=True)
        return True

    screening_attempted = True
    order = ['centre_w10', 'centre_w12', 'centre_w11'] + [i for i in variants if i.startswith('outer_')]
    for ident in order:
        variant = variants[ident]
        if variant['cad_accepted'] and not execute(ident, 2.):
            screening_attempted = False
            break
    selected = {}
    if screening_attempted:
        for component in ('carrier_base_p', 'central_diaphragm'):
            candidates = [r for (ident, size), r in results.items() if size == 2. and r['component'] == component and qualified_rows(r)]
            selected[component] = [r['id'] for r in sorted(candidates, key=lambda r: (motion(r), r['volume_mm3'], r['id']))[:2]]
        # Finish all 1.5 mm comparisons before spending remaining budget on 1 mm.
        for size in (1.5, 1.):
            for identifiers in selected.values():
                for ident in identifiers:
                    previous = results.get((ident, 2. if size == 1.5 else 1.5))
                    if previous and qualified_rows(previous):
                        execute(ident, size)
    assessments, winners = {}, {}
    for component, identifiers in selected.items():
        for ident in identifiers:
            if (ident, 1.5) in results and (ident, 1.) in results:
                assessments[ident] = assessment(results[ident, 1.5], results[ident, 1.])
        accepted = [i for i in identifiers if assessments.get(i, {}).get('accepted')]
        winners[component] = min(accepted, key=lambda i: (variants[i]['volume_mm3'], i)) if accepted else None
    eligible = [i for i, v in variants.items() if v['cad_accepted']]
    screening_complete = bool(eligible) and all((i, 2.) in results and qualified_rows(results[i, 2.]) for i in eligible)
    refinement_complete = (len(selected) == 2 and all(len(ids) == 2 for ids in selected.values())
                           and all((i, s) in results and qualified_rows(results[i, s])
                                   for ids in selected.values() for i in ids for s in (1.5, 1.)))
    report = {'classification': 'G11_fixed_foot_generic_cold_component_screen', **identity,
              'manufacturing_authorized': False, 'engine_start_authorized': False,
              'assembled_stiffness_qualified': False, 'hot_material_qualified': False,
              'generic_material': {'E_MPa': g8.E, 'nu': g8.NU},
              'cad_rejected': [i for i, v in variants.items() if not v['cad_accepted']],
              'records': records, 'screening_attempted': screening_attempted,
              'screening_complete': screening_complete, 'refinement_candidates': selected,
              'assessments': assessments, 'selected_variants': winners,
              'both_components_below_0p040_mm_and_mesh_stable': len(winners) == 2 and all(winners.values()),
              'complete': screening_complete and refinement_complete,
              'assembly_next': {'status': 'not_run', 'missing_qualified_inputs': ['contact_pairs', 'bolt_preloads', 'hot_material_cards', 'head_support_conditions'],
                                'bonded_model_if_used': 'optimistic_hypothesis_only_not_assembly_validation'}}
    number = len(list(args.output.glob('summary-*.json'))) + 1
    publish(args.output/f'summary-{number:04d}.json', report)
    print(json.dumps({'summary': f'summary-{number:04d}.json', 'selected_variants': winners,
                      'complete': report['complete']}), flush=True)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad', type=Path, required=True, help='G11 CAD receipt.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('cpu', 'cuda'), default='cuda')
    parser.add_argument('--deadline', type=float, help='absolute UTC epoch; collection reserve remains unused')
    parser.add_argument('--case-timeout', type=int, default=900)
    parser.add_argument('--reserve-seconds', type=int, default=180)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    parser.add_argument('--mesh', type=float, choices=(2., 1.5, 1.), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.mesh is None:
            parser.error('worker requires mesh size')
        worker(args)
    else:
        if (args.deadline is None or not math.isfinite(args.deadline)
                or args.case_timeout < 1 or args.reserve_seconds < 1):
            parser.error('finite deadline and positive time limits required')
        signal.signal(signal.SIGTERM, lambda number, frame: sys.exit(128+number))
        raise SystemExit(run(args))
