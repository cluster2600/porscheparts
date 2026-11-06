"""Find continuous axial tunnel-core pull collision witnesses in assumed CAD.

The counterexample tests only rigid +/-X translations of tools containing the
declared centreline points. It neither designs a core nor qualifies a mould.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from geometry import evaluate, parameter_at_x


def height_root(surface, profile_v, height, low, high):
    def value(u):
        return float(evaluate(surface, u, profile_v)[2]-height)
    fa, fb = value(low), value(high)
    if fa*fb >= 0:
        raise ValueError('A signed, interior collision bracket is required')
    for _ in range(64):
        middle = (low+high)/2
        fm = value(middle)
        if fa*fm <= 0:
            high, fb = middle, fm
        else:
            low, fa = middle, fm
    parameter = (low+high)/2
    point = evaluate(surface, parameter, profile_v)
    return point, abs(value(parameter))


def screen(model):
    if model['status'] != 'assumed' or model['units'] != 'mm' or model['physical_interfaces_admitted']:
        raise ValueError('Require the independent hypothetical design frame')
    components = {c['name']: c for c in model['components']}
    roof, lower = components['integrated_tunnel'], components['tunnel_lower_return']
    witnesses = []
    for direction, start_x, wall, profile_v in [(1, 350., lower, 1.5), (-1, 1750., roof, 7.)]:
        u = parameter_at_x(roof, start_x)
        roof_point, lower_point = evaluate(roof, u, 7), evaluate(lower, u, 1.5)
        point = .5*(roof_point+lower_point)
        if not lower_point[2] < point[2] < roof_point[2] or abs(point[1]) > 1e-9:
            raise ValueError('Centreline witness is not between the authored tunnel surfaces')
        end = float(len(wall['sections_mm'])-1)
        collision, residual = height_root(wall, profile_v, point[2], u if direction > 0 else 0., end if direction > 0 else u)
        shift = float(collision[0]-point[0])
        translated = point+np.array([shift, 0, 0])
        if direction*shift <= 0 or np.linalg.norm(translated-collision) > 1e-7:
            raise ValueError('Collision is not on the declared rigid translation')
        witnesses.append({'direction': '+X' if direction > 0 else '-X',
                          'initial_core_point_mm': point.tolist(), 'wall_component': wall['name'],
                          'collision_point_mm': collision.tolist(),
                          'collision_witness_translation_mm': shift, 'height_root_residual_mm': residual,
                          'is_first_collision': False, 'prescribed_axial_pull_rejected': True})
    return witnesses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output path')
    raw = args.model.read_bytes()
    result = {'classification': 'continuous_canonical_midplane_axial_core_pull_counterexamples',
              'canonical_model_sha256': hashlib.sha256(raw).hexdigest(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'pull_witnesses': screen(json.loads(raw)),
              'scope': 'Any rigid tool containing these declared tunnel centreline points collides during these prescribed pure-X pulls. Witnesses are not first-contact results.',
              'core_initial_solid_clearance_verified': False,
              'other_directions_rotations_segmentation_or_processes_evaluated': False,
              'mould_geometry_created': False, 'drape_cure_or_manufacturing_simulation_completed': False,
              'physical_or_manufacturing_validation': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
