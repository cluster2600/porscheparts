#!/usr/bin/env python3
"""Pure fixed20, isolation, deadline and telemetry guards for D2 completion."""
import hashlib
import json
import re
import tarfile
import time
from pathlib import Path

IMAGE = 'sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696'
GLOBAL_CAP = 240


def remaining(deadline, reserve=0, now=None):
    value = deadline - reserve - (time.monotonic() if now is None else now)
    if value <= 0:
        raise TimeoutError('Frozen aggregate budget exhausted; no retry')
    return value


def validate_plan(plan):
    if (plan['restart_iteration'], plan['first_iteration'], plan['target_iteration'],
        plan['new_iterations'], plan['new_cases'], plan['current_control_replayed']) != (
            1000,1001,1020,20,['extended'],False):
        raise ValueError('Only one fixed20 extended continuation is permitted')
    b = plan['budget_proposed_not_authorized_or_started']
    if (b['CPU_max'],b['memory_and_swap_GiB'],b['aggregate_wall_cap_seconds'],
        b['solver_wall_cap_seconds'],b['existing_image']) != (4,5,240,110,IMAGE):
        raise ValueError('Frozen resource and aggregate caps changed')


def check_complete20(log):
    blocks = re.split(r'(?m)^Time = ',log)[1:]
    steps = [int(float(re.match(r'([0-9.eE+-]+)',b)[1])) for b in blocks]
    complete = [n for n,b in zip(steps,blocks) if re.search(r'ExecutionTime = [0-9.eE+-]+ s\s+ClockTime = ',b)]
    if steps != list(range(1001,1021)) or complete != steps or not re.search(r'(?m)^End\s*$',log) or 'FOAM FATAL' in log:
        raise ValueError('Exactly20 complete native steps1001-to1020 and End required')
    return steps


def container_command(name,prepared,previous,selections,capsule,output,uid,gid,release,deadline):
    if not release.strip() or not name.startswith('fan-d2-completion-'):
        raise ValueError('Explicit coordinated release and owned name required')
    args = ['docker','run','--name',name,'--pull=never','--rm','--network','none',
            '--cpus','4','--cpuset-cpus','0,2,4,5','--memory','5g','--memory-swap','5g',
            '--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--user',str(uid)+':'+str(gid)]
    for value in ['OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1',
                  'FAN_D2_COMPLETION_RELEASE='+release,
                  'FAN_D2_COMPLETION_DEADLINE='+str(deadline)]:
        args += ['--env',value]
    for source,target in [(prepared,'/prepared'),(previous,'/previous'),
                          (selections,'/selections.npz'),(capsule,'/capsule')]:
        args += ['--mount','type=bind,source='+str(source)+',target='+target+',readonly']
    args += ['--mount','type=bind,source='+str(output)+',target=/run',IMAGE,'bash','-c',
             'source /opt/openfoam13/etc/bashrc; exec python3 -B /capsule/source/run_d2_completion.py']
    return args


def inspect_limits(data,uid,gid):
    h = data['HostConfig'];m = {x['Destination']:not x['RW'] for x in data['Mounts']}
    result = {'CPU_max':h['NanoCpus']/1e9,'cpuset':h['CpusetCpus'],
              'RAM_limit_bytes':h['Memory'],'memory_and_swap_limit_bytes':h['MemorySwap'],
              'network':h['NetworkMode'],'pids_limit':h['PidsLimit'],
              'user':data['Config']['User'],'image_ID':data['Image'],
              'cap_drop':h['CapDrop'],'security_options':h['SecurityOpt'],
              'mounts_read_only':m}
    if (result['CPU_max'],result['cpuset'],result['RAM_limit_bytes'],result['memory_and_swap_limit_bytes'],
        result['network'],result['pids_limit'],result['user'],result['image_ID']) != (
            4,'0,2,4,5',5*1024**3,5*1024**3,'none',256,str(uid)+':'+str(gid),IMAGE):
        raise ValueError('Actual container resource isolation differs')
    if not all(m.get(p) is True for p in ['/prepared','/previous','/selections.npz','/capsule']) or m.get('/run') is not False:
        raise ValueError('Actual source/output mount isolation differs')
    if 'ALL' not in h['CapDrop'] or not any(x.startswith('no-new-privileges') for x in h['SecurityOpt']):
        raise ValueError('Actual capability isolation differs')
    return result


def merge_native_rows(old_text,new_text,parse):
    old,new = parse(old_text),parse(new_text)
    if old[:,0].tolist() != list(range(960,1001)):
        raise ValueError('Original41 native extended measurements required')
    expected = list(range(1001,1021));times = new[:,0].tolist()
    if times == [1000]+expected:
        import numpy as np
        if not np.allclose(old[-1],new[0],rtol=1e-8,atol=1e-5):
            raise ValueError('Duplicate checkpoint1000 measurements differ')
    elif times != expected:
        raise ValueError('Only a complete native final20 window is permitted')
    old_lines = [l for l in old_text.splitlines() if l.strip() and not l.lstrip().startswith('#')]
    new_lines = [l for l in new_text.splitlines() if l.strip() and not l.lstrip().startswith('#')]
    if times[0] == 1000:
        new_lines = new_lines[1:]
    return '# Derived view: original41 plus continuation20; raw sources retained separately.\n'+'\n'.join(old_lines+new_lines)+'\n'


class BoundedReader:
    def __init__(self,stream,deadline):
        self.stream,self.deadline=stream,deadline
    def read(self,size=-1):
        remaining(self.deadline)
        return self.stream.read(min(size,1024*1024) if size>=0 else 1024*1024)


def digest_file(path,deadline):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        reader=BoundedReader(f,deadline)
        while True:
            block=reader.read(1024*1024)
            if not block:break
            digest.update(block)
    return {'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def archive_private(root,deadline):
    # Native processor1020 fields are included, even if serial reconstruction fails.
    partial=root/'native-evidence.tar.gz.partial';final=root/'native-evidence.tar.gz'
    if partial.exists() or final.exists():raise FileExistsError('Do not overwrite private evidence')
    files=[f for f in sorted(root.rglob('*')) if f.is_file() and not f.is_symlink()
           and f not in [partial,final] and 'analysis' not in f.relative_to(root).parts]
    records={}
    with tarfile.open(partial,'w:gz',compresslevel=1) as tar:
        for f in files:
            key=str(f.relative_to(root));records[key]=digest_file(f,deadline)
            with f.open('rb') as stream:
                tar.addfile(tar.gettarinfo(str(f),arcname=key),BoundedReader(stream,deadline))
    with tarfile.open(partial,'r:gz') as tar:
        seen=[]
        for member in tar:
            remaining(deadline)
            if not member.isfile() or member.name not in records:raise ValueError('Unexpected archive member')
            digest=hashlib.sha256();stream=tar.extractfile(member);reader=BoundedReader(stream,deadline);count=0
            while True:
                block=reader.read(1024*1024)
                if not block:break
                count+=len(block);digest.update(block)
            if {'bytes':count,'sha256':digest.hexdigest()}!=records[member.name]:raise ValueError('Private archive identity mismatch')
            seen.append(member.name)
    if len(seen)!=len(records):raise ValueError('Archive member coverage differs')
    record={'status':'native_archive_verified','members':records,'archive_identity':digest_file(partial,deadline),
            'native_processor_checkpoints_included':True,'all_members_verified':True,'private_archive_not_published':True}
    remaining(deadline);partial.rename(final)
    (root/'native-evidence-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
