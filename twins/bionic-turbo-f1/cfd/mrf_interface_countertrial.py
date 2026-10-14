#!/usr/bin/env python3
"""Move the diagnostic MRF interface outward, preserving geometry and physical inputs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import parallel_restart
import transient_pilot
from prepare_case import IMAGE, sha
from run_case import inspect_mesh
from run_cartesian_pilot import verify


def prepare(parent, output):
    transient_pilot.prepare(parent, output)
    path = output / 'system/topoSetDict'
    content = path.read_text()
    if content.count('radius .032;') != 1:
        raise ValueError('Expected original 32 mm MRF cylinder')
    path.write_text(content.replace('radius .032;', 'radius .038;'))
    mesh = output / 'constant/polyMesh'
    unchanged = {p.name: sha(p) for p in mesh.iterdir() if p.is_file() and p.name != 'cellZones'}
    command = ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/arm64', '--network', 'none',
               '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '128',
               '--cpus', '1', '--memory', '3g', '--tmpfs', '/tmp:rw,nosuid,size=128m',
               '--user', f'{os.getuid()}:{os.getgid()}', '--mount', f'type=bind,source={output.resolve()},target=/case',
               '--entrypoint', '/bin/bash', IMAGE, '-c',
               'source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; exec topoSet']
    with (output / 'log.interface-topoSet').open('x') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300, check=True)
    if any(sha(mesh / name) != digest for name, digest in unchanged.items()):
        raise ValueError('Native zone update changed cell geometry or connectivity')
    manifest = json.loads((output / 'case-manifest.json').read_text())
    topology = inspect_mesh(output, manifest['surface']['boundary_topology'])
    # Fresh cold start: no inherited relative flux requires a reference-frame conversion.
    if (output / '0/phi').exists() or (output / '0/rho').exists():
        raise ValueError('Cold-start primary fields required')
    (output / 'system/decomposeParDict').write_text(
        'FoamFile {version 2.0; format ascii; class dictionary; object decomposeParDict;}\nnumberOfSubdomains 4; method scotch;\n')
    for name in ('system/topoSetDict', 'system/decomposeParDict'):
        manifest['file_sha256'][name] = sha(output / name)
    manifest['rotor_zone']['radius_m'] = .038
    manifest['mrf_interface_countertrial'] = {
        'source_sha256': sha(Path(__file__)), 'parent_radius_m': .032, 'radius_m': .038,
        'hypothesis': 'Cold-cell/high-speed anomaly lies near the 32 mm interface and staircase stator; move the interface into the diffuser to test sensitivity.',
        'operating_conditions_changed': False, 'geometry_changed': False,
        'native_zone_log_sha256': sha(output / 'log.interface-topoSet'),
        'qualification': 'Diagnostic sensitivity only; no mesh, performance or hardware qualification.'}
    manifest['parallel_execution'] = {
        'source_sha256': sha(Path(parallel_restart.__file__)), 'ranks': 4, 'method': 'scotch',
        'saved_field_interval': 20, 'equations_changed': False}
    (output / 'case-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    proof = json.loads((output / 'cartesian-proof.json').read_text())
    proof['case_manifest_sha256'] = sha(output / 'case-manifest.json')
    proof['mesh'] = topology
    proof['derivation']['interface_countertrial_source_sha256'] = sha(Path(__file__))
    proof['derivation']['geometry_connectivity_byte_identical'] = unchanged
    (output / 'cartesian-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    verify(output)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(parallel_restart.launch(Path(sys.argv[2]))))
