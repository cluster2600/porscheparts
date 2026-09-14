#!/usr/bin/env python3
"""Measure nominal insert/body contact patches on private native geometry.

These are geometric coincidence areas, not press-fit pressure, conductance,
hot retention or a manufacturing qualification. Both the unported reference
and ported candidate stay unchanged; exact component identities are checked.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import time

import build_four_valve_distribution as design
import build_continuous_valve_envelopes as motion
import audit_port_skin_openings as skin
import build_scan_seeded_ports as ports


def adaptive_area(cad, shape, epsilon):
    props = cad.GProp_GProps()
    estimator = cad.BRepGProp.SurfaceProperties_s(shape, props, epsilon, True)
    return {'area': props.Mass(), 'relative_error_estimate_not_bound': estimator}


def external_cylinder_face(cad, shape, radius):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    selected = []
    for face in skin.indexed_faces(cad, shape):
        adaptor = BRepAdaptor_Surface(face, True)
        if adaptor.GetType() == GeomAbs_Cylinder and abs(adaptor.Cylinder().Radius()-radius) < 1e-7:
            selected.append(face)
    if len(selected) != 1:
        raise ValueError('one_unique_nominal_external_cylinder_required')
    return selected[0]


def contact_patch(cad, surface, body):
    patch, _ = skin.boolean(cad, surface, body, 'common')
    return patch, {'face_count': len(skin.indexed_faces(cad, patch)),
                   'quadrature': {str(eps): adaptive_area(cad, patch, eps) for eps in (1e-9, 1e-11)}}


def topology_tolerances(cad, shape):
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE
    from OCP.TopoDS import TopoDS
    result = {}
    for label, kind, cast in [('vertex', TopAbs_VERTEX, TopoDS.Vertex_s),
                              ('edge', TopAbs_EDGE, TopoDS.Edge_s),
                              ('face', TopAbs_FACE, TopoDS.Face_s)]:
        indexed = cad.indexed(shape, kind)
        values = [BRep_Tool.Tolerance_s(cast(indexed.FindKey(i)))
                  for i in range(1, indexed.Extent()+1)]
        result[label] = {'count': len(values), 'max': max(values, default=0.)}
    return result


def reject_insert_penetration(cad, insert, body):
    overlap = motion.native_boolean(cad, insert, body)
    volume = cad.volume(overlap)
    if not math.isfinite(volume) or abs(volume) > 1e-7:
        raise ValueError('nominal_insert_penetrates_body')
    return volume


def compare_contact(cad, outside, body_before, body_after, nominal_area):
    before_shape, before = contact_patch(cad, outside, body_before)
    after_shape, after = contact_patch(cad, outside, body_after)
    area_before = before['quadrature']['1e-11']['area']
    area_after = after['quadrature']['1e-11']['area']
    # Screening invariant only. Integration estimates are retained, not treated
    # as certified error bounds; every ratio is reported before interpretation.
    if area_after > area_before + 1e-5 + nominal_area*1e-7:
        raise ValueError('contact_area_increased_after_material_removal')
    return after_shape, {'reference': before, 'candidate': after,
                        'nominal_full_lateral_area': nominal_area,
                        'reference_nominal_fraction': area_before/nominal_area,
                        'candidate_nominal_fraction': area_after/nominal_area,
                        'area_removed_by_porting': area_before-area_after,
                        'load_capacity_or_heat_conductance_proven': False}


def run(args):
    import OCP
    started = time.monotonic()
    trial = json.loads((args.trial/'routing-report.json').read_text())
    registration = json.loads(args.body_build.read_text())
    module_build_path = args.module/'build-report.json'
    module_path = args.module/'closed.step'
    module = json.loads(module_build_path.read_text())
    body_path = args.trial/'ported-candidate.brep'
    paths = {'candidate_native': body_path, 'reference_STEP': args.reference,
             'body_build': args.body_build, 'module_STEP': module_path,
             'module_build': module_build_path, 'trial_report': args.trial/'routing-report.json',
             'source': Path(__file__), 'motion_source': Path(motion.__file__),
             'design_source': Path(design.__file__), 'skin_source': Path(skin.__file__),
             'routing_source': Path(ports.__file__)}
    hashes = {key: ports.sha(path) for key, path in paths.items()}
    expected = trial['inputs_sha256']
    if (hashes['candidate_native'] != trial['candidate_exports']['native_BRep_sha256']
            or hashes['reference_STEP'] != expected['body']
            or hashes['body_build'] != expected['body_build']
            or hashes['module_STEP'] != expected['module_STEP']
            or hashes['module_build'] != expected['module_build']
            or hashes['module_STEP'] != module['closed_step']['sha256']
            or hashes['module_STEP'] != registration['module_sha256']
            or not trial['input_files_unchanged']
            or trial['candidate_exports']['native_BOP']['has_faulty']):
        raise ValueError('body_module_or_trial_provenance_mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    ports.save(args.output/'context.json', {'inputs_sha256': hashes, 'OCP_version': OCP.__version__,
        'role': 'nominal_geometric_contact_not_contact_physics', 'manufacturing_authorized': False})
    cad = design.CAD(); p = design.Parameters(**module['parameters']).validate()
    body_before = cad.read_step(args.reference)
    body_after = skin.native_read(body_path)
    actual_module = cad.read_step(module_path)
    for shape, solids in ((body_before, 1), (body_after, 1), (actual_module, 12)):
        if not cad.valid(shape) or cad.indexed(shape, cad.TopAbs_SOLID).Extent() != solids:
            raise ValueError('unexpected_native_shape_validity_or_solid_count')
    indexed = cad.indexed(actual_module, cad.TopAbs_SOLID)
    actual = [indexed.FindKey(i) for i in range(1, indexed.Extent()+1)]
    records = []
    for part in design.construct(cad, p, design.lift_states(p)[0]):
        if part['role'] not in ('seat', 'guide'):
            continue
        identity = motion.identify_imported_valve(cad, actual, part['shape'])
        insert = motion.registered(cad, actual[identity['STEP_solid_index']-1], registration['registration'])
        radius = (part['spec']['diameter_mm']/2+p.seat_outer_radial_allowance_mm
                  if part['role']=='seat' else p.guide_outer_diameter_mm/2)
        length = p.seat_axial_thickness_mm if part['role']=='seat' else p.guide_length_mm
        outside = external_cylinder_face(cad, insert, radius)
        expected_area = 2*math.pi*radius*length
        full_area = adaptive_area(cad, outside, 1e-11)['area']
        if abs(full_area-expected_area)>1e-7*expected_area:
            raise ValueError('insert_lateral_area_does_not_match_nominal_profile')
        reference_penetration_volume = reject_insert_penetration(cad, insert, body_before)
        penetration_volume = reject_insert_penetration(cad, insert, body_after)
        patch, comparison = compare_contact(cad, outside, body_before, body_after, expected_area)
        path = args.output/(part['name']+'-OD-contact.brep')
        skin.native_write(path, patch)
        record = {'name': part['name'], 'role': part['role'], 'module_identity': identity,
                  'comparison': comparison, 'contact_native_sha256': ports.sha(path),
                  'reference_penetration_volume': reference_penetration_volume,
                  'candidate_penetration_volume': penetration_volume,
                  'insert_topology_tolerances': topology_tolerances(cad, insert),
                  'contact_only_on_outer_cylindrical_side': True,
                  'end_shoulders_inner_surfaces_and_valve_sealing_band_not_included': True}
        records.append(record); ports.save(args.output/(part['name']+'-contact-report.json'), record)
        print(json.dumps({'name': part['name'], 'nominal_OD_fraction': comparison['candidate_nominal_fraction']}), flush=True)
    unchanged = all(ports.sha(path)==hashes[key] for key, path in paths.items())
    if not unchanged:
        raise ValueError('input_changed_during_contact_audit')
    report = {'schema': 'm64-private-insert-OD-contact/v2', 'inputs_sha256': hashes,
              'length_unit': 'scan_units_under_unverified_1_unit_per_mm_hypothesis',
              'records': records, 'input_files_unchanged': unchanged,
              'reference_topology_tolerances': topology_tolerances(cad, body_before),
              'candidate_topology_tolerances': topology_tolerances(cad, body_after),
              'Boolean_fuzzy_value': 0.,
              'coincidence_at_native_OCCT_tolerances_not_strict_zero_gap': True,
              'gaps_below_native_tolerance_may_be_classified_as_coincident': True,
              'penetration_screen_absolute_volume_threshold_scan_units_cubed': 1e-7,
              'cold_nominal_coincidence_only': True, 'contact_pressure_or_conductance_assigned': False,
              'thermal_expansion_or_interference_fit_checked': False,
              'cam_carrier_stud_preloads_or_hot_retention_checked': False,
              'manufacturing_authorized': False, 'wall_seconds': time.monotonic()-started}
    ports.save(args.output/'contact-report.json', report)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('trial', 'reference', 'body-build', 'module', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (300, 305))
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
