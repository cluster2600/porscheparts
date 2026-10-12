#!/usr/bin/env python3
"""Build real native detail around the frozen flat-12; no functional release."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
from engine_layout import beam,box,transform,module
from reconstruct import check_output,save,sha256
import numpy as np
import trimesh
import design
from detail_audit import audit_native,verified_cache


def sources():
    files=[HERE/'Program.cs',HERE/'Detail.csproj',HERE/'Route.cs',HERE/'Route.csproj',HERE/'Housing.cs',HERE/'Housing.csproj',HERE/'design.py',HERE/'run.py',HERE/'verify.py',HERE/'detail_audit.py',
           HERE.parent/'assembly/Program.cs',HERE.parent/'assembly/Engine.csproj',
           study.ROOT/'parts/picogk-catalog/common/Sdf.cs',study.ROOT/'parts/picogk-catalog/engine/EngineSdf.cs',
           study.ROOT/'twins/m64-cylinder-head/source/picogk-local-junction/exact_zero_countertrial.py',
           study.ROOT/'twins/m64-cylinder-head/source/picogk-local-junction/audit_mesh.py']
    return {str(p.relative_to(study.ROOT)):sha256(p) for p in files}


def clear_housing(output,cfg,dotnet):
    meshes={};levels={}
    study.command([dotnet,'build',HERE/'Housing.csproj','-c','Release','-o',output/'housing-app','-p:BaseIntermediateOutputPath='+str(output/'housing-obj')+'/'],output/'housing-build.log')
    for grid in (1,.5):
        source=output/f'native-{grid:g}'/'drive_housing.vdb'
        recipe=output/f'housing-clearance-vdb-{grid:g}.json';dest=output/f'housing-clearance-vdb-{grid:g}'
        save(recipe,{'classification':'housing_rotation_clearance_no_physical_release','manufacturing_authorized':False,
                     'source_vdb':{'path':str(source.resolve()),'sha256':sha256(source)},'gear_envelopes':cfg['gear_envelopes']})
        study.command([dotnet,output/'housing-app/Housing.dll',recipe,sha256(recipe),grid,dest],output/f'housing-clearance-vdb-{grid:g}.log')
        accepted,audits=audit_native(dest)
        if not all(r['passed'] for r in audits.values()):raise ValueError('Housing rotation clearance topology rejected')
        levels[str(grid)]=audits
        if grid==.5:meshes.update(accepted)
    return meshes,levels


def run(previous,output,dotnet,native_from=None):
    output=check_output(output);output.mkdir(parents=True,mode=0o700);executed=sources();save(output/'execution-sources.json',executed)
    lock=json.loads((previous/'delivery-manifest.json').read_text())['files']
    def prior(name):
        p=previous/name
        if sha256(p)!=lock[name]:raise ValueError('Prior delivery changed: '+name)
        return p
    old=json.loads(prior('assembly.json').read_text());drive=json.loads(prior('layout.json').read_text())
    gears=[]
    for r in old['instances']:
        if r['family'] in {'drive_27_2_5','drive_48_2_5','drive_54_2_5'}:
            n=int(r['family'].split('_')[1]);m=r['matrix_mm'];gears.append([m[0][3],m[1][3],m[2][3],1.5*n/2+1.5])
    if len(gears)!=26:raise ValueError('Wrong cam-drive baseline')
    # Axes are taken from the previous candidate, not treated as measured Porsche interfaces.
    positive=next(r for r in old['instances'] if r['family']=='camshaft_positive_intake')
    cam_z=positive['matrix_mm'][1][3]-211.25;cam_y=positive['matrix_mm'][2][3]
    cfg={'classification':'917_mechanical_detail_geometry_hypothesis','gear_envelopes':gears,
         'cover_bolts_yz':design.cover_bolts(gears),'trains':drive['trains'],
         'case_sources':[{'path':str(prior('pieces/'+n+'.stl')),'sha256':lock['pieces/'+n+'.stl']} for n in ('crankcase_negative','crankcase_positive')],
         'cam_local_z_mm':cam_z,'cam_local_y_mm':cam_y,'valve_cover_top_mm':cam_z+35,
         'actual_alloy':None,'measured_interfaces':None,'manufacturing_authorized':False,'engine_start_authorized':False}
    save(output/'config.json',cfg)
    levels={};native_origin=None
    if native_from is not None:
        origin=json.loads((native_from/'execution-sources.json').read_text())
        for path in [HERE/'Program.cs',study.ROOT/'parts/picogk-catalog/common/Sdf.cs',study.ROOT/'parts/picogk-catalog/engine/EngineSdf.cs']:
            if sha256(path)!=origin[str(path.relative_to(study.ROOT))]:raise ValueError('Cached native generation source changed')
        if sha256(native_from/'config.json')!=sha256(output/'config.json'):raise ValueError('Cached native configuration differs')
        native_origin={'generation_sources':origin,'config_sha256':sha256(native_from/'config.json')}
    else:
        study.command([dotnet,'build',HERE/'Detail.csproj','-c','Release','-o',output/'app','-p:BaseIntermediateOutputPath='+str(output/'obj')+'/'],output/'build.log')
    for grid in (1,.5):
        native=output/f'native-{grid:g}'
        if native_from is not None:
            shutil.copytree(native_from/f'native-{grid:g}',native)
            meshes,audits=verified_cache(native)
        else:
            study.command([dotnet,output/'app/Detail.dll',output/'config.json',sha256(output/'config.json'),grid,native],output/f'native-{grid:g}.log')
            meshes,audits=audit_native(native)
        levels[str(grid)]=audits
        if not all(r['passed'] for r in audits.values()):raise ValueError('Native detail topology rejected')
    recipes=[];branch_parts=[]
    for bank in (-1,1):
        name='intake_'+('negative' if bank<0 else 'positive')
        bounds=trimesh.load_mesh(prior('pieces/'+name+'.stl'),process=False).bounds
        low=bounds[0]-4;high=bounds[1]+4;high[0]=375
        recipes.append({'id':name,'source_mesh':{'path':str(prior('pieces/'+name+'.stl')),'sha256':lock['pieces/'+name+'.stl']},
                        'add':[],'subtract':[],'intersect':[box((low+high)/2,(high-low)/2)], 'post_add':[], 'final_subtract':[]})
        # The existing executor intersects after post_add: split clipping and pipe attachment into two native steps.
        # Two roots bifurcate to the four nominal exchanger mounting ears.
        adds=[]
        for x in (-40,120):
            for y in (258,362):
                p=design.curve([x,bank*65,64],[x,bank*240,110],[x,bank*y,264])
                for a,b in zip(p,p[1:]):adds.append(beam(a,b,6,True))
        adds.extend([beam([-40,bank*258,264],[120,bank*258,264],6),beam([-40,bank*362,264],[120,bank*362,264],6)])
        branch_parts.append({'id':'intercooler_bionic_bracket_'+('negative' if bank<0 else 'positive'),'branches':adds})
    def native_recipe(parts,name):
        path=output/(name+'.json');save(path,{'classification':'hypothetical_engine_components_not_manufacturing_geometry','parts':parts})
        dest=output/name
        study.command([dotnet,output/'engine-app/Engine.dll',path,sha256(path),'.5',dest],output/(name+'.log'))
        result,audits=audit_native(dest)
        if not all(r['passed'] for r in audits.values()):raise ValueError('Routed native detail rejected')
        return result,audits
    study.command([dotnet,'build',HERE.parent/'assembly/Engine.csproj','-c','Release','-o',output/'engine-app','-p:BaseIntermediateOutputPath='+str(output/'engine-obj')+'/'],output/'route-build.log')
    housing,housing_audits=clear_housing(output,cfg,dotnet);meshes.update(housing)
    routed,route_audits=native_recipe(recipes,'route-clip')
    route_parts=branch_parts
    for bank in (-1,1):
        suffix='negative' if bank<0 else 'positive';name='intake_'+suffix
        path=output/'route-clip'/(name+'.stl')
        route_parts.append({'id':name,'points':design.return_path(bank),'source_mesh':{'path':str(path),'sha256':sha256(path)}})
        points=design.charge_path(bank)
        route_parts.append({'id':'charge_pipe_'+suffix,'points':points,
                            'outer_radii':[18,18]+[25]*(len(points)-2),
                            'inner_radii':[15.5,15.5]+[22.5]*(len(points)-2)})
    recipe=output/'route-pipes.json';save(recipe,{'classification':'hypothetical_pipe_routes_no_physical_release','manufacturing_authorized':False,'parts':route_parts})
    study.command([dotnet,'build',HERE/'Route.csproj','-c','Release','-o',output/'route-app','-p:BaseIntermediateOutputPath='+str(output/'route-obj')+'/'],output/'pipe-build.log')
    study.command([dotnet,output/'route-app/Route.dll',recipe,sha256(recipe),'.5',output/'route-final'],output/'route-final.log')
    intake,intake_audits=audit_native(output/'route-final')
    if not all(r['passed'] for r in intake_audits.values()):raise ValueError('Native pipe topology rejected')
    routed.update(intake);meshes.update(routed)
    removed={'intercooler','oil_cooler','drive_idler_pin'}
    rows=[copy.deepcopy(r) for r in old['instances'] if r['family'] not in removed]
    def add(name,pos=(0,0,0),rotation=(0,0,0),**metadata):rows.append({'family':name,'matrix_mm':transform(pos,rotation).tolist(),**metadata})
    for r in rows:
        name=r['family']
        if name=='alternator':r['matrix_mm']=transform([-185,0,270]).tolist()
        if name=='ecu':r['matrix_mm']=transform([-270,0,135]).tolist()
        if name=='starter_motor':r['matrix_mm']=transform([420,-100,-125],[0,90,0]).tolist()
        if name=='throttle':r['matrix_mm']=transform([208,r['bank']*310,295],[0,90,0]).tolist()
        if name=='oil_pump_cover':r['matrix_mm'][2][3]-=3
    for bank in (-1,1):
        for name,rotation in [('intercooler_core',(0,0,0)),('intercooler_tank',(0,0,0)),('intercooler_tank',(0,0,180))]:
            add(name,[40,bank*310,295],rotation,bank=bank)
        add('charge_pipe_'+('negative' if bank<0 else 'positive'),bank=bank)
        add('intercooler_bionic_bracket_'+('negative' if bank<0 else 'positive'),bank=bank)
    for name,rotation in [('oil_cooler_core',(0,0,0)),('oil_cooler_tank',(0,0,0)),('oil_cooler_tank',(0,0,180))]:add(name,[-520,0,-235],rotation)
    for name in ['drive_housing','drive_cover','drive_bionic_frame','alternator_bionic_bracket']:add(name)
    for q in cfg['cover_bolts_yz']:add('drive_cover_bolt',[443,q[0],q[1]])
    for train in drive['trains']:
        role=train['cam'].rsplit('_',1)[-1]
        for y,z in train['centres_yz_mm'][1:-1]:add('drive_pin_'+role,[404 if role=='intake' else 420,y,z])
    counts=Counter(r['family'] for r in rows);pieces=output/'pieces';pieces.mkdir();prototypes={}
    for name,count in counts.items():
        if name in meshes:prototypes[name]=meshes[name];meshes[name].export(pieces/(name+'.stl'))
        else:
            p=prior('pieces/'+name+'.stl');shutil.copy2(p,pieces/(name+'.stl'));prototypes[name]=trimesh.load_mesh(p,process=True)
    for i,r in enumerate(rows):r['instance_id']=f'part_{i:04d}'
    parts={name:{**old['parts'].get(name,{'id':name,'actual_alloy':None,'manufacturing_process':None}),
                 'quantity':count,'detail_level':'new_native_mechanical_detail_hypothesis' if name in meshes else old['parts'][name]['detail_level']} for name,count in counts.items()}
    save(output/'assembly.json',{'classification':'917_mechanical_detail_cold_hypothesis_no_release','units':'mm_hypothetical','parts':parts,'instances':rows})
    scene=study.prior.export_scene(output,prototypes,rows)
    checked=module('mechanical_detail_verify',HERE/'verify.py').run(output,prototypes,rows,meshes)
    if executed!=sources():raise ValueError('Executed sources changed')
    report={'classification':'917_mechanical_detail_geometry_no_physical_release','source_hashes':executed,'native_audits':levels,
            'route_audits':route_audits,'intake_audits':intake_audits,'housing_clearance_audits':housing_audits,'verification':checked,'glb_roundtrip':scene,
            'definitions':len(parts),'assembly_occurrences':len(rows),'removed_box_families':['alternator','starter_motor','ecu','oil_cooler','intercooler','throttle','oil_pump_body','oil_pump_cover'],
            'native_generation_origin':native_origin,'prior_manifest_sha256':sha256(previous/'delivery-manifest.json'),'actual_alloy':None,'measured_interfaces':None,
            'full_assembly_interference_checked':False,'thermal_or_fatigue_validated':False,'professional_review':None,
            'manufacturing_authorized':False,'engine_start_authorized':False}
    save(output/'report.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--previous',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--dotnet',required=True);p.add_argument('--native-from',type=Path);a=p.parse_args()
    print(json.dumps(run(a.previous.resolve(),a.output.resolve(),a.dotnet,a.native_from.resolve() if a.native_from else None),indent=2))
