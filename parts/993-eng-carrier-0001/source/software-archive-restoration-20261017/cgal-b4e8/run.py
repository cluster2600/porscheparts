"""Restore only the pinned experimental CGALb4e8 archive in one new owned Linux prefix."""
import hashlib, json, os, shlex, signal, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def validate_smokes(report):
    from fractions import Fraction
    expected=[('union-prisms','union',4000),('intersection-prisms','intersection',2000),('difference-prism-gap','difference',3200)]
    if report.get('status')!='three_existing_binary_witnesses_passed' or report.get('global_admission') is not False:
        raise ValueError('Finite smoke receipt is incomplete or promoted')
    rows=report.get('cases',[])
    if len(rows)!=3:raise ValueError('Exactly three native witness results required')
    for row,(name,mode,volume) in zip(rows,expected):
        if (row.get('name')!=name or row.get('mode')!=mode or row.get('actual_worker_returncode')!=0
                or row.get('actual_native_returncode')!=0 or row.get('passed') is not True
                or Fraction(row['actual_exact_volume_mm3'])!=volume
                or Fraction(row['expected_exact_volume_mm3'])!=volume
                or any(row.get(k) is not True for k in ['native_exact_gate_pass','rounded_exact_contact_gate_pass','source_face_lineage_complete'])
                or row.get('output_topology',{}).get('pass') is not True):
            raise ValueError('Finite binary witness gate refused')


def main():
    start = time.monotonic(); deadline = start + 900
    plan_path = HERE/'plan.json'; plan_sha = sha(plan_path); p = json.loads(plan_path.read_text())
    receipt = HERE/'execution-receipt.json'
    if receipt.exists() or receipt.is_symlink(): raise FileExistsError('Preserve prior attempt')
    attempted = []; prefix_verified = False
    report = dict(status='starting_no_carrier_admission', events=[], global_admission=False)
    if sha(__file__) != p['caller_sha256']: raise ValueError('Caller changed')
    if p['memory_max_bytes'] != 6*1024**3 or p['cpu_max'] != 1 or p['network'] != 'none':
        raise ValueError('Root approved only oneCPU/6GiB/networknone')
    for stage in p['stages']:
        if any(value not in stage['argv'] for value in ['CPUQuota=100%', 'MemoryMax=6G', 'MemorySwapMax=0', '--unshare-net']):
            raise ValueError('Exact approved scope isolation differs')
    def verify():
        if sha(plan_path) != plan_sha: raise ValueError('Plan changed')
        for name, value in p['files_sha256'].items():
            if sha(name) != value: raise ValueError('Input/source changed')
    verify()
    payload = p['payload']; remote = (HERE/'remote_check.py').read_text()
    def command(argv, label, cap, cleanup=False):
        left = deadline-time.monotonic()-(5 if cleanup else 60)-3
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
        left = min(cap, deadline-time.monotonic()-(5 if cleanup else 60)-3)
        if left <= 5: raise TimeoutError('Not enough time to reap metadata/cleanup')
        return json.loads(ssh(['/usr/bin/timeout', '--signal=TERM', '--kill-after=2s', str(left-5),
                               '/usr/bin/python3', '-B', '-c', remote, mode, json.dumps(payload, separators=(',', ':'))], label, left, cleanup))
    def stop(*_): raise KeyboardInterrupt('Owned restoration interrupted')
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    try:
        before = check('preflight', 'preflight', 30); prefix_verified = True
        payload['runtime_before'] = {k: before[k] for k in ['runtime_files_sha256','compiler_cmake_sha256','compiler_version']}
        (HERE/'preflight.json').write_text(json.dumps(before, indent=2)+'\n')
        command(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                 *[str(HERE/n) for n in p['copied_names']], p['host']+':'+shlex.quote(payload['prefix']+'/')], 'upload', 25)
        check('uploaded', 'uploaded'); verify()
        for stage in p['stages']:
            attempted.append(stage['unit']); text = ssh(stage['argv'], stage['id'], stage['ssh_cap_seconds']); verify()
            if stage['id'] == 'restore':
                restored = check('restored', 'restored', 35)
                (HERE/'restored.json').write_text(json.dumps(restored, indent=2)+'\n')
            elif stage['id'] == 'compile':
                built = check('built', 'postcompile', 35)
                (HERE/'postcompile.json').write_text(json.dumps(built, indent=2)+'\n')
            elif stage['id'] == 'smoke':
                report['native_stdout'] = json.loads(text)
        after = check('post', 'postflight', 35); (HERE/'postflight.json').write_text(json.dumps(after, indent=2)+'\n')
        (HERE/'collected').mkdir()
        artifacts = [('source-restoration.json','source-restoration.json'), ('smoke/smoke-receipt.json','smoke-receipt.json')]
        for row in after['smoke']['cases']:
            for name in ['audit.json','native.json','result.npz','result.mesh64.exact']:
                artifacts.append(('smoke/'+row['name']+'/'+name,row['name']+'-'+name))
        for remote_name, local_name in artifacts:
            command(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=10',
                p['host']+':'+shlex.quote(payload['prefix']+'/'+remote_name),str(HERE/'collected'/local_name)],'collect-'+local_name,15)
        if (sha(HERE/'collected/source-restoration.json') != after['source_restoration_receipt_sha256']
                or sha(HERE/'collected/smoke-receipt.json') != after['smoke_receipt_sha256']):
            raise ValueError('Collected restoration/smoke receipt changed')
        if any(after[k] != built[k] for k in ['binary_sha256','linked_libraries_sha256','compiled_headers_sha256']):
            raise ValueError('New binary or read-only compiler dependencies changed during smokes')
        for row in after['smoke']['cases']:
            for name,key in [('audit.json','audit_sha256'),('native.json','native_sha256'),('result.npz','result_sha256'),('result.mesh64.exact','exact_result_sha256')]:
                if sha(HERE/'collected'/(row['name']+'-'+name)) != row[key]:
                    raise ValueError('Collected finite witness output differs')
        validate_smokes(after['smoke'])
        report.update(status='pinned_archive_restored_and_native_smoke_passed_no_carrier_admission',
                      actual_foreground_restore_exit_code=0, actual_foreground_configure_exit_code=0, actual_foreground_compile_exit_code=0, actual_foreground_smoke_exit_code=0, runtime=after)
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
                      global_budget_seconds=900, cleanup_reserve_seconds=60, attempted_exact_scopes=attempted)
        if report['wall_seconds'] > 900: report['status'] = 'global_budget_exceeded'
        report['output_files_sha256'] = {str(x.relative_to(HERE)): sha(x) for x in HERE.rglob('*') if x.is_file() and x != receipt}
        receipt.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': report['status'], 'receipt_sha256': sha(receipt), 'wall_seconds': report['wall_seconds']}), flush=True)
    return 0 if report['status'] == 'pinned_archive_restored_and_native_smoke_passed_no_carrier_admission' else 1


if __name__ == '__main__': raise SystemExit(main())
