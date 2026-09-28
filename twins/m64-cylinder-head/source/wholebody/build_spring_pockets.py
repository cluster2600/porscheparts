#!/usr/bin/env python3
"""Private fixed V5 pocket experiment; no master promotion or physical wall approval."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

from render_v5_v2 import PINS, preflight, save, sha
from spring_packaging import LIFTS, SPRING, stack

PORT_PINS = {'intake': '72e0a786a601b96250380d16296004de9e6746caa3888ee470b6cd218f2d0251',
             'exhaust': '9e1ab8b34bcc19457c74ff1e96928f05790d85e975dc78b57ade25d53a988cc9'}
FLOOR, TOP, OUTER_DIAMETER, INNER_DIAMETER = 58.1, 110., 32., 14.
SEAT_ALLOWANCE, TIP_ALLOWANCE, PORT_DISTANCE = 1.5, 5., 3.


def design_stack(lift):
    tip = FLOOR + SEAT_ALLOWANCE + SPRING['installed_height_mm'] + TIP_ALLOWANCE
    return dict(stack(SPRING['installed_height_mm'], SPRING['coil_bind_height_mm'], lift,
                      tip=tip, tip_allowance=TIP_ALLOWANCE), stem_tip_axial_hypothesis=tip,
                stem_extension_from_V2=tip - 82.)


def zero_common(solids, volume):
    return (type(solids) is int and solids == 0 and not isinstance(volume, bool)
            and math.isfinite(volume) and 0. <= volume <= 1e-7)


def port_gate(solids, volume, distance):
    return (zero_common(solids, volume) and not isinstance(distance, bool)
            and math.isfinite(distance) and distance >= PORT_DISTANCE)


def run(root, intake, exhaust, out):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepTools import BRepTools
    from OCP.BinTools import BinTools, BinTools_FormatVersion_VERSION_3
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.TopoDS import TopoDS_Shape
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('exact_OCP_runtime_required')
    started = time.monotonic()
    ports = {'intake': intake, 'exhaust': exhaust}
    sources = [Path(__file__), Path(__file__).with_name('render_v5_v2.py'),
               Path(__file__).with_name('spring_packaging.py'), Path(design.__file__)]
    source_hashes = {p.name: sha(p) for p in sources}
    def unchanged():
        preflight(root)
        for name, path in ports.items():
            if path.is_symlink() or not path.is_file() or sha(path) != PORT_PINS[name]:
                raise ValueError('exact_port_required_' + name)
        if source_hashes != {p.name: sha(p) for p in sources}:
            raise ValueError('source_changed_during_run')
    unchanged()
    cad, fuzzy = design.CAD(), []
    def operation(cls, first, second):
        arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
        arguments.Append(first)
        tools.Append(second)
        job = cls()
        job.SetArguments(arguments)
        job.SetTools(tools)
        job.SetNonDestructive(True)
        job.SetRunParallel(False)
        job.Build()
        # OCP 7.9.3.1 has no BRepAlgoAPI.HasErrors binding; validity/count gates remain.
        if not job.IsDone() or job.Shape().IsNull() or not cad.valid(job.Shape()):
            raise ValueError('invalid_native_boolean')
        fuzzy.append(job.FuzzyValue())  # Default recorded; no tolerance override.
        return job.Shape()
    def one_body(shape):
        if (shape.IsNull() or not cad.valid(shape) or cad.indexed(shape, cad.TopAbs_SOLID).Extent() != 1
                or cad.indexed(shape, TopAbs_SHELL).Extent() != 1):
            raise ValueError('one_valid_solid_and_shell_required')
    def write(shape, path):
        if path.exists() or not BinTools.Write_s(shape, str(path), False, False, BinTools_FormatVersion_VERSION_3):
            raise ValueError('exclusive_native_write_failed')
    rows = json.loads((root / 'registration.json').read_text())['tools_private']
    if len(rows) != 4 or {r['name'] for r in rows} != {f'{b}_{i}' for b in LIFTS for i in (1, 2)}:
        raise ValueError('four_exact_registered_axes_required')
    body = TopoDS_Shape()
    if not BinTools.Read_s(body, str(root / 'candidate.binbrep')):
        raise ValueError('native_body_read_failed')
    one_body(body)
    native_ports = {}
    for name, path in ports.items():
        shape = TopoDS_Shape()
        if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
            raise ValueError('native_port_read_failed_' + name)
        one_body(shape)
        native_ports[name] = shape
    os.umask(0o077)
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    write(body, out / 'retained-body-before.binbrep')
    def annulus(row, bottom, top, od, inner):
        origin, axis = row['axis_origin'], row['axis_direction']
        if (len(origin) != 3 or len(axis) != 3 or not all(math.isfinite(v) for v in origin + axis)
                or abs(math.dist(axis, [0., 0., 0.]) - 1.) > 1e-12 or axis[0] != 0.
                or row['guide_axial_interval'] != [20., 55.] or row['guide_OD'] != 11.):
            raise ValueError('exact_registered_guide_required')
        base = [c + bottom * u for c, u in zip(origin, axis)]
        frame = cad.gp_Ax2(cad.gp_Pnt(*base), cad.gp_Dir(*axis))
        shape = operation(cad.BRepAlgoAPI_Cut,
                          cad.BRepPrimAPI_MakeCylinder(frame, od / 2, top - bottom).Shape(),
                          cad.BRepPrimAPI_MakeCylinder(frame, inner / 2, top - bottom).Shape())
        one_body(shape)
        if not math.isclose(cad.volume(shape), math.pi / 4 * (od * od - inner * inner) * (top - bottom), rel_tol=1e-10):
            raise ValueError('annulus_analytic_volume_mismatch')
        return shape
    tools = [(row, annulus(row, FLOOR, TOP, OUTER_DIAMETER, INNER_DIAMETER)) for row in rows]
    gates = []
    for row, tool in tools:
        for bank, port in native_ports.items():
            common = operation(cad.BRepAlgoAPI_Common, tool, port)
            solids, volume, distance = cad.indexed(common, cad.TopAbs_SOLID).Extent(), cad.volume(common), cad.distance(tool, port)
            gates.append({'tool': row['name'], 'port': bank, 'common_solids': solids, 'common_volume': volume,
                          'minimum_distance': distance, 'pass': port_gate(solids, volume, distance)})
    save(out / 'port-gates.json', {'criterion': 'exploratory_distance_not_physical_wall_allowable',
                                 'threshold_scan_units': PORT_DISTANCE, 'rows': gates})
    unchanged()
    if not all(g['pass'] for g in gates):
        raise ValueError('port_gate_failed_no_body_cut')
    candidate = BRepBuilderAPI_Copy(body, True, False).Shape()
    one_body(candidate)
    before_volume = cad.volume(body)
    for _, tool in tools:
        candidate = operation(cad.BRepAlgoAPI_Cut, candidate, tool)
        one_body(candidate)
    after_volume = cad.volume(candidate)
    if not (math.isfinite(before_volume) and math.isfinite(after_volume) and 0. < after_volume < before_volume):
        raise ValueError('finite_material_removal_required')
    target = out / 'candidate.binbrep'
    write(candidate, target)
    reread = TopoDS_Shape()
    if not BinTools.Read_s(reread, str(target)):
        raise ValueError('candidate_native_readback_failed')
    one_body(reread)
    if not math.isclose(cad.volume(reread), after_volume, rel_tol=1e-12):
        raise ValueError('native_readback_volume_mismatch')
    spring_rows = []
    for row, _ in tools:
        axial = design_stack(LIFTS[row['name'].split('_')[0]])
        envelope = annulus(row, axial['seat_axial'], axial['retainer_closed_axial'],
                           SPRING['outer_diameter_mm'], SPRING['inner_diameter_mm'])
        common = operation(cad.BRepAlgoAPI_Common, reread, envelope)
        solids, volume, distance = cad.indexed(common, cad.TopAbs_SOLID).Extent(), cad.volume(common), cad.distance(reread, envelope)
        if not zero_common(solids, volume) or not math.isfinite(distance) or distance < 0.:
            raise ValueError('post_cut_nominal_spring_envelope_not_empty')
        spring_rows.append({'name': row['name'], 'axial_stack': axial, 'common_solids': solids,
                            'common_volume': volume, 'minimum_distance': distance})
    write(body, out / 'retained-body-after.binbrep')
    if sha(out / 'retained-body-before.binbrep') != sha(out / 'retained-body-after.binbrep'):
        raise ValueError('retained_body_changed_in_memory')
    unchanged()
    save(out / 'report.json', {'schema': 'private-V5-spring-pockets/v1', 'status': 'native_prototype_gates_passed',
         'inputs_sha256': PINS, 'port_inputs_sha256': PORT_PINS, 'source_sha256': source_hashes, 'OCP_version': OCP.__version__,
         'unit': 'scan_units_using_uncertified_1_unit_per_mm_registration',
         'design_hypothesis': {'pocket_floor': FLOOR, 'pocket_top': TOP, 'outer_diameter': OUTER_DIAMETER,
                               'inner_diameter': INNER_DIAMETER, 'seat_allowance': SEAT_ALLOWANCE, 'tip_allowance': TIP_ALLOWANCE},
         'port_gates': gates, 'spring_rows': spring_rows, 'removed_volume': before_volume - after_volume,
         'candidate_exact_BRepCheck_valid': True, 'candidate_solids': 1, 'candidate_shells': 1,
         'native_readback_checked': True, 'retained_body_serialization_unchanged': True, 'inputs_unchanged': True,
         'Boolean_non_destructive': True, 'Boolean_tolerance_override': False, 'Boolean_effective_fuzzy_values': fuzzy,
         'healing_applied': False, 'master_replaced': False, 'spring_wire_or_hardware_modeled': False,
         'longer_valves_modeled': False, 'complete_assembly_validated': False, 'physical_wall_qualified': False,
         'spring_seat_full_support_qualified': False, 'spring_seat_or_washer_engineering_required': True,
         'BOP_check_performed': False, 'manufacturing_authorized': False,
         'outputs_sha256': {p.name: sha(p) for p in sorted(out.iterdir())}, 'wall_seconds': time.monotonic() - started})
    print(json.dumps({'status': 'native_prototype_gates_passed', 'report_sha256': sha(out / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'intake', 'exhaust', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    signal.alarm(600)
    run(args.root, args.intake, args.exhaust, args.output)
