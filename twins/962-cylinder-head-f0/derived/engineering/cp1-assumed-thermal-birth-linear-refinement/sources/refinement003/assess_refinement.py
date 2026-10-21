"""Fixed three-reference LINEAR thermal energy-refinement binding successor; held until complete."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARED = {'card': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-prep-001/card.json', 'sha256': '4e07cbb997c831bac2c0abd43092148c5518b6c7aa04d7b3d287779f9e700986'}, 'deck': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-prep-001/thermal-birth.i', 'sha256': 'ffe9b19786d534a8b4ad60e78290c7d3698a2dcb6b7ddf183f100321b02df1aa'}, 'assessor': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-prep-001/assess.py', 'sha256': '0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338'}}
REFERENCES = [{'level': 0, 'numerical_reference': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level0-prep-001/case-contract.json', 'sha256': '7607afa5fd41e7df2b867aa4f2d6342e9adf03e2ee81b84085dedfed3e972535'}, 'time_input': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level0-prep-001/time-level.i', 'sha256': 'efa207979d8df59060209e7d6673a7630bc3f9cf8fe7356700d7ed85de190ac6'}}, {'level': 1, 'numerical_reference': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level1-prep-001/case-contract.json', 'sha256': '047471049c96bfb3c28fd74395998748eb5ca5c91feb24495449ce78f9f5ad47'}, 'time_input': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level1-prep-001/time-level.i', 'sha256': '65a7d5bf03d5f3cc7ae5620edab2bc591b597cdfd035de3de1c859b4944583cc'}}, {'level': 2, 'numerical_reference': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-prep-001/case-contract.json', 'sha256': '13a12dc586cf773a0a4b0a2777276d062d60d2e7c67aa7357e6581fd83f4fddd'}, 'time_input': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-prep-001/time-level.i', 'sha256': '460a3332eac1ec0eddd1884657d2b8b0cdd96bd49443180d00651e44fb76a09a'}}]
IMMUTABLE_LEVEL2 = {'native_receipt': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-001/native-execution.json', 'sha256': 'a210f0ef6d41686ce795b76d7d43fc17aa320038cfabd601d0250ae8feb2b673'}, 'assessment': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-assessment-001/assessment.json', 'sha256': '198ae20f6baa27a726b17f3924659b8c1e0613e9a5b1e161ad8f6ef3b5107dbf'}, 'assessment_result_peer': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-assessment-result-peer-001/review.json', 'sha256': '73064c4848bf2955c65fff2a339cd98cc0db98a4b6035898cf964a84ed7226b2'}, 'root_assessment_acceptance': {'path': 'work/962-engineering/cp1-assumed-thermal-birth-linear-assessment-root-execution-001/result-peer-acceptance.json', 'sha256': '519da0e769a31f66942a0c376058036aa0b3b6869d3dcae98efd509b78a71fcf'}}
RESULT_KEYS = ('native_receipt', 'assessment', 'assessment_result_peer', 'root_assessment_acceptance')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bound_file(record):
    if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
        raise ValueError('Complete exact bound file required; future NULL cannot be evaluated')
    name = Path(record['path'])
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('Project-relative bound file required')
    path = ROOT / name
    if not path.is_file() or path.is_symlink() or path.resolve() != path or sha(path) != record['sha256']:
        raise ValueError('Bound refinement input changed')
    return path


def assess(manifest_path, assessments):
    manifest=json.loads(Path(manifest_path).read_text())
    if (manifest.get('schema')!='962-CP1-LINEAR-fixed-three-level-refinement-manifest/v1'
            or manifest.get('status')!='BOUND_THREE_ACCEPTED_LEVELS'
            or manifest.get('ready_for_evaluation') is not True or manifest['shared']!=SHARED
            or any(manifest.get(k) is not False for k in ['native_execution_authorized','assessment_execution_authorized',
                'refinement_evaluation_authorized','head_execution_authorized','engineering_accepted','physics_qualified',
                'material_qualified','process_calibrated','manufacturing_authorized'])):
        raise ValueError('Complete reviewed fixed software manifest required; no execution or physical authority')
    paths={key:bound_file(record) for key,record in SHARED.items()}
    card=json.loads(paths['card'].read_text())
    rows=manifest['levels']
    if len(rows)!=3 or any(type(r['level']) is not int for r in rows) or [r['level'] for r in rows]!=[0,1,2] or len(assessments)!=3:
        raise ValueError('All fixed time levels are required in order')
    if {key:rows[2][key] for key in RESULT_KEYS}!=IMMUTABLE_LEVEL2:
        raise ValueError('Immutable accepted level2 cannot be reassociated')
    reports=[]
    for i,row in enumerate(rows):
        if {key:row[key] for key in ('level','numerical_reference','time_input')}!=REFERENCES[i]:
            raise ValueError('Different numerical reference or time-level input')
        reference=json.loads(bound_file(row['numerical_reference']).read_text())
        time_path=bound_file(row['time_input'])
        if (reference['card']!=card or reference['card_sha256']!=SHARED['card']['sha256']
                or reference['input_sha256']['thermal-birth.i']!=SHARED['deck']['sha256']
                or reference['assessor_sha256']!=SHARED['assessor']['sha256']
                or reference['selected_level_only']!=i
                or reference['level_input_sha256']!={str(i):row['time_input']['sha256']}
                or reference['time_level_inputs']!={str(i):time_path.read_text()}):
            raise ValueError('Shared physics or per-level reference differs')
        result_paths={key:bound_file(row[key]) for key in RESULT_KEYS}
        if Path(assessments[i]).resolve()!=result_paths['assessment']:
            raise ValueError('Assessment path/order differs from the fixed manifest')
        r=json.loads(result_paths['assessment'].read_text())
        receipt=json.loads(result_paths['native_receipt'].read_text())
        peer=json.loads(result_paths['assessment_result_peer'].read_text())
        accepted=json.loads(result_paths['root_assessment_acceptance'].read_text())
        if (not r['passed'] or r['level']!=i or r['dt_s']!=card['time_steps_s'][i]
                or r['frozen_contract_sha256']!=row['numerical_reference']['sha256']
                or r['assessor_sha256']!=SHARED['assessor']['sha256']
                or r['native_receipt_sha256']!=row['native_receipt']['sha256']
                or r['classification']!=card['classification'] or r['failed_checks']):
            raise ValueError('An accepted own-contract unchanged-assessor report is missing')
        if (receipt['level']!=i or receipt['physics_contract_sha256']!=row['numerical_reference']['sha256']
                or receipt['returncode']!=0 or receipt['native_execution_completed'] is not True
                or receipt['inputs_unchanged'] is not True or receipt['binary_and_runtime_unchanged'] is not True
                or peer.get('blockers')!=[] or not str(peer.get('decision','')).startswith('CLEAR_')
                or accepted.get('passed_single_level_software_assessment') is not True
                or accepted.get('assessment_sha256')!=row['assessment']['sha256']
                or accepted.get('peer_sha256')!=row['assessment_result_peer']['sha256']):
            raise ValueError('Native receipt and stopped peer/root assessment acceptance must join')
        count=round(card['end_time_s']/r['dt_s'])
        # 0548 stores signed trace defects; its summary is their maximum absolute value.
        trace_errors=[trace['relative_continuous_energy_error'] for trace in r['traces']]
        if (r['native_steps']!=count or len(trace_errors)!=count
                or [trace['step'] for trace in r['traces']]!=list(range(1,count+1))
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in trace_errors)
                or r['max_continuous_relative_energy_error']!=max(abs(x) for x in trace_errors)):
            raise ValueError('Complete finite trace maximum must match the saved assessment summary')
        reports.append(r)
    errors=[r['max_continuous_relative_energy_error'] for r in reports]
    for error in errors:
        try:
            valid=type(error) in (int,float) and math.isfinite(error) and error>=0
        except OverflowError:
            valid=False
        if not valid:
            raise ValueError('Refinement errors must be finite nonnegative numbers')
    if any(error==0 for error in errors[1:]):
        raise ValueError('A zero denominator cannot establish the frozen refinement ratio')
    ratios=[a/b for a,b in zip(errors,errors[1:])]
    if any(not math.isfinite(ratio) for ratio in ratios):
        raise ValueError('Refinement ratios must remain finite')
    limit=card['predeclared_tolerances']['minimum_refinement_error_ratio']
    passed=all(ratio>=limit for ratio in ratios) and errors[-1]<=card['predeclared_tolerances']['finest_continuous_energy_relative']
    return {'schema_version':'1.0.0','passed':passed,'classification':card['classification'],
            'whole_head_lpbf_complete':False,'time_steps_s':card['time_steps_s'],
            'max_continuous_relative_energy_errors':errors,'successive_error_ratios':ratios,
            'predeclared_minimum_error_ratio':limit,'predeclared_finest_energy_limit':card['predeclared_tolerances']['finest_continuous_energy_relative'],
            'refinement_manifest_sha256':sha(manifest_path),
            'numerical_reference_sha256s':[row['numerical_reference']['sha256'] for row in rows],
            'refinement_assessor_sha256':sha(__file__),
            'native_levels':[{'level':r['level'],'checks_count':r['checks_count'],'max_error_by_check':r['max_error_by_check'],
                              'native_receipt_sha256':r['native_receipt_sha256'],'final_state':r['traces'][-1],
                              'assessment_path':str(p),'assessment_sha256':sha(p)} for p,r in zip(assessments,reports)],
            'engineering_accepted':False,'physics_qualified':False,'material_qualified':False,
            'process_calibrated':False,'manufacturing_authorized':False,
            'scope':'Fixed synthetic constant-cp LINEAR thermal energy-error refinement only. No full-field spatial convergence, original Newton convergence, head solve, matched physical alloy or calibrated LPBF process.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--assessment',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute or sha(args.manifest)!=args.manifest_sha256:
        raise ValueError('Separate exact completed-manifest query authority required')
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError('Refinement output must be new')
    result=assess(args.manifest,args.assessment)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('passed','max_continuous_relative_energy_errors','successive_error_ratios')}))
    raise SystemExit(0 if result['passed'] else 1)
