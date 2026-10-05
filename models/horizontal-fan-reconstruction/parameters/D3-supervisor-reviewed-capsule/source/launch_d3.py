#!/usr/bin/env python3
"""Native D3 supervisor; explicit post-support coordination, one360s deadline."""
import argparse,json,os,platform,re,signal,subprocess,sys,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True
from d3_guards import IMAGE,GLOBAL_CAP,LABELS,remaining,validate_plan,verify_manifest,digest_file,container_command,inspect_limits,active_native_jobs


def launch(prepared,previous,selections,capsule,output,release,expected_capsule_sha256):
    started=time.monotonic();deadline=started+GLOBAL_CAP
    if sys.platform!='linux' or platform.machine() not in ['x86_64','amd64'] or not release.strip() or any(c in release for c in ['\n','\r','\x00']):raise ValueError('Native Linux amd64 and explicit single-line post-support coordinated release required')
    prepared,previous,selections,capsule=[p.resolve(strict=True) for p in [prepared,previous,selections,capsule]];output=output.resolve()
    if output.exists() or any(output==p or p in output.parents or output in p.parents for p in [prepared,previous,capsule]):raise ValueError('New isolated output required')
    if not re.fullmatch(r'[0-9a-f]{64}',expected_capsule_sha256) or digest_file(capsule/'capsule-manifest.json',started+20)['sha256']!=expected_capsule_sha256:raise ValueError('Trusted reviewed capsule manifest SHA256 differs')
    plan=json.loads((capsule/'configs/diagnostic-plan.json').read_text());validate_plan(plan)
    manifest=json.loads((capsule/'capsule-manifest.json').read_text())
    verify_manifest(capsule,manifest['files'],started+20,excluded=['capsule-manifest.json'])
    if manifest['new_solver_launched'] is not False:raise ValueError('Frozen prepared capsule required')
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    cpus=os.cpu_count();load=os.getloadavg()
    if available<7*1024**3 or cpus is None or cpus<8 or load[0]>cpus-4:raise ValueError('Insufficient fresh CPU/RAM reserve')
    physical=[]
    for cpu in [0,2,4,5]:
        base=Path('/sys/devices/system/cpu')/('cpu'+str(cpu))/'topology';physical.append(tuple((base/name).read_text().strip() for name in ['physical_package_id','core_id']))
    if len(set(physical))!=4:raise ValueError('Four distinct physical cores required')
    if active_native_jobs(Path('/proc')):raise ValueError('Existing CFD/meshing/mechanical job active; no overlapping launch')
    def docker(args,timeout=2,check=True):
        result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=min(timeout,remaining(deadline)))
        if check and result.returncode:raise RuntimeError('Docker read/control action failed: '+args[0])
        return result
    services=sorted(docker(['ps','--format','{{.Names}} {{.Image}}']).stdout.splitlines())
    if any(any(marker in row.split()[0].lower() for marker in ['support','fan-d','cylinder-head']) for row in services) or docker(['ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}']).stdout.strip():raise ValueError('Support/CFD container active; explicit release cannot override overlap gate')
    docker(['image','inspect',IMAGE])
    if time.monotonic()>started+20:raise TimeoutError('Preflight exceeds setup share')
    output.mkdir(parents=True,exist_ok=False);name='fan-d3-'+uuid.uuid4().hex[:12]
    command=container_command(name,prepared,previous,selections,capsule,output,os.getuid(),os.getgid(),release,deadline)
    proc=None;code=125;error=None;limits=None;cleanup=[];original_term=signal.getsignal(signal.SIGTERM)
    def interrupted(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:
        with (output/'log.container').open('x') as log:
            proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            inspection_end=min(started+25,time.monotonic()+5);data=None
            while time.monotonic()<inspection_end:
                result=docker(['inspect',name],timeout=.8,check=False)
                if result.returncode==0:data=json.loads(result.stdout)[0];break
                time.sleep(.05)
            if data is None:raise RuntimeError('Owned container actual isolation could not be checked')
            limits=inspect_limits(data,os.getuid(),os.getgid())
            temporary=output/'isolation-admitted.json.tmp';temporary.write_text(json.dumps({'actual_isolation_verified':True,
                'aggregate_deadline_monotonic':deadline,'capsule_manifest_sha256':digest_file(capsule/'capsule-manifest.json',started+30)['sha256'],'limits':limits},indent=2)+'\n')
            temporary.replace(output/'isolation-admitted.json')
            code=proc.wait(timeout=remaining(deadline,5))
            if code:raise RuntimeError('Owned D3 runtime failed or remained partial')
    except (Exception,KeyboardInterrupt) as exc:
        error=type(exc).__name__+': '+str(exc);code=124 if isinstance(exc,subprocess.TimeoutExpired) else 130 if isinstance(exc,KeyboardInterrupt) else 125
    finally:
        try:
            own=docker(['ps','--filter','name=^/'+name+'$','--format','{{.ID}}'],timeout=.6).stdout.strip()
            if own:
                result=docker(['stop','--time','0',name],timeout=1.2,check=False);cleanup.append({'action':'stop','exact_owned_name':name,'exit_status':result.returncode})
                if result.returncode:
                    result=docker(['kill',name],timeout=.8,check=False);cleanup.append({'action':'kill','exact_owned_name':name,'exit_status':result.returncode})
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=min(.5,remaining(deadline)))
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=min(.5,remaining(deadline)))
            own_after=docker(['ps','--filter','name=^/'+name+'$','--format','{{.ID}}'],timeout=.6).stdout.strip()
            services_after=sorted(docker(['ps','--format','{{.Names}} {{.Image}}'],timeout=.6).stdout.splitlines())
        except Exception as exc:own_after='release_unconfirmed';services_after=None;code=125;error=(error or '')+'; release: '+type(exc).__name__+': '+str(exc)
        finally:signal.signal(signal.SIGTERM,original_term)
        archive_file=output/'native-evidence-manifest.json';execution_file=output/'execution-receipt.json'
        archive=json.loads(archive_file.read_text()) if archive_file.exists() else None;execution=json.loads(execution_file.read_text()) if execution_file.exists() else None
        complete=bool(code==0 and not own_after and services_after==services and archive and archive['all_members_verified'] and execution and execution['status']=='completed_two_fixed20_no_retry' and execution['completed_solver_arms']==list(LABELS))
        if not complete and code==0:code=2
        receipt={'status':'completed_two_fixed20_preserved_and_released' if complete else 'failed_or_partial_no_retry',
            'exit_status':code,'error':error,'commands':[command],'coordinated_release':release,'container_name':name,
            'actual_isolation':limits,'owned_cleanup':cleanup,'owned_container_remaining':bool(own_after),
            'services_before':services,'services_after':services_after,'service_name_image_inventory_unchanged':services_after==services,
            'no_foreign_service_or_process_modified':True,'new_cases':list(LABELS),'solver_count_max':2,
            'maximum_new_iterations_per_arm':20,'restart_iteration':1020,'target_iteration':1040,'no_retry_or_further_continuation':True,
            'global_wall_cap_seconds':360,'global_wall_seconds_including_preservation_and_release':time.monotonic()-started,
            'mem_available_at_admission_bytes':available,'load_at_admission':load,'logical_CPU_count':cpus,'physical_cores_at_admission':physical,
            'native_archive_verified':bool(archive and archive['all_members_verified']),'resources_released_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'trusted_capsule_manifest_sha256':expected_capsule_sha256,
            'native_fields_and_archive_private':True,'physical_validation_established':False}
        if receipt['global_wall_seconds_including_preservation_and_release']>360:code=125;receipt.update(status='aggregate_cap_exceeded_not_admitted',exit_status=code)
        (output/'launcher-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return code


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ['prepared','previous','selections','capsule','output']:cli.add_argument(name,type=Path)
    cli.add_argument('--coordinated-release',required=True);cli.add_argument('--capsule-sha256',required=True);a=cli.parse_args()
    raise SystemExit(launch(a.prepared,a.previous,a.selections,a.capsule,a.output,a.coordinated_release,a.capsule_sha256))
