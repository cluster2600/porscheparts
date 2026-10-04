#!/usr/bin/env python3
"""Prepare exactly two D1 configuration branches; never launch or copy a mesh."""
import argparse,copy,hashlib,json,re,shutil
from pathlib import Path
from measurement_window import configure_measurement_cadence


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source,identity_path,output):
    identity=json.loads(identity_path.read_text())
    for name,record in identity['files'].items():
        if (source/name).stat().st_size!=record['bytes'] or sha(source/name)!=record['sha256']:
            raise ValueError('Native source identity differs: '+name)
    old=json.loads((source/'reference-protocol.json').read_text())
    gate=json.loads((source/'independent-mesh-gate.json').read_text())
    if old['iterations']!=900 or not gate['accepted_for_bounded_pilot']:
        raise ValueError('Frozen900 checkpoint and both mesh gates required')
    if not all('900/'+name in identity['checkpoint_files'] for name in ['U','p','k','omega','nut','phi','Uf']):
        raise ValueError('Complete native900 restart state required')
    output.mkdir(exist_ok=False)
    records={}
    for label,reltol in [('control',.01),('absolute',0.0)]:
        branch=output/label;shutil.copytree(source/'system',branch/'system')
        control=configure_measurement_cadence((source/'system/controlDict').read_text(),60)
        control,n=re.subn(r'\bendTime\s+900\s*;','endTime 960;',control)
        if n!=1 or 'startFrom latestTime;' not in control:raise ValueError('Exact900-to960 restart required')
        (branch/'system/controlDict').write_text(control)
        original=(source/'system/fvSolution').read_text()
        match=re.search(r'\bp\s*\{([^{}]*)\}',original)
        if not match or not re.search(r'\btolerance\s+1e-8\s*;',match[1]):raise ValueError('Original pressure tolerance differs')
        if not re.search(r'fields\s*\{\s*p\s+0\.15\s*;',original):raise ValueError('Original pressure relaxation differs')
        body,n=re.subn(r'\brelTol\s+\.01\s*;','relTol '+format(reltol,'.8g')+';',match[0])
        if n!=1:raise ValueError('Exactly one original pressure relTol required')
        solution=original[:match.start()]+body+original[match.end():]
        (branch/'system/fvSolution').write_text(solution)
        for dictionary in (branch/'system').iterdir():
            if dictionary.is_file():dictionary.write_text(dictionary.read_text().rstrip()+'\n')
        protocol=copy.deepcopy(old)
        protocol.update(protocol_id='D1-V2-900-'+label,iterations=960,initial_fields_sha256={n:r['sha256'] for n,r in identity['checkpoint_files'].items()},previous_frozen_protocol_sha256=sha(source/'reference-protocol.json'),previous_target_iteration=900,planned_total_target=960,planned_phase_end_iterations=[960],wall_timeout_seconds=300,maximum_CPU=4,maximum_memory_GiB=5,additional_phase_reason='Prospective paired linear-pressure-solve discriminator; no automatic continuation',numerical_pressure_relaxation_before=.15,numerical_pressure_relaxation_after=.15,numerical_pressure_relTol=reltol,pressure_absolute_tolerance=1e-8,telemetry_write_interval_iterations=1,checkpoint_write_interval_iterations=60,expected_actual_solver_iterations=list(range(901,961)),required_admission_sample_iterations=list(range(941,961)),global_pair_wall_cap_seconds=600,inner_MPI_wall_cap_seconds=270,shared_MPI_partition_required=True,prepared_before_launch=True,not_launched=True)
        protocol['frozen_system_file_sha256']={str(f.relative_to(branch)):sha(f) for f in (branch/'system').iterdir() if f.is_file()}
        protocol['expected_cell_count']=identity['expected_cell_count']
        protocol['source_completed_fields_summary_sha256']=identity['source_completed_fields_summary_sha256']
        protocol['prospective_iteration_variability_screen']={'windows':[list(range(a,a+20)) for a in [901,921,941]],'quantities':['Qin','Qout','total_fluid_on_rotor_torque','p_initial_residual_max','p_final_linear_residual_max','continuity_global'],'statistics':['mean','standard_deviation','minimum','maximum','relative_standard_deviation_if_nonzero_mean'],'interpretation':'Deterministic steady-iteration variability only; not stochastic noise, independent samples, physical frequency or a confidence interval. No threshold inferred from sparse historical fine tables.','paired_difference':'Report difference of last20 means relative to control and both within-window CVs descriptively; no significance or installed-performance ranking.'}
        (branch/'reference-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
        for name in ['preparation.json','independent-mesh-gate.json']:shutil.copyfile(source/name,branch/name)
        records[label]={'relTol':reltol,'files':{str(f.relative_to(branch)):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(branch.rglob('*')) if f.is_file()}}
    if (output/'control/system/controlDict').read_bytes()!=(output/'absolute/system/controlDict').read_bytes():raise ValueError('Control dictionaries must match')
    pair={'status':'exact_two_branch_configurations_prepared_not_launched','source_identity_sha256':sha(identity_path),'script_sha256':sha(Path(__file__)),'source_files':identity['files'],'initial_checkpoint_files':identity['checkpoint_files'],'constant_files':identity['constant_files'],'branches':records,'only_paired_numerical_difference':'Pressure GAMG relTol0.01 vs0; same absolute tolerance1e-8, relaxation0.15, mesh, restart, physical BCs and original acceptance criteria','future_materialization':'After coordinated resource release only, copy the declared native constant/900 state into fresh owned cases; verify every hash, decompose once and clone that initial partition for both branches. Preparation/copy, solves, reconstruction and telemetry audits are inside the600s pair cap.','limits':{'CPU':4,'GiB':5,'total_wall_seconds':600,'inner_MPI_seconds_each':270,'sequential_cases':2,'iterations_each':60},'solver_started':False,'physical_validation_established':False}
    (output/'pair-manifest.json').write_text(json.dumps(pair,indent=2)+'\n')
    print('Prepared two configuration branches only; solver launch remains blocked by resource coordination')
    return pair

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('native_small_source',type=Path);a.add_argument('source_identity',type=Path);a.add_argument('output',type=Path);v=a.parse_args();prepare(v.native_small_source,v.source_identity,v.output)
