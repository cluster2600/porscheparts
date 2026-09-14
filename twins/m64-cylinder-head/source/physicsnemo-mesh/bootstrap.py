#!/usr/bin/env python3
"""Bounded dependency bootstrap in an owned disposable Vast workstation."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path('/workspace/m64-physicsnemo/bootstrap-v2')
VENV = ROOT / 'venv'
PYTHON = VENV / 'bin/python'
START = time.monotonic()
DEADLINE = START + 1000
REPORT = {'status': 'incomplete', 'steps': [], 'manufacturing_authorized': False}


def run(name, argv, seconds):
    record = {'name': name, 'exit_code': None}
    REPORT['steps'].append(record)
    child = None
    with (ROOT / (name + '.log')).open('xb') as log:
        try:
            child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
            record['exit_code'] = child.wait(timeout=min(seconds, max(1, DEADLINE-time.monotonic())))
        finally:
            if child is not None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=10)
    if record['exit_code'] != 0:
        raise RuntimeError(name + '_failed')


def main():
    ROOT.mkdir(mode=0o700, exist_ok=True)
    os.environ.update(PIP_NO_INPUT='1', PIP_DISABLE_PIP_VERSION_CHECK='1',
                      PIP_PROGRESS_BAR='off', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
    try:
        if VENV.exists() or (ROOT / 'bootstrap-report.json').exists():
            raise RuntimeError('fresh_environment_required')
        run('venv', ['/usr/bin/python3', '-m', 'venv', str(VENV)], 30)
        run('pip-upgrade', [str(PYTHON), '-m', 'pip', 'install', '--no-cache-dir',
            'pip==26.2.1', '--report', str(ROOT/'pip-upgrade-report.json')], 60)
        run('torch-install', [str(PYTHON), '-m', 'pip', 'install', '--no-cache-dir',
            'torch==2.10.0', 'torchvision==0.25.0',
            '--index-url', 'https://download.pytorch.org/whl/cu128',
            '--report', str(ROOT/'torch-install-report.json')], 450)
        run('physicsnemo-install', [str(PYTHON), '-m', 'pip', 'install', '--no-cache-dir',
            'nvidia-physicsnemo==2.2.2', '--report', str(ROOT/'physicsnemo-install-report.json')], 450)
        install = json.loads((ROOT/'physicsnemo-install-report.json').read_text())
        own = [x for x in install['install'] if x['metadata']['name'].replace('_','-').lower() == 'nvidia-physicsnemo']
        if len(own) != 1 or own[0]['download_info']['archive_info']['hashes']['sha256'] != 'c447771384d92f5c31547e293f65b70e0947f8829981f34c7e8300daf1b8d2eb':
            raise RuntimeError('physicsnemo_wheel_hash_mismatch')
        run('pip-check', [str(PYTHON), '-m', 'pip', 'check'], 30)
        run('freeze', [str(PYTHON), '-m', 'pip', 'freeze'], 30)
        run('import-gpu', [str(PYTHON), '-c',
            'import json,torch,physicsnemo; from physicsnemo.mesh import Mesh; '
            'assert torch.cuda.is_available(); '
            'print(json.dumps(dict(torch=torch.__version__,physicsnemo=physicsnemo.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0),capability=torch.cuda.get_device_capability(0))))'], 60)
        REPORT.update(status='software_gpu_ready_not_physics_validated',
                      versions=json.loads((ROOT/'import-gpu.log').read_text().splitlines()[-1]),
                      script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    except Exception as error:
        REPORT.update(status='bootstrap_failed', reason=type(error).__name__+':'+str(error)[:160])
    finally:
        REPORT['seconds'] = time.monotonic()-START
        with (ROOT/'bootstrap-report.json').open('x') as stream:
            json.dump(REPORT, stream, indent=2)
        print(json.dumps(REPORT))
    return 0 if REPORT['status']=='software_gpu_ready_not_physics_validated' else 1


if __name__ == '__main__':
    sys.exit(main())
