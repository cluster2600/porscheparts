"""Apply the refinement gate frozen before the native thermal-birth runs."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(contract_path, assessments):
    contract=json.loads(Path(contract_path).read_text())
    card=contract['card']
    reports=[json.loads(Path(p).read_text()) for p in assessments]
    if len(reports)!=len(card['time_steps_s']) or [r['level'] for r in reports]!=list(range(len(reports))):
        raise ValueError('All frozen time levels are required in order')
    for i,r in enumerate(reports):
        if not r['passed'] or r['dt_s']!=card['time_steps_s'][i] or r['frozen_contract_sha256']!=sha(contract_path):
            raise ValueError('An accepted frozen native assessment is missing')
        if r['assessor_sha256']!=contract['assessor_sha256']:
            raise ValueError('Assessment code differs from the frozen contract')
    errors=[r['max_continuous_relative_energy_error'] for r in reports]
    ratios=[a/b for a,b in zip(errors,errors[1:])]
    limit=card['predeclared_tolerances']['minimum_refinement_error_ratio']
    passed=all(ratio>=limit for ratio in ratios) and errors[-1]<=card['predeclared_tolerances']['finest_continuous_energy_relative']
    return {'schema_version':'1.0.0','passed':passed,'classification':card['classification'],
            'whole_head_lpbf_complete':False,'time_steps_s':card['time_steps_s'],
            'max_continuous_relative_energy_errors':errors,'successive_error_ratios':ratios,
            'predeclared_minimum_error_ratio':limit,'predeclared_finest_energy_limit':card['predeclared_tolerances']['finest_continuous_energy_relative'],
            'frozen_contract_sha256':sha(contract_path),
            'native_levels':[{'level':r['level'],'checks_count':r['checks_count'],'max_error_by_check':r['max_error_by_check'],
                              'native_receipt_sha256':r['native_receipt_sha256'],'final_state':r['traces'][-1],
                              'assessment_path':str(p),'assessment_sha256':sha(p)} for p,r in zip(assessments,reports)],
            'scope':'Moving Gaussian normalization, field material evaluation, conforming-node birth and nonlinear thermal storage/conservation only. No head solve, physical alloy or calibrated LPBF process.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--assessment',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refinement output must be new')
    result=assess(args.contract,args.assessment)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('passed','max_continuous_relative_energy_errors','successive_error_ratios')}))
    raise SystemExit(0 if result['passed'] else 1)
