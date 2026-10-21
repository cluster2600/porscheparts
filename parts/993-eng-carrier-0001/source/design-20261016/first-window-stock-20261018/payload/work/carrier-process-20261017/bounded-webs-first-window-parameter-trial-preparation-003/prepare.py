"""Freeze one non-armed candidate trial using only stdlib and existing input bytes."""
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
W = R / 'work/carrier-process-20261017'
S = R / 'parts/993-eng-carrier-0001/source'
began = time.monotonic()

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            digest.update(block)
    return digest.hexdigest()

def read(path):
    return json.loads(path.read_text())

def name(path):
    return str(path.relative_to(R)) if path.is_relative_to(R) else str(path)

def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())

def main():
    old = W / 'bounded-webs-C1-functional-law-addition-preparation-001'
    reference = read(old / 'pending-plan.json')
    old_launch = read(old / 'pending-launch-plan.json')
    p = {key: copy.deepcopy(reference[key]) for key in ('native_site', 'baseline_STEP', 'volume_source', 'strict_cut_source', 'minimum_xyz_mm', 'maximum_xyz_mm', 'existing_bound_guard_mm')}
    p.update(schema='single-first-window-parameter-trial-plan-1', launch_ready=False, root_GO=None, root_GO_sha256=None,
        trial=dict(main_scale=.9, first_window_index=0, inset_mm=2.8, unchanged_inset_mm=1.5, unchanged_outer_window_scale=.4, both_X_mirrors=True),
        bounds=dict(outer=600, inner=560, CPU=[520, 540], threads=1, workers=0),
        source_settings=name(S / 'design-20261016/bounded-webs.json'), baseline_study='work/part-workflow/run-001/cad/study.json',
        current_BREP=name(W / 'bounded-webs-C1-full-contour-native-observer-preparation-001/patched-output-001/candidate-native.brep'),
        current_native_ROOT=name(W / 'bounded-webs-C1-full-contour-native-observer-preparation-001/root-terminal-review-001.json'),
        current_addition_ROOT=name(old / 'root-terminal-review-001.json'),
        current_FEA_ROOT=name(W / 'bounded-webs-C1-functional-law-static-preparation-001/root-solver-terminal-review-001.json'),
        current_geometry_ROOT=name(W / 'bounded-webs-C1-functional-law-peak-native-preparation-002/root-terminal-review-001.json'),
        current_geometry_terminal=name(W / 'bounded-webs-C1-functional-law-peak-native-preparation-002/terminal-collection.json'),
        output_directory=name(H / 'output-001'), execution_directory=name(H / 'execution-001'), candidate_qualified=False,
        old_complete7_functional_law_proof_transferred=False, downstream_checks={key: 'PENDING' for key in ('protected_interfaces', 'surface_topology_and_distance', 'STEP_exchange', 'FEA')})
    pins = {path: digest for path, digest in reference['files_sha256'].items() if '/runtimes/' in path}
    contract_path = S / 'bionic-20261011/correction-20261013/interface-study.json'
    contract = read(contract_path)
    pins.update(contract['sources_sha256'])
    sources = [H / file for file in ('trial.py', 'selfcheck.py', 'prepare.py', 'build_stock.py', 'normal-builder/cad.py', 'source-changes.json', 'normal-builder-cad.py.diff', H.name+'-build_stock.py.diff', 'README.md', 'ARMING.md', 'from-001.json', 'trial-from-001.diff', 'from-002.json', 'trial-from-002.diff', 'boolean-reference-source-note.json')]
    # The generated bounded-builder diff is named from its source directory.
    sources = [q for q in sources if q.exists()]
    sources.extend(H.glob('*-build_stock.py.diff'))
    paths = sources + [R / p[key] for key in ('source_settings', 'baseline_study', 'baseline_STEP', 'current_BREP', 'current_native_ROOT', 'current_addition_ROOT', 'current_FEA_ROOT', 'current_geometry_ROOT', 'current_geometry_terminal', 'volume_source', 'strict_cut_source')]
    paths += [contract_path, S / 'design-20261016/bounded-webs-plan.json', S / 'design-20261016/build_bounded_webs.py', S / 'design-20261016/normal-builder/cad.py', S / 'bionic-20261011/cad.py', W / 'bounded-webs-C1-endfillet-preparation-002/close_end.py', W / 'source010-exposure-preflight-003/supervise.py']
    for path in paths:
        pins[name(path)] = sha(path)
    assert all(sha(R / path) == digest for path, digest in pins.items())
    p['files_sha256'] = pins
    write(H / 'pending-plan.json', p)
    spec = importlib.util.spec_from_file_location('_first_window_preflight_only', H / 'trial.py')
    trial = importlib.util.module_from_spec(spec); spec.loader.exec_module(trial)
    trial.verify(H / 'pending-plan.json', sha(H / 'pending-plan.json'))
    result = subprocess.run([sys.executable, '-I', '-B', str(H / 'selfcheck.py')], capture_output=True, text=True, timeout=30)
    for suffix, text in (('stdout', result.stdout), ('stderr', result.stderr)):
        with (H / f'selfcheck.{suffix}.log').open('x') as stream: stream.write(text)
    assert result.returncode == 0, result.stderr
    assert not any(module.split('.')[0] in ('OCP', 'build123d', 'numpy', 'gmsh') for module in sys.modules)
    write(H / 'preflight.json', dict(status='SOURCE_ONLY_complete_pins_settings_authorities_and25_stdlib_tests_PASS', plan_sha256=sha(H / 'pending-plan.json'), plan_pins=len(pins), actual_tests_returncode=0, scientific_imports=False, native_executed=False, elapsed_seconds=time.monotonic()-began))
    supervisor = W / 'source010-exposure-preflight-003/supervise.py'
    launch = {key: copy.deepcopy(value) for key, value in old_launch.items() if key not in ('inputs_sha256', 'source_sha256')}
    launch.update(schema='owned_single_first_window_trial_pending_1', launch_ready=False, root_GO=None, root_GO_sha256=None,
        command=[old_launch['command'][0], '-I', '-B', str(H / 'trial.py'), 'run', str(H / 'pending-plan.json'), sha(H / 'pending-plan.json')],
        output_directory=p['output_directory'], execution_directory=p['execution_directory'],
        source_sha256={name(path): sha(path) for path in (supervisor, H / 'trial.py', H / 'build_stock.py', H / 'normal-builder/cad.py')}, inputs_sha256=dict(pins))
    for path in (H / 'pending-plan.json', H / 'preflight.json'):
        launch['inputs_sha256'][name(path)] = sha(path)
    assert launch['total_wall_budget_seconds'] == 600 and launch['cleanup_grace_seconds'] == [10, 10]
    write(H / 'pending-launch-plan.json', launch)
    command = dict(schema='pending_first_window_trial_command_1', launch_ready=False, root_GO=None, root_GO_sha256=None,
        argv=[old_launch['command'][0], '-I', '-B', str(supervisor), str(H / 'pending-launch-plan.json'), '--plan-sha256', sha(H / 'pending-launch-plan.json')], cwd=str(R), native_executed=False, parent_not_niced=True)
    write(H / 'pending-command.json', command)
    assessment = dict(status='SOURCE_ONLY_one_fixed_first_window_trial_pending_ROOT_review', source_sha256={name(path): sha(path) for path in sources}, plan_sha256=sha(H / 'pending-plan.json'), launch_sha256=sha(H / 'pending-launch-plan.json'), command_sha256=sha(H / 'pending-command.json'), preflight_sha256=sha(H / 'preflight.json'), plan_pins=len(pins), merged_launch_pins=len({**launch['inputs_sha256'], **launch['source_sha256']}), tests=25, actual_tests_returncode=0, native_executed=False)
    write(H / 'preparation-assessment.json', assessment)
    print(json.dumps(assessment))

if __name__ == '__main__':
    main()
