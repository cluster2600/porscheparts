#!/usr/bin/env python3
"""Execute one owned D1 pair inside the approved isolated container, after release."""
import argparse,hashlib,json,os,resource,shutil,subprocess,sys,time
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(native,configs,output):
    started=time.monotonic();deadline=started+570
    if sys.platform!='linux' or not Path('/opt/openfoam13').is_dir():raise ValueError('Existing Foundation13 container runtime required')
    if not os.environ.get('FAN_D1_COORDINATED_RELEASE'):raise ValueError('Coordinator resource release must be supplied before execution')
    os.nice(10)
    manifest=json.loads((configs/'pair-manifest.json').read_text())
    if manifest.get('future_container_runner_sha256')!=sha(Path(__file__)):raise ValueError('Frozen D1 runner identity differs')
    if manifest['solver_started'] or manifest['limits']!={'CPU':4,'GiB':5,'total_wall_seconds':600,'inner_MPI_seconds_each':270,'sequential_cases':2,'iterations_each':60}:raise ValueError('Exact prepared limits required')
    for name,record in {**manifest['source_files'],**manifest['initial_checkpoint_files'],**manifest['constant_files']}.items():
        if (native/name).stat().st_size!=record['bytes'] or sha(native/name)!=record['sha256']:raise ValueError('Native source changed: '+name)
    output.mkdir(exist_ok=False)
    cases={}
    for label in ['control','absolute']:
        case=output/label;case.mkdir();cases[label]=case
        for name in ['constant','900']:shutil.copytree(native/name,case/name)
        for name,record in {**manifest['initial_checkpoint_files'],**manifest['constant_files']}.items():
            if (case/name).stat().st_size!=record['bytes'] or sha(case/name)!=record['sha256']:raise ValueError('Copied native restart differs')
        for name,record in manifest['branches'][label]['files'].items():
            source=configs/label/name
            if source.stat().st_size!=record['bytes'] or sha(source)!=record['sha256']:raise ValueError('Prepared configuration changed')
            dest=case/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    commands=[]
    def command(case,args,log,cap):
        remaining=int(deadline-time.monotonic())
        if remaining<=5:raise TimeoutError('D1 pair deadline reached; no continuation')
        owned_cap=min(cap,remaining-5);t=time.monotonic()
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
        with (case/log).open('x') as stream:
            result=subprocess.run(['timeout','--signal=TERM','--kill-after=5',str(owned_cap),*args],cwd=case,env=env,stdout=stream,stderr=subprocess.STDOUT)
        commands.append({'case':case.name,'command':args,'wall_cap_seconds':owned_cap,'wall_seconds':time.monotonic()-t,'exit_status':result.returncode})
        if result.returncode:raise RuntimeError('Owned D1 command failed; no retry: '+log)
    partition_sha=None
    try:
        command(cases['control'],['decomposePar','-latestTime'],'log.decomposePar',60)
        for index in range(4):shutil.copytree(cases['control']/('processor'+str(index)),cases['absolute']/('processor'+str(index)))
        partitions={}
        for label,case in cases.items():
            partitions[label]={str(f.relative_to(case)):sha(f) for index in range(4) for f in sorted((case/('processor'+str(index))).rglob('*')) if f.is_file()}
        if partitions['control']!=partitions['absolute']:raise ValueError('Exactly identical initial MPI partition required')
        partition_sha=hashlib.sha256(json.dumps(partitions['control'],sort_keys=True).encode()).hexdigest()
        record={'status':'native_initial_MPI_partition_identical_before_either_solve','shared_partition_sha256':partition_sha,'all_initial_processor_files_hashes_match':True,'source_checkpoint_sha256':{n:r['sha256'] for n,r in manifest['initial_checkpoint_files'].items()},'files':partitions['control']}
        for case in cases.values():(case/'partition-preparation.json').write_text(json.dumps(record,indent=2)+'\n')
        code=Path(__file__).resolve().parent
        for case in cases.values():
            command(case,['mpirun','--bind-to','none','--use-hwthread-cpus','-np','4','foamRun','-parallel'],'log.foamRun',270)
            command(case,['reconstructPar','-latestTime'],'log.reconstructPar',40)
            command(case,[sys.executable,str(code/'summarize_reference_flow.py'),str(case),str(case/'flow-summary.json')],'log.summary',30)
        command(output,[sys.executable,str(code/'summarize_d1_variability.py'),str(cases['control']),str(cases['absolute']),str(cases['control']/'flow-summary.json'),str(cases['absolute']/'flow-summary.json'),str(output/'D1-variability.json')],'log.variability',20)
    finally:
        (output/'execution-receipt.json').write_text(json.dumps({'commands':commands,'wall_seconds':time.monotonic()-started,'owned_case_pair_only':True,'no_automatic_retry_or_continuation':True,'coordinated_release':os.environ['FAN_D1_COORDINATED_RELEASE'],'shared_initial_partition_sha256':partition_sha,'peak_child_RSS_KiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'native_source_read_only_by_container_mount_required':True,'physical_validation_established':False},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['native','configs','output']:p.add_argument(name,type=Path)
    a=p.parse_args();execute(a.native,a.configs,a.output)
