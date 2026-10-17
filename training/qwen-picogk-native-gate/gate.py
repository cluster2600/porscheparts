"""Independently check a bounded model plan, its raw mesh and its native VDB field."""
import argparse
import html
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'training/qwen-picogk-20261012'))
import pilot


def read(path):
    if path.stat().st_size > 16384:
        raise ValueError('Input exceeds 16 KiB')
    return json.loads(path.read_text(), object_pairs_hook=pilot.unique)


def checked_plan(receipt, expected):
    if not isinstance(receipt, dict) or not isinstance(receipt.get('raw_response'), str) or receipt.get('structure_passed') is not True:
        raise ValueError('A complete raw response accepted by the inference boundary is required')
    actual = pilot.parse(receipt['raw_response'])
    expected = pilot.parse(json.dumps(expected, allow_nan=False))
    if actual['missing'] or expected['missing']:
        raise ValueError('Measured interfaces are missing; no geometry may execute')
    if not pilot.matches(actual, expected):
        raise ValueError('Plan differs from the independently authored expected dimensions')
    return actual


def verify(work):
    manifest = pilot.load(work / 'FROZEN.json')
    if any(pilot.digest(p) != h for p, h in manifest['files'].items()):
        raise ValueError('Native gate source or runtime changed')
    return manifest


def prepare(work, source):
    frozen = pilot.verify(source)
    original = pilot.HERE / 'GeometryHost.cs'
    items = [Path(e.attrib['Include']) for e in ET.parse(source / 'host/GeometryHost.csproj').iter('Compile')]
    if len(items) != 88 or items.count(original) != 1 or any(str(p) not in frozen['files'] for p in items):
        raise ValueError('Expected only the original host and its 87 frozen library sources')
    work.mkdir()
    host = work / 'host'; host.mkdir()
    derived = host / 'GeometryHost.cs'
    needle = '        mesh.SaveToStlFile(args[1], Mesh.EStlUnit.MM);'
    text = original.read_text()
    if text.count(needle) != 1:
        raise ValueError('Frozen host insertion point changed')
    derived.write_text(text.replace(needle, needle + '\n        VdbWitness.SaveAndCheck(solid, lib, args[1] + ".vdb");'))
    items = [derived if p == original else p for p in items] + [HERE / 'VdbWitness.cs']
    compile_items = ''.join('<Compile Include="' + html.escape(str(p)) + '" />' for p in items)
    project = host / 'GeometryHost.csproj'
    project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
                      '<TargetFramework>net9.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
                      '<Nullable>enable</Nullable><EnableDefaultCompileItems>false</EnableDefaultCompileItems>'
                      '</PropertyGroup><ItemGroup>' + compile_items + '<Reference Include="PicoGK"><HintPath>'
                      + html.escape(str(pilot.PICO / 'picogk-bin/PicoGK.dll'))
                      + '</HintPath></Reference></ItemGroup></Project>')
    env = os.environ.copy(); env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
    with (host / 'build.log').open('w') as log:
        subprocess.run([str(pilot.PICO / 'dotnet/dotnet'), 'build', str(project), '-c', 'Release',
                        '-o', str(host / 'bin'), '--nologo', '-v', 'q'], env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    files = dict(frozen['files'])
    for p in [Path(__file__), HERE / 'VdbWitness.cs', derived, project,
              ROOT / 'twins/m64-cylinder-head/source/picogk-local-junction/audit_mesh.py',
              *sorted((host / 'bin').glob('*'))]:
        if p.is_file(): files[str(p)] = pilot.digest(p)
    pilot.save(work / 'FROZEN.json', {'files': files, 'original_preparation_sha256':
               pilot.digest(source / 'dataset/FROZEN.json'), 'limits': 'Synthetic geometry screen only; no manufacturing qualification'})
    verify(work)


def run(work, receipt_path, expected_path, output, voxel):
    verify(work)
    if receipt_path.resolve() == expected_path.resolve():
        raise ValueError('Expected dimensions require a separate authored file')
    output.mkdir()
    report = {'schema': 'qwen-picogk-native-gate/v1', 'manufacturing_qualified': False,
              'geometry_executed': False, 'status': 'rejected', 'voxel_mm': voxel,
              'receipt_sha256': pilot.digest(receipt_path), 'expected_sha256': pilot.digest(expected_path),
              'frozen_sha256': pilot.digest(work / 'FROZEN.json'),
              'expected_dimensions_provenance': 'caller_authored_synthetic_contract',
              'mesh_repairs_applied': False}
    try:
        plan = checked_plan(read(receipt_path), read(expected_path))
        report['plan'] = plan
        report['geometry_executed'] = True
        native = pilot.native(work, plan, output / 'geometry', voxel)
        raw = output / 'geometry/raw.stl'
        auditor = ROOT / 'twins/m64-cylinder-head/source/picogk-local-junction/audit_mesh.py'
        spec = importlib.util.spec_from_file_location('raw_auditor', auditor)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        import numpy
        import trimesh
        mesh = module.topology(trimesh.load_mesh(raw, process=False))
        vdb = pilot.load(Path(str(raw) + '.vdb.json'))
        report.update(native=native, raw_mesh=mesh, vdb=vdb, vdb_sha256=pilot.digest(Path(str(raw) + '.vdb')),
                      numpy_version=numpy.__version__, trimesh_version=trimesh.__version__)
        if native['geometry_screen_passed'] and mesh['strict_raw_mesh_screen_pass'] and vdb['passed']:
            report['status'] = 'accepted_synthetic_geometry'
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    verify(work)
    if pilot.digest(receipt_path) != report['receipt_sha256'] or pilot.digest(expected_path) != report['expected_sha256']:
        raise ValueError('Input changed during validation')
    pilot.save(output / 'report.json', report)
    return report


def self_check():
    pipe = {'recipe': 'pipe', 'parameters_mm': [18, 7, 3], 'missing': []}
    receipt = {'raw_response': json.dumps(pipe), 'plan': {'recipe': 'cylinder'}, 'structure_passed': True}
    assert checked_plan(receipt, pipe) == pipe
    bad = [dict(receipt, structure_passed=False),
           dict(receipt, raw_response='```json\n' + receipt['raw_response'] + '\n```'),
           dict(receipt, raw_response='{"recipe":"pipe","recipe":"pipe","parameters_mm":[18,7,3],"missing":[]}'),
           dict(receipt, raw_response='{"recipe":"pipe","parameters_mm":[18,true,3],"missing":[]}'),
           dict(receipt, raw_response='{"recipe":"pipe","parameters_mm":[18,NaN,3],"missing":[]}'),
           dict(receipt, raw_response='{"recipe":"pipe","parameters_mm":[18,3,7],"missing":[]}'),
           dict(receipt, raw_response='{"recipe":"needs_measurement","parameters_mm":[],"missing":["measured_interfaces"]}'),
           dict(receipt, raw_response='{"recipe":"pipe","parameters_mm":[18,8,3],"missing":[]}')]
    for value in bad:
        try: checked_plan(value, pipe)
        except ValueError: pass
        else: raise AssertionError('Invalid or mismatched plan accepted')
    print('Native gate boundary self-check passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-check', action='store_true'); p.add_argument('--prepare', action='store_true')
    p.add_argument('--work', type=Path); p.add_argument('--source-work', type=Path)
    p.add_argument('--receipt', type=Path); p.add_argument('--expected', type=Path); p.add_argument('--output', type=Path)
    p.add_argument('--voxel-mm', type=float, choices=(0.5, 1.0), default=0.5)
    a = p.parse_args()
    if a.self_check: self_check()
    elif a.prepare:
        if not a.work or not a.source_work: p.error('--work and --source-work required')
        prepare(a.work.resolve(), a.source_work.resolve()); print('Prepared and verified native gate')
    else:
        if not all((a.work, a.receipt, a.expected, a.output)): p.error('--work, --receipt, --expected and --output required')
        r = run(a.work.resolve(), a.receipt, a.expected, a.output, a.voxel_mm)
        print(json.dumps(r, indent=2)); raise SystemExit(0 if r['status'] == 'accepted_synthetic_geometry' else 2)
