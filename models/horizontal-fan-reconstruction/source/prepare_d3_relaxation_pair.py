#!/usr/bin/env python3
"""Prepare two equal-work native1020 restarts; no solver, Docker or SSH action."""
import argparse,hashlib,json,os,re,shutil,time
from pathlib import Path
from prepare_d2_restart1000 import identity


def changed_system(control,solution,alpha):
    if alpha not in (.15,.05):raise ValueError('Only the declared relaxation contrast is allowed')
    for key,old,new in [('startTime',1000,1020),('endTime',1020,1040)]:
        control,count=re.subn(r'\b'+key+r'\s+'+str(old)+r'\s*;',key+' '+str(new)+';',control)
        if count!=1:raise ValueError('Unexpected preserved native control: '+key)
    if not re.search(r'\bstartFrom\s+startTime\s*;',control) or not re.search(r'\bwriteInterval\s+20\s*;',control):
        raise ValueError('Fixed restart/checkpoint cadence required')
    solution,count=re.subn(r'(relaxationFactors\s*\{\s*fields\s*\{\s*p\s+)0\.15(\s*;)',lambda m:m[1]+str(alpha)+m[2],solution)
    if count!=1:raise ValueError('Unexpected preserved pressure relaxation')
    return control,solution


def prepare(root,native,output):
    start=time.monotonic();record=json.loads((root/'results/runtime/D2-completion-native-archive-verification.json').read_text())
    previous=json.loads((root/'parameters/D2-restart1000-protocol.json').read_text())
    source=(native/'extended').resolve(strict=True);output=output.resolve()
    if output.exists() or output==source or source in output.parents or output in source.parents:raise ValueError('New separate private output required')
    expected={name.removeprefix('extended/'):value for name,value in record['members'].items()
              if name.startswith(('extended/constant/','extended/system/')) or re.match(r'^extended/processor[0-3]/(?:constant/|1020/)',name)}
    actual={str(f.relative_to(source)) for base in [source/'constant',source/'system',*[source/f'processor{rank}'/name for rank in range(4) for name in ['constant','1020']]] for f in base.rglob('*') if f.is_file()}
    if actual!=set(expected):raise ValueError('Frozen mesh/config/native1020 inventory differs')
    for name,entry in expected.items():
        if identity(source/name)!=entry:raise ValueError('Native archive source changed: '+name)
    seeds={name:entry for name,entry in expected.items() if '/1020/' in name}
    if len(seeds)!=32:raise ValueError('All28 native fields and four time markers required')
    output.mkdir(parents=True);cases={}
    for label,alpha in [('control015',.15),('candidate005',.05)]:
        case=output/label;case.mkdir()
        for name,entry in expected.items():
            dest=case/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
            if identity(dest)!=entry:raise ValueError('Native copy changed')
        control,solution=changed_system((source/'system/controlDict').read_text(),(source/'system/fvSolution').read_text(),alpha)
        (case/'system/controlDict').write_text(control);(case/'system/fvSolution').write_text(solution)
        cases[label]={'pressure_relaxation':alpha,'native_MPI_seed_files':seeds,
                      'system_files':{name:identity(case/'system'/name) for name in ['controlDict','fvSolution','fvSchemes','decomposeParDict','topoSetDict']}}
    differences=[]
    for name in expected:
        if identity(output/'control015'/name)!=identity(output/'candidate005'/name):differences.append(name)
    if differences!=['system/fvSolution']:raise ValueError('Only pressure relaxation may differ between arms')
    stationarity=dict(previous['additional_stationarity_screen'])
    stationarity['checkpoint1020_to1040_core_pressure_volume_RMS_Pa_max']=stationarity.pop('checkpoint1000_to1020_core_pressure_volume_RMS_Pa_max')
    stationarity['checkpoint1020_to1040_core_velocity_volume_RMS_m_s_max']=stationarity.pop('checkpoint1000_to1020_core_velocity_volume_RMS_m_s_max')
    plan={'protocol_id':'D3-1020-relaxation-contrast20-each','status':'private_native_pair_prepared_not_launched',
          'preparer_sha256':identity(Path(__file__))['sha256'],
          'dependencies_sha256':{'prepare_d2_restart1000.py':identity(Path(__file__).parent/'prepare_d2_restart1000.py')['sha256']},
          'diagnostic_report_sha256':identity(root/'results/cfd/D2-establishment-diagnostic.json')['sha256'],
          'source_archive_sha256':record['archive_identity']['sha256'],
          'source_archive_verification_sha256':identity(root/'results/runtime/D2-completion-native-archive-verification.json')['sha256'],
          'source_files':expected,'cases':cases,'native_seed_identity_equal_between_arms':True,
          'case_differences':differences,'restart_iteration':1020,'first_iteration':1021,'target_iteration':1040,
          'new_iterations_per_case':20,'solver_count_max':2,'cases_run_sequentially':True,
          'ranks':4,'cells':680596,'rank_cells':previous['rank_cells'],
          'required_final_native_window':[1021,1040],'previous_native_window':[1001,1020],
          'original_numerical_acceptance_all_required':previous['original_numerical_acceptance_all_required'],
          'additional_stationarity_screen':stationarity,
          'unchanged':['geometry','native_partition','1020_fields','boundary_conditions','6000rpm_MRF','kOmegaSST','fvSchemes','GAMG_relTol0p01','U_k_omega_relaxation0p5','common_selections'],
          'budget_requires_resource_coordination_before_launch':{'aggregate_wall_cap_seconds':360,'CPU_max':4,
             'RAM_and_swap_limit_bytes':5*1024**3,'minimum_native_memory_available_bytes':7*1024**3,
             'phase_caps_seconds':{'setup':30,'control_solver':90,'candidate_solver':90,'reconstruction':40,'analysis':45,'preservation':60,'release':5},
             'single_global_deadline_from_initial_launcher':True,'network':'none','existing_image_only':True},
          'prospective_owned_solver_commands':['mpirun -np 4 foamRun -parallel -case /run/control015','mpirun -np 4 foamRun -parallel -case /run/candidate005'],
          'future_supervised_launcher_admitted':False,
          'no_solver_container_or_reconstruction_launched':True,
          'no_automatic_extension_or_retry':True,'raw_scan_or_native_fields_published':False,
          'physical_transient_demonstrated':False,'physical_validation_established':False,
          'elapsed_preparation_seconds':time.monotonic()-start}
    (output/'preparation-report.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'status':plan['status'],'native_seed_files_per_case':len(seeds),'case_differences':differences,'elapsed_seconds':plan['elapsed_preparation_seconds']}));return plan


if __name__=='__main__':
    os.nice(15);cli=argparse.ArgumentParser(description=__doc__)
    for arg in ['root','native','output']:cli.add_argument(arg,type=Path)
    a=cli.parse_args();prepare(a.root,a.native,a.output)
