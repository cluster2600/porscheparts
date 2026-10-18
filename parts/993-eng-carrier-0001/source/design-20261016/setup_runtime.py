"""Create the carrier study runtime while borrowing an explicit CAD installation read-only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PINS = {'numpy': '2.2.6', 'scipy': '1.14.1', 'trimesh': '5.1.0',
        'manifold3d': '3.5.2', 'rtree': '1.4.1', 'gmsh': '4.15.2',
        'matplotlib': '3.10.8', 'build123d': '0.11.1', 'OCP': '7.9.3.1'}
CCX_IMAGE = 'sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
CCX_BINARY_SHA256 = '271f8411371b978d7a8d31a7a13d0765e6e1f872e8a8b1d6aac6d0856c71ec6c'


def probe(python):
    script = """import hashlib,importlib.metadata as m,json,platform,sys,sysconfig
import build123d,OCP
from pathlib import Path
names=['numpy','scipy','trimesh','manifold3d','rtree','gmsh','matplotlib','build123d']
versions={'OCP':OCP.__version__}
for name in names:
 try: versions[name]=m.version(name)
 except m.PackageNotFoundError: pass
binary=next(Path(OCP.__file__).parent.glob('OCP*.so'))
print(json.dumps({'python':sys.version,'machine':platform.machine(),'purelib':sysconfig.get_path('purelib'),
 'versions':versions,'OCP_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}))"""
    return json.loads(subprocess.check_output([str(python), '-c', script], text=True))


def setup(cad_python, output, validate_only=False):
    cad_python, output = Path(cad_python).absolute(), Path(output).absolute()
    cad_root = cad_python.parent.parent.resolve()
    if output.resolve() == cad_root or cad_root in output.resolve().parents:
        raise ValueError('The borrowed CAD environment must remain read-only')
    cad = probe(cad_python)
    if not validate_only:
        if output.exists():
            raise FileExistsError('Use a fresh runtime directory or --validate-only')
        subprocess.run([str(cad_python), '-m', 'venv', '--system-site-packages', str(output)], check=True)
        python = output / 'bin/python'
        purelib = subprocess.check_output([str(python), '-c', "import sysconfig;print(sysconfig.get_path('purelib'))"], text=True).strip()
        (Path(purelib) / 'historical-cad-readonly.pth').write_text(cad['purelib'] + '\n')
        uv = shutil.which('uv')
        if uv is None:
            raise RuntimeError('uv is required to install the pinned non-CAD packages')
        packages = [f'{name}=={version}' for name, version in PINS.items() if name not in ('build123d', 'OCP')]
        subprocess.run([uv, 'pip', 'install', '--python', str(python), *packages], check=True)
    runtime = probe(output / 'bin/python')
    if any(runtime['versions'].get(name) != version for name, version in PINS.items()):
        raise ValueError('Runtime package versions do not match the declared pins')
    if runtime['OCP_binary_sha256'] != cad['OCP_binary_sha256']:
        raise ValueError('CAD binary differs from the explicitly borrowed installation')
    receipt = {'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'cad_python': str(cad_python), 'borrowed_CAD_read_only': True,
               'cad_runtime': cad, 'runtime': runtime, 'pinned_versions': PINS,
               'ccx_image': CCX_IMAGE, 'ccx_binary_sha256': CCX_BINARY_SHA256,
               'ccx_execution_launcher': 'scripts/run_carrier_calculations.py',
               'validation_only': validate_only}
    (output / 'provenance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'runtime_python': str(output / 'bin/python'), 'versions': runtime['versions']}))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('work/part-workflow/runtimes/design'))
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    setup(args.cad_python, args.output, args.validate_only)
