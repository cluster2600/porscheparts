"""One bounded owned process group, derived from retained build_once.py; no admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fresh_path(name):
    path = Path(name)
    if not path.is_absolute():
        path = ROOT/path
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symbolic output paths are refused')
    path = path.resolve()
    if not path.is_relative_to(ROOT/'work') or path.exists():
        raise ValueError('A fresh output below this workspace work directory is required')
    return path


def members(pgid):
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


def living(rows):
    return [row for row in rows if not row['state'].startswith('Z')]


def signal_owned(pgid, signum, events):
    rows = members(pgid)
    if not living(rows):
        return
    try:
        os.killpg(pgid, signum)
        events.append(dict(signal=signum, pgid=pgid, members_before=rows))
    except ProcessLookupError:
        events.append(dict(signal=signum, pgid=pgid, group_disappeared_before_signal=True))


def await_quiet(pgid, deadline):
    rows = members(pgid)
    while living(rows) and time.monotonic() < deadline:
        time.sleep(min(.025, max(0., deadline-time.monotonic())))
        rows = members(pgid)
    return rows


def run(plan_path, expected):
    started = time.monotonic()
    plan_path = Path(plan_path).resolve()
    if sha(plan_path) != expected:
        raise ValueError('Supervision plan identity differs')
    plan = json.loads(plan_path.read_text())
    budget = plan['total_wall_budget_seconds']
    grace = plan['cleanup_grace_seconds']
    if (type(budget) is not int or not 1 <= budget <= 3600 or len(grace) != 2
            or any(type(v) not in (int, float) or not 0 < v <= 10 for v in grace)
            or sum(grace) >= budget or plan['section_workers'] != 1
            or plan['maximum_pending_layers'] != 2 or plan['cwd'] != str(ROOT)):
        raise ValueError('Unexpected supervision bounds, worker count or working directory')
    if (not isinstance(plan['command'], list) or not plan['command']
            or any(not isinstance(word, str) for word in plan['command'])):
        raise ValueError('Only an explicit argv array is accepted')
    diagnostic_output = fresh_path(plan['output_directory'])
    execution = fresh_path(plan['execution_directory'])
    if diagnostic_output == execution or diagnostic_output in execution.parents or execution in diagnostic_output.parents:
        raise ValueError('Diagnostic output and supervision output must be separate')
    if any(plan['source_sha256'][name] != plan['inputs_sha256'][name]
           for name in set(plan['source_sha256']) & set(plan['inputs_sha256'])):
        raise ValueError('Conflicting source and input identities')
    pins = {**plan['source_sha256'], **plan['inputs_sha256']}
    if plan['source_sha256'].get(str(Path(__file__).relative_to(ROOT))) != sha(__file__):
        raise ValueError('The supervisor source must be pinned')
    before = {name: sha(ROOT/name) for name in pins}
    if before != pins or sha(plan_path) != expected:
        raise ValueError('A source, input or plan changed before launch')
    execution.mkdir(parents=True, exist_ok=False)
    deadline = started+budget
    child, timed_out, interrupted, failure, residual = None, False, False, None, []
    events, final_members, cleanup_error = [], None, None
    old_handlers = {}
    def interrupt(signum, frame):
        raise InterruptedError(f'Supervisor received signal {signum}')
    for sig in (signal.SIGTERM, signal.SIGINT):
        old_handlers[sig] = signal.signal(sig, interrupt)
    try:
        if time.monotonic() >= deadline-sum(grace):
            raise TimeoutError('Preparation exhausted the global budget')
        # Recheck both fresh destinations immediately before creating this owned session.
        fresh_path(plan['output_directory'])
        env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        with (execution/'stdout.log').open('xb') as stdout, (execution/'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(['/usr/bin/nice', '-n', '10', *plan['command']],
                cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            if child.pid == os.getpgrp():
                raise ValueError('The child did not receive a private group')
            (execution/'started.json').write_text(json.dumps(dict(pid=child.pid, pgid=child.pid,
                plan_sha256=expected, members=members(child.pid)), indent=2)+'\n')
            try:
                child.wait(timeout=max(0., deadline-sum(grace)-time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
    except BaseException as error:
        interrupted = isinstance(error, (InterruptedError, KeyboardInterrupt))
        failure = dict(type=type(error).__name__, message=str(error))
    finally:
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        if child is not None:
            try:
                # A finished leader is insufficient: inspect remaining owned non-zombie members.
                residual = await_quiet(child.pid, min(deadline-sum(grace), time.monotonic()+.2))
                if living(residual):
                    signal_owned(child.pid, signal.SIGTERM, events)
                    await_quiet(child.pid, min(deadline, time.monotonic()+grace[0]))
                if living(members(child.pid)):
                    signal_owned(child.pid, signal.SIGKILL, events)
                    await_quiet(child.pid, min(deadline, time.monotonic()+grace[1]))
                child.wait(timeout=max(.001, deadline-time.monotonic()))
                final_members = members(child.pid)
            except BaseException as error:
                cleanup_error = dict(type=type(error).__name__, message=str(error))
    after = {}
    for name in pins:
        try:
            after[name] = sha(ROOT/name)
        except OSError:
            after[name] = None
    closed = child is not None and child.returncode is not None and final_members is not None and not living(final_members)
    try:
        plan_after = sha(plan_path)
    except OSError:
        plan_after = None
    unchanged = before == after and plan_after == expected
    executed = (closed and child.returncode == 0 and not timed_out and not interrupted
                and failure is None and cleanup_error is None and not living(residual) and unchanged)
    receipt = dict(schema='owned-local-diagnostic-supervision-1', status='executed' if executed else 'refused_or_interrupted',
        plan_sha256=expected, command=plan['command'], cwd=str(ROOT), pid=None if child is None else child.pid,
        actual_returncode=None if child is None else child.returncode, direct_child_reaped=child is not None and child.returncode is not None,
        total_wall_budget_seconds=budget, cleanup_grace_seconds=grace, timeout=timed_out, interrupted=interrupted,
        budget_scope='Owned group deadline, including preparation and cleanup grace; final group queries and hash I/O add reported overhead, not a universal kernel hard wall.',
        calculation_phase_budget_seconds=budget-sum(grace),
        failure=failure, cleanup_error=cleanup_error, residual_members_before_cleanup=residual,
        signals_to_owned_group_only=events, final_group_members=final_members,
        no_non_zombie_group_members=closed, sources_before=before, sources_after=after, sources_and_plan_unchanged=unchanged,
        source010_or_global_admission=False, elapsed_seconds=time.monotonic()-started,
        output_directory=str(diagnostic_output), process_group_limit='Only PGID from this new Popen; zombie members recorded separately.',
        logs_sha256={n: sha(execution/n) for n in ['stdout.log', 'stderr.log'] if (execution/n).is_file()})
    (execution/'execution-receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=receipt['status'], actual_returncode=receipt['actual_returncode'],
                         no_non_zombie_group_members=closed, elapsed_seconds=receipt['elapsed_seconds'])))
    for sig, previous in old_handlers.items():
        signal.signal(sig, previous)
    return 0 if executed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.plan, args.plan_sha256))
