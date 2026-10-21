"""Run the frozen 900 MPa or published Luo J2 sensitivity without changing linear cases."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import numpy as np

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE.parent/'bionic-20261011'))
import simulate
sys.path.insert(0,str(SOURCE.parent/'revalidation-20261016'))
from audit_energy import sha,dat_fields

IMAGE='sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
BINARY_SHA='271f8411371b978d7a8d31a7a13d0765e6e1f872e8a8b1d6aac6d0856c71ec6c'


def docker(*args):
    return subprocess.check_output(['/usr/local/bin/docker',*args],text=True,timeout=30).strip()


def material_cards(plan):
    model=plan['plasticity']
    if 'curve_input' in model:
        path=SOURCE.parent/model['curve_input']
        assert sha(path)==model['curve_sha256']
        assert sha(path.parent/'provenance.json')==model['curve_provenance_sha256']
        text=path.read_text()
        table=np.array([[float(v) for v in line.split(',')] for line in text.splitlines()
                        if line.strip() and not line.startswith('*')])
        assert table.shape[1]==2 and table[0,1]==0
        assert np.all(np.diff(table[:,1])>0) and np.all(np.diff(table[:,0])>=0)
    else:
        text='*PLASTIC,HARDENING=ISOTROPIC\n900.,0.\n900.,1.\n'
        table=np.array([[900.,0.],[900.,1.]])
    return text,table


def prepare(reference,output,plan):
    reference,output=Path(reference),Path(output)
    assert sha(reference/'mesh.inp')==plan['mesh_inp_sha256']
    path=reference/(plan['linear_reference_case']+'.inp')
    assert sha(path)==plan['reference_deck_sha256']
    assert sha(reference.parent/'carrier.step')==plan['geometry_STEP_sha256']
    output.mkdir(parents=True,exist_ok=False)
    for name in ('mesh.inp','mesh.npz','mesh.json'):
        shutil.copyfile(reference/name,output/name)
    text=path.read_text()
    assert '*PLASTIC' not in text and '*STEP\n' in text and text.count('\nS\n')==2
    plastic,_=material_cards(plan)
    old_elastic='*ELASTIC\n107000.0,0.31\n'
    assert text.count(old_elastic)==1
    text=text.replace(old_elastic,f"*ELASTIC\n{plan['plasticity']['E_MPa']},{plan['plasticity']['nu']}\n",1)
    text=text.replace('*DENSITY\n',plastic+'\n*DENSITY\n',1)
    step='*STEP,NLGEOM,INC=100\n' if plan['plasticity']['geometric_nonlinearity'] else '*STEP,INC=100\n'
    text=text.replace('*STEP\n',step,1)
    increments=plan['step']
    values=','.join(str(increments[key]) for key in ('initial_increment','end_time','minimum_increment','maximum_increment'))
    text=text.replace('*STATIC,SOLVER=SPOOLES\n','*STATIC,SOLVER=SPOOLES\n'+values+'\n',1)
    text=text.replace('\nS\n','\nS,PEEQ,ENER\n')
    if plan.get('unload_to_zero'):
        reference_lines=path.read_text().splitlines()
        start=reference_lines.index('*CLOAD')+1
        end=next(i for i in range(start,len(reference_lines)) if reference_lines[i].startswith('*'))
        zero_loads=[','.join(line.split(',')[:2])+',0.' for line in reference_lines[start:end]]
        step_settings=plan['unload_step']
        increment_line=','.join(str(step_settings[key]) for key in ('initial_increment','end_time','minimum_increment','maximum_increment'))
        output_start=reference_lines.index('*NODE PRINT,NSET=ALLN')
        output_lines=[line.replace('S','S,PEEQ,ENER') if line=='S' else line for line in reference_lines[output_start:]]
        text+='\n'.join(['*STEP,NLGEOM,INC=100','*STATIC,SOLVER=SPOOLES',increment_line,
                         '*CLOAD,OP=NEW',*zero_loads,*output_lines])+'\n'
    # These blocks must remain exactly the reference. No load or support fitting.
    from audit_energy import blocks
    protected=lambda values:[(key,rows) for key,rows in values if key.startswith(('*ELEMENT','*SPRING','*NSET','*CLOAD','*BOUNDARY'))]
    name=plan.get('case_name','combined-spring-1000-plastic900')
    (output/(name+'.inp')).write_text(text)
    changed=blocks(output/(name+'.inp'))
    first_step_end=next(i for i,(key,_) in enumerate(changed) if key=='*ENDSTEP')
    assert protected(blocks(path))==protected(changed[:first_step_end+1])
    shutil.copyfile(path,output/'reference-linear.inp')
    shutil.copyfile(reference/(plan['linear_reference_case']+'.json'),output/'reference-linear.json')
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    if 'curve_input' in plan['plasticity']:
        material=SOURCE.parent/plan['plasticity']['curve_input']
        shutil.copyfile(material,output/'material-curve.inp')
        shutil.copyfile(material.parent/'provenance.json',output/'material-provenance.json')
        shutil.copyfile(material.parent/'DATA_LICENSE.json',output/'material-DATA_LICENSE.json')
    return name


def coupon(output,plan):
    folder=output/'coupon';folder.mkdir()
    (folder/'mesh.inp').write_text('''*NODE
1,0,0,0
2,1,0,0
3,1,1,0
4,0,1,0
5,0,0,1
6,1,0,1
7,1,1,1
8,0,1,1
*ELEMENT,TYPE=C3D8,ELSET=BODY
1,1,2,3,4,5,6,7,8
''')
    (folder/'coupon.inp').write_text('''*INCLUDE,INPUT=mesh.inp
*MATERIAL,NAME=REFERENCE
*ELASTIC
107000.,0.31
*PLASTIC,HARDENING=ISOTROPIC
900.,0.
900.,1.
*SOLID SECTION,ELSET=BODY,MATERIAL=REFERENCE
*NSET,NSET=ALLN,GENERATE
1,8
*STEP,INC=100
*STATIC,SOLVER=SPOOLES
0.25,1.,0.001,0.25
*BOUNDARY
1,1,1,0.
4,1,1,0.
5,1,1,0.
8,1,1,0.
1,2,2,0.
2,2,2,0.
5,2,2,0.
6,2,2,0.
1,3,3,0.
2,3,3,0.
3,3,3,0.
4,3,3,0.
2,1,1,0.02
3,1,1,0.02
6,1,1,0.02
7,1,1,0.02
*NODE PRINT,NSET=ALLN
U
*EL PRINT,ELSET=BODY
S,PEEQ
*NODE FILE
U
*EL FILE
S,PEEQ
*END STEP
''')
    plastic,raw_table=material_cards(plan)
    from ccx_curve_reference import effective_curve,maximum_interpolation_difference
    table=effective_curve(raw_table)
    model=plan['plasticity'];modulus=model['E_MPa']
    path=folder/'coupon.inp'
    text=path.read_text().replace('107000.,0.31',f"{modulus},{model['nu']}")
    text=text.replace('*PLASTIC,HARDENING=ISOTROPIC\n900.,0.\n900.,1.\n',plastic+'\n')
    path.write_text(text)
    total_strain=table[:,1]+table[:,0]/modulus
    assert total_strain[0]<.02<total_strain[-1]
    expected_stress=float(np.interp(.02,total_strain,table[:,0]))
    seconds=simulate.execute(folder,'coupon',timeout_seconds=60)
    fields=dat_fields(folder/'coupon.dat');stress=fields['stresses'][:,2:]
    assert stress.shape==(8,6)
    assert np.max(np.abs(stress[:,0]-expected_stress))<=.01
    assert np.max(np.abs(stress[:,1:]))<=.01
    assert np.max(np.abs(fields['displacements'][[1,2,5,6],1]-.02))<=1e-10
    from analyze_plastic900 import fields as read_fields
    peeq=read_fields(folder/'coupon.dat')['equivalent plastic strain'][1.][:,2]
    expected_peeq=.02-expected_stress/modulus
    peeq_error=float(np.max(np.abs(peeq-expected_peeq)))
    assert peeq.shape==(8,) and peeq_error<=1e-6
    report={'known_uniaxial_small_strain':.02,'expected_axial_stress_MPa':expected_stress,
            'input_curve_points':len(raw_table),'CCX_effective_curve_points':len(table),
            'CCX_curve_reference_source_sha256':sha(SOURCE/'ccx_curve_reference.py'),
            'raw_vs_effective_maximum_stress_difference_MPa':maximum_interpolation_difference(raw_table,table)[0],
            'expected_equivalent_plastic_strain':.02-expected_stress/modulus,
            'PEEQ_max_absolute_error':peeq_error,'PEEQ_absolute_tolerance':1e-6,
            'stress_absolute_tolerance_MPa':.01,'stress_max_absolute_error_MPa':float(np.max(np.abs(stress[:,0]-expected_stress))),
            'other_stress_max_absolute_MPa':float(np.max(np.abs(stress[:,1:]))),
            'pass':True,'seconds':seconds,'inputs_sha256':{n:sha(folder/n) for n in ('mesh.inp','coupon.inp','coupon.dat')}}
    (folder/'known-result.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def run(reference,output,plan_path=SOURCE/'plastic900-plan.json'):
    output=Path(output)
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text())
    name=prepare(reference,output,plan)
    container='carrier-plastic900-'+uuid.uuid4().hex[:12]
    simulate.CONTAINER=container
    receipt={'status':'starting','container':container,'image':IMAGE,'cpus':1,'memory_GiB':6,
             'swap_GiB':0,'network':'none','name':name,'source_sha256':sha(__file__),
             'plan_sha256':sha(plan_path),'simulation_source_sha256':sha(Path(simulate.__file__)),
             'mesh_sha256':sha(output/'mesh.inp'),'input_sha256':sha(output/(name+'.inp')),
             'scope':plan['scope'],'constitutive_model':plan['plasticity']}
    def save(): (output/'runtime.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    try:
        docker('run','-d','--name',container,'--network','none','--cpus','1','--memory','6g',
               '--memory-swap','6g','--pids-limit','128','--tmpfs','/tmp:rw,size=512m',
               '--entrypoint','/bin/sleep',IMAGE,'infinity')
        assert docker('exec',container,'sha256sum','/usr/bin/ccx').split()[0]==BINARY_SHA
        receipt.update(status='coupon',ccx_binary_sha256=BINARY_SHA);save()
        receipt['coupon']=coupon(output,plan)
        receipt['status']='carrier_running';save()
        receipt['seconds']=simulate.execute(output,name,timeout_seconds=plan['step']['timeout_seconds'])
        receipt['status']='executed'
    except BaseException as error:
        receipt.update(status='failed',error=str(error));raise
    finally:
        removed=subprocess.run(['/usr/local/bin/docker','rm','-f',container],capture_output=True,text=True,timeout=30)
        receipt['owned_container_removed']=removed.returncode==0
        save()
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_mesh',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--plan',type=Path,default=SOURCE/'plastic900-plan.json')
    args=parser.parse_args();print(json.dumps(run(args.reference_mesh,args.output,args.plan)))
