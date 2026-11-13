"""Finite full-run supervision; outer SIGTERM follows exact owned-group cleanup."""
from pathlib import Path
import json
import os
import shutil
import signal
import subprocess
import time
import common

WALL_SECONDS = 7200
RSS_BYTES = 8 * 1024**3
RESERVE_BYTES = 8 * 1024**3


def supervise(command, runroot, verify_sources, storage_parent, contract_sha256):
    runroot = Path(runroot)
    cleanup_module = common.module('unchanged_full_owned_group', common.LAYER / 'owned_process_group.py')
    child, cleanup, error, reason, peak = None, None, None, 'complete', 0
    events, failed = [], 0
    started = time.monotonic()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    def interrupted(signum, _frame):
        raise InterruptedError('Supervisor received signal ' + str(signum))
    for sig in previous:
        signal.signal(sig, interrupted)
    try:
        verify_sources()
        with (runroot/'stdout.log').open('x') as stdout, (runroot/'stderr.log').open('x') as stderr:
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', LC_ALL='C', OPENBLAS_NUM_THREADS='1',
                       OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
            child = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
            common.write(runroot/'process.json', dict(pid=child.pid, pgid=child.pid, supervisor_pid=os.getpid()))
            while child.poll() is None:
                elapsed = time.monotonic()-started
                free = shutil.disk_usage(storage_parent).free
                rss = None
                try:
                    state = subprocess.run(['/bin/ps','-axo','pid=,pgid=,rss='],
                                           capture_output=True,text=True,check=True,timeout=5)
                    rss = sum(int(row.split()[2])*1024 for row in state.stdout.splitlines()
                              if len(row.split())==3 and int(row.split()[1])==child.pid)
                    peak=max(peak,rss);failed=0
                except (subprocess.TimeoutExpired,subprocess.CalledProcessError) as exc:
                    failed+=1;events.append(dict(elapsed_seconds=elapsed,event=type(exc).__name__,consecutive=failed))
                observation=dict(elapsed_seconds=elapsed,group_RSS_bytes=rss,peak_group_RSS_bytes=peak,free_bytes=free,telemetry_events=events)
                (runroot/'observation.json').write_text(json.dumps(observation,indent=2)+'\n')
                if elapsed>WALL_SECONDS or free<RESERVE_BYTES or (rss is not None and rss>RSS_BYTES) or failed>=3:
                    reason='finite_resource_or_observer_guard';break
                time.sleep(2)
    except InterruptedError as exc:
        error=repr(exc);reason='supervisor_interrupted'
    except BaseException as exc:
        error=repr(exc);reason='supervisor_error'
    finally:
        # A repeated outer TERM must not interrupt the finite exact-group cleanup.
        for sig in previous:
            signal.signal(sig,signal.SIG_IGN)
        if child is not None:
            try:
                cleanup=cleanup_module.cleanup_owned_group(child,child.pid)
                if not (cleanup['group_absent'] and cleanup['direct_child_reaped'] and cleanup['only_exact_owned_group_signaled']):
                    raise RuntimeError('Exact owned group closure failed')
            except BaseException as exc:
                error=repr(exc);reason='owned_group_cleanup_failed'
        if child is not None and child.returncode!=0 and reason=='complete':reason='worker_return_nonzero'
        try:
            verify_sources();unchanged=True
        except BaseException as exc:
            unchanged=False;error=repr(exc);reason='prepared_source_changed'
        report=dict(actual_returncode=None if child is None else child.returncode,
                    child_reaped=child is not None and child.returncode is not None,
                    reason=reason,error=error,elapsed_seconds=time.monotonic()-started,
                    peak_group_RSS_bytes=peak,telemetry_events=events,
                    prepared_sources_unchanged=unchanged,owned_group_cleanup=cleanup,contract_sha256=contract_sha256,new_paid_action=False)
        common.write(runroot/'terminal.json',report)
        for sig,handler in previous.items():signal.signal(sig,handler)
    return report
