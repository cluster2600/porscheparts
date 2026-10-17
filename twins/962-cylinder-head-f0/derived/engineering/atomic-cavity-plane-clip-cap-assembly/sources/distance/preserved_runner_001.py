"""Fail-closed monitor companion; original numerical fixtures stay unchanged.

This version kills/reaps the owned process group after any monitor exception
and retains its refusal. macOS controls remain sampled RSS plus wall deadline,
not a hard address-space/CPU quota. No fixture query is repeated by this change.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
WORKER = Path(__file__).with_name("audit_quality_distance.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")


def monitor(process, started, resources):
    samples = 0; peak = 0; stopped = None; error = None
    cleanup_error = None; reaped = False
    try:
        while process.poll() is None:
            if time.monotonic()-started >= resources["process_group_deadline_seconds"]:
                stopped = "process_group_wall_deadline"
            else:
                observed = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(process.pid)],
                                          capture_output=True, text=True, timeout=2)
                if observed.returncode == 0 and observed.stdout.strip().isdigit():
                    rss = int(observed.stdout)*1024; peak = max(peak, rss); samples += 1
                    if rss > resources["rss_stop_bytes"]:
                        stopped = "observed_worker_RSS_exceeded_4GiB"
                elif process.poll() is None:
                    stopped = "RSS_observation_unavailable"
            if stopped:
                break
            time.sleep(resources["rss_poll_seconds"])
    except BaseException as exc:
        stopped = "monitor_exception_refusal"
        error = type(exc).__name__+": "+str(exc)
    finally:
        # A failed observer must never leave its native worker running.
        try:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=3); reaped = True
        except BaseException as exc:
            stopped = stopped or "cleanup_exception_refusal"
            cleanup_error = type(exc).__name__+": "+str(exc)
    return dict(maximum_observed_worker_RSS_bytes=peak, RSS_samples=samples,
                stopped_by_watchdog=stopped, monitor_error=error,
                cleanup_error=cleanup_error, worker_reaped=reaped,
                worker_running_after_monitor=process.poll() is None)


def run(contract_path, contract_sha256, output):
    if output.exists() or output.is_symlink() or digest(contract_path) != contract_sha256:
        raise ValueError("Exact frozen contract and fresh output required")
    contract = json.loads(contract_path.read_text())
    resources = dict(rss_stop_bytes=4294967296, rss_poll_seconds=.1,
        process_group_deadline_seconds=300, native_library_serial=True,
        thread_environment_limit=2, hard_address_space_quota=False, OS_CPU_quota=False)
    if contract["resources"] != resources or contract["kind"] != "reviewed_head":
        raise ValueError("Reviewed head child and unchanged macOS controls required")
    if contract.get("root_authorised_head_distance") is not True:
        raise ValueError("Head queries require the separate reviewed child freeze")
    pins = dict(contract["input_hashes"], **contract["query_config_hashes"])
    verify = lambda: all(digest(ROOT/path) == sha for path, sha in pins.items())
    if not verify() or contract["input_hashes"].get(str(Path(__file__).relative_to(ROOT))) != digest(Path(__file__)):
        raise ValueError("Frozen source, configuration or runtime changed")
    output.mkdir(parents=True, exist_ok=False)
    (output/"frozen-execution-contract.json").write_bytes(contract_path.read_bytes())
    (output/"controller-executed.py").write_bytes(Path(__file__).read_bytes())
    (output/"worker-executed.py").write_bytes(WORKER.read_bytes())
    env = dict(PATH="/usr/bin:/bin", LANG="C.UTF-8", PYTHONDONTWRITEBYTECODE="1",
               OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2",
               VECLIB_MAXIMUM_THREADS="2", NUMEXPR_NUM_THREADS="2")
    rows = []
    for query_path in contract["queries"]:
        if not verify():
            raise ValueError("Frozen inputs drifted; subsequent query refused")
        config = json.loads((ROOT/query_path).read_text())
        directory = output/config["id"]
        directory.mkdir(exist_ok=False)
        command = [contract["python"], "-B", str(WORKER), "--worker",
                   str(contract_path), str(ROOT/query_path), str(directory/"worker-report.json")]
        receipt = dict(query=config["id"], command=command, environment=env,
            resources=resources, contract_sha256=contract_sha256,
            config_sha256=digest(ROOT/query_path), status="running",
            hard_address_space_quota_established=False, OS_CPU_quota_established=False)
        save(directory/"running-receipt.json", receipt)
        started = time.monotonic(); process = timer = None; error = None
        stopped = {'reason': None}; lock = threading.Lock(); samples = []
        cleanup_error = None; reaped = False; sigterm_requested = False
        def stop(reason):
            with lock:
                if stopped['reason'] is None:
                    stopped['reason'] = reason
                    if process is not None:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
        def request_sigterm(*_):
            nonlocal sigterm_requested
            sigterm_requested = True
        previous_sigterm = signal.getsignal(signal.SIGTERM)
        try:
            with (directory/"native.log").open("x") as stream:
                try:
                    signal.signal(signal.SIGTERM, request_sigterm)
                    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
                        stderr=subprocess.STDOUT, start_new_session=True)
                    timer = threading.Timer(max(0., resources['process_group_deadline_seconds']-
                        (time.monotonic()-started)), lambda: stop('process_group_wall_deadline'))
                    timer.daemon = True; timer.start()
                    while process.poll() is None and not sigterm_requested:
                        try:
                            observed = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', str(process.pid)],
                                capture_output=True, text=True, timeout=2)
                            if process.poll() is not None:
                                break
                            if observed.returncode != 0 or not observed.stdout.strip().isdigit():
                                raise ValueError('RSS observation unavailable')
                            rss = int(observed.stdout.strip())*1024; samples.append(rss)
                            if rss >= resources['rss_stop_bytes']:
                                stop('observed_worker_RSS_exceeded_4GiB')
                        except (OSError, ValueError, subprocess.SubprocessError):
                            if process.poll() is None:
                                stop('RSS_observation_unavailable')
                        try:
                            process.wait(timeout=resources['rss_poll_seconds'])
                        except subprocess.TimeoutExpired:
                            pass
                finally:
                    try:
                        if timer is not None:
                            timer.cancel()
                        if process is not None:
                            if process.poll() is None:
                                stop('controller_SIGTERM' if sigterm_requested else 'controller_interrupted')
                            process.wait(); reaped = True
                    except BaseException as exc:
                        cleanup_error = type(exc).__name__+': '+str(exc)
                    finally:
                        if sigterm_requested and stopped['reason'] is None:
                            stopped['reason'] = 'controller_SIGTERM'
                        signal.signal(signal.SIGTERM, previous_sigterm)
        except BaseException as exc:
            error = type(exc).__name__+': '+str(exc)
        observation = dict(maximum_observed_worker_RSS_bytes=max(samples, default=0),
            RSS_samples=len(samples), stopped_by_watchdog=stopped['reason'], monitor_error=error,
            cleanup_error=cleanup_error, worker_reaped=reaped,
            worker_running_after_monitor=process.poll() is None if process is not None else False,
            SIGTERM_requested=sigterm_requested,
            SIGTERM_handler_restored=signal.getsignal(signal.SIGTERM) == previous_sigterm)
        receipt.update(status="finished", returncode=process.returncode if process is not None else None,
            wall_seconds=time.monotonic()-started, **observation,
            all_bound_inputs_unchanged=verify(),
            artifact_sha256={p.name: digest(p) for p in directory.iterdir() if p.is_file()})
        save(directory/"execution-receipt.json", receipt); rows.append(receipt)
        print(json.dumps({key: receipt[key] for key in ("query", "returncode", "wall_seconds",
              "maximum_observed_worker_RSS_bytes", "stopped_by_watchdog", "monitor_error", "worker_reaped")}), flush=True)
        if (process is None or process.returncode != 0 or observation["stopped_by_watchdog"]
                or observation["monitor_error"] or observation["cleanup_error"]
                or not observation["SIGTERM_handler_restored"] or not receipt["all_bound_inputs_unchanged"]):
            break
    complete = len(rows) == len(contract["queries"]) and all(
        r["returncode"] == 0 and not r["stopped_by_watchdog"] and r["worker_reaped"]
        and not r["monitor_error"] and not r["cleanup_error"] and r["SIGTERM_handler_restored"]
        and not r["worker_running_after_monitor"] and r["all_bound_inputs_unchanged"] for r in rows)
    result = dict(status="native_queries_completed_assessment_pending" if complete else "native_query_failure_retained",
        contract_sha256=contract_sha256, completed_queries=len(rows),
        planned_queries=len(contract["queries"]), all_bound_inputs_unchanged=verify(),
        native_queries_completed=complete, independent_distance_gate_passed=False,
        engineering_accepted=False, manufacturing_authorized=False,
        execution_receipt_sha256={str(p.relative_to(output)): digest(p)
            for p in output.glob("*/execution-receipt.json")})
    save(output/"execution-summary.json", result)
    return 0 if complete else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.contract.resolve(), args.contract_sha256, args.output.resolve()))
