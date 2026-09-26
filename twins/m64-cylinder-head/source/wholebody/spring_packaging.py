#!/usr/bin/env python3
"""Private nominal spring-space audit on the exact V5 body; no body modification.

This is an annular keep-out envelope, not spring wire, a fitted spring kit, or
proof of physical collision. Section display sampling follows render_sections.py.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

from render_v5_v2 import PINS, preflight, save, sha

CATALOG = 'https://www.supertechperformance.com/dl-400298/2026-Catalog_WEB-sprd.pdf'
# Published nominal spring dimensions, sheet 22; not toleranced supplier CAD.
SPRING = {'id': 'SPR-H1021D', 'outer_diameter_mm': 30., 'inner_diameter_mm': 15.5,
          'installed_height_mm': 40.4, 'coil_bind_height_mm': 22.7}
LIFTS = {'intake': 11.5, 'exhaust': 9.6}


def stack(height, bind, lift, tip=82., guide_top=55., tip_allowance=5.):
    """Positive lift moves the retainer toward the fixed spring seat/guide."""
    values = (height, bind, lift, tip, guide_top, tip_allowance)
    if any(isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('positive_finite_stack_dimensions_required')
    if bind >= height or lift >= height or guide_top >= tip or tip_allowance + height >= tip:
        raise ValueError('invalid_axial_stack')
    retainer = tip - tip_allowance
    return {'seat_axial': retainer - height, 'retainer_closed_axial': retainer,
            'retainer_full_lift_axial': retainer - lift,
            'compressed_height': height - lift, 'bind_reserve': height - lift - bind,
            'retainer_to_guide_at_full_lift': retainer - lift - guide_top,
            'stem_tip_to_guide_at_full_lift': tip - lift - guide_top}


def envelope_clear(volume, minimum_distance):
    # No positive engineering running clearance is inferred from this numerical test.
    return (math.isfinite(volume) and math.isfinite(minimum_distance)
            and 0. <= volume <= 1e-7 and minimum_distance > 1e-7)


def section_curves(cad, shape, x):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    operation = cad.BRepAlgoAPI_Section(shape, cad.gp_Pln(cad.gp_Pnt(x, 0, 0), cad.gp_Dir(1, 0, 0)), False)
    operation.SetNonDestructive(True)
    operation.SetRunParallel(False)
    operation.Build()
    if not operation.IsDone():
        raise ValueError('native_section_failed')
    edges = cad.indexed(operation.Shape(), cad.TopAbs_EDGE)
    curves = []
    for i in range(1, edges.Extent() + 1):
        curve = BRepAdaptor_Curve(cad.TopoDS.Edge_s(edges.FindKey(i)))
        a, b = curve.FirstParameter(), curve.LastParameter()
        if not math.isfinite(a + b):
            raise ValueError('unbounded_section_curve')
        points = [curve.Value(a + (b - a) * j / 40) for j in range(41)]
        curves.append([[point.Y(), point.Z()] for point in points])
    return curves


def diagram(path, sections, tip_allowance):
    # ponytail: native section curves sampled for display, not a metrology export.
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
           '<rect width="1600" height="900" fill="#14212b"/>',
           '<g font-family="sans-serif" fill="#edf3f8">',
           '<text x="40" y="48" font-size="29">V5 / V2 — espace nécessaire aux quatre ressorts</text>',
           '<text x="40" y="80" font-size="18">Coupes du corps CAO réel ; enveloppes nominales, pas des ressorts détaillés</text>']
    colors = {'body': '#b9c5cd', 'envelope': '#efb84f', 'overlap': '#ff6262'}
    for panel, section in enumerate(sections):
        svg.append(f'<text x="{40 + 780 * panel}" y="135" font-size="20">Coupe X = {section["x"]:+.1f} unités du scan</text>')
        for role in ('body', 'envelope', 'overlap'):
            for curve in section['curves'][role]:
                # Equal scale in both axes; camera changes cannot hide interference.
                points = ' '.join(f'{65 + panel * 780 + (y + 90) * 3.25:.2f},{630 - z * 3.25:.2f}' for y, z in curve)
                svg.append(f'<polyline points="{points}" fill="none" stroke="{colors[role]}" stroke-width="{1 if role == "body" else 2.3}"/>')
    svg += ['<text x="40" y="735" font-size="19" fill="#b9c5cd">Gris : corps conservé</text>',
            '<text x="370" y="735" font-size="19" fill="#efb84f">Jaune : place réservée aux ressorts</text>',
            '<text x="940" y="735" font-size="19" fill="#ff6262">Rouge : intersection avec le corps</text>',
            f'<text x="40" y="780" font-size="18">SPR-H1021D : Ø30 / Ø15,5 / H40,4 mm nominaux ; recul coupelle-sommet de tige de {tip_allowance:g} mm supposé.</text>',
            '<text x="40" y="817" font-size="18">Pas de découpe du corps. Coupelles, clavettes, sièges de ressorts et tolérances ne sont pas modélisés.</text>',
            '<text x="40" y="854" font-size="18">Hypothèse 1 unité/mm non étalonnée. Aucun agrément de fabrication ni validation à chaud.</text>',
            '</g></svg>']
    with path.open('x') as stream:
        stream.write('\n'.join(svg) + '\n')


def run(root, out, tip_allowance):
    import OCP
    from OCP.BinTools import BinTools, BinTools_FormatVersion_VERSION_3
    from OCP.TopoDS import TopoDS_Shape
    from OCP.TopTools import TopTools_ListOfShape
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('exact_OCP_runtime_required')
    start = time.monotonic()
    preflight(root)
    source_paths = [Path(__file__), Path(__file__).with_name('render_v5_v2.py'), Path(design.__file__)]
    source_hashes = {p.name: sha(p) for p in source_paths}
    registration = json.loads((root / 'registration.json').read_text())
    rows = registration['tools_private']
    expected = {f'{bank}_{i}' for bank in LIFTS for i in (1, 2)}
    if len(rows) != 4 or {r['name'] for r in rows} != expected:
        raise ValueError('four_registered_axes_required')
    cad = design.CAD()
    effective_fuzzy_values = []
    def operation(cls, first, second):
        arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
        arguments.Append(first)
        tools.Append(second)
        job = cls()
        job.SetArguments(arguments)
        job.SetTools(tools)
        job.SetNonDestructive(True)
        job.SetRunParallel(False)
        job.SetFuzzyValue(0.)
        job.Build()
        if not job.IsDone() or job.Shape().IsNull():
            raise ValueError('native_boolean_failed')
        effective_fuzzy_values.append(job.FuzzyValue())
        return job.Shape()
    body = TopoDS_Shape()
    if not BinTools.Read_s(body, str(root / 'candidate.binbrep')) or not cad.valid(body) or cad.indexed(body, cad.TopAbs_SOLID).Extent() != 1:
        raise ValueError('one_valid_exact_body_required')
    os.umask(0o077)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {'schema': 'private-V5-V2-spring-packaging/v1', 'inputs_sha256': PINS,
              'source_sha256': source_hashes, 'OCP_version': OCP.__version__,
              'spring_nominal_catalog_values': SPRING, 'catalog_url': CATALOG, 'catalog_pdf_sheet': 22,
              'tip_allowance_design_hypothesis': tip_allowance,
              'V2_tip_axial_from_retained_build': 82., 'V2_guide_top_axial': 55.,
              'unit': 'scan_units_using_uncertified_1_unit_per_mm_registration',
              'classification': 'nominal_required_space_not_actual_spring_or_complete_head',
              'body_modified': False, 'spring_kit_compatible': False, 'manufacturing_authorized': False,
              'wire_retainer_locks_spring_seat_seal_and_tolerances_modeled': False,
              'thermal_or_dynamics_validation': False, 'rows': []}
    shapes = []
    for row in rows:
        name = row['name']
        bank = name.split('_')[0]
        origin, axis = row['axis_origin'], row['axis_direction']
        if (row['guide_axial_interval'] != [20., 55.] or abs(math.dist(axis, [0., 0., 0.]) - 1.) > 1e-12
                or axis[0] != 0 or row['guide_OD'] != 11.):
            raise ValueError('exact_registered_guide_required')
        axial = stack(SPRING['installed_height_mm'], SPRING['coil_bind_height_mm'], LIFTS[bank], tip_allowance=tip_allowance)
        base = [c + axial['seat_axial'] * u for c, u in zip(origin, axis)]
        direction = cad.gp_Ax2(cad.gp_Pnt(*base), cad.gp_Dir(*axis))
        outer = cad.BRepPrimAPI_MakeCylinder(direction, SPRING['outer_diameter_mm'] / 2, SPRING['installed_height_mm']).Shape()
        inner = cad.BRepPrimAPI_MakeCylinder(direction, SPRING['inner_diameter_mm'] / 2, SPRING['installed_height_mm']).Shape()
        envelope = operation(cad.BRepAlgoAPI_Cut, outer, inner)
        common = operation(cad.BRepAlgoAPI_Common, body, envelope)
        if not cad.valid(envelope) or not cad.valid(common):
            raise ValueError('invalid_native_envelope_or_intersection')
        volume, distance = cad.volume(common), cad.distance(body, envelope)
        nominal_volume = math.pi / 4 * (30. ** 2 - 15.5 ** 2) * 40.4
        if not math.isclose(cad.volume(envelope), nominal_volume, rel_tol=1e-10):
            raise ValueError('envelope_analytic_volume_cross_check_failed')
        item = {'name': name, 'axial_stack': axial, 'body_intersection_scan_units_cubed': volume,
                'envelope_volume_scan_units_cubed': nominal_volume,
                'occupied_envelope_fraction': volume / nominal_volume, 'minimum_distance_scan_units': distance,
                'nominal_envelope_clear': envelope_clear(volume, distance)}
        report['rows'].append(item)
        print(json.dumps(item), flush=True)
        shapes.append((row, envelope, common))
    assembly = cad.compound([body] + [envelope for _, envelope, _ in shapes])
    target = out / 'body-with-required-spring-space.binbrep'
    if not BinTools.Write_s(assembly, str(target), False, False, BinTools_FormatVersion_VERSION_3):
        raise ValueError('diagnostic_native_write_failed')
    reread = TopoDS_Shape()
    if not BinTools.Read_s(reread, str(target)) or not cad.valid(reread) or cad.indexed(reread, cad.TopAbs_SOLID).Extent() != 5:
        raise ValueError('diagnostic_native_readback_failed')
    sections = []
    for x in sorted({row['axis_origin'][0] for row in rows}):
        curves = {'body': section_curves(cad, body, x), 'envelope': [], 'overlap': []}
        for row, envelope, common in shapes:
            if row['axis_origin'][0] == x:
                curves['envelope'] += section_curves(cad, envelope, x)
                curves['overlap'] += section_curves(cad, common, x)
        sections.append({'x': x, 'curves': curves})
    save(out / 'sections.json', {'display_sampling': '41_points_per_native_curve_no_deviation_bound', 'sections': sections})
    diagram(out / 'spring-space-sections.svg', sections, tip_allowance)
    preflight(root)
    if source_hashes != {p.name: sha(p) for p in source_paths}:
        raise ValueError('source_changed_during_run')
    report.update(inputs_unchanged=True, status='envelope_conflict' if any(not r['nominal_envelope_clear'] for r in report['rows']) else 'nominal_envelope_clear_only',
                  Boolean_non_destructive=True, Boolean_requested_fuzzy_value=0.,
                  Boolean_effective_fuzzy_values=effective_fuzzy_values,
                  closed_envelope_contains_nominal_compressed_annuli=True,
                  continuous_wire_motion_tested=False,
                  outputs_sha256={p.name: sha(p) for p in sorted(out.iterdir())}, wall_seconds=time.monotonic() - start)
    save(out / 'report.json', report)
    print(json.dumps({'status': report['status'], 'wall_seconds': report['wall_seconds']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tip-allowance', type=float, default=5., help='Unqualified design allowance, not a keeper dimension')
    args = parser.parse_args()
    stack(40.4, 22.7, 11.5, tip_allowance=args.tip_allowance)
    signal.alarm(600)
    run(args.root, args.output, args.tip_allowance)
