#!/usr/bin/env python3
"""Two local exhaust support pads; private geometry, no physical qualification.

The pads deliberately change the local fin contour. Their chosen 3-unit axial
thickness is a CAD experiment, not a structural or thermal allowable.
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
from build_spring_pockets import PORT_PINS, port_gate, zero_common

POCKET_PINS = {'candidate.binbrep': '2969035f9a802d08652c295e310591788f851d2ace2935c484c0e90c36c9a9af',
               'report.json': 'e1f56194ccb91fb0571cdc3531dabe8081effe8d9897882a5064c3acf851ae1a'}
FLOOR, PAD_BOTTOM, OUTER_RADIUS, INNER_RADIUS = 58.1, 55.1, 16., 7.
AREA = math.pi * (OUTER_RADIUS ** 2 - INNER_RADIUS ** 2)
DEPENDENCIES = {'render_v5_v2.py': '63ccd3df8f07997a1bbeb6d7ba1434732622c7fc41106483ace0155ff00c3947',
                'build_spring_pockets.py': 'cd7e05f0882466cd90686f273a544064d64b3ae9db6d418acf25820940e32442',
                'spring_packaging.py': '04836203e87bd0538179906cf487b73aebb16d121d3ef7602e31a67858facc8b',
                'build_four_valve_distribution.py': '4604b5fbc74e02c7029481cdf269a3ee93d208229d87379bc6545db46bdb3d1c'}


def full_support(missing_faces, missing_area, contact_area):
    return (type(missing_faces) is int and missing_faces == 0
            and all(not isinstance(x, bool) and math.isfinite(x) for x in (missing_area, contact_area))
            and 0. <= missing_area <= 1e-7 and abs(contact_area - AREA) <= 1e-6)


def unchanged_box(before, after):
    return (len(before) == len(after) == 6
            and all(not isinstance(v, bool) and math.isfinite(v) for v in before + after)
            and max(abs(a-b) for a, b in zip(before, after)) <= 1e-6)


def exact_files(directory, pins):
    for name, expected in pins.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError('exact_input_required_' + name)


def run(root, pockets, intake, exhaust, output):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BinTools import BinTools, BinTools_FormatVersion_VERSION_3
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('exact_OCP_required')
    started = time.monotonic()
    sources = {p.name: p for p in [Path(__file__), Path(design.__file__)]}
    sources.update({n: Path(__file__).with_name(n) for n in DEPENDENCIES if n != Path(design.__file__).name})
    source_hashes = {name: sha(path) for name, path in sources.items()}
    if any(source_hashes.get(n) != h for n, h in DEPENDENCIES.items()):
        raise ValueError('frozen_dependency_changed')
    ports = {'intake': intake, 'exhaust': exhaust}
    def check_inputs():
        preflight(root)
        exact_files(pockets, POCKET_PINS)
        for name, path in ports.items():
            if path.is_symlink() or sha(path) != PORT_PINS[name]:
                raise ValueError('native_port_hash_mismatch')
        if source_hashes != {name: sha(path) for name, path in sources.items()}:
            raise ValueError('source_changed')
    check_inputs()
    if json.loads((pockets/'report.json').read_text())['outputs_sha256']['candidate.binbrep'] != POCKET_PINS['candidate.binbrep']:
        raise ValueError('pocket_receipt_binding')
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    cad, fuzzy = design.CAD(), []
    def indexed(shape, kind):
        table = cad.indexed(shape, kind)
        return [table.FindKey(i) for i in range(1, table.Extent()+1)]
    def operation(cls, first, second):
        args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
        args.Append(first); tools.Append(second)
        job = cls(); job.SetArguments(args); job.SetTools(tools)
        job.SetNonDestructive(True); job.SetRunParallel(False); job.Build()
        if not job.IsDone() or job.Shape().IsNull() or not cad.valid(job.Shape()):
            raise ValueError('invalid_native_boolean')
        fuzzy.append(job.FuzzyValue())
        return job.Shape()
    def one_body(shape):
        if not cad.valid(shape) or len(indexed(shape, cad.TopAbs_SOLID)) != 1 or len(indexed(shape, TopAbs_SHELL)) != 1:
            raise ValueError('one_valid_solid_shell_required')
    def binary_read(path):
        shape = TopoDS_Shape()
        if not BinTools.Read_s(shape, str(path)):
            raise ValueError('native_read_failed')
        one_body(shape)
        return shape
    def write(shape, name):
        path = output/name
        if path.exists() or not BinTools.Write_s(shape, str(path), False, False, BinTools_FormatVersion_VERSION_3):
            raise ValueError('exclusive_native_write_failed')
        return sha(path)
    def bbox(shape):
        box = Bnd_Box(); BRepBndLib.AddOptimal_s(shape, box, False, False)
        return list(box.Get())
    def empty(shape):
        return zero_common(len(indexed(shape, cad.TopAbs_SOLID)), cad.volume(shape))
    body = binary_read(pockets/'candidate.binbrep')
    retained = write(body, 'retained-body-before.binbrep')
    registration = json.loads((root/'registration.json').read_text())
    axes = registration['tools_private']
    if len(axes) != 4 or {a['name'] for a in axes} != {'intake_1','intake_2','exhaust_1','exhaust_2'}:
        raise ValueError('four_retained_axes_required')
    module = cad.read_step(root/'closed.step')
    module_solids = cad.indexed(module, cad.TopAbs_SOLID)
    tr = cad.gp_Trsf(); tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0), cad.gp_Dir(0,0,1)), -math.pi/2)
    tr.SetTranslationPart(cad.gp_Vec(0,0,3))
    guides = {a['name']: cad.BRepBuilderAPI_Transform(module_solids.FindKey(a['imported_module_solid_id']), tr, True).Shape()
              for a in registration['components_imported_from_exact_STEP'] if a['name'].endswith('_guide')}
    if len(guides) != 4:
        raise ValueError('four_exact_guides_required')
    native_ports = {}
    for name, path in ports.items():
        shape = TopoDS_Shape()
        if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
            raise ValueError('native_port_read_failed')
        one_body(shape); native_ports[name] = shape
    def annulus(row, bottom, top, outer=OUTER_RADIUS, inner=INNER_RADIUS):
        axis, origin = row['axis_direction'], row['axis_origin']
        frame = cad.gp_Ax2(cad.gp_Pnt(*(o+bottom*a for o,a in zip(origin,axis))), cad.gp_Dir(*axis))
        shape = operation(cad.BRepAlgoAPI_Cut, cad.BRepPrimAPI_MakeCylinder(frame,outer,top-bottom).Shape(),
                          cad.BRepPrimAPI_MakeCylinder(frame,inner,top-bottom).Shape())
        one_body(shape)
        if not math.isclose(cad.volume(shape), math.pi*(outer*outer-inner*inner)*(top-bottom), rel_tol=1e-10):
            raise ValueError('annulus_volume_mismatch')
        return shape
    def footprint(row, offset=0.):
        shape = annulus(row, FLOOR+offset, FLOOR+offset+1.)
        faces = []
        for raw in indexed(shape, cad.TopAbs_FACE):
            face = cad.TopoDS.Face_s(raw)
            if BRepAdaptor_Surface(face, True).GetType() != GeomAbs_Plane:
                continue
            props = cad.GProp_GProps(); cad.BRepGProp.SurfaceProperties_s(face, props)
            axial = sum(a*(p-o) for a,p,o in zip(row['axis_direction'],props.CentreOfMass().Coord(),row['axis_origin']))
            if abs(axial-FLOOR-offset) < 1e-7:
                faces.append(face)
        if len(faces) != 1:
            raise ValueError('one_bottom_footprint_required')
        return faces[0]
    def support(shape):
        result = []
        for row in axes:
            for offset in (0., -.001):
                face = footprint(row, offset)
                contact = operation(cad.BRepAlgoAPI_Common, face, shape)
                missing = operation(cad.BRepAlgoAPI_Cut, face, shape)
                count, area, contact_area = len(indexed(missing,cad.TopAbs_FACE)), cad.area(missing), cad.area(contact)
                result.append({'name': row['name'], 'offset': offset, 'missing_faces': count, 'missing_area': area,
                               'contact_area': contact_area, 'analytic_area': AREA, 'full_footprint': full_support(count,area,contact_area)})
        return result
    report = {'schema':'private-V5-spring-seat-pads/v1','status':'in_progress','source_sha256':source_hashes,
              'inputs_sha256':PINS,'pocket_inputs_sha256':POCKET_PINS,'port_inputs_sha256':PORT_PINS,
              'OCP_version':OCP.__version__,'unit':'uncalibrated_scan_units_under_1_unit_per_mm_hypothesis',
              'design_hypothesis':{'pad_bottom':PAD_BOTTOM,'pad_top':FLOOR,'outer_radius':OUTER_RADIUS,'inner_radius':INNER_RADIUS},
              'local_exterior_contour_changed':True,'original_skin_preserved':False,'BOP_check_performed':False,
              'thickness_structurally_qualified':False,'thermal_or_cooling_qualified':False,'manufacturing_authorized':False,
              'spring_hardware_or_longer_valves_modeled':False,'master_replaced':False}
    report['support_before'] = support(body)
    save(output/'support-before.json', report['support_before'])
    pads, gates = [], []
    for row in axes:
        if not row['name'].startswith('exhaust_'):
            continue
        pad = annulus(row,PAD_BOTTOM,FLOOR)
        overlap = operation(cad.BRepAlgoAPI_Common,pad,body)
        addition = operation(cad.BRepAlgoAPI_Cut,pad,body)
        if cad.volume(overlap) <= 0. or cad.volume(addition) <= 0.:
            raise ValueError('positive_attachment_and_addition_required')
        item = {'name':row['name'],'pad_volume':cad.volume(pad),'attachment_overlap_volume':cad.volume(overlap),
                'proposed_added_volume':cad.volume(addition),'ports':[],'guides':[]}
        for name, port in native_ports.items():
            common = operation(cad.BRepAlgoAPI_Common,pad,port); distance = cad.distance(pad,port)
            entry = {'name':name,'common_solids':len(indexed(common,cad.TopAbs_SOLID)), 'common_volume':cad.volume(common), 'minimum_distance':distance}
            if not port_gate(entry['common_solids'],entry['common_volume'],distance):
                raise ValueError('pad_port_gate_failed')
            item['ports'].append(entry)
        for name, guide in guides.items():
            common = operation(cad.BRepAlgoAPI_Common,pad,guide); distance = cad.distance(pad,guide)
            if not empty(common) or distance < 1.5-1e-6:
                raise ValueError('pad_guide_gate_failed')
            item['guides'].append({'name':name,'common_volume':cad.volume(common),'minimum_distance':distance})
        pads.append(pad); gates.append(item)
    report['pad_gates'] = gates
    save(output/'pad-gates.json',gates)
    candidate = body
    for pad in pads:
        candidate = operation(BRepAlgoAPI_Fuse,candidate,pad); one_body(candidate)
    before_box, after_box = bbox(body), bbox(candidate)
    if not unchanged_box(before_box,after_box):
        raise ValueError('overall_bbox_changed')
    removed = operation(cad.BRepAlgoAPI_Cut,body,candidate)
    added = operation(cad.BRepAlgoAPI_Cut,candidate,body)
    outside = operation(cad.BRepAlgoAPI_Cut,added,cad.compound(pads))
    if not empty(removed) or not empty(outside) or cad.volume(added) <= 0.:
        raise ValueError('strict_additive_locality_failed')
    report['candidate_sha256'] = write(candidate,'candidate.binbrep')
    reread = binary_read(output/'candidate.binbrep')
    report['support_saved_candidate'] = support(reread)
    if not all(row['full_footprint'] for row in report['support_saved_candidate']):
        raise ValueError('saved_washer_footprint_incomplete')
    for row in axes:
        spring = annulus(row,59.6,100.,15.,7.75)
        if not empty(operation(cad.BRepAlgoAPI_Common,reread,spring)):
            raise ValueError('saved_spring_envelope_obstructed')
    if retained != write(body,'retained-body-after.binbrep'):
        raise ValueError('original_in_memory_body_changed')
    check_inputs()
    report.update(status='native_local_pad_prototype_gates_passed',candidate_solids=1,candidate_shells=1,
                  candidate_exact_BRepCheck_valid=True,native_saved_readback_checked=True,
                  before_bbox=before_box,after_bbox=after_box,overall_bbox_unchanged=True,
                  added_volume=cad.volume(added),removed_volume=cad.volume(removed),outside_pad_added_volume=cad.volume(outside),
                  saved_nominal_spring_envelopes_empty=True,retained_body_unchanged=True,inputs_unchanged=True,
                  Boolean_effective_fuzzy_values=fuzzy,Boolean_tolerance_override=False,healing_applied=False,
                  wall_seconds=time.monotonic()-started)
    report['outputs_sha256'] = {p.name:sha(p) for p in sorted(output.iterdir())}
    save(output/'report.json',report)
    print(json.dumps({'status':report['status'],'candidate_sha256':report['candidate_sha256'],'report_sha256':sha(output/'report.json')}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root','pockets','intake','exhaust','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); signal.alarm(600)
    run(args.root,args.pockets,args.intake,args.exhaust,args.output)
