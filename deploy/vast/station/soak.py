#!/usr/bin/env python3
"""Run the real 30-minute station qualification as root; never manages rentals.

Only the Qwen HTTP client opens a network connection, exclusively on loopback.
--self-check exercises parsers, not the station or its qualification result.
"""
import concurrent.futures
import csv
import datetime
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request

DURATION = 1800
SAMPLE_INTERVAL = 15
MODEL = 'qwen3.8-flash-next-uncensored-nvfp4'
OUTPUT = Path('/workspace/qualification/soak')
JOBS = Path('/workspace/jobs')


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def supervisor_pids(text):
    result = {}
    for line in text.splitlines():
        match = re.fullmatch(r'(qwen|kit)\s+RUNNING\s+pid (\d+), uptime .+', line.strip())
        if not match or int(match[2]) <= 0:
            raise ValueError('Qwen and Kit must both be RUNNING: ' + line)
        result[match[1]] = int(match[2])
    if set(result) != {'qwen', 'kit'}:
        raise ValueError('both supervisor processes must be observed')
    return result


def gpu_memory(text):
    rows = []
    for row in csv.reader(text.splitlines()):
        index, uuid, total, used, utilization = [v.strip() for v in row]
        total, used = int(total), int(used)
        if total <= 0 or not 0 <= used <= total:
            raise ValueError('invalid GPU memory accounting')
        rows.append(dict(index=int(index), uuid=uuid, total_mib=total, used_mib=used,
                         used_fraction=used / total, utilization_percent=int(utilization)))
    if {row['index'] for row in rows} != {0, 1, 2, 3} or len(rows) != 4:
        raise ValueError('four GPUs must remain visible')
    return rows


def memory_counters():
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in {'MemTotal', 'MemAvailable'}:
            memory[key] = int(value.split()[0]) * 1024
    root = Path('/sys/fs/cgroup')
    if (root / 'memory.events').is_file():
        events = dict(line.split() for line in (root / 'memory.events').read_text().splitlines())
        oom = {key: int(events[key]) for key in ('oom', 'oom_kill')}
        limit = (root / 'memory.max').read_text().strip()
        used = int((root / 'memory.current').read_text())
    else:
        root /= 'memory'
        events = dict(line.split() for line in (root / 'memory.oom_control').read_text().splitlines())
        oom = {'oom_kill': int(events['oom_kill']),
               'allocation_failures': int((root / 'memory.failcnt').read_text())}
        limit = (root / 'memory.limit_in_bytes').read_text().strip()
        used = int((root / 'memory.usage_in_bytes').read_text())
    if limit != 'max':
        memory['MemTotal'] = min(memory['MemTotal'], int(limit))
        memory['MemAvailable'] = min(memory['MemAvailable'], max(0, int(limit) - used))
    if memory['MemTotal'] <= 0 or memory['MemAvailable'] < 0:
        raise ValueError('invalid system memory accounting')
    return dict(effective_total_bytes=memory['MemTotal'], available_bytes=memory['MemAvailable'],
                available_fraction=memory['MemAvailable'] / memory['MemTotal'],
                cgroup_current_bytes=used, cgroup_limit=limit, oom=oom)


def snapshot():
    states = subprocess.check_output(['supervisorctl', '-c', '/opt/station/supervisord.conf',
                                      'status', 'qwen', 'kit'], text=True, timeout=10)
    gpus = subprocess.check_output(['nvidia-smi',
        '--query-gpu=index,uuid,memory.total,memory.used,utilization.gpu',
        '--format=csv,noheader,nounits'], text=True, timeout=10)
    return dict(pids=supervisor_pids(states), gpus=gpu_memory(gpus), memory=memory_counters())


def infer(batch, slot):
    started = time.monotonic()
    request = urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',
        headers={'Content-Type': 'application/json'}, data=json.dumps({
            'model': MODEL, 'temperature': 0, 'max_tokens': 128,
            'messages': [{'role': 'user', 'content':
                f'Qualification lot {batch}, requête {slot}. Explique en français trois contrôles '
                'géométriques avant une impression métal EOS M 290. Ne prétends pas qualifier la fabrication.'}]
        }).encode())
    # Ignore proxy environment settings and reject redirects away from loopback.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=50) as response:
        data = json.loads(response.read(1024 * 1024))
    elapsed = time.monotonic() - started
    usage = data['usage']
    if (data.get('model') != MODEL or not data.get('choices') or
            type(usage.get('completion_tokens')) is not int or usage['completion_tokens'] <= 0 or
            type(usage.get('prompt_tokens')) is not int or usage['prompt_tokens'] <= 0):
        raise ValueError('Qwen response lacks the expected model, choices or measured token usage')
    return dict(batch=batch, slot=slot, duration_seconds=elapsed, usage=usage,
                completion_tokens_per_second=usage['completion_tokens'] / elapsed,
                finish_reason=data['choices'][0]['finish_reason'])


def pipeline(job, span, worker, stop, deadline, emit):
    work = JOBS / job
    work.mkdir(mode=0o750)
    os.chown(work, worker.pw_uid, worker.pw_gid)
    started = time.monotonic()
    environment = dict(PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                       HOME=worker.pw_dir, USER=worker.pw_name, LOGNAME=worker.pw_name,
                       DOTNET_ROOT='/usr/share/dotnet', DOTNET_CLI_TELEMETRY_OPTOUT='1',
                       PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', MPLBACKEND='Agg')
    commands = [('demo', ['/usr/local/bin/station-demo', str(work / 'output'),
                          '--span-mm', str(span), '--voxel-mm', '0.25']),
                ('render', ['/usr/local/bin/station-render',
                            str(work / 'output/station-assembly.usda'), str(work / 'render.png')])]
    for action, command in commands:
        action_start = time.monotonic()
        state = dict(action=action, job=job, span_mm=span, voxel_mm=0.25,
                     updated_epoch=time.time(), status='starting')
        state_path = work / (action + '.json')
        atomic_json(state_path, state)
        process = None
        try:
            if stop.is_set() or action_start >= deadline:
                raise RuntimeError('qualification stopped before starting action')
            with (work / (action + '.log')).open('xb') as log:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, cwd=work, env=environment, start_new_session=True,
                    user=worker.pw_uid, group=worker.pw_gid, extra_groups=[])
                state.update(status='running', pid=process.pid)
                atomic_json(state_path, state)
                while process.poll() is None:
                    if stop.wait(0.25) or time.monotonic() >= min(deadline, action_start + 600):
                        raise RuntimeError('action interrupted or exceeded its deadline')
                if process.returncode != 0:
                    raise RuntimeError(f'{action} exited {process.returncode}')
            if action == 'demo':
                receipt = json.loads((work / 'output/completed.json').read_text())
                if receipt.get('status') != 'software_pipeline_completed':
                    raise ValueError('demo completion receipt missing')
            elif (work / 'render.png').read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
                raise ValueError('render PNG missing')
            state.update(status='complete', returncode=0)
        except Exception as error:
            state.update(status='failed', error=str(error))
            raise
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            state.update(duration_seconds=time.monotonic() - action_start, updated_epoch=time.time())
            atomic_json(state_path, state)
            archive = OUTPUT / job
            archive.mkdir(exist_ok=True)
            shutil.copyfile(state_path, archive / state_path.name)
            if (work / (action + '.log')).is_file():
                shutil.copyfile(work / (action + '.log'), archive / (action + '.log'))
            emit('pipeline_action', **state)
    return dict(job=job, span_mm=span, duration_seconds=time.monotonic() - started)


def run():
    if os.geteuid() != 0:
        raise ValueError('root controller required to inspect supervisor and drop worker privileges')
    worker = pwd.getpwnam('station-worker')
    if worker.pw_uid != 10002:
        raise ValueError('station-worker must have uid 10002')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    deadline = started + DURATION
    stop = threading.Event()
    lock = threading.Lock()
    report = dict(status='RUNNING', passed=False, duration_required_seconds=DURATION, model=MODEL,
                  start_epoch=time.time(), errors=[], inference=[], pipelines=[], samples=[],
                  manufacturing_validated=False)
    atomic_json(OUTPUT / 'report.json', report)

    def emit(kind, **data):
        with lock, (OUTPUT / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(kind=kind, elapsed_seconds=time.monotonic() - started,
                                         observed_epoch=time.time(), **data)) + '\n')

    def interrupted(number, frame):
        report['errors'].append(f'interrupted by signal {number}')
        stop.set()
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, interrupted)
    llm = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    geometry = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    futures, pipeline_future = [], None
    baseline, batch, next_sample, next_batch = None, 0, started, started
    last_pipeline_seconds, job_number = 45, 0
    prefix = 'soak-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
    try:
        while not stop.is_set() and time.monotonic() < deadline:
            now = time.monotonic()
            for future in list(futures):
                if future.done():
                    result = future.result()
                    report['inference'].append(result)
                    emit('inference', **result)
                    futures.remove(future)
            if pipeline_future is not None and pipeline_future.done():
                result = pipeline_future.result()
                report['pipelines'].append(result)
                emit('pipeline_complete', **result)
                last_pipeline_seconds = max(last_pipeline_seconds, result['duration_seconds'])
                pipeline_future = None
            if now >= next_sample:
                measured = snapshot()
                measured['elapsed_seconds'] = time.monotonic() - started
                report['samples'].append(measured)
                emit('resources', measurement=measured)
                if baseline is None:
                    baseline = measured
                if measured['pids'] != baseline['pids']:
                    raise ValueError('Qwen or Kit PID changed during qualification')
                if measured['memory']['oom'] != baseline['memory']['oom']:
                    raise ValueError('cgroup OOM/allocation failure counters changed')
                if measured['memory']['available_fraction'] <= 0.02:
                    raise ValueError('available RAM fell to 2% or less')
                if any(gpu['used_fraction'] >= 0.98 for gpu in measured['gpus']):
                    raise ValueError('GPU memory reached 98% or more')
                next_sample += SAMPLE_INTERVAL
            if now >= next_batch:
                if futures or now - next_batch >= SAMPLE_INTERVAL:
                    raise ValueError('four-request Qwen batch missed its one-minute cadence')
                emit('batch_started', batch=batch, concurrency=4)
                futures = [llm.submit(infer, batch, slot) for slot in range(4)]
                batch += 1
                next_batch += 60
            # Reserve twice the longest observed pipeline plus a margin so no
            # new GPU task needs to start after the 30-minute deadline.
            if pipeline_future is None and deadline - now > 2 * last_pipeline_seconds + 30:
                job_number += 1
                span = (20, 30, 40)[(job_number - 1) % 3]
                pipeline_future = geometry.submit(pipeline, f'{prefix}-{job_number:03}',
                                                   span, worker, stop, deadline, emit)
            stop.wait(min(0.5, max(0, deadline - time.monotonic())))
        if stop.is_set():
            raise RuntimeError('qualification interrupted')
        for future in futures:
            result = future.result(timeout=1)
            report['inference'].append(result)
            emit('inference', **result)
        if pipeline_future is not None:
            result = pipeline_future.result(timeout=1)
            report['pipelines'].append(result)
            emit('pipeline_complete', **result)
        final = snapshot()
        final['elapsed_seconds'] = time.monotonic() - started
        report['samples'].append(final)
        emit('resources', measurement=final)
        samples = report['samples']
        gaps = [b['elapsed_seconds'] - a['elapsed_seconds'] for a, b in zip(samples, samples[1:])]
        report['checks'] = dict(
            full_1800_seconds=time.monotonic() - started >= DURATION,
            thirty_four_request_batches=batch == 30 and len(report['inference']) == 120,
            repeated_geometry_and_renders={p['span_mm'] for p in report['pipelines']} == {20, 30, 40},
            sample_gap_at_most_30_seconds=bool(gaps) and max(gaps) <= 30,
            stable_service_pids=all(s['pids'] == baseline['pids'] for s in samples),
            no_new_oom=all(s['memory']['oom'] == baseline['memory']['oom'] for s in samples),
            ram_available_above_2_percent=all(s['memory']['available_fraction'] > 0.02 for s in samples),
            gpu_memory_below_98_percent=all(g['used_fraction'] < 0.98 for s in samples for g in s['gpus']))
        if not all(report['checks'].values()):
            raise RuntimeError('one or more qualification checks failed')
        report.update(status='PASS', passed=True)
    except Exception as error:
        report['errors'].append(str(error))
        emit('error', error=str(error))
        report.update(status='FAIL', passed=False)
    finally:
        stop.set()
        llm.shutdown(wait=True, cancel_futures=True)
        geometry.shutdown(wait=True, cancel_futures=True)
        if report['errors']:
            report.update(status='FAIL', passed=False)
        report.update(duration_seconds=time.monotonic() - started, end_epoch=time.time())
        report['summary'] = dict(
            successful_requests=len(report['inference']), completed_pipelines=len(report['pipelines']),
            completion_tokens=sum(r['usage']['completion_tokens'] for r in report['inference']),
            maximum_gpu_memory_fraction=max((g['used_fraction'] for s in report['samples']
                                             for g in s['gpus']), default=None),
            minimum_ram_available_bytes=min((s['memory']['available_bytes']
                                             for s in report['samples']), default=None))
        atomic_json(OUTPUT / 'report.json', report)
    print(json.dumps(dict(status=report['status'], passed=report['passed'],
                         duration_seconds=report['duration_seconds'], directory=str(OUTPUT),
                         errors=report['errors'])))
    return 0 if report['passed'] else 1


def self_check():
    assert DURATION == 1800
    assert supervisor_pids('qwen RUNNING pid 123, uptime 0:01:00\nkit RUNNING pid 456, uptime 0:01:00') == {'qwen': 123, 'kit': 456}
    try:
        supervisor_pids('qwen STOPPED\nkit RUNNING pid 456, uptime 0:01:00')
    except ValueError:
        pass
    else:
        raise AssertionError('stopped service accepted')
    rows = gpu_memory('\n'.join(f'{i}, GPU-{i}, 96000, 48000, 10' for i in range(4)))
    assert all(row['used_fraction'] == 0.5 for row in rows)
    assert 128 / 2.0 == 64.0
    print('Parser self-check PASS; no GPU qualification was performed.')


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-check']:
        self_check()
    elif sys.argv[1:]:
        raise SystemExit('Usage: soak.py [--self-check]')
    else:
        raise SystemExit(run())
