#!/usr/bin/env python3
"""Use local pseudo-time stepping to seek a steady state without claiming physical time."""
import json
from pathlib import Path
import sys

import steady_restart
import transient_pilot
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    steady_restart.prepare(parent, output)
    # Keep the stable PIMPLE formulation; the failed direct SIMPLE restart remains separate.
    (output / 'system/fvSolution').write_bytes((parent / 'system/fvSolution').read_bytes())
    path = output / 'system/fvSolution'
    content = path.read_text()
    if content.count('PIMPLE {') != 1:
        raise ValueError('Expected parent PIMPLE controls')
    path.write_text(content.replace('PIMPLE {', 'PIMPLE {maxCo 0.8; maxDeltaT 1e-6; rDeltaTSmoothingCoeff 0.02; rDeltaTDampingCoeff 0.2;'))
    path = output / 'system/fvSchemes'
    content = path.read_text().replace('default steadyState;', 'default localEuler;').replace('bounded Gauss upwind', 'Gauss upwind')
    path.write_text(content)
    path = output / 'system/controlDict'
    content = path.read_text().replace('application rhoSimpleFoam;', 'application rhoPimpleFoam;').replace('endTime 400;', 'endTime 600;')
    path.write_text(content)
    manifest = json.loads((output / 'case-manifest.json').read_text())
    for name in ('system/controlDict', 'system/fvSchemes', 'system/fvSolution'):
        manifest['file_sha256'][name] = sha(output / name)
    manifest['solver'] = 'rhoPimpleFoam'
    manifest['steady_iterations'] = 600
    manifest['active_solve'] = {'solver': 'rhoPimpleFoam', 'time_semantics': 'local_pseudo_time_iterations_not_seconds',
                              'source_sha256': sha(Path(__file__)), 'max_local_courant': 0.8,
                              'max_local_step_s': 1e-6, 'iterations': 600,
                              'source_url': 'https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoPimpleFoam/setRDeltaT.H',
                              'performance_ranking_authorized': False}
    manifest['transient_diagnostic']['superseded_by'] = 'active_solve: local pseudo-time; original physical end time no longer applies'
    (output / 'case-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    proof = json.loads((output / 'cartesian-proof.json').read_text())
    proof['case_manifest_sha256'] = sha(output / 'case-manifest.json')
    proof['derivation']['local_pseudo_time_source_sha256'] = sha(Path(__file__))
    (output / 'cartesian-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    verify(output)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(transient_pilot.launch(Path(sys.argv[2]))))
