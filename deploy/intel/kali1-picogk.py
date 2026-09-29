#!/usr/bin/env python3
"""Run a bounded PicoGK CPU job on Kali1, then collect verified artifacts on Kali2."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('job')
parser.add_argument('--span-mm', type=float, default=40)
parser.add_argument('--voxel-mm', type=float, default=0.25)
args = parser.parse_args()
if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', args.job):
    parser.error('job must match [a-z][a-z0-9-]{0,47}')
if not math.isfinite(args.span_mm) or not 20 <= args.span_mm <= 80:
    parser.error('span must be between 20 and 80 mm')
if not math.isfinite(args.voxel_mm) or not 0.1 <= args.voxel_mm <= 0.5:
    parser.error('voxel must be between 0.1 and 0.5 mm')
base = Path.home() / 'stations/kali1'
destination = base / args.job
if base.is_symlink() or destination.exists() or destination.is_symlink():
    parser.error('output exists or collection root is a symlink')
ssh = ['ssh', '-p', '2221', '-i', str(Path.home() / '.ssh/id_picogk_kali1_cpu'),
       '-o', 'HostKeyAlias=kali1-cpu', '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
       '-o', 'StrictHostKeyChecking=yes', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
       '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3']
remote = '/home/lolman/station-cpu-runner-20260928-r8kj70sz'
command = ['bash', remote + '/run-picogk-cpu.sh', remote + '/runtime',
           remote + '/results/' + args.job, str(args.span_mm), str(args.voxel_mm)]
subprocess.run(ssh + ['lolman@127.0.0.1', shlex.join(command)], check=True, timeout=330)
destination.mkdir(mode=0o700, parents=True)
subprocess.run(['rsync', '-rt', '--no-links', '--no-devices', '--no-specials', '--protect-args',
                '--chmod=Du=rwx,Dgo=,Fu=rw,Fgo=', '-e', shlex.join(ssh), '--',
                'lolman@127.0.0.1:' + remote + '/results/' + args.job + '/', str(destination) + '/'],
               check=True, timeout=120)
report = json.loads((destination / 'execution.json').read_text())
assert report['passed'] and report['host'] == 'kali1'
for item in report['artifacts']:
    path = Path(item['path'])
    assert not path.is_absolute() and '..' not in path.parts
    target = destination / path
    assert target.is_file() and not target.is_symlink()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']
print(json.dumps({'job': args.job, 'host': 'kali1', 'passed': True,
                  'collected_to': str(destination), 'artifact_hashes_verified': len(report['artifacts']),
                  'manufacturing_validated': False}))
