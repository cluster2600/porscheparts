"""Check the frozen analytical birth/plastic-history/release software witness."""
import argparse,csv,hashlib,json,math,re
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def assess(folder):
    folder=Path(folder);contract=json.loads((folder/'contract.json').read_text());tol=contract['absolute_tolerances'];checks=[];rows={}
    for label,name in [('plastic','birth-cycle-release.i'),('elastic','elastic-control.i')]:
        sub=folder/label;receipt=json.loads((sub/'native-execution.json').read_text());log=(sub/'native.log').read_text();clean=re.sub(r'\x1b\[[0-9;]*m','',log)
        checks.append({'name':label+'_native_receipt','pass':receipt['returncode']==0 and not receipt['timed_out'] and receipt['input_i_unchanged'] and receipt.get('source_and_binary_unchanged',True) and receipt['log_sha256']==sha(sub/'native.log') and receipt['image_digest']==contract['image_digest'] and receipt['input_i_sha256'][name]==contract['inputs_sha256'][name] and sha(sub/name)==contract['inputs_sha256'][name]})
        final_residuals=[]
        for segment in clean.split('Solve Converged!')[:-1]:
            values=re.findall(r'\d+ Nonlinear \|R\| = ([0-9.eE+\-]+)',segment)
            if values:final_residuals.append(float(values[-1]))
        checks.append({'name':label+'_six_balanced_increments','pass':len(final_residuals)==6 and max(final_residuals)<1e-9,'final_residual_norms':final_residuals})
        data=list(csv.DictReader((sub/(Path(name).stem+'_out.csv')).open()));rows[label]={int(float(x['time'])):{k:float(v) for k,v in x.items()} for x in data}
        checks.append({'name':label+'_complete_finite_history','pass':set(rows[label])==set(range(7)) and all(math.isfinite(v) for x in rows[label].values() for v in x.values())})
    mapping={'u_right_mm':('u_right',tol['displacement_mm']),'stress_MPa':('stress_bar',tol['stress_MPa']),'plastic_xx':('plastic_xx_bar',tol['plastic_strain']),'temperature_K':('temperature_bar',tol['temperature_K'])}
    for stage,expected in contract['expectations'].items():
        label='elastic' if stage.startswith('elastic_') else 'plastic';time=int(stage[-1]);actual=rows[label][time]
        for key,value in expected.items():
            if key=='residual_relative_birth_mm':observed=actual['u_right']-rows[label][1]['u_right'];limit=tol['displacement_mm']
            else:field,limit=mapping[key];observed=actual[field]
            checks.append({'name':stage+'_'+key,'expected':value,'actual':observed,'absolute_tolerance':limit,'pass':abs(observed-value)<=limit})
    checks.append({'name':'history_retained_through_cooling_and_release','pass':all(abs(rows['plastic'][t]['plastic_xx_bar']+.001)<=tol['plastic_strain'] for t in [3,4,5,6])})
    return {'passed':all(x['pass'] for x in checks),'purpose':contract['purpose'],'thermal_cycle':'prescribed uniform synthetic temperature, no heat equation and no titanium calibration','checks':checks,'inputs_sha256':contract['inputs_sha256'],'history':rows,'artifacts_sha256':{str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='assessment.json'},'assessor_sha256':sha(Path(__file__))}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();output=a.folder/'assessment.json';assert not output.exists();result=assess(a.folder);output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':len(result['checks'])}));raise SystemExit(0 if result['passed'] else 1)
