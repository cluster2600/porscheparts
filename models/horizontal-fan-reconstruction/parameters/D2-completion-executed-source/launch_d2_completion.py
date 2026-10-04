#!/usr/bin/env python3
"""Explicitly coordinated single-case supervisor; no launch until operator signal."""
import argparse,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path
sys.dont_write_bytecode = True
from d2_completion_guards import IMAGE,GLOBAL_CAP,remaining,container_command,inspect_limits,validate_plan,digest_file


def launch(prepared,previous,selections,capsule,output,release):
    started=time.monotonic();deadline=started+GLOBAL_CAP
    if sys.platform!='linux' or not release.strip():raise ValueError('Native Linux and explicit coordinated release required')
    if any(c in release for c in ['\n','\r','\x00']):raise ValueError('A single-line coordinated release is required')
    prepared,previous,selections,capsule=[p.resolve(strict=True) for p in [prepared,previous,selections,capsule]]
    output=output.resolve()
    if output.exists() or any(output==p or p in output.parents or output in p.parents for p in [prepared,previous,capsule]):raise ValueError('Fresh isolated output required')
    plan=json.loads((capsule/'configs/completion-protocol.json').read_text());validate_plan(plan)
    manifest=json.loads((capsule/'capsule-manifest.json').read_text())
    actual={str(p.relative_to(capsule)) for p in capsule.rglob('*') if p.is_file() and p.name!='capsule-manifest.json'}
    if actual!=set(manifest['files']):raise ValueError('Frozen capsule coverage differs')
    for name,record in manifest['files'].items():
        if digest_file(capsule/name,started+30)!=record:raise ValueError('Frozen capsule altered')
    if not manifest['new_solver_launched'] is False:raise ValueError('Prepared capsule required')
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    load=os.getloadavg();cpus=os.cpu_count()
    if available<6*1024**3 or cpus is None or cpus<8 or load[0]>cpus-4:raise ValueError('Insufficient fresh memory/CPU reserve')
    physical=[]
    for cpu in [0,2,4,5]:
        base=Path('/sys/devices/system/cpu')/('cpu'+str(cpu))/'topology'
        physical.append(tuple((base/name).read_text().strip() for name in ['physical_package_id','core_id']))
    if len(set(physical))!=4:raise ValueError('Four distinct physical cores required')
    native_active=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            command=(proc/'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace')
            if Path(command).name in ['foamRun','checkMesh','reconstructPar','decomposePar']:native_active.append(proc.name)
        except (OSError,ProcessLookupError):pass
    if native_active:raise ValueError('Existing native CFD command active; no duplicate job')
    def docker(args,timeout=3,check=True):
        cap=min(timeout,remaining(deadline))
        result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=cap)
        if check and result.returncode:raise RuntimeError('Docker read/control action failed: '+args[0])
        return result
    services=sorted(docker(['ps','--format','{{.Names}} {{.Image}}']).stdout.splitlines())
    if docker(['ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}']).stdout.strip():raise ValueError('Existing flow container active; no duplicate job')
    docker(['image','inspect',IMAGE])
    if time.monotonic()>started+20:raise TimeoutError('Preflight leaves insufficient setup reserve')
    output.mkdir(parents=True,exist_ok=False);name='fan-d2-completion-'+uuid.uuid4().hex[:12]
    command=container_command(name,prepared,previous,selections,capsule,output,os.getuid(),os.getgid(),release,deadline)
    proc=None;code=125;error=None;limits=None;cleanup=[]
    previous_term=signal.getsignal(signal.SIGTERM)
    def interrupted(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:
        with (output/'log.container').open('x') as log:
            proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            inspect_deadline=min(started+25,time.monotonic()+5)
            data=None
            while time.monotonic()<inspect_deadline:
                result=docker(['inspect',name],timeout=1,check=False)
                if result.returncode==0:data=json.loads(result.stdout)[0];break
                time.sleep(.05)
            if data is None:raise RuntimeError('Owned container isolation could not be checked')
            limits=inspect_limits(data,os.getuid(),os.getgid())
            (output/'isolation-admitted.json').write_text(json.dumps({'actual_isolation_verified':True,'aggregate_deadline_monotonic':deadline,'limits':limits},indent=2)+'\n')
            code=proc.wait(timeout=remaining(deadline,10))
            if code:raise RuntimeError('Owned completion exited failed or partial')
    except (Exception,KeyboardInterrupt) as exc:
        error=type(exc).__name__+': '+str(exc)
        code=124 if isinstance(exc,subprocess.TimeoutExpired) else 130 if isinstance(exc,KeyboardInterrupt) else 125
    finally:
        # A unique exact name is used; no foreign process/container is stopped.
        try:
            own=docker(['ps','--filter','name=^/'+name+'$','--format','{{.ID}}'],timeout=1).stdout.strip()
            if own:
                result=docker(['stop','--time','1',name],timeout=3,check=False);cleanup.append({'action':'stop','name':name,'exit_status':result.returncode})
                if result.returncode:
                    result=docker(['kill',name],timeout=2,check=False);cleanup.append({'action':'kill','name':name,'exit_status':result.returncode})
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=min(1,remaining(deadline)))
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=min(1,remaining(deadline)))
            own_after=docker(['ps','--filter','name=^/'+name+'$','--format','{{.ID}}'],timeout=1).stdout.strip()
            services_after=sorted(docker(['ps','--format','{{.Names}} {{.Image}}'],timeout=1).stdout.splitlines())
        except Exception as exc:
            own_after='release_unconfirmed';services_after=None;code=125;error=(error or '')+'; release: '+type(exc).__name__+': '+str(exc)
        finally:signal.signal(signal.SIGTERM,previous_term)
        archive_file=output/'native-evidence-manifest.json';execution_file=output/'execution-receipt.json'
        archive=json.loads(archive_file.read_text()) if archive_file.exists() else None
        execution=json.loads(execution_file.read_text()) if execution_file.exists() else None
        complete=bool(code==0 and not own_after and archive and archive['all_members_verified'] and execution and execution['status']=='completed_exact20_no_retry')
        if not complete and code==0:code=2
        receipt={'status':'completed_exact20_preserved_and_released' if complete else 'failed_or_partial_no_retry',
                 'exit_status':code,'error':error,'commands':[command],'coordinated_release':release,
                 'container_name':name,'actual_isolation':limits,'owned_cleanup':cleanup,
                 'owned_container_remaining':bool(own_after),'services_before':services,'services_after':services_after,
                 'services_unchanged':services_after==services,'no_foreign_service_or_process_modified':True,
                 'new_cases':['extended'],'maximum_new_iterations':20,'target_iteration':1020,
                 'current_control_replayed':False,'no_retry_or_further_continuation':True,
                 'global_wall_cap_seconds':240,'global_wall_seconds_including_preservation_and_release':time.monotonic()-started,
                 'mem_available_at_admission_bytes':available,'load_at_admission':load,'logical_CPU_count':cpus,
                 'physical_cores_at_admission':physical,'capsule_manifest_identity':digest_file(capsule/'capsule-manifest.json',deadline) if time.monotonic()<deadline else None,
                 'native_archive_verified':bool(archive and archive['all_members_verified']),
                 'resources_released_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                 'native_fields_and_archive_private':True,'physical_validation_established':False}
        if receipt['global_wall_seconds_including_preservation_and_release']>240:receipt['aggregate_cap_exceeded']=True;code=125;receipt['exit_status']=code;receipt['status']='aggregate_cap_exceeded_not_admitted'
        (output/'launcher-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return code


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ['prepared','previous','selections','capsule','output']:cli.add_argument(name,type=Path)
    cli.add_argument('--coordinated-release',required=True)
    args=cli.parse_args()
    raise SystemExit(launch(args.prepared,args.previous,args.selections,args.capsule,args.output,args.coordinated_release))
