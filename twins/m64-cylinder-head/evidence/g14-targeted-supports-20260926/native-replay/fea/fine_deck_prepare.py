"""Private uniform 1 mm deck preparation only; never run CCX, CG or a rental."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
WRITER = HERE/'caps_medium_candidate.py'
WRITER_SHA = '4ddbb328b3a7f46d8af7191ee2e7c8d2dfeb654c381bc93d04b37ca7ae00347e'
if hashlib.sha256(WRITER.read_bytes()).hexdigest() != WRITER_SHA:
    raise ValueError('frozen deck writer changed')
spec = importlib.util.spec_from_file_location('g14_fine_deck_writer', WRITER)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
c = m.c
MEDIUM = HERE/'candidate-centre-caps-1p5-hashfix-v1'
SUMMARY_SHA = 'ce43a396cbbe9b02ae731a9c374c121b628935da15d1587b016eb1ead6b9c00d'
CASE_SHA = 'b720929212869abe1386c9b31169a63a46c815347173508676757de56b0cda60'
TEST = HERE/'test_fine_deck_prepare.py'
SECONDS, OWN_RSS, COMBINED_RSS, FREE_DISK = 600, 12*1024**3, 28*1024**3, 12*1024**3
PEER_PGID = 46631


def inputs():
    if c.g8.sha256(WRITER) != WRITER_SHA or c.g8.sha256(MEDIUM/'summary.json') != SUMMARY_SHA:
        raise ValueError('frozen writer or medium summary changed')
    summary = json.loads((MEDIUM/'summary.json').read_text())
    path = c.g13.confined(MEDIUM, summary['result'])
    manifest = summary['artifacts_sha256']
    if manifest.get(summary['result']) != CASE_SHA or c.g8.sha256(path) != CASE_SHA:
        raise ValueError('medium case fingerprint changed')
    for name, digest in manifest.items():
        if c.g8.sha256(c.g13.confined(MEDIUM, name)) != digest:
            raise ValueError('medium artifact changed: '+name)
    baseline, variant, coarse = m.pre.inputs()
    case = json.loads(path.read_text())
    if (summary['complete'] is not True or summary['returncode'] != 0 or summary['error'] is not None
            or summary['numerically_qualified'] is not True or case['proof'] != summary['proof']
            or case['id'] != c.IDENT or case['step_sha256'] != variant['step_sha256']
            or case['mesh']['size_mm'] != 1.5 or case['mesh']['nominal_journal_width_mm'] != 11
            or case['error'] is not None or case['numerically_qualified'] is not True
            or not c.g11.qualified_rows(case)):
        raise ValueError('completed qualified medium caps case required')
    for name, digest in case['hashes'].items():
        if manifest.get(str(path.parent.relative_to(MEDIUM)/name)) != digest:
            raise ValueError('medium case artifact binding changed')
    motion = c.g11.motion(case)
    if motion != case['maximum_journal_motion_mm'] or motion > .040:
        raise ValueError('medium journal motion exceeds 0.040 mm or differs from vectors')
    for row in case['cases']:
        agreement, mechanics = row['fresh_direct'], row['mechanics']
        if (row['solver']['info'] != 0 or not c.native.bounded(row['relative_residual'], 1e-8)
                or not c.native.bounded(agreement['max_nodal_difference_over_max_reference_U'], 1e-4)
                or not c.native.bounded(agreement['printed_dat_relative_residual'], agreement['printed_dat_rounding_residual_bound'])
                or not c.native.bounded(mechanics['force_balance_relative_error'], 1e-4)
                or not c.native.bounded(mechanics['moment_balance_F_times_100mm_error'], 1e-4)):
            raise ValueError('medium numerical thresholds failed')
    proof = dict(medium_summary_sha256=SUMMARY_SHA, medium_case_sha256=CASE_SHA,
        verified_medium_artifact_count=len(manifest), medium_maximum_journal_motion_mm=motion,
        coarse_summary_sha256=coarse['coarse_summary_sha256'], coarse_case_sha256=coarse['coarse_case_sha256'],
        cad_receipt_sha256=c.CAD_SHA, step_sha256=variant['step_sha256'], G7_receipt_sha256=c.g8.sha256(c.g8.BASELINE),
        writer_sha256=WRITER_SHA, numerical_sources_sha256=c.g11.source_hashes(),
        source_sha256=c.g8.sha256(Path(__file__)), test_sha256=c.g8.sha256(TEST))
    return baseline, variant, proof


def check_decks(output, mesh, support, weights, forces, face_height):
    rows, prefixes = [], []
    for name, direction in c.g11.DIRECTIONS:
        text = (output/(name+'.inp')).read_text()
        prefixes.append(hashlib.sha256(text.split('*STEP\n')[0].encode()).hexdigest())
        points, loads, fixed = c.g9.deck(text)
        axis = 1 if name == 'x' else 3
        sign = 1 if name == 'x' else -1
        bottom = {n for n, p in points.items() if abs(p[2]-face_height) < 1e-5}
        loaded = {n for n, _ in loads}
        if (len(points) != mesh['nodes'] or fixed != set(support) or len(fixed) != mesh['fixed_nodes']
                or fixed != bottom or loaded != set(weights['intake']) | set(weights['exhaust'])
                or any(d != axis or sign*f <= 0 for (_, d), f in loads.items())
                or text.count(f'*ELASTIC\n{c.g8.E},{c.g8.NU}\n') != 1):
            raise ValueError('deck node/support/material/load-direction mismatch')
        totals = {}
        for side, nodes in weights.items():
            totals[side] = math.fsum(sign*loads[n, axis] for n in nodes)
            if not math.isclose(totals[side], forces[side], rel_tol=1e-11, abs_tol=1e-8):
                raise ValueError('deck journal force differs from G7: '+side)
        rows.append(dict(direction=name, nodes=len(points), fixed_nodes=len(fixed), loaded_nodes=len(loaded),
            applied_force_vector_N=[math.fsum(f for (_, d), f in loads.items() if d == i) for i in (1, 2, 3)],
            journal_force_magnitudes_N=totals, expected_journal_forces_N=forces,
            full_bottom_land_fixed_XYZ=True, load_sign_and_axis_passed=True))
        del text, points, loads, fixed, bottom
    if len(set(prefixes)) != 1:
        raise ValueError('two decks do not share geometry and material prefix')
    return dict(shared_geometry_material_prefix_sha256=prefixes[0], cases=rows)


def worker(output):
    if sys.platform != 'darwin' or any(os.environ.get(k) != '1' for k in c.THREAD_ENV):
        raise ValueError('native Mac preparation with explicit numerical thread environment required')
    baseline, variant, proof = inputs()
    if json.loads((output/'identity.json').read_text()) != proof:
        raise ValueError('worker preparation identity changed')
    start = time.monotonic()
    report = dict(classification='G14_uniform_1mm_portable_decks_no_solve', complete=False, error=None,
        id=c.IDENT, proof=proof, step_sha256=variant['step_sha256'], mesh_is_new_not_preflight_reused=True,
        FEA_executed=False, CCX_executed=False, CG_executed=False, CUDA_executed=False,
        mesh_convergence_qualified=False, assembled_stiffness_qualified=False, hot_material_qualified=False,
        manufacturing_authorized=False, engine_start_authorized=False, remote_Linux_job_operational=False,
        boundary_hypothesis='Unchanged whole bottom land fixed XYZ, 11 mm journals, generic E=70000 MPa and nu=0.33; no contact, preload or hot assembly.',
        scope='Input preparation only. No direct factorization, iterative solve, residual or displacement result.')
    try:
        points, elements, support, weights, mesh = c.g11.mesh(variant['step_path'], 1., baseline['values'], variant, output)
        forces = c.g11.forces(baseline, variant['component'])
        report.update(mesh=mesh, kinematic_free_dofs=3*(len(points)-len(support)), journal_forces_N=forces,
            material=dict(E_MPa=c.g8.E, nu=c.g8.NU), mesher='unchanged g11.mesh with Gmsh General.NumThreads=4')
        for name, direction in c.g11.DIRECTIONS:
            m.write_deck(output, points, elements, support, weights, forces, direction, name)
        del points, elements
        report['deck_checks'] = check_decks(output, mesh, support, weights, forces, baseline['values']['carrier_face_height'])
        if inputs()[2] != proof:
            raise ValueError('source, input or medium proof changed during preparation')
        report['complete'] = True
    except BaseException as exc:
        report['error'] = type(exc).__name__+': '+str(exc)
    finally:
        report['wall_seconds'] = time.monotonic()-start
        report['files'] = {p.name:dict(bytes=p.stat().st_size, sha256=c.g8.sha256(p))
            for p in sorted(output.iterdir()) if p.is_file() and p.name != 'worker.log'}
        c.g11.publish(output/'receipt.json', report)
    return 0 if report['complete'] else 2


def control(output):
    proof = inputs()[2]
    if shutil.disk_usage(HERE).free < FREE_DISK:
        raise ValueError('minimum 12 GiB free disk required')
    output.mkdir(parents=True, exist_ok=False)
    for source in (Path(__file__), TEST):
        shutil.copyfile(source, output/source.name)
    c.g11.publish(output/'identity.json', proof)
    start = time.monotonic()
    peak = combined_peak = 0
    lowest = shutil.disk_usage(output).free
    reason = None
    with (output/'worker.log').open('x') as log:
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', '--output', str(output)],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=dict(os.environ, **c.THREAD_ENV))
        try:
            while process.poll() is None:
                rows = subprocess.check_output(['ps', '-axo', 'pid=,pgid=,rss='], text=True, timeout=5).splitlines()
                rss = sum(int(r.split()[2])*1024 for r in rows if int(r.split()[1]) == process.pid)
                combined = sum(int(r.split()[2])*1024 for r in rows if int(r.split()[1]) in (process.pid, PEER_PGID))
                free = shutil.disk_usage(output).free
                peak, combined_peak, lowest = max(peak, rss), max(combined_peak, combined), min(lowest, free)
                if rss > OWN_RSS or combined > COMBINED_RSS or free < FREE_DISK or time.monotonic()-start > SECONDS:
                    reason = ('12GiB_own_RSS_limit' if rss > OWN_RSS else '28GiB_combined_RSS_limit' if combined > COMBINED_RSS
                        else '12GiB_free_disk_limit' if free < FREE_DISK else '600s_deadline')
                    break
                time.sleep(1)
        except BaseException as exc:
            reason = type(exc).__name__+': '+str(exc)
        finally:
            if process.poll() is None:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
            process.wait()
    path = output/'receipt.json'
    result = json.loads(path.read_text()) if path.is_file() else {}
    passed = process.returncode == 0 and reason is None and result.get('complete') is True and result.get('error') is None
    summary = dict(classification='bounded_G14_uniform_1mm_deck_preparation_no_solve', complete=passed,
        returncode=process.returncode, error=reason or result.get('error'), proof=proof,
        worker_reaped=True, worker_pgid=process.pid, peer_pgid=PEER_PGID,
        limits=dict(seconds=SECONDS, own_RSS_bytes=OWN_RSS, combined_RSS_bytes=COMBINED_RSS, minimum_free_disk_bytes=FREE_DISK),
        observed_group_RSS_peak_bytes=peak, observed_combined_RSS_peak_bytes=combined_peak,
        lowest_observed_free_disk_bytes=lowest, wall_seconds=time.monotonic()-start,
        guard_scope='One-second process-group samples, not an OS-enforced memory limit; only owned group can be stopped.',
        receipt_sha256=c.g8.sha256(path) if path.is_file() else None,
        files={p.name:dict(bytes=p.stat().st_size, sha256=c.g8.sha256(p)) for p in sorted(output.iterdir()) if p.is_file()},
        FEA_executed=False, CCX_executed=False, CG_executed=False, CUDA_executed=False,
        mesh_convergence_qualified=False, manufacturing_authorized=False, engine_start_authorized=False,
        remote_Linux_job_operational=False)
    c.g11.publish(output/'summary.json', summary)
    print(json.dumps(dict(complete=passed, error=summary['error'], receipt_sha256=summary['receipt_sha256'])), flush=True)
    return 0 if passed else 2


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise InterruptedError('deck preparation interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to(HERE) or args.output == HERE:
        parser.error('new private output under fea required')
    if args.check:
        print(json.dumps(inputs()[2])); raise SystemExit(0)
    raise SystemExit(worker(args.output) if args.worker else control(args.output))
