#!/usr/bin/env python3
"""Build native 4V candidates and integrate the selected hypothesis into the private flat-12."""
import argparse
from collections import Counter
import copy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'assembly'))
import optimize
import cams
from engine_layout import beam, box, head_transform
from reconstruct import check_output, save, sha256
spec=importlib.util.spec_from_file_location('prior_assembly',HERE.parent/'assembly/run.py')
prior=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
from build_f37_printable_head_mesh import intersection_volume, boolean_difference


def command(args,log):
    with log.open('x') as stream:
        subprocess.run(list(map(str,args)),stdout=stream,stderr=subprocess.STDOUT,check=True)


def prepare(output):
    layout,packing=optimize.packing()
    timing,campaign=optimize.timing(layout)
    lengths={44.0}
    for cycle in cams.cycles():
        for role in ('intake','exhaust'):
            lift=cams.cam_law(role,timing['roles'][role]).valve_lift(-math.radians(cycle['overlap_tdc_deg'])).item()*1000
            lengths.add(round(44-lift,6))
    config={'classification':'917_bionic_head_design_candidate_no_physical_release',
            'intake_diameter_mm':layout['intake_mm'],'exhaust_diameter_mm':layout['exhaust_mm'],
            'pair_half_pitch_mm':layout['x_mm'],'row_offset_mm':layout['y_mm'],
            'face_z_mm':timing['face_z_mm'],'roof_height_mm':10,'port_wall_mm':3,
            'spring_lengths_mm':sorted(lengths,reverse=True),'manufacturing_authorized':False,
            'engine_start_authorized':False,'actual_alloy':None,'manufacturing_process':None,'measured_interfaces':None}
    search={'packing':layout,'packing_cases':packing,'timing':timing,'timing_cases':campaign,'cycles':cams.cycles()}
    save(output/'config.json',config);save(output/'search.json',search)
    return config,search


def audit_native(directory):
    receipt=json.loads((directory/'receipt.json').read_text())
    audits,meshes={},{}
    records=receipt['parts']
    if isinstance(records,list):records={r['id']:r for r in records}
    for name,row in records.items():
        print('Audit '+directory.name+'/'+name,flush=True)
        for ext in ('stl','vdb'):
            if sha256(directory/(name+'.'+ext))!=row[ext+'_sha256']:
                raise ValueError('Native output changed: '+name)
        try:
            mesh,audit=prior.inspect(directory/(name+'.stl'),allow_exact_zero=True)
            if not audit['passed']:raise ValueError('Non-single closed surface')
            meshes[name]=mesh
        except ValueError as error:
            audit={'passed':False,'error':str(error)}
        audits[name]=audit
    save(directory/'independent-audit.json',audits)
    return meshes,audits


def contact(a,b):
    volume,method,witness=intersection_volume(a,b)
    if not math.isfinite(volume) or volume<0:raise ValueError('Boolean contact failed: '+method)
    return {'volume_mm3':volume,'method':'Manifold_float_triangle_boolean_not_exact_BRep','witness':witness}


def axis_pose(center,axis,distance):
    import numpy as np
    import trimesh
    matrix=trimesh.geometry.align_vectors([0,0,1],axis)
    matrix[:3,3]=np.asarray(center)+np.asarray(axis)*distance
    return matrix


def local_components(config,search,cycle):
    import numpy as np
    alpha=math.radians(8)
    rows=[]
    identity=np.eye(4)
    rows.extend((name,identity.copy()) for name in ('individual_head','rocker_carrier','valve_cover','cam_cap_bolted','head_gasket','spark_plug'))
    cam_s=164.1;cam_z=config['face_z_mm']+cam_s*math.cos(alpha)
    cam_y=config['row_offset_mm']+cam_s*math.sin(alpha)
    for sign in (-1,1):
        for side in (-1,1):
            m=identity.copy();m[:3,3]=[side*8,sign*cam_y+side*12,cam_z]
            rows.append(('cam_cap_bolt',m))
    for i in range(4):
        role='intake' if i<2 else 'exhaust';sign=1 if i<2 else -1
        n=np.array([0,sign*math.sin(alpha),math.cos(alpha)])
        c=np.array([(-1 if i%2==0 else 1)*config['pair_half_pitch_mm'],sign*config['row_offset_mm'],config['face_z_mm']])
        law=cams.cam_law(role,search['timing']['roles'][role]);phi=-math.radians(cycle['overlap_tdc_deg'])
        lift=law.valve_lift(phi).item()*1000;cam_lift=law.cam_derivatives(phi).item()*1000
        vi=i*3+1
        move=identity.copy();move[:3,3]=-n*lift
        rows.extend([(f'head_component_{vi:02d}',move),(f'head_component_{vi+1:02d}',identity.copy()),(f'head_component_{vi+2:02d}',identity.copy())])
        spring_index=min(range(len(config['spring_lengths_mm'])),key=lambda k:abs(config['spring_lengths_mm'][k]-(44-lift)))
        if abs(config['spring_lengths_mm'][spring_index]-(44-lift))>1e-5:raise ValueError('Missing unscaled spring height')
        for name,s in [('valve_stem_seal',61),('lower_spring_seat',61),
                       (f'outer_valve_spring_{spring_index}',62),(f'inner_valve_spring_{spring_index}',62),
                       ('upper_spring_retainer',108-lift),('valve_shim',116-lift),('rocker',118.1-cam_lift)]:
            rows.append((name,axis_pose(c,n,s)))
        for half in (0,1):
            m=axis_pose(c,n,109-lift)
            if half:m[:3,:3]=m[:3,:3]@np.diag([-1,-1,1])
            rows.append(('valve_keeper_half',m))
        for name in ('cam_roller','cam_roller_pin'):rows.append((name,axis_pose(c,n,136.1-cam_lift)))
    for sx in (-1,1):
        for sy in (-1,1):
            rows.append(('head_stud',axis_pose([sx*39,sy*39,0],[0,0,1],-44.5)))
            rows.append(('head_nut',axis_pose([sx*39,sy*39,0],[0,0,1],36)))
    for sign in (-1,1):
        a=math.radians(sign*165)
        rows.append(('location_dowel',axis_pose([48*math.cos(a),48*math.sin(a),0],[0,0,1],0)))
    return rows


def integrate(output,previous,native,config,search,dotnet,native_meshes,audits):
    import numpy as np
    import trimesh
    old=json.loads((previous/'assembly.json').read_text())
    lock=json.loads((previous/'delivery-manifest.json').read_text())['files']
    execution=json.loads((HERE.parent/'assembly/execution-20261011.json').read_text())
    if sha256(previous/'report.json')!=execution['private_report_sha256']:
        raise ValueError('Previous release differs from pinned execution')
    if sha256(previous/'assembly.json')!=lock['assembly.json']:raise ValueError('Prior placement changed')
    pieces=output/'pieces';pieces.mkdir()
    replace={'individual_head','rocker_carrier','valve_cover','head_gasket','head_stud','head_nut','location_dowel',
             'spark_plug','valve_stem_seal','lower_spring_seat','outer_valve_spring','inner_valve_spring',
             'upper_spring_retainer','valve_keeper_pair','valve_shim','rocker','rocker_shaft','camshaft','ignition_coil'}
    replace.update(f'head_component_{i:02d}' for i in range(1,13))
    required={name for cycle in cams.cycles() for name,_ in local_components(config,search,cycle)}-{'individual_head'}
    if not required<=native_meshes.keys():raise ValueError('Rejected assembly part: '+str(required-native_meshes.keys()))
    candidates={n:m.volume for n,m in native_meshes.items() if n.startswith('head_bionic_')}
    if not candidates:raise ValueError('No positive bionic candidate')
    selected=min(candidates,key=candidates.get)
    if selected not in native_meshes or 'head_dense_reference' not in native_meshes:
        raise ValueError('Bionic/reference topology rejected')
    replacements={name:native_meshes[name] for name in required}
    replacements['individual_head']=native_meshes[selected]
    audits['individual_head']=copy.deepcopy(audits[selected])
    heads=[r for r in old['instances'] if r['family']=='individual_head']
    heads_by_bank={bank:sorted((r for r in heads if r['bank']==bank),key=lambda r:r['matrix_mm'][0][3]) for bank in (-1,1)}
    recipes=[];cam_checks=[]
    def derivative(name,adds,cuts):
        source=previous/'pieces'/(name+'.stl')
        if sha256(source)!=lock['pieces/'+name+'.stl']:raise ValueError('Prior mesh changed')
        recipes.append({'id':name,'source_mesh':{'path':str(source),'sha256':sha256(source)},'add':adds,'subtract':cuts,'intersect':[]})
    for bank in (-1,1):
        adds=[];cuts=[]
        for head in heads_by_bank[bank]:
            x=head['matrix_mm'][0][3]
            for sx in (-1,1):
                for sy in (-1,1):
                    xx=x+sx*39;z=sy*39
                    adds.append(beam([xx,bank*74,z],[xx,bank*106,z],8))
                    cuts.append(beam([xx,bank*80,z],[xx,bank*110,z],4.1))
        derivative('crankcase_negative' if bank<0 else 'crankcase_positive',adds,cuts)
        for role,sign in (('intake',1),('exhaust',-1)):
            name=f'camshaft_{"negative" if bank<0 else "positive"}_{role}'
            lobes=[]
            for cycle in (r for r in cams.cycles() if r['bank']==bank):
                x=heads_by_bank[bank][cycle['pair_index']]['matrix_mm'][0][3]
                polygon,screen=cams.section(role,search['timing']['roles'][role],bank,cycle['overlap_tdc_deg'])
                for sx in (-1,1):
                    xx=x-bank*sx*config['pair_half_pitch_mm'];lobes.append(cams.extrude(polygon,xx-5,xx+5))
                cam_checks.append({'id':name,'pair_index':cycle['pair_index'],**screen})
            source=output/(name+'-lobes.stl');trimesh.util.concatenate(lobes).export(source)
            recipes.append({'id':name,'source_mesh':{'path':str(source),'sha256':sha256(source)},
                            'add':[beam([-380,0,0],[380,0,0],9)],'subtract':[],'intersect':[]})
        for role,sign in (('intake',1),('exhaust',-1)):
            name=role+('_negative' if bank<0 else '_positive')
            radius=.86*config[role+'_diameter_mm']/2*math.sqrt(2)*1.03
            trunk=[[-360,bank*310,sign*155],[380,bank*310,sign*155]]
            paths=[trunk]
            for head in heads_by_bank[bank]:
                x=head['matrix_mm'][0][3]
                a=np.array([x,bank*246.25,sign*104]);b=np.array([x,bank*246.25,sign*145]);c=np.array([x,bank*310,sign*155])
                paths.append([(1-t)**2*a+2*(1-t)*t*b+t*t*c for t in np.linspace(0,1,25)])
            terminal=np.array([400.25,bank*386.25,-160-bank*43]) if role=='exhaust' else np.array([500,bank*372.25,-160-bank*49])
            paths.append([trunk[-1],[terminal[0],terminal[1],sign*155],terminal])
            adds=[];cuts=[]
            for path in paths:
                for a,b in zip(path,path[1:]):
                    adds.append(beam(a,b,radius+3,False if np.array_equal(b,terminal) else True));cuts.append(beam(a,b,radius,True))
            for head in heads_by_bank[bank]:
                x=head['matrix_mm'][0][3]
                cuts.append(beam([x,bank*246.25,sign*80],[x,bank*246.25,sign*125],radius))
                cuts.append(box([x,bank*246.25,sign*92],[42,45,12]))
            v=terminal-np.asarray(paths[-1][-2]);cuts.append(beam(terminal,terminal+v/np.linalg.norm(v)*50,radius))
            recipes.append({'id':name,'add':adds,'subtract':cuts,'intersect':[]})
    adds=[];cuts=[]
    for sign in (-1,1):
        a=math.radians(sign*165);x=-48*math.cos(a);z=48*math.sin(a)
        adds.append(beam([x,150,z],[x,160,z],6));cuts.append(beam([x,151,z],[x,163,z],3.2))
    derivative('cylinder',adds,cuts)
    save(output/'integration-recipe.json',{'classification':'hypothetical_engine_components_not_manufacturing_geometry','parts':recipes})
    command([dotnet,'build',HERE.parent/'assembly/Engine.csproj','-c','Release','-o',output/'engine-app',
             '-p:BaseIntermediateOutputPath='+str(output/'engine-obj')+'/'],output/'integration-build.log')
    command([dotnet,output/'engine-app/Engine.dll',output/'integration-recipe.json',sha256(output/'integration-recipe.json'),'.5',output/'integrated-native'],output/'integration-native.log')
    derived,derived_audits=audit_native(output/'integrated-native')
    if not all(r['passed'] for r in derived_audits.values()):raise ValueError('Integrated derivative topology rejected')
    replacements.update(derived)
    keep=[copy.deepcopy(r) for r in old['instances'] if r['family'] not in replace]
    alpha=math.radians(8);cam_z=config['face_z_mm']+164.1*math.cos(alpha);cam_y=config['row_offset_mm']+164.1*math.sin(alpha)
    for cycle in cams.cycles():
        bank=cycle['bank'];head=heads_by_bank[bank][cycle['pair_index']]
        matrix=head_transform(head['matrix_mm'][0][3],bank,211.25)
        for name,local in local_components(config,search,cycle):
            keep.append({'family':name,'matrix_mm':(matrix@local).tolist(),'bank':bank,'cycle':cycle,
                         'placement_basis':'new_parametric_cold_hypothesis'} )
        # One central plug replaces the previous twin-plug purchased envelopes.
        keep.append({'family':'ignition_coil','matrix_mm':(matrix@axis_pose([0,0,0],[0,0,1],52)).tolist(),'bank':bank})
    for bank in (-1,1):
        for role,sign in (('intake',1),('exhaust',-1)):
            m=np.eye(4);m[:3,3]=[0,bank*(211.25+cam_z),sign*cam_y]
            keep.append({'family':f'camshaft_{"negative" if bank<0 else "positive"}_{role}','matrix_mm':m.tolist(),'bank':bank})
    # shortcut: services retain purchased envelopes; their connectors and the gear drive require measured redesign.
    for row in keep:
        if row['family']=='injector':row['matrix_mm'][1][3]=row['bank']*263;row['matrix_mm'][2][3]=143
        if row['family']=='fuel_rail':row['matrix_mm'][1][3]=row['bank']*263;row['matrix_mm'][2][3]=177
        if row['family']=='intercooler':row['matrix_mm'][1][3]=row['bank']*255;row['matrix_mm'][2][3]=260
    counts=Counter(r['family'] for r in keep)
    meshes={}
    for name in counts:
        if name in replacements:
            meshes[name]=replacements[name];meshes[name].export(pieces/(name+'.stl'))
        else:
            source=previous/'pieces'/(name+'.stl')
            if sha256(source)!=lock['pieces/'+name+'.stl']:raise ValueError('Previous prototype changed: '+name)
            shutil.copy2(source,pieces/(name+'.stl'));meshes[name]=trimesh.load_mesh(source,process=True)
        if not meshes[name].is_volume:raise ValueError('Non-positive prototype: '+name)
    for i,row in enumerate(keep):
        row['instance_id']=f'part_{i:04d}'
        row.pop('translation_mm',None);row.pop('rotation_xyz_deg',None)
        m=np.asarray(row['matrix_mm'])
        if not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3)) or not np.isclose(np.linalg.det(m[:3,:3]),1):raise ValueError('Non-rigid pose')
    for name in replacements:
        if name in meshes:audits[name]=derived_audits.get(name,audits.get(name,{}))
    parts={name:{'id':name,'quantity':count,'detail_level':'new_native_cold_hypothesis' if name in replacements else old['parts'][name]['detail_level'],
                 'actual_alloy':None,'manufacturing_process':None} for name,count in counts.items()}
    scene_report=prior.export_scene(output,meshes,keep)
    save(output/'assembly.json',{'classification':'modern_bionic_4v_biturbo_cold_hypothesis_no_release','parts':parts,'instances':keep,'units':'mm_hypothetical'})
    save(output/'cam-profiles.json',cam_checks)
    mass=(native_meshes['head_component_01'].volume+sum(native_meshes[n].volume*k for n,k in
          [('upper_spring_retainer',1),('valve_keeper_half',2),('valve_shim',1),('rocker',1),('cam_roller',1),('cam_roller_pin',1),('outer_valve_spring_0',1/3),('inner_valve_spring_0',1/3)]))*7.85e-6
    if mass>.11:raise ValueError('Assumed moving mass exceeded')
    gas_head=contact(native_meshes['gas_domain'],native_meshes[selected])
    gas=native_meshes['gas_domain']
    flow={'native_gas_head_independent_meshing_overlap':gas_head,
          'inset_gas_head_separation_witness':contact(native_meshes['gas_inset_screen_0_5mm'],native_meshes[selected]),
          'gas_oil':contact(gas,native_meshes['oil_domain']),'gas_oil_guard_2mm':contact(gas,native_meshes['oil_guard_2mm']),
          'inset_witness_mm':.5,'conforming_cfd_domain_qualified':False,
          'construction':'native_domains_and_declared_eroded_separation_witness_not_physical_flow_or_pressure_test'}
    if flow['gas_oil']['volume_mm3']>0:raise ValueError('Gas/oil intersection')
    dense=native_meshes['head_dense_reference'].volume
    report={'classification':'bionic_head_and_flat12_cold_geometry_candidate_no_physical_release',
            'glb_roundtrip':scene_report,'native_mesh_audits':audits,'integration_mesh_audits':derived_audits,
            'selected_head':selected,'candidate_volumes_mm3':candidates,'head_volume_mm3':native_meshes[selected].volume,'dense_reference_volume_mm3':dense,
            'material_volume_reduction_fraction':1-native_meshes[selected].volume/dense,
            'steel_equivalent_moving_mass_kg':mass,'assumed_mass_ceiling_kg':.11,'flow_mesh_checks':flow,
            'search_sha256':sha256(output/'search.json'),'source_sha256':source_hashes(),
            'previous_report_sha256':sha256(previous/'report.json'),'prior_turbo_prototypes_unchanged':True,
            'full_assembly_interference_checked':False,'cam_drive_defined':False,'hot_clearance_validated':False,
            'fea_or_cfd_optimized':False,'material_qualified':False,'physical_bom_complete':False,
            'manufacturing_authorized':False,'engine_start_authorized':False}
    save(output/'report.json',report)
    return meshes,keep,report


def source_hashes():
    files=[*HERE.glob('*.py'),HERE/'Program.cs',HERE/'Head.csproj',
           ROOT/'parts/picogk-catalog/common/Sdf.cs',ROOT/'parts/picogk-catalog/common/Params.cs',ROOT/'parts/picogk-catalog/common/Runner.cs',ROOT/'parts/picogk-catalog/engine/EngineSdf.cs',
           ROOT/'parts/picogk-catalog/engine/Valves.cs',ROOT/'twins/m64-cylinder-head/source/valvetrain/valvetrain.py',
           HERE.parent/'assembly/Program.cs',HERE.parent/'assembly/Engine.csproj',HERE.parent/'assembly/run.py',
           HERE.parent/'hypothesis/run.py',ROOT/'twins/m64-cylinder-head/source/picogk-local-junction/exact_zero_countertrial.py',
           ROOT/'twins/m64-cylinder-head/source/picogk-local-junction/audit_mesh.py',ROOT/'twins/reference-917-engine/source/build_f37_printable_head_mesh.py']
    return {str(p.relative_to(ROOT)):sha256(p) for p in files}


def run(output,previous,dotnet):
    output=check_output(output);output.mkdir(parents=True,mode=0o700)
    sources=source_hashes();save(output/'execution-sources.json',sources)
    config,search=prepare(output)
    command([dotnet,'build',HERE/'Head.csproj','-c','Release','-o',output/'app',
             '-p:BaseIntermediateOutputPath='+str(output/'obj')+'/'],output/'build.log')
    levels={}
    for grid in (1,.5):
        directory=output/f'native-{grid:g}'
        command([dotnet,output/'app/Head.dll',output/'config.json',sha256(output/'config.json'),grid,directory],output/f'native-{grid:g}.log')
        native_meshes,audits=audit_native(directory);levels[str(grid)]=audits
    save(output/'grid-audits.json',levels)
    result=integrate(output,previous,output/'native-0.5',config,search,dotnet,native_meshes,audits)
    if sources!=source_hashes():raise ValueError('Executed sources changed during run')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--dotnet',required=True)
    args=parser.parse_args();run(args.output.resolve(),args.previous.resolve(),args.dotnet)
