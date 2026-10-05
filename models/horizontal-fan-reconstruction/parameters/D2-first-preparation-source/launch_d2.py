#!/usr/bin/env python3
"""One coordinated container, frozen720s global cap, preserve and release."""
import argparse,hashlib,json,os,signal,subprocess,sys,tarfile,time,uuid
from pathlib import Path
IMAGE='sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def launch(native,selections,capsule,output,release):
    started=time.monotonic();deadline=started+720
    if sys.platform!='linux' or not release.strip():raise ValueError('Coordinated native Linux execution required')
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    if available<6*1024**3:raise ValueError('Insufficient memory reserve')
    services=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Image}}'],text=True,timeout=10).splitlines()
    active=subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True,timeout=10)
    if active.strip():raise ValueError('Existing flow container active; refuse duplicate job')
    subprocess.run(['docker','image','inspect',IMAGE],stdout=subprocess.DEVNULL,check=True,timeout=10)
    native=native.resolve();selections=selections.resolve();capsule=capsule.resolve();output=output.resolve()
    manifest=json.loads((capsule/'capsule-manifest.json').read_text())
    for name,record in manifest['files'].items():
        p=capsule/name
        if p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:raise ValueError('Frozen capsule identity differs')
    output.mkdir(exist_ok=False);name='fan-d2-'+uuid.uuid4().hex[:12]
    cmd=['docker','run','--name',name,'--pull=never','--rm','--network','none','--cpus','4','--cpuset-cpus','0,2,4,5','--memory','5g','--memory-swap','5g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--env','FAN_D2_COORDINATED_RELEASE='+release,'--env','FAN_D2_DEADLINE_MONOTONIC='+str(started+625),'--mount','type=bind,source='+str(native)+',target=/native,readonly','--mount','type=bind,source='+str(selections)+',target=/selections.npz,readonly','--mount','type=bind,source='+str(capsule)+',target=/capsule,readonly','--mount','type=bind,source='+str(output)+',target=/run',IMAGE,'bash','-c','source /opt/openfoam13/etc/bashrc; exec python3 /capsule/source/run_d2_in_container.py']
    cleanup=None;code=1;proc=None;timed_out=False
    with (output/'log.container').open('x') as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        def interrupted(signum,frame):raise KeyboardInterrupt
        previous=signal.signal(signal.SIGTERM,interrupted)
        try:
            inspected=None;inspect_deadline=time.monotonic()+5
            while time.monotonic()<inspect_deadline:
                trial=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=2)
                if trial.returncode==0:inspected=json.loads(trial.stdout)[0];break
                time.sleep(.1)
            if inspected is None:raise RuntimeError('Cannot verify owned container isolation')
            h=inspected['HostConfig'];mounts={m['Destination']:not m['RW'] for m in inspected['Mounts']}
            limits={'CPU_max':h['NanoCpus']/1e9,'cpuset':h['CpusetCpus'],'RAM_limit_bytes':h['Memory'],'memory_and_swap_limit_bytes':h['MemorySwap'],'network':h['NetworkMode'],'pids_limit':h['PidsLimit'],'user':inspected['Config']['User'],'mounts_read_only':mounts,'cap_drop':h['CapDrop'],'security_options':h['SecurityOpt'],'image_ID':inspected['Image']}
            if limits['CPU_max']!=4 or limits['RAM_limit_bytes']!=5*1024**3 or limits['memory_and_swap_limit_bytes']!=5*1024**3 or limits['network']!='none' or not all(mounts[k] for k in ['/native','/selections.npz','/capsule']) or mounts['/run']:raise RuntimeError('Actual isolation differs from frozen caps')
            (output/'isolation-verification.json').write_text(json.dumps(limits,indent=2)+'\n')
            code=proc.wait(timeout=max(1,635-(time.monotonic()-started)))
        except (Exception,KeyboardInterrupt) as e:
            timed_out=isinstance(e,subprocess.TimeoutExpired);code=124 if timed_out else 130 if isinstance(e,KeyboardInterrupt) else 125
            try:cleanup=subprocess.run(['docker','stop','--time','3',name],capture_output=True,text=True,timeout=5).returncode
            except subprocess.TimeoutExpired:cleanup=subprocess.run(['docker','kill',name],capture_output=True,text=True,timeout=3).returncode
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=1)
        finally:signal.signal(signal.SIGTERM,previous)
    active_after=subprocess.check_output(['docker','ps','--filter','name=^/'+name+'$','--format','{{.ID}}'],text=True,timeout=5).strip()
    services_after=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Image}}'],text=True,timeout=5).splitlines()
    if active_after:raise RuntimeError('Owned container still active')
    receipt={'status':'D2_completed' if code==0 else 'D2_failed_or_partial_no_retry','exit_status':code,'timed_out':timed_out,'container_name':name,'coordinated_release':release,'global_wall_cap_seconds':720,'wall_seconds_before_preservation':time.monotonic()-started,'mem_available_at_admission_bytes':available,'services_before':services,'services_after':services_after,'services_unchanged':services==services_after,'owned_container_remaining':False,'resources_released_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'CPU_max':4,'RAM_limit_bytes':5*1024**3,'memory_and_swap_limit_bytes':5*1024**3,'cpuset':'0,2,4,5','network':'none','all_source_mounts_read_only':True,'no_other_service_modified':True,'command':cmd,'owned_timeout_cleanup_exit':cleanup,'physical_validation_established':False}
    (output/'launcher-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    members={};files=[f for f in sorted(output.rglob('*')) if f.is_file() and 'processor' not in str(f.relative_to(output)) and (any('/'+str(t)+'/' in '/'+str(f.relative_to(output)) for t in [980,1000,1020]) or f.name.startswith('log.') or f.suffix=='.json' or f.suffix=='.dat' or '/system/' in '/'+str(f.relative_to(output)) or '/constant/' in '/'+str(f.relative_to(output)) or f.suffix=='.npz')]
    archive=output/'native-evidence.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
        for p in files:
            if time.monotonic()>=deadline-5:raise TimeoutError('Preservation deadline reached; no solver continuation')
            key=str(p.relative_to(output));members[key]={'bytes':p.stat().st_size,'sha256':sha(p)};tf.add(p,arcname=key,recursive=False)
    index={'status':'D2_native_outputs_preserved','archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'members':members,'global_elapsed_seconds_setup_solver_reconstruction_audit_and_preservation':time.monotonic()-started,'global_wall_cap_seconds':720,'all_members_verified':False,'private_archive_not_published':True}
    with tarfile.open(archive,'r:gz') as tf:
        for member in tf:
            data=tf.extractfile(member).read();record=members[member.name]
            if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Preserved member identity differs')
    index['all_members_verified']=True;index['global_elapsed_seconds_setup_solver_reconstruction_audit_and_preservation']=time.monotonic()-started
    (output/'native-evidence-manifest.json').write_text(json.dumps(index,indent=2)+'\n')
    if index['global_elapsed_seconds_setup_solver_reconstruction_audit_and_preservation']>720:raise TimeoutError('Global cap exceeded')
    return code


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['native','selections','capsule','output']:ap.add_argument(name,type=Path)
    ap.add_argument('--coordinated-release',required=True);a=ap.parse_args();raise SystemExit(launch(a.native,a.selections,a.capsule,a.output,a.coordinated_release))
