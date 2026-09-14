#!/usr/bin/env python3
"""Private continuous nominal valve-motion exclusions, not an engine release.

For a filled axisymmetric profile with nonincreasing radius r(z) and an initial
positive-height cylindrical base, translations by -t ez, 0 <= t <= L, have the
exact union obtained by extending only that maximum-radius base down by L.
Both the monotonicity and initial-cylinder conditions are checked explicitly.
Only new diagnostic envelopes receive the registered module-to-body transform.
"""
import argparse
from dataclasses import asdict
import json
import math
import multiprocessing
from pathlib import Path
import resource
import sys
import time

import build_four_valve_distribution as design

sys.path.insert(0, str(Path(__file__).parent / 'picogk'))
from compare_meshes import atomic_private_json, json_hash
from export_master import sha256
from audit_shell_against_step import shape_counts, shape_volume, valid_shape


def continuous_sweep_profile(profile, lift):
    """Return an exact profile for this restricted monotone-radius family."""
    if not math.isfinite(lift) or lift < 0:
        raise ValueError('nonnegative_finite_lift_required')
    if len(profile) < 4 or any(len(point) != 2 or not all(math.isfinite(x) for x in point) for point in profile):
        raise ValueError('finite_radial_axial_profile_required')
    outer = profile[1:-1]
    if (profile[0][0] != 0 or profile[-1][0] != 0
            or profile[0][1] != outer[0][1] or profile[-1][1] != outer[-1][1]
            or any(r <= 0 for r, _ in outer)
            or any(b[1] <= a[1] for a, b in zip(outer, outer[1:]))
            or any(b[0] > a[0] for a, b in zip(outer, outer[1:]))):
        raise ValueError('filled_single_valued_nonincreasing_positive_radius_profile_required')
    # Moving only the first two polygon vertices preserves the original radial
    # graph above zmin ONLY when its first outer segment is cylindrical. A cone
    # beginning at zmin would otherwise acquire a shallower, undersized slope.
    if outer[0][0] != outer[1][0]:
        raise ValueError('positive_height_initial_cylindrical_base_required')
    result = [tuple(point) for point in profile]
    result[0] = (0., profile[0][1] - lift)
    result[1] = (outer[0][0], outer[0][1] - lift)
    proof = {
        'radius_positive': True, 'outer_z_strictly_increasing': True,
        'initial_base_cylindrical_with_positive_height': True,
        'initial_cylindrical_base_height': outer[1][1] - outer[0][1],
        'radius_piecewise_linear_nonincreasing': True,
        'outer_segment_dr_dz': [(b[0] - a[0]) / (b[1] - a[1]) for a, b in zip(outer, outer[1:])],
        'lift_interval': [0., lift], 'translation_axis_local': [0., 0., -1.],
        'union_formula': 'union_{0<=t<=L}(S-t*ez) = extended_base_profile',
        'above_original_base': 'at z>=zmin, r(z+t)<=r(z); t=0 attains r(z)',
        'below_original_base': 'at zmin-L<=z<zmin, t=zmin-z attains the maximum radius r(zmin)',
        'outside_axial_extent': 'no translated point lies outside [zmin-L,zmax]',
        'added_volume_formula': 'pi*r(zmin)^2*L',
        'analytic_added_volume': math.pi * outer[0][0] ** 2 * lift,
        'proof_is_for_rigid_nominal_translation_only': True,
        'sampling_is_not_the_continuous_coverage_proof': True,
    }
    return result, proof


def registered(cad, shape, registration):
    if registration != {'scale_scan_units_per_mm_hypothesis': 1.0,
                         'rotation_Z_deg_hypothesis': -90.0,
                         'translation_Z_hypothesis': 3.0}:
        raise ValueError('explicit_V2_registered_frame_required')
    transform = cad.gp_Trsf()
    transform.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0, 0, 0), cad.gp_Dir(0, 0, 1)), -math.pi / 2)
    transform.SetTranslationPart(cad.gp_Vec(0, 0, 3.))
    return cad.BRepBuilderAPI_Transform(shape, transform, True).Shape()


def native_boolean(cad, first, second, kind='common'):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    arguments = TopTools_ListOfShape(); arguments.Append(first)
    tools = TopTools_ListOfShape(); tools.Append(second)
    job = (BRepAlgoAPI_Common if kind == 'common' else BRepAlgoAPI_Cut)()
    job.SetArguments(arguments); job.SetTools(tools)
    job.SetNonDestructive(True); job.SetFuzzyValue(0.); job.SetRunParallel(False)
    job.Build()
    if not job.IsDone() or not valid_shape(job.Shape()):
        raise ValueError('native_boolean_failed_or_invalid')
    return job.Shape()


def identify_imported_valve(cad, actual, expected):
    matches = []
    expected_volume = shape_volume(expected)
    for index, candidate in enumerate(actual):
        candidate_volume = shape_volume(candidate)
        if abs(candidate_volume - expected_volume) > 1e-5:
            continue
        common = native_boolean(cad, candidate, expected)
        difference = candidate_volume + expected_volume - 2 * shape_volume(common)
        if abs(difference) <= 1e-7:
            matches.append({'STEP_solid_index': index + 1, 'symmetric_volume_difference': difference})
    if len(matches) != 1:
        raise ValueError('imported_valve_identity_not_unique')
    return matches[0]


def write_private_step(path, shape):
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.IFSelect import IFSelect_RetDone
    if path.exists():
        raise FileExistsError(path)
    writer = STEPControl_Writer()
    if writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone or writer.Write(str(path)) != IFSelect_RetDone:
        raise ValueError('private_STEP_export_failed')
    path.chmod(0o600)


def input_context(args):
    import OCP
    build_path = args.module_directory / 'build-report.json'
    module_path = args.module_directory / 'closed.step'
    build = json.loads(build_path.read_text())
    private_build = json.loads(args.registration_report.read_text())
    repair = json.loads(args.repair_report.read_text())
    p = design.Parameters(**json.loads(args.parameters.read_text())).validate()
    module_hash, body_hash = sha256(module_path), sha256(args.body)
    if (asdict(p) != build['parameters'] or module_hash != build['closed_step']['sha256']
            or module_hash != private_build['module_sha256']
            or private_build['candidate_sha256'] != repair['original_sha256']
            or repair['candidate_sha256'] != body_hash or body_hash != args.body_sha256):
        raise ValueError('module_parameters_or_body_registration_provenance_mismatch')
    registration = private_build['registration']
    if registration != {'scale_scan_units_per_mm_hypothesis': 1.0,
                         'rotation_Z_deg_hypothesis': -90.0, 'translation_Z_hypothesis': 3.0}:
        raise ValueError('unexpected_module_body_registration')
    paths = [Path(__file__), Path(design.__file__), Path(__file__).parent / 'picogk/compare_meshes.py',
             Path(__file__).parent / 'picogk/audit_shell_against_step.py',
             args.parameters, args.registration_report, args.repair_report, build_path, module_path, args.body]
    return {'schema': 'm64-private-continuous-valve-exclusion-context/v1',
            'source_hashes_private': {str(path): sha256(path) for path in paths},
            'module_STEP_sha256': module_hash, 'body_STEP_sha256': body_hash,
            'parameters': asdict(p), 'registration': registration,
            'OCP_version': OCP.__version__, 'python_version': sys.version,
            'maximum_worker_seconds': args.worker_timeout_seconds,
            'nominal_shape_not_clearance_allowance': True, 'manufacturing_authorized': False}


def worker(args, context, name):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (args.worker_timeout_seconds, args.worker_timeout_seconds + 5))
    if input_context(args) != context:
        raise ValueError('inputs_changed_before_worker')
    cad = design.CAD(); p = design.Parameters(**context['parameters']).validate()
    spec = next(item for item in design.valve_specs(p) if item['name'] == name)
    profile = design.profiles(p, spec)[0]['valve']
    sweep_profile, proof = continuous_sweep_profile(profile, spec['max_lift_mm'])
    original = cad.revolve(profile); sweep_local = cad.revolve(sweep_profile)
    if abs(shape_volume(sweep_local) - shape_volume(original) - proof['analytic_added_volume']) > 1e-7:
        raise ValueError('analytic_and_native_swept_volume_disagree')
    module = cad.read_step(args.module_directory / 'closed.step')
    if not cad.valid(module):
        raise ValueError('imported_module_invalid')
    module_solids = cad.indexed(module, cad.TopAbs_SOLID)
    if module_solids.Extent() != 12:
        raise ValueError('expected_twelve_module_solids')
    expected = cad.pose(original, spec)
    match = identify_imported_valve(cad, [module_solids.FindKey(i) for i in range(1, 13)], expected)
    sweep = registered(cad, cad.pose(sweep_local, spec), context['registration'])
    if not valid_shape(sweep) or shape_counts(sweep)['solids'] != 1:
        raise ValueError('one_valid_registered_sweep_solid_required')
    body = cad.read_step(args.body)  # Already in final frame: NEVER transform it.
    if not valid_shape(body) or shape_counts(body)['solids'] != 1 or shape_volume(body) <= 0:
        raise ValueError('body_must_be_one_valid_positive_solid')
    intersection = native_boolean(cad, sweep, body)
    counts = shape_counts(intersection)
    directory = args.output / name
    if directory.exists():
        raise FileExistsError(directory)
    directory.mkdir(mode=0o700)
    sweep_path = directory / 'continuous-motion-exclusion-final-frame.step'
    write_private_step(sweep_path, sweep)
    reread = cad.read_step(sweep_path)
    reread_volume_delta = shape_volume(reread) - shape_volume(sweep)
    if not valid_shape(reread) or shape_counts(reread)['solids'] != 1 or abs(reread_volume_delta) > 1e-7:
        raise ValueError('sweep_STEP_roundtrip_failed')
    record = {
        'schema': 'm64-private-continuous-valve-exclusion/v1', 'context_sha256': json_hash(context),
        'name': name, 'imported_module_match': match, 'profile_monotonicity_and_coverage_proof': proof,
        'module_STEP_sha256': context['module_STEP_sha256'], 'body_STEP_sha256': context['body_STEP_sha256'],
        'envelope_STEP_sha256': sha256(sweep_path), 'envelope_native_volume': shape_volume(sweep),
        'STEP_roundtrip_volume_delta': reread_volume_delta,
        'intersection_with_current_body': {'exact_BRep_check_valid': True, 'topology_counts': counts,
                                           'volume_scan_units_cubed': shape_volume(intersection),
                                           'topologically_empty': all(value == 0 for value in counts.values())},
        'body_transformed': False, 'new_envelope_registration_applied_exactly_once': True,
        'nominal_lift_interval_continuously_covered': True,
        'clearance_or_thermal_growth_margin_added': False, 'cam_law_needed_for_this_union': False,
        'ports_oil_or_any_body_geometry_modified': False,
        'piston_springs_cams_timing_or_hot_deflections_checked': False,
        'M64_fitment_validated': False, 'manufacturing_authorized': False,
        'elapsed_seconds': time.monotonic() - started,
    }
    if any(counts.values()):
        overlap_path = directory / 'body-intersection-private.step'
        write_private_step(overlap_path, intersection)
        record['intersection_STEP_sha256'] = sha256(overlap_path)
    if input_context(args) != context:
        raise ValueError('source_changed_during_worker')
    record['source_files_unchanged'] = True
    atomic_private_json(args.output / (name + '-checkpoint.json'), record)


def run(args):
    context = input_context(args)
    if args.output.exists():
        if not args.resume or args.output.is_symlink() or args.output.stat().st_mode & 0o077:
            raise ValueError('new_private_output_or_explicit_valid_resume_required')
        if json.loads((args.output / 'context-private.json').read_text()) != context:
            raise ValueError('resume_context_mismatch')
    else:
        args.output.mkdir(parents=True, mode=0o700)
        atomic_private_json(args.output / 'context-private.json', context)
    p = design.Parameters(**context['parameters']).validate()
    report = {'schema': 'm64-private-four-continuous-valve-exclusions/v1', 'status': 'incomplete',
              'context_sha256': json_hash(context), 'records': [], 'manufacturing_authorized': False}
    report_path = args.output / 'continuous-motion-report-private.json'
    atomic_private_json(report_path, report)
    for spec in design.valve_specs(p):
        name = spec['name']; checkpoint = args.output / (name + '-checkpoint.json')
        if not checkpoint.exists():
            process = multiprocessing.get_context('spawn').Process(target=worker, args=(args, context, name))
            process.start()
            try:
                process.join(args.worker_timeout_seconds)
            except BaseException:
                process.terminate(); process.join(5)
                if process.is_alive():
                    process.kill(); process.join()
                raise
            if process.is_alive():
                process.terminate(); process.join(5)
                if process.is_alive():
                    process.kill(); process.join()
                raise RuntimeError('bounded_valve_worker_timed_out_' + name)
            if process.exitcode != 0:
                raise RuntimeError(f'valve_worker_failed_{name}_exit_{process.exitcode}')
        record = json.loads(checkpoint.read_text())
        sweep_path = args.output / name / 'continuous-motion-exclusion-final-frame.step'
        if (record.get('context_sha256') != json_hash(context) or record.get('name') != name
                or record.get('source_files_unchanged') is not True
                or sha256(sweep_path) != record['envelope_STEP_sha256']):
            raise ValueError('checkpoint_binding_or_artifact_integrity_mismatch')
        report['records'].append(record)
        atomic_private_json(report_path, report)
        print(json.dumps({'valve': name, 'intersection': record['intersection_with_current_body']}), flush=True)
    if len({row['imported_module_match']['STEP_solid_index'] for row in report['records']}) != 4:
        raise ValueError('four_distinct_imported_valves_required')
    if input_context(args) != context:
        raise ValueError('inputs_changed_before_final_report')
    cad = design.CAD()
    assembly_path = args.output / 'four-continuous-motion-exclusions-final-frame.step'
    shapes = [cad.read_step(args.output / spec['name'] / 'continuous-motion-exclusion-final-frame.step')
              for spec in design.valve_specs(p)]
    if not assembly_path.exists():
        write_private_step(assembly_path, cad.compound(shapes))
    assembly = cad.read_step(assembly_path)
    if not valid_shape(assembly) or shape_counts(assembly)['solids'] != 4:
        raise ValueError('four_exclusion_STEP_assembly_invalid')
    combined_solids = cad.indexed(assembly, cad.TopAbs_SOLID)
    actual = [combined_solids.FindKey(i) for i in range(1, 5)]
    combined_matches = [identify_imported_valve(cad, actual, shape) for shape in shapes]
    if len({match['STEP_solid_index'] for match in combined_matches}) != 4:
        raise ValueError('combined_STEP_does_not_match_four_verified_envelopes')
    report['combined_STEP_native_identity_matches'] = combined_matches
    report['combined_exclusions_STEP_sha256'] = sha256(assembly_path)
    report['all_nominal_motion_envelopes_disjoint_from_body'] = all(
        row['intersection_with_current_body']['topologically_empty'] for row in report['records'])
    report['status'] = 'completed_geometric_diagnostic_not_engine_validation'
    report['source_files_unchanged'] = True
    atomic_private_json(report_path, report)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module-directory', type=Path, required=True)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--body', type=Path, required=True)
    parser.add_argument('--body-sha256', required=True)
    parser.add_argument('--registration-report', type=Path, required=True)
    parser.add_argument('--repair-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--worker-timeout-seconds', type=int, default=180)
    args = parser.parse_args()
    if not 30 <= args.worker_timeout_seconds <= 600:
        raise ValueError('worker_timeout_must_be_30_to_600_seconds')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
