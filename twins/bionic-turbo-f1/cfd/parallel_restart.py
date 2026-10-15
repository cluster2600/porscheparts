#!/usr/bin/env python3
"""Run the complete local-time restart on four native MPI ranks with retained outputs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import lts_restart_complete
from prepare_case import IMAGE, sha
from run_cartesian_pilot import verify
from transient_pilot import SUPERVISOR, ENTRYPOINT


def prepare(parent, output):
    lts_restart_complete.prepare(parent, output)
    decomposition = 'FoamFile {version 2.0; format ascii; class dictionary; object decomposeParDict;}\nnumberOfSubdomains 4; method scotch;\n'
    (output / 'system/decomposeParDict').write_text(decomposition)
    path = output / 'system/controlDict'
    content = path.read_text()
    if content.count('writeInterval 20;') != 1:
        raise ValueError('Expected original field-save interval')
    path.write_text(content.replace('writeInterval 20;', 'writeInterval 100;'))
    manifest = json.loads((output / 'case-manifest.json').read_text())
    for name in ('system/controlDict', 'system/decomposeParDict'):
        manifest['file_sha256'][name] = sha(output / name)
    manifest['parallel_execution'] = {'source_sha256': sha(Path(__file__)), 'ranks': 4, 'method': 'scotch',
                                      'saved_field_interval': 100, 'equations_changed': False,
                                      'reason': 'Serial native solver uses one CPU; bounded four-rank execution advances the same equations faster.'}
    (output / 'case-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    proof = json.loads((output / 'cartesian-proof.json').read_text())
    proof['case_manifest_sha256'] = sha(output / 'case-manifest.json')
    proof['derivation']['parallel_source_sha256'] = sha(Path(__file__))
    (output / 'cartesian-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    verify(output)


def launch(case):
    case = case.resolve()
    hashes = verify(case)
    manifest = json.loads((case / 'case-manifest.json').read_text())
    if manifest.get('parallel_execution', {}).get('source_sha256') != sha(Path(__file__)):
        raise ValueError('Current parallel preparation required')
    if (case / 'launch-parallel.json').exists() or (case / 'postProcessing').exists() or list(case.glob('processor*')):
        raise ValueError('Fresh parallel case required')
    script = SUPERVISOR.replace('stdbuf -oL -eL rhoPimpleFoam', 'decomposePar > log.decomposePar 2>&1 || exit 91\nstdbuf -oL -eL mpirun -np 4 rhoPimpleFoam -parallel')
    script = script.replace('exit "$code"', 'if [ "$code" -eq 0 ]; then\n    reconstructPar -latestTime > log.reconstructPar 2>&1 || code=92\nfi\nexit "$code"')
    with (case / 'transient-supervisor.sh').open('x') as f:
        f.write(script)
    container = 'bionic-parallel-' + uuid.uuid4().hex[:12]
    report = {'status': 'launch_requested', 'container': container, 'image': IMAGE,
              'input_sha256': hashes, 'source_sha256': sha(Path(__file__)),
              'supervisor_sha256': sha(case / 'transient-supervisor.sh'), 'ranks': 4,
              'cpus': 4, 'memory_gb': 7, 'timeout_seconds': 7200, 'performance_ranking_authorized': False}
    receipt = case / 'launch-parallel.json'
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    result = subprocess.run(['docker','run','-d','--pull=never','--platform','linux/arm64','--network','none',
        '--read-only','--name',container,'--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','256',
        '--cpus','4','--memory','7g','--shm-size','256m','--tmpfs','/tmp:rw,nosuid,size=256m',
        '--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case},target=/case',
        '--entrypoint','/bin/bash',IMAGE,'-c',ENTRYPOINT],capture_output=True,text=True,timeout=60)
    report.update(status='launched' if result.returncode == 0 else 'launch_failed',container_id=result.stdout.strip(),launch_error=result.stderr.strip())
    receipt.write_text(json.dumps(report,indent=2)+'\n')
    if result.returncode:
        raise RuntimeError(result.stderr)
    return report


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(launch(Path(sys.argv[2]))))
