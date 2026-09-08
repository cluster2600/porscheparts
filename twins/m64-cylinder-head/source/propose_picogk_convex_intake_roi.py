#!/usr/bin/env python3
"""Bound a PROPOSED convex box/interior-cylinder ROI, without running PicoGK.

The interior cylinder is infinite along the recorded Y axis; the box limits Y.
OCCT control-pole subarc boxes bound whole curves, not only sampled points.
No native shape, original package, surface or functional interface is changed.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import time

import prepare_picogk_intake_junction as prep


def directed_float(value, upper):
    value = Fraction(value)
    result = float(value)
    if (upper and Fraction(result) < value) or (not upper and Fraction(result) > value):
        result = math.nextafter(result, math.inf if upper else -math.inf)
    return result


def sqrt_bound(value, upper):
    value = Fraction(value)
    if value < 0:
        raise ValueError('Nonnegative squared radius required')
    result = math.sqrt(float(value))
    for _ in range(4):
        exact = Fraction(result) ** 2
        if (upper and exact >= value) or (not upper and exact <= value):
            return result
        result = math.nextafter(result, math.inf if upper else -math.inf)
    raise ValueError('Could not produce directed square-root bound')


def radial_box_upper(bounds, center):
    x = max(abs(Fraction(bounds[0])-Fraction(center[0])),
            abs(Fraction(bounds[3])-Fraction(center[0])))
    z = max(abs(Fraction(bounds[2])-Fraction(center[2])),
            abs(Fraction(bounds[5])-Fraction(center[2])))
    return sqrt_bound(x*x + z*z, True)


def radial_point_lower(point, center):
    x, z = Fraction(point[0])-Fraction(center[0]), Fraction(point[2])-Fraction(center[2])
    return sqrt_bound(x*x + z*z, False)


def point_inside_convex_roi(point, bounds, center, radius):
    if (len(point) != 3 or len(bounds) != 6 or len(center) != 3 or
            not all(math.isfinite(v) for v in [*point, *bounds, *center, radius]) or
            radius <= 0 or any(bounds[k] >= bounds[k+3] for k in range(3))):
        raise ValueError('Finite nonempty convex ROI required')
    if not all(bounds[k] <= point[k] <= bounds[k+3] for k in range(3)):
        return False
    x, z = Fraction(point[0])-Fraction(center[0]), Fraction(point[2])-Fraction(center[2])
    return x*x + z*z <= Fraction(radius)**2


def triangle_inside_convex_roi(triangle, bounds, center, radius):
    if len(triangle) != 3:
        raise ValueError('Three triangle vertices required')
    # Box and solid circular cylinder are convex; their intersection is convex.
    # Every barycentric point of three contained vertices is therefore inside.
    return all(point_inside_convex_roi(point, bounds, center, radius) for point in triangle)


def cylinder_policy(reference_radius, outer_bounds, band=.4, buffer=3*.2):
    if (not all(math.isfinite(v) for v in [reference_radius, band, buffer, *outer_bounds]) or
            reference_radius <= 0 or band <= 0 or buffer <= 0):
        raise ValueError('Finite positive reference radius/band/buffer required')
    authorized = directed_float(Fraction(reference_radius)-Fraction(band), False)
    calculation = directed_float(Fraction(authorized)-Fraction(buffer), False)
    inner_bounds = [directed_float(Fraction(outer_bounds[k])+Fraction(buffer), True) for k in range(3)] + [
                    directed_float(Fraction(outer_bounds[k+3])-Fraction(buffer), False) for k in range(3)]
    if calculation <= 0 or any(inner_bounds[k] >= inner_bounds[k+3] for k in range(3)):
        raise ValueError('Contracted convex ROI is empty')
    return {'reference_radius_scan_units': reference_radius,
            'protected_radial_band_hypothesis_scan_units': band,
            'construction_buffer_hypothesis_scan_units': buffer,
            'authorized_cylinder_radius_scan_units': authorized,
            'calculation_cylinder_radius_scan_units': calculation,
            'authorized_box_private': list(outer_bounds), 'calculation_box_private': inner_bounds,
            'cylinder_radius_rounding': 'downward; radial band and buffer are never weakened',
            'box_contraction_rounding': 'inward',
            'band_is_not_OEM_or_physical_tolerance': True}


def radius_status(radius, clearance_lower, clearance_upper):
    if radius <= clearance_lower:
        return 'radius_neighborhood_contained_by_conservative_bound'
    if radius > clearance_upper:
        return 'radius_neighborhood_cannot_fit_without_clipping'
    return 'inconclusive_between_bounds'


def edge_radial_bounds(edge, center, segments=128):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRep import BRep_Tool
    from OCP.BndLib import BndLib_Add3dCurve
    from OCP.Bnd import Bnd_Box
    from OCP.GeomAbs import GeomAbs_BSplineCurve
    from OCP.Precision import Precision
    curve = BRepAdaptor_Curve(edge)
    if curve.GetType() != GeomAbs_BSplineCurve:
        raise ValueError('This bound is restricted to the recorded rational B-spline edges')
    spline = curve.BSpline()
    weights = [spline.Weight(i) for i in range(1, spline.NbPoles()+1)]
    if any(not math.isfinite(weight) or weight <= 0 for weight in weights):
        raise ValueError('Positive finite weights required for control-hull bounds')
    tolerance = max(BRep_Tool.Tolerance_s(edge), Precision.Confusion_s())
    first, last = curve.FirstParameter(), curve.LastParameter()
    if segments < 1 or segments > 256 or not math.isfinite(first+last) or first >= last:
        raise ValueError('Bounded finite curve intervals required')
    boxes = []
    samples = []
    for index in range(segments):
        start, end = first+(last-first)*index/segments, first+(last-first)*(index+1)/segments
        box = Bnd_Box()
        # Add (not sampled extrema/AddOptimal) uses the B-spline control poles
        # of the bounded arc and enlarges the result by the supplied tolerance.
        BndLib_Add3dCurve.Add_s(curve, start, end, tolerance, box)
        if box.IsVoid() or box.IsOpen():
            raise ValueError('Unbounded subarc')
        boxes.append(list(box.Get()))
        for parameter in (start, (start+end)/2, end):
            point = curve.Value(parameter)
            samples.append([point.X(), point.Y(), point.Z()])
    upper = max(radial_box_upper(box, center) for box in boxes)
    # Samples provide a LOWER bound on the maximum, never its upper bound.
    # Deduct the native numerical tolerance so the infeasibility witness is
    # not based on a rounded point exaggerating the radius.
    lower = max(0., directed_float(Fraction(max(radial_point_lower(point, center) for point in samples)) -
                                  Fraction(tolerance), False))
    if lower > upper:
        raise ValueError('Native curve bounds disagree with sampled lower bound')
    whole_bounds = [min(box[k] for box in boxes) for k in range(3)] + [
                    max(box[k+3] for box in boxes) for k in range(3)]
    return {'radial_max_lower_bound_scan_units': lower, 'radial_max_upper_bound_scan_units': upper,
            'subarc_count': segments, 'positive_control_weights': True,
            'native_tolerance_reserve_scan_units': tolerance,
            'complete_edge_bounds_private': whole_bounds, 'subarc_boxes_private': boxes,
            'upper_bound_from_continuous_control_pole_boxes_not_samples': True,
            'lower_bound_from_evaluated_points_minus_native_tolerance': True,
            'bounds_are_native_kernel_numerical_not_formal_original_curve_rational_certificates': True}


def coplanar_cap_assessment(cad, source, seed):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRep import BRep_Tool
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.Precision import Precision
    faces = cad.indexed(source, cad.TopAbs_FACE)
    matching = []
    tolerances = [Precision.Confusion_s()]
    for index in range(1, faces.Extent()+1):
        face = cad.TopoDS.Face_s(faces.FindKey(index))
        surface = BRepAdaptor_Surface(face, False)
        tolerance = BRep_Tool.Tolerance_s(face)
        tolerances.append(tolerance)
        if surface.GetType() == GeomAbs_Plane:
            plane = surface.Plane()
            if abs(abs(plane.Axis().Direction().Y())-1) <= 1e-12 and plane.Distance(cad.gp_Pnt(*seed['center'])) <= tolerance:
                matching.append(index)
    edges = cad.indexed(source, cad.TopAbs_EDGE)
    tolerances.extend(BRep_Tool.Tolerance_s(cad.TopoDS.Edge_s(edges.FindKey(i))) for i in range(1, edges.Extent()+1))
    return {'coplanar_face_ids_private': matching, 'coplanar_cap_present': bool(matching),
            'first_plane_section_wires_are_not_a_filled_gas_region_or_area': True,
            'first_preparation_section_edge_count_not_loop_or_cavity_count': True,
            'off_plane_sections_required_before_any_area_equality_claim': bool(matching),
            'off_plane_epsilon_PROPOSED_scan_units': 10*max(tolerances),
            'epsilon_is_numeric_separation_hypothesis_not_a_physical_tolerance': True,
            'off_plane_minus_and_plus_sections_executed': False,
            'full_gas_section_area': None,
            'required_definition': 'compare oriented closed gas regions on Y0-epsilon and Y0+epsilon; classify loops/nesting; never sum wire areas blindly'}


def run(args):
    import OCP
    started = time.monotonic()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    package_path = args.prepared_dir/'preparation-report.json'
    package = json.loads(package_path.read_text())
    source_path = Path(package['inputs_private']['intake'])
    checkpoint_path = Path(package['inputs_private']['checkpoint'])
    paths = {'prepared_report': package_path, 'native_intake': source_path, 'checkpoint': checkpoint_path,
             'proposal_helper': Path(__file__), 'preparation_helper': Path(prep.__file__),
             'edge_identification_helper': Path(prep.local.__file__)}
    hashes = {name: prep.local.ports.sha(path) for name, path in paths.items()}
    checkpoint = json.loads(checkpoint_path.read_text())
    if (hashes['native_intake'] != prep.EXPECTED_INTAKE or
            hashes['native_intake'] != package['inputs_sha256']['intake'] or
            hashes['checkpoint'] != package['inputs_sha256']['checkpoint'] or
            checkpoint['exports']['native_BRep_sha256'] != hashes['native_intake']):
        raise ValueError('Prepared package and native input hashes disagree')
    seed = checkpoint['seed_sections_private'][0]
    if seed['normal'] not in ([0.,1.,0.], [0.,-1.,0.]):
        raise ValueError('Recorded reference cylinder must have Y axis')
    policy = cylinder_policy(seed['radius'], package['ROI_proposal']['authorized_box_PROPOSED_private'])
    args.output.mkdir(parents=True, mode=0o700)
    if args.output.stat().st_mode & 0o077:
        raise ValueError('Private output directory required')
    preregistration = {'schema': 'm64-proposed-convex-intake-ROI-preregistration/v1',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'inputs_sha256': hashes,
        'candidate_radii_scan_units': [1., .5, .25], 'voxel_scan_units': .2,
        'subarc_bound_count_per_edge': 128, 'policy': policy,
        'mask_definition': 'box INTERSECT infinite solid cylinder coaxial with first recorded reference circle',
        'no_automatic_geometry_execution_or_integration': True}
    prep.local.ports.save(args.output/'roi-preregistration.json', preregistration)
    preregistration_sha = prep.local.ports.sha(args.output/'roi-preregistration.json')
    cad = prep.local.ports.design.CAD()
    source = prep.local.read_native(source_path)
    selected = prep.local.branch_cap_edges(cad, source, seed)
    if len(selected) != 3 or [index for index, _, _ in selected] != [row['native_edge_id_in_this_source_only'] for row in package['selected_edges']]:
        raise ValueError('Three original selected edges must match the preparation package')
    rows = []
    for index, edge, _ in selected:
        bounds = edge_radial_bounds(edge, seed['center'])
        row = {'source_edge_id': index, **bounds, 'clearance_intervals': {}}
        for role in ('authorized', 'calculation'):
            radius = policy[f'{role}_cylinder_radius_scan_units']
            lower = directed_float(Fraction(radius)-Fraction(bounds['radial_max_upper_bound_scan_units']), False)
            upper = directed_float(Fraction(radius)-Fraction(bounds['radial_max_lower_bound_scan_units']), True)
            box = policy[f'{role}_box_private']
            edge_box = bounds['complete_edge_bounds_private']
            margins = [Fraction(edge_box[k])-Fraction(box[k]) for k in range(3)] + [
                       Fraction(box[k+3])-Fraction(edge_box[k+3]) for k in range(3)]
            box_lower = directed_float(min(margins), False)
            row['clearance_intervals'][role] = {'cylinder_radial_clearance_lower': lower,
                'cylinder_radial_clearance_upper': upper, 'box_boundary_clearance_lower': box_lower,
                'full_convex_ROI_clearance_lower': min(lower, box_lower),
                'edge_contained_by_continuous_bounds': lower > 0 and box_lower > 0}
        rows.append(row)
        prep.local.ports.save(args.output/f'edge-{index:02d}-bounds.json', row)
    lower = min(row['clearance_intervals']['calculation']['full_convex_ROI_clearance_lower'] for row in rows)
    # This upper bound on limiting clearance comes from a point on an edge and
    # the cylindrical wall. Other box boundaries can only reduce the clearance.
    upper = min(row['clearance_intervals']['calculation']['cylinder_radial_clearance_upper'] for row in rows)
    radius_rows = [{'radius_scan_units': radius, 'radius_over_voxel_size': radius/.2,
                    'clearance_screen': radius_status(radius, lower, upper)} for radius in (1., .5, .25)]
    feasible = [row['radius_scan_units'] for row in radius_rows
                if row['clearance_screen'] == 'radius_neighborhood_contained_by_conservative_bound']
    # A cylinder can intersect a box trivially yet leave the target edges out.
    # Here one contained source edge proves nonemptiness of the convex region.
    all_contained = all(row['clearance_intervals']['calculation']['edge_contained_by_continuous_bounds'] for row in rows)
    report = {'schema': 'm64-private-proposed-convex-intake-ROI-bound/v1',
        'preregistration_sha256': preregistration_sha, 'inputs_sha256': hashes,
        'OCP_version': OCP.__version__, 'policy': policy, 'cylinder_axis_center_private': seed['center'],
        'source_registration_reapplied': False, 'edges': rows,
        'all_three_edges_contained_in_authorized_and_calculation_regions': all(
            row['clearance_intervals'][role]['edge_contained_by_continuous_bounds'] for row in rows for role in ('authorized', 'calculation')),
        'calculation_domain_nonempty_proved_by_contained_edge': all_contained,
        'limiting_calculation_clearance_interval_scan_units': [lower, upper],
        'radii': radius_rows, 'smallest_geometrically_fitting_radius_proposal': min(feasible) if feasible else None,
        'radius_neighborhood_is_not_a_proof_of_complete_morphological_closing_or_full_fillet': True,
        'one_point_six_box_inflation_from_previous_pack_not_recomputed_to_force_pass': True,
        'sampling_is_only_used_for_radial_max_lower_bound': True,
        'convexity_proof': 'intersection of two convex sets; three contained triangle vertices imply its whole barycentric support is contained',
        'outer_reference_cylinder_is_excluded_by_positive_radial_band': policy['authorized_cylinder_radius_scan_units'] < seed['radius'],
        'surface_equality_outside_ROI_and_existing_sections_still_required': True,
        'cap_and_section_semantics': coplanar_cap_assessment(cad, source, seed),
        'resolution_adequacy_and_nonzero_added_volume': 'untested',
        'status': 'proposal_awaiting_main_approval' if all_contained and feasible else 'blocked_no_proved_feasible_local_radius',
        'native_input_modified': False, 'previous_package_modified': False,
        'PicoGK_executed': False, 'native_integration_performed': False, 'manufacturing_authorized': False,
        'elapsed_seconds': time.monotonic()-started}
    if any(prep.local.ports.sha(path) != hashes[name] for name, path in paths.items()) or prep.local.ports.sha(args.output/'roi-preregistration.json') != preregistration_sha:
        raise ValueError('Input/code/preregistration changed during bounds audit')
    report['source_files_unchanged'] = True
    prep.local.ports.save(args.output/'roi-proposal-report.json', report)
    print(json.dumps({'status': report['status'], 'limiting_clearance_interval': [lower, upper],
                      'radii': radius_rows, 'output': str(args.output), 'PicoGK_executed': False}))
    return 0 if report['status'] == 'proposal_awaiting_main_approval' else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))
