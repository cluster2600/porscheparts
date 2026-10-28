"""Two separate bounded linear CCX cases on the actually qualified h2 mesh."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE = 'sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
BINARY = '271f8411371b978d7a8d31a7a13d0765e6e1f872e8a8b1d6aac6d0856c71ec6c'
CASES = {'rigid': ('combined-rigid-static', None), 'spring': ('combined-spring-1000-static', 1000)}


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def copy_exact(source, target, expected):
    with Path(source).open('rb') as src, Path(target).open('xb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    require(sha(target) == expected, 'Copied case input differs')


class DeckPrepared(Exception):
    pass


def prepare_execute(case, execution, name, digest_record):
    """Preserve the deck made by unchanged solve(), then stop before Docker."""
    def execute(folder, actual_name, *args, **kwargs):
        require(Path(folder) == case and actual_name == name, 'Unexpected preparation callback')
        source = case / (name + '.inp'); target = execution / 'prepared-deck.inp'
        require(not target.exists() and not target.is_symlink(), 'Prepared deck already exists')
        digest_record['deck_sha256'] = sha(source)
        source.rename(target)
        require(sha(target) == digest_record['deck_sha256'], 'Prepared deck rename differs')
        raise DeckPrepared('Generated native deck retained; no solver called')
    return execute


def make_execute(helper, backend, plan, case, execution, started):
    """The sole production solve callback: frozen owned Docker supervision."""
    used = False
    def execute(folder, name, *args, **kwargs):
        nonlocal used
        require(not used and Path(folder) == case and name == plan['case_name'], 'Unexpected/repeated execute callback')
        used = True; callback_start = time.monotonic()
        require(sha(case / (name + '.inp')) == plan['prepared_deck_sha256'], 'Native deck differs from prepared original solve deck')
        require(sha(execution / 'prepared-deck.inp') == plan['prepared_deck_sha256'], 'Frozen prepared deck changed')
        owned = dict(case_directory=str(case.resolve()), case_name=name,
                     container_name=plan['container_name'], ownership_token=plan['ownership_token'],
                     image=IMAGE, binary_sha256=BINARY, wall_budget_seconds=1800, cleanup_reserve_seconds=60,
                     solver_timeout_seconds=1680,
                     container_command=['--signal=TERM', '--kill-after=10s', '1680s', '/usr/bin/ccx', '-i', name],
                     initial_case_files=['mesh.inp', 'mesh.npz', 'mesh.json', name + '.inp'],
                     files_sha256={str(ROOT / p): h for p, h in plan['files_sha256'].items()})
        owned['files_sha256'][str(case / (name + '.inp'))] = plan['prepared_deck_sha256']
        for filename in ['mesh.inp', 'mesh.npz', 'mesh.json']:
            owned['files_sha256'][str(case / filename)] = plan['mesh_files_sha256'][filename]
        write(execution / 'native-plan.json', owned)
        helper.HERE = execution  # Private module instance; frozen capsule directory is never written.
        result = helper.supervise(owned, backend, started=started)
        result.update(native_plan_sha256=sha(execution / 'native-plan.json'), helper_source_sha256=plan['helper_sha256'])
        write(execution / 'native-receipt.json', result)
        require(result['status'] == 'solver_executed_no_numeric_admission'
                and result['actual_container_exit_code'] == 0 and result['container_removed']
                and result['input_hashes_unchanged'] and result['within_global_budget'], 'Owned CCX execution/cleanup failed')
        require(not backend.cancelled, 'Cancellation requested after owned cleanup')
        write(case / 'runtime.json', dict(status='executed', image=IMAGE, ccx_binary_sha256=BINARY,
              container_name=plan['container_name'], actual_container_id=result['container_id'],
              native_returncode=result['actual_container_exit_code'], owned_container_removed=True,
              CPUs=1, memory_bytes=6*1024**3, memory_swap_bytes=6*1024**3, network='none',
              native_plan_sha256=sha(execution / 'native-plan.json'), native_receipt_sha256=sha(execution / 'native-receipt.json')))
        left = started + 1800 - time.monotonic()
        require(left > 0, 'No postprocess time remains in per-case budget')
        # No local alarm can interrupt the frozen helper's reserved container cleanup.
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Per-case postprocess deadline')))
        signal.setitimer(signal.ITIMER_REAL, left)
        return time.monotonic() - callback_start
    return execute


def verify_mesh(plan):
    terminal = json.loads((ROOT / plan['mesh_terminal']).read_text())
    assessment = json.loads((ROOT / plan['mesh_assessment']).read_text())
    supervision = json.loads((ROOT / plan['mesh_supervision']).read_text())
    require(terminal['actual_tool_returncode'] == 0 and terminal['pins_unchanged'] is True
            and terminal['assessment_sha256'] == sha(ROOT / plan['mesh_assessment'])
            and terminal['supervision_sha256'] == sha(ROOT / plan['mesh_supervision']), 'Actual h2 mesh terminal differs')
    require(supervision['actual_returncode'] == 0 and supervision['direct_child_reaped']
            and supervision['no_non_zombie_group_members'] and supervision['sources_and_plan_unchanged'], 'Actual mesh execution not closed')
    require(assessment['status'] == 'local_adaptive_discrete_h2_mesh_checked_no_FEA' and assessment['h2_qualified']
            and assessment['volume_error_non_regression'] and assessment['protected_facets_unchanged_at_every_pass']
            and assessment['original_NPZ_XYZ_block_preserved'] and assessment['original_INP_NODE_lexemes_preserved']
            and assessment['all_original_nodes_IDs_XYZ_unchanged_and_used'] and assessment['pins_unchanged']
            and assessment['plan_unchanged'] and all(r['target_attained'] for r in assessment['measurements']), 'Actual adaptive mesh gates are not all passed')


def verified(plan, expected_hash, plan_path):
    require(sha(plan_path) == expected_hash and plan['launch_ready'] is True, 'Plan not armed or changed')
    require(plan['case_key'] in CASES and (plan['case_name'], plan['support_N_mm']) == CASES[plan['case_key']], 'Wrong fixed case')
    require(plan['wall_budget_seconds'] == 1800 and plan['cleanup_reserve_seconds'] == 60
            and plan['image'] == IMAGE and plan['binary_sha256'] == BINARY, 'Fixed solver/resource identity differs')
    require(plan['mesh_source'] == 'work/carrier-process-20261017/bounded-webs-discrete-real-preparation-002/output-001/mesh', 'Wrong qualified mesh')
    require(os.getpriority(os.PRIO_PROCESS, 0) == 10 and all(os.environ.get(k) == '1' for k in
            ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')), 'nice10 and one local BLAS thread required')
    actual = {p: sha(ROOT / p) for p in plan['files_sha256']}; require(actual == plan['files_sha256'], 'An input/source/runtime differs')
    verify_mesh(plan)
    study = json.loads((ROOT / plan['CAD_inputs']['study.json']).read_text())
    require(study['material']['E_MPa'] == 107000 and study['material']['nu'] == .31
            and study['load_cases']['combined']['force_N'] == [0, 0, -4000]
            and study['load_cases']['combined']['moment_Nmm'] == [0, 850000, 0], 'Original fixed physics differs')
    return actual


def prepare(plan, plan_path, expected_hash):
    before = verified(plan, expected_hash, plan_path)
    output = ROOT / plan['case_output']; require(not output.exists() and not output.is_symlink(), 'Fresh case copy required')
    require(all(not p.is_symlink() for p in output.parents), 'Symlink case ancestor')
    output.mkdir(); cad = output / 'cad'; cad.mkdir(); case = cad / 'mesh-h2'; case.mkdir(); execution = output / 'execution'; execution.mkdir()
    for name, p in plan['CAD_inputs'].items(): copy_exact(ROOT / p, cad / name, before[p])
    for name, digest in plan['mesh_files_sha256'].items(): copy_exact(ROOT / plan['mesh_source'] / name, case / name, digest)
    sys.path.insert(0, str(ROOT / plan['numpy_site']))
    sim = load('private_static_prepare_' + plan['case_key'], ROOT / plan['simulation_source'])
    sim.CONTAINER = plan['container_name']; record = {}
    sim.execute = prepare_execute(case, execution, plan['case_name'], record)
    try: sim.solve(case, 'combined', support=plan['support_N_mm'], procedure='static')
    except DeckPrepared: pass
    else: raise ValueError('Deck preparation failed to stop before execution')
    require(record.get('deck_sha256') and not (case / (plan['case_name'] + '.inp')).exists(), 'Prepared deck not retained exclusively')
    armed = dict(plan, prepared_deck_sha256=record['deck_sha256'], preparation_plan_sha256=expected_hash)
    write(output / 'case-plan.json', armed)
    require(before == {p: sha(ROOT / p) for p in before}, 'Preparation changed frozen inputs')
    write(output / 'preparation.json', dict(status='actual_original_solve_deck_prepared_no_FEA', case_name=plan['case_name'],
          case_plan_sha256=sha(output / 'case-plan.json'), prepared_deck_sha256=record['deck_sha256'],
          sources_unchanged=True, FEA_started=False))
    print(json.dumps(dict(status='prepared_no_FEA', case=plan['case_key'], plan_sha256=sha(output / 'case-plan.json'), deck_sha256=record['deck_sha256'])), flush=True)


def run(plan, plan_path, expected_hash):
    started = time.monotonic(); before = verified(plan, expected_hash, plan_path)
    output = ROOT / plan['case_output']; case = output / 'cad/mesh-h2'; execution = output / 'execution'
    require(not (output / 'assessment.json').exists() and not (execution / 'ccx.prestart').exists(), 'Preserve previous native case')
    require(set(p.name for p in case.iterdir()) == {'mesh.inp', 'mesh.npz', 'mesh.json'}, 'Case copy is no longer fresh')
    require(sha(execution / 'prepared-deck.inp') == plan['prepared_deck_sha256'], 'Prepared original deck changed')
    sys.path.insert(0, str(ROOT / plan['numpy_site']))
    sim = load('private_static_solve_' + plan['case_key'], ROOT / plan['simulation_source'])
    energy = load('private_static_energy_' + plan['case_key'], ROOT / plan['energy_source'])
    peak = load('private_static_peak_' + plan['case_key'], ROOT / plan['peak_source'])
    helper = load('private_owned_CCX_' + plan['case_key'], ROOT / plan['helper_source']); backend = helper.DockerCLI()
    require(energy.ENERGY_RELATIVE_TOLERANCE == 1e-4, 'Energy criterion changed')
    old_handlers = {sig: signal.signal(sig, backend.cancel) for sig in (signal.SIGTERM, signal.SIGINT)}
    sim.CONTAINER = plan['container_name']; sim.execute = make_execute(helper, backend, plan, case, execution, started)
    report = dict(status='incomplete_no_numeric_admission', case_name=plan['case_name'], image=IMAGE,
                  physical_validation=False, strength_allowable_added=False, convergence_threshold_added=False)
    error = None
    try:
        native = sim.solve(case, 'combined', support=plan['support_N_mm'], procedure='static')
        require(not backend.cancelled, 'Cancellation requested')
        independent = energy.audit(case, plan['case_name']); write(output / 'energy-audit.json', independent)
        require(independent['energy_closure_pass'], 'Original independent energy criterion failed')
        peaks = peak.locate_case(case, plan['case_name'], energy, sim, sim.np); write(output / 'global-peaks.json', peaks)
        comparisons = []
        for baseline in plan['baselines']:
            retained = json.loads((ROOT / baseline['receipt']).read_text())
            retained_peaks = json.loads((ROOT / baseline['peaks']).read_text())
            require(retained['name'] == plan['case_name'] and retained_peaks['case'] == plan['case_name'], 'Wrong retained comparison case')
            comparisons.append(dict(mesh=baseline['mesh'], retained=retained, retained_global_peaks=retained_peaks,
                displacement_max_ratio=native['displacement_max_mm'] / retained['displacement_max_mm'],
                global_VM_max_ratio=native['integration_point_VM_max_MPa'] / retained['integration_point_VM_max_MPa'],
                load_dot_displacement_ratio=native['external_work_Nmm'] / retained['external_work_Nmm'],
                interpretation='Measured ratios only; no new convergence or strength criterion'))
        require(time.monotonic() - started < 1800, 'Per-case budget exceeded before numeric closeout')
        report.update(status='actual_linear_static_and_independent_energy_completed', native_result=native,
                      energy_audit_sha256=sha(output / 'energy-audit.json'), global_peaks_sha256=sha(output / 'global-peaks.json'),
                      comparisons_to_retained_mesh9_mesh7=comparisons, all_global_maxima_included=True)
    except BaseException as exc:
        error = exc; report['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in old_handlers.items(): signal.signal(sig, handler)
    after = {p: sha(ROOT / p) for p in before}
    report.update(plan_sha256=expected_hash, plan_unchanged=sha(plan_path) == expected_hash,
                  sources_before=before, sources_after=after, sources_unchanged=before == after,
                  wall_seconds=time.monotonic()-started, per_case_budget_seconds=1800,
                  scope='One new linear case on qualified local h2 mesh; assumed loads/material and discrete supports unchanged. No physical or manufacturing qualification.')
    report['within_case_budget'] = report['wall_seconds'] <= 1800
    if not report['within_case_budget']:
        report['status'] = 'case_budget_exceeded_no_numeric_admission'
        if error is None: error = TimeoutError('Per-case bookkeeping exceeded 1800s')
    write(output / 'assessment.json', report)
    require(before == after and report['plan_unchanged'], 'A frozen case input changed')
    if error is not None: raise error
    print(json.dumps(dict(status=report['status'], case=plan['case_key'], assessment_sha256=sha(output / 'assessment.json'))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=['prepare', 'run']); parser.add_argument('plan'); parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args(); path = Path(args.plan); plan = json.loads(path.read_text())
    (prepare if args.mode == 'prepare' else run)(plan, path, args.plan_sha256)
