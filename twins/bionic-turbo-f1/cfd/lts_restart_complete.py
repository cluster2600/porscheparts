#!/usr/bin/env python3
"""Restore native relative mass flux and density instead of reconstructing absolute flux."""
import json
from pathlib import Path
import shutil
import sys

import lts_restart
import transient_pilot
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    lts_restart.prepare(parent, output)
    manifest = json.loads((output / 'case-manifest.json').read_text())
    seeds = manifest['steady_restart']['seed_field_sha256']
    checkpoint = next(iter(seeds)).split('/')[0]
    for name in ('phi', 'rho'):
        source = parent / checkpoint / name
        before = sha(source)
        shutil.copyfile(source, output / '0' / name)
        if before != sha(source) or before != sha(output / '0' / name):
            raise ValueError('Restart flux/density changed during copy')
        seeds[checkpoint + '/' + name] = before
        manifest['file_sha256']['0/' + name] = before
    manifest['complete_restart'] = {
        'source_sha256': sha(Path(__file__)),
        'change': 'Restore native relative phi and transported rho as well as all seven primary/turbulence fields.',
        'reason': 'compressibleCreatePhi.H otherwise computes absolute interpolate(rho*U).Sf; this is not the saved MRF flux.',
        'source_url': 'https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/src/finiteVolume/cfdTools/compressible/compressibleCreatePhi.H',
        'operating_conditions_changed': False}
    (output / 'case-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    proof = json.loads((output / 'cartesian-proof.json').read_text())
    proof['case_manifest_sha256'] = sha(output / 'case-manifest.json')
    proof['derivation']['complete_restart_source_sha256'] = sha(Path(__file__))
    (output / 'cartesian-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    verify(output)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(transient_pilot.launch(Path(sys.argv[2]))))
