"""Inspect actual Linux cgroup v1/v2 limits; never replace an unknown quota with host RAM."""
import json
import os
from pathlib import Path
import platform
import shutil


def memory_limit(raw):
    value=raw.strip()
    if value in ['max','-1']:return None
    number=int(value)
    if number<=0:raise ValueError('Positive memory limit required')
    return None if number>=2**60 else number


def cpu_limit(quota,period):
    period=int(period)
    if period<=0:raise ValueError('Positive CPU period required')
    if quota=='max'or int(quota)==-1:return None
    quota=int(quota)
    if quota<=0:raise ValueError('Positive CPU quota required')
    return quota/period


def group_paths(base,membership,filename):
    relative=Path(membership.lstrip('/'))
    if '..' in relative.parts:raise ValueError('Invalid cgroup membership path')
    leaf=base/relative
    if not (leaf/filename).is_file():leaf=base
    paths=[]
    while True:
        if (leaf/filename).is_file():paths.append(leaf/filename)
        if leaf==base:break
        leaf=leaf.parent
    return paths


def inspect_limits(root,cgroups=None):
    root=Path(root).resolve()
    if cgroups is None:
        proc=Path('/proc/self/cgroup');cgroups=proc.read_text()if proc.is_file()else''
    groups={}
    for line in cgroups.splitlines():
        fields=line.split(':',2)
        if len(fields)!=3:raise ValueError('Malformed cgroup membership')
        for name in fields[1].split(','):groups[name]=fields[2]
    memory=None
    for base,filename,controller in [(root,'memory.max',''),(root/'memory','memory.limit_in_bytes','memory')]:
        paths=group_paths(base,groups.get(controller,''),filename)
        if paths:
            observations=[(memory_limit(p.read_text()),p.read_text().strip(),p)for p in paths]
            finite=[row for row in observations if row[0]is not None]
            memory=min(finite,key=lambda row:row[0])if finite else observations[0]
            memory_version='v2'if controller==''else'v1';break
    if memory is None:raise ValueError('Unsupported cgroup memory layout')
    observations=[]
    for base,filename,controller in [(root,'cpu.max',''),(root/'cpu','cpu.cfs_quota_us','cpu'),(root/'cpu,cpuacct','cpu.cfs_quota_us','cpu')]:
        paths=group_paths(base,groups.get(controller,''),filename)
        if not paths:continue
        for path in paths:
            if controller=='':
                fields=path.read_text().split()
                if len(fields)!=2:raise ValueError('Malformed cgroup v2 CPU limit')
                quota,period=fields
            else:quota=path.read_text().strip();period=(path.parent/'cpu.cfs_period_us').read_text().strip()
            observations.append((cpu_limit(quota,period),quota,int(period),path))
        cpu_version='v2'if controller==''else'v1';break
    if not observations:raise ValueError('Unsupported cgroup CPU layout')
    finite=[row for row in observations if row[0]is not None];cpu=min(finite,key=lambda row:row[0])if finite else observations[0]
    return dict(memory_limit_bytes=memory[0],memory_limit_raw=memory[1],memory_controller=memory_version,memory_source=str(memory[2]),cpu_limit_cores=cpu[0],cpu_quota_raw=cpu[1],cpu_period_us=cpu[2],cpu_controller=cpu_version,cpu_source=str(cpu[3]))


def main():
    report=inspect_limits('/sys/fs/cgroup');report.update(machine=platform.machine(),python=platform.python_version(),cpu_affinity_count=len(os.sched_getaffinity(0)),stdbuf=shutil.which('stdbuf'),rsync=shutil.which('rsync'),image_ready=Path('/workspace/READY').exists());print(json.dumps(report,indent=2))

if __name__=='__main__':main()
