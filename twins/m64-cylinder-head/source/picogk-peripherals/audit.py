#!/usr/bin/env python3
"""Independent raw topology and two-resolution counter-check; no mesh repair."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

from prepare import NAMES, PINS, sha, write_json

HERE = Path(__file__).resolve().parent


def load_topology():
    helper = HERE.parent / 'picogk-local-junction/audit_surface_topology.py'
    spec = importlib.util.spec_from_file_location('peripheral_topology', helper)
    topology = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(topology)
    topology.MAX_FACES, topology.MAX_VERTICES = 2_000_000, 6_000_000
    return topology, helper


def expected_roles():
    result = {'head': 'head', 'intake_cover': 'veined_cover_without_mounts',
              'exhaust_cover': 'veined_cover_without_mounts', 'oil_distributor': 'branched_oil_hypothesis'}
    for name in NAMES:
        for suffix, role in (('seat', 'seat'), ('guide', 'guide'), ('extended_valve', 'extended_valve_hypothesis'),
                             ('spring_seat', 'spring_seat_hypothesis'), ('retainer', 'retainer_without_keeper'),
                             ('spring_space', 'keepout_not_spring')):
            result[name + '_' + suffix] = role
    return result


def validate_manifest(data):
    if (data.get('schema') != 'm64-picogk-peripherals/v1' or data.get('source_sha256') != PINS
            or type(data.get('voxel_world_units')) not in (int, float) or data['voxel_world_units'] not in (.4, .2)
            or data.get('status') != 'research_assembly_incomplete_not_released'
            or data.get('units') != 'uncalibrated_scan_unit_assumed_mm'):
        raise ValueError('Exact research assembly required')
    for key in ('assembly_complete', 'manufacturing_authorized', 'source_master_modified',
                'dynamics_validated', 'thermal_validated'):
        if data.get(key) is not False:
            raise ValueError('Missing or promoted authority: ' + key)
    rows = data['parts']
    if len(rows) != 28 or {r['name']: r['role'] for r in rows} != expected_roles():
        raise ValueError('Exact twenty-eight placements required')
    for row in rows:
        if (row['filename'] != row['name'] + '.stl' or row['transform'] != 'identity_already_registered'
                or row['reference'] is not (row['role'] in ('head', 'seat', 'guide'))
                or row['manufacturing_authorized'] is not False):
            raise ValueError('Placement, local filename or authority changed')
    return rows


def checked_parts(inputs, directory):
    report_path = directory / 'assembly.json'
    report = json.loads(report_path.read_text())
    rows = validate_manifest(report)
    if sha(inputs / 'inputs.json') != report['inputs_sha256']:
        raise ValueError('Different retained input manifest')
    paths = {}
    for row in rows:
        path = (inputs if row['reference'] else directory) / row['filename']
        if path.is_symlink() or not path.is_file() or sha(path) != row['sha256']:
            raise ValueError('Part hash mismatch')
        paths[row['name']] = path
    return report, paths


def volume_comparison(coarse, fine):
    if any(isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in (coarse, fine)):
        raise ValueError('Positive finite volumes required')
    difference = abs(coarse - fine) / fine
    return dict(relative_difference=difference, exploratory_threshold=.02, passes=difference <= .02,
                continuous_surface_error_proved=False)


def run(inputs, coarse, fine, output):
    if output.exists():
        raise FileExistsError(output)
    topology, helper = load_topology()
    import numpy as np
    results, native = [], []
    for directory, h in ((coarse, .4), (fine, .2)):
        report, paths = checked_parts(inputs, directory)
        if report['voxel_world_units'] != h:
            raise ValueError('Wrong resolution order')
        native.append(report)
        fluid = directory / 'oil-fluid-diagnostic.stl'
        if sha(fluid) != report['oil_fluid_diagnostic_sha256']:
            raise ValueError('Oil diagnostic changed')
        todo = [(r['name'], paths[r['name']]) for r in report['parts'] if not r['reference']]
        todo.append(('oil_fluid_diagnostic', fluid))
        meshes = {}
        for name, path in todo:
            triangles, digest = topology.load_binary_stl(path)
            raw = topology.audit_arrays(triangles.reshape(-1, 3), np.arange(triangles.size // 3).reshape(-1, 3))
            records = np.frombuffer(path.read_bytes(), dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]), offset=84)
            meshes[name] = dict(sha256=digest, raw=raw,
                               nonfinite_STL_normals=int((~np.isfinite(records['normal']).all(axis=1)).sum()))
            print(json.dumps(dict(h=h, part=name, faces=len(triangles), zero=raw['exact_zero_area_faces'],
                                  components=raw['edge_connected_face_components'],
                                  raw_pass=raw['closed_oriented_combinatorial_surface_screen_pass'])), flush=True)
        results.append(dict(voxel_world_units=h, meshes=meshes, collision_screen=report['collision_screen'],
                            receipt_sha256=sha(directory / 'assembly.json')))
    for key in ('program_sha256', 'picogk_sha256', 'native_version', 'native_build', 'inputs_sha256'):
        if native[0][key] != native[1][key]:
            raise ValueError('Different builds or inputs are not a resolution study')
    volumes = {name: volume_comparison(*(r['meshes'][name]['raw']['signed_triangle_volume_scan_units_cubed']
                                        for r in results)) for name in results[0]['meshes']}
    raw_pass = all(m['nonfinite_STL_normals'] == 0 and m['raw']['closed_oriented_combinatorial_surface_screen_pass']
                   and m['raw']['edge_connected_face_components'] == 1
                   for r in results for m in r['meshes'].values())
    # Independent closed-form annulus volumes, not the producer's voxel integration.
    annuli = {}
    for name, mesh in results[1]['meshes'].items():
        if name.endswith('_spring_seat'):
            expected = math.pi * (16**2 - 7.75**2) * 3
        elif name.endswith('_retainer'):
            expected = math.pi * (16**2 - 3.2**2) * 3
        elif name.endswith('_spring_space'):
            expected = math.pi * (15**2 - 7.75**2) * 40.4
        else:
            continue
        measured = mesh['raw']['signed_triangle_volume_scan_units_cubed']
        annuli[name] = dict(analytic_volume=expected, triangle_volume=measured,
                           relative_error=abs(measured - expected) / expected)
    for directory in (coarse, fine):
        receipt, _ = checked_parts(inputs, directory)
        if sha(directory/'oil-fluid-diagnostic.stl') != receipt['oil_fluid_diagnostic_sha256']:
            raise ValueError('Oil diagnostic changed during audit')
    data = dict(schema='m64-peripheral-counter-audit/v1', resolutions=results,
                topology_source_sha256=sha(helper), inspection_source_sha256=sha(__file__),
                raw_single_component_screens_pass=raw_pass, volume_comparisons=volumes,
                analytic_annulus_counter_checks=annuli, original_meshes_modified=False,
                normalized_or_repaired_meshes_used=False, new_reference_body_audit_performed=False,
                physical_clearance_proved=False, manufacturing_authorized=False,
                assembly_complete=False, status='research_assembly_incomplete_not_released')
    write_json(output, data)
    return 0 if raw_pass and all(v['passes'] for v in volumes.values()) else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'coarse', 'fine', 'output'):
        parser.add_argument('--' + key, required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.inputs, args.coarse, args.fine, args.output))
