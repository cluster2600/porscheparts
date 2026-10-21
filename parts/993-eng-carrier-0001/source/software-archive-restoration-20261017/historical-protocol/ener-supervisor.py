"""Supervise only the prepared ENER refinement in one newly owned Docker container."""
import hashlib
import json
from pathlib import Path
import re
import signal
import subprocess
import time

HERE=Path(__file__).resolve().parent
OWNER_KEY='org.porscheparts.carrier.ener-supervision'
FORMAT='{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"Owner":{{json (index .Config.Labels "'+OWNER_KEY+'")}},"NanoCpus":{{json .HostConfig.NanoCpus}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"PidsLimit":{{json .HostConfig.PidsLimit}},"NetworkMode":{{json .HostConfig.NetworkMode}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Tmpfs":{{json .HostConfig.Tmpfs}},"Mounts":{{json .Mounts}},"Entrypoint":{{json .Config.Entrypoint}},"Cmd":{{json .Config.Cmd}},"WorkingDir":{{json .Config.WorkingDir}},"Running":{{json .State.Running}},"ExitCode":{{json .State.ExitCode}},"OOMKilled":{{json .State.OOMKilled}},"StateError":{{json .State.Error}}}'


def sha(path,guard=lambda:None):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):guard();h.update(chunk)
    return h.hexdigest()


class DockerCLI:
    def __init__(self):self.cancelled=False
    def cancel(self,*_):self.cancelled=True
    def invoke(self,args,timeout,log=None,ignore_cancel=False):
        if self.cancelled and not ignore_cancel:raise InterruptedError('Cancellation requested')
        deadline=time.monotonic()+timeout;out=err=None;proc=None;timed=False
        try:
            if log:
                out=Path(log).open('xb');err=Path(str(log)+'.stderr').open('xb')
            proc=subprocess.Popen(['/usr/local/bin/docker',*args],stdout=out or subprocess.PIPE,
                                  stderr=err or subprocess.PIPE,text=not bool(log))
            while True:
                left=deadline-time.monotonic()
                if left<=0 or (self.cancelled and not ignore_cancel):
                    timed=left<=0;proc.kill()
                    try:stdout,stderr=proc.communicate(timeout=min(2,max(0.01,left+2)))
                    except subprocess.TimeoutExpired:stdout=stderr='';proc.poll()
                    return dict(returncode=proc.returncode,stdout=stdout or '',stderr=stderr or '',timed_out=timed,cancelled=not timed)
                try:
                    stdout,stderr=proc.communicate(timeout=min(.25,left))
                    return dict(returncode=proc.returncode,stdout=stdout or '',stderr=stderr or '',timed_out=False,cancelled=False)
                except subprocess.TimeoutExpired:continue
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                try:proc.wait(timeout=1)
                except subprocess.TimeoutExpired:pass
            if out:out.close()
            if err:err.close()


def supervise(plan,backend,clock=time.monotonic,started=None):
    started=clock() if started is None else started;deadline=started+plan['wall_budget_seconds'];work_deadline=deadline-plan['cleanup_reserve_seconds']
    report=dict(status='starting_no_admission',global_admission=False,container_id=None,
                actual_container_exit_code=None,attach_cli_returncode=None,container_removed=False,
                creation_attempted=False,operations=[],input_hashes_unchanged=False)
    case=Path(plan['case_directory']);name=plan['container_name'];cid=None
    def remaining(cleanup=False):
        left=(deadline-10 if cleanup else work_deadline)-clock()
        if left<=0:raise TimeoutError('Declared total execution budget exhausted')
        return left
    def guard():remaining()
    def command(args,cap=20,cleanup=False,log=None):
        left=remaining(cleanup)
        if left<=3:raise TimeoutError('Insufficient budget to call and reap a Docker CLI')
        budget=min(cap,left-3);result=backend.invoke(args,budget,log,ignore_cancel=cleanup)
        report['operations'].append(dict(arguments=args,timeout_seconds=budget,cleanup=cleanup,
            returncode=result['returncode'],timed_out=result.get('timed_out',False),cancelled=result.get('cancelled',False),
            stdout=result.get('stdout','')[:1000],stderr=result.get('stderr','')[:1000]))
        return result
    def checked(args,**kwargs):
        result=command(args,**kwargs)
        if result.get('timed_out'):raise TimeoutError('Docker operation timed out: '+args[0])
        if result.get('cancelled'):raise InterruptedError('Cancellation requested')
        if result['returncode']!=0:raise RuntimeError('Docker operation failed: '+args[0])
        return result
    def inspect(target,cleanup=False):
        result=checked(['container','inspect',target,'--format',FORMAT],cleanup=cleanup,cap=15)
        data=json.loads(result['stdout'])
        if not re.fullmatch('[0-9a-f]{64}',data.get('Id','')) or data.get('Name')!='/'+name or data.get('Owner')!=plan['ownership_token'] or data.get('Image')!=plan['image']:
            raise ValueError('Container ownership identity refused')
        if (cid is not None and data['Id']!=cid) or (re.fullmatch('[0-9a-f]{64}',target) and data['Id']!=target):raise ValueError('Container ID changed')
        return data
    def verify_pins(cleanup=False):
        for path,digest in plan['files_sha256'].items():
            if sha(path,lambda:remaining(cleanup))!=digest:raise ValueError('Frozen input/source changed')
    try:
        verify_pins()
        if case.resolve()!=case or any(p.is_symlink() for p in case.rglob('*')):raise ValueError('Case path contains a symlink')
        if set(p.name for p in case.iterdir())!=set(plan['initial_case_files']):raise ValueError('Case outputs are not fresh')
        for path in [case/(plan['case_name']+'.log'),case/'runtime.json',HERE/'ccx.prestart']:
            if path.exists() or path.is_symlink():raise ValueError('A new output already exists')
        image=json.loads(checked(['image','inspect',plan['image'],'--format','{"Id":{{json .Id}},"Architecture":{{json .Architecture}},"Os":{{json .Os}}}'])['stdout'])
        if image!={'Id':plan['image'],'Architecture':'arm64','Os':'linux'}:raise ValueError('Image platform changed')
        existing=checked(['container','ls','-a','--no-trunc','--filter','name=^/'+name+'$','--format','{{.ID}}'])
        if existing['stdout'].strip():raise ValueError('The proposed new container name is not fresh')
        argv=['create','--pull=never','--name',name,'--label',OWNER_KEY+'='+plan['ownership_token'],
              '--network','none','--cpus','1','--memory','6g','--memory-swap','6g','--pids-limit','128',
              '--read-only','--tmpfs','/tmp:rw,size=512m','--mount','type=bind,src='+str(case)+',dst=/work',
              '--workdir','/work','--env','OMP_NUM_THREADS=1','--env','CCX_NPROC_RESULTS=1','--env','OPENBLAS_NUM_THREADS=1',
              '--entrypoint','/usr/bin/timeout',plan['image'],*plan['container_command']]
        report['creation_attempted']=True
        created=checked(argv,cap=30)
        proposed=created['stdout'].strip()
        if not re.fullmatch('[0-9a-f]{64}',proposed):raise ValueError('Unknown container creation response')
        data=inspect(proposed);cid=data['Id'];report['container_id']=cid
        expected={'NanoCpus':1000000000,'Memory':6*1024**3,'MemorySwap':6*1024**3,'PidsLimit':128,
                  'NetworkMode':'none','ReadonlyRootfs':True,'Entrypoint':['/usr/bin/timeout'],
                  'Cmd':plan['container_command'],'WorkingDir':'/work','Tmpfs':{'/tmp':'rw,size=512m'}}
        if any(data.get(k)!=v for k,v in expected.items()):raise ValueError('Actual isolation/entrypoint differs')
        mounts=data.get('Mounts',[])
        bind=[m for m in mounts if m.get('Type')=='bind']
        if len(bind)!=1 or bind[0].get('Source')!=str(case) or bind[0].get('Destination')!='/work' or bind[0].get('RW') is not True:
            raise ValueError('Case bind mount differs')
        if any(m.get('Type')!='bind' and not (m.get('Type')=='tmpfs' and m.get('Destination')=='/tmp') for m in mounts):
            raise ValueError('An additional mount is present')
        report['actual_container_before_start']=data
        checked(['cp',cid+':/usr/bin/ccx',str(HERE/'ccx.prestart')],cap=25)
        if sha(HERE/'ccx.prestart',guard)!=plan['binary_sha256']:raise ValueError('Prestart CCX binary hash differs')
        report['prestart_binary_sha256']=plan['binary_sha256']
        attached=command(['start','--attach',cid],cap=plan['solver_timeout_seconds']+15,log=case/(plan['case_name']+'.log'))
        report['attach_cli_returncode']=attached['returncode']
        if attached.get('timed_out'):raise TimeoutError('Attached solver exceeded remaining work budget')
        if attached.get('cancelled'):raise InterruptedError('Attached solver cancelled')
        ended=inspect(cid);report['actual_container_after_start']=ended
        report['actual_container_exit_code']=ended.get('ExitCode')
        if ended.get('Running') or ended.get('OOMKilled') or ended.get('StateError') or ended.get('ExitCode')!=0 or attached['returncode']!=0:
            raise RuntimeError('Actual solver/container execution failed')
        outputs={}
        for suffix in ['dat','frd','sta','cvg','log']:
            p=case/(plan['case_name']+'.'+suffix)
            if not p.is_file() or p.is_symlink() or p.stat().st_size==0:raise ValueError('Expected native output missing: '+suffix)
            outputs[p.name]={'sha256':sha(p,guard),'bytes':p.stat().st_size}
        log=case/(plan['case_name']+'.log')
        with log.open('rb') as stream:
            tail=b''
            for chunk in iter(lambda:stream.read(65536),b''):
                guard();combined=tail+chunk
                if b'*ERROR' in combined.upper():raise ValueError('Native log contains an error')
                tail=combined[-16:]
        report['outputs']=outputs;report['status']='solver_executed_no_numeric_admission'
    except BaseException as error:
        report.update(status='execution_refused_no_admission',error_type=type(error).__name__,error=str(error))
    finally:
        if report['creation_attempted']:
            try:
                # A failed/unknown create is resolved only by this fresh name AND label.
                owned=inspect(cid or name,cleanup=True);cid=owned['Id'];report['container_id']=cid
                checked(['rm','--force',cid],cleanup=True,cap=25)
                absence=checked(['container','ls','-a','--no-trunc','--filter','id='+cid,'--format','{{.ID}}'],cleanup=True,cap=15)
                if absence['stdout'].strip():raise RuntimeError('Created container is still listed')
                report['container_removed']=True
            except BaseException as error:
                report['cleanup_error_type']=type(error).__name__;report['cleanup_error']=str(error)
                report['status']='cleanup_unconfirmed_no_admission'
        try:
            verify_pins(cleanup=True);report['input_hashes_unchanged']=True
        except BaseException as error:
            report['integrity_error']=str(error);report['status']='input_identity_refused_no_admission'
        report['wall_seconds']=clock()-started;report['global_budget_seconds']=plan['wall_budget_seconds']
        report['cleanup_reserve_seconds']=plan['cleanup_reserve_seconds']
        report['within_global_budget']=report['wall_seconds']<=plan['wall_budget_seconds']
        if not report['within_global_budget']:report['status']='global_budget_exceeded_no_admission'
    return report


def main():
    started=time.monotonic()
    plan_path=HERE/'plan.json';plan_sha=sha(plan_path);plan=json.loads(plan_path.read_text())
    receipt=HERE/'execution-receipt.json'
    for p in [receipt,HERE/'ccx.prestart']:
        if p.exists() or p.is_symlink():raise FileExistsError('Preserve previous execution artifacts')
    if sha(__file__)!=plan['caller_sha256']:raise ValueError('Caller source differs from reviewed plan')
    if plan['wall_budget_seconds']!=3600 or plan['cleanup_reserve_seconds']!=90 or plan['solver_timeout_seconds']!=3300:
        raise ValueError('Resource bounds differ from the reviewed 3600-second plan')
    cli=DockerCLI();signal.signal(signal.SIGTERM,cli.cancel);signal.signal(signal.SIGINT,cli.cancel)
    result=supervise(plan,cli,started=started)
    result.update(plan_sha256=plan_sha,caller_sha256=sha(__file__),plan_unchanged=sha(plan_path)==plan_sha)
    if not result['plan_unchanged']:result['status']='plan_changed_no_admission'
    if result['status']=='solver_executed_no_numeric_admission':
        case=Path(plan['case_directory'])
        runtime={'status':'executed','name':plan['case_name'],'image':plan['image'],'container':result['container_id'],
            'cpus':1,'memory_GiB':6,'swap_GiB':0,'network':'none','source_sha256':sha(__file__),
            'plan_sha256':sha(case/'plan.json'),'mesh_sha256':sha(case/'mesh.inp'),'input_sha256':sha(case/(plan['case_name']+'.inp')),
            'ccx_binary_sha256':result['prestart_binary_sha256'],'constitutive_model':plan['constitutive_model'],
            'seconds':result['wall_seconds'],'owned_container_removed':result['container_removed'],
            'supervision_plan_sha256':plan_sha,'scope':'Refined-increment constitutive sensitivity; no numeric admission before independent audits.'}
        try:
            with (case/'runtime.json').open('x') as stream:json.dump(runtime,stream,indent=2);stream.write('\n')
            result['runtime_json_sha256']=sha(case/'runtime.json')
        except BaseException as error:
            result.update(status='runtime_publication_refused_no_admission',publication_error=str(error))
    result['wall_seconds']=time.monotonic()-started
    if result['wall_seconds']>plan['wall_budget_seconds']:result['status']='global_budget_exceeded_no_admission'
    with receipt.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':result['status'],'actual_container_exit_code':result['actual_container_exit_code'],'container_removed':result['container_removed'],'receipt_sha256':sha(receipt)}),flush=True)
    return 0 if result['status']=='solver_executed_no_numeric_admission' else 1


if __name__=='__main__':raise SystemExit(main())
