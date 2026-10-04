#!/usr/bin/env python3
"""One bounded current/extended outlet comparison; gates before any flow solve."""
import json,os,re,resource,subprocess,sys,time
from pathlib import Path
import numpy as np
from append_outlet_prisms import prepare_pair,sha,body
from analyze_flow_balance import field_values,patch_block
from summarize_reference_flow import summarize


def run(source,capsule,selections,output):
    started=time.monotonic();deadline=float(os.environ['FAN_D2_DEADLINE_MONOTONIC']);release=os.environ['FAN_D2_COORDINATED_RELEASE'];os.nice(10)
    if sys.platform!='linux' or not Path('/opt/openfoam13').is_dir() or not release.strip():raise ValueError('Coordinated existing runtime required')
    commands=[];status='failed_or_partial';error=None;phase='preparation';mesh_deadline=min(deadline,time.monotonic()+120)
    def command(case,args,log,cap,end=None,allow_failure=False):
        remaining=min(deadline-10,end if end is not None else deadline-10)-time.monotonic()
        if remaining<2:raise TimeoutError('Frozen global/stage budget exhausted')
        limit=min(cap,max(1,int(remaining)));t=time.monotonic()
        with (case/log).open('x') as f:code=subprocess.run(['timeout','--signal=TERM','--kill-after=3',str(limit),*args],cwd=case,stdout=f,stderr=subprocess.STDOUT).returncode
        commands.append({'case':case.name,'args':args,'log':log,'exit_status':code,'wall_cap_seconds':limit,'wall_seconds':time.monotonic()-t})
        if code and not allow_failure:raise RuntimeError('Owned command failed: '+case.name+'/'+log)
        return code
    try:
        output.mkdir(parents=True,exist_ok=False)
        prepare_pair(source,output,capsule,selections)
        for label in ['current','extended']:
            case=output/label
            command(case,['checkMesh'],'log.checkMesh-standard',25,mesh_deadline,True)
            command(case,['checkMesh','-allGeometry','-allTopology'],'log.checkMesh-extended',35,mesh_deadline,True)
            checks={}
            for name in ['log.checkMesh-standard','log.checkMesh-extended']:
                text=(case/name).read_text();failed=re.search(r'Failed\s+(\d+)\s+mesh checks',text);checks[name]={'Mesh_OK':'Mesh OK' in text,'failed_checks':int(failed[1]) if failed else 0,'sha256':sha(case/name)}
            gate={'accepted_for_bounded_pilot':all(x['Mesh_OK'] and x['failed_checks']==0 for x in checks.values()),'checks':checks,'flow_solver_launched':False,'thresholds_unchanged':True,'physical_validation_established':False}
            (case/'independent-mesh-gate.json').write_text(json.dumps(gate,indent=2)+'\n')
            if not gate['accepted_for_bounded_pilot']:raise ValueError('Independent mesh gate rejected '+label)
        phase='functionObject_seed_checks'
        expected=json.loads((capsule/'configs/diagnostic.json').read_text())['common_zones'];seed_records={}
        for label in ['current','extended']:
            case=output/label;command(case,['foamPostProcess','-solver','incompressibleFluid','-time','960'],'log.seed-functions',20)
            pp=case/'postProcessing';checks={}
            for zone,record in expected.items():
                files=list((pp/(zone+'Mean')).glob('*/*.dat'))
                if len(files)!=1:raise ValueError('Missing seed cellZone functionObject '+zone)
                rows=np.loadtxt(files[0],comments='#',ndmin=2);errorPa=abs(rows[-1,1]*1.2-record['consistent960_volume_mean_p_Pa']);checks[zone]={'pressure_Pa':float(rows[-1,1]*1.2),'absolute_seed_pressure_error_Pa':float(errorPa),'sha256':sha(files[0])}
                if rows[-1,0]!=960 or errorPa>1e-5:raise ValueError('Common pressure seed statistic differs')
            files=list((pp/'commonOutletFlux').glob('*/*.dat'));rows=np.loadtxt(files[0],comments='#',ndmin=2);phi=field_values(patch_block((source/'960/phi').read_text(),'outlet'),'value',4542,1);checks['flow']={'common_seed_Q_m3_s':float(rows[-1,1]),'native_seed_Q_m3_s':float(phi.sum()),'sha256':sha(files[0])}
            if len(files)!=1 or abs(rows[-1,1]-phi.sum())>1e-8:raise ValueError('Oriented common seed flux differs')
            seed_records[label]=checks
        (output/'seed-observables-verification.json').write_text(json.dumps({'status':'passed_without_solver_iterations','cases':seed_records,'statistics_identical_to_private_seed':True},indent=2)+'\n')
        for label,cap in [('current',180),('extended',300)]:
            case=output/label;phase=label+'_decomposition'
            command(case,['decomposePar','-latestTime'],'log.decomposePar',35)
            expected_proc=np.fromstring(body(case/'constant/manualCellProc')[1],sep=' ',dtype=np.int64);counts=[]
            for rank in range(4):
                addressing=np.fromstring(body(case/('processor'+str(rank))/'constant/polyMesh/cellProcAddressing')[1],sep=' ',dtype=np.int64)
                if not np.array_equal(addressing,np.flatnonzero(expected_proc==rank)):raise ValueError('Exact manual core MPI mapping differs')
                link=case/('processor'+str(rank))/'960/uniform'
                if link.is_symlink() and not link.exists():raise ValueError('Broken uniform link refused')
                counts.append(len(addressing))
            (case/'partition-verification.json').write_text(json.dumps({'exact_manual_assignment_verified':True,'rank_cells':counts,'manual_assignment_sha256':sha(case/'constant/manualCellProc'),'core_assignment_preserved':True},indent=2)+'\n')
            phase=label+'_solver';command(case,['mpirun','--bind-to','none','--use-hwthread-cpus','-np','4','foamRun','-parallel'],'log.foamRun',cap)
            times=[int(float(x)) for x in re.findall(r'(?m)^Time = ([0-9.eE+-]+)',(case/'log.foamRun').read_text())]
            if times!=list(range(961,1021)) or 'End' not in (case/'log.foamRun').read_text():raise ValueError('Exactly60 native solver iterations required')
            phase=label+'_reconstruction';command(case,['reconstructPar','-time','980,1000,1020'],'log.reconstructPar',35)
            summarize(case,case/'flow-summary.json')
        phase='comparison';from analyze_d2_result import analyze
        analyze(output,capsule/'configs/protocol.json',output/'comparison.json')
        status='completed_exact_pair'
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
        if output.exists():(output/'failure.json').write_text(json.dumps({'status':'incomplete_no_retry','phase':phase,'error':error,'no_additional_iterations_or_extension':True},indent=2)+'\n')
    finally:
        output.mkdir(parents=True,exist_ok=True)
        receipt={'status':status,'phase':phase,'error':error,'commands':commands,'wall_seconds':time.monotonic()-started,'coordinated_release':release,'exact_distance_m':.275,'exact_layers':50,'maximum_new_cases':2,'maximum_iterations_each':60,'no_retry_or_continuation':True,'child_peak_RSS_KiB_not_aggregate':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'physical_validation_established':False}
        (output/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if status=='completed_exact_pair' else 2


if __name__=='__main__':raise SystemExit(run(Path('/native'),Path('/capsule'),Path('/selections.npz'),Path('/run/cases')))
