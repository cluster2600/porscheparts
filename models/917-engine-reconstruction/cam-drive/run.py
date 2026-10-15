#!/usr/bin/env python3
"""Generate and inspect a new cam-drive study without altering frozen engine sources."""
import argparse
import copy
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
import cams
from engine_layout import beam, transform
import drive
from reconstruct import save, sha256, check_output
import numpy as np
import trimesh


def placed(mesh,yz,phase,x=0):
    result=mesh.copy();result.apply_transform(transform([x,*yz],[math.degrees(phase),0,0]));return result


def recipes(output):
    parts=[]
    for teeth in drive.TEETH:
        profile=cams.extrude(np.asarray(drive.profile(teeth)),-drive.WIDTH/2,drive.WIDTH/2)
        source=output/f'profile_{teeth}.stl';profile.export(source)
        root=drive.MODULE*teeth/2-1.25*drive.MODULE
        bore=9.25 if teeth!=48 else 5.25
        for rib in (None,2.5,3.5):
            name=f'drive_{teeth}_'+('dense' if rib is None else str(rib).replace('.','_'))
            cuts=[];adds=[]
            if rib is not None:
                cuts.append(beam([-8,0,0],[8,0,0],root-3))
                adds.append(beam([-6,0,0],[6,0,0],bore+4))
                for sector in range(6):
                    angle=sector*math.tau/6
                    for side in (-1,1):
                        start=np.array([0,(bore+2)*math.cos(angle),(bore+2)*math.sin(angle)])
                        bend=np.array([0,root*.63*math.cos(angle+side*.10),root*.63*math.sin(angle+side*.10)])
                        end=np.array([0,drive.web_tip_radius(root,rib)*math.cos(angle+side*.25),drive.web_tip_radius(root,rib)*math.sin(angle+side*.25)])
                        path=[(1-t)**2*start+2*t*(1-t)*bend+t*t*end for t in np.linspace(0,1,12)]
                        for a,b in zip(path,path[1:]):adds.append(beam(a,b,rib,True))
            parts.append({'id':name,'source_mesh':{'path':str(source),'sha256':sha256(source)},'add':[],
                          'subtract':cuts,'post_add':adds,'final_subtract':[beam([-12,0,0],[12,0,0],bore)],'intersect':[]})
    for name,length,radius in [('drive_idler_pin',20,5),('drive_cam_extension_intake',32,9),('drive_cam_extension_exhaust',56,9),('drive_crank_extension',56,9)]:
        parts.append({'id':name,'add':[beam([-length/2,0,0],[length/2,0,0],radius)],'subtract':[],'intersect':[]})
    save(output/'recipe.json',{'classification':'hypothetical_engine_components_not_manufacturing_geometry','parts':parts})


def mesh_motion(meshes):
    results=[]
    # Sample one complete tooth repetition per pair; analytic ratio and phase checks span the cycle in tests.
    for counts in ((27,48),(48,48),(48,54)):
        a,b=counts; distance=drive.MODULE*(a+b)/2
        print('Check tooth repetition '+str(counts),flush=True)
        maximum=0.;cases=48
        for i in range(cases):
            phase=math.tau*i/(a*cases)
            other=(b*math.pi-math.pi-a*phase)/b
            first=placed(meshes[a],[0,0],phase)
            second=placed(meshes[b],[distance,0],other)
            hit=study.contact(first,second)
            maximum=max(maximum,hit['volume_mm3'])
        results.append({'teeth':list(counts),'phases_checked':cases,'max_intersection_mm3':maximum,
                        'sampled_only':True,'passed':maximum==0})
    return results


def run(previous,output,dotnet):
    output=check_output(output);output.mkdir(parents=True,mode=0o700)
    lock=json.loads((previous/'delivery-manifest.json').read_text())
    expected=lock['files']
    def prior_file(relative):
        path=previous/relative
        if sha256(path)!=expected[relative]:raise ValueError('Previous delivery hash mismatch: '+relative)
        return path
    assembly=json.loads(prior_file('assembly.json').read_text())
    centres={r['family']:[r['matrix_mm'][i][3] for i in (1,2)] for r in assembly['instances'] if r['family'].startswith('camshaft_')}
    if len(centres)!=4:raise ValueError('Expected four cam axes')
    layout=drive.layout(centres);save(output/'layout.json',layout)
    recipes(output)
    source_paths=[HERE/'drive.py',HERE/'run.py',HERE.parent/'assembly/Program.cs',HERE.parent/'assembly/Engine.csproj',
                  HERE.parent/'head-bionic/cams.py',study.ROOT/'parts/picogk-catalog/common/Sdf.cs']
    sources={str(p.relative_to(study.ROOT)):sha256(p) for p in source_paths}
    ideal={n:study.prior.inspect(output/f'profile_{n}.stl',allow_exact_zero=True)[0] for n in drive.TEETH}
    ideal_checks=mesh_motion(ideal);save(output/'ideal-mesh-checks.json',ideal_checks)
    if not all(r['passed'] for r in ideal_checks):raise ValueError('Ideal gear profile rejected')
    study.command([dotnet,'build',HERE.parent/'assembly/Engine.csproj','-c','Release','-o',output/'app',
                   '-p:BaseIntermediateOutputPath='+str(output/'obj')+'/'],output/'build.log')
    grids={};audits={}
    for voxel in ('0.5','0.25'):
        directory=output/('native-'+voxel)
        study.command([dotnet,output/'app/Engine.dll',output/'recipe.json',sha256(output/'recipe.json'),voxel,directory],output/('native-'+voxel+'.log'))
        grids[voxel],audits[voxel]=study.audit_native(directory)
        if not all(r['passed'] for r in audits[voxel].values()):raise ValueError('Native topology rejected')
    fine=grids['0.25'];selected={};reductions={}
    for n in drive.TEETH:
        candidates={name:m for name,m in fine.items() if name.startswith(f'drive_{n}_') and not name.endswith('dense')}
        chosen=min(candidates,key=lambda k:candidates[k].volume);selected[n]=chosen
        reductions[n]={'selected':chosen,'volume_mm3':fine[chosen].volume,'dense_volume_mm3':fine[f'drive_{n}_dense'].volume,
                       'volume_reduction_fraction':1-fine[chosen].volume/fine[f'drive_{n}_dense'].volume}
    motion=mesh_motion({n:fine[name] for n,name in selected.items()})
    save(output/'gear-mesh-checks.json',motion)
    if not all(r['passed'] for r in motion):raise ValueError('Native gear meshing rejected; retain diagnostic outputs')
    # shortcut: tooth strength, root fillets, splines, bearings and housing interfaces remain unqualified; measure before mechanical release.
    rows=[copy.deepcopy(r) for r in assembly['instances'] if r['family'] not in {'cam_drive_gear','cam_drive_intermediate_shaft'}]
    crank_planes=set()
    def add(name,xyz,phase=0,**metadata):
        rows.append({'family':name,'matrix_mm':transform(xyz,[math.degrees(phase),0,0]).tolist(),**metadata})
    for train in layout['trains']:
        plane=train['plane_x_mm'];role=train['cam'].rsplit('_',1)[1]
        for i,(n,yz,phase,ratio) in enumerate(zip(train['teeth'],train['centres_yz_mm'],train['phase_rad'],train['speed_ratio_to_crank'])):
            if i==0 and plane in crank_planes:continue
            if i==0:crank_planes.add(plane)
            add(selected[n],[plane,*yz],phase,drive_target=train['cam'],speed_ratio_to_crank=ratio)
            if 0<i<len(train['teeth'])-1:add('drive_idler_pin',[plane,*yz],drive_target=train['cam'])
        add('drive_cam_extension_'+role,[(380+plane+12)/2,*train['centres_yz_mm'][-1]],drive_target=train['cam'])
    add('drive_crank_extension',[408,0,0])
    pieces=output/'pieces';pieces.mkdir();counts=Counter(r['family'] for r in rows);meshes={}
    for name,count in counts.items():
        path=pieces/(name+'.stl')
        if name in fine:meshes[name]=fine[name];meshes[name].export(path)
        else:shutil.copy2(prior_file('pieces/'+name+'.stl'),path);meshes[name]=trimesh.load_mesh(path,process=True)
    for i,r in enumerate(rows):r['instance_id']=f'part_{i:04d}'
    parts={name:assembly['parts'].get(name,{'id':name,'detail_level':'new_cam_drive_cold_hypothesis','actual_alloy':None,'manufacturing_process':None})|{'quantity':count} for name,count in counts.items()}
    save(output/'assembly.json',{'classification':'modern_bionic_4v_biturbo_cold_hypothesis_no_release','units':'mm_hypothetical','parts':parts,'instances':rows})
    scene=study.prior.export_scene(output,meshes,rows)
    report={'classification':'cam_drive_geometry_study_no_functional_release','prototype_count':len(parts),'instance_count':len(rows),
            'previous_manifest_sha256':sha256(previous/'delivery-manifest.json'),'native_audits':audits,'gears':reductions,
            'mesh_motion':motion,'all_sampled_gear_pairs_clear':all(r['passed'] for r in motion),'glb_roundtrip':scene,
            'source_hashes':sources,'ideal_mesh_motion':ideal_checks,
            'full_assembly_interference_checked':False,'bearing_supports_defined':False,'torsional_dynamics_checked':False,
            'actual_alloy':None,'manufacturing_process':None,'professional_review':None,
            'manufacturing_authorized':False,'engine_start_authorized':False}
    if sources!={str(p.relative_to(study.ROOT)):sha256(p) for p in source_paths}:raise ValueError('Executed sources changed')
    save(output/'report.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--previous',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--dotnet',required=True);a=parser.parse_args()
    print(json.dumps(run(a.previous.resolve(),a.output.resolve(),a.dotnet),indent=2))
