#!/usr/bin/env python3
"""Execute one coordinated coupling branch from preserved native900 partition."""
import hashlib,json,os,resource,shutil,subprocess,sys,time
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(native,baseline,capsule,output):
    started=time.monotonic();deadline=float(os.environ['FAN_D1C_DEADLINE_MONOTONIC'])
    release=os.environ['FAN_D1C_COORDINATED_RELEASE']
    if sys.platform!='linux' or not Path('/opt/openfoam13').is_dir() or not release.strip():raise ValueError('Existing runtime and coordinated release required')
    os.nice(10)
    frozen=json.loads((capsule/'configs/D1-source-manifest.json').read_text())
    proposal=json.loads((capsule/'configs/proposed-protocol.json').read_text())
    if proposal['new_cases']!=1 or proposal['expected_new_iterations']!=list(range(901,961)):raise ValueError('Exactly one60-iteration branch required')
    source_index={**frozen['initial_checkpoint_files'],**frozen['constant_files']}
    commands=[];partition_sha=None;case=output/'consistent';case.mkdir(parents=True,exist_ok=False)
    def command(args,log,cap):
        remaining=deadline-time.monotonic()
        if remaining<=5:raise TimeoutError('Global budget exhausted; no continuation')
        owned_cap=min(cap,max(1,int(remaining-5)));t=time.monotonic()
        with (case/log).open('x') as stream:
            r=subprocess.run(['timeout','--signal=TERM','--kill-after=5',str(owned_cap),*args],cwd=case,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),stdout=stream,stderr=subprocess.STDOUT)
        commands.append({'command':args,'wall_cap_seconds':owned_cap,'wall_seconds':time.monotonic()-t,'exit_status':r.returncode})
        if r.returncode:raise RuntimeError('Owned command failed; no automatic retry: '+log)
    try:
        for name,record in source_index.items():
            file=native/name
            if file.stat().st_size!=record['bytes'] or sha(file)!=record['sha256']:raise ValueError('Native900 or constant identity differs')
        for folder in ['constant','900']:shutil.copytree(native/folder,case/folder,symlinks=True)
        for name,record in source_index.items():
            file=case/name
            if file.stat().st_size!=record['bytes'] or sha(file)!=record['sha256']:raise ValueError('Copied native identity differs')
        shutil.copytree(capsule/'configs/consistent/system',case/'system')
        for name in ['reference-protocol.json','independent-mesh-gate.json']:shutil.copyfile(capsule/'configs/consistent'/name,case/name)
        before=(capsule/'configs/control-fvSolution').read_text();after=(case/'system/fvSolution').read_text()
        if after!=before.replace('consistent no;','consistent yes;') or sha(case/'system/fvSolution')!=proposal['candidate_fvSolution_sha256']:raise ValueError('Single declared coupling difference required')
        expected=json.loads((baseline/'partition-preparation.json').read_text())
        for index in range(4):
            processor=case/('processor'+str(index));processor.mkdir()
            for folder in ['constant','900']:shutil.copytree(baseline/processor.name/folder,processor/folder,symlinks=True)
            link=processor/'900/uniform'
            if not link.is_symlink() or os.readlink(link)!='../../900/uniform':raise ValueError('Exact native uniform link required')
        actual={str(f.relative_to(case)):sha(f) for index in range(4) for f in sorted((case/('processor'+str(index))).rglob('*')) if f.is_file()}
        partition_sha=hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest()
        if actual!=expected['files'] or partition_sha!=proposal['shared_initial_MPI_partition_sha256']:raise ValueError('Preserved initial MPI partition differs')
        (case/'partition-preparation.json').write_text(json.dumps({'status':'identical_to_preserved_D1_initial900_MPI_partition','shared_partition_sha256':partition_sha,'all_initial_processor_files_hashes_match':True,'native_initial_processor_file_count':len(actual),'files':actual},indent=2)+'\n')
        (case/'config-verification.json').write_text(json.dumps({'only_declared_change':'SIMPLE.consistent no -> yes','all_initial_native_files_match':True,'shared_initial_partition_verified':True,'native_source_files':source_index,'system_sha256':{str(f.relative_to(case)):sha(f) for f in sorted((case/'system').iterdir()) if f.is_file()},'proposal_sha256':sha(capsule/'configs/proposed-protocol.json'),'runner_sha256':sha(Path(__file__))},indent=2)+'\n')
        command(['mpirun','--bind-to','none','--use-hwthread-cpus','-np','4','foamRun','-parallel'],'log.foamRun',180)
        command(['reconstructPar','-latestTime'],'log.reconstructPar',35)
        command([sys.executable,'/capsule/source/summarize_reference_flow.py',str(case),str(case/'flow-summary.json')],'log.summary',30)
    finally:
        (output/'execution-receipt.json').write_text(json.dumps({'commands':commands,'wall_seconds':time.monotonic()-started,'coordinated_release':release,'one_new_case_only':True,'no_automatic_retry_or_continuation':True,'shared_initial_partition_sha256':partition_sha,'peak_child_RSS_KiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'native_and_baseline_mounted_read_only_required':True,'physical_validation_established':False},indent=2)+'\n')


if __name__=='__main__':execute(Path('/native'),Path('/baseline'),Path('/capsule'),Path('/run/cases'))
