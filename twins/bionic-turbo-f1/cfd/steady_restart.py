#!/usr/bin/env python3
"""Continue a completed transient startup with conservative steady convection."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from prepare_case import IMAGE, sha
from run_cartesian_pilot import verify
from transient_pilot import SUPERVISOR, ENTRYPOINT


def prepare(parent, output):
    hashes = verify(parent)
    completion = parent / 'native-exit.json'
    if json.loads(completion.read_text()).get('exit_code') != 0 or not (parent / 'log.transient-rhoPimpleFoam').read_text().rstrip().endswith('End'):
        raise ValueError('Completed native transient required')
    seed = max((p for p in parent.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name)), key=lambda p: float(p.name))
    if float(seed.name) <= 0:
        raise ValueError('Saved positive-time fields required')
    manifest = json.loads((parent / 'case-manifest.json').read_text())
    proof = json.loads((parent / 'cartesian-proof.json').read_text())
    output.mkdir(parents=True, exist_ok=False)
    for name in manifest['file_sha256'] | proof['mesh']['mesh_sha256']:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(parent / name, target)
        if sha(target) != hashes[name]:
            raise ValueError('Input copy changed')
    seed_hashes = {}
    for name in ('U', 'p', 'T', 'k', 'omega', 'nut', 'alphat'):
        source = seed / name
        seed_hashes[str(source.relative_to(parent))] = sha(source)
        shutil.copyfile(source, output / '0' / name)
        manifest['file_sha256']['0/' + name] = sha(output / '0' / name)
        if manifest['file_sha256']['0/' + name] != seed_hashes[str(source.relative_to(parent))]:
            raise ValueError('Seed copy changed')
    scheme = output / 'system/fvSchemes'
    content = scheme.read_text()
    if content.count('default Euler;') != 1:
        raise ValueError('Expected transient Euler input')
    content = content.replace('default Euler;', 'default steadyState;')
    for field in ('U', 'h', 'K', 'k', 'omega'):
        content = content.replace(f'div(phi,{field}) Gauss upwind;', f'div(phi,{field}) bounded Gauss upwind;')
    scheme.write_text(content)
    control = output / 'system/controlDict'
    content = control.read_text().replace('application rhoPimpleFoam;', 'application rhoSimpleFoam;')
    old = 'endTime 0.00002; deltaT 1e-8;\nadjustTimeStep yes; maxCo 0.3; maxDeltaT 1e-7;'
    if content.count(old) != 1:
        raise ValueError('Unexpected transient controls')
    control.write_text(content.replace(old, 'endTime 400; deltaT 1;'))
    (output / 'system/fvSolution').write_text('''FoamFile {version 2.0; format ascii; class dictionary; object fvSolution;}
solvers {
 p {solver GAMG; smoother GaussSeidel; scaleCorrection false; tolerance 1e-8; relTol .01;}
 "(U|k|omega|h)" {solver PBiCGStab; preconditioner DILU; tolerance 1e-9; relTol .05;}
}
SIMPLE {nNonOrthogonalCorrectors 2; consistent no; transonic yes;}
relaxationFactors {fields {p .1; rho .1;} equations {U .2; h .2; "(k|omega)" .2;}}
''')
    for name in ('system/controlDict', 'system/fvSchemes', 'system/fvSolution'):
        manifest['file_sha256'][name] = sha(output / name)
    manifest['steady_iterations'] = 400
    manifest['steady_restart'] = {'source_sha256': sha(Path(__file__)), 'parent_manifest_sha256': hashes['case-manifest.json'],
                                 'seed_time_s': float(seed.name), 'seed_field_sha256': seed_hashes,
                                 'parent_completion_sha256': sha(completion),
                                 'change': 'Native saved initial fields; bounded upwind steady convection; enthalpy relaxation 0.2.',
                                 'operating_conditions_changed': False, 'performance_ranking_authorized': False}
    (output / 'case-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    proof['case_manifest_sha256'] = sha(output / 'case-manifest.json')
    proof['derivation'] = {'source_sha256': sha(Path(__file__)), 'parent_proof_sha256': hashes['cartesian-proof.json'], 'method': 'Exact mesh and boundary conditions; saved transient initial state and steady numerics.'}
    (output / 'cartesian-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    if any(sha(parent / name) != digest for name, digest in (hashes | seed_hashes).items()):
        raise ValueError('Parent changed while preparing')
    verify(output)


def launch(case):
    case = case.resolve()
    hashes = verify(case)
    manifest = json.loads((case / 'case-manifest.json').read_text())
    if manifest.get('steady_restart', {}).get('source_sha256') != sha(Path(__file__)):
        raise ValueError('Current restart preparation required')
    if (case / 'postProcessing').exists() or (case / 'launch-steady.json').exists() or any(p.name != '0' and p.name[:1].isdigit() for p in case.iterdir()):
        raise ValueError('Fresh case required')
    # Reuse the frozen, tested in-container watchdog and terminal-receipt protocol.
    supervisor = SUPERVISOR.replace('rhoPimpleFoam', 'rhoSimpleFoam')
    entrypoint = ENTRYPOINT.replace('rhoPimpleFoam', 'rhoSimpleFoam')
    with (case / 'transient-supervisor.sh').open('x') as f:
        f.write(supervisor)
    container = 'bionic-steady-' + uuid.uuid4().hex[:12]
    report = {'status': 'launch_requested', 'container': container, 'image': IMAGE, 'input_sha256': hashes,
              'source_sha256': sha(Path(__file__)), 'supervisor_sha256': sha(case / 'transient-supervisor.sh'),
              'timeout_seconds': 7200, 'cpus': 2, 'memory_gb': 6, 'performance_ranking_authorized': False}
    receipt = case / 'launch-steady.json'
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    result = subprocess.run(['docker', 'run', '-d', '--pull=never', '--platform', 'linux/arm64', '--network', 'none',
        '--read-only', '--name', container, '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '256',
        '--cpus', '2', '--memory', '6g', '--tmpfs', '/tmp:rw,nosuid,size=256m', '--user', f'{os.getuid()}:{os.getgid()}',
        '--mount', f'type=bind,source={case},target=/case', '--entrypoint', '/bin/bash', IMAGE, '-c', entrypoint],
        capture_output=True, text=True, timeout=60)
    report.update(status='launched' if result.returncode == 0 else 'launch_failed', container_id=result.stdout.strip(), launch_error=result.stderr.strip())
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(result.stderr)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'launch'))
    parser.add_argument('case', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.output is None:
            parser.error('Output required')
        prepare(args.case, args.output)
        print('Fresh steady restart prepared; performance remains unqualified.')
    else:
        print(json.dumps(launch(args.case)))
