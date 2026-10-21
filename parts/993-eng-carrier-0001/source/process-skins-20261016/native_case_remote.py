"""Native per-case controller; explicit runtimes, owned scopes, fresh outputs."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

import numpy as np
from native_case_contract import PROFILES, bind_repair, runtime_config, sha, write

SOURCE = Path(__file__).resolve().parent
STOP = False


def request_stop(*_):
    global STOP
    STOP = True


def main(job):
    job = Path(job).resolve()
    plan = json.loads((job/'plan.json').read_text())
    runtime = runtime_config(job/'runtime.json')
    source = plan['source_index']; profile = PROFILES[source]
    if profile != plan['profile']:
        raise ValueError('Profile differs from the frozen source-index contract')
    frozen = {str(job/'plan.json'): sha(job/'plan.json'), str(job/'runtime.json'): sha(job/'runtime.json')}
    for name, expected in plan['sources_sha256'].items():
        path = job/'source'/name
        if path.is_symlink() or sha(path) != expected:
            raise ValueError('Uploaded source snapshot mismatch')
        frozen[str(path)] = expected
    inputs = {role: job/'inputs'/row['name'] for role, row in plan['inputs'].items()}
    for role, path in inputs.items():
        if sha(path) != plan['inputs'][role]['sha256']:
            raise ValueError('Uploaded input mismatch')
        frozen[str(path)] = sha(path)
    output = job/'output'; output.mkdir()
    state = dict(schema='native-envelope-case-execution-v2', status='running',
                 source_index=source, profile=profile, steps=[],
                 inputs_sha256=frozen, runtime_sha256=sha(job/'runtime.json'))
    start = time.monotonic()
    owned_jobs = []

    def verify():
        if any(sha(path) != expected for path, expected in frozen.items()):
            raise ValueError('Controller source, configuration or input changed')

    def cancelled():
        return STOP or (job/'cancel.request').exists() or time.monotonic()-start > 3200

    def scope_stop(unit):
        if not re.fullmatch(r'carrier-[A-Za-z0-9-]+\.scope', unit):
            raise ValueError('Refusing an unexpected owned unit name')
        initial = subprocess.run(['systemctl','--user','is-active',unit],capture_output=True,text=True,timeout=5)
        if initial.returncode in (3,4) and initial.stdout.strip() in ('inactive','unknown','failed'):
            return dict(unit=unit,kill_returncode=None,stop_returncode=None,state_returncode=initial.returncode,
                state=initial.stdout.strip(),inactive=True,already_inactive=True)
        kill = subprocess.run(['systemctl', '--user', 'kill', unit], capture_output=True, timeout=5)
        stop = subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True, timeout=10)
        check = subprocess.run(['systemctl', '--user', 'is-active', unit], capture_output=True, text=True, timeout=5)
        inactive = check.returncode in (3, 4) and check.stdout.strip() in ('inactive', 'unknown', 'failed')
        record = dict(unit=unit, kill_returncode=kill.returncode, stop_returncode=stop.returncode,
            state_returncode=check.returncode, state=check.stdout.strip(), inactive=inactive)
        if not inactive:
            raise ValueError('Owned scope inactivity not proven: '+unit)
        return record

    def cleanup_jobs():
        units = set(row['unit'] for row in state['steps'] if 'unit' in row)
        for path in owned_jobs:
            descriptor = path/'execution-plan.json'
            if descriptor.exists():
                item = json.loads(descriptor.read_text())
                unit = item.get('unit')
                if unit:
                    units.add(unit if unit.endswith('.scope') else unit+'.scope')
        return [scope_stop(unit) for unit in sorted(units)]

    def checkpoint():
        write(output/'execution-receipt.json', state)

    def run(name, arguments, seconds, *, native_job=None, own_scope=False, allowed_codes=(0,)):
        verify()
        if cancelled():
            raise InterruptedError('Per-case cancellation/deadline reached')
        command = [str(x) for x in arguments]
        unit = None
        if own_scope:
            unit = 'carrier-case-'+uuid.uuid4().hex[:12]+'.scope'
            command = ['systemd-run', '--user', '--scope', '--quiet', '--unit', unit,
                '-p', 'CPUQuota=200%', '-p', 'MemoryMax=4G', '-p', 'MemorySwapMax=0',
                '-p', 'TasksMax=128', '-p', 'RuntimeMaxSec='+str(seconds+10),
                'timeout', '--kill-after=10s', str(seconds),
                'bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid',
                '--die-with-parent', '--proc', '/proc', '--dev', '/dev',
                '--bind', str(output), str(output), '--tmpfs', '/tmp',
                '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                '--setenv', 'OMP_NUM_THREADS', '1', '--setenv', 'OPENBLAS_NUM_THREADS', '1',
                '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', *command]
        row = dict(name=name, command=command, timeout_seconds=seconds, status='running')
        if unit:
            row['unit'] = unit
        state['steps'].append(row); checkpoint()
        if native_job:
            owned_jobs.append(native_job)
            state['owned_native_jobs'] = [str(path) for path in owned_jobs]
            checkpoint()
        began = time.monotonic(); child = None
        try:
            with (output/(name+'.log')).open('w') as log:
                child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
                while child.poll() is None:
                    if cancelled() or time.monotonic()-began > seconds+40:
                        if unit:
                            scope_stop(unit)
                        cleanup_jobs()
                        try:
                            child.wait(timeout=25)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGTERM)
                            child.wait(timeout=5)
                        raise InterruptedError('Owned child stopped after cancellation/deadline')
                    time.sleep(.25)
                row.update(returncode=child.returncode, status='executed' if child.returncode == 0 else 'retained_refusal')
                if child.returncode not in allowed_codes:
                    raise ValueError(name+' rejected; see retained log/receipts')
        finally:
            if unit:
                row['scope_cleanup'] = scope_stop(unit)
                row['owned_scope_inactive'] = row['scope_cleanup']['inactive']
            row['seconds'] = time.monotonic()-began; checkpoint()
        verify()

    token = job.name
    py = runtime['python']; audit_py = runtime['audit_python']
    def native_path(key, suffix):
        return Path(runtime[key])/'jobs'/(token+'-'+suffix)
    csg = native_path('prism_csg' if source in (0, 2) else 'pymesh_orders', 'csg')
    first = native_path('snap', 'first-snap')
    final = first
    distance = native_path('distance', 'distance')
    try:
        if source in (0, 2):
            with np.load(inputs['roofs'], allow_pickle=False) as roofs:
                maximum = np.max(np.abs(roofs['vertices']), axis=0)
            steps = [math.ldexp(1., math.frexp(float(x))[1]+1-51) if x else 0. for x in maximum]
            limit = 5*math.sqrt(sum(x*x for x in steps))/2
            if source == 2:
                expected = json.loads((SOURCE/'left-repair-template-v2.json').read_text())['plan']['frozen_shape_drift_limit_mm']
                if limit != expected:
                    raise ValueError('Left input-derived snap bound differs from the frozen original bound')
            freeze = dict(schema='cold-prism-pre-csg-plan-v2', source_index=source,
                inputs_sha256={role:dict(path=str(path),sha256=sha(path)) for role,path in inputs.items()},
                downstream_frozen=dict(original_shape_drift_limit_mm=limit,
                    no_old_central_snap_receipt=True, snap_grid_bits=51, snap_iteration_budget=5,
                    input_roof_maximum_absolute_axes_mm=maximum.tolist(), input_domain_snap_step_mm=steps),
                scope='Frozen before CSG. Finite all-vertex/exact-centroid composed admission; no continuous Hausdorff claim.')
            write(output/'frozen-plan.json', freeze)
            run('csg', [py, Path(runtime['prism_csg'])/'run.py', 'prism_free', inputs['roofs'], csg,
                '--second-input', inputs['mask'], '--part-input', inputs['part'],
                '--timeout-seconds', profile['csg_seconds']], profile['csg_seconds'], native_job=csg)
        else:
            run('csg', [py, Path(runtime['pymesh_orders'])/'run.py', inputs['chain'], inputs['mask'], inputs['part'], csg,
                '--timeout-seconds', profile['csg_seconds'], '--order', profile['order']],
                profile['csg_seconds'], native_job=csg)
        run('first-snap', [py, Path(runtime['snap'])/'run.py', csg/'result.npz', first,
            '--grid-bits', 51, '--iterations', 5, '--cumulative-grid-bound'], 600,
            native_job=first, allowed_codes=(0, 1))
        # Code 1 can be a retained legacy IGL-only refusal. Native and topology
        # gates are rechecked by exact measurement; no arbitrary failure bypass.
        if source == 2:
            bind_repair(SOURCE/'left-repair-template-v2.json', first/'result.npz', csg/'result.npz', output/'repair-plan.json')
            candidate = output/'repair'
            run('explicit-repair', [audit_py, SOURCE/'repair_ancestral_line_sheet.py', first/'result.npz',
                csg/'result.npz', output/'repair-plan.json', candidate], 60, own_scope=True)
            attestation = dict(status='executed', command_record=state['steps'][-1],
                source_sha256=sha(candidate/'repair_ancestral_line_sheet.py'),
                plan_sha256=sha(output/'repair-plan.json'), assessment_sha256=sha(candidate/'assessment.json'),
                result_sha256=sha(candidate/'result.npz'), recorded_after_child_completion=True,
                scope='New cold execution recorded by controller; no inherited historical outer execution claim.')
            write(candidate/'execution-completion-attestation.json', attestation)
            final = native_path('snap', 'repaired-snap')
            run('repaired-snap', [py, Path(runtime['snap'])/'run.py', candidate/'result.npz', final,
                '--grid-bits', 51, '--iterations', 5, '--cumulative-grid-bound'], 600,
                native_job=final, allowed_codes=(0, 1))
            distance = output/'direct-distance'
            measure = SOURCE.parent/'native-cgal-mesh-remeasure-20261016'
            run('direct-distance', [py, measure/'run.py', csg/'result.npz', candidate/'result.npz', final,
                output/'repair-plan.json', distance, '--distance-runtime', runtime['distance']], 600, native_job=distance)
            run('composed', [audit_py, measure/'audit_composed_repair.py', csg, final, distance, first,
                output/'repair-plan.json', output/'composed', '--conversion-module',
                SOURCE.parent/'native-cgal-prism-free-20261016-v4/audit_composed_drift_initial.py'], 120, own_scope=True)
        else:
            run('exact-distance', [py, Path(runtime['distance'])/'run.py', csg/'result.npz', final, distance],
                600, native_job=distance)
            if source == 0:
                run('composed', [audit_py, SOURCE.parent/'native-cgal-prism-free-20261016-v4/audit_composed_drift_initial.py',
                    csg, final, distance, first, output/'composed', '--plan', output/'frozen-plan.json'],
                    120, own_scope=True)
        run('independent', [audit_py, SOURCE/'audit_envelope_case.py', final/'result.npz', output/'independent',
            '--audit-python', audit_py], 120, own_scope=True)
        if source in (0, 2):
            command = [audit_py, SOURCE/'seal_prism_native_case.py', '--original-native-job', csg,
                '--final-snap-job', final, '--distance-job', distance,
                '--composed', output/'composed/composed-drift.json',
                '--contacts', output/'independent/exact-contacts.json',
                '--pairs', output/'independent/topology/pairs.npz',
                '--frozen-plan', output/('repair-plan.json' if source == 2 else 'frozen-plan.json'),
                '--schema', SOURCE.parent/'native-cgal-prism-free-20261016-v4/prism-face-schema.json',
                '--output', output/'sealed', '--source-index', source]
            if source == 2:
                command += ['--repair-candidate-dir', candidate, '--first-snap-job', first]
            run('seal-prism', command, 120, own_scope=True)
            terminal = dict(native_audit=dict(path='sealed/native_audit.json',sha256=sha(output/'sealed/native_audit.json')))
        else:
            bundle = output/'legacy'; bundle.mkdir()
            for name, path in [('csg', csg), ('snap', final), ('distance', distance), ('independent', output/'independent')]:
                shutil.copytree(path, bundle/name)
            terminal = dict(legacy_case_directory=dict(path='legacy'))
        verify()
    except BaseException as error:
        state.update(status='rejected_or_incomplete', error_type=type(error).__name__, error=str(error),
            identities_unchanged=all(sha(path)==expected for path,expected in frozen.items()),
            seconds=time.monotonic()-start)
        checkpoint()
        raise
    finally:
        try:
            state['terminal_scope_cleanup'] = cleanup_jobs()
            state['all_owned_scopes_inactive'] = all(row['inactive'] for row in state['terminal_scope_cleanup'])
        except BaseException as error:
            state.update(status='failed_cleanup', cleanup_error=str(error))
            checkpoint()
            raise
        checkpoint()
    verify()
    state.update(status='executed', identities_unchanged=True, seconds=time.monotonic()-start)
    checkpoint()
    report = dict(schema='native-envelope-case-v2', source_index=source, status='executed',
        backend=profile['backend'], profile=profile, input_manifest_sha256=plan['input_manifest_sha256'],
        runtime_sha256=sha(job/'runtime.json'), source_snapshot_sha256=plan['sources_sha256'],
        all_owned_scopes_inactive=state['all_owned_scopes_inactive'], **terminal)
    report['files_sha256'] = {str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write(output/'case.json', report)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('job', type=Path)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, request_stop)
    raise SystemExit(main(parser.parse_args().job))
