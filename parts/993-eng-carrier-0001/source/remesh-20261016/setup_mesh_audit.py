"""Build a pinned, bounded local Linux audit backend without compiling native libraries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[4]
REQUIREMENTS = Path(__file__).with_name('mesh-audit-requirements.txt')
BASE = 'python:3.11.15-slim-bookworm@sha256:ecb0ac954790dd64a0d518d699b9c61a91780c42b0d877c802dbaffd04db66f9'
VERSIONS = {'numpy': '2.2.6', 'scipy': '1.15.3', 'libigl': '2.6.3', 'trimesh': '4.8.3', 'rtree': '1.4.1'}
PROBE = r'''
import hashlib,json,platform,sys
from pathlib import Path
from importlib import metadata
import igl,igl.predicates,numpy,scipy,trimesh,rtree
names=['numpy','scipy','libigl','trimesh','rtree'];files={}
for name in names:
 d=metadata.distribution(name)
 for f in d.files or []:
  if str(f).endswith(('.so','.dylib','/METADATA','/WHEEL','/RECORD')):
   p=Path(d.locate_file(f));files[name+'/'+str(f)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
print(json.dumps({'versions':{n:metadata.version(n)for n in names},'python_version':platform.python_version(),
 'architecture':platform.machine(),'python_abi':sys.implementation.cache_tag,'artifacts':files}))
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def probe(python):
    return json.loads(subprocess.run([str(python), '-I', '-B', '-c', PROBE], capture_output=True, text=True,
                                     check=True, timeout=120).stdout)


def setup(output):
    output = Path(output).resolve()
    saved = output / 'provenance.json'
    python = output / 'bin/python'
    runtime = {'mesh_audit_python': str(python)}
    if output.exists() and not saved.is_file():
        raise ValueError('Existing directory has no completed receipt; use a fresh path')
    if output.exists():
        previous = json.loads(saved.read_text())
        if (previous['installer_sha256'] != sha(__file__) or previous['requirements_sha256'] != sha(REQUIREMENTS)
                or previous['launcher_sha256'] != sha(python)
                or previous['installed_runtime'] != probe(python)
                or json.loads((output / 'runtime.json').read_text()) != runtime):
            raise ValueError('Runtime or installation inputs changed; use a fresh path')
        return runtime
    output.mkdir(parents=True)
    (output / 'bin').mkdir()
    (output / 'requirements.txt').write_bytes(REQUIREMENTS.read_bytes())
    dockerfile = 'FROM ' + BASE + '\nCOPY requirements.txt /opt/requirements.txt\n' + \
        'RUN python -I -B -m pip --isolated install --index-url https://pypi.org/simple --no-cache-dir --no-deps --require-hashes --only-binary=:all: --report /opt/pip-install-report.json -r /opt/requirements.txt\n' + \
        'ENV PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1\n'
    (output / 'Dockerfile').write_text(dockerfile)
    tag = '993-mesh-audit:20261016'
    with (output / 'build.log').open('xb') as log:
        subprocess.run(['docker', 'build', '--platform', 'linux/arm64', '--cpuset-cpus', '0-1', '--memory', '4g',
                        '--iidfile', str(output / 'image-id'), '-t', tag, str(output)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    image = (output / 'image-id').read_text().strip()
    command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2', '--memory', '4g', '--memory-swap', '4g',
               '--user', str(os.getuid()) + ':' + str(os.getgid()), '--read-only', '--tmpfs', '/tmp:rw,size=128m',
               '--mount', 'type=bind,src=' + str(ROOT) + ',dst=' + str(ROOT) + ',readonly',
               '--mount', 'type=bind,src=' + str(ROOT / 'work') + ',dst=' + str(ROOT / 'work'),
               '--workdir', str(ROOT), image, 'python']
    python.write_text('#!/bin/sh\nexec ' + shlex.join(command) + ' "$@"\n')
    python.chmod(0o755)
    installed = probe(python)
    if installed['versions'] != VERSIONS:
        raise ValueError('Installed versions differ from pinned versions')
    report = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only', image,
                             'cat', '/opt/pip-install-report.json'], check=True, capture_output=True).stdout
    (output / 'pip-install-report.json').write_bytes(report)
    receipt = {'schema': 'porscheparts.mesh-audit-runtime@1', 'installer_sha256': sha(__file__),
               'requirements_sha256': sha(REQUIREMENTS), 'launcher_sha256': sha(python),
               'base_image': BASE, 'image_id': image, 'backend': 'local Docker Linux ARM64',
               'installed_runtime': installed, 'limits': {'cpus': 2, 'memory_GiB': 4, 'swap_GiB': 0, 'network': 'none'},
               'pip_install_report_sha256': sha(output / 'pip-install-report.json'),
               'build_log_sha256': sha(output / 'build.log'),
               'sources': {name: 'https://pypi.org/project/' + name + '/' + value + '/' for name, value in VERSIONS.items()},
               'licenses': {'numpy': 'BSD-3-Clause', 'scipy': 'BSD-3-Clause', 'libigl': 'MPL-2.0 (see included component licenses)',
                            'trimesh': 'MIT', 'rtree': 'MIT; bundled libspatialindex license included in wheel'}}
    (output / 'runtime.json').write_text(json.dumps(runtime, indent=2) + '\n')
    saved.write_text(json.dumps(receipt, indent=2) + '\n')
    return runtime


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/part-workflow/runtimes/mesh-audit')
    args = parser.parse_args()
    print(json.dumps(setup(args.output)))
