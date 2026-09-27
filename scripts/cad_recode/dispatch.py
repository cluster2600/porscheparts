#!/usr/bin/env python3
"""Operator-owned, single-pass dispatcher. OpenClaw has file tools, not Docker."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import re
from pipeline import export_sandbox, new_output, write_json


def request_stage(value):
    if not isinstance(value, dict) or set(value) != {'stage', 'attempt'}:
        raise ValueError('only stage and attempt are accepted')
    if value['stage'] not in ('export', 'evaluate') or type(value['attempt']) is not int or not 1 <= value['attempt'] <= 3:
        raise ValueError('invalid stage or attempt')
    return value['stage'], value['attempt']


def contained(root, path):
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('path outside workspace')
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace', type=Path); p.add_argument('run', type=Path)
    p.add_argument('--cad-image', required=True)
    a = p.parse_args()
    if not re.fullmatch(r"(?:[a-z0-9][a-z0-9._/:-]*@)?sha256:[0-9a-f]{64}", a.cad_image):
        raise ValueError("immutable CAD image required")
    # Invoke serially from a systemd timer/terminal; no daemon or Docker socket for agent.
    lock = (a.run / '.dispatcher.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    requests = contained(a.workspace, a.workspace / 'requests')
    for path in sorted(requests.glob('*.json')):
        contained(requests, path)
        if path.stat().st_size > 4096: raise ValueError('request too large')
        stage, attempt = request_stage(json.loads(path.read_text()))
        dest = a.run / f'{stage}-{attempt}'
        if dest.exists(): continue  # Exactly one execution per stage/attempt.
        if stage == 'export':
            code = contained(a.workspace, a.workspace / f'candidate-{attempt}.py')
            if code.stat().st_size > 1_000_000: raise ValueError('code too large')
            # Snapshot is not writable by the agent, avoiding bind-mount races.
            snapshot = new_output(a.run / f'submission-{attempt}') / 'candidate.py'
            shutil.copyfile(code, snapshot)
            export_sandbox(snapshot, a.run / 'intake', dest, a.cad_image)
        else:
            # STEP is untrusted: parsing/evaluation also stays in a bounded container.
            dest = new_output(dest)
            dest.chmod(0o777)
            command = ['docker', 'run', '--rm', '--platform=linux/amd64', '--network=none', '--read-only',
                '--cap-drop=ALL', '--security-opt=no-new-privileges', '--memory=8g',
                '--cpus=2', '--pids-limit=64', '--user=65534:65534', '--tmpfs=/tmp:rw,size=256m',
                '--mount', f'type=bind,src={a.run.resolve()},dst=/run,readonly',
                '--mount', f'type=bind,src={dest.resolve()},dst=/evaluation',
                a.cad_image, 'python', '/opt/cad-recode/pipeline.py', 'evaluate', '/run/intake',
                f'/run/export-{attempt}/candidate.step', '/evaluation/report']
            name = f'cad-recode-evaluate-{attempt}'
            command[3:3] = ['--name', name]
            try:
                with (dest / 'execution.log').open('wb') as log:
                    r = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                write_json(dest / 'execution.json', {'status': 'finished' if r.returncode == 0 else 'failed'})
            except subprocess.TimeoutExpired:
                write_json(dest / 'execution.json', {'status': 'timeout'})
            finally:
                subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


if __name__ == '__main__': main()
