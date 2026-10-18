"""Build an isolated, pinned Gmsh runtime around an explicitly supplied read-only CAD Python."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
REQUIREMENTS = Path(__file__).with_name('geometry-runtime-requirements.txt')
CAD_VERSIONS = {'build123d': '0.11.1', 'OCP': '7.9.3.1', 'numpy': '2.0.2'}

PROBE = r'''
import hashlib,json,platform,sys,sysconfig
from pathlib import Path
from importlib import metadata,util
import build123d,OCP,numpy
versions={'build123d':metadata.version('build123d'),'OCP':OCP.__version__,'numpy':numpy.__version__}
files={name:Path(util.find_spec(name).origin)for name in ['build123d','OCP.OCP','numpy._core._multiarray_umath']}
for name in ['build123d','numpy','cadquery-ocp-novtk','cadquery-ocp']:
    try:dist=metadata.distribution(name)
    except metadata.PackageNotFoundError:continue
    for path in dist.files or []:
        if str(path).endswith('.dist-info/RECORD'):files[name+'/RECORD']=Path(dist.locate_file(path))
if sys.argv[1]=='geometry':
    import gmsh
    versions['gmsh']=gmsh.__version__
    gmsh.initialize()
    gmsh.finalize()
    dist=metadata.distribution('gmsh')
    for path in dist.files:
        if str(path).endswith(('.dylib','.so','gmsh.py','/METADATA','/WHEEL','/RECORD')):
            files['gmsh/'+str(path)]=Path(dist.locate_file(path))
print(json.dumps({'versions':versions,'python_version':platform.python_version(),
    'python_abi':sys.implementation.cache_tag,'architecture':platform.machine(),
    'purelib':sysconfig.get_path('purelib'),'executable':sys.executable,
    'artifacts':{name:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
    'bytes':path.stat().st_size}for name,path in files.items()}}))
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def probe(python, mode):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    result = subprocess.run([str(python), '-I', '-B', '-c', PROBE, mode], env=env,
                            capture_output=True, text=True, check=True, timeout=120)
    return json.loads(result.stdout)


def require_versions(observed, geometry=False):
    expected = dict(CAD_VERSIONS, **({'gmsh': '4.15.2'} if geometry else {}))
    if observed['versions'] != expected:
        raise ValueError('Runtime versions differ from pinned CAD/Gmsh versions: ' + json.dumps(observed['versions']))


def setup(cad_python, output):
    cad_python = Path(cad_python).expanduser().absolute()
    output = Path(output).resolve()
    python = output / 'bin/python'
    receipt_path = output / 'provenance.json'
    runtime = {'geometry_python': str(python)}
    if output.exists() and not receipt_path.is_file():
        raise ValueError('Existing directory has no completed runtime receipt; use a fresh path')
    source = probe(cad_python, 'cad')
    require_versions(source)
    if output.exists():
        saved = json.loads(receipt_path.read_text())
        if (saved['installer_sha256'] != sha(__file__) or saved['requirements_sha256'] != sha(REQUIREMENTS)
                or saved['source_CAD'] != source):
            raise ValueError('Installer, pinned requirements or source CAD changed; use a fresh path')
        hook = saved['readonly_CAD_import_hook']
        if sha(hook['path']) != hook['sha256']:
            raise ValueError('Read-only CAD import hook changed')
        installed = probe(python, 'geometry')
        require_versions(installed, geometry=True)
        if installed != saved['installed_runtime'] or json.loads((output / 'runtime.json').read_text()) != runtime:
            raise ValueError('Installed runtime changed after setup')
        return runtime
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    subprocess.run([str(cad_python), '-I', '-B', '-m', 'venv', str(output)], env=env, check=True, timeout=300)
    state = {'source_CAD': source, 'status': 'installing'}
    write(output / 'setup-state.json', state)
    try:
        site = subprocess.run([str(python), '-I', '-B', '-c', 'import sysconfig;print(sysconfig.get_path("purelib"))'],
                              capture_output=True, text=True, env=env, check=True, timeout=30).stdout.strip()
        if '\n' in source['purelib'] or not Path(source['purelib']).is_dir():
            raise ValueError('CAD site-packages directory is invalid')
        # shortcut: the explicit CAD environment remains a read-only dependency; copy/install it only for a standalone distribution.
        hook_path = Path(site) / 'carrier-cad-readonly.pth'
        hook_path.write_text('import sys; sys.dont_write_bytecode = True\n' + source['purelib'] + '\n')
        command = [str(python), '-I', '-B', '-m', 'pip', '--isolated', '--cache-dir', str(output / 'pip-cache'),
                   'install', '--index-url', 'https://pypi.org/simple', '--no-deps', '--require-hashes',
                   '--only-binary=:all:', '--report', str(output / 'pip-install-report.json'),
                   '-r', str(REQUIREMENTS)]
        with (output / 'pip-install.log').open('xb') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        installed = probe(python, 'geometry')
        require_versions(installed, geometry=True)
        if probe(cad_python, 'cad') != source:
            raise ValueError('Source CAD environment changed during setup')
        receipt = {'schema': 'porscheparts.geometry-runtime@1', 'installer_sha256': sha(__file__),
                   'requirements_sha256': sha(REQUIREMENTS), 'source_CAD': source,
                   'readonly_CAD_import_hook': {'path': str(hook_path), 'sha256': sha(hook_path)},
                   'installed_runtime': installed, 'Gmsh_license': 'GPLv2+',
                   'Gmsh_source': 'https://pypi.org/project/gmsh/4.15.2/',
                   'pip_install_report_sha256': sha(output / 'pip-install-report.json'),
                   'pip_install_log_sha256': sha(output / 'pip-install.log'),
                   'source_CAD_mutated': False}
        write(output / 'runtime.json', runtime)
        write(receipt_path, receipt)
        state['status'] = 'ready'
    except Exception as error:
        state.update(status='failed', error=str(error))
        raise
    finally:
        write(output / 'setup-state.json', state)
    return runtime


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/part-workflow/runtimes/geometry')
    args = parser.parse_args()
    print(json.dumps(setup(args.cad_python, args.output)))
