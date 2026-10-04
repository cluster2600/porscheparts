#!/usr/bin/env python3
"""Verify frozen prospective D1 configurations and reject sparse software fixtures."""
import hashlib,json,shutil,tempfile
from pathlib import Path
from summarize_d1_variability import compare,audit_case
CHECKS=['initial_time_matches_frozen_continuation','residual_p','residual_U','residual_turbulence','mass_balance','flow_stability','torque_stability','declared_flow_direction','complete_finite_fields','finite_measurements']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    manifest=json.loads((root/'parameters/D1-prepared-pair-manifest.json').read_text())
    def require(value,message):
        if not value:raise ValueError(message)
    require(set(manifest['branches'])=={'control','absolute'} and manifest['limits']=={'CPU':4,'GiB':5,'total_wall_seconds':600,'inner_MPI_seconds_each':270,'sequential_cases':2,'iterations_each':60},'Exactly two declared bounded branches required')
    require(not manifest['solver_started'] and not manifest['full_cases_materialized'],'D1 preparation must not claim a native run')
    for key,name in [('source_preparer_sha256','prepare_d1_configurations.py'),('prospective_variability_reporter_sha256','summarize_d1_variability.py'),('future_container_runner_sha256','run_d1_in_container.py'),('prospective_launcher_sha256','launch_d1_pair.py')]:
        require(manifest[key]==sha(root/'source'/name),'Prospective source identity differs')
    for label,record in manifest['branches'].items():
        for name,expected in record['files'].items():
            file=root/'parameters/D1-prepared-configurations'/label/name
            require(file.stat().st_size==expected['bytes'] and sha(file)==expected['sha256'],'Actual prepared configuration hash differs')
        protocol=json.loads((root/'parameters/D1-prepared-configurations'/label/'reference-protocol.json').read_text())
        require(protocol['expected_actual_solver_iterations']==list(range(901,961)) and protocol['required_admission_sample_iterations']==list(range(941,961)) and protocol['expected_cell_count']==453496,'Prospective native windows and cell identity')
        require(protocol['source_completed_fields_summary_sha256']==sha(root/'results/cfd/V2-fine-pressure015-900-summary.json'),'Native completed-field source identity')
        require(protocol['telemetry_write_interval_iterations']==1 and protocol['checkpoint_write_interval_iterations']==60,'Telemetry separate from checkpoints')
    contract=json.loads((root/'parameters/qualitative-subsystem-contract.json').read_text())
    require(not contract['CAD_generation_authorized_by_this_contract'] and not contract['third_party_images_published'] and not contract['absolute_scale_verified'],'Unmeasured visual contract boundary')
    for subsystem in contract['subsystems'].values():
        require(subsystem['functional_completion_blocked'] and all(value is None for value in subsystem['parameters'].values()) and all(value is None for interface in subsystem['required_interfaces'].values() for value in interface.values()),'Unknown dimensions/interfaces must remain unknown')
    # Native decomposePar uses this exact relative uniform directory link.
    with tempfile.TemporaryDirectory(prefix='fan-D1-uniform-link-') as directory:
        linkroot=Path(directory)
        for label in ['control','absolute']:
            (linkroot/label/'900/uniform').mkdir(parents=True)
            (linkroot/label/'900/uniform/time').write_text('software fixture900\n')
        (linkroot/'control/processor0/900').mkdir(parents=True)
        (linkroot/'control/processor0/900/uniform').symlink_to('../../900/uniform',target_is_directory=True)
        shutil.copytree(linkroot/'control/processor0',linkroot/'absolute/processor0',symlinks=True)
        require((linkroot/'absolute/processor0/900/uniform').is_symlink() and (linkroot/'absolute/processor0/900/uniform/time').read_bytes()==(linkroot/'control/processor0/900/uniform/time').read_bytes(),'Native uniform symlink clone regression')
    # Synthetic rows exercise future software guards, never solver/physical evidence.
    with tempfile.TemporaryDirectory(prefix='fan-D1-software-fixture-') as directory:
        work=Path(directory)
        for label in ['control','absolute']:
            case=work/label;shutil.copytree(root/'parameters/D1-prepared-configurations'/label,case)
            (case/'partition-preparation.json').write_text(json.dumps({'all_initial_processor_files_hashes_match':True,'shared_partition_sha256':'SOFTWARE_FIXTURE_NOT_NATIVE'}))
            log=[]
            for time in range(901,961):
                log+=['Time = '+str(time)]+['Solving for p, Initial residual = 5e-5, Final residual = 1e-8, No Iterations 3']*3+['time step continuity errors : sum local = 1e-7, global = 1e-8']
            (case/'log.foamRun').write_text('\n'.join(log)+'\nEnd\n')
            for name in ['inletFlow','outletFlow','rotorForces']:
                folder=case/'postProcessing'/name/'900';folder.mkdir(parents=True);rows=[]
                for time in range(900,961):
                    row=[time,-1 if name=='inletFlow' else 1] if name!='rotorForces' else [time]+[0]*8+[-4]+[0]*3
                    rows.append(' '.join(map(str,row)))
                (folder/('forces.dat' if name=='rotorForces' else 'surfaceFieldValue.dat')).write_text('\n'.join(rows)+'\n')
            files=[case/'log.foamRun',case/'reference-protocol.json',*case.glob('postProcessing/*/900/*.dat')]
            summary={'software_fixture_not_solver_result':True,'status':'reference_pilot_admitted_numerically','contiguous_measurement_window_verified':True,'native_window_sample_count':20,'iterations_completed':960,'criteria_checks':{name:True for name in CHECKS},'final_field_cell_counts':{name:453496 for name in ['U','p','k','omega','nut']},'file_sha256':{str(file.relative_to(case)):sha(file) for file in files}}
            (case/'flow-summary.json').write_text(json.dumps(summary))
        args=[work/'control',work/'absolute',work/'control/flow-summary.json',work/'absolute/flow-summary.json',work/'SOFTWARE_FIXTURE_REPORT.json']
        report=compare(*args)
        require(report['both_original_frozen_flow_gates_passed'] and not report['historical_fine_admission_restored'],'Synthetic complete-window positive control')
        summary_file=work/'absolute/flow-summary.json';summary=json.loads(summary_file.read_text());original_summary=summary_file.read_text();summary['criteria_checks']={};summary_file.write_text(json.dumps(summary))
        require(not audit_case(work/'absolute',summary_file)['current_original_frozen_gates_passed'],'Empty criterion set must not establish admission')
        summary_file.write_text(original_summary)
        sparse=work/'absolute/postProcessing/outletFlow/900/surfaceFieldValue.dat';original=sparse.read_text();lines=original.splitlines();sparse.write_text('\n'.join([lines[0],lines[-1]])+'\n')
        try:audit_case(work/'absolute',summary_file)
        except ValueError as error:require('Insufficient native samples' in str(error),'Sparse-window rejection reason')
        else:raise ValueError('Sparse synthetic rows incorrectly accepted')
        sparse.write_text(original)
        file=work/'absolute/system/controlDict';file.write_text(file.read_text().replace('endTime 960','endTime 961'))
        try:compare(*args)
        except ValueError as error:require('Paired discretization/control differs' in str(error),'Paired-mismatch rejection reason')
        else:raise ValueError('Mismatched paired configuration accepted')
    print('D1 configuration identities and software fixture guards passed; checker launches no solver')

if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
