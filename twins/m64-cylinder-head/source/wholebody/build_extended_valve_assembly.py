#!/usr/bin/env python3
"""Extend four retained native valve stems; report, never remove, body collisions.

Only the existing radius-3 stem is continued from axial 82 to 105. Keeper
grooves, retainers and supplier interfaces are neither invented nor qualified.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

from render_v5_v2 import PINS, REGISTRATION, preflight, save, sha

BODY_SHA = '111342292d92b7303072ecc5be606047ac810df25ee4fa5c112f992404224c60'
BODY_REPORT_SHA = 'da3dd990f8ef802459cdedb8efd0600aa9274632303b11dd978cdf761d17272a'
DEPENDENCIES = {'render_v5_v2.py':'63ccd3df8f07997a1bbeb6d7ba1434732622c7fc41106483ace0155ff00c3947',
                'build_four_valve_distribution.py':'4604b5fbc74e02c7029481cdf269a3ee93d208229d87379bc6545db46bdb3d1c'}
LIFTS = {'intake':11.5,'exhaust':9.6}
STEM_RADIUS, ORIGINAL_TIP, NEW_TIP = 3., 82., 105.
ADDED_VOLUME = math.pi*STEM_RADIUS**2*(NEW_TIP-ORIGINAL_TIP)


def stroke_vector(bank, axis):
    if (bank not in LIFTS or len(axis)!=3 or any(isinstance(v,bool) or not math.isfinite(v) for v in axis)
            or abs(math.dist(axis,[0.,0.,0.])-1.)>1e-12 or axis[2]<=0):
        raise ValueError('retained_unit_axis_and_bank_required')
    return [-LIFTS[bank]*a for a in axis]


def native_stem_gate(radius, low, high, dot, cap_area, radial_error):
    values=(radius,low,high,dot,cap_area,radial_error)
    return (all(not isinstance(v,bool) and math.isfinite(v) for v in values)
            and abs(radius-3.)<1e-10 and abs(low-9.)<1e-8 and abs(high-82.)<1e-8
            and abs(abs(dot)-1.)<1e-12 and abs(cap_area-math.pi*9.)<1e-8 and 0.<=radial_error<1e-8)


def zero_volume(solids, volume):
    return type(solids) is int and solids==0 and not isinstance(volume,bool) and math.isfinite(volume) and 0.<=volume<=1e-7


def addition_gate(removed_solids, removed_volume, added_volume, outside_solids, outside_volume):
    return (zero_volume(removed_solids,removed_volume) and zero_volume(outside_solids,outside_volume)
            and not isinstance(added_volume,bool) and math.isfinite(added_volume)
            and math.isclose(added_volume,ADDED_VOLUME,rel_tol=1e-9,abs_tol=1e-7))


def run(root, padded, output):
    import OCP
    from OCP.BinTools import BinTools, BinTools_FormatVersion_VERSION_3
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.TopoDS import TopoDS_Shape
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    if OCP.__version__!='7.9.3.1':raise ValueError('exact_OCP_required')
    started=time.monotonic()
    sources={Path(__file__).name:Path(__file__),'render_v5_v2.py':Path(__file__).with_name('render_v5_v2.py'),
             'build_four_valve_distribution.py':Path(design.__file__)}
    source_hashes={name:sha(path) for name,path in sources.items()}
    if any(source_hashes[name]!=h for name,h in DEPENDENCIES.items()):raise ValueError('frozen_dependency_mismatch')
    def inputs():
        preflight(root)
        for name,h in (('candidate.binbrep',BODY_SHA),('report.json',BODY_REPORT_SHA)):
            path=padded/name
            if path.is_symlink() or sha(path)!=h:raise ValueError('padded_body_binding_mismatch')
        if source_hashes!={name:sha(path) for name,path in sources.items()}:raise ValueError('source_changed')
    inputs();cad=design.CAD();fuzzy=[]
    def indexed(shape,kind):
        table=cad.indexed(shape,kind);return [table.FindKey(i) for i in range(1,table.Extent()+1)]
    def one(shape):
        if (shape.IsNull() or not cad.valid(shape) or len(indexed(shape,cad.TopAbs_SOLID))!=1
                or len(indexed(shape,TopAbs_SHELL))!=1):raise ValueError('one_exact_valid_solid_shell_required')
    def operation(cls,a,b):
        aa=TopTools_ListOfShape();aa.Append(a);bb=TopTools_ListOfShape();bb.Append(b)
        job=cls();job.SetArguments(aa);job.SetTools(bb);job.SetNonDestructive(True);job.SetRunParallel(False);job.Build()
        if not job.IsDone() or job.Shape().IsNull() or not cad.valid(job.Shape()):raise ValueError('invalid_native_boolean')
        fuzzy.append(job.FuzzyValue());return job.Shape()
    def write(shape,name):
        path=output/name
        if path.exists() or not BinTools.Write_s(shape,str(path),False,False,BinTools_FormatVersion_VERSION_3):raise ValueError('exclusive_native_write_failed')
        return sha(path)
    def count(shape):return len(indexed(shape,cad.TopAbs_SOLID))
    body=TopoDS_Shape()
    if not BinTools.Read_s(body,str(padded/'candidate.binbrep')):raise ValueError('padded_body_read_failed')
    one(body)
    module=cad.read_step(root/'closed.step');actual=cad.indexed(module,cad.TopAbs_SOLID)
    reg=json.loads((root/'registration.json').read_text());axes={row['name']:row for row in reg['tools_private']}
    if len(axes)!=4 or set(axes)!={f'{b}_{i}' for b in LIFTS for i in (1,2)}:raise ValueError('four_retained_axes_required')
    tr=cad.gp_Trsf();tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
    tr.SetTranslationPart(cad.gp_Vec(0,0,3))
    parts=[(row['name'],row['imported_module_solid_id'],cad.BRepBuilderAPI_Transform(actual.FindKey(row['imported_module_solid_id']),tr,True).Shape())
           for row in sorted(reg['components_imported_from_exact_STEP'],key=lambda r:r['imported_module_solid_id'])]
    os.umask(0o077);output.mkdir(parents=True,mode=0o700,exist_ok=False)
    retained=write(body,'retained-body-before.binbrep')
    old_parts_hash=write(cad.compound([part for _,_,part in parts]),'retained-module-before.binbrep')
    report={'schema':'private-V5-V2-extended-valve-assembly/v1','source_sha256':source_hashes,'input_pins':PINS,
            'padded_body_sha256':BODY_SHA,'padded_body_report_sha256':BODY_REPORT_SHA,'OCP_version':OCP.__version__,
            'registration':REGISTRATION,'unit':'uncalibrated_scan_units_under_1_unit_per_mm_hypothesis',
            'stem_radius':3.,'original_tip':82.,'new_tip':105.,'keeper_retainer_supplier_interfaces_modeled':False,
            'body_modified':False,'seats_or_guides_modified':False,'physical_fitment_or_dynamics_qualified':False,
            'manufacturing_authorized':False,'BOP_check_performed':False,'valves':[],'parts':[],'position_screens':[]}
    replacement={}
    for name,source_id,original in parts:
        if not name.endswith('_valve'):continue
        one(original);axisrow=axes[name[:-6]];origin,axis=axisrow['axis_origin'],axisrow['axis_direction']
        stroke_vector(name.split('_')[0],axis)
        def axial(point):return sum(a*(x-o) for a,x,o in zip(axis,point.Coord(),origin))
        stems=[];caps=[]
        for raw in indexed(original,cad.TopAbs_FACE):
            face=cad.TopoDS.Face_s(raw);surf=BRepAdaptor_Surface(face,True)
            if surf.GetType()==GeomAbs_Cylinder and abs(surf.Cylinder().Radius()-3.)<1e-10:
                lo,hi=sorted(axial(surf.Value(surf.FirstUParameter(),v)) for v in (surf.FirstVParameter(),surf.LastVParameter()))
                stems.append((surf.Cylinder(),lo,hi))
            elif surf.GetType()==GeomAbs_Plane:
                props=cad.GProp_GProps();cad.BRepGProp.SurfaceProperties_s(face,props)
                if abs(axial(props.CentreOfMass())-82.)<1e-8:caps.append((props.CentreOfMass(),props.Mass()))
        if len(stems)!=1 or len(caps)!=1:raise ValueError('one_retained_stem_and_top_cap_required')
        cylinder,low,high=stems[0];center,area=caps[0]
        dot=sum(a*b for a,b in zip(axis,cylinder.Axis().Direction().Coord()))
        radial_error=math.dist(center.Coord(),[o+82.*a for o,a in zip(origin,axis)])
        if not native_stem_gate(cylinder.Radius(),low,high,dot,area,radial_error):raise ValueError('retained_native_stem_mismatch')
        # Use the actual imported cylinder direction and cap centre, not a reauthored lower profile.
        direction=[v*(1 if dot>0 else -1) for v in cylinder.Axis().Direction().Coord()]
        extension=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(center,cad.gp_Dir(*direction)),cylinder.Radius(),23.).Shape();one(extension)
        extended=operation(BRepAlgoAPI_Fuse,original,extension);one(extended)
        removed=operation(cad.BRepAlgoAPI_Cut,original,extended)
        added=operation(cad.BRepAlgoAPI_Cut,extended,original)
        outside=operation(cad.BRepAlgoAPI_Cut,added,extension)
        if not addition_gate(count(removed),cad.volume(removed),cad.volume(added),count(outside),cad.volume(outside)):
            raise ValueError('valve_extension_locality_or_volume_failed')
        record={'name':name,'original_module_solid_id':source_id,'native_stem_interval':[low,high],
                'native_cap_axis_residual':radial_error,'original_volume':cad.volume(original),
                'extended_volume':cad.volume(extended),'added_volume':cad.volume(added),'analytic_added_volume':ADDED_VOLUME,
                'removed_volume':cad.volume(removed),'outside_extension_added_volume':cad.volume(outside),
                'extended_native_sha256':write(extended,name+'.binbrep'),'one_valid_solid_shell':True}
        replacement[name]=extended;report['valves'].append(record);print(json.dumps(record),flush=True)
    assembled=[body]
    for index,(name,source_id,original) in enumerate(parts,2):
        assembled.append(replacement.get(name,original))
        report['parts'].append({'name':name,'assembly_solid_id':index,'original_module_solid_id':source_id,
                               'retained_original_shape_used':not name.endswith('_valve')})
    compound=cad.compound(assembled)
    if count(compound)!=13 or not cad.valid(compound):raise ValueError('thirteen_native_valid_solids_required')
    report['assembly_sha256']=write(compound,'extended-valve-assembly.binbrep')
    reread=TopoDS_Shape()
    if not BinTools.Read_s(reread,str(output/'extended-valve-assembly.binbrep')) or count(reread)!=13 or not cad.valid(reread):
        raise ValueError('assembly_saved_readback_failed')
    reread_solids=indexed(reread,cad.TopAbs_SOLID)
    for before,after in zip(assembled,reread_solids):
        one(after)
        if not math.isclose(cad.volume(before),cad.volume(after),rel_tol=1e-12,abs_tol=1e-9):raise ValueError('readback_part_volume_changed')
    # Screens use saved-file shapes, not only transient producer objects.
    saved_body=reread_solids[0]
    for part in report['parts']:
        name=part['name']
        if not name.endswith('_valve'):continue
        row=axes[name[:-6]];valve=reread_solids[part['assembly_solid_id']-1]
        for state in ('closed','declared_full_lift'):
            translation=[0.,0.,0.] if state=='closed' else stroke_vector(name.split('_')[0],row['axis_direction'])
            move=cad.gp_Trsf();move.SetTranslation(cad.gp_Vec(*translation))
            posed=cad.BRepBuilderAPI_Transform(valve,move,True).Shape()
            common=operation(cad.BRepAlgoAPI_Common,saved_body,posed)
            solids,volume=count(common),cad.volume(common)
            record={'name':name,'state':state,'translation':translation,'common_solids':solids,
                    'common_volume':volume,'native_common_valid':cad.valid(common),
                    'body_intersection_empty':zero_volume(solids,volume),'minimum_distance':cad.distance(saved_body,posed)}
            report['position_screens'].append(record);save(output/(name+'-'+state+'.json'),record);print(json.dumps(record),flush=True)
    if retained!=write(body,'retained-body-after.binbrep') or old_parts_hash!=write(cad.compound([part for _,_,part in parts]),'retained-module-after.binbrep'):
        raise ValueError('retained_body_or_module_changed')
    inputs()
    clear=all(r['body_intersection_empty'] for r in report['position_screens'])
    report.update(status='assembly_built_positional_screens_clear' if clear else 'assembly_built_body_interference_present',
                  assembly_solids=13,saved_readback_exact_BRepCheck_valid=True,
                  all_eight_body_intersection_screens_empty=clear,continuous_motion_sweep_tested=False,
                  valve_vs_valve_or_seat_guide_collision_screens_performed=False,
                  original_shapes_unchanged=True,inputs_unchanged=True,Boolean_effective_fuzzy_values=fuzzy,
                  Boolean_tolerance_override=False,healing_applied=False,wall_seconds=time.monotonic()-started)
    report['outputs_sha256']={p.name:sha(p) for p in sorted(output.iterdir())}
    save(output/'report.json',report)
    print(json.dumps({'status':report['status'],'report_sha256':sha(output/'report.json')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('root','padded','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();signal.alarm(600);run(args.root,args.padded,args.output)
