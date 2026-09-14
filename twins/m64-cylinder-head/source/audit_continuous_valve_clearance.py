#!/usr/bin/env python3
"""Bound pairwise valve clearance between samples; not a hot engine validation."""
import argparse
import itertools
import json
import math
from pathlib import Path
import resource

import build_four_valve_distribution as design


def lift_grid(max_lift, maximum_step):
    if not all(math.isfinite(v) and v > 0 for v in (max_lift, maximum_step)):
        raise ValueError('finite positive lift and step required')
    intervals = math.ceil(max_lift / maximum_step)
    if intervals > 100:
        raise ValueError('more than 100 intervals refused')
    return [max_lift * i / intervals for i in range(intervals + 1)]


def covering_radius(grid):
    if len(grid) < 2 or any(not math.isfinite(v) for v in grid):
        raise ValueError('finite grid with two endpoints required')
    if any(b <= a for a, b in zip(grid, grid[1:])):
        raise ValueError('strictly increasing grid required')
    return max(b - a for a, b in zip(grid, grid[1:])) / 2


def clearance_bound(sample_minimum, first_grid, second_grid, numerical_allowance):
    if not math.isfinite(sample_minimum) or sample_minimum < 0:
        raise ValueError('invalid sampled distance')
    if not math.isfinite(numerical_allowance) or numerical_allowance < 0:
        raise ValueError('invalid numerical allowance')
    return (sample_minimum - covering_radius(first_grid)
            - covering_radius(second_grid) - numerical_allowance)


def run(directory, maximum_step, numerical_allowance):
    build_path = directory / 'build-report.json'
    build = json.loads(build_path.read_text())
    step_path = directory / 'closed.step'
    if design.sha(step_path) != build['closed_step']['sha256']:
        raise ValueError('STEP hash does not match build receipt')
    p = design.Parameters(**build['parameters']).validate()
    cad = design.CAD()
    imported = cad.read_step(step_path)
    if not cad.valid(imported):
        raise ValueError('invalid imported STEP')
    solids = cad.indexed(imported, cad.TopAbs_SOLID)
    if solids.Extent() != 12:
        raise ValueError('expected twelve STEP solids')
    actual = [solids.FindKey(i) for i in range(1, 13)]
    used = set()
    moving = []
    # Identify actual imported valve solids by native volumetric equivalence,
    # not by the order of solids in a STEP file or visual resemblance.
    for spec in design.valve_specs(p):
        profiles, _ = design.profiles(p, spec)
        expected = cad.pose(cad.revolve(profiles['valve']), spec)
        matches = []
        for index, candidate in enumerate(actual):
            if index in used:
                continue
            if abs(cad.volume(candidate) - cad.volume(expected)) > 1e-5:
                continue
            common = cad.operation(cad.BRepAlgoAPI_Common, candidate, expected)
            symmetric_difference = (cad.volume(candidate) + cad.volume(expected)
                                    - 2 * cad.volume(common))
            if abs(symmetric_difference) <= 1e-7:
                matches.append((index, symmetric_difference))
        if len(matches) != 1:
            raise ValueError('imported valve identification ambiguous or failed')
        index, difference = matches[0]
        used.add(index)
        grid = lift_grid(spec['max_lift_mm'], maximum_step)
        poses = []
        angle = math.radians(spec['axis_angle_deg'])
        for lift in grid:
            transform = cad.gp_Trsf()
            transform.SetTranslation(cad.gp_Vec(-lift * math.sin(angle), 0,
                                               -lift * math.cos(angle)))
            poses.append(cad.BRepBuilderAPI_Transform(actual[index], transform, True).Shape())
        moving.append({'spec': spec, 'grid': grid, 'poses': poses,
                       'STEP_solid_index': index + 1,
                       'identification_difference_mm3': difference})
    pairs = []
    for a, b in itertools.combinations(moving, 2):
        samples = []
        for ia, first in enumerate(a['poses']):
            for ib, second in enumerate(b['poses']):
                distance = cad.distance(first, second)
                if not math.isfinite(distance) or distance < 0:
                    raise ValueError('invalid native distance')
                samples.append([a['grid'][ia], b['grid'][ib], distance])
        minimum = min(samples, key=lambda row: row[2])
        bound = clearance_bound(minimum[2], a['grid'], b['grid'], numerical_allowance)
        record = {'first': a['spec']['name'], 'second': b['spec']['name'],
                  'samples_columns': ['first_lift_mm', 'second_lift_mm', 'native_gap_mm'],
                  'samples': samples, 'sample_minimum': minimum,
                  'first_covering_radius_mm': covering_radius(a['grid']),
                  'second_covering_radius_mm': covering_radius(b['grid']),
                  'continuous_lower_bound_mm': bound,
                  'positive_bound_under_numerical_assumption': bound > 0}
        pairs.append(record)
        print(json.dumps({k: v for k, v in record.items() if k != 'samples'}), flush=True)
    return {
        'schema': 'm64-continuous-valve-pair-clearance/v1',
        'STEP_sha256': design.sha(step_path), 'build_report_sha256': design.sha(build_path),
        'audit_source_sha256': design.sha(Path(__file__)),
        'design_source_sha256': design.sha(Path(design.__file__)),
        'length_unit': 'mm_design_frame_not_scan',
        'maximum_step_mm': maximum_step, 'numerical_allowance_mm': numerical_allowance,
        'numerical_allowance_is_assumed_not_interval_verified': True,
        'method': 'native_OCCT_distances_plus_translation_Lipschitz_lower_bound',
        'bound_formula': 'min_grid_distance - first_covering_radius - second_covering_radius - numerical_allowance',
        'domain': 'independent_lifts_of_each_valve_in_its_closed_to_maximum_interval',
        'rigid_translation_only': True,
        'identified_imported_solids': [{'name': m['spec']['name'],
                                       'STEP_solid_index': m['STEP_solid_index'],
                                       'symmetric_volume_difference_mm3': m['identification_difference_mm3']}
                                      for m in moving],
        'pairs': pairs,
        'minimum_continuous_lower_bound_mm': min(r['continuous_lower_bound_mm'] for r in pairs),
        'all_pairs_positive_under_numerical_assumption': all(r['positive_bound_under_numerical_assumption'] for r in pairs),
        'piston_or_fixed_component_clearance_checked': False,
        'thermal_or_elastic_deformation_checked': False,
        'cam_timing_selected': False, 'manufacturing_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assembly-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--maximum-step-mm', type=float, default=1.0)
    parser.add_argument('--numerical-allowance-mm', type=float, default=1e-5)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if not 0.25 <= args.maximum_step_mm <= 2:
        raise ValueError('step outside bounded audit range')
    if not 1e-7 <= args.numerical_allowance_mm <= 0.1:
        raise ValueError('numerical allowance outside audit range')
    resource.setrlimit(resource.RLIMIT_CPU, (550, 560))
    report = run(args.assembly_directory, args.maximum_step_mm, args.numerical_allowance_mm)
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2) + '\n')
    if not report['all_pairs_positive_under_numerical_assumption']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
