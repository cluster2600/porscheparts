"""Restore the retained untagged OCI archive and run only its two owned CCX smokes."""
import hashlib, importlib.util, json, re, signal, tarfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path, guard=lambda: None):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            guard(); h.update(block)
    return h.hexdigest()


def temperatures(path):
    rows = {}
    lines = Path(path).read_text().splitlines()
    for i, line in enumerate(lines):
        m = re.fullmatch(r'\s*temperatures for set NALL and time\s+(\S+)\s*', line)
        if not m:
            continue
        t = float(m[1]); values = []
        for line2 in lines[i + 1:]:
            if not line2.strip():
                if values: break
                continue
            fields = line2.split()
            if len(fields) != 2: raise ValueError('Incomplete temperature row')
            values.append((int(fields[0]), float(fields[1])))
        if t in rows or [x[0] for x in values] != list(range(1, 9)):
            raise ValueError('Duplicate/incomplete temperature state')
        rows[t] = [x[1] for x in values]
    if set(rows) != {.005, .01}: raise ValueError('Unexpected temperature schedule')
    for t, expected in [(.005, 300.5), (.01, 301.)]:
        if any(not abs(x - expected) <= 1e-4 for x in rows[t]):
            raise ValueError('Existing temperature criterion refused')
    return rows


def main():
    started = time.monotonic(); plan_path = HERE / 'plan.json'; plan_sha = sha(plan_path)
    plan = json.loads(plan_path.read_text()); deadline = started + 300; work_stop = deadline - 45
    receipt = HERE / 'execution-receipt.json'
    if receipt.exists() or receipt.is_symlink(): raise FileExistsError('Preserve previous execution')
    if sha(__file__) != plan['caller_sha256']: raise ValueError('Caller identity changed')
    for p, d in plan['files_sha256'].items():
        if sha(p) != d: raise ValueError('Input identity changed')
    spec = importlib.util.spec_from_file_location('private_owned_ccx_restore_protocol', plan['protocol'])
    protocol = importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)
    cli = protocol.DockerCLI(); signal.signal(signal.SIGTERM, cli.cancel); signal.signal(signal.SIGINT, cli.cancel)
    report = {'status': 'starting_no_admission', 'operations': [], 'containers': [], 'archive_load_executed': False,
              'global_admission': False, 'clean_daemon_claim': False}

    def remaining(cleanup=False):
        value = (deadline - 5 if cleanup else work_stop) - time.monotonic()
        if value <= 3: raise TimeoutError('Global budget exhausted')
        return value

    def command(args, cap=15, cleanup=False, log=None, expected_rc=0):
        result = cli.invoke(args, min(cap, remaining(cleanup) - 2), log, ignore_cancel=cleanup)
        report['operations'].append({'arguments': args, **result})
        if result.get('timed_out') or result.get('cancelled') or result['returncode'] != expected_rc:
            raise RuntimeError('Actual Docker operation refused: ' + args[0])
        return result

    def image_metadata(cleanup=False):
        fmt = '{"Id":{{json .Id}},"RepoTags":{{json .RepoTags}},"Architecture":{{json .Architecture}},"Os":{{json .Os}}}'
        return json.loads(command(['image', 'inspect', plan['image'], '--format', fmt], cleanup=cleanup)['stdout'])

    def owned(target, name, token, cleanup=False):
        d = json.loads(command(['container', 'inspect', target, '--format', protocol.FORMAT], cleanup=cleanup)['stdout'])
        if (not re.fullmatch('[0-9a-f]{64}', d.get('Id', '')) or d['Name'] != '/' + name
                or d['Owner'] != token or d['Image'] != plan['image']
                or (re.fullmatch('[0-9a-f]{64}', target) and d['Id'] != target)):
            raise ValueError('Container ownership refused')
        return d

    def smoke(kind, seconds, expected_rc):
        row = {'kind': kind, 'creation_attempted': False, 'container_removed': False}; report['containers'].append(row)
        name = plan['container_names'][kind]; token = plan['ownership_token'] + '-' + kind; cid = None
        case = HERE / kind
        if case.is_symlink() or case.resolve() != case: raise ValueError('Case path changed')
        for f in [case / 'native.log', HERE / (kind + '-ccx.prestart')]:
            if f.exists() or f.is_symlink(): raise FileExistsError('Smoke output not fresh')
        cmd = ['--kill-after=2s', str(seconds) + 's', '/usr/bin/ccx', *(['-v'] if kind == 'version' else ['-i', 'common'])]
        try:
            previous = command(['container', 'ls', '-a', '--no-trunc', '--filter', 'name=^/' + name + '$', '--format', '{{.ID}}'])
            if previous['stdout'].strip(): raise FileExistsError('Owned name not fresh')
            argv = ['create', '--pull=never', '--name', name, '--label', protocol.OWNER_KEY + '=' + token,
                    '--network', 'none', '--cpus', '1', '--memory', '6g', '--memory-swap', '6g', '--pids-limit', '128',
                    '--read-only', '--tmpfs', '/tmp:rw,size=64m', '--mount', 'type=bind,src=' + str(case) + ',dst=/work',
                    '--workdir', '/work', '--env', 'OMP_NUM_THREADS=1', '--env', 'OPENBLAS_NUM_THREADS=1',
                    '--env', 'CCX_NPROC_RESULTS=1', '--entrypoint', '/usr/bin/timeout', plan['image'], *cmd]
            row['creation_attempted'] = True
            cid = command(argv, 25)['stdout'].strip()
            if not re.fullmatch('[0-9a-f]{64}', cid): raise ValueError('Unknown creation response')
            d = owned(cid, name, token); row['container_id'] = cid; row['before_start'] = d
            expected = {'NanoCpus': 10**9, 'Memory': 6*1024**3, 'MemorySwap': 6*1024**3,
                        'PidsLimit': 128, 'NetworkMode': 'none', 'ReadonlyRootfs': True,
                        'Tmpfs': {'/tmp': 'rw,size=64m'}, 'Entrypoint': ['/usr/bin/timeout'], 'Cmd': cmd, 'WorkingDir': '/work'}
            if any(d.get(k) != v for k, v in expected.items()): raise ValueError('Isolation changed')
            mounts = d['Mounts']; binds = [m for m in mounts if m['Type'] == 'bind']
            if len(binds) != 1 or binds[0]['Source'] != str(case) or binds[0]['Destination'] != '/work' or not binds[0]['RW']:
                raise ValueError('Unexpected bind mount')
            if any(m['Type'] != 'bind' and not (m['Type'] == 'tmpfs' and m['Destination'] == '/tmp') for m in mounts):
                raise ValueError('Additional mount refused')
            binary = HERE / (kind + '-ccx.prestart')
            command(['cp', cid + ':/usr/bin/ccx', str(binary)], 15)
            if sha(binary, remaining) != plan['binary_sha256']: raise ValueError('Binary changed')
            r = command(['start', '--attach', cid], seconds + 5, log=case / 'native.log', expected_rc=expected_rc)
            row['attach_cli_returncode'] = r['returncode']; d = owned(cid, name, token); row['after_start'] = d
            row['actual_container_exit_code'] = d['ExitCode']
            if d['Running'] or d['OOMKilled'] or d['StateError'] or d['ExitCode'] != expected_rc:
                raise ValueError('Actual native state refused')
            text = (case / 'native.log').read_text() + (case / 'native.log.stderr').read_text()
            if re.search(r'error while loading|No such file|\*ERROR', text, re.I): raise ValueError('Native error')
            if kind == 'version':
                if not re.search(r'Version\s*2\.21\b', text, re.I): raise ValueError('Version not identified')
            else:
                if 'Job finished' not in text: raise ValueError('Missing completion marker')
                for suffix in ['dat', 'frd', 'sta', 'cvg']:
                    p = case / ('common.' + suffix)
                    if not p.is_file() or p.is_symlink() or p.stat().st_size == 0: raise ValueError('Missing output')
                row['temperatures_K_by_time_s'] = temperatures(case / 'common.dat')
            row['status'] = 'passed_software_smoke'
        finally:
            if row['creation_attempted']:
                try:
                    d = owned(cid or name, name, token, cleanup=True); cid = d['Id']
                    command(['rm', '--force', cid], 15, cleanup=True)
                    r = command(['container', 'ls', '-a', '--no-trunc', '--filter', 'id=' + cid, '--format', '{{.ID}}'], cleanup=True)
                    if r['stdout'].strip(): raise ValueError('Owned container remains')
                    row['container_removed'] = True
                except BaseException as error:
                    row['cleanup_error'] = repr(error); raise

    try:
        with tarfile.open(plan['archive'], 'r:') as archive:
            index = json.load(archive.extractfile('index.json')); manifest = json.load(archive.extractfile('manifest.json'))
            if len(index['manifests']) != 1 or index['manifests'][0]['digest'] != plan['image']:
                raise ValueError('OCI manifest mismatch')
            if len(manifest) != 1 or manifest[0].get('RepoTags') is not None: raise ValueError('Archive aliases refused')
        before = image_metadata(); report['image_metadata_before'] = before
        if before['Id'] != plan['image'] or before['Architecture'] != 'arm64' or before['Os'] != 'linux':
            raise ValueError('Existing image identity refused')
        loaded = command(['image', 'load', '--input', plan['archive']], 120, log=HERE / 'load.log')
        report['archive_load_executed'] = True; report['load_cli_returncode'] = loaded['returncode']
        report['image_metadata_after_load'] = image_metadata()
        if report['image_metadata_after_load'] != before: raise ValueError('Existing image metadata changed')
        smoke('version', 10, 201)
        smoke('solve', 60, 0)
        report['status'] = 'archive_accepted_and_native_smokes_passed_cached_image_explicit'
    except BaseException as error:
        report.update(status='restoration_or_smoke_refused', error_type=type(error).__name__, error=str(error))
    finally:
        try:
            report['image_metadata_final'] = image_metadata(cleanup=True)
            if report.get('image_metadata_before') != report['image_metadata_final']: raise ValueError('Image metadata not preserved')
            for p, d in plan['files_sha256'].items():
                if sha(p, lambda: remaining(True)) != d: raise ValueError('Input/source changed')
            if sha(plan_path) != plan_sha: raise ValueError('Plan changed')
            report['inputs_and_image_preserved'] = True
        except BaseException as error:
            report.update(status='integrity_or_final_metadata_refused', final_error=str(error))
        report.update(plan_sha256=plan_sha, caller_sha256=sha(__file__), wall_seconds=time.monotonic()-started,
                      global_budget_seconds=300, cleanup_reserve_seconds=45)
        report['within_global_budget'] = report['wall_seconds'] <= 300
        report['output_files_sha256'] = {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file() and p != receipt}
        if not report['within_global_budget']: report['status'] = 'global_budget_exceeded'
        receipt.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': report['status'], 'receipt_sha256': sha(receipt), 'wall_seconds': report['wall_seconds']}), flush=True)
    return 0 if report['status'] == 'archive_accepted_and_native_smokes_passed_cached_image_explicit' else 1


if __name__ == '__main__': raise SystemExit(main())
