"""Retessellate a hash-bound carrier STEP with the installed native Gmsh CAD kernel."""
import argparse
import hashlib
import json
from pathlib import Path

import re


def identity_step_sha256(receipt):
    record = json.loads(Path(receipt).read_text())
    geometry = record.get('geometry_sha256') if isinstance(record, dict) else None
    value = geometry.get('carrier.step') if isinstance(geometry, dict) else None
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('Identity receipt requires geometry_sha256["carrier.step"]')
    return value


def run(source, output, expected_sha256, minimum_size_mm=.5):
    import gmsh
    source, output = Path(source), Path(output)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('STEP differs from the declared frozen source hash')
    output.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 2)
        gmsh.option.setNumber('Mesh.MeshSizeMin', minimum_size_mm)
        gmsh.option.setNumber('Mesh.MeshSizeMax', 3)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 96)
        gmsh.option.setNumber('Mesh.Algorithm', 6)
        gmsh.option.setNumber('Mesh.ElementOrder', 1)
        gmsh.option.setNumber('Mesh.Smoothing', 0)
        gmsh.option.setNumber('Mesh.Binary', 1)
        gmsh.model.occ.importShapes(str(source))
        gmsh.model.occ.synchronize()
        if len(gmsh.model.getEntities(3)) != 1:
            raise ValueError('One unchanged source solid required')
        gmsh.model.mesh.generate(2)
        gmsh.write(str(output / 'carrier-remeshed.stl'))
        gmsh.write(str(output / 'carrier-remeshed.msh'))
        result = {'source_STEP_sha256': digest, 'gmsh_version': gmsh.__version__,
                  'candidate_STL_sha256': hashlib.sha256((output / 'carrier-remeshed.stl').read_bytes()).hexdigest(),
                  'candidate_STL': 'carrier-remeshed.stl',
                  'options': {'MeshSizeMin': minimum_size_mm, 'MeshSizeMax': 3, 'MeshSizeFromCurvature': 96,
                              'Algorithm': 6, 'ElementOrder': 1, 'Smoothing': 0},
                  'source_CAD_changed': False,
                  'worker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'manufacturing_authorized': False}
        (output / 'meshing.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
    finally:
        gmsh.finalize()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--expected-step-sha256')
    identity.add_argument('--identity-receipt', type=Path)
    parser.add_argument('--minimum-size-mm', type=float, choices=(.5, .25), default=.5,
                        help='Frozen recipe minimum: 0.25 resolves the new R0.5 window corners')
    args = parser.parse_args()
    expected = identity_step_sha256(args.identity_receipt) if args.identity_receipt else args.expected_step_sha256
    run(args.source, args.output, expected, args.minimum_size_mm)
