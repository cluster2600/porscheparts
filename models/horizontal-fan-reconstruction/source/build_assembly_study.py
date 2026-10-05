#!/usr/bin/env python3
"""Build editable packaging envelopes around unchanged V2 CAD; no installed fits."""
import argparse,hashlib,json,math,os,resource,time
from pathlib import Path
from assembly_interface_gate import evaluate


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root,output):
    import build123d as cad
    started=time.monotonic();p=json.loads((root/'parameters/assembly-study-S1.json').read_text())
    contract=json.loads((root/'parameters/assembly-interface-contract.json').read_text());gate=evaluate(contract,p)
    output.mkdir(parents=True,exist_ok=False);D=p['reference_diameter_mm'];R=D/2
    base=json.loads((root/'parameters/V2.json').read_text())
    if D!=base['diameter_mm'] or gate['functional_completion_allowed']:raise ValueError('Expected unmeasured V2 study')
    # The imported original assembly remains byte-identical at its source.
    imported=cad.import_step(root/'V2-assembly.step')
    original=cad.Compound(list(imported.solids()))
    gap=base['tip_gap_ratio']*R;wall=base['shroud_wall_ratio']*R
    top_z=-.18*D;depth=p['plenum_depth_over_D']*D;bottom_z=top_z-depth
    outer_top=R+gap+wall;outer_bottom=p['plenum_bottom_radius_over_D']*D
    inner=p['plenum_inner_exclusion_radius_over_D']*D;t=p['plenum_wall_mm']
    if not (0<t<inner<outer_top<outer_bottom and depth>0):raise ValueError('Invalid study plenum envelope')
    def cyl(radius,height,origin=(0,0,0),axis=(0,0,1)):
        return cad.Solid.make_cylinder(radius,height,cad.Plane(origin=origin,z_dir=axis))
    plane=cad.Plane(origin=(0,0,bottom_z))
    outside=cad.Solid.make_cone(outer_bottom,outer_top,depth,plane)
    inside=cad.Solid.make_cone(outer_bottom-t,outer_top-t,depth+2,cad.Plane(origin=(0,0,bottom_z-1)))
    # Study duct shell only: an open bottom, open central exclusion and a drive passage.
    plenum=outside.cut(inside)
    gear_z=-.31*D;corridor=cyl(p['drive_corridor_radius_mm'],D,(0,0,gear_z),(1,0,0))
    plenum=plenum.cut(corridor)
    rp=p['pulley_pitch_diameter_mm']/2;width=p['pulley_width_mm'];x=p['pulley_axial_position_over_D']*D
    C=p['pulley_center_distance_mm'];shaft_radius=R*base['bore_radius_ratio']*.72
    upper=cyl(rp,width,(x,0,gear_z),(1,0,0)).cut(cyl(shaft_radius*1.08,width+2,(x-1,0,gear_z),(1,0,0)))
    lower=cyl(rp,width,(x,0,gear_z-C),(1,0,0))
    shaft_extension=cyl(shaft_radius,x+width-.35*D,(.35*D,0,gear_z),(1,0,0))
    # Equal-pulley pitch-path envelope; no belt teeth, grooves or tensioner implied.
    bw=width/2;bt=3.;belt=[]
    for y in [-rp,rp]:
        belt.append(cad.Solid.make_box(bw,bt,C,cad.Plane(origin=(x+width/4,y-bt/2,gear_z-C))))
    for z in [gear_z,gear_z-C]:
        ring=cyl(rp+bt/2,bw,(x+width/4,0,z),(1,0,0)).cut(cyl(rp-bt/2,bw+2,(x+width/4-1,0,z),(1,0,0)))
        half=cad.Solid.make_box(D,2*D,D,cad.Plane(origin=(0,-D,z if z==gear_z else z-D)))
        part=ring.intersect(half)
        belt.extend(part if isinstance(part,cad.ShapeList) else [part])
    belt=cad.Compound(belt)
    sw=p['support_section_width_mm'];sh=p['support_section_height_mm']
    supports=cad.Compound([cad.Solid.make_box(.5*D,sw,sh,cad.Plane(origin=(-.25*D,y-sw/2,bottom_z-sh))) for y in [-.28*D,.28*D]])
    shapes={'V2_original_assembly':original,'plenum_shell_envelope':plenum,
            'input_pulley_pitch_envelope':upper,'driver_pulley_pitch_envelope':lower,
            'input_shaft_extension_envelope':shaft_extension,
            'belt_pitch_path_envelope':belt,'support_stock_envelopes':supports}
    records={};geometry_dir=output/'geometry';geometry_dir.mkdir()
    for name,shape in shapes.items():
        valid=bool(shape.is_valid)
        if not valid or shape.volume<=0:raise ValueError('Invalid positive BRep: '+name)
        step=geometry_dir/(name+'.step');mesh=geometry_dir/(name+'.stl')
        cad.export_step(shape,step);cad.export_stl(shape,mesh,tolerance=.15,angular_tolerance=.2)
        reread=cad.import_step(step);err=abs(reread.volume/shape.volume-1)
        if not reread.is_valid or err>1e-6:raise ValueError('STEP roundtrip: '+name)
        box=shape.bounding_box()
        solid_meshes={}
        for index,solid in enumerate(shape.solids()):
            solid_mesh=geometry_dir/(name+'_solid'+str(index)+'.stl')
            cad.export_stl(solid,solid_mesh,tolerance=.15,angular_tolerance=.2)
            solid_meshes[solid_mesh.name]=sha(solid_mesh)
        records[name]={'brep_valid':valid,'solids':len(shape.solids()),'volume_mm3':shape.volume,
                       'bounds_mm':[list(box.min),list(box.max)],'step_roundtrip_relative_volume_error':err,
                       'STEP_volume_representation_screen_relative':1e-6,
                       'STEP_representation_screen_is_not_manufacturing_tolerance':True,
                       'step_sha256':sha(step),'stl_sha256':sha(mesh),
                       'separate_solid_STL_sha256':solid_meshes,
                       'role':'unchanged_analytical_study' if name.startswith('V2') else 'assumed_packaging_envelope'}
    cad.export_step(cad.Compound(list(shapes.values())),output/'S1-assembly.step')
    intersection=original.intersect(plenum)
    common_volume=0. if intersection is None else sum(s.volume for s in intersection) if isinstance(intersection,cad.ShapeList) else intersection.volume
    if common_volume>1e-5:raise ValueError('Plenum intersects original V2 study')
    s=p['sizing_scenario'];deltaF=2*s['torque_Nm']/p['pulley_pitch_diameter_mm']*1000
    pret=s['belt_pretension_per_span_N'];ft=pret+deltaF/2;fs=pret-deltaF/2
    n=s['rotor_speed_rpm'];omega=n*2*math.pi/60
    report={'status':'editable_assembly_layout_study_only','study_id':p['study_id'],'units':'mm','up_axis':'Z',
            'source_assembly_sha256':sha(root/'V2-assembly.step'),'source_rotor_sha256':sha(root/'V2-rotor.step'),
            'parameters_sha256':sha(root/'parameters/assembly-study-S1.json'),
            'interface_contract_sha256':sha(root/'parameters/assembly-interface-contract.json'),
            'builder_sha256':sha(Path(__file__)),'build123d_version':cad.__version__,
            'interface_gate':gate,'components':records,'assembly_step_sha256':sha(output/'S1-assembly.step'),
            'layout_clearance_checks':{'original_plenum_intersection_volume_mm3':common_volume,
              'central_exclusion_radius_mm':inner,'shaft_passage_radius_mm':p['drive_corridor_radius_mm'],
              'physical_engine_packaging_and_support_attachment_verified':False},
            'derived_sizing':{'pulley_ideal_speed_ratio':1-s['belt_slip_fraction'],
              'equal_pulley_open_belt_pitch_length_mm':2*C+math.pi*p['pulley_pitch_diameter_mm'],
              'belt_speed_m_s':math.pi*p['pulley_pitch_diameter_mm']/1000*n/60,
              'torque_power_W':s['torque_Nm']*omega,'belt_tension_difference_N':deltaF,
              'assumed_tight_span_N':ft,'assumed_slack_span_N':fs,'resultant_equal_pulley_bearing_load_N':ft+fs,
              'positive_slack_for_assumed_pretension':fs>0,
              'plenum_annular_bottom_flow_area_m2':math.pi*((outer_bottom-t)**2-(inner+t)**2)*1e-6,
              'plenum_effective_velocity_at_diagnostic_Q_m_s':None,
              'sizing_is_not_verified_service_load_or_component_selection':True},
            'functional_interfaces_verified':False,'physical_validation_established':False,
            'manufacturing_authorized':False,'elapsed_seconds':time.monotonic()-started,
            'peak_RSS_bytes_mac':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    diagnostic=json.loads((root/'results/cfd/D2-establishment-diagnostic.json').read_text())
    report['derived_sizing']['plenum_effective_velocity_at_diagnostic_Q_m_s']=diagnostic['physical_time_proxies']['net_common_flow1020_m3_s']/report['derived_sizing']['plenum_annular_bottom_flow_area_m2']
    report['derived_sizing']['unconverged_diagnostic_Q_report_sha256']=sha(root/'results/cfd/D2-establishment-diagnostic.json')
    (output/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'components':len(shapes),'elapsed_seconds':report['elapsed_seconds'],'missing_interfaces':len(gate['missing_evidence'])}));return report


if __name__=='__main__':
    os.nice(15);cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('root',type=Path);cli.add_argument('output',type=Path)
    args=cli.parse_args();build(args.root,args.output)
