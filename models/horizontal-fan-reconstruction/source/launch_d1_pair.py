#!/usr/bin/env python3
"""Launch one owned, bounded D1 container only after coordinator resource release."""
import argparse,hashlib,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path
IMAGE='sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696'


def launch(native,capsule,output,release):
    started=time.monotonic()
    if sys.platform!='linux' or not release.strip():raise ValueError('Linux runtime and explicit coordinated resource release required')
    available={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')}['MemAvailable']
    if available<6*1024**3:raise ValueError('Insufficient memory reserve for5GiB D1 pair')
    subprocess.run(['docker','image','inspect',IMAGE],stdout=subprocess.DEVNULL,check=True,timeout=10)
    active=subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True,timeout=10)
    if active.strip():raise ValueError('Existing flow image active; refuse duplicate solver')
    native=native.resolve();capsule=capsule.resolve();output=output.resolve()
    if not (capsule/'configs/pair-manifest.json').is_file() or not (native/'900').is_dir():raise ValueError('Prepared capsule and native900 restart required')
    capsule_manifest=json.loads((capsule/'capsule-manifest.json').read_text())
    for name,record in capsule_manifest['files'].items():
        file=capsule/name
        if file.stat().st_size!=record['bytes'] or hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Prepared capsule identity changed')
    output.mkdir(exist_ok=False);name='fan-d1-'+uuid.uuid4().hex[:12]
    cmd=['docker','run','--name',name,'--pull=never','--rm','--network','none','--cpus','4','--cpuset-cpus','0,2,4,5','--memory','5g','--memory-swap','5g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--env','FAN_D1_COORDINATED_RELEASE='+release,'--mount','type=bind,source='+str(native)+',target=/native,readonly','--mount','type=bind,source='+str(capsule)+',target=/capsule,readonly','--mount','type=bind,source='+str(output)+',target=/run',IMAGE,'bash','-c','source /opt/openfoam13/etc/bashrc; exec timeout --signal=TERM --kill-after=5 580 python3 /capsule/source/run_d1_in_container.py /native /capsule/configs /run/cases']
    timed_out=False;owned_cleanup=None
    with (output/'log.D1-container').open('x') as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        def interrupted(signum,frame):raise KeyboardInterrupt
        previous_handler=signal.signal(signal.SIGTERM,interrupted)
        try:code=proc.wait(timeout=max(1,590-(time.monotonic()-started)))
        except (subprocess.TimeoutExpired,KeyboardInterrupt) as error:
            timed_out=isinstance(error,subprocess.TimeoutExpired);code=124 if timed_out else 130
            try:
                cleanup=subprocess.run(['docker','stop','--time','5',name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
                owned_cleanup={'name':name,'exit_status':cleanup.returncode,'output':cleanup.stdout}
            except subprocess.TimeoutExpired:owned_cleanup={'name':name,'stop_command_timed_out':True}
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=1)
        finally:signal.signal(signal.SIGTERM,previous_handler)
    receipt={'status':'bounded_owned_D1_completed' if code==0 else 'bounded_owned_D1_failed_no_retry','exit_status':code,'timed_out':timed_out,'wall_seconds_including_admission_setup':time.monotonic()-started,'pair_cap_seconds':600,'container_payload_cap_seconds':580,'owned_container_name':name,'owned_timeout_cleanup':owned_cleanup,'command':cmd,'mem_available_at_admission_bytes':available,'coordinated_release':release,'no_other_container_or_service_modified':True,'physical_validation_established':False}
    (output/'launcher-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return code

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['native','capsule','output']:p.add_argument(name,type=Path)
    p.add_argument('--coordinated-release',required=True)
    a=p.parse_args();raise SystemExit(launch(a.native,a.capsule,a.output,a.coordinated_release))
