#!/usr/bin/env python3
"""Private input package for a future local PicoGK experiment, never a design.

The native intake is read without a STEP translation. Full plane sections,
selected native edges and proposed convex boxes are exported as diagnostics.
No fillet, gas-volume alteration, body cut or implicit/private PicoGK run occurs.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import multiprocessing
from pathlib import Path
import time

import build_local_port_junction_fillet as local

EXPECTED_INTAKE = '72e0a786a601b96250380d16296004de9e6746caa3888ee470b6cd218f2d0251'
EXPECTED_REGISTRATION = {'scale_scan_units_per_mm_hypothesis': 1.0,
                         'rotation_Z_deg_hypothesis': -90.0,
                         'translation_Z_hypothesis': 3.0}


def proposal_boxes(bounds, radius=1., voxel=.2):
    if (len(bounds) != 6 or not all(math.isfinite(v) for v in bounds) or
            not math.isfinite(radius) or radius <= 0 or
            not math.isfinite(voxel) or voxel <= 0 or
            any(bounds[k] > bounds[k+3] for k in range(3))):
        raise ValueError('Finite ordered bounds and positive radius/voxel required')
    margin = 3 * voxel
    outer = [bounds[k] - radius - margin for k in range(3)] + [
             bounds[k+3] + radius + margin for k in range(3)]
    inner = [outer[k] + margin for k in range(3)] + [outer[k+3] - margin for k in range(3)]
    if any(inner[k+3] <= inner[k] for k in range(3)):
        raise ValueError('Contracted calculation ROI is empty')
    return {'exploratory_radius_scan_units': radius, 'voxel_scan_units': voxel,
            'calculation_margin_scan_units': margin, 'inflation_scan_units': radius + margin,
            'authorized_box_PROPOSED_private': outer, 'calculation_box_PROPOSED_private': inner,
            'boxes_nonempty': True, 'numeric_inflation_not_morphology_support_proof': True,
            'authorized_box_frozen_by_this_preparation': False,
            'keepout_subtracted_domain_nonempty': None,
            'private_processing_authorized': False}


def verify_provenance(hashes, checkpoint, context, body_build, routing):
    if (hashes['intake'] != EXPECTED_INTAKE or checkpoint['kind'] != 'intake' or
            checkpoint['exports']['native_BRep_sha256'] != hashes['intake'] or
            checkpoint['exports']['native_BOP']['has_faulty'] is not False or
            len(checkpoint['seed_sections_private']) != 7 or
            checkpoint['trunk_quality']['method'] != 'bounded-c1' or
            {row['name'] for row in checkpoint['branches']} != {'intake_1', 'intake_2'} or
            hashes['body_build'] != context['inputs_sha256']['body_build'] or
            body_build['module_sha256'] != context['inputs_sha256']['module_STEP'] or
            body_build['registration'] != EXPECTED_REGISTRATION or
            routing['inputs_sha256'] != context['inputs_sha256'] or
            not any(row == checkpoint for row in routing['bank_records'])):
        raise ValueError('Intake/checkpoint/body/module/frame provenance mismatch')


def native_bounds(shape):
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, True)
    if box.IsVoid() or box.IsOpen():
        raise ValueError('Finite nonempty native bound required')
    return list(box.Get())


def write_shape(path, shape):
    from OCP.BRepTools import BRepTools
    if path.exists():
        raise FileExistsError(path)
    if not BRepTools.Write_s(shape, str(path)):
        raise RuntimeError('Native diagnostic BRep write failed')
    path.chmod(0o600)
    return {'filename': path.name, 'sha256': local.ports.sha(path)}


def edge_description(cad, edge, edge_index=None):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRep import BRep_Tool
    curve = BRepAdaptor_Curve(edge)
    first, last = curve.FirstParameter(), curve.LastParameter()
    points = []
    for index in range(65):
        point = curve.Value(first + (last-first) * index/64)
        points.append([point.X(), point.Y(), point.Z()])
    return {'native_edge_id_in_this_source_only': edge_index,
            'curve_type': str(curve.GetType()), 'parameter_range': [first, last],
            'edge_tolerance_scan_units': BRep_Tool.Tolerance_s(edge),
            'native_precision_bounds_private': native_bounds(edge),
            'uniform_parameter_samples_private': points,
            'samples_are_not_continuous_extrema_or_distance_proof': True}


def full_plane_section(cad, source, section):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    plane = cad.gp_Pln(cad.gp_Pnt(*section['center']), cad.gp_Dir(*section['normal']))
    operation = BRepAlgoAPI_Section(source, plane, False)
    operation.SetNonDestructive(True)
    operation.Approximation(False)
    operation.Build()
    if not operation.IsDone():
        raise RuntimeError('Complete native plane section failed')
    result = operation.Shape()
    if cad.indexed(result, cad.TopAbs_EDGE).Extent() == 0:
        raise ValueError('Recorded section produced no edges')
    return result


def box_shape(bounds):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    if any(bounds[k+3] <= bounds[k] for k in range(3)):
        raise ValueError('Empty convex ROI')
    return BRepPrimAPI_MakeBox(gp_Pnt(*bounds[:3]), gp_Pnt(*bounds[3:])).Shape()


def reservation_shapes(cad, tools, choices):
    result = []
    for tool in tools:
        for role, interval, radius in (
                ('seat_envelope', tool['seat_axial_interval'], tool['seat_OD']/2),
                ('guide_envelope', tool['guide_axial_interval'], tool['guide_OD']/2),
                ('guide_boss_envelope', [choices['guide_boss_start_axial'], choices['guide_boss_end_axial']],
                 choices['guide_boss_radius'])):
            if radius <= 0 or interval[1] <= interval[0]:
                raise ValueError('Invalid recorded keepout envelope')
            origin = [tool['axis_origin'][k] + interval[0]*tool['axis_direction'][k] for k in range(3)]
            shape = cad.BRepPrimAPI_MakeCylinder(
                cad.gp_Ax2(cad.gp_Pnt(*origin), cad.gp_Dir(*tool['axis_direction'])),
                radius, interval[1]-interval[0]).Shape()
            result.append((shape, {'valve': tool['name'], 'role': role,
                                   'axis_origin_private': tool['axis_origin'],
                                   'axis_direction_private': tool['axis_direction'],
                                   'axial_interval_private': interval, 'radius_scan_units': radius,
                                   'solid_cylinder_is_reservation_not_actual_part': True}))
    return result


def distance_worker(first_path, second_path, boundary_only, queue):
    try:
        cad = local.ports.design.CAD()
        first, second = local.read_native(first_path), local.read_native(second_path)
        if boundary_only:
            faces = cad.indexed(second, cad.TopAbs_FACE)
            second = cad.compound([faces.FindKey(i) for i in range(1, faces.Extent()+1)])
        value = cad.distance(first, second)
        queue.put({'status': 'kernel_distance_completed', 'distance_scan_units': value,
                   'boundary_only': boundary_only, 'certified_wall_thickness': False})
    except Exception as error:
        queue.put({'status': 'failed', 'distance_scan_units': None, 'error': str(error),
                   'certified_wall_thickness': False})


def bounded_distance(first, second, boundary_only, seconds=20):
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    process = context.Process(target=distance_worker, args=(str(first), str(second), boundary_only, queue))
    process.start()
    process.join(seconds)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join()
        result = {'status': 'timed_out', 'distance_scan_units': None,
                  'certified_wall_thickness': False}
    else:
        try:
            result = queue.get(timeout=1)
        except Exception:
            result = {'status': 'worker_did_not_return', 'distance_scan_units': None,
                      'certified_wall_thickness': False}
    queue.close()
    return result


def run(args):
    import OCP
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Circ
    started = time.monotonic()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    paths = {'intake': args.routing_dir/'intake-negative.brep',
             'checkpoint': args.routing_dir/'intake-checkpoint.json',
             'context': args.routing_dir/'execution-context.json',
             'routing_report': args.routing_dir/'routing-report.json',
             'body_build': args.body_build, 'preparation_source': Path(__file__),
             'edge_identification_helper': Path(local.__file__),
             'routing_helper': Path(local.ports.__file__),
             'CAD_helper': Path(local.ports.design.__file__)}
    hashes = {name: local.ports.sha(path) for name, path in paths.items()}
    read = lambda name: json.loads(paths[name].read_text())
    checkpoint, context, build, routing = (read(name) for name in ('checkpoint', 'context', 'body_build', 'routing_report'))
    verify_provenance(hashes, checkpoint, context, build, routing)
    cad = local.ports.design.CAD()
    source = local.read_native(paths['intake'])
    if not cad.valid(source) or cad.indexed(source, cad.TopAbs_SOLID).Extent() != 1:
        raise ValueError('One valid native intake required')
    selected = local.branch_cap_edges(cad, source, checkpoint['seed_sections_private'][0])
    if len(selected) != 3:
        raise ValueError('Exactly three identified branch/cap edges required')
    args.output.mkdir(parents=True, mode=0o700)
    if args.output.stat().st_mode & 0o077:
        raise ValueError('Private output directory required')
    selected_shape = cad.compound([edge for _, edge, _ in selected])
    edge_path = args.output/'selected-junction-edges.brep'
    edge_export = write_shape(edge_path, selected_shape)
    proposal = proposal_boxes(native_bounds(selected_shape), args.radius, args.voxel)
    proposed_box = box_shape(proposal['authorized_box_PROPOSED_private'])
    calculation_box = box_shape(proposal['calculation_box_PROPOSED_private'])
    report = {'schema': 'm64-private-picogk-intake-input-preparation/v1',
              'created_at_utc': datetime.now(timezone.utc).isoformat(), 'OCP_version': OCP.__version__,
              'inputs_private': {name: str(path) for name, path in paths.items()}, 'inputs_sha256': hashes,
              'length_unit': 'scan_unit_under_unverified_1_mm_hypothesis',
              'source_registration_reapplied': False, 'native_admission_only_no_STEP_reimport': True,
              'native_BOP_from_checkpoint_not_reexecuted': checkpoint['exports']['native_BOP'],
              'bound_method': 'BRepBndLib.AddOptimal_useTriangulation_false_useShapeTolerance_true',
              'native_bounds_are_kernel_precision_not_exact_rational_certificates': True,
              'selected_edges': [{**edge_description(cad, edge, index),
                                  'selection_sampled_radial_max': radial} for index, edge, radial in selected],
              'selection_uses_existing_sampled_branch_cap_helper_not_a_new_exact_classifier': True,
              'selected_edges_export': edge_export, 'ROI_proposal': proposal,
              'proposed_box_export': write_shape(args.output/'authorized-box-PROPOSED.brep', proposed_box),
              'calculation_box_export': write_shape(args.output/'calculation-box-PROPOSED.brep', calculation_box),
              'sections': [], 'protections': {}, 'distance_diagnostics': {},
              'original_master_modified': False, 'prototype_created': False,
              'PicoGK_private_execution_authorized': False, 'manufacturing_authorized': False}
    local.ports.save(args.output/'preparation-stage-01.json', report)
    for index, section in enumerate(checkpoint['seed_sections_private']):
        shape = full_plane_section(cad, source, section)
        edges = cad.indexed(shape, cad.TopAbs_EDGE)
        row = {'section_number': index+1, 'plane_and_seed_private': section,
               'full_infinite_plane_intersection': True, 'contains_all_section_edges_not_only_seed_circle': True,
               'section_export': write_shape(args.output/f'complete-section-{index+1:02d}.brep', shape),
               'edges': [edge_description(cad, cad.TopoDS.Edge_s(edges.FindKey(i)))
                         for i in range(1, edges.Extent()+1)],
               'filled_section_area_and_loop_nesting': None,
               'section_equality_after_modification_tested': False}
        report['sections'].append(row)
        local.ports.save(args.output/f'section-{index+1:02d}-receipt.json', row)
    seed = checkpoint['seed_sections_private'][0]
    circle = BRepBuilderAPI_MakeEdge(gp_Circ(cad.gp_Ax2(cad.gp_Pnt(*seed['center']),
                                            cad.gp_Dir(*seed['normal'])), seed['radius'])).Edge()
    reservations = reservation_shapes(cad, build['tools_private'], routing['design_choices'])
    keepouts = cad.compound([shape for shape, _ in reservations])
    report['protections'] = {
        'first_section_outer_circle': {'seed_private': seed,
            'export': write_shape(args.output/'outer-section-circle-reference.brep', circle),
            'analytic_circle_from_frozen_checkpoint_not_OEM_measurement': True},
        'seat_guide_and_boss_reservations': {'records': [row for _, row in reservations],
            'export': write_shape(args.output/'seat-guide-boss-reservations.brep', keepouts),
            'registration_is_already_in_recorded_body_frame': True},
        'branch_records_private': checkpoint['branches'],
        'branches_outside_proposed_local_region_must_remain_unchanged': True,
        'outer_ring_keepout_has_no_qualified_annular_band_width_yet': True,
        'convex_box_is_not_a_keepout_aware_authorized_domain': True,
        'protected_nonconvex_domain_requires_full_triangle_intersection_checks': True,
        'seven_complete_section_regions_must_match_not_only_contained_seed_discs': True,
    }
    report['distance_diagnostics']['selected_edges_to_outer_circle'] = {
        'distance_scan_units': cad.distance(selected_shape, circle), 'certified_wall_thickness': False}
    report['distance_diagnostics']['proposed_authorized_box_to_outer_circle'] = {
        'distance_scan_units': cad.distance(proposed_box, circle), 'certified_wall_thickness': False}
    report['distance_diagnostics']['proposed_authorized_box_to_reservations'] = {
        'distance_scan_units': cad.distance(proposed_box, keepouts), 'certified_wall_thickness': False}
    local.ports.save(args.output/'preparation-stage-02.json', report)
    ported = args.routing_dir/'ported-candidate.brep'
    if ported.is_file():
        paths['body_with_intake_and_exhaust'] = ported
        hashes['body_with_intake_and_exhaust'] = local.ports.sha(ported)
        if hashes['body_with_intake_and_exhaust'] != routing['candidate_exports']['native_BRep_sha256']:
            raise ValueError('Body-with-ports differs from routing receipt')
        report['body_with_ports_input'] = {'sha256': hashes['body_with_intake_and_exhaust'],
            'original_status_retained': routing['status'],
            'native_BOP_from_receipt_not_reexecuted': routing['candidate_exports']['native_BOP']}
        report['distance_diagnostics']['selected_edges_to_body_with_ports_boundary'] = {
            **bounded_distance(edge_path, ported, True),
            'own_intake_wall_is_included_zero_is_not_a_wall_failure_or_thickness': True}
    else:
        report['distance_diagnostics']['selected_edges_to_body_with_ports_boundary'] = {
            'status': 'body_with_other_ports_unavailable', 'distance_scan_units': None,
            'certified_wall_thickness': False}
    exhaust = args.routing_dir/'exhaust-negative.brep'
    if exhaust.is_file():
        exhaust_record = next(row for row in routing['bank_records'] if row['kind'] == 'exhaust')
        paths['exhaust'] = exhaust
        hashes['exhaust'] = local.ports.sha(exhaust)
        if hashes['exhaust'] != exhaust_record['exports']['native_BRep_sha256']:
            raise ValueError('Exhaust differs from routing receipt')
        report['distance_diagnostics']['proposed_box_to_exhaust_negative'] = {
            **bounded_distance(args.output/'authorized-box-PROPOSED.brep', exhaust, False),
            'conservative_proposal_box_distance_not_final_added_gas_wall': True}
    report['inputs_private'] = {name: str(path) for name, path in paths.items()}
    report['inputs_sha256'] = hashes
    if any(local.ports.sha(path) != hashes[name] for name, path in paths.items()):
        raise ValueError('An input/helper changed during preparation')
    report['source_files_unchanged'] = True
    report['elapsed_seconds'] = time.monotonic() - started
    report['status'] = 'input_package_prepared_proposed_domain_not_approved'
    report['blocking_guards_before_private_PicoGK'] = [
        'buffered_synthetic_witness_and_existing_guards_must_pass',
        'freeze_private_authorized_domain_separately_from_inner_calculation_mask',
        'define_ring_band_and_keepouts_then_prove_remaining_domain_nonempty',
        'preserve_complete_section_regions_and_analytic_functional_interfaces',
        'native_to_voxel_baseline_error_is_separate_from_local_change',
        'no_original_body_or_intake_cut_from_this_package']
    local.ports.save(args.output/'preparation-report.json', report)
    print(json.dumps({'status': report['status'], 'selected_edges': len(selected),
                      'complete_sections': len(report['sections']), 'output': str(args.output),
                      'source_files_unchanged': True, 'PicoGK_private_execution_authorized': False}))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routing-dir', type=Path, required=True)
    parser.add_argument('--body-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--radius', type=float, default=1.)
    parser.add_argument('--voxel', type=float, default=.2)
    args = parser.parse_args()
    if args.radius != 1. or args.voxel != .2:
        parser.error('This preparation is restricted to the proposed R1/h0.2 experiment')
    raise SystemExit(run(args))
