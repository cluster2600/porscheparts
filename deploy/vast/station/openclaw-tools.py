#!/usr/bin/env python3
"""Fixed station commands for OpenClaw; no credentials or Vast lifecycle API."""
import argparse
import ipaddress
import json
import math
import re
import shlex
import subprocess
import sys
from pathlib import Path

JOB = re.compile(r"[a-z][a-z0-9-]{0,47}\Z")

# Executed as station-worker after SSH authenticates with its dedicated key.
# The child survives SSH disconnects; stdout/stderr stay in the job directory.
WORKER = r'''
import fcntl, json, os, signal, subprocess, sys, time
from pathlib import Path
work, action, command = Path(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3])
state = work / (action + '.json')
def record(status, **extra):
    temporary = state.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(action=action, status=status, updated_epoch=time.time(), **extra)) + '\n')
    temporary.replace(state)
try:
    record('queued', pid=os.getpid())
    # ponytail: one compute queue; split per GPU only if measured throughput needs it.
    with (work.parent / '.compute.lock').open('a') as queue:
        fcntl.flock(queue, fcntl.LOCK_EX)
        record('running', pid=os.getpid())
        process = subprocess.Popen(command, start_new_session=True)
        try:
            result = process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise RuntimeError('task exceeded 1800 seconds')
        record('complete' if result == 0 else 'failed', returncode=result)
except Exception as error:
    record('failed', error=str(error))
    raise
'''

REMOTE = 'WORKER = ' + repr(WORKER) + r'''
import json, math, os, re, subprocess, sys, time
from pathlib import Path
root = Path('/workspace/jobs')
action, job, span, voxel = json.loads(sys.argv[1])
if action == 'status':
    states = []
    for work in sorted(root.iterdir()):
        if not work.is_dir() or work.is_symlink() or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', work.name):
            continue
        for path in sorted(work.glob('*.json')):
            if path.name not in {'demo.json', 'render.json'} or path.is_symlink():
                continue
            record = json.loads(path.read_text())
            if record.get('status') in {'queued', 'running'}:
                try:
                    command_line = Path('/proc', str(record['pid']), 'cmdline').read_bytes()
                    work_argument = str(work).encode()
                    if not any(arg == work_argument or arg.startswith(work_argument + b'/')
                               for arg in command_line.split(b'\0')):
                        raise FileNotFoundError()
                except (KeyError, FileNotFoundError):
                    record['status'] = 'interrupted_or_unknown'
            states.append(dict(job=work.name, **record))
    print(json.dumps({'jobs': states, 'manufacturing_validated': False}))
    sys.exit(0)
if action not in {'demo', 'render'} or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', job):
    raise ValueError('invalid station task')
work = root / job
if action == 'demo':
    if not math.isfinite(span) or not 20 <= span <= 80 or not math.isfinite(voxel) or not 0.1 <= voxel <= 0.5:
        raise ValueError('invalid geometry parameters')
    work.mkdir(mode=0o700)
    command = ['/usr/local/bin/station-demo', str(work / 'output'), '--span-mm', str(span), '--voxel-mm', str(voxel)]
else:
    if not work.is_dir() or work.is_symlink() or not (work / 'output/completed.json').is_file():
        raise ValueError('completed demo required before render')
    command = ['/usr/local/bin/station-render', str(work / 'output/station-assembly.usda'), str(work / 'render.png')]
state = work / (action + '.json')
with state.open('x') as output:
    json.dump({'action': action, 'status': 'starting', 'updated_epoch': time.time()}, output)
try:
    with (work / (action + '.log')).open('xb') as log:
        process = subprocess.Popen([sys.executable, '-c', WORKER, str(work), action, json.dumps(command)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
except Exception as error:
    state.write_text(json.dumps({'action': action, 'status': 'failed_to_start', 'error': str(error)}) + '\n')
    raise
print(json.dumps({'job': job, 'action': action, 'pid': process.pid, 'directory': str(work), 'accepted': True}))
'''


def validate_job(value):
    if not JOB.fullmatch(value):
        raise argparse.ArgumentTypeError('job must match [a-z][a-z0-9-]{0,47}')
    return value


def bounded_number(low, high):
    def parse(value):
        result = float(value)
        if not math.isfinite(result) or not low <= result <= high:
            raise argparse.ArgumentTypeError(f'value must be between {low} and {high}')
        return result
    return parse


def endpoint(path):
    value = json.loads(path.read_text())
    host, port = value.get('host', ''), value.get('port')
    if not isinstance(host, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}', host):
        raise ValueError('endpoint host must be an IPv4 address or DNS hostname')
    if all(character in '0123456789.' for character in host):
        ipaddress.IPv4Address(host)
    elif any(not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', label) for label in host.split('.')):
        raise ValueError('invalid endpoint DNS hostname')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('endpoint port must be an integer in 1..65535')
    return host, port


def ssh_options(port):
    return ['ssh', '-p', str(port), '-i', str(Path.home() / '.ssh/id_picogk_station_worker'),
            '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3']


def collect(host, port, job):
    base = Path.home() / 'stations'
    destination = base / job
    if base.is_symlink() or destination.is_symlink():
        raise ValueError('collection directory must not be a symlink')
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any(path.is_symlink() for path in destination.rglob('*')):
        raise ValueError('collection directory contains a symlink')
    subprocess.run(['rsync', '-rt', '--no-links', '--no-devices', '--no-specials', '--protect-args',
                    '--chmod=Du=rwx,Dgo=,Fu=rw,Fgo=', '-e', shlex.join(ssh_options(port)), '--',
                    f'station-worker@{host}:/workspace/jobs/{job}/', str(destination) + '/'],
                   check=True, timeout=300)
    print(json.dumps({'job': job, 'collected_to': str(destination)}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', type=Path, default=Path.home() / '.config/picogk-station/endpoint.json')
    commands = parser.add_subparsers(dest='action', required=True)
    demo = commands.add_parser('demo')
    demo.add_argument('job', type=validate_job)
    demo.add_argument('--span-mm', type=bounded_number(20, 80), default=30.0)
    demo.add_argument('--voxel-mm', type=bounded_number(0.1, 0.5), default=0.25)
    commands.add_parser('status')
    for action in ('render', 'collect'):
        commands.add_parser(action).add_argument('job', type=validate_job)
    args = parser.parse_args(argv)
    host, port = endpoint(args.endpoint)
    if args.action == 'collect':
        collect(host, port, args.job)
        return
    payload = [args.action, getattr(args, 'job', None), getattr(args, 'span_mm', None), getattr(args, 'voxel_mm', None)]
    command = shlex.join(['/usr/bin/python3', '-c', REMOTE, json.dumps(payload)])
    subprocess.run(ssh_options(port) + [f'station-worker@{host}', command], check=True, timeout=30)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'station-task: {error}', file=sys.stderr)
        sys.exit(1)
