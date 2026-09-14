#!/usr/bin/env python3
"""Private boundary-contact diagnostic; never fabrication or leak qualification.

The pre-cut boundary is intersected with a native gas negative. All contacts
are retained, including contacts inside nominal housing/mouth authorization
volumes. Such volumes can hide a pre-existing pocket; a zero residual is not
proof that only intended openings exist. No source geometry is modified.
"""
import argparse
import json
import math
import multiprocessing
from pathlib import Path
import resource
import sys
import time

import build_scan_seeded_ports as routing


AREA_THRESHOLD = 1e-4  # Scan-unit squared; reporting threshold, not a tolerance on design.
GEOMETRY_MATCH_TOLERANCE = 1e-7


def native_read(path):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
        raise ValueError('native_BRep_read_failed')
    return shape


def native_write(path, shape):
    from OCP.BRepTools import BRepTools
    if path.exists():
        raise FileExistsError(path)
    if not BRepTools.Write_s(shape, str(path)):
        raise ValueError('native_BRep_write_failed')
    path.chmod(0o600)


def boolean(cad, first, second, kind):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    arguments = TopTools_ListOfShape(); arguments.Append(first)
    tools = TopTools_ListOfShape(); tools.Append(second)
    job = (BRepAlgoAPI_Common if kind == 'common' else BRepAlgoAPI_Cut)()
    job.SetArguments(arguments); job.SetTools(tools)
    job.SetNonDestructive(True); job.SetFuzzyValue(0.); job.SetRunParallel(False)
    job.Build()
    if not job.IsDone() or not cad.valid(job.Shape()):
        raise ValueError('surface_boolean_failed_or_invalid')
    return job.Shape(), job


def indexed_faces(cad, shape):
    from OCP.TopoDS import TopoDS
    faces = cad.indexed(shape, cad.TopAbs_FACE)
    return [TopoDS.Face_s(faces.FindKey(i)) for i in range(1, faces.Extent()+1)]


def surface_summary(cad, shape):
    faces = indexed_faces(cad, shape)
    return {'face_count': len(faces), 'area_scan_units_squared': sum(cad.area(face) for face in faces)}


def disjoint_boxes(first, second):
    # These are conservative native bounding boxes, NOT the skin-preservation test.
    return any(first[i+3] < second[i] or second[i+3] < first[i] for i in range(3))


def conservative_bbox(shape):
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape,box,False,True)
    return list(box.Get())


def mouth_authorization(cad, api, stations, mode):
    if mode == 'original_loft':
        return routing.loft(cad,api,stations)
    # Independent of the smooth degree-eight routing loft: matching circle
    # parameters are connected by straight generators. Between each adjacent
    # parallel section, centre and radius therefore interpolate linearly.
    normals = [routing.unit(station['normal']) for station in stations]
    if len(stations)<2 or any(routing.norm([a-b for a,b in zip(normal,normals[0])])>1e-12 for normal in normals):
        raise ValueError('parallel_same_oriented_sections_required_for_ruled_authorization')
    maker = api['BRepOffsetAPI_ThruSections'](True,True,1e-6)
    maker.CheckCompatibility(False)
    for station,normal in zip(stations,normals):
        xdir = routing.unit([1-normal[0]**2,-normal[0]*normal[1],-normal[0]*normal[2]])
        axes = api['gp_Ax2'](api['gp_Pnt'](*station['center']),api['gp_Dir'](*normal),api['gp_Dir'](*xdir))
        circle = api['gp_Circ'](axes,station['radius'])
        maker.AddWire(api['BRepBuilderAPI_MakeWire'](api['BRepBuilderAPI_MakeEdge'](circle).Edge()).Wire())
    maker.Build()
    result = maker.Shape()
    if not maker.IsDone() or not cad.valid(result) or cad.indexed(result,cad.TopAbs_SOLID).Extent()!=1:
        raise ValueError('ruled_authorization_not_one_valid_solid')
    return result


def housing_volumes_and_face_labels(cad, body_faces, tools):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    records, shapes = [], []
    if len(tools) != 4 or len({tool['name'] for tool in tools}) != 4:
        raise ValueError('four_unique_housing_axes_required')
    for tool in tools:
        axis, origin = tool['axis_direction'], tool['axis_origin']
        if abs(routing.norm(axis)-1.) > 1e-10:
            raise ValueError('housing_axis_not_unit')
        for kind in ('seat', 'guide'):
            lo, hi = tool[kind+'_axial_interval']; radius = tool[kind+'_OD']/2
            if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo and radius > 0):
                raise ValueError('invalid_recorded_housing')
            records.append({'name': tool['name']+'_'+kind, 'axis_origin_private': origin,
                            'axis_direction_private': axis, 'radius': radius, 'axial_interval': [lo,hi],
                            'original_boundary_face_indices': []})
    cylindrical_faces = []
    for index, face in enumerate(body_faces, 1):
        adaptor = BRepAdaptor_Surface(face, True)
        if adaptor.GetType() != GeomAbs_Cylinder:
            continue
        cylindrical_faces.append(index)
        cylinder = adaptor.Cylinder(); direction = cylinder.Axis().Direction()
        point = cylinder.Location()
        matches = []
        for record in records:
            axis, origin = record['axis_direction_private'], record['axis_origin_private']
            dot = sum(a*b for a,b in zip(axis, [direction.X(),direction.Y(),direction.Z()]))
            offset = [point.X()-origin[0],point.Y()-origin[1],point.Z()-origin[2]]
            axial = sum(a*b for a,b in zip(axis,offset))
            radial = routing.norm([x-axial*a for x,a in zip(offset,axis)])
            projections = []
            for v in (adaptor.FirstVParameter(), adaptor.LastVParameter()):
                position = adaptor.Value(adaptor.FirstUParameter(),v)
                projections.append(sum(a*(b-c) for a,b,c in zip(axis,[position.X(),position.Y(),position.Z()],origin)))
            interval = sorted(projections)
            if (abs(abs(dot)-1.) <= GEOMETRY_MATCH_TOLERANCE and radial <= GEOMETRY_MATCH_TOLERANCE
                    and abs(cylinder.Radius()-record['radius']) <= GEOMETRY_MATCH_TOLERANCE
                    and interval[0] <= record['axial_interval'][0]+GEOMETRY_MATCH_TOLERANCE
                    and interval[1] >= record['axial_interval'][1]-GEOMETRY_MATCH_TOLERANCE):
                matches.append((record,interval))
        if len(matches) != 1:
            raise ValueError('cylindrical_boundary_face_not_uniquely_bound_to_recorded_housing')
        record, interval = matches[0]
        record['original_boundary_face_indices'].append(index)
        record['original_cylindrical_face_axial_extent_private'] = interval
    if len(cylindrical_faces) != 8 or any(len(record['original_boundary_face_indices']) != 1 for record in records):
        raise ValueError('exactly_eight_semantically_bound_housing_faces_required')
    for record in records:
        # The recorded interval describes the insert, not the entire original
        # through-bore. Use its actual native face extent, never an arbitrary
        # extension. This still authorizes a volume, not a vetted face patch.
        lo, hi = record['original_cylindrical_face_axial_extent_private']
        origin, axis = record['axis_origin_private'],record['axis_direction_private']
        shapes.append(cad.BRepPrimAPI_MakeCylinder(
            cad.gp_Ax2(cad.gp_Pnt(*routing.add(origin,routing.mul(axis,lo))),cad.gp_Dir(*axis)),
            record['radius'],hi-lo).Shape())
    return shapes, records


def raw_face_history(cad, job, result, original_faces):
    result_map = cad.indexed(result,cad.TopAbs_FACE)
    owners = {i: [] for i in range(1,result_map.Extent()+1)}
    rows = []
    for source_index, face in original_faces:
        indices = set()
        unchanged = result_map.FindIndex(face)
        if unchanged:
            indices.add(unchanged)
        for descendant in list(job.Modified(face)) + list(job.Generated(face)):
            index = result_map.FindIndex(descendant)
            if index:
                indices.add(index)
        if indices:
            for index in indices:
                owners[index].append(source_index)
            rows.append({'original_boundary_face_index': source_index,
                         'raw_contact_face_indices': sorted(indices),
                         'raw_contact_area_scan_units_squared': sum(cad.area(result_map.FindKey(i)) for i in indices)})
    return {'contacts_by_original_face': rows,
            'unmapped_raw_contact_face_indices': [i for i,v in owners.items() if not v],
            'multiply_owned_raw_contact_face_indices': [i for i,v in owners.items() if len(v) > 1],
            'all_raw_faces_retained_even_if_history_incomplete': True}


def bound_inputs(args):
    context_path = args.trial/'execution-context.json'
    context = json.loads(context_path.read_text())
    paths = {'body': args.body, 'body_build': args.body_build,
             'context': context_path, 'audit_source': Path(__file__),
             'routing_source': Path(routing.__file__), 'module_source': Path(routing.design.__file__)}
    generation_path = args.trial/'routing-report.json'
    generation = json.loads(generation_path.read_text())
    if generation['inputs_sha256'] != context['inputs_sha256'] or generation.get('input_files_unchanged') is not True:
        raise ValueError('generation_report_context_or_input_integrity_mismatch')
    paths['generation_report'] = generation_path
    hashes = {key:routing.sha(path) for key,path in paths.items()}
    for key in ('body','body_build','routing_source','module_source'):
        if hashes[key] != context['inputs_sha256'][key]:
            raise ValueError('trial_context_source_mismatch_'+key)
    banks = {}
    for kind in ('intake','exhaust'):
        checkpoint_path = args.trial/(kind+'-checkpoint.json')
        checkpoint = json.loads(checkpoint_path.read_text())
        brep_path = args.trial/(kind+'-negative.brep')
        if checkpoint['kind'] != kind or routing.sha(brep_path) != checkpoint['exports']['native_BRep_sha256']:
            raise ValueError('native_bank_checkpoint_mismatch')
        generation_banks = [row for row in generation['bank_records'] if row['kind']==kind]
        if len(generation_banks) != 1 or generation_banks[0] != checkpoint:
            raise ValueError('checkpoint_not_bound_to_generation_report')
        if checkpoint['exports']['native_BOP']['has_faulty']:
            raise ValueError('faulty_native_bank')
        paths[kind+'_checkpoint'] = checkpoint_path; paths[kind+'_native'] = brep_path
        hashes[kind+'_checkpoint'] = routing.sha(checkpoint_path); hashes[kind+'_native'] = routing.sha(brep_path)
        banks[kind] = checkpoint
    return paths, hashes, banks


def audit_bank(args, kind):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU,(args.worker_seconds,args.worker_seconds+5))
    paths, hashes, checkpoints = bound_inputs(args)
    cad = routing.design.CAD(); api = routing.native()
    body = cad.read_step(args.body); bank = native_read(paths[kind+'_native'])
    if not cad.valid(body) or not cad.valid(bank):
        raise ValueError('input_shape_invalid')
    body_faces = indexed_faces(cad,body)
    tools = json.loads(args.body_build.read_text())['tools_private']
    housings, housing_records = housing_volumes_and_face_labels(cad,body_faces,tools)
    bank_box = conservative_bbox(bank)
    possible = [(i,face) for i,face in enumerate(body_faces,1)
                if not disjoint_boxes(conservative_bbox(face),bank_box)]
    report = {'schema':'m64-private-port-boundary-contact/v1','kind':kind,'status':'incomplete',
              'inputs_sha256':hashes,'manufacturing_authorized':False,
              'geometrical_length_unit':'unverified_scan_unit_equals_mm_hypothesis',
              'boundary_scope':'all_original_body_boundary_faces_including_existing_internal_void_walls',
              'body_face_count':len(body_faces),'bbox_prefilter_candidate_faces':len(possible),
              'bbox_used_only_for_conservative_prefilter':True,
              'bbox_includes_native_shape_tolerances':True,
              'native_boolean_fuzzy_value':0.,'native_shape_tolerances_not_modified':True,
              'housing_match_tolerance_scan_units':GEOMETRY_MATCH_TOLERANCE,
              'residual_area_reporting_threshold_scan_units_squared':AREA_THRESHOLD,
              'authorized_housing_records_private':housing_records,
              'housing_authorization_extent':'observed_original_cylindrical_face_axial_extent_not_insert_length',
              'negative_ports_use_native_BRep_not_failed_STEP':True,
              'only_intended_openings_proven':False,'minimum_wall_thickness_verified':False,
              'existing_void_communications_verified':False,'powder_removal_verified':False,
              'authorization_warning':'A pre-existing pocket inside an authorization volume can disappear from the residual; inspect all raw contacts.'}
    report['mouth_screen'] = args.mouth_screen
    if args.raw_audit is None:
        raw, history = boolean(cad,cad.compound([face for _,face in possible]),bank,'common')
        report['raw_boundary_history'] = raw_face_history(cad,history,raw,possible)
    else:
        previous_path = args.raw_audit/kind/'boundary-contact-report.json'
        previous = json.loads(previous_path.read_text())
        raw_input = args.raw_audit/kind/'all-raw-boundary-contacts.brep'
        if previous.get('input_files_unchanged') is not True or previous['kind'] != kind:
            raise ValueError('raw_parent_audit_incomplete_or_wrong_bank')
        for key,value in hashes.items():
            if key != 'audit_source' and previous['inputs_sha256'].get(key) != value:
                raise ValueError('raw_parent_audit_context_mismatch_'+key)
        if routing.sha(raw_input) != previous['raw_contacts_BRep_sha256']:
            raise ValueError('raw_parent_native_contacts_hash_mismatch')
        paths['raw_parent_report'] = previous_path; paths['raw_parent_contacts'] = raw_input
        hashes['raw_parent_report'] = routing.sha(previous_path); hashes['raw_parent_contacts'] = routing.sha(raw_input)
        raw = native_read(raw_input)
        report['raw_boundary_history'] = previous['raw_boundary_history']
        report['raw_contact_reuse'] = {'previous_audit_source_sha256':previous['inputs_sha256']['audit_source'],
                                      'raw_native_shape_sha256':hashes['raw_parent_contacts'],
                                      'raw_parent_report_sha256':hashes['raw_parent_report'],
                                      'previous_raw_summary':previous['raw_contacts']}
    report['raw_contacts'] = surface_summary(cad,raw)
    directory = args.output/kind; directory.mkdir(mode=0o700)
    raw_path = directory/'all-raw-boundary-contacts.brep'; native_write(raw_path,raw)
    report['raw_contacts_BRep_sha256'] = routing.sha(raw_path)
    routing.save(directory/'raw-contact-checkpoint.json',report)
    checkpoint = checkpoints[kind]
    mouth = mouth_authorization(cad,api,checkpoint['seed_sections_private']+[checkpoint['extension_private']],args.mouth_screen)
    report['mouth_authorization_definition'] = ('same_smooth_degree_eight_loft_as_routing_NOT_independent_against_overshoot'
        if args.mouth_screen=='original_loft' else
        'ruled_parallel_circle_sections_linear_centres_and_radii_between_recorded_stations_NO_inflation')
    report['mouth_authorization_BOP'] = routing.bop_check(mouth)
    if report['mouth_authorization_BOP']['has_faulty']:
        raise ValueError('mouth_authorization_native_BOP_faulty')
    native_write(directory/'mouth-authorization-volume.brep',mouth)
    remaining = raw; stages = []
    for name,authorization in [('recorded_mouth_envelope',mouth),
                               *[(record['name'],shape) for record,shape in zip(housing_records,housings)]]:
        before = surface_summary(cad,remaining)['area_scan_units_squared']
        allowed,_ = boolean(cad,remaining,authorization,'common')
        remaining,_ = boolean(cad,remaining,authorization,'cut')
        allowed_summary, remaining_summary = surface_summary(cad,allowed), surface_summary(cad,remaining)
        after, removed = remaining_summary['area_scan_units_squared'], allowed_summary['area_scan_units_squared']
        conservation_error = after+removed-before
        tolerance = 1e-4+1e-7*max(before,after,removed)
        if after > before+tolerance or abs(conservation_error) > tolerance:
            native_write(directory/(name+'-rejected-remaining.brep'),remaining)
            native_write(directory/(name+'-rejected-classified.brep'),allowed)
            report['status'] = 'indeterminate_surface_area_partition_failure'
            report['failure'] = {'authorization':name,'area_before':before,
                'area_classified_inside_authorization':removed,'area_remaining':after,
                'partition_error':conservation_error,'partition_tolerance':tolerance,
                'remaining_surface_summary':remaining_summary,'classified_surface_summary':allowed_summary,
                'remaining_native_sha256':routing.sha(directory/(name+'-rejected-remaining.brep')),
                'classified_native_sha256':routing.sha(directory/(name+'-rejected-classified.brep'))}
            report['input_files_unchanged'] = all(routing.sha(path)==hashes[key] for key,path in paths.items())
            report['elapsed_seconds'] = time.monotonic()-started
            routing.save(directory/'boundary-contact-failure.json',report)
            raise ValueError('surface_area_partition_failed_'+name)
        stages.append({'authorization':name,'area_before':before,'area_classified_inside_authorization':removed,
                       'area_remaining':after,'partition_error':conservation_error,'partition_tolerance':tolerance})
        native_write(directory/(name+'-classified-contacts.brep'),allowed)
    report['authorization_stages'] = stages
    report['residual_outside_authorization_volumes'] = surface_summary(cad,remaining)
    report['residual_faces_private'] = [
        {'index':i,'area_scan_units_squared':cad.area(face),'bbox_private':routing.bbox(api,face)}
        for i,face in enumerate(indexed_faces(cad,remaining),1)]
    residual_path = directory/'residual-outside-authorization-volumes.brep'; native_write(residual_path,remaining)
    report['residual_BRep_sha256'] = routing.sha(residual_path)
    report['status'] = ('unexpected_boundary_contacts_detected' if
        report['residual_outside_authorization_volumes']['area_scan_units_squared'] > AREA_THRESHOLD else
        'no_residual_above_reporting_threshold_NOT_an_opening_qualification')
    report['input_files_unchanged'] = all(routing.sha(path)==hashes[key] for key,path in paths.items())
    if not report['input_files_unchanged']:
        raise ValueError('source_changed_during_boundary_audit')
    report['elapsed_seconds'] = time.monotonic()-started
    routing.save(directory/'boundary-contact-report.json',report)
    print(json.dumps({'kind':kind,'status':report['status'],'raw':report['raw_contacts'],
                      'residual':report['residual_outside_authorization_volumes']}),flush=True)


def self_test():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeSphere
    cad = routing.design.CAD()
    cube = BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    negative = BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(5.,5.,8.),cad.gp_Dir(0,0,1)),1.,4.).Shape()
    authorization = BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(5.,5.,9.),cad.gp_Dir(0,0,1)),1.,3.).Shape()
    def contacts(body):
        raw,_ = boolean(cad,cad.compound(indexed_faces(cad,body)),negative,'common')
        residual,_ = boolean(cad,raw,authorization,'cut')
        return surface_summary(cad,raw)['area_scan_units_squared'],surface_summary(cad,residual)['area_scan_units_squared']
    healthy_raw,healthy_residual = contacts(cube)
    assert abs(healthy_raw-math.pi)<1e-7 and healthy_residual<1e-7
    cavity = BRepPrimAPI_MakeSphere(cad.gp_Pnt(5.,5.,9.4),.2).Shape()
    pocketed,_ = boolean(cad,cube,cavity,'cut')
    pocket_raw,pocket_residual = contacts(pocketed)
    assert abs(pocket_raw-healthy_raw-.16*math.pi)<1e-7 and pocket_residual<1e-7
    # Same cavity below the authorized region is retained as an unexpected contact.
    cavity = BRepPrimAPI_MakeSphere(cad.gp_Pnt(5.,5.,8.5),.2).Shape()
    pocketed,_ = boolean(cad,cube,cavity,'cut')
    outside_raw,outside_residual = contacts(pocketed)
    assert abs(outside_raw-healthy_raw-.16*math.pi)<1e-7 and abs(outside_residual-.16*math.pi)<1e-7
    print(json.dumps({'self_test':'PASS','native_witnesses':3,
                      'inside_authorization_false_negative_demonstrated_and_raw_contacts_retained':True}))
    stations = [{'center':[x,y,0.],'normal':[0.,1.,0.],'radius':radius}
                for x,y,radius in ((0.,0.,1.),(0.,1.,2.),(2.,2.,.5),(0.,3.,1.5))]
    ruled = mouth_authorization(cad,routing.native(),stations,'ruled_sections')
    box = routing.bbox(routing.native(),ruled)
    assert all(abs(a-b)<1e-6 for a,b in zip(box,[-2.,0.,-2.,2.5,3.,2.]))
    assert not routing.bop_check(ruled)['has_faulty']
    print(json.dumps({'ruled_section_witness':'PASS','overshoot_free_vertex_section_bounds_checked':True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    for name in ('body','body-build','trial','output'):
        parser.add_argument('--'+name,type=Path)
    parser.add_argument('--worker-seconds',type=int,default=180)
    parser.add_argument('--raw-audit',type=Path)
    parser.add_argument('--mouth-screen',choices=('original_loft','ruled_sections'),default='original_loft')
    parser.add_argument('--bank',choices=('both','intake','exhaust'),default='both')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return 0
    if any(getattr(args,name) is None for name in ('body','body_build','trial','output')):
        parser.error('body, body-build, trial and output are required')
    if not 1 <= args.worker_seconds <= 300:
        parser.error('worker-seconds must be between 1 and 300')
    if args.output.exists():
        raise FileExistsError(args.output)
    bound_inputs(args)
    args.output.mkdir(parents=True,mode=0o700)
    statuses = []
    for kind in (('intake','exhaust') if args.bank=='both' else (args.bank,)):
        process = multiprocessing.get_context('spawn').Process(target=audit_bank,args=(args,kind))
        process.start()
        try:
            process.join(args.worker_seconds)
        except BaseException:
            process.terminate(); process.join(3)
            if process.is_alive(): process.kill(); process.join()
            raise
        timed_out = process.is_alive()
        if timed_out:
            process.terminate(); process.join(3)
            if process.is_alive(): process.kill(); process.join()
        statuses.append({'kind':kind,'exit_code':process.exitcode,'timeout':timed_out,
                         'complete':(args.output/kind/'boundary-contact-report.json').exists()})
        routing.save(args.output/(kind+'-process-receipt.json'),statuses[-1])
    routing.save(args.output/'execution-receipt.json',{'banks':statuses,'manufacturing_authorized':False})
    return 0 if all(row['exit_code']==0 and row['complete'] for row in statuses) else 2


if __name__ == '__main__':
    sys.exit(main())
