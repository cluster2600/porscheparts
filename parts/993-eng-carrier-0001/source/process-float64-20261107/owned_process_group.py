"""Bounded cleanup of one freshly owned start_new_session process group."""
import math
import os
import signal
import subprocess
import time


def _members(pgid):
    # Same exact-group ownership checks as the qualified current24af supervisor.
    if pgid <= 1 or pgid == os.getpgrp():
        raise ValueError('Only the newly created child group may be queried')
    result = subprocess.run(['/bin/ps', '-g', str(pgid), '-o', 'pid=,ppid=,pgid=,stat='],
                            capture_output=True, text=True, timeout=1)
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return []
    if result.returncode != 0 or result.stderr.strip():
        raise ValueError('Owned group query was not confirmed')
    rows = []
    for line in result.stdout.splitlines():
        pid, ppid, group, state = line.split()
        pid, ppid, group = int(pid), int(ppid), int(group)
        if group != pgid:
            raise ValueError('Process group query returned an unrelated process')
        if pid == pgid and ppid != os.getpid():
            raise ValueError('The leader PID was recycled outside this supervisor')
        try:
            if os.getpgid(pid) != pgid or os.getsid(pid) != pgid:
                raise ValueError('A group member is outside the owned session')
        except ProcessLookupError:
            continue
        rows.append(dict(pid=pid, ppid=ppid, pgid=group, state=state))
    return rows


def cleanup_owned_group(child, pgid, term_seconds=5, kill_seconds=5):
    """Reap the direct child and require complete group absence, even after its exit.

    The caller must own this fresh Popen child, created with start_new_session=True.
    This API never discovers or adopts a group by command/name matching.
    Ownership/query errors raise before any unverified signal.
    """
    if type(pgid) is not int or pgid != child.pid or pgid <= 1 or pgid == os.getpgrp():
        raise ValueError('Exact newly owned child PID/PGID required')
    if any(not math.isfinite(float(x)) or not 0 < x <= 5 for x in (term_seconds, kill_seconds)):
        raise ValueError('Cleanup phases must each be positive and at most five seconds')
    started = time.monotonic()
    signals, observations = [], []
    initial_returncode = child.poll()
    if initial_returncode is None:
        try:
            if os.getpgid(child.pid) != pgid or os.getsid(child.pid) != pgid:
                raise ValueError('Direct child was not created in its own session')
        except ProcessLookupError:
            child.poll()

    def sample():
        child.poll()  # Reap a dead leader before checking for any remaining descendants.
        rows = _members(pgid)
        observations.append(dict(elapsed_seconds=time.monotonic()-started, members=rows))
        return rows

    def send(signum):
        rows = sample()
        if not any(not row['state'].startswith('Z') for row in rows):
            return
        event = dict(pgid=pgid, signal=int(signum), members_before=rows)
        try:
            os.killpg(pgid, signum)
            event['sent'] = True
        except ProcessLookupError:
            event['sent'] = False
            event['group_disappeared_before_signal'] = True
        signals.append(event)

    def await_absence(seconds):
        deadline = time.monotonic() + seconds
        rows = sample()
        while rows and time.monotonic() < deadline:
            time.sleep(min(.025, max(0., deadline-time.monotonic())))
            rows = sample()
        return rows

    initial_members = sample()
    remaining = initial_members
    if remaining:
        send(signal.SIGTERM)
        remaining = await_absence(term_seconds)
    if remaining:
        send(signal.SIGKILL)
        remaining = await_absence(kill_seconds)
    child.poll()
    if child.returncode is not None:
        child.wait(timeout=.1)
    final_members = sample()
    reaped = child.returncode is not None
    return dict(status='owned_group_absent_and_direct_child_reaped' if not final_members and reaped
                else 'owned_group_cleanup_incomplete',
                pgid=pgid, direct_child_pid=child.pid, initial_returncode=initial_returncode,
                direct_child_returncode=child.returncode, direct_child_reaped=reaped,
                group_absent=not final_members, all_owned_group_members_absent=not final_members,
                initial_members=initial_members, final_members=final_members, signals=signals,
                observations=observations, term_seconds=term_seconds, kill_seconds=kill_seconds,
                elapsed_seconds=time.monotonic()-started,
                only_exact_owned_group_signaled=all(row['pgid']==pgid for row in signals))
