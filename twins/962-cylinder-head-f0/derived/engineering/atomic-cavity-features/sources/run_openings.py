"""One local opening worker through the exact retained owned-process monitor."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import time

PREP = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def run(path, expected, output):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(path) != expected:
        raise ValueError('Exact reviewed child required before worker import')
    initial = json.loads(path.read_text()); root = PREP.parents[2]
    for source in (Path(__file__).resolve(), PREP/'audit_openings.py'):
        if initial['input_hashes'].get(str(source.relative_to(root))) != sha(source):
            raise ValueError('New controller/worker source changed before import')
    # Only the standard-library worker contract guards are imported here.
    w = load(PREP/'audit_openings.py', 'isolated_opening_contract_guards')
    c = w.load_contract(path, expected)
    if output.resolve() != w.OUTPUT.resolve() or output.exists() or output.is_symlink():
        raise ValueError('Fixed fresh opening-audit output required')
    monitor_path = w.SOURCE/'run_quality_distance_002.py'
    monitor = load(monitor_path, 'frozen_read_only_process_monitor')
    output.mkdir(); (output/'frozen-contract.json').write_bytes(path.read_bytes())
    (output/'controller-executed.py').write_bytes(Path(__file__).read_bytes())
    (output/'worker-executed.py').write_bytes((PREP/'audit_openings.py').read_bytes())
    snapshots = output/'source-snapshots'; snapshots.mkdir()
    for name in c['input_hashes']:
        if name.endswith('.py'):
            (snapshots/Path(name).name).write_bytes((w.ROOT/name).read_bytes())
    command = [c['interpreter'], '-B', str(PREP/'audit_openings.py'), '--contract', str(path),
               '--contract-sha256', expected, '--output', str(output)]
    env = dict(PATH='/usr/bin:/bin', LANG='C', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2',
        VECLIB_MAXIMUM_THREADS='2', NUMEXPR_NUM_THREADS='2')
    w.save(output/'running-receipt.json', dict(command=command, environment=env, resources=w.RESOURCES,
        original_child_sha256=expected, original_monitor_sha256=w.digest(monitor_path), qualification=w.QUALIFICATION))
    started = time.monotonic(); process = None; observation = None; error = None
    try:
        with (output/'native.log').open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                                       cwd=w.ROOT, start_new_session=True)
            observation = monitor.monitor(process, started, w.RESOURCES)
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
    finally:
        if process is not None and observation is None:
            # Reuse the same owned monitor for the Popen-to-monitor interruption gap.
            observation = monitor.monitor(process, started, dict(w.RESOURCES, process_group_deadline_seconds=0))
    try:
        w.load_contract(path, expected); unchanged = True
    except Exception:
        unchanged = False
    report_path = output/'worker-report.json'
    report = json.loads(report_path.read_text()) if report_path.is_file() and not report_path.is_symlink() else {}
    passed = (process is not None and process.returncode == 0 and error is None and observation is not None
        and not observation['stopped_by_watchdog'] and not observation['monitor_error']
        and not observation['cleanup_error'] and observation['worker_reaped']
        and not observation['worker_running_after_monitor'] and unchanged
        and report.get('opening_subgate_passed') is True and report.get('bound_inputs_unchanged') is True)
    w.save(output/'receipt.json', dict(status='eight_openings_subgate_passed_no_admission' if passed else 'failed_or_rejected_outputs_preserved',
        returncode=process.returncode if process is not None else None, error=error, monitor_observation=observation,
        wall_seconds=time.monotonic()-started, resources=w.RESOURCES, all_inputs_unchanged=unchanged,
        original_child_sha256=expected, original_monitor_sha256=w.digest(monitor_path),
        worker_report_sha256=w.digest(report_path) if report else None,
        native_log_sha256=w.digest(output/'native.log') if (output/'native.log').is_file() else None,
        qualification=w.QUALIFICATION, automatic_retry=False))
    return 0 if passed else 2


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, required=True); p.add_argument('--contract-sha256', required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('Opening controller terminated')))
    raise SystemExit(run(a.contract.resolve(), a.contract_sha256, a.output))
