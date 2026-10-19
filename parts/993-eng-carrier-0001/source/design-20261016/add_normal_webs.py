"""Add true-offset webs, window ligaments and secondary-bore sleeves to the frozen thick-skin body."""
import argparse
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE.parent / 'bionic-20261011/correction-20261013'))
from corrected_cad import precise_volume, sha
sys.path.insert(0, str(SOURCE.parent / 'bionic-20261011'))
from cad import arm_envelope


def outer_face():
    from build123d import Edge, Wire, Face
    edges = [Edge.make_bezier((-278,-22),(-220,-20),(-100,-36),(-65,-36)),
             Edge.make_line((-65,-36),(65,-36)),
             Edge.make_bezier((65,-36),(100,-36),(220,-20),(278,-22)),
             Edge.make_line((278,-22),(278,22)),
             Edge.make_bezier((278,22),(220,20),(100,36),(65,36)),
             Edge.make_line((65,36),(-65,36)),
             Edge.make_bezier((-65,36),(-100,36),(-220,20),(-278,22)),
             Edge.make_line((-278,22),(-278,-22))]
    return Face(Wire(edges))


def build(folder, output, plan_path=SOURCE/'normal-webs-plan.json', identity_receipt=None):
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import Edge, Wire, Face, Polygon, Pos, Cylinder, Box
    from build123d import extrude, fillet, import_step, export_step, export_stl, export_brep
    folder, output = Path(folder), Path(output)
    plan_path = Path(plan_path)
    plan = json.loads(plan_path.read_text())
    if identity_receipt is None:
        assert sha(folder/'carrier.step') == plan['baseline_step_sha256']
    else:
        receipt=json.loads(Path(identity_receipt).read_text())
        assert receipt['geometry_sha256']['carrier.step']==sha(folder/'carrier.step')
        expected=json.loads((SOURCE/'thick-skins.json').read_text())
        actual=json.loads((folder/'study.json').read_text())
        for field in ('geometry','material','load_cases'):
            assert expected[field]==actual[field]
        assert abs(receipt['volume_mm3']/plan['baseline_volume_mm3']-1)<1e-8
    output.mkdir(parents=True, exist_ok=False)
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (output/'construction-plan.json').write_bytes(plan_path.read_bytes())
    settings = json.loads((folder/'study.json').read_text())
    settings['design_id'] = plan['design_id']
    settings['revision_reason'] = plan['reason']
    settings['design_constraints']['absolute_mass_ceiling_kg'] = 1.3
    settings['geometry']['local_reinforcement'] = plan['generators']
    body = import_step(folder/'carrier.step')
    original_volume, _ = precise_volume(body)
    if identity_receipt is not None:
        assert abs(original_volume/plan['baseline_volume_mm3']-1)<1e-8
    g = settings['geometry']; depth = g['arm_shell']['depth_mm']; pad = g['thickness_mm']
    envelope = arm_envelope(depth, pad)
    outer = outer_face()
    stock = Pos(0,0,-depth/2)*extrude(outer,amount=depth)
    shell = stock & envelope
    web = g['arm_shell']['web_mm']
    reference_cap=plan['generators'].get('window_rim_reference_cap_mm',g['arm_shell']['cap_mm'])
    for side, core in zip((-1,1), arm_envelope(depth-2*reference_cap,0,end=268)):
        inner = [Edge.make_bezier((side*65,-36+web),(side*100,-36+web),(side*220,-20+web),(side*278,-22+web)),
                 Edge.make_line((side*278,-22+web),(side*278,22-web)),
                 Edge.make_bezier((side*278,22-web),(side*220,20-web),(side*100,36-web),(side*65,36-web)),
                 Edge.make_line((side*65,36-web),(side*65,-36+web))]
        hollow = Pos(0,0,-depth)*extrude(Face(Wire(inner)),amount=2*depth,dir=(0,0,1))
        shell = shell - (hollow & core)
    # Positive distance is outward for this closed wire; assert the inset area.
    inset = Face(outer.outer_wire().offset_2d(-plan['generators']['outer_web_true_XY_inward_offset_mm']))
    assert 0 < inset.area < outer.area
    outer_overlap=plan['generators'].get('outer_web_ring_outer_overlap_inset_mm',0)
    ring_outer=Face(outer.outer_wire().offset_2d(-outer_overlap)) if outer_overlap else outer
    ring = Pos(0,0,-depth/2)*extrude(ring_outer-inset,amount=depth)
    ring = ring & envelope
    # Exclude the study pad; the unchanged original material remains in that region.
    arms = Pos(171.5,0,0)*Box(213,200,100) + Pos(-171.5,0,0)*Box(213,200,100)
    ring = ring & arms
    additions = []
    def add(label, material):
        nonlocal body
        before, _ = precise_volume(body)
        body = body + material
        after, _ = precise_volume(body)
        additions.append({'generator':label,'added_volume_mm3':after-before})
    add('true_normal_outer_webs', ring)
    windows = [([(78,-25),(146,-20),(80,24)],6),
               ([(105,24),(217,18),(156,-22)],7),
               ([(172,-20),(255,-14),(243,15)],5)]
    # Window three retains the earlier end-window scale 0.4, inside its exact mask.
    for side in (-1,1):
        for index,(points,radius) in enumerate(windows):
            scale=g['window_scale']
            cx,cy=[sum(p[i] for p in points)/len(points) for i in (0,1)]
            vertices=[(side*(cx+scale*(x-cx)),cy+scale*(y-cy)) for x,y in points]
            face=Polygon(*vertices,align=None)
            face=fillet(face.vertices(),radius*scale)
            face=face.faces()[0]
            inset=Face(face.outer_wire().offset_2d(-plan['generators']['rounded_window_inward_offset_mm']))
            assert 0 < inset.area < face.area
            rim=Pos(0,0,-depth)*extrude(face-inset,amount=2*depth,dir=(0,0,1))
            add(f'window_{side}_{index}',rim & shell & arms)
    for x,y in plan['generators']['secondary_centres_xy_mm']:
        boss=Pos(x,y,0)*Cylinder(plan['generators']['secondary_boss_radius_mm'],depth)
        add(f'secondary_sleeve_{x}_{y}',boss)
        body=body-Pos(x,y,0)*Cylinder(plan['generators']['secondary_bore_radius_mm'],2*depth)
    assert body.is_valid and len(body.solids())==1
    volume,error=precise_volume(body)
    (output/'native-construction.json').write_text(json.dumps({'volume_mm3':volume,
        'additions':additions,'native_valid':body.is_valid,'native_solids':len(body.solids()),
        'STEP_export_write_pcurves':False,'OCP_default_thread_pool_size':1},indent=2)+'\n')
    export_brep(body,output/'native-body.brep')
    # The full central-pad comparator and end interfaces are checked independently.
    # OCC's STEP pcurve transfer intersected two offset loops. Recompute pcurves
    # from the retained 3D curves on import, then enforce the same solid/volume gate.
    export_step(body,output/'carrier.step',write_pcurves=False)
    export_stl(body,output/'carrier.stl',tolerance=.06,angular_tolerance=.10)
    reread=import_step(output/'carrier.step')
    read_volume,read_error=precise_volume(reread)
    assert reread.is_valid and len(reread.solids())==1
    assert abs(read_volume/volume-1)<1e-8
    mass=volume*settings['material']['density_tonne_mm3']*1000
    assert mass<=plan['criteria']['nominal_mass_kg_max']
    box=reread.bounding_box()
    assert box.min.X>=-296.000001 and box.max.X<=296.000001
    assert box.min.Y>=-36.500001 and box.max.Y<=36.500001
    assert box.min.Z>=-22.000001 and box.max.Z<=30.000001
    (output/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
    integration={'adaptive_original_mm3':volume,'adaptive_readback_mm3':read_volume,
                 'estimated_relative_integration_errors':[error,read_error],
                 'adaptive_relative_difference':read_volume/volume-1}
    (output/'volume-integration.json').write_text(json.dumps(integration,indent=2)+'\n')
    report={'design_id':settings['design_id'],'volume_mm3':volume,'dense_reference_mass_kg':mass,
            'original_mass_ceiling_kg':1.2,'original_mass_ceiling_pass':mass<=1.2,
            'declared_mass_ceiling_kg':1.3,'mass_ceiling_pass':mass<=1.3,
            'CAD_valid':True,'solid_count':1,'STEP_readback_volume_match':True,
            'baseline_STEP_sha256':sha(folder/'carrier.step'),'construction_plan_sha256':sha(plan_path),
            'generator_sha256':sha(__file__),'inherited_generator_sha256':sha(SOURCE.parent/'bionic-20261011/cad.py'),
            'geometry_sha256':{n:sha(output/n) for n in ('carrier.step','carrier.stl')},
            'additions':additions,'net_added_volume_mm3':volume-original_volume,
            'bounds_mm':[list(box.min),list(box.max)],'manufacturing_authorized':False}
    (output/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--plan',type=Path,default=SOURCE/'normal-webs-plan.json')
    parser.add_argument('--identity-receipt',type=Path)
    args=parser.parse_args();build(args.folder,args.output,args.plan,args.identity_receipt)
