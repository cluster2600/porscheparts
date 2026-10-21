"""Check qualified typed plans and native exports without rewriting the legacy gate."""
import argparse
import html
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate as legacy

ROOT, HERE, pilot = legacy.ROOT, legacy.HERE, legacy.pilot
spec = importlib.util.spec_from_file_location('qualified_request_contract', ROOT/'training/qwen-picogk-qualified-20261014/request_contract.py')
contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


def checked_plan(receipt, expected, request, request_sha256, manifest):
    if not isinstance(receipt, dict) or any(receipt.get(k) is not v for k, v in
            (('semantic_intent_verified', True), ('model_called', True),
             ('geometry_executed', False), ('manufacturing_qualified', False))):
        raise ValueError('A qualified typed-plan receipt without prior geometry is required')
    for key, expected_hash in (('profile_sha256', manifest['qualified_profile_sha256']),
                               ('adapter_sha256', manifest['adapter_sha256']),
                               ('request_sha256', request_sha256)):
        if receipt.get(key) != expected_hash:
            raise ValueError('Qualified receipt identity differs: ' + key)
    actual = pilot.parse(json.dumps(receipt.get('plan'), allow_nan=False))
    expected = pilot.parse(json.dumps(expected, allow_nan=False))
    requested = contract.normalize(request)
    if actual['missing'] or expected['missing'] or requested['missing']:
        raise ValueError('Measured interfaces are missing; no geometry may execute')
    if not pilot.matches(actual, expected) or not pilot.matches(requested, expected):
        raise ValueError('Plan or request differs from the independently authored expected dimensions')
    return actual


def prepare(work, old_work, libraries, profile):
    historical = pilot.load(HERE/'results.json')
    old_manifest = old_work/'FROZEN.json'
    if pilot.digest(old_manifest) != historical['frozen_manifest_sha256']:
        raise ValueError('Historical native manifest differs from its published digest')
    bindings = pilot.load(old_manifest)['files']
    published = pilot.load(ROOT/'training/qwen-picogk-qualified-20261014/results-002.json')
    config = legacy.read(profile)
    if (published.get('eligible') is not True or config.get('schema') != 'qwen.picogk.qualified-profile@1'
            or config.get('adapter_sha256') != published['adapter_sha256']
            or config.get('results_sha256') != published['private_receipt_sha256']['results.json']
            or config.get('frozen_sha256') != published['private_receipt_sha256']['FROZEN.json']):
        raise ValueError('Profile differs from the published qualified continuation')
    sources = []
    for repository, folders in [('LEAP71_ShapeKernel', ['ShapeKernel']),
                               ('LEAP71_LatticeLibrary', ['LatticeLibrary', 'ImplicitLibrary']),
                               ('LEAP71_HelixHeatX', ['src'])]:
        for folder in folders:
            sources += sorted((libraries/repository/folder).rglob('*.cs'))
    sources += [libraries/'PicoGK-Fasteners'/name for name in ('FastenerTools.cs', 'FastenerUtils.cs')]
    if len(sources) != 87 or len(set(sources)) != 87:
        raise ValueError('Expected exactly 87 trusted library sources')
    for source in sources:
        suffix = '/sources/' + source.relative_to(libraries).as_posix()
        expected = {digest for name, digest in bindings.items() if name.endswith(suffix)}
        if len(expected) != 1 or pilot.digest(source) != next(iter(expected)):
            raise ValueError('Native source has no byte-identical historical binding: ' + source.name)
    original = pilot.HERE/'GeometryHost.cs'
    expected = {digest for name, digest in bindings.items()
                if name.endswith('/training/qwen-picogk-20261012/GeometryHost.cs')}
    if len(expected) != 1 or pilot.digest(original) != next(iter(expected)):
        raise ValueError('Trusted recipe source changed')
    runtime = [pilot.PICO/'picogk-bin'/name for name in ('PicoGK.dll', 'picogk.26.2.dylib')]
    for path in runtime:
        if pilot.digest(path) != bindings.get(str(path)):
            raise ValueError('Native runtime differs from historical bytes')
    before = {p: pilot.digest(p) for p in sources + runtime + [original, profile, old_manifest]}
    work.mkdir(); host = work/'host'; host.mkdir()
    needle = '        mesh.SaveToStlFile(args[1], Mesh.EStlUnit.MM);'
    text = original.read_text()
    if text.count(needle) != 1:
        raise ValueError('Trusted host insertion point changed')
    derived = host/'GeometryHost.cs'
    derived.write_text(text.replace(needle, needle + '\n        VdbWitness.SaveAndCheck(solid, lib, args[1] + ".vdb");'))
    sources += [derived, HERE/'VdbWitness.cs']
    items = ''.join('<Compile Include="' + html.escape(str(p)) + '" />' for p in sources)
    project = host/'GeometryHost.csproj'
    project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
                       '<TargetFramework>net9.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
                       '<Nullable>enable</Nullable><EnableDefaultCompileItems>false</EnableDefaultCompileItems>'
                       '</PropertyGroup><ItemGroup>' + items + '<Reference Include="PicoGK"><HintPath>'
                       + html.escape(str(runtime[0])) + '</HintPath></Reference></ItemGroup></Project>')
    env = os.environ.copy(); env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
    with (host/'build.log').open('w') as log:
        subprocess.run([str(pilot.PICO/'dotnet/dotnet'), 'build', str(project), '-c', 'Release',
                        '-o', str(host/'bin'), '--nologo', '-v', 'q'], env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    if any(pilot.digest(p) != digest for p, digest in before.items()):
        raise ValueError('Native preparation input changed during compilation')
    code = [p for folder in ('qwen-picogk-native-gate', 'qwen-picogk-20261012', 'qwen-research-corpus',
                             'qwen-porsche-corpus', 'qwen-engineering-20261002', 'm64-qwen', 'm64-engineer')
            for p in (ROOT/'training'/folder).glob('*.py')]
    files = sources + code + runtime + [original, project, old_manifest, profile, Path(contract.__file__),
             ROOT/'training/qwen-picogk-qualified-20261014/results-002.json', pilot.PICO/'dotnet/dotnet',
             ROOT/'twins/m64-cylinder-head/source/picogk-local-junction/audit_mesh.py',
             *sorted((host/'bin').glob('*'))]
    pilot.save(work/'FROZEN.json', dict(files={str(p): pilot.digest(p) for p in files if p.is_file()},
               qualified_profile_sha256=pilot.digest(profile), adapter_sha256=config['adapter_sha256'],
               historical_native_manifest_sha256=pilot.digest(old_manifest),
               historical_training_reproduced=False, scope='Native-only recovery with byte-identical library aliases; typed receipt geometry screen'))
    legacy.verify(work)


def run(work, receipt_path, expected_path, request_path, output, voxel):
    manifest = legacy.verify(work)
    if len({p.resolve() for p in (receipt_path, expected_path, request_path)}) != 3:
        raise ValueError('Receipt, request and independent expected plan require separate files')
    output.mkdir()
    paths = dict(receipt=receipt_path, expected=expected_path, request=request_path)
    report = dict(schema='qwen-picogk-qualified-native-gate/v1', status='rejected',
                  geometry_executed=False, manufacturing_qualified=False, mesh_repairs_applied=False,
                  receipt_kind='qualified_typed_plan', original_model_text_available=False,
                  input_sha256={k: pilot.digest(p) for k, p in paths.items()},
                  frozen_sha256=pilot.digest(work/'FROZEN.json'), voxel_mm=voxel)
    try:
        plan = checked_plan(*(legacy.read(paths[k]) for k in ('receipt', 'expected', 'request')),
                            report['input_sha256']['request'], manifest)
        report.update(plan=plan, geometry_executed=True)
        native = pilot.native(work, plan, output/'geometry', voxel)
        raw = output/'geometry/raw.stl'
        spec = importlib.util.spec_from_file_location('raw_auditor', ROOT/'twins/m64-cylinder-head/source/picogk-local-junction/audit_mesh.py')
        auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
        import numpy
        import trimesh
        mesh = auditor.topology(trimesh.load_mesh(raw, process=False))
        vdb = pilot.load(Path(str(raw) + '.vdb.json'))
        report.update(native=native, raw_mesh=mesh, vdb=vdb, vdb_sha256=pilot.digest(Path(str(raw) + '.vdb')),
                      numpy_version=numpy.__version__, trimesh_version=trimesh.__version__)
        if native['geometry_screen_passed'] and mesh['strict_raw_mesh_screen_pass'] and vdb['passed']:
            report['status'] = 'accepted_synthetic_geometry'
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    legacy.verify(work)
    if any(pilot.digest(p) != report['input_sha256'][k] for k, p in paths.items()):
        raise ValueError('Input changed during validation')
    pilot.save(output/'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    for name in ('work', 'legacy-work', 'libraries', 'profile', 'receipt', 'expected', 'request', 'output'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--voxel-mm', type=float, choices=(0.5, 1.0), default=0.5)
    args = parser.parse_args()
    if not args.work:
        parser.error('--work is required')
    if args.prepare:
        if not all((args.legacy_work, args.libraries, args.profile)):
            parser.error('--legacy-work, --libraries and --profile are required')
        prepare(*(p.resolve() for p in (args.work, args.legacy_work, args.libraries, args.profile)))
    else:
        if not all((args.receipt, args.expected, args.request, args.output)):
            parser.error('--receipt, --expected, --request and --output are required')
        report = run(*(p.resolve() for p in (args.work, args.receipt, args.expected, args.request, args.output)), args.voxel_mm)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report['status'] == 'accepted_synthetic_geometry' else 2)
