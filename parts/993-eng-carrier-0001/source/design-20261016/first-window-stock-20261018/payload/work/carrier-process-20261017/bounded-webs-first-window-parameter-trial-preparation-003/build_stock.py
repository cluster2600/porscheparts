"""Build the predeclared slope-bounded walls and inset-window carrier, then sleeve secondary bores."""
import argparse
import json
from pathlib import Path
import sys

SOURCE = Path('/Users/maxime/.codex/worktrees/993-carrier-revalidation/3dprinting993/parts/993-eng-carrier-0001/source/design-20261016')
sys.path.insert(0,str(SOURCE.parent/'bionic-20261011/correction-20261013'))
import corrected_cad


def build(output):
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import Cylinder,Pos,import_step,export_step,export_stl,export_brep
    output=Path(output)
    plan_path=SOURCE/'bounded-webs-plan.json'; plan=json.loads(plan_path.read_text())
    settings=json.loads((SOURCE/'bounded-webs.json').read_text())
    # The immutable correction builder exposes BASE only to select its CAD module.
    corrected_cad.BASE=Path(__file__).resolve().parent/'normal-builder'
    built=output.parent/(output.name+'-without-sleeves')
    corrected_cad.build(settings,built)
    output.mkdir(parents=True,exist_ok=False)
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (output/'construction-plan.json').write_bytes(plan_path.read_bytes())
    body=import_step(built/'carrier.step')
    settings=json.loads((built/'study.json').read_text());settings['design_id']=plan['design_id']
    for x,y in plan['generators']['secondary_centres_xy_mm']:
        body=body+Pos(x,y,0)*Cylinder(plan['generators']['secondary_boss_radius_mm'],44)
        body=body-Pos(x,y,0)*Cylinder(plan['generators']['secondary_bore_radius_mm'],88)
    assert body.is_valid and len(body.solids())==1
    volume,error=corrected_cad.precise_volume(body)
    (output/'native-construction.json').write_text(json.dumps({'volume_mm3':volume,'native_valid':True,'native_solid_count':1},indent=2)+'\n')
    export_brep(body,output/'native-body.brep')
    export_step(body,output/'carrier.step')
    export_stl(body,output/'carrier.stl',tolerance=.06,angular_tolerance=.10)
    reread=import_step(output/'carrier.step');read_volume,read_error=corrected_cad.precise_volume(reread)
    assert reread.is_valid and len(reread.solids())==1
    assert abs(read_volume/volume-1)<1e-8
    mass=volume*settings['material']['density_tonne_mm3']*1000
    assert mass<=1.3
    box=reread.bounding_box()
    assert box.min.X>=-296.000001 and box.max.X<=296.000001
    assert box.min.Y>=-36.500001 and box.max.Y<=36.500001
    assert box.min.Z>=-22.000001 and box.max.Z<=30.000001
    (output/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
    (output/'volume-integration.json').write_text(json.dumps({'adaptive_original_mm3':volume,'adaptive_readback_mm3':read_volume,
        'estimated_relative_integration_errors':[error,read_error],'adaptive_relative_difference':read_volume/volume-1},indent=2)+'\n')
    report={'design_id':settings['design_id'],'volume_mm3':volume,'dense_reference_mass_kg':mass,'mass_ceiling_pass':mass<=1.3,
        'original_mass_ceiling_kg':1.2,'original_mass_ceiling_pass':mass<=1.2,'declared_mass_ceiling_kg':1.3,
        'CAD_valid':True,'solid_count':1,'STEP_readback_volume_match':True,
        'construction_plan_sha256':corrected_cad.sha(plan_path),'generator_sha256':corrected_cad.sha(__file__),
        'source_dependencies_sha256':{str(p):corrected_cad.sha(p) for p in
            (Path(__file__).resolve().parent/'normal-builder/cad.py',SOURCE.parent/'bionic-20261011/cad.py',SOURCE.parent/'bionic-20261011/correction-20261013/corrected_cad.py')},
        'geometry_sha256':{name:corrected_cad.sha(output/name) for name in ('carrier.step','carrier.stl')},
        'bounds_mm':[list(box.min),list(box.max)],'manufacturing_authorized':False}
    (output/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    build(parser.parse_args().output)
