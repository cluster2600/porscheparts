#!/usr/bin/env python3
"""Check actual allocation, Vulkan and NVENC before downloading model weights."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def cgroup_allocation(memory, cpu, root=Path('/sys/fs/cgroup')):
    """Apply v2 or v1 limits; host RAM/affinity alone do not prove allocation."""
    memory = dict(memory)
    quota, cpu_observed, memory_observed = None, False, False
    if (root / 'cpu.max').exists():
        quota = (root / 'cpu.max').read_text().strip()
        limit, period = quota.split()
        if int(period) <= 0 or limit != 'max' and int(limit) <= 0:
            raise ValueError('invalid cgroup v2 CPU quota')
        if limit != 'max':
            cpu = min(cpu, int(limit) / int(period))
        cpu_observed = True
    else:
        for directory in (root / 'cpu', root / 'cpu,cpuacct', root / 'cpuacct,cpu'):
            if (directory / 'cpu.cfs_quota_us').exists():
                limit = int((directory / 'cpu.cfs_quota_us').read_text())
                period = int((directory / 'cpu.cfs_period_us').read_text())
                if period <= 0 or limit != -1 and limit <= 0:
                    raise ValueError('invalid cgroup v1 CPU quota')
                if limit != -1:
                    cpu = min(cpu, limit / period)
                quota, cpu_observed = f'{limit} {period}', True
                break
    for limit_path, used_path in ((root / 'memory.max', root / 'memory.current'),
                                  (root / 'memory/memory.limit_in_bytes', root / 'memory/memory.usage_in_bytes')):
        if limit_path.exists():
            limit = limit_path.read_text().strip()
            if limit != 'max':
                limit, used = int(limit), int(used_path.read_text())
                if limit <= 0 or used < 0:
                    raise ValueError('invalid cgroup memory accounting')
                memory.update(cgroup_limit=limit, cgroup_used=used)
                memory['MemTotal'] = min(memory['MemTotal'], limit)
                memory['MemAvailable'] = min(memory['MemAvailable'], max(0, limit - used))
            memory_observed = True
            break
    return memory, cpu, quota, cpu_observed and memory_observed


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in {'MemTotal', 'MemAvailable'}:
            memory[key] = int(value.split()[0]) * 1024
    cpu = len(os.sched_getaffinity(0))
    memory, cpu, quota, cgroup_observed = cgroup_allocation(memory, cpu)
    query = 'index,name,uuid,pci.bus_id,memory.total,driver_version'
    gpu_csv = subprocess.check_output(['nvidia-smi', '--query-gpu=' + query, '--format=csv,noheader,nounits'], text=True)
    gpus = [dict(zip(query.split(','), [v.strip() for v in row])) for row in csv.reader(gpu_csv.splitlines())]
    report = {'observed_epoch': int(time.time()), 'gpus': gpus, 'effective_cpus': cpu,
              'cpu_quota': quota, 'memory_bytes': memory,
              'workspace_disk_free_bytes': shutil.disk_usage('/workspace').free,
              'checks': {}}
    checks = report['checks']
    checks['cgroup_allocation_observed'] = cgroup_observed
    checks['four_blackwell_96gb'] = (len(gpus) == 4 and all('RTX PRO 6000' in g['name'] and int(g['memory.total']) >= 95000 for g in gpus))
    checks['cpu_64'] = cpu >= 64
    checks['ram_512gb'] = memory['MemTotal'] >= 512 * 10**9
    checks['ram_available_400gb'] = memory['MemAvailable'] >= 400 * 10**9
    checks['disk_free_600gb'] = report['workspace_disk_free_bytes'] >= 600 * 10**9
    commands = {
        'vulkan': ['vulkaninfo', '--summary'],
        'nvenc_gpu2': ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                       'color=c=black:s=128x128:r=30', '-frames:v', '30', '-c:v', 'h264_nvenc',
                       '-gpu', '2', '-f', 'null', '-'],
    }
    for name, command in commands.items():
        with (output / (name + '.log')).open('w') as stream:
            try:
                result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
                checks[name] = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                checks[name] = False
    checks['vulkan'] = checks['vulkan'] and 'NVIDIA' in (output / 'vulkan.log').read_text()
    report['passed'] = all(checks.values())
    (output / 'preflight.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = run(Path(sys.argv[1]))
    print(json.dumps(report))
    raise SystemExit(0 if report['passed'] else 1)
