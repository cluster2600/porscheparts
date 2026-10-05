#!/usr/bin/env python3
"""Exercise only private source copying/protocol construction, never a solver."""
import argparse,hashlib,json,time
from pathlib import Path
from unittest.mock import patch
from run_d3 import copy_inputs
from d3_guards import LABELS,digest_file


def audit(root,prepared,previous,selections,capsule,output,report_file):
    started=time.monotonic();deadline=started+30
    output.mkdir(parents=True,exist_ok=False)
    with patch('run_d3.subprocess.Popen',side_effect=AssertionError('No process launch is allowed during input-copy QA')):
        plan,manifest=copy_inputs(prepared,previous,selections,capsule,output,deadline)
    files={};protocols={}
    for label in LABELS:
        case=output/label
        for name,record in plan['cases'][label]['native_MPI_seed_files'].items():
            if digest_file(case/name,deadline)!=record:raise ValueError('Working MPI1020 source copy differs')
            files[label+'/'+name]=record
        for name in ['p','U','k','omega','nut','phi','Uf','uniform/time']:
            if digest_file(case/'1020'/name,deadline)!=digest_file(previous/'1020'/name,deadline):raise ValueError('Working serial1020 source copy differs')
        protocol=json.loads((case/'reference-protocol.json').read_text())
        if protocol['acceptance_all_required']!=plan['original_numerical_acceptance_all_required'] or protocol['required_admission_sample_iterations']!=list(range(1021,1041)):raise ValueError('Working runtime protocol changed frozen criteria/window')
        if any((case/f'processor{rank}/1040').exists() for rank in range(4)):raise ValueError('No final solve checkpoint may exist during copy-only QA')
        protocols[label]=protocol
    differences=[name for name in plan['source_files'] if digest_file(output/LABELS[0]/name,deadline)!=digest_file(output/LABELS[1]/name,deadline)]
    if differences!=['system/fvSolution']:raise ValueError('Working arms differ beyond pressure relaxation')
    result={'status':'private_runtime_input_copy_QA_passed_no_solver','audit_script_sha256':digest_file(Path(__file__),deadline)['sha256'],
            'runtime_copy_helper_sha256':digest_file(Path(__file__).parent/'run_d3.py',deadline)['sha256'],
            'capsule_manifest_identity':digest_file(capsule/'capsule-manifest.json',deadline),
            'prepared_input_files_verified':len(manifest),'all64_working_MPI1020_seed_files_verified':len(files)==64,
            'both_serial1020_copies_verified':True,'working_arms_differences':differences,
            'native_MPI_seed_files':files,'working_protocols':protocols,'no_subprocess_solver_container_or_reconstruction_launched':True,
            'no_native1040_results_created':True,'elapsed_seconds':time.monotonic()-started,'physical_validation_established':False}
    report_file.write_text(json.dumps(result,indent=2)+'\n');print('D3 working-source copies and protocols independently checked; no process launched');return result


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ['root','prepared','previous','selections','capsule','output','report']:cli.add_argument(name,type=Path)
    a=cli.parse_args();audit(a.root,a.prepared,a.previous,a.selections,a.capsule,a.output,a.report)
