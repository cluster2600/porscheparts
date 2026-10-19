"""Run the six comparative carrier cases in one bounded, owned CalculiX container."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py'
DOCKER = '/usr/local/bin/docker'
IMAGE = 'sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
CCX_SHA256 = '271f8411371b978d7a8d31a7a13d0765e6e1f872e8a8b1d6aac6d0856c71ec6c'
CASES = [(9, 'combined', None), (9, 'combined', 1000),
         (9, 'gravity', None), (9, 'pitch', None),
         (7, 'combined', None), (7, 'combined', 1000)]


def docker(*args):
    return subprocess.check_output([DOCKER, *args], text=True, timeout=30).strip()


def terminate(signum, frame):
    raise InterruptedError('Calculation cancellation requested')


def run(folder):
    folder = folder.resolve()
    receipt_path = folder / 'simulation-runtime.json'
    if any((folder / name).exists() for name in ('simulation-runtime.json', 'simulation-launcher.py', 'simulation-engine.py')):
        raise FileExistsError('Preserve the previous calculation runtime receipt')
    for size, case, support in CASES:
        mesh = folder / f'mesh-{size}'
        if not (mesh / 'mesh.inp').is_file():
            raise ValueError('Both C3D10 meshes must exist before calculation')
        name = case + (f'-spring-{support}' if support else '-rigid') + '-static'
        if (mesh / (name + '.inp')).exists():
            raise FileExistsError('Preserve previous calculations; use a fresh run')
    launcher_source, engine_source = Path(__file__).read_bytes(), SOURCE.read_bytes()
    (folder / 'simulation-launcher.py').write_bytes(launcher_source)
    (folder / 'simulation-engine.py').write_bytes(engine_source)
    spec = importlib.util.spec_from_file_location('carrier_simulation', SOURCE)
    simulation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(simulation)
    container = 'carrier-workflow-' + uuid.uuid4().hex[:16]
    simulation.CONTAINER = container
    receipt = {'image': IMAGE, 'container': container, 'network': 'none',
               'cpus': 1, 'memory_bytes': 6 * 1024**3, 'swap_bytes': 0,
               'filesystem': 'ephemeral_container_layer_without_host_mounts',
               'pids_limit': 128, 'status': 'starting', 'completed_cases': [],
               'simulation_source_sha256': hashlib.sha256(engine_source).hexdigest(),
               'launcher_sha256': hashlib.sha256(launcher_source).hexdigest()}
    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    save()
    try:
        # Docker cp cannot write a tmpfs mount through its archive API.
        docker('run', '-d', '--name', container, '--network', 'none',
               '--cpus', '1', '--memory', '6g', '--memory-swap', '6g', '--pids-limit', '128',
               '--tmpfs', '/tmp:rw,size=512m',
               '--entrypoint', '/bin/sleep', IMAGE, 'infinity')
        binary = docker('exec', container, 'sha256sum', '/usr/bin/ccx').split()[0]
        if binary != CCX_SHA256:
            raise ValueError('CalculiX binary identity mismatch')
        receipt.update(status='running', ccx_binary_sha256=binary,
                       package=docker('exec', container, 'dpkg-query', '-W', 'calculix-ccx'))
        save()
        for size, case, support in CASES:
            simulation.solve(folder / f'mesh-{size}', case, support=support)
            receipt['completed_cases'].append({'mesh': size, 'case': case, 'support_N_mm': support})
            save()
        if SOURCE.read_bytes() != engine_source or Path(__file__).read_bytes() != launcher_source:
            raise ValueError('Calculation source changed during execution')
        receipt['status'] = 'executed'
    except BaseException as error:
        receipt.update(status='failed', error=str(error))
        raise
    finally:
        result = subprocess.run([DOCKER, 'rm', '-f', container], capture_output=True, text=True, timeout=30)
        receipt['owned_container_removed'] = result.returncode == 0
        save()
        if result.returncode and receipt['status'] == 'executed':
            raise RuntimeError('Calculations completed but owned container removal failed')
    return receipt


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminate)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    print(json.dumps(run(parser.parse_args().folder)))
