"""Restore only the pinned PyMesh archive in one new owned Linux prefix; smoke at2GiB."""
import hashlib, json, os, shlex, signal, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def main():
    start = time.monotonic(); deadline = start + 360
    plan_path = HERE/'plan.json'; plan_sha = sha(plan_path); p = json.loads(plan_path.read_text())
    receipt = HERE/'execution-receipt.json'
    if receipt.exists() or receipt.is_symlink(): raise FileExistsError('Preserve prior attempt')
    attempted = []; prefix_verified = False
    report = dict(status='starting_no_carrier_admission', events=[], global_admission=False)
    if sha(__file__) != p['caller_sha256']: raise ValueError('Caller changed')
    if p['memory_max_bytes'] != 2*1024**3 or p['cpu_max'] != 1 or p['network'] != 'none':
        raise ValueError('Root approved only oneCPU/2GiB/networknone')
    for stage in p['stages']:
        if any(value not in stage['argv'] for value in ['CPUQuota=100%', 'MemoryMax=2G', 'MemorySwapMax=0', '--unshare-net']):
            raise ValueError('Exact approved scope isolation differs')
    def verify():
        if sha(plan_path) != plan_sha: raise ValueError('Plan changed')
        for name, value in p['files_sha256'].items():
            if sha(name) != value: raise ValueError('Input/source changed')
    verify()
    payload = p['payload']; remote = (HERE/'remote_check.py').read_text()
    def command(argv, label, cap, cleanup=False):
        left = deadline-time.monotonic()-(5 if cleanup else 45)-3
        if left <= 0: raise TimeoutError('Global budget exhausted')
        limit = min(cap, left); began = time.monotonic()
        with (HERE/(label+'.stdout.log')).open('x') as out, (HERE/(label+'.stderr.log')).open('x') as err:
            try:
                result = subprocess.run(argv, stdout=out, stderr=err, timeout=limit)
                report['events'].append(dict(stage=label, returncode=result.returncode, wall_seconds=time.monotonic()-began, timeout_seconds=limit))
            except BaseException as error:
                report['events'].append(dict(stage=label, error_type=type(error).__name__, timeout_seconds=limit)); raise
        if result.returncode != 0: raise RuntimeError(label+' actualRC='+str(result.returncode))
        return (HERE/(label+'.stdout.log')).read_text()
    def ssh(argv, label, cap, cleanup=False):
        return command(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', p['host'], shlex.join(argv)], label, cap, cleanup)
    def check(mode, label, cap=25, cleanup=False):
        left = min(cap, deadline-time.monotonic()-(5 if cleanup else 45)-3)
        if left <= 5: raise TimeoutError('Not enough time to reap metadata/cleanup')
        return json.loads(ssh(['/usr/bin/timeout', '--signal=TERM', '--kill-after=2s', str(left-5),
                               '/usr/bin/python3', '-B', '-c', remote, mode, json.dumps(payload, separators=(',', ':'))], label, left, cleanup))
    def stop(*_): raise KeyboardInterrupt('Owned restoration interrupted')
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    try:
        before = check('preflight', 'preflight', 30); prefix_verified = True
        (HERE/'preflight.json').write_text(json.dumps(before, indent=2)+'\n')
        command(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                 *[str(HERE/n) for n in p['copied_names']], p['host']+':'+shlex.quote(payload['prefix']+'/')], 'upload', 25)
        check('uploaded', 'uploaded'); verify()
        for stage in p['stages']:
            attempted.append(stage['unit']); text = ssh(stage['argv'], stage['id'], stage['ssh_cap_seconds']); verify()
            if stage['id'] == 'restore':
                payload['restored_before'] = check('restored', 'restored', 35)
                (HERE/'restored.json').write_text(json.dumps(payload['restored_before'], indent=2)+'\n')
            else:
                report['native_stdout'] = json.loads(text)
        after = check('post', 'postflight', 35); (HERE/'postflight.json').write_text(json.dumps(after, indent=2)+'\n')
        (HERE/'collected').mkdir()
        for remote_name, local_name in [('pymesh/installation-receipt.json', 'installation-receipt.json'),
                                        ('smoke/smoke-receipt.json', 'smoke-receipt.json'), ('smoke/result.npz', 'result.npz')]:
            command(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                     p['host']+':'+shlex.quote(payload['prefix']+'/'+remote_name), str(HERE/'collected'/local_name)], 'collect-'+local_name, 15)
        if sha(HERE/'collected/installation-receipt.json') != after['installation_receipt_sha256']:
            raise ValueError('Collected installation identity changed')
        if sha(HERE/'collected/smoke-receipt.json') != after['smoke_receipt_sha256'] or sha(HERE/'collected/result.npz') != after['smoke']['result_sha256']:
            raise ValueError('Collected smoke identity changed')
        report.update(status='pinned_archive_restored_and_native_smoke_passed_no_carrier_admission',
                      actual_foreground_restore_exit_code=0, actual_foreground_smoke_exit_code=0, runtime=after)
    except BaseException as error:
        report.update(status='restoration_or_smoke_refused_or_incomplete', error_type=type(error).__name__, error=str(error))
    finally:
        try:
            if prefix_verified:
                payload['attempted_units'] = attempted; report['scope_cleanup'] = check('cleanup', 'cleanup', 35, True)
                report['owned_scopes_inactive'] = True
            elif attempted: raise ValueError('Scope attempted without confirmed prefix ownership')
            else: report['no_native_scope_attempted'] = True
        except BaseException as error:
            report.update(status='cleanup_unconfirmed_no_admission', cleanup_error=str(error), owned_scopes_inactive=False)
        try: verify(); report['local_frozen_files_unchanged'] = True
        except BaseException as error: report.update(status='integrity_refused', integrity_error=str(error))
        report.update(plan_sha256=plan_sha, caller_sha256=sha(__file__), wall_seconds=time.monotonic()-start,
                      global_budget_seconds=360, cleanup_reserve_seconds=45, attempted_exact_scopes=attempted)
        if report['wall_seconds'] > 360: report['status'] = 'global_budget_exceeded'
        report['output_files_sha256'] = {str(x.relative_to(HERE)): sha(x) for x in HERE.rglob('*') if x.is_file() and x != receipt}
        receipt.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': report['status'], 'receipt_sha256': sha(receipt), 'wall_seconds': report['wall_seconds']}), flush=True)
    return 0 if report['status'] == 'pinned_archive_restored_and_native_smoke_passed_no_carrier_admission' else 1


if __name__ == '__main__': raise SystemExit(main())
