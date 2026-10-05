import json,hashlib
from pathlib import Path
from prepare_engineering_sensitivities import prepare_eigenstrain
root=Path.cwd()
cases=[]
for variant in ['R0','V5']:
    for name,h,amp,n,pitch,yaw in [
        ('diagonal-edge', 'h4p5',.001,[0,1,0],5,-45),
        ('half-strain','h4p5',.0005,[0,1,0],5,-45),
        ('zero-strain','h4p5',0,[0,1,0],5,-45),
        ('upright','h4p5',.001,[0,0,1],5,0),
        ('sparse-support','h4p5',.001,[0,1,0],10,-45),
        ('finer-mesh','h3p6',.001,[0,1,0],5,-45)]:
        label='manufacturing-'+variant+'-'+name
        case=root/label; mesh=root/('mesh-'+variant+'-'+h)
        r=prepare_eigenstrain(mesh/'rotation.inp',case,amp,n,pitch,yaw)
        r.update(configuration_id=json.load(open(mesh/'mesh-report.json'))['configuration_id'],source_mesh_report_sha256=hashlib.sha256((mesh/'mesh-report.json').read_bytes()).hexdigest(),source_step_sha256=json.load(open(mesh/'mesh-report.json'))['source_step_sha256'],scenario='Candidate AlSi10Mg review; BLT workshop target, actual alloy/condition/machine unselected. Generic elastic E=70GPa nu=.33 inherited, no machine calibration or thermal recipe simulated',build_pose_description='Rx90 then Rz45; 10mm envelope margin' if n==[0,1,0] else 'Upright Rx0 Rz0; EOS envelope non-fit, BLT envelope screening only')
        (case/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');cases.append(label)
Path('manufacturing-case-list.json').write_text(json.dumps(cases,indent=2)+'\n')
print(cases)
