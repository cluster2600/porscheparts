#!/usr/bin/env python3
"""Read-only native/contextual BRepCheck localization of a rejected gas cut.

No Boolean replay, tolerance modification, healing, component omission or
geometry integration. Private outputs contain exact diagnostic subshapes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import resource
import sys
import time

import audit_gas_boundaries as boundaries
import build_local_port_junction_fillet as local
import prepare_picogk_intake_junction as prep


def status_names(statuses):
    return [str(status).split('.')[-1] for status in statuses if str(status).split('.')[-1]!='BRepCheck_NoError']


def inspect_native(cad, shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    kinds={'solid':TopAbs_SOLID,'shell':TopAbs_SHELL,'face':TopAbs_FACE,
           'wire':TopAbs_WIRE,'edge':TopAbs_EDGE,'vertex':TopAbs_VERTEX}
    maps={name:cad.indexed(shape,kind) for name,kind in kinds.items()}
    # Set exact method at construction, before checks are initialized.
    analyzer=BRepCheck_Analyzer(shape,True,False,True)
    valid=analyzer.IsValid()
    records=[];bad_faces=set();bad_edges=set();histogram=Counter()
    def identity(subshape):
        for name,kind in kinds.items():
            if subshape.ShapeType()==kind:
                return {'kind':name,'id':maps[name].FindIndex(subshape)}
        return {'kind':str(subshape.ShapeType()),'id':0}
    for name,indexed in maps.items():
        for index in range(1,indexed.Extent()+1):
            sub=indexed.FindKey(index);result=analyzer.Result(sub)
            if result is None:continue
            statuses=status_names(result.Status());contexts=[]
            result.InitContextIterator()
            while result.MoreShapeInContext():
                values=status_names(result.StatusOnShape())
                if values:
                    context=result.ContextualShape()
                    contexts.append({'context':identity(context),'statuses':values})
                    if context.ShapeType()==TopAbs_FACE:bad_faces.add(maps['face'].FindIndex(context))
                    if context.ShapeType()==TopAbs_EDGE:bad_edges.add(maps['edge'].FindIndex(context))
                result.NextShapeInContext()
            if not statuses and not contexts:continue
            histogram.update(statuses)
            for row in contexts:histogram.update(row['statuses'])
            row={'kind':name,'id':index,'self_statuses':statuses,'contextual_statuses':contexts,
                 'native_bbox_private':prep.native_bounds(sub)}
            if name=='face':
                face=TopoDS.Face_s(sub);bad_faces.add(index)
                row.update(tolerance=BRep_Tool.Tolerance_s(face),area=cad.area(face),
                           surface_type=str(BRepAdaptor_Surface(face,False).GetType()).split('.')[-1])
            elif name=='edge':
                edge=TopoDS.Edge_s(sub);bad_edges.add(index)
                row.update(tolerance=BRep_Tool.Tolerance_s(edge),degenerated=BRep_Tool.Degenerated_s(edge),
                           same_parameter=BRep_Tool.SameParameter_s(edge),same_range=BRep_Tool.SameRange_s(edge))
                if not row['degenerated']:
                    curve=BRepAdaptor_Curve(edge)
                    row.update(curve_type=str(curve.GetType()).split('.')[-1],
                               parameter_range=[curve.FirstParameter(),curve.LastParameter()])
            elif name=='vertex':row['tolerance']=BRep_Tool.Tolerance_s(TopoDS.Vertex_s(sub))
            records.append(row)
    bad_faces.discard(0);bad_edges.discard(0)
    # Wires with contextual faults can implicate otherwise self-valid edges.
    for row in records:
        if row['kind']=='wire':
            wire_edges=cad.indexed(maps['wire'].FindKey(row['id']),TopAbs_EDGE)
            bad_edges.update(maps['edge'].FindIndex(wire_edges.FindKey(i)) for i in range(1,wire_edges.Extent()+1))
    bad_edges.discard(0)
    return {'BRep_valid_exact_method':valid,'topology_counts':{k:v.Extent() for k,v in maps.items()},
        'exact_method_only_applies_to_SameParameter_edges_per_OCCT':True,
        'status_occurrence_counts_not_unique_defect_counts':dict(histogram),
        'invalid_records':records,'implicated_face_ids':sorted(bad_faces),'implicated_edge_ids':sorted(bad_edges)},maps


def inspect_shells(cad, shape):
    """Report oriented shells and shared topology; never delete small shells."""
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    shells=cad.indexed(shape,TopAbs_SHELL);faces=cad.indexed(shape,cad.TopAbs_FACE)
    rows=[];pair_rows=[];implicated=set()
    for i in range(1,shells.Extent()+1):
        shell=shells.FindKey(i);shell_faces=cad.indexed(shell,cad.TopAbs_FACE)
        props=GProp_GProps();BRepGProp.VolumeProperties_s(shell,props)
        face_rows=[]
        for j in range(1,shell_faces.Extent()+1):
            face=TopoDS.Face_s(shell_faces.FindKey(j))
            face_rows.append({'face_id_in_solid':faces.FindIndex(face),'area':cad.area(face),
                'surface_type':str(BRepAdaptor_Surface(face,False).GetType()).split('.')[-1],
                'orientation_in_shell':str(face.Orientation()).split('.')[-1],
                'tolerance':BRep_Tool.Tolerance_s(face),'native_bbox_private':prep.native_bounds(face)})
        rows.append({'shell_id':i,'orientation':str(shell.Orientation()).split('.')[-1],
            'face_count':shell_faces.Extent(),'signed_volume_quadrature_not_bound':props.Mass(),
            'area':cad.area(shell),'native_bbox_private':prep.native_bounds(shell),
            'BRep_valid_exact_method':inspect_native(cad,shell)[0]['BRep_valid_exact_method'],
            'faces':face_rows})
    for i in range(len(rows)):
        for j in range(i+1,len(rows)):
            shared=sorted({r['face_id_in_solid'] for r in rows[i]['faces']} &
                          {r['face_id_in_solid'] for r in rows[j]['faces']})
            pair_rows.append({'shell_ids':[i+1,j+1],'shared_native_face_ids':shared,
                'distance':cad.distance(shells.FindKey(i+1),shells.FindKey(j+1)),
                'distance_zero_does_not_establish_shared_area':True})
            if shared:
                implicated.update(shared)
                # Localize every face of both shells that actually share topology.
                # The largest shell's nonshared faces are not fault-local evidence.
                smaller=min((rows[i],rows[j]),key=lambda r:r['face_count'])
                implicated.update(r['face_id_in_solid'] for r in smaller['faces'])
    return {'shells':rows,'pairs':pair_rows,
            'signed_volume_is_not_a_reason_to_remove_a_shell':True,
            'shared_topology_localization_face_ids':sorted(implicated)}


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS
    started=time.monotonic()
    if args.output.exists() or args.output.is_symlink():raise FileExistsError(args.output)
    paths={'before':args.run_dir/'before-component-cut.brep',
           'after':args.run_dir/'rejected-after-component-cut.brep',
           'builder_report':args.run_dir/'gas-domain-report.json',
           'module':args.module,'build':args.build,'registration':args.registration,
           'diagnostic_source':Path(__file__),'boundaries_source':Path(boundaries.__file__),
           'local_source':Path(local.__file__),'bounds_source':Path(prep.__file__)}
    hashes={name:boundaries.inspection.digest(path) for name,path in paths.items()}
    existing=json.loads(paths['builder_report'].read_text())
    if (hashes['before']!=existing['before_component_cut_sha256'] or
            hashes['after']!=existing['rejected_candidate_sha256'] or
            any(hashes[k]!=boundaries.inspection.EXPECTED[k] for k in ('module','build','registration'))):
        raise ValueError('Exact rejected-run/module provenance required')
    args.output.mkdir(parents=True,mode=0o700)
    report={'schema':'m64-rejected-gas-boolean-native-diagnostic/v1','inputs_sha256':hashes,
            'OCP_version':OCP.__version__,'status':'running',
            'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
            'native_Boolean_replayed':False,'tolerance_modified':False,'geometry_repaired':False,
            'master_modified':False,'manufacturing_authorized':False,'CFD_qualified':False}
    def save(label):
        report['elapsed_seconds']=time.monotonic()-started
        local.ports.save(args.output/(label+'.json'),report)
    save('preregistration')
    cad=boundaries.inspection.design.CAD()
    try:
        before=local.read_native(paths['before']);after=local.read_native(paths['after'])
        report['before'],_=inspect_native(cad,before);save('before-checkpoint')
        report['after'],indexed=inspect_native(cad,after);save('after-checkpoint')
        report['shell_diagnostic']=inspect_shells(cad,after);save('shell-checkpoint')
        registration=json.loads(args.registration.read_text())
        if registration['registration']!={'scale_scan_units_per_mm_hypothesis':1.,'rotation_Z_deg_hypothesis':-90.,'translation_Z_hypothesis':3.}:
            raise ValueError('Recorded one-time module registration required')
        p=boundaries.inspection.design.Parameters(**json.loads(args.build.read_text())['parameters']).validate()
        module=cad.read_step(args.module);parts=cad.indexed(module,cad.TopAbs_SOLID)
        ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
        components={}
        for spec in boundaries.inspection.design.valve_specs(p):
            for role in ('seat','valve','guide'):
                name=spec['name']+'_'+role
                lift=6. if role=='valve' and spec['kind']=='intake' else 0.
                components[name]=boundaries.registered(cad,parts.FindKey(ids[name]),spec,lift)
        report['localized_faces']=[]
        implicated_faces=set(report['after']['implicated_face_ids']) | set(report['shell_diagnostic']['shared_topology_localization_face_ids'])
        for index in sorted(implicated_faces):
            face=TopoDS.Face_s(indexed['face'].FindKey(index))
            path=args.output/f'implicated-face-{index:04d}.brep'
            BRepTools.Write_s(face,str(path));path.chmod(0o600)
            distances={name:cad.distance(face,component) for name,component in components.items()}
            report['localized_faces'].append({'face_id':index,'native_face_sha256':boundaries.inspection.digest(path),
                'distance_to_each_actual_component':distances,
                'distance_is_localization_not_contact_area_or_containment_proof':True})
            save(f'face-{index:04d}-checkpoint')
        report['localized_edges']=[]
        for index in report['after']['implicated_edge_ids']:
            edge=TopoDS.Edge_s(indexed['edge'].FindKey(index))
            path=args.output/f'implicated-edge-{index:04d}.brep'
            BRepTools.Write_s(edge,str(path));path.chmod(0o600)
            report['localized_edges'].append({'edge_id':index,'native_edge_sha256':boundaries.inspection.digest(path),
                'native_bbox_private':prep.native_bounds(edge)})
        report['status']='read_only_native_fault_localization_complete'
    except Exception as exc:
        report['status']='partial_diagnostic';report['error']=type(exc).__name__+': '+str(exc)
    report['all_input_hashes_unchanged']=all(boundaries.inspection.digest(path)==hashes[name] for name,path in paths.items())
    report['process_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    save('diagnostic-report')
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],
                      'error':report.get('error'),'output':str(args.output)}))
    return 0 if report['status']=='read_only_native_fault_localization_complete' else 3


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run-dir','module','build','registration','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(300,305))
    raise SystemExit(run(parser.parse_args()))
