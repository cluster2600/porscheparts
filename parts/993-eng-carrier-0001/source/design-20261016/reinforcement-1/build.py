"""Widen existing curved ribs with a bounded C1 contour law on the frozen STEP.

The base carrier, its interfaces and its fixed envelope remain the reference.
Each new ribbon has positive overlap with an existing rib; no tangent plate or
smoothing of the imported surface is used. Width is measured parallel to Y.
"""
import argparse
import hashlib
import json
from math import comb
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def elevated(points):
    """Exact cubic-to-quintic Bezier degree elevation, with float arithmetic."""
    assert len(points) == 4
    return [tuple(sum(comb(3,j)*comb(2,i-j)/comb(5,i)*points[j][k]
                      for j in range(max(0,i-2),min(3,i)+1)) for k in range(2))
            for i in range(6)]


def width_controls(base, peak):
    assert peak >= base > 0
    control = base+(peak-base)/.625
    return [base,base,control,control,base,base]


def build(base_folder, output):
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import (Edge,Wire,Face,Box,Cylinder,Pos,extrude,
                          import_step,export_step,export_stl,export_brep)
    sys.path.insert(0,str(SOURCE.parent.parent/'bionic-20261011/correction-20261013'))
    from corrected_cad import precise_volume

    base_folder,output=Path(base_folder),Path(output)
    assert not output.exists(), 'Output must be fresh'
    plan=json.loads((SOURCE/'plan.json').read_text())
    assert sha(base_folder/'carrier.step')==plan['base_STEP_sha256']
    settings=json.loads((base_folder/'study.json').read_text())
    g=settings['geometry']; rib=g['central_back_ribs']
    assert rib=={'width_mm':2.8,'top_z_mm':30,'inboard_y_mm':5}
    assert g['thickness_mm']==8 and g['arm_shell']['depth_mm']==44
    assert plan['base_Y_width_mm']==rib['width_mm'] and plan['bottom_Z_mm']==4 and plan['top_Z_mm']==30
    assert settings['material']['density_tonne_mm3']*1000==plan['density_kg_mm3']
    assert plan['base_mass_kg']+plan['maximum_added_mass_upper_bound_kg']<plan['mass_ceiling_kg']

    output.mkdir(parents=True)
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (output/'construction-plan.json').write_bytes((SOURCE/'plan.json').read_bytes())
    body=import_step(base_folder/'carrier.step');original=body
    base_volume,_=precise_volume(body)
    # This roof is the unchanged cubic XZ rib envelope of the retained builder.
    roof_edges=[
      Edge.make_bezier((-105,-100,22),(-90,-100,22),(-80,-100,30),(-65,-100,30)),
      Edge.make_line((-65,-100,30),(65,-100,30)),
      Edge.make_bezier((65,-100,30),(80,-100,30),(90,-100,22),(105,-100,22)),
      Edge.make_line((105,-100,22),(105,-100,4)),
      Edge.make_line((105,-100,4),(-105,-100,4)),
      Edge.make_line((-105,-100,4),(-105,-100,22))]
    roof=extrude(Face(Wire(roof_edges)),amount=200,dir=(0,1,0))
    added=[]
    for name,controls,peak in (
      ('root',plan['root_centreline_XY_mm'],plan['root_peak_Y_width_mm']),
      ('central_curve',plan['central_centreline_XY_mm'],plan['central_curve_peak_Y_width_mm'])):
        centre=elevated(controls); widths=width_controls(plan['base_Y_width_mm'],peak)
        for sx in plan['mirror_X']:
            for sy in plan['mirror_Y']:
                lower=[(sx*x,sy*(y-w/2)) for (x,y),w in zip(centre,widths)]
                upper=[(sx*x,sy*(y+w/2)) for (x,y),w in zip(centre,widths)]
                edges=[Edge.make_bezier(*lower),Edge.make_line(lower[-1],upper[-1]),
                       Edge.make_bezier(*upper[::-1]),Edge.make_line(upper[0],lower[0])]
                face=Face(Wire(edges));assert face.is_valid and face.area>0
                ribbon=Pos(0,0,4)*extrude(face,amount=26,dir=(0,0,1))
                clipped=ribbon&roof
                before,_=precise_volume(body)
                body=body+clipped
                assert body.is_valid and len(body.solids())==1
                after,_=precise_volume(body)
                added.append({'region':name,'mirror_X':sx,'mirror_Y':sy,
                              'added_volume_mm3':after-before})
                print(json.dumps(added[-1]),flush=True)
    # Recut the unchanged tool corridors after reinforcement. The central
    # openings are also protected through the raised region against overhang.
    for x,y in g['central_bolt_centres_xy_mm']:
        body=body-Pos(x,y,29)*Cylinder(12.5,50)
    for x in g['central_opening_centres_x_mm']:
        body=body-Pos(x,0,29)*Cylinder(g['central_opening_radius_mm'],50)
    assert body.is_valid and len(body.solids())==1
    volume,error=precise_volume(body)
    removed=original-body;removed_volume=precise_volume(removed)[0] if removed is not None else 0
    # A contour reinforcement must not erode the frozen reference carrier.
    assert abs(removed_volume)<1e-5, removed_volume
    increment=volume-base_volume
    assert 0<increment<=plan['maximum_added_volume_upper_bound_mm3']+1e-4
    mass=volume*plan['density_kg_mm3'];assert mass<=plan['mass_ceiling_kg']
    pad=Pos(0,0,0)*Box(130,72,8)
    new_pad=body&pad;old_pad=original&pad
    pad_added=new_pad-old_pad;pad_removed=old_pad-new_pad
    pad_difference=sum(abs(precise_volume(s)[0]) if s is not None else 0 for s in (pad_added,pad_removed))
    assert pad_difference<1e-6,pad_difference
    export_brep(body,output/'native-body.brep')
    export_step(body,output/'carrier.step')
    export_stl(body,output/'carrier.stl',tolerance=.06,angular_tolerance=.10)
    reread=import_step(output/'carrier.step');read_volume,read_error=precise_volume(reread)
    assert reread.is_valid and len(reread.solids())==1
    assert abs(read_volume/volume-1)<1e-8
    box=reread.bounding_box();minimum=list(box.min);maximum=list(box.max)
    assert all(abs(a-b)<1e-6 for a,b in zip(minimum,[-296,-36.5,-22]))
    assert all(abs(a-b)<1e-6 for a,b in zip(maximum,[296,36.5,30]))
    settings['design_id']=plan['design_id']
    settings['reinforcement']=plan
    (output/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
    report={'design_id':plan['design_id'],'base_STEP_sha256':sha(base_folder/'carrier.step'),
      'generator_sha256':sha(__file__),'construction_plan_sha256':sha(SOURCE/'plan.json'),
      'volume_mm3':volume,'readback_volume_mm3':read_volume,'dense_reference_mass_kg':mass,
      'additional_mass_kg':increment*plan['density_kg_mm3'],'additional_volume_mm3':increment,
      'declared_mass_ceiling_kg':plan['mass_ceiling_kg'],'mass_ceiling_pass':mass<=plan['mass_ceiling_kg'],
      'STEP_readback_relative_volume_difference':read_volume/volume-1,
      'estimated_relative_integration_errors':[error,read_error],
      'removed_from_reference_mm3':removed_volume,'central_pad_symmetric_difference_mm3':pad_difference,
      'CAD_valid':True,'solid_count':1,'bounds_mm':[minimum,maximum],
      'geometry_sha256':{n:sha(output/n) for n in ('carrier.step','carrier.stl')},
      'regional_incremental_volumes':added,'mechanical_objectives_evaluated':False}
    (output/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_folder',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();build(args.base_folder,args.output)
