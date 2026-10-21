"""Support the frozen pad footprint with a cubic, tangent-width rib foot."""
import json
from pathlib import Path
import sys

from restore_pad import restore, SOURCE, ROOT, precise_volume, sha


def rib_wire(width, z, side, inner):
    from build123d import Edge, Wire
    edges = []
    for offset in (-width / 2, width / 2):
        def p(x, y):
            return (x, side * (y + offset), z)
        edges += [
            Edge.make_bezier(p(-105, 25), p(-90, 25), p(-80, inner), p(-65, inner)),
            Edge.make_line(p(-65, inner), p(-35, inner)),
            Edge.make_bezier(p(-35, inner), p(-29, inner), p(-27, 16), p(-22, 16)),
            Edge.make_line(p(-22, 16), p(22, 16)),
            Edge.make_bezier(p(22, 16), p(27, 16), p(29, inner), p(35, inner)),
            Edge.make_line(p(35, inner), p(65, inner)),
            Edge.make_bezier(p(65, inner), p(80, inner), p(90, 25), p(105, 25)),
        ]
    edges += [Edge.make_line((x, side * (25 - width / 2), z),
                            (x, side * (25 + width / 2), z)) for x in (-105, 105)]
    return Wire(edges)


def width_at(foot, z):
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.gp import gp_Pnt, gp_Dir, gp_Lin
    ray = IntCurvesFace_ShapeIntersector()
    ray.Load(foot.wrapped, 1e-9)
    ray.Perform(gp_Lin(gp_Pnt(0, 0, z), gp_Dir(0, 1, 0)), -100, 100)
    assert ray.IsDone() and ray.NbPnt() == 2
    y = sorted(ray.Pnt(i).Y() for i in (1, 2))
    return y[1] - y[0]


def build(source_folder, output):
    from build123d import Solid, export_step, export_stl, import_step
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCP.Approx import Approx_ParametrizationType
    from OCP.TopoDS import TopoDS
    source_folder, output = Path(source_folder), Path(output)
    plan = json.loads((SOURCE / 'revision-2-plan.json').read_text())
    settings = json.loads((source_folder / 'study.json').read_text())
    rib = settings['geometry']['central_back_ribs']
    assert rib['width_mm'] == plan['central_back_rib_width_mm']
    assert rib['top_z_mm'] == plan['central_back_rib_top_z_mm']
    output.mkdir(parents=True, exist_ok=False)
    (output / 'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    restore(source_folder, output / 'pad-restored-intermediate')
    body = import_step(output / 'pad-restored-intermediate/carrier.step')
    f = plan['foot']
    w0, w1, z0, height = f['baseline_width_mm'], f['top_width_mm'], f['bottom_z_mm'], f['height_mm']
    checks = []
    for side in (-1, 1):
        loft = BRepOffsetAPI_ThruSections(True, False, 1e-9)
        loft.CheckCompatibility(False)
        loft.SetParType(Approx_ParametrizationType.Approx_IsoParametric)
        loft.SetMaxDegree(3)
        for t in f['section_parameters']:
            width = w0 + (w1 - w0) * (3 * t * t - 2 * t * t * t)
            loft.AddWire(rib_wire(width, z0 + height * t, side, rib['inboard_y_mm']).wrapped)
        loft.Build()
        assert loft.IsDone()
        foot = Solid(TopoDS.Solid_s(loft.Shape())).fix()
        assert foot.is_valid and precise_volume(foot)[0] > 0
        export_step(foot, output / f'foot-{side:+d}.step')
        errors = []
        for t in (1 / 6, .5, 5 / 6):
            expected = w0 + (w1 - w0) * (3 * t * t - 2 * t * t * t)
            errors.append(abs(width_at(foot, z0 + height * t) - expected))
        eps = .001
        bottom_slope = (-3 * w0 + 4 * width_at(foot, z0 + eps) - width_at(foot, z0 + 2 * eps)) / (2 * eps)
        top_slope = (3 * w1 - 4 * width_at(foot, z0 + height - eps) + width_at(foot, z0 + height - 2 * eps)) / (2 * eps)
        check = {'side': side, 'sampled_width_law_max_error_mm': max(errors),
                 'estimated_bottom_width_slope': bottom_slope, 'estimated_top_width_slope': top_slope}
        checks.append(check)
        (output / 'foot-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
        assert max(errors) <= f['numerical_width_law_error_mm_max']
        assert max(abs(bottom_slope), abs(top_slope)) <= f['numerical_endpoint_width_slope_abs_max']
        body = body + foot
    assert body.is_valid and len(body.solids()) == 1
    export_step(body, output / 'carrier.step')
    export_stl(body, output / 'carrier.stl', tolerance=.06, angular_tolerance=.10)
    readback = import_step(output / 'carrier.step')
    assert readback.is_valid and len(readback.solids()) == 1
    volume, error = precise_volume(body)
    read_volume, read_error = precise_volume(readback)
    integration = {'adaptive_original_mm3': volume, 'adaptive_readback_mm3': read_volume,
                   'estimated_relative_integration_errors': [error, read_error],
                   'adaptive_relative_difference': read_volume / volume - 1}
    (output / 'volume-integration.json').write_text(json.dumps(integration, indent=2) + '\n')
    assert abs(integration['adaptive_relative_difference']) < 1e-8
    settings['design_id'] = 'carrier-design-20261016-tall-tangent-foot'
    settings['postprocessing'] = {'pad_restore': sha(output / 'pad-restored-intermediate/geometry.json'),
                                 'revision_plan_sha256': sha(SOURCE / 'revision-2-plan.json'),
                                 'foot_checks': checks, 'source_sha256': sha(__file__)}
    (output / 'study.json').write_text(json.dumps(settings, indent=2) + '\n')
    mass = volume * settings['material']['density_tonne_mm3'] * 1000
    bounds = readback.bounding_box()
    receipt = {'design_id': settings['design_id'], 'volume_mm3': volume,
               'dense_reference_mass_kg': mass, 'mass_ceiling_pass': mass <= 1.2,
               'CAD_valid': True, 'solid_count': 1, 'STEP_readback_volume_match': True,
               'geometry_sha256': {name: sha(output / name) for name in ('carrier.step', 'carrier.stl')},
               'bounds_mm': [list(bounds.min), list(bounds.max)], 'foot_checks': checks,
               'dimension_source': 'provisional_study_contract_not_OEM',
               'fitment_validated': False, 'manufacturing_authorized': False}
    (output / 'geometry.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert receipt['mass_ceiling_pass']
    assert bounds.max.Z <= 34 + 1e-6 and bounds.min.Z >= -22 - 1e-6
    assert bounds.max.X <= 296 + 1e-6 and bounds.min.X >= -296 - 1e-6
    assert bounds.max.Y <= 36.5 + 1e-6 and bounds.min.Y >= -36.5 - 1e-6
    print(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
