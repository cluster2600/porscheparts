"""Deux coupons thermiques immuables, une tentative, reçus bornés."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import time
import uuid

IMAGE = 'sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17'
PREP = '491887d1aa2c84057b54c7982621e9f34b1116d36ad5c6e506a2a72b77760aad'
BINARY = 'b13dacc72146e8df5ded9d20c4b20e7a21051dd21244f9598d441e81c871364d'
BASE = Path('/tmp/917-f50/out/f58-energy-diagnostic-20260907-v2')
RUNTIME = Path('/tmp/917-f50/additivefoam-runtime')
LABEL = 'm64.f58_quadrature_40us_owner'
MIB = 1024**2


def need(ok, why):
    if not ok: raise ValueError(why)


def safe(path):
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts and
         re.fullmatch(r'/[A-Za-z0-9_./+-]+', str(path)), 'unsafe_path')
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink_path')
    return path


def sha(path):
    h = hashlib.sha256()
    with safe(Path(path)).open('rb') as f:
        for block in iter(lambda: f.read(MIB), b''): h.update(block)
    return h.hexdigest()


def inventory(root, sources=False, source_links=None):
    result = {}
    links = {}
    for p in sorted(safe(root).rglob('*')):
        if sources and p.is_symlink():
            target = os.readlink(p)
            need(p.parent.name == 'lnInclude' and not Path(target).is_absolute(), 'unexpected_source_link')
            resolved = safe(Path(os.path.normpath(p.parent/target)))
            need(root in resolved.parents and resolved.is_file(), 'source_link_outside_or_nonfile')
            need((p.parent/target).resolve(strict=True) == resolved, 'source_link_resolution_mismatch')
            links[str(p.relative_to(root))] = {'target': target, 'resolved': str(resolved.relative_to(root)), 'sha256': sha(resolved)}
            continue
        need(not p.is_symlink(), 'symlink_tree')
        if p.is_file() and (not sources or p.suffix in ('.C', '.H') or
                            (p.parent.name == 'Make' and p.name in ('files', 'options'))):
            result[str(p.relative_to(root))] = sha(p)
    if sources:
        need(links == source_links and all(result.get(v['resolved']) == v['sha256'] for v in links.values()), 'source_links_pin')
    return result


def save(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()
    need(len(data) <= MIB, 'receipt_exceeds_1MiB')
    with safe(path).open('xb') as f: f.write(data)


def left(start, cap, cleanup=False):
    remaining = start + (600 if cleanup else 570) - time.monotonic()
    need(remaining > 0, 'shared_wall_deadline_exhausted')
    return min(cap, remaining)


def pump(argv, output, deadline, cap, observe=None):
    """Drain stdout+stderr through one bounded writer; no disk spool."""
    child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    selector = selectors.DefaultSelector(); selector.register(child.stdout, selectors.EVENT_READ)
    pending = b''
    try:
        while selector.get_map():
            need(time.monotonic() < deadline, 'native_wall_deadline_exhausted')
            for key, _ in selector.select(min(.1, max(.001, deadline-time.monotonic()))):
                data = os.read(key.fd, 65536)
                if not data:
                    selector.unregister(key.fileobj); continue
                room = cap-output.tell()
                output.write(data[:max(room, 0)]); output.flush()
                need(len(data) <= room, 'log_limit_exceeded')
                if observe:
                    pending += data
                    lines = pending.split(b'\n'); pending = lines.pop()
                    need(len(pending) <= MIB, 'native_line_too_long')
                    for line in lines: observe(line.decode('utf-8', 'replace'))
        if pending and observe: observe(pending.decode('utf-8', 'replace'))
        return child.wait(timeout=max(.001, deadline-time.monotonic()))
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=2)
        selector.close(); child.stdout.close()


def owned(row, name, token, cid=None):
    return (re.fullmatch('[a-f0-9]{64}', row.get('Id', '')) is not None and
            (cid is None or row['Id'] == cid) and row.get('Name') == '/'+name and
            row.get('Image') == IMAGE and (row.get('Config', {}).get('Labels') or {}).get(LABEL) == token)


def mounts(packet):
    result = {str(packet/n): ('/packet/'+n, False) for n in
              ('run_quadrature.py', 'quadrature_worker.py', 'manifest.json', 'preparation-report.json')}
    result.update({str(packet/q): ('/input/'+q, False) for q in ('q10', 'q20')})
    result.update({str(RUNTIME): ('/runtime', False), str(BASE/'bin'): ('/f58bin', False),
                   str(packet/'results'): ('/results', True)})
    return result


def resources(row, packet):
    h = row['HostConfig']; cfg = row['Config']
    actual = {m['Source']: (m['Destination'], m['RW']) for m in row['Mounts'] if m['Type'] == 'bind'}
    return (h.get('NanoCpus') == 2000000000 and h.get('Memory') == h.get('MemorySwap') == 4*1024**3
            and h.get('NetworkMode') == 'none' and h.get('ReadonlyRootfs') is True
            and h.get('CapDrop') == ['ALL'] and h.get('PidsLimit') == 128
            and 'no-new-privileges:true' in h.get('SecurityOpt', [])
            and cfg.get('User') == f'{os.getuid()}:{os.getgid()}' and os.getuid() != 0
            and h.get('LogConfig', {}).get('Type') == 'none'
            and h.get('Tmpfs') == {'/work': 'rw,noexec,nosuid,nodev,size=1g,mode=1777',
                                  '/tmp': 'rw,noexec,nosuid,nodev,size=64m,mode=1777'}
            and actual == mounts(packet) and len(actual) == len(mounts(packet))
            and all(m['Type'] == 'bind' or (m['Type'] == 'tmpfs' and m['Destination'] in ('/work', '/tmp'))
                    for m in row['Mounts']))


def command(packet, name, token):
    argv = ['docker', 'create', '--name', name, '--label', LABEL+'='+token, '--pull', 'never', '--init',
            '--cpus', '2', '--memory', '4g', '--memory-swap', '4g', '--pids-limit', '128', '--network', 'none',
            '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
            '--user', f'{os.getuid()}:{os.getgid()}', '--log-driver', 'none',
            '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=1g,mode=1777',
            '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777',
            '--env', 'PYTHONDONTWRITEBYTECODE=1', '--env', 'OMP_NUM_THREADS=2', '--env', 'OPENBLAS_NUM_THREADS=1']
    for src, (dst, rw) in mounts(packet).items():
        argv += ['--mount', f'type=bind,src={src},dst={dst}'+('' if rw else ',readonly')]
    script = ('source /opt/openfoam14/etc/bashrc && export ADDITIVEFOAM_PROJECT_DIR=/runtime/AdditiveFOAM && '
              'source /runtime/AdditiveFOAM/etc/bashrc && export LD_LIBRARY_PATH='
              '/runtime/user-openfoam/platforms/linux64GccDPInt32Opt/lib:$LD_LIBRARY_PATH && '
              'exec python3 -B -u /packet/quadrature_worker.py')
    return argv+['--entrypoint', '/bin/bash', IMAGE, '--noprofile', '--norc', '-c', script]


def verify(packet, manifest_sha):
    need(re.fullmatch('[a-f0-9]{64}', manifest_sha), 'invalid_manifest_sha')
    need(sha(packet/'manifest.json') == manifest_sha and sha(packet/'preparation-report.json') == PREP, 'manifest_or_preparation_pin')
    m = json.loads((packet/'manifest.json').read_text())
    need(set(m['packet_files']) == {'run_quadrature.py', 'quadrature_worker.py'}, 'exact_source_files_required')
    need(all(sha(packet/n) == h for n, h in m['packet_files'].items()), 'runner_worker_pin')
    prep = json.loads((packet/'preparation-report.json').read_text())
    need(prep['expected_steps'] == 1600 and prep['dt_s'] == 2.5e-8 and prep['end_time_s'] == 4e-5, 'time_grid')
    for q in ('q10', 'q20'):
        need(len(prep['cases'][q]['inputs_sha256']) == 29 and inventory(packet/q) == prep['cases'][q]['inputs_sha256'], 'exact_case_pin')
    backend = m['backend_files']; lib = RUNTIME/'user-openfoam/platforms/linux64GccDPInt32Opt/lib'
    required = {str(BASE/'bin/additiveFoamF58'), str(RUNTIME/'AdditiveFOAM/etc/bashrc'),
                str(RUNTIME/'AdditiveFOAM/etc/materials/AlSi10Mg.cfg'),
                *(str(lib/n) for n in ('libadditiveFoamFunctionObjects.so', 'libadditiveFoamUtilities.so', 'libmovingBeamModels.so'))}
    need(required <= set(backend) and backend[str(BASE/'bin/additiveFoamF58')] == BINARY, 'backend_coverage')
    need(all((RUNTIME in safe(Path(p)).parents or BASE in safe(Path(p)).parents) and sha(Path(p)) == h
             for p, h in backend.items()), 'backend_pin')
    need(m['source_files'] and inventory(BASE/'solver', True, m['source_links']) == m['source_files'], 'solver_source_pin')
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', required=True, type=Path); p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--execute', action='store_true'); a = p.parse_args()
    if not a.execute:
        print('Prepared only: no Docker, SSH or native execution.'); return 0
    start = time.monotonic(); packet = safe(a.packet); os.umask(0o077)
    need(packet.parent == Path('/var/tmp') and re.fullmatch(r'm64-f58-quad\.[A-Za-z0-9]{6,32}', packet.name), 'unique_private_packet')
    need(os.getuid() != 0 and Path(__file__) == packet/'run_quadrature.py', 'nonroot_exact_runner')
    results = packet/'results'; results.mkdir(mode=0o700)  # Exclusive attempt marker.
    token = uuid.uuid4().hex; name = 'm64-f58-quad-'+token; cid = None; proven = False; requested = False
    report = {'schema': 'm64-f58-quadrature-process/v1', 'image': IMAGE, 'manifest_sha256': a.manifest_sha256,
              'container_name': name, 'owner_token': token, 'total_limit_s': 600, 'cleanup_reserve_s': 30,
              'native_case_limit_s': 250, 'automatic_retry': False, 'manufacturing_authorized': False}
    def docker(args, cap=5, cleanup=False):
        return subprocess.check_output(['docker', *args], text=True, timeout=left(start, cap, cleanup))
    try:
        verify(packet, a.manifest_sha256)
        need(docker(['image', 'inspect', IMAGE, '--format', '{{.Id}} {{.Os}}/{{.Architecture}}']) == IMAGE+' linux/amd64\n', 'image_pin')
        memory = next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
        disk = os.statvfs(packet)
        need(memory >= 5*1024**3 and disk.f_bavail*disk.f_frsize >= 512*MIB, 'host_resources')
        argv = command(packet, name, token); report['command'] = argv
        save(results/'preflight.json', report); requested = True
        created = subprocess.check_output(argv, text=True, timeout=left(start, 10)).strip()
        need(re.fullmatch('[a-f0-9]{64}', created), 'container_id'); cid = created
        row = json.loads(docker(['inspect', cid]))[0]
        need(owned(row, name, token, cid), 'initial_identity'); proven = True
        need(resources(row, packet), 'resource_or_mount_mismatch')
        report['inspected_caps_and_mounts'] = {'HostConfig': row['HostConfig'], 'Mounts': row['Mounts'],
            'Id': row['Id'], 'Name': row['Name'], 'Image': row['Image'], 'User': row['Config']['User'],
            'Labels': row['Config']['Labels']}
        with (results/'docker.log').open('xb') as output:
            report['client_exit'] = pump(['docker', 'start', '-a', cid], output, start+570, MIB)
    except Exception as e:
        report['error'] = type(e).__name__+': '+str(e)
    finally:
        contradiction = False
        if requested:
            try:
                row = json.loads(docker(['inspect', cid or name], cleanup=True))[0]
                if not owned(row, name, token, cid):
                    contradiction = True; raise ValueError('cleanup_identity_contradiction')
                cid = row['Id']; proven = True; report['final_state'] = row['State']
                report['final_identity'] = {k: row[k] for k in ('Id', 'Name', 'Image')}
            except Exception as e: report['final_inspection_error'] = str(e)
            if proven and not contradiction:
                try:
                    report['remove_output'] = docker(['rm', '-f', cid], 10, True).strip()
                    ids = docker(['ps', '-aq', '--no-trunc', '--filter', 'id='+cid], cleanup=True).splitlines()
                    report['container_absent'] = cid not in ids and not ids
                except Exception as e: report['cleanup_error'] = str(e)
            else: report['cleanup_error'] = 'No proven uncontradicted ownership; no removal attempted.'
        try:
            verify(packet, a.manifest_sha256); report['inputs_sources_backend_unchanged'] = True
            worker = json.loads((results/'worker-report.json').read_text()); report['worker_completed'] = worker.get('completed') is True
            report['output_sha256'] = inventory(results)
        except Exception as e: report['integrity_or_worker_error'] = str(e)
        state = report.get('final_state', {}); report['container_id'] = cid
        report['elapsed_with_cleanup_s'] = time.monotonic()-start
        report['completed'] = (not report.get('error') and report.get('client_exit') == 0 and
            report.get('container_absent') is True and report.get('inputs_sources_backend_unchanged') is True and
            report.get('worker_completed') is True and state.get('ExitCode') == 0 and state.get('Status') == 'exited' and
            all(state.get(k) is False for k in ('OOMKilled', 'Running', 'Restarting', 'Dead')) and report['elapsed_with_cleanup_s'] <= 600)
        save(results/'process-report.json', report)
    print(json.dumps({'completed': report['completed'], 'container_id': cid, 'results': str(results)}))
    return 0 if report['completed'] else 2


if __name__ == '__main__': raise SystemExit(main())
