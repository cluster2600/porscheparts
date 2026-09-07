#!/usr/bin/env python3
"""Private exploratory 4V port routing from recorded scan cross-section seeds.

This makes new gas passages, not measured Porsche internals. The outer master
is read only; every output stays in a new private directory. No thermal, flow,
wall-thickness, fitment or manufacturing approval follows from a valid B-Rep.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import build_four_valve_distribution as design


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def mul(a, s):
    return [x * s for x in a]


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def unit(a):
    length = norm(a)
    if not math.isfinite(length) or length < 1e-12:
        raise ValueError('nonzero finite direction required')
    return mul(a, 1 / length)


def bezier(controls, t):
    if len(controls) != 4 or not 0 <= t <= 1:
        raise ValueError('four controls and unit parameter required')
    weights = [(1-t)**3, 3*t*(1-t)**2, 3*t*t*(1-t), t**3]
    return [sum(w*p[k] for w, p in zip(weights, controls)) for k in range(3)]


def bezier_derivative(controls, t):
    q = [[3*(b[k]-a[k]) for k in range(3)] for a,b in zip(controls, controls[1:])]
    return [q[0][k]*(1-t)**2 + 2*q[1][k]*t*(1-t) + q[2][k]*t*t for k in range(3)]


def seed_sections(interfaces, side):
    """ABC section coordinates -> existing F36/F43 local frame, without refit.

    Section centres are already expressed in ABC, so frame_rows_A_B_C must
    NOT be applied again. Only chamber-origin subtraction and C inversion.
    Original fit residuals and point counts remain attached to each seed.
    """
    if side not in ('low_B', 'high_B'):
        raise ValueError('unknown geometric port side')
    chamber = interfaces['combustion_interface']['chamber_step']
    ca, cb = chamber['center']
    pc = chamber['plane_C']
    sign = 1 if side == 'high_B' else -1
    records = []
    for row in interfaces['port_sections'][side]:
        radius = row['diameter_obj_units']/2
        values = [*row['center'], row['plane_B'], radius, row['fit_p95_obj_units'], ca, cb, pc]
        if not all(math.isfinite(v) for v in values) or radius <= 0:
            raise ValueError('invalid scan section seed')
        records.append({'center': [row['center'][0]-ca, row['plane_B']-cb, pc-row['center'][1]],
                        'radius': radius, 'normal': [0., float(sign), 0.],
                        'fit_p95_scan_units': row['fit_p95_obj_units'], 'inliers': row['inliers']})
    records.sort(key=lambda row: sign*row['center'][1])
    if len(records) < 2 or any(sign*(b['center'][1]-a['center'][1]) <= 0 for a,b in zip(records,records[1:])):
        raise ValueError('two or more ordered distinct sections required')
    return records


def branch_stations(origin, axis, throat_radius, seed, tangent_length, approach_length, count=17):
    """New cubic centreline, with explicit endpoint directions and radii."""
    if count < 3 or any(not math.isfinite(v) or v <= 0 for v in (throat_radius,tangent_length,approach_length)):
        raise ValueError('invalid branch parameters')
    axis, outward = unit(axis), unit(seed['normal'])
    controls = [origin, add(origin,mul(axis,tangent_length)),
                add(seed['center'],mul(outward,-approach_length)), seed['center']]
    stations = []
    for i in range(count):
        t = i/(count-1)
        # C1 radius ramp at the ends; these are loft constraints, not a claim
        # of an exact circular cross-section everywhere between stations.
        blend = t*t*(3-2*t)
        stations.append({'center': bezier(controls,t),
                         'normal': unit(bezier_derivative(controls,t)),
                         'radius': throat_radius+(seed['radius']-throat_radius)*blend})
    return stations, controls


def check_registered_axes(p, tools):
    """Match private recorded axes to this exact module, not just four labels."""
    specs=design.valve_specs(p)
    if len(tools)!=4 or {row['name'] for row in tools}!={s['name'] for s in specs}:
        raise ValueError('four unique recorded V2 axes required')
    for spec in specs:
        row=next(row for row in tools if row['name']==spec['name'])
        x,y,z=spec['center']; angle=math.radians(spec['axis_angle_deg'])
        expected={'axis_origin':[y,-x,z+3.],
                  'axis_direction':[0.,-math.sin(angle),math.cos(angle)],
                  'seat_axial_interval':[p.valve_margin_radial_mm*math.tan(math.radians(p.seat_angle_from_transverse_plane_deg)),
                                         p.valve_margin_radial_mm*math.tan(math.radians(p.seat_angle_from_transverse_plane_deg))+p.seat_axial_thickness_mm],
                  'guide_axial_interval':[p.guide_start_above_gauge_mm,p.guide_start_above_gauge_mm+p.guide_length_mm]}
        for key,values in expected.items():
            if len(row[key])!=len(values) or any(not math.isfinite(a) or abs(a-b)>1e-10 for a,b in zip(row[key],values)):
                raise ValueError('recorded axis or interval does not match registered V2 module')
        for key,value in [('seat_OD',spec['diameter_mm']+2*p.seat_outer_radial_allowance_mm),
                          ('guide_OD',p.guide_outer_diameter_mm)]:
            if not math.isfinite(row[key]) or abs(row[key]-value)>1e-10:
                raise ValueError('recorded housing dimension does not match V2 module')


def save(path, payload):
    with Path(path).open('x') as handle:
        handle.write(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    Path(path).chmod(0o600)


def native():
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.gp import gp_Circ, gp_Ax2, gp_Pnt, gp_Dir
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    return locals()


def operation(cad, kind, a, b):
    job = kind()
    from OCP.TopTools import TopTools_ListOfShape
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(a); tools.Append(b)
    job.SetArguments(args); job.SetTools(tools)
    job.SetNonDestructive(True); job.SetFuzzyValue(0.); job.SetRunParallel(False)
    job.Build()
    if not job.IsDone():
        raise RuntimeError('Boolean failed')
    result = job.Shape()
    if not cad.valid(result):
        raise ValueError('Boolean result invalid')
    va,vb,vr=cad.volume(a),cad.volume(b),cad.volume(result)
    allowance=1e-5+1e-7*max(va,vb,vr)
    name=kind.__name__
    if name.endswith('_Fuse') and not max(va,vb)-allowance<=vr<=va+vb+allowance:
        raise ValueError('Boolean union violates volume monotonicity')
    if name.endswith('_Cut') and vr>va+allowance:
        raise ValueError('Boolean cut increases volume')
    if name.endswith('_Common') and vr>min(va,vb)+allowance:
        raise ValueError('Boolean intersection exceeds input volume')
    return result


def loft(cad, api, stations, *, ruled=False):
    """Keep every circle; optionally join consecutive circles by ruled faces.

    Ruled trunks deliberately retain C0 junctions at recorded stations. This
    option does not fair, refit, inflate or remove a measured section. Branches
    retain the historical smooth loft because they do not pass this flag.
    """
    if not isinstance(ruled,bool):
        raise ValueError('ruled flag must be Boolean')
    maker = api['BRepOffsetAPI_ThruSections'](True,ruled,1e-6)
    maker.CheckCompatibility(False)
    maker.SetMaxDegree(8)
    for station in stations:
        # Stable seam anchored to projected global X; these paths never have
        # an X-parallel tangent. Refuse that degeneracy rather than twisting.
        n = unit(station['normal'])
        xdir = unit([1-n[0]*n[0], -n[0]*n[1], -n[0]*n[2]])
        axes = api['gp_Ax2'](api['gp_Pnt'](*station['center']),api['gp_Dir'](*n),api['gp_Dir'](*xdir))
        circle = api['gp_Circ'](axes,station['radius'])
        wire = api['BRepBuilderAPI_MakeWire'](api['BRepBuilderAPI_MakeEdge'](circle).Edge()).Wire()
        maker.AddWire(wire)
    maker.Build()
    if not maker.IsDone():
        raise RuntimeError('loft did not complete')
    result = maker.Shape()
    if not cad.valid(result) or cad.indexed(result,cad.TopAbs_SOLID).Extent()!=1:
        raise ValueError('loft is not one valid solid')
    return result


def bbox(api, shape):
    box=api['Bnd_Box'](); api['BRepBndLib'].AddOptimal_s(shape,box,False,False)
    return list(box.Get())


def bop_check(shape):
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from collections import Counter
    checker=BOPAlgo_ArgumentAnalyzer(); checker.SetShape1(shape)
    checker.SelfInterMode=True; checker.SmallEdgeMode=True
    checker.RebuildFaceMode=True; checker.ContinuityMode=True; checker.CurveOnSurfaceMode=True
    checker.Perform()
    counts=Counter(str(row.GetCheckStatus()).split('.')[-1] for row in checker.GetCheckResult())
    return {'has_faulty':checker.HasFaulty(),'fault_counts':dict(counts)}


def write_native_and_step(cad, out, name, shape):
    """Retain the native shape even if STEP serialization loses p-curve data."""
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape
    brep_path=out/(name+'.brep'); step_path=out/(name+'.step')
    if brep_path.exists() or step_path.exists(): raise FileExistsError(brep_path)
    native_audit=bop_check(shape)
    if not BRepTools.Write_s(shape,str(brep_path)):
        raise ValueError('native BRep write failed')
    brep_path.chmod(0o600)
    reread_native=TopoDS_Shape()
    if not BRepTools.Read_s(reread_native,str(brep_path),BRep_Builder()):
        raise ValueError('native BRep read failed')
    native_roundtrip=bop_check(reread_native)
    if not cad.valid(reread_native) or native_roundtrip!=native_audit:
        raise ValueError('native BRep roundtrip changed validity')
    cad.write_step(step_path,[{'shape':shape,'role':'diagnostic','name':name+'_NOT_RELEASED'}])
    step_path.chmod(0o600)
    reread_step=cad.read_step(step_path); step_audit=bop_check(reread_step)
    return {'native_BRep_sha256':sha(brep_path),'native_brep_valid':cad.valid(shape),
            'native_BOP':native_audit,'native_solid_count':cad.indexed(shape,cad.TopAbs_SOLID).Extent(),
            'native_roundtrip_BOP':native_roundtrip,
            'native_roundtrip_volume_delta':cad.volume(reread_native)-cad.volume(shape),
            'STEP_sha256':sha(step_path),'STEP_brep_valid':cad.valid(reread_step),
            'STEP_solid_count':cad.indexed(reread_step,cad.TopAbs_SOLID).Extent(),
            'STEP_BOP':step_audit,'STEP_volume_delta':cad.volume(reread_step)-cad.volume(shape),
            'STEP_qualified_for_further_CAD':cad.valid(reread_step) and not step_audit['has_faulty'],
            'no_tolerance_or_translator_parameter_override':True}


def run(args):
    start=time.monotonic()
    paths={'body':args.body,'body_build':args.body_build,'interfaces':args.interfaces,
           'repair_report':args.repair_report,'module_build':args.module_build,
           'module_STEP':args.module_build.parent/'closed.step',
           'routing_source':Path(__file__),'module_source':Path(design.__file__)}
    hashes={key:sha(path) for key,path in paths.items()}
    if hashes['body']!=args.body_sha256 or hashes['interfaces']!=args.interfaces_sha256:
        raise ValueError('source hash mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    interfaces=json.loads(args.interfaces.read_text()); build=json.loads(args.body_build.read_text())
    module=json.loads(args.module_build.read_text())
    repair=json.loads(args.repair_report.read_text())
    if (build['module_sha256']!=module['closed_step']['sha256']
            or hashes['module_STEP']!=build['module_sha256']
            or build['candidate_sha256']!=repair['original_candidate_sha256']
            or hashes['body']!=repair['candidate_sha256']):
        raise ValueError('module to body repair provenance chain mismatch')
    p=design.Parameters(**module['parameters']).validate()
    if build['registration']!={'scale_scan_units_per_mm_hypothesis':1.0,
                              'rotation_Z_deg_hypothesis':-90.0,'translation_Z_hypothesis':3.0}:
        raise ValueError('this routing trial requires the recorded existing frame')
    check_registered_axes(p,build['tools_private'])
    # The body build receipt predates its local p-curve repair. The exact final
    # body hash is required explicitly, not compared to the pre-repair hash.
    cad=design.CAD(); api=native(); body=cad.read_step(args.body)
    if not cad.valid(body) or cad.indexed(body,cad.TopAbs_SOLID).Extent()!=1:
        raise ValueError('one valid master required')
    args.output.mkdir(parents=True,mode=0o700)
    import OCP
    save(args.output/'execution-context.json',{'inputs_sha256':hashes,'OCP_version':OCP.__version__,
         'axis_comparison_absolute_tolerance_scan_units':1e-10,'new_geometry_is_exploratory':True,
         'trunk_interpolation':args.trunk_interpolation,'branch_interpolation':'smooth',
         'manufacturing_authorized':False})
    report={'schema':'m64-scan-seeded-port-routing-private/v1','inputs_sha256':hashes,
            'source_sha256':sha(__file__),'length_unit':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
            'status':'routing_in_progress','manufacturing_authorized':False,
            'master_geometry_modified':False,'original_internals_reconstructed':False,
            'semantic_mapping':{'intake':'high_B','exhaust':'low_B'},
            'semantic_mapping_status':'new_V2_design_choice_not_OEM_and_opposite_legacy_F36_labels',
            'design_choices':{'guide_boss_radius':7.5,'guide_boss_start_axial':32.,
                              'guide_boss_end_axial':100.,'branch_stations':17,
                              'throat_start_axial':5.99,'branch_trunk_overlap':3.,
                              'terminal_lateral_offset':{'intake':2.,'exhaust':3.},
                              'branch_radius':'constant_throat_radius',
                              'trunk_interpolation':args.trunk_interpolation,
                              'branch_interpolation':'smooth',
                              'trunk_C0_station_junctions_expected':args.trunk_interpolation=='ruled',
                              'trunk_section_centres_and_radii_modified':False,
                              'outlet_extension_beyond_body_bbox':8.},
            'bank_records':[],'wall_thickness_verified':False,'exterior_openings_qualified':False,
            'M64_fitment_validated':False,'flow_or_thermal_performance_simulated':False,
            'source_bbox_private':bbox(api,body)}
    protected=[]
    for tool in build['tools_private']:
        origin,axis=tool['axis_origin'],tool['axis_direction']
        boss=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(*add(origin,mul(axis,32.))),cad.gp_Dir(*axis)),7.5,68.).Shape()
        protected.append(boss)
    bosses=cad.compound(protected)
    banks={}
    for kind,side,tangent,approach,offset in [('intake','high_B',30.,28.,2.),('exhaust','low_B',23.,23.,3.)]:
        seeds=seed_sections(interfaces,side)
        extension=dict(seeds[-1]); extension['center']=list(extension['center'])
        sign=seeds[-1]['normal'][1]
        extension['center'][1]=report['source_bbox_private'][4 if sign>0 else 1]+8*sign
        trunk=loft(cad,api,seeds+[extension],ruled=args.trunk_interpolation=='ruled')
        branches=[]; records=[]
        for spec in design.valve_specs(p):
            if spec['kind']!=kind: continue
            tool=next(row for row in build['tools_private'] if row['name']==spec['name'])
            profiles,_=design.profiles(p,spec)
            throat=min(r for r,z in profiles['seat'])
            origin=add(tool['axis_origin'],mul(tool['axis_direction'],5.99))
            join_seed=dict(seeds[0])
            join_seed['center']=add(seeds[0]['center'],mul(seeds[0]['normal'],3.))
            join_seed['center'][0]+=math.copysign(offset,tool['axis_origin'][0])
            join_seed['radius']=throat
            stations,controls=branch_stations(origin,tool['axis_direction'],throat,join_seed,tangent,approach)
            branch=loft(cad,api,stations)
            branches.append(branch)
            records.append({'name':spec['name'],'throat_radius':throat,'controls_private':controls,
                            'volume_scan_units_cubed':cad.volume(branch)})
        bank=branches[0]
        stages=[]
        for branch in [branches[1],trunk]:
            bank=operation(cad,api['BRepAlgoAPI_Fuse'],bank,branch)
            stages.append({'stage':'fuse_branch','solids':cad.indexed(bank,cad.TopAbs_SOLID).Extent(),
                           'volume':cad.volume(bank)})
        bank=operation(cad,api['BRepAlgoAPI_Cut'],bank,bosses)
        stages.append({'stage':'protect_guide_bosses','solids':cad.indexed(bank,cad.TopAbs_SOLID).Extent(),
                       'volume':cad.volume(bank)})
        if cad.indexed(bank,cad.TopAbs_SOLID).Extent()!=1:
            path=args.output/(kind+'-rejected-negative.step')
            cad.write_step(path,[{'shape':bank,'role':'diagnostic','name':'REJECTED_disconnected_gas_negative'}])
            report['status']='rejected_port_bank_disconnected'
            report['failure']={'kind':kind,'stages':stages,'diagnostic_STEP_sha256':sha(path)}
            save(args.output/'routing-report.json',report)
            print(json.dumps(report['failure']),flush=True)
            return 2
        exported=write_native_and_step(cad,args.output,kind+'-negative',bank)
        if exported['native_BOP']['has_faulty']:
            report['status']='rejected_native_port_BOP';report['failure']={'kind':kind,'exported':exported}
            save(args.output/'routing-report.json',report);return 2
        # Native .brep is authoritative for this experiment. A failed STEP is
        # retained as an explicitly rejected exchange derivative, never used
        # to cut the body or represented as a fabrication-ready export.
        banks[kind]=bank
        row={'kind':kind,'side':side,'seed_sections_private':seeds,'extension_private':extension,
             'branches':records,'stages':stages,'exports':exported,
             'body_cut_uses':'native_BRep_not_STEP_reimport',
             'volume_scan_units_cubed':cad.volume(bank)}
        report['bank_records'].append(row)
        save(args.output/(kind+'-checkpoint.json'),row)
        print(json.dumps({'bank_completed':kind,'one_connected_solid':True}),flush=True)
    common=operation(cad,api['BRepAlgoAPI_Common'],banks['intake'],banks['exhaust'])
    report['intake_exhaust_common_volume']=cad.volume(common)
    report['intake_exhaust_distance']=cad.distance(banks['intake'],banks['exhaust'])
    if report['intake_exhaust_common_volume']>1e-7 or report['intake_exhaust_distance']<=1e-5:
        report['status']='rejected_bank_collision';save(args.output/'routing-report.json',report);return 2
    candidate=body
    for kind,bank in banks.items():
        candidate=operation(cad,api['BRepAlgoAPI_Cut'],candidate,bank)
        if cad.indexed(candidate,cad.TopAbs_SOLID).Extent()!=1:
            report['status']='rejected_body_disconnected';save(args.output/'routing-report.json',report);return 2
        print(json.dumps({'body_cut_completed':kind,'one_solid':True}),flush=True)
    exported=write_native_and_step(cad,args.output,'ported-candidate',candidate)
    report.update({'status':'native_ported_candidate_built_not_qualified','candidate_exports':exported,
                   'source_volume_scan_units_cubed':cad.volume(body),
                   'candidate_volume_scan_units_cubed':cad.volume(candidate),
                   'candidate_bbox_private':bbox(api,candidate),'wall_seconds':time.monotonic()-start})
    if exported['native_BOP']['has_faulty']:
        report['status']='native_ported_candidate_rejected_BOP'
    report['input_files_unchanged']=all(sha(paths[key])==value for key,value in hashes.items())
    if not report['input_files_unchanged']:
        raise ValueError('input changed during routing')
    save(args.output/'routing-report.json',report)
    print(json.dumps({'status':report['status'],'candidate_exports':exported,'wall_seconds':report['wall_seconds']}),flush=True)
    return 0 if not exported['native_BOP']['has_faulty'] and exported['STEP_qualified_for_further_CAD'] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('body','body-build','repair-report','interfaces','module-build','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    for key in ('body-sha256','interfaces-sha256'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--trunk-interpolation',choices=('smooth','ruled'),default='smooth',
                        help='trunk only; ruled retains C0 joins at every recorded section')
    args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU,(1200,1210))
    output_preexisted=args.output.exists()
    try:
        return run(args)
    except Exception as error:
        if not output_preexisted and args.output.is_dir():
            save(args.output/'execution-failure.json',{'status':'failed_no_candidate_accepted',
                 'exception_class':type(error).__name__,'reason':str(error),
                 'source_sha256':sha(__file__),'manufacturing_authorized':False})
        raise


if __name__=='__main__':
    raise SystemExit(main())
