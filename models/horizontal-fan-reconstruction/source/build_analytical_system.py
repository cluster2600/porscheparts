#!/usr/bin/env python3
"""Build an explicit study BRep from parameters; never fits or repairs a scan."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time


def build(parameters, output):
    import build123d as cad
    start=time.monotonic()
    p=parameters
    diameter=float(p['diameter_mm']); radius=diameter/2
    blade_count=int(p['blade_count']); gap=float(p['tip_gap_ratio'])*radius
    root=float(p['blade_root_radius_ratio'])*radius
    carrier=float(p['carrier_radius_ratio'])*radius
    bore=float(p['bore_radius_ratio'])*radius
    thickness=float(p['blade_thickness_ratio'])*radius
    if not (100<diameter<450 and 5<=blade_count<=16 and 0<bore<root<carrier<radius and 0<gap<radius*.04):
        raise ValueError('Invalid exploratory geometry envelope')
    output.mkdir(parents=True,exist_ok=False)
    def cyl(r,h,z=0,origin=None,normal=(0,0,1)):
        return cad.Solid.make_cylinder(r,h,cad.Plane(origin=origin or (0,0,z),z_dir=normal))
    def annulus(r_outer,r_inner,h,z):
        return cyl(r_outer,h,z).cut(cyl(r_inner,h+2,z-1))
    web=float(p['web_thickness_ratio'])*radius
    body=annulus(carrier,bore,web,-web)
    # A tapered boss and through bore are deliberate hypotheses, not mating evidence.
    boss_height=diameter*.12
    boss=cad.Solid.make_cone(radius*.24,radius*.20,boss_height,
                            cad.Plane(origin=(0,0,-boss_height),z_dir=(0,0,1)))
    boss=boss.cut(cyl(bore,boss_height+4,-boss_height-2))
    body=body.fuse(boss)
    wires=[]
    for fraction in (0,.25,.5,.75,1):
        x=root+(radius*1.025-root)*fraction
        chord=radius*(p['root_chord_ratio']+(p['tip_chord_ratio']-p['root_chord_ratio'])*fraction)
        beta=math.radians(p['root_pitch_deg']+p['tip_twist_deg']*fraction)
        sweep=radius*p['sweep_ratio']*fraction*fraction
        camber=radius*p['camber_ratio']
        points=[]
        for side,us in ((1,[i/10 for i in range(11)]),(-1,[i/10 for i in range(10,-1,-1)])):
            for u in us:
                tangent=(u-.5)*chord
                normal=4*camber*u*(1-u)+side*thickness/2*(.55+.45*math.sin(math.pi*u))
                y=tangent*math.cos(beta)-normal*math.sin(beta)+sweep
                z=tangent*math.sin(beta)+normal*math.cos(beta)
                points.append((x,y,z))
        wires.append(cad.Wire.make_polygon(points,close=True))
    blade=cad.Solid.make_loft(wires,ruled=False)
    clip=cyl(radius,diameter,-diameter/2)
    clipped=blade.intersect(clip)
    if isinstance(clipped,cad.ShapeList):
        if len(clipped)!=1:raise ValueError('Blade clipping did not yield one solid')
        blade=clipped[0]
    else:
        blade=clipped
    blades=[blade.rotate(cad.Axis.Z,i*360/blade_count) for i in range(blade_count)]
    rotor=body.fuse(*blades)
    if len(rotor.solids())!=1:
        raise ValueError('Rotor load path is disconnected in the study geometry')
    barrel_half=diameter*.18
    inner_radius=radius+gap
    wall=radius*p['shroud_wall_ratio']
    barrel=annulus(inner_radius+wall,inner_radius,2*barrel_half,-barrel_half)
    lip_height=diameter*.10
    lip_outer=cad.Solid.make_cone(inner_radius+wall,inner_radius*1.13+wall,lip_height,
                                 cad.Plane(origin=(0,0,barrel_half),z_dir=(0,0,1)))
    lip_inner=cad.Solid.make_cone(inner_radius,inner_radius*1.13,lip_height,
                                 cad.Plane(origin=(0,0,barrel_half),z_dir=(0,0,1)))
    shroud=barrel.fuse(lip_outer.cut(lip_inner))
    # Simplified right-angle gear case, orthogonal shafts and named interface flanges.
    shaft_radius=bore*.72
    gear_z=-diameter*.31
    case=cad.Solid.make_box(diameter*.24,diameter*.20,diameter*.20,
                            cad.Plane(origin=(-diameter*.12,-diameter*.10,gear_z-diameter*.10)))
    cavity=cad.Solid.make_box(diameter*.20,diameter*.16,diameter*.16,
                              cad.Plane(origin=(-diameter*.10,-diameter*.08,gear_z-diameter*.08)))
    case=case.cut(cavity).cut(cyl(shaft_radius*1.12,diameter*.40,gear_z-diameter*.15)).cut(
        cyl(shaft_radius*1.12,diameter*.50,origin=(-diameter*.15,0,gear_z),normal=(1,0,0)))
    shaft_z=cyl(shaft_radius,-gear_z,gear_z)
    shaft_x=cyl(shaft_radius,diameter*.35,origin=(0,0,gear_z),normal=(1,0,0))
    flange_z=annulus(radius*.17,shaft_radius*1.08,diameter*.015,gear_z+diameter*.10)
    flange_x=cyl(radius*.14,diameter*.015,origin=(diameter*.12,0,gear_z),normal=(1,0,0)).cut(
        cyl(shaft_radius*1.08,diameter*.02,origin=(diameter*.119,0,gear_z),normal=(1,0,0)))
    gears=cad.Compound([cad.Solid.make_cone(radius*.17,radius*.04,diameter*.05,
                                           cad.Plane(origin=(0,0,gear_z),z_dir=(0,0,1))),
                        cad.Solid.make_cone(radius*.17,radius*.04,diameter*.05,
                                           cad.Plane(origin=(0,0,gear_z),z_dir=(1,0,0)))])
    shapes={'rotor':rotor,'shroud':shroud,'gearcase':case,'vertical_shaft':shaft_z,
            'input_shaft':shaft_x,'rotor_interface_flange':flange_z,'drive_interface_flange':flange_x,
            'bevel_gear_envelopes':gears}
    report={'status':'analytic_study_geometry','geometry_origin':p['geometry_origin'],
            'configuration_id':p['configuration_id'],'units':'mm','up_axis':'Z',
            'rotor_axis':[0,0,1],'input_drive_axis':[1,0,0],
            'parameters':p,'build123d_version':cad.__version__,'components':{},
            'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'functional_interfaces_verified':False,'historical_identity_verified':False,
            'manufacturing_authorized':False,'physical_validation_established':False,
            'gear_teeth_bearings_seals_and_tolerances_resolved':False}
    for name,shape in shapes.items():
        valid=shape.is_valid if isinstance(shape.is_valid,bool) else shape.is_valid()
        if not valid or shape.volume<=0:raise ValueError('Invalid BRep: '+name)
        step=output/(name+'.step');stl=output/(name+'.stl')
        cad.export_step(shape,step);cad.export_stl(shape,stl,tolerance=.12,angular_tolerance=.18)
        reread=cad.import_step(step)
        reread_valid=reread.is_valid if isinstance(reread.is_valid,bool) else reread.is_valid()
        if not reread_valid or not math.isclose(reread.volume,shape.volume,rel_tol=1e-7):
            raise ValueError('STEP roundtrip failed: '+name)
        report['components'][name]={'brep_valid':bool(valid),'solids':len(shape.solids()),
                                   'volume_mm3':shape.volume,'faces':len(shape.faces()),
                                   'step_roundtrip_volume_relative_error':abs(reread.volume/shape.volume-1),
                                   'step_sha256':hashlib.sha256(step.read_bytes()).hexdigest(),
                                   'stl_sha256':hashlib.sha256(stl.read_bytes()).hexdigest()}
    cad.export_step(cad.Compound(list(shapes.values())),output/'assembly.step')
    report['elapsed_seconds']=time.monotonic()-start
    (output/'parameters.json').write_text(json.dumps(p,indent=2)+'\n')
    (output/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'components':len(shapes),'rotor_solids':len(rotor.solids()),
                      'rotor_volume_mm3':rotor.volume,'elapsed_seconds':report['elapsed_seconds']}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();build(json.loads(args.parameters.read_text()),args.output)
