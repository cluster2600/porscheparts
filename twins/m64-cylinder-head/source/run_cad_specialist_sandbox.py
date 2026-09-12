#!/usr/bin/env python3
"""Kali controller for two separate bounded generated-CAD containers.

Only inert bytes are read by this controller. Docker, not Python isolation,
contains generated execution. The native audit uses a fresh process/container.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

IMAGE = 'sha256:3f97e71ebf07ee38b5729fa61858578d9c759dfa212f757e7286f3f09f7dc02d'


def cleanup_container(name):
    """An unavailable Docker daemon is unknown state, never verified absence."""
    inspected, removed, probe = None, None, None
    errors = {}
    try:
        inspected = subprocess.run(['docker', 'inspect', name, '--format', '{{json .State}}'],
                                   capture_output=True, text=True, timeout=15)
    except (subprocess.TimeoutExpired, OSError) as error:
        errors['inspect'] = type(error).__name__
    finally:
        try:
            removed = subprocess.run(['docker', 'rm', '-f', name], capture_output=True,
                                     text=True, timeout=20)
        except (subprocess.TimeoutExpired, OSError) as error:
            errors['remove'] = type(error).__name__
        finally:
            try:
                probe = subprocess.run(['docker', 'ps', '-a', '--filter', f'name=^/{name}$',
                                        '--format', '{{.Names}}'], capture_output=True,
                                       text=True, timeout=10)
            except (subprocess.TimeoutExpired, OSError) as error:
                errors['absence_probe'] = type(error).__name__
    state = None
    if inspected is not None and inspected.returncode == 0:
        try:
            state = json.loads(inspected.stdout)
        except (ValueError, TypeError):
            errors['inspect_state'] = 'invalid_JSON'
    return {
        'state': state,
        'removed_verified': bool(probe is not None and probe.returncode == 0 and not probe.stdout.strip()),
        'absence_proof': 'successful_docker_ps_all_exact_name_filter_with_empty_output',
        'inspect_return_code': inspected.returncode if inspected is not None else None,
        'remove_return_code': removed.returncode if removed is not None else None,
        'absence_probe_return_code': probe.returncode if probe is not None else None,
        'absence_probe_names': probe.stdout.splitlines() if probe is not None and probe.returncode == 0 else None,
        'cleanup_errors': errors,
    }


def run_stage(stage, worker, source, output):
    output.mkdir()
    name = 'm64-specialist-' + stage + '-' + uuid.uuid4().hex[:12]
    command = ['docker', 'run', '--name', name, '--network', 'none', '--read-only',
               '--cpus', '2', '--memory', '4g', '--memory-swap', '4g', '--pids-limit', '128',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--user', f'{os.getuid()}:{os.getgid()}', '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m',
               '--ulimit', 'fsize=20000000:20000000', '--ulimit', 'nofile=128:128',
               '-e', 'XDG_CACHE_HOME=/tmp/cache', '-e', 'HOME=/tmp',
               '--mount', f'type=bind,src={worker},dst=/worker.py,readonly',
               '--mount', f'type=bind,src={source},dst=/input,readonly',
               '--mount', f'type=bind,src={output},dst=/output',
               '--entrypoint', '/opt/venv/bin/python3', IMAGE,
               '/worker.py', '--stage', stage, '--input', '/input', '--output', '/output']
    started = time.monotonic()
    timed_out = False
    with (output.parent / f'{stage}.log').open('wb') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                subprocess.run(['docker', 'kill', name], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=15)
            except (subprocess.TimeoutExpired, OSError):
                pass  # the finally path still attempts forced removal and checks absence
            try:
                code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait(timeout=5)
        finally:
            cleanup = cleanup_container(name)
    return {'container_name': name, 'image_id': IMAGE, 'exit_code': code,
            'timed_out': timed_out, 'elapsed_seconds': time.monotonic() - started,
            **cleanup, 'network': 'none',
            'cpu_limit': 2, 'memory_bytes': 4 * 1024**3, 'timeout_seconds': 120}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    code, worker = args.code.resolve(strict=True), args.worker.resolve(strict=True)
    if code.stat().st_size > 100000 or args.output.exists():
        raise ValueError('bounded_code_and_new_output_required')
    args.output.mkdir()
    output = args.output.resolve()
    results = {'schema': 'specialist-CAD-two-stage-container/v1',
               'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'worker_sha256': hashlib.sha256(worker.read_bytes()).hexdigest(),
               'code_sha256': hashlib.sha256(code.read_bytes()).hexdigest()}
    results['execute'] = run_stage('execute', worker, code, output / 'producer')
    native = output / 'producer' / 'candidate.brep'
    if (results['execute']['exit_code'] == 0 and native.is_file() and not native.is_symlink()
            and native.stat().st_size <= 50_000_000):
        results['audit'] = run_stage('audit', worker, native, output / 'independent-audit')
    else:
        results['audit'] = {'not_run': True, 'reason': 'producer_did_not_complete_with_bounded_regular_BRep'}
    (output / 'sandbox-receipt.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
