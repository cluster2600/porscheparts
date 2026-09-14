#!/usr/bin/env python3
"""Independent, preregistered local CAD budget; never overrides fillet v1.

No tolerance setter, repair, body integration, or physical accuracy claim.
The radius-0.25 construction is replayed only to recover native history.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import resource
import time

import build_local_port_junction_fillet as local
import audit_local_port_junction_fillet as constraints
import prepare_picogk_intake_junction as prep


EXPECTED_CANDIDATE = '455a382d7136f353fd0bfd31018ad00247a948cb32832e14845a32497fb6c3fb'
NEW_BUDGET = 1e-4
PARAMETER_SEARCH_TOLERANCE = 1e-9
SOURCE_URL = 'https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_9_3/src/ChFi3d/ChFi3d_Builder_1.cxx'


def entity_bytes(shape):
    from OCP.BRepTools import BRepTools
    stream = io.BytesIO()
    BRepTools.Write_s(shape, stream)
    return stream.getvalue()


def entity_hash(shape):
    from OCP.TopAbs import TopAbs_FORWARD
    # Orientation of a subshape occurrence belongs to its parent wire/shell,
    # not to the geometric carrier. Parent face bytes retain child orientations.
    return hashlib.sha256(entity_bytes(shape.Oriented(TopAbs_FORWARD))).hexdigest()


def entity_groups(cad, shape):
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    result = {}
    for name, kind, cast in (('faces', TopAbs_FACE, TopoDS.Face_s),
                             ('edges', TopAbs_EDGE, TopoDS.Edge_s),
                             ('vertices', TopAbs_VERTEX, TopoDS.Vertex_s)):
        indexed = cad.indexed(shape, kind)
        result[name] = [(cast(indexed.FindKey(i)), entity_hash(indexed.FindKey(i)),
                         BRep_Tool.Tolerance_s(cast(indexed.FindKey(i))))
                        for i in range(1, indexed.Extent()+1)]
    return result


def numerical_budget_pass(classification, tolerance, original_tolerance=None):
    if not math.isfinite(tolerance) or tolerance < 0:
        return False
    if classification == 'unchanged_exact_native_entity':
        return original_tolerance is not None and tolerance == original_tolerance
    return classification in ('modified_native_history', 'generated_native_history',
                              'new_or_modified_boundary_of_history_face') and tolerance <= NEW_BUDGET


def classify_history(cad, original, before, candidate, maker):
    """Unchanged means IsSame AND canonical native bytes captured before Build.

    New boundaries can lack direct fillet history. They are admitted only as
    subshapes of a history-generated/modified FACE; origin remains explicit.
    """
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    kinds = {'faces': TopAbs_FACE, 'edges': TopAbs_EDGE, 'vertices': TopAbs_VERTEX}
    all_old = [s for group in before.values() for s, _, _ in group]
    modified, generated = [], []
    for old in all_old:
        modified.extend(list(maker.Modified(old)))
        generated.extend(list(maker.Generated(old)))
    changed_faces = [s for s in modified+generated if s.ShapeType() == TopAbs_FACE]
    rows = {}
    for name, group in entity_groups(cad, candidate).items():
        records = []
        for index, (shape, digest, tolerance) in enumerate(group, 1):
            same = [(i, old_digest, old_tol) for i, (old, old_digest, old_tol) in enumerate(before[name], 1)
                    if shape.IsSame(old)]
            exact = [r for r in same if r[1] == digest]
            explicit_modified = any(shape.IsSame(s) for s in modified)
            explicit_generated = any(shape.IsSame(s) for s in generated)
            in_history_face = any(cad.indexed(face, kinds[name]).Contains(shape) for face in changed_faces)
            classification = ('unchanged_exact_native_entity' if exact else
                              'modified_native_history' if explicit_modified else
                              'generated_native_history' if explicit_generated else
                              'new_or_modified_boundary_of_history_face' if name != 'faces' and in_history_face else
                              'unclassified_rejected')
            old_tolerance = exact[0][2] if exact else None
            records.append({'candidate_id': index, 'classification': classification,
                'original_same_entity_ids': [r[0] for r in same], 'native_entity_sha256': digest,
                'tolerance_scan_units': tolerance, 'original_tolerance_if_unchanged': old_tolerance,
                'budget_pass': numerical_budget_pass(classification, tolerance, old_tolerance),
                'new_boundary_origin_not_inferred_as_exact_edge_history': classification == 'new_or_modified_boundary_of_history_face'})
        rows[name] = records
    return {'records': rows, 'all_entities_classified_and_within_budget': all(
        r['budget_pass'] for group in rows.values() for r in group),
        'unchanged_uses_IsSame_and_prebuild_canonical_serialization_not_shape_index': True,
        'subshape_root_occurrence_orientation_canonicalized_not_child_wire_orientation': True,
        'modified_or_generated_history_face_count_with_duplicates': len(changed_faces)}


def curve_surface_consistency(cad, shape):
    from OCP.Adaptor3d import Adaptor3d_CurveOnSurface
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
    from OCP.GeomLib import GeomLib_CheckCurveOnSurface
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopoDS import TopoDS
    ancestors = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, ancestors)
    edges = cad.indexed(shape, TopAbs_EDGE)
    pcurves, vertices = [], []
    for index in range(1, edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(index))
        if BRep_Tool.Degenerated_s(edge):
            raise ValueError('Degenerate edge requires a separately specified audit')
        curve = BRepAdaptor_Curve(edge)
        for face_shape in ancestors.FindFromKey(edge):
            face = TopoDS.Face_s(face_shape)
            uv = BRepAdaptor_Curve2d(edge, face)
            surface = BRepAdaptor_Surface(face, False)
            checker = GeomLib_CheckCurveOnSurface(curve, PARAMETER_SEARCH_TOLERANCE)
            checker.SetParallel(False)
            checker.Perform(Adaptor3d_CurveOnSurface(uv, surface))
            if not checker.IsDone() or checker.ErrorStatus() != 0:
                raise ValueError('Native curve-on-surface extremum search incomplete')
            value = checker.MaxDistance()
            allowance = max(BRep_Tool.Tolerance_s(edge), BRep_Tool.Tolerance_s(face))
            pcurves.append({'edge_id': index, 'max_distance_scan_units': value,
                'max_parameter': checker.MaxParameter(), 'declared_edge_face_tolerance': allowance,
                'within_declared_tolerance': math.isfinite(value) and value <= allowance,
                'within_absolute_new_budget': math.isfinite(value) and value <= NEW_BUDGET})
        indexed = cad.indexed(edge, TopAbs_VERTEX)
        for j in range(1, indexed.Extent()+1):
            vertex = TopoDS.Vertex_s(indexed.FindKey(j))
            parameter = BRep_Tool.Parameter_s(vertex, edge)
            distance = BRep_Tool.Pnt_s(vertex).Distance(curve.Value(parameter))
            allowance = max(BRep_Tool.Tolerance_s(vertex), BRep_Tool.Tolerance_s(edge))
            vertices.append({'edge_id': index, 'vertex_local_id': j, 'distance_scan_units': distance,
                'declared_vertex_edge_tolerance': allowance, 'within_declared_tolerance': distance <= allowance,
                'within_absolute_new_budget': distance <= NEW_BUDGET})
    return {'pcurves': pcurves, 'vertices': vertices,
        'method': 'GeomLib_CheckCurveOnSurface native numerical extremum search; vertex parameter evaluation',
        'formal_continuous_error_bound_or_physical_accuracy_claimed': False,
        'parameter_search_tolerance_not_geometric_allowance': PARAMETER_SEARCH_TOLERANCE,
        'all_within_declared_tolerance_and_absolute_budget': all(
            r['within_declared_tolerance'] and r['within_absolute_new_budget'] for r in pcurves+vertices)}


def protected_outer_wire(cad, source, candidate, seed):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    matching = []
    for face, _, _ in entity_groups(cad, source)['faces']:
        surface = BRepAdaptor_Surface(face, False)
        if surface.GetType() == GeomAbs_Plane:
            plane = surface.Plane()
            if (abs(abs(plane.Axis().Direction().Y())-1) <= 1e-12 and
                    abs(plane.Location().Y()-seed['center'][1]) <= 1e-9):
                matching.append(face)
    if len(matching) != 1:
        raise ValueError('Exactly one recorded cap plane required for protected outer wire')
    outer = BRepTools.OuterWire_s(matching[0])
    if outer.IsNull():
        raise ValueError('Native cap has no outer wire')
    old_edges = cad.indexed(outer,TopAbs_EDGE)
    after = entity_groups(cad,candidate)['edges']
    rows = []
    for index in range(1,old_edges.Extent()+1):
        edge = TopoDS.Edge_s(old_edges.FindKey(index)); digest = entity_hash(edge)
        matches = [j for j,(_,h,_) in enumerate(after,1) if h == digest]
        rows.append({'outer_wire_edge_number':index,'canonical_native_entity_sha256':digest,
                     'identical_candidate_edge_ids':matches,'unchanged_geometry_and_tolerance':bool(matches)})
    return {'selection':'BRepTools.OuterWire of the unique native cap plane, not radial samples',
            'edges':rows,'all_unchanged':len(rows)==4 and all(row['unchanged_geometry_and_tolerance'] for row in rows),
            'reference_circle_from_existing_model_not_new_fit_or_physical_measurement':True}


def empty_shape(cad, shape):
    from OCP.TopAbs import TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID
    return all(cad.indexed(shape, kind).Extent() == 0 for kind in
               (TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID))


def shape_record(cad, shape):
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID
    empty = empty_shape(cad, shape)
    volume, error = (0., 0.) if empty else local.bounded.adaptive_volume(shape)
    return {'empty_topologically': empty, 'valid': cad.valid(shape),
            'solids': cad.indexed(shape, TopAbs_SOLID).Extent(),
            'faces': cad.indexed(shape, TopAbs_FACE).Extent(),
            'edges': cad.indexed(shape, TopAbs_EDGE).Extent(),
            'volume_scan_units_cubed': volume, 'volume_relative_numerical_error_estimate': error}


def volume_reconciliation(before, after, added, removed):
    """OCCT returns RELATIVE quadrature estimates, not volume-unit errors."""
    records = (before,after,added,removed)
    if any(not math.isfinite(v) or not math.isfinite(e) or e < 0 for v,e in records):
        raise ValueError('Finite volume and nonnegative relative error estimates required')
    absolute_estimate = sum(abs(volume)*error for volume,error in records)
    difference = after[0]-before[0]
    boolean_difference = added[0]-removed[0]
    residual = abs(difference-boolean_difference)
    return {'before_volume_scan_units_cubed':before[0], 'after_volume_scan_units_cubed':after[0],
            'subtracted_volume_difference':difference, 'Boolean_added_minus_removed_volume':boolean_difference,
            'absolute_residual_scan_units_cubed':residual,
            'summed_absolute_quadrature_error_estimates_scan_units_cubed':absolute_estimate,
            'relative_error_estimates_converted_by_each_absolute_volume':True,
            'quadrature_estimates_are_not_geometric_error_bounds':True,
            'agrees_within_reported_quadrature_estimates':residual<=absolute_estimate,
            'not_a_manufacturing_tolerance_or_physical_mass_conservation_validation':True}


def filled_section(cad, shape, plane_center, normal, size):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    face = BRepBuilderAPI_MakeFace(cad.gp_Pln(cad.gp_Pnt(*plane_center), cad.gp_Dir(*normal)),
                                   -size, size, -size, size).Face()
    return constraints.boolean(BRepAlgoAPI_Common, face, shape)


def section_comparison(cad, source, candidate, roi_shape, section, size):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    before = filled_section(cad, source, section['center'], section['normal'], size)
    after = filled_section(cad, candidate, section['center'], section['normal'], size)
    added = constraints.boolean(BRepAlgoAPI_Cut, after, before)
    removed = constraints.boolean(BRepAlgoAPI_Cut, before, after)
    outside_add = constraints.boolean(BRepAlgoAPI_Cut, added, roi_shape)
    outside_remove = constraints.boolean(BRepAlgoAPI_Cut, removed, roi_shape)
    return {'plane_private': section, 'before_area_scan_units_squared': cad.area(before),
            'after_area_scan_units_squared': cad.area(after),
            'added_area_scan_units_squared': cad.area(added), 'removed_area_scan_units_squared': cad.area(removed),
            'added_outside_ROI': shape_record(cad, outside_add),
            'removed_outside_ROI': shape_record(cad, outside_remove),
            'outside_ROI_unchanged_native_boolean': empty_shape(cad, outside_add) and empty_shape(cad, outside_remove),
            'filled_planar_regions_from_native_face_solid_common_not_wire_area_sum': True,
            'formal_exact_region_proof': False}


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    started = time.monotonic()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    package_path = args.prepared_dir/'preparation-report.json'
    roi_path = args.roi_dir/'roi-proposal-report.json'
    v1_path = args.v1_dir/'junction-fillet-report.json'
    package, roi, v1 = [json.loads(p.read_text()) for p in (package_path, roi_path, v1_path)]
    paths = {'package': package_path, 'roi_report': roi_path, 'v1_report': v1_path,
             'source': Path(package['inputs_private']['intake']),
             'checkpoint': Path(package['inputs_private']['checkpoint']),
             'v1_candidate': args.v1_dir/'intake-junction-prototype.brep',
             'reservations': args.prepared_dir/'seat-guide-boss-reservations.brep',
             'outer_circle': args.prepared_dir/'outer-section-circle-reference.brep',
             'helper': Path(__file__), 'fillet_helper': Path(local.__file__),
             'constraint_helper': Path(constraints.__file__), 'preparation_helper': Path(prep.__file__),
             'ports_helper': Path(local.ports.__file__), 'bounded_helper': Path(local.bounded.__file__)}
    hashes = {k: local.ports.sha(p) for k,p in paths.items()}
    if (hashes['source'] != prep.EXPECTED_INTAKE or hashes['source'] != package['inputs_sha256']['intake']
            or hashes['v1_candidate'] != EXPECTED_CANDIDATE or v1['candidate_BRep_sha256'] != EXPECTED_CANDIDATE
            or v1['status'] != 'rejected_native_or_tolerance_audit'
            or hashes['checkpoint'] != package['inputs_sha256']['checkpoint']
            or roi['inputs_sha256']['prepared_report'] != hashes['package']
            or hashes['reservations'] != package['protections']['seat_guide_and_boss_reservations']['export']['sha256']
            or hashes['outer_circle'] != package['protections']['first_section_outer_circle']['export']['sha256']):
        raise ValueError('Exact original/rejected candidate/private protection provenance required')
    checkpoint = json.loads(paths['checkpoint'].read_text())
    args.output.mkdir(mode=0o700, parents=True)
    policy = {'schema': 'local-junction-numerical-CAD-budget-preregistration/v2',
        'audit_revision': 3,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'inputs_sha256': hashes,
        'source_reference': SOURCE_URL, 'OCCT_default_Tesp_and_TApp3d': 1e-4,
        'new_or_locally_modified_entity_absolute_tolerance_budget_scan_units': NEW_BUDGET,
        'unchanged_native_entities_tolerance_and_geometry_must_be_unchanged': True,
        'reconstruction_radius_scan_units': .25, 'constructor_mode': 'default_no_parameter_override',
        'v1_rejection_retained': True, 'no_tolerance_setter_or_repair_permitted': True,
        'ROI_policy': roi['policy'], 'ROI_is_authorized_box_intersection_authorized_cylinder_not_calculation_mask': True,
        'section_offsets_at_first_cap_scan_units': [-5e-5, 0., 5e-5],
        'section_policy': 'compare complete filled planar gas regions; changes INSIDE authorized ROI are design changes, outside must be empty native Boolean differences; far planes unchanged',
        'outer_circle_and_seat_guide_reservations_protected_separately': True,
        'outer_wire_all_four_native_edges_and_tolerances_must_match': True,
        'source_native_serialization_must_not_change_in_memory_during_replay': True,
        'independent_volume_reconciliation': 'compare Boolean added-minus-removed with native adaptive after-minus-before; each OCCT RELATIVE error estimate is multiplied by its absolute volume before summation; estimates are not geometric error bounds',
        'a_volume_reconciliation_failure_blocks_complete_local_geometric_qualification': True,
        'no_acceptance_by_zero_volume_only': True, 'length_unit': 'unverified_scan_unit',
        'numerical_kernel_acceptance_not_formal_exact_or_physical_validation': True,
        'no_master_integration_or_manufacturing_authorization': True}
    local.ports.save(args.output/'preregistration.json', policy)
    report = {'schema': 'private-local-junction-numerical-CAD-budget/v2',
        'preregistration_sha256': local.ports.sha(args.output/'preregistration.json'),
        'inputs_sha256': hashes, 'OCP_version': OCP.__version__, 'status': 'running',
        'v1_rejection_retained': True, 'no_tolerances_modified': True,
        'master_modified': False, 'manufacturing_authorized': False, 'thermal_or_CFD_validation': False}
    def save(stage):
        report['elapsed_seconds'] = time.monotonic()-started
        local.ports.save(args.output/(stage+'.json'), report)
    try:
        cad = local.ports.design.CAD()
        source = local.read_native(paths['source'])
        source_serialization = entity_bytes(source)
        before = entity_groups(cad, source)
        selected = local.branch_cap_edges(cad, source, checkpoint['seed_sections_private'][0])
        if len(selected) != 3:
            raise ValueError('Expected three branch/cap edges')
        maker, build = local.build_fillet(source, [e for _,e,_ in selected], .25)
        report['replay_build'] = build
        if not build['done']:
            raise ValueError('Replay construction failed')
        candidate = maker.Shape()
        report['source_in_memory_serialization_unchanged_after_build'] = source_serialization == entity_bytes(source)
        if not report['source_in_memory_serialization_unchanged_after_build']:
            raise ValueError('Constructor altered the source native representation in memory')
        output = args.output/'replayed-candidate.brep'
        BRepTools.Write_s(candidate, str(output)); output.chmod(0o600)
        report['replayed_candidate_sha256'] = local.ports.sha(output)
        report['candidate_identical_to_v1_serialization'] = report['replayed_candidate_sha256'] == EXPECTED_CANDIDATE
        if not report['candidate_identical_to_v1_serialization']:
            raise ValueError('Different replay candidate; original candidate qualification stopped')
        report['history'] = classify_history(cad, source, before, candidate, maker)
        reread = local.read_native(output)
        report['reread_topology'] = local.topology(cad, reread)
        report['reread_BOP'] = local.ports.bop_check(reread)
        report['reread_serialization_identical'] = entity_bytes(candidate) == entity_bytes(reread)
        save('stage-01-history')
        if (not report['history']['all_entities_classified_and_within_budget'] or
                not report['reread_topology']['valid'] or report['reread_topology']['solids'] != 1 or
                report['reread_BOP']['has_faulty'] or not report['reread_serialization_identical']):
            raise ValueError('History/local budget/native reread gate failed')
        report['geometry_consistency'] = curve_surface_consistency(cad, reread)
        save('stage-02-consistency')
        if not report['geometry_consistency']['all_within_declared_tolerance_and_absolute_budget']:
            raise ValueError('Actual native curve/surface or vertex discrepancy exceeds declared tolerance/budget')
        policy_roi = roi['policy']; bounds = policy_roi['authorized_box_private']
        seed = checkpoint['seed_sections_private'][0]; center = seed['center']
        cylinder = BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(center[0], bounds[1]-1., center[2]),
            cad.gp_Dir(0,1,0)), policy_roi['authorized_cylinder_radius_scan_units'], bounds[4]-bounds[1]+2.).Shape()
        roi_shape = constraints.boolean(BRepAlgoAPI_Common, prep.box_shape(bounds), cylinder)
        added = constraints.boolean(BRepAlgoAPI_Cut, candidate, source)
        removed = constraints.boolean(BRepAlgoAPI_Cut, source, candidate)
        report['delta'] = {'added': shape_record(cad, added), 'removed': shape_record(cad, removed)}
        volume_before, error_before = local.bounded.adaptive_volume(source)
        volume_after, error_after = local.bounded.adaptive_volume(candidate)
        report['volume_reconciliation'] = volume_reconciliation((volume_before,error_before),(volume_after,error_after),
            tuple(report['delta']['added'][k] for k in ('volume_scan_units_cubed','volume_relative_numerical_error_estimate')),
            tuple(report['delta']['removed'][k] for k in ('volume_scan_units_cubed','volume_relative_numerical_error_estimate')))
        report['delta']['added_outside_ROI'] = shape_record(cad, constraints.boolean(BRepAlgoAPI_Cut, added, roi_shape))
        report['delta']['removed_outside_ROI'] = shape_record(cad, constraints.boolean(BRepAlgoAPI_Cut, removed, roi_shape))
        report['delta']['whole_solid_difference_confined_to_ROI_native_boolean'] = all(
            report['delta'][name]['empty_topologically'] for name in ('added_outside_ROI','removed_outside_ROI'))
        save('stage-03-locality')
        if not report['delta']['whole_solid_difference_confined_to_ROI_native_boolean']:
            raise ValueError('A native solid difference extends outside authorized convex ROI')
        circle = local.read_native(paths['outer_circle']); reservations = local.read_native(paths['reservations'])
        differences = cad.compound([added, removed])
        report['protections'] = {'delta_to_outer_reference_circle_distance': cad.distance(differences, circle),
            'delta_to_seat_guide_boss_reservations_distance': cad.distance(differences, reservations),
            'no_original_body_distance_relabelled_as_final_wall_thickness': True,
            'actual_body_wall_thickness': None}
        report['protections']['protected_native_outer_wire'] = protected_outer_wire(cad,source,candidate,seed)
        # Every source face outside the local box must remain byte-identical,
        # including branch bank-end faces. Box is a conservative ROI superset.
        after_faces = entity_groups(cad, candidate)['faces']; distant_faces = []
        for index, (face,digest,tolerance) in enumerate(before['faces'],1):
            box = prep.native_bounds(face)
            separated = any(box[k+3] < bounds[k] or box[k] > bounds[k+3] for k in range(3))
            if separated:
                matches = [j for j,(f,d,t) in enumerate(after_faces,1) if d == digest and t == tolerance]
                distant_faces.append({'source_face_id': index, 'identical_candidate_face_ids': matches,
                                      'unchanged': bool(matches)})
        report['protections']['all_faces_wholly_outside_ROI_box'] = distant_faces
        save('stage-04-protections')
        if (not distant_faces or not all(row['unchanged'] for row in distant_faces) or
                not report['protections']['protected_native_outer_wire']['all_unchanged'] or
                report['protections']['delta_to_outer_reference_circle_distance'] <= NEW_BUDGET or
                report['protections']['delta_to_seat_guide_boss_reservations_distance'] <= NEW_BUDGET):
            raise ValueError('Separate outer ring/distant face/seat-guide protection failed')
        full_box = prep.native_bounds(cad.compound([source,candidate]))
        size = 4*max(abs(v) for v in full_box)+10
        report['sections'] = []
        sections = [dict(row) for row in checkpoint['seed_sections_private']]
        for offset in (-5e-5,5e-5):
            shifted = dict(seed); shifted['center'] = [center[0],center[1]+offset,center[2]]
            shifted['offset_scan_units'] = offset; sections.append(shifted)
        for index, section in enumerate(sections,1):
            row = section_comparison(cad, source, candidate, roi_shape, section, size)
            row['section_number'] = index; report['sections'].append(row)
            save(f'stage-05-section-{index:02d}')
            if not row['outside_ROI_unchanged_native_boolean']:
                raise ValueError('Filled gas section changed outside authorized ROI')
        report['status'] = 'local_approximate_CAD_within_preregistered_numerical_budget_not_head_qualification'
        if not report['volume_reconciliation']['agrees_within_reported_quadrature_estimates']:
            report['status'] = 'local_budget_and_protection_screens_passed_volume_reconciliation_unresolved'
    except Exception as exc:
        report['status'] = 'stopped_partial_or_rejected_v2'
        report['stop_reason'] = type(exc).__name__+': '+str(exc)
    report['all_input_files_unchanged'] = all(local.ports.sha(p) == hashes[k] for k,p in paths.items())
    if not report['all_input_files_unchanged']:
        report['status'] = 'rejected_provenance_changed'
    save('report')
    print(json.dumps({'status': report['status'], 'stop_reason': report.get('stop_reason'),
                      'elapsed_seconds': report['elapsed_seconds'], 'output': str(args.output)}))
    return 0 if report['status'].startswith('local_approximate_CAD_') else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared-dir','roi-dir','v1-dir','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(300,305))
    raise SystemExit(run(parser.parse_args()))
