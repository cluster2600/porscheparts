"""Install the locked standalone CAD base and execute its analytic native witness."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

LOCK = Path(__file__).with_name('cad-base-macos-arm64-python310.lock.txt')
OCP_SHA256 = 'ff6431ccc1428562b8180007f3d220f7e3425444138411e5dcd27bc1f0125059'
PROBE = "import json,platform,sys;print(json.dumps({'system':platform.system(),'machine':platform.machine(),'version':list(sys.version_info[:3])}))"
WITNESS = r'''
import hashlib,json,math,platform,sys
from pathlib import Path
from importlib import metadata
from build123d import Box,Cylinder,export_step,import_step
import OCP
out=Path(sys.argv[1])
body=Box(20,10,4)-Cylinder(2,4)
expected=800-16*math.pi
export_step(body,out/'bored-box.step')
restored=import_step(out/'bored-box.step')
checks={'valid':body.is_valid,'one_solid':len(body.solids())==1,
        'analytic_volume_match':abs(body.volume-expected)/expected<1e-8,
        'STEP_readback_valid':restored.is_valid,'STEP_readback_one_solid':len(restored.solids())==1,
        'STEP_readback_match':abs(restored.volume-body.volume)/body.volume<1e-8}
binary=next(Path(OCP.__file__).parent.glob('OCP*.so'))
print(json.dumps({'checks':checks,'volume_mm3':body.volume,'expected_volume_mm3':expected,
 'STEP_readback_volume_mm3':restored.volume,
 'STEP_sha256':hashlib.sha256((out/'bored-box.step').read_bytes()).hexdigest(),
 'native_OCP_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
 'OCP_version':OCP.__version__,'python_version':platform.python_version(),
 'versions':{d.metadata['Name']:d.version for d in metadata.distributions()}}))
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locked_versions():
    entries = [re.fullmatch(r'([A-Za-z0-9_.-]+)==([^ ]+) --hash=sha256:[0-9a-f]{64}', line)
               for line in LOCK.read_text().splitlines() if line and not line.startswith('#')]
    if not entries or any(entry is None for entry in entries):
        raise ValueError('Invalid CAD wheel lock')
    canonical = lambda name: re.sub(r'[-_.]+', '-', name).lower()
    pairs = [(canonical(item[1]), item[2]) for item in entries]
    if len(dict(pairs)) != len(pairs):
        raise ValueError('Duplicate package in CAD wheel lock')
    return dict(pairs)


def validate(python, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    witness = output / 'native-witness.py'
    witness.write_text(WITNESS)
    result = subprocess.run([str(python), '-I', '-B', str(witness), str(output)],
                            capture_output=True, text=True, check=True, timeout=120)
    data = json.loads(result.stdout)
    canonical = lambda name: re.sub(r'[-_.]+', '-', name).lower()
    observed = {canonical(name): version for name, version in data['versions'].items()}
    expected = locked_versions()
    if any(observed.get(name) != version for name, version in expected.items()):
        raise ValueError('Installed CAD packages differ from the locked versions')
    if data['native_OCP_sha256'] != OCP_SHA256 or not all(data['checks'].values()):
        raise ValueError('Native CAD witness failed')
    data.update(installer_sha256=sha(__file__), lock_sha256=sha(LOCK),
                witness_sha256=sha(witness), locked_packages=len(expected))
    (output / 'validation.json').write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    return data


def setup(python, output):
    python, output = Path(python).expanduser().absolute(), Path(output).resolve()
    host = json.loads(subprocess.check_output([str(python), '-I', '-B', '-c', PROBE], text=True, timeout=30))
    if host['system'] != 'Darwin' or host['machine'] != 'arm64' or host['version'][:2] != [3, 10]:
        raise ValueError('This wheel lock requires native macOS arm64 and Python 3.10')
    if output.exists():
        raise FileExistsError('Use a fresh CAD runtime directory')
    locked_versions()
    inputs = {'installer': sha(__file__), 'lock': sha(LOCK)}
    subprocess.run([str(python), '-I', '-B', '-m', 'venv', str(output)], check=True, timeout=120)
    runtime = output / 'bin/python'
    state = {'status': 'installing', 'host': host, 'inputs_sha256': inputs}
    state_path = output / 'setup-state.json'
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    try:
        command = [str(runtime), '-I', '-B', '-m', 'pip', '--isolated', 'install',
                   '--index-url', 'https://pypi.org/simple', '--require-hashes', '--only-binary=:all:',
                   '--report', str(output / 'pip-install-report.json'), '-r', str(LOCK)]
        with (output / 'pip-install.log').open('xb') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        with (output / 'pip-check.log').open('xb') as log:
            subprocess.run([str(runtime), '-I', '-B', '-m', 'pip', 'check'], stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=60)
        native = validate(runtime, output / 'native-check')
        if inputs != {'installer': sha(__file__), 'lock': sha(LOCK)}:
            raise ValueError('CAD installer or lock changed during installation')
        state.update(status='ready', runtime_python=str(runtime), native_validation=native,
                     pip_report_sha256=sha(output / 'pip-install-report.json'),
                     pip_log_sha256=sha(output / 'pip-install.log'), pip_check_sha256=sha(output / 'pip-check.log'))
    except Exception as error:
        state.update(status='failed', error=str(error))
        raise
    finally:
        state_path.write_text(json.dumps(state, indent=2, allow_nan=False) + '\n')
    return {'cad_base_python': str(runtime), 'status': state['status'], 'locked_packages': native['locked_packages']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(validate(args.python, args.output) if args.validate_only else setup(args.python, args.output)))
