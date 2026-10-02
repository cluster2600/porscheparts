#!/usr/bin/env python3
"""Screen the reconstructed Turbo rotor using the existing LPBF geometry kernel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import runpy
import sys

import trimesh

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry', type=Path, help='PicoGK reference output directory')
    parser.add_argument('output', type=Path, help='New analysis directory; must not exist')
    args = parser.parse_args()
    source = args.geometry.resolve() / 'rotor-mm.stl'
    mesh = trimesh.load_mesh(source, process=True)
    if not mesh.is_watertight or mesh.body_count != 1 or mesh.volume <= 0:
        raise ValueError('Reference rotor must be a positive closed single solid')
    args.output.mkdir(parents=True, exist_ok=False)
    surface = args.output.resolve() / 'rotor-analysis.stl'
    mesh.simplify_quadric_decimation(face_count=50000).export(surface)
    analysis = trimesh.load_mesh(surface, process=True)
    error = abs(analysis.volume / mesh.volume - 1)
    if not analysis.is_watertight or analysis.body_count != 1 or error >= 0.002:
        raise ValueError('Reduction failed topology/volume checks; no screen released')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (args.output / 'inputs.json').write_text(json.dumps({
        'source_sha256': sha(source), 'surface_sha256': sha(surface),
        'relative_volume_error': error, 'raw_volume_mm3': mesh.volume,
        'analysis_volume_mm3': analysis.volume,
        'scope': 'Visual reconstruction only; no dimensional or print authorization',
    }, indent=2) + '\n')
    subprocess.run([
        sys.executable, str(ROOT / 'scripts/run_metal_am_geometry_screen.py'),
        '--part-id', '993-TURBO-FAN-REFERENCE',
        '--master', str(source), '--master-sha256', sha(source),
        '--surface', str(surface), '--surface-sha256', sha(surface),
        '--machine-card', str(ROOT / 'catalog/manufacturing/machines/zrapid-islm420dn.json'),
        '--material', 'AlSi10Mg candidate, supplier-qualified process unavailable',
        '--expected-envelope-mm', *map(str, analysis.extents),
        '--layer-thickness-mm', '0.05', '--voxel-pitch-mm', '1',
        '--output', str(args.output.resolve() / 'screen'),
    ], check=True)
    shared = runpy.run_path(str(ROOT / 'scripts/run_metal_am_geometry_screen.py'))
    kernel = shared['load_kernel']()
    kernel.MACHINE = json.loads((ROOT / 'catalog/manufacturing/machines/zrapid-islm420dn.json').read_text())
    kernel.LAYER_MM = 0.05
    kernel.machine_fit = lambda extents: shared['machine_fit'](kernel.MACHINE, extents)
    rows, flat = kernel.slice_build(analysis, 'build_z')
    shared['write_rows'](args.output / 'screen/flat-layer-metrics.csv', rows)
    (args.output / 'screen/flat-slicing.json').write_text(json.dumps(flat, indent=2) + '\n')


if __name__ == '__main__':
    main()
