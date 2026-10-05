#!/usr/bin/env python3
"""D3 two-arm fixed20/deadline/isolation guards; no host or solver mutations."""
import json,re,time
from pathlib import Path
from d2_completion_guards import IMAGE,remaining,digest_file,archive_private,inspect_limits as inspect_d2_limits

GLOBAL_CAP=360
LABELS=('control015','candidate005')
PHASES={'setup':30,'control_solver':90,'candidate_solver':90,'reconstruction':40,'analysis':45,'preservation':60,'release':5}
NUMERICAL={'last_window_iterations':20,'maximum_initial_residual_p':.0001,'maximum_initial_residual_U_components':1e-5,
           'maximum_initial_residual_k_and_omega':.0001,'maximum_absolute_inlet_plus_outlet_flow_over_mean_absolute_flow':.005,
           'maximum_flow_relative_standard_deviation':.01,'maximum_rotor_torque_relative_standard_deviation':.02,
           'flow_direction_matches_declared_reference':True,'fields_finite_and_complete':True}
STATIONARITY={'last_two20_windows_required':True,'last_window_common_flow_CV_max':.01,'last_window_common_pressure_std_Pa_max':2,
              'between_last_two_window_mean_common_flow_relative_max':.01,'between_last_two_window_mean_torque_relative_max':.02,
              'between_last_two_window_mean_pressure_difference_Pa_max':2,'local_wake_p99_and_max_must_be_reported':True,
              'local_field_qualification_established_by_bulk_gates':False,'checkpoint1020_to1040_core_pressure_volume_RMS_Pa_max':1,
              'checkpoint1020_to1040_core_velocity_volume_RMS_m_s_max':.1}


def validate_plan(plan):
    if (plan['restart_iteration'],plan['first_iteration'],plan['target_iteration'],plan['new_iterations_per_case'],plan['solver_count_max'],plan['cases_run_sequentially'])!=(1020,1021,1040,20,2,True):
        raise ValueError('Only the fixed native1020 two-arm20-iteration diagnostic is allowed')
    if tuple(plan['cases'])!=LABELS or [plan['cases'][name]['pressure_relaxation'] for name in LABELS]!=[.15,.05]:raise ValueError('Frozen pressure relaxation contrast required')
    if (plan['cells'],plan['ranks'],plan['rank_cells'])!=(680596,4,[122709,167115,208232,182540]):raise ValueError('Original mesh and four native partitions required')
    if plan['original_numerical_acceptance_all_required']!=NUMERICAL or plan['additional_stationarity_screen']!=STATIONARITY:raise ValueError('Original numerical and stationarity thresholds must not change')
    if plan['cases'][LABELS[0]]['native_MPI_seed_files']!=plan['cases'][LABELS[1]]['native_MPI_seed_files'] or len(plan['cases'][LABELS[0]]['native_MPI_seed_files'])!=32:raise ValueError('Identical complete32 native seeds required')
    b=plan['budget_requires_resource_coordination_before_launch']
    if (b['aggregate_wall_cap_seconds'],b['CPU_max'],b['RAM_and_swap_limit_bytes'],b['minimum_native_memory_available_bytes'],b['phase_caps_seconds'],b['network'])!=(360,4,5*1024**3,7*1024**3,PHASES,'none'):raise ValueError('Frozen global resource/phase caps differ')
    if not plan['no_automatic_extension_or_retry'] or not plan['no_solver_container_or_reconstruction_launched']:raise ValueError('Preparation must not imply execution or retries')


def check_complete20(log):
    blocks=re.split(r'(?m)^Time = ',log)[1:]
    values=[float(re.match(r'([0-9.eE+-]+)',b)[1]) for b in blocks]
    if any(value!=int(value) for value in values):raise ValueError('Integer SIMPLE bookkeeping steps required')
    steps=[int(value) for value in values]
    completed=[n for n,b in zip(steps,blocks) if re.search(r'ExecutionTime = [0-9.eE+-]+ s\s+ClockTime = ',b)]
    if steps!=list(range(1021,1041)) or completed!=steps or not re.search(r'(?m)^End\s*$',log) or 'FOAM FATAL' in log:raise ValueError('Exactly20 complete steps1021-to1040 and End required')
    return steps


def verify_manifest(root,manifest,deadline,excluded=()):
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and str(p.relative_to(root)) not in excluded}
    if actual!=set(manifest):raise ValueError('Frozen inventory differs')
    for name,record in manifest.items():
        path=root/name
        if path.is_symlink() or digest_file(path,deadline)!=record:raise ValueError('Frozen input changed: '+name)


def container_command(name,prepared,previous,selections,capsule,output,uid,gid,release,deadline):
    if not re.fullmatch(r'fan-d3-[a-z0-9-]+',name) or not release.strip() or any(c in release for c in ['\n','\r','\x00']):raise ValueError('Owned name and single-line coordinated release required')
    args=['docker','run','--name',name,'--pull=never','--rm','--network','none','--cpus','4','--cpuset-cpus','0,2,4,5',
          '--memory','5g','--memory-swap','5g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(uid)+':'+str(gid)]
    for value in ['OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','PYTHONDONTWRITEBYTECODE=1','FAN_D3_RELEASE='+release,'FAN_D3_DEADLINE='+str(deadline)]:args+=['--env',value]
    for source,target in [(prepared,'/prepared'),(previous,'/previous'),(selections,'/selections.npz'),(capsule,'/capsule')]:args+=['--mount','type=bind,source='+str(source)+',target='+target+',readonly']
    args+=['--mount','type=bind,source='+str(output)+',target=/run',IMAGE,'bash','-c','source /opt/openfoam13/etc/bashrc; exec python3 -B /capsule/source/run_d3.py']
    return args


def inspect_limits(data,uid,gid):
    result=inspect_d2_limits(data,uid,gid)
    if set(result['mounts_read_only'])!={'/prepared','/previous','/selections.npz','/capsule','/run'} or data['HostConfig'].get('Privileged',False):raise ValueError('Unexpected source/output mount or privileged container')
    return result


def phase_deadline(global_deadline,cap,reserve,now=None):
    now=time.monotonic() if now is None else now
    remaining(global_deadline,reserve,now)
    return min(now+cap,global_deadline-reserve)


def active_native_jobs(proc_root):
    found=[]
    for proc in proc_root.iterdir():
        if not proc.name.isdigit():continue
        try:
            executable=(proc/'comm').read_text().strip().lower()
            if executable in ['foamrun','checkmesh','reconstructpar','decomposepar','gmsh'] or executable.startswith(('ccx','calculix')):found.append(proc.name)
        except (OSError,ProcessLookupError):pass
    return found
