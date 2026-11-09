"""Bounded macOS syscall diagnostic; no historical controller is executed."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import sys
import time


def signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
        return {"signal": int(sig), "errno": None}
    except OSError as exc:
        return {"signal": int(sig), "errno": exc.errno}


def reap(pid, flags, seconds=2):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        found, status = os.waitpid(pid, flags | os.WNOHANG)
        if found:
            return status
        time.sleep(0.005)
    raise TimeoutError("owned-child wait exceeded bound")


def trial(mode):
    record = {"mode": mode, "signals": [], "reaped": False, "group_absent": None}
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            signal.signal(signal.SIGTERM, signal.SIG_IGN if mode == "ignore-term" else signal.SIG_DFL)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            signal.alarm(10)
            os.kill(os.getpid(), signal.SIGSTOP)
            if mode == "already-exited":
                os._exit(0)
            while True:
                signal.pause()
        finally:
            os._exit(97)
    certified = False
    try:
        status = reap(pid, os.WUNTRACED)
        record["reaped"] = os.WIFEXITED(status) or os.WIFSIGNALED(status)
        assert os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP
        certificate = {"pid": pid, "pgid": os.getpgid(pid), "sid": os.getsid(pid)}
        assert certificate["pid"] == certificate["pgid"] == certificate["sid"]
        certified = True
        record["certificate"] = certificate
        with closing(select.kqueue()) as queue:
            event = select.kevent(pid, filter=select.KQ_FILTER_PROC,
                                 flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE | select.KQ_EV_ONESHOT,
                                 fflags=select.KQ_NOTE_EXIT)
            assert not queue.control([event], 1, 0)
            os.kill(pid, signal.SIGCONT)
            if mode != "already-exited":
                record["signals"].append(signal_group(pid, signal.SIGTERM))
            if mode == "ignore-term":
                assert not queue.control(None, 1, 0.05)
                record["signals"].append(signal_group(pid, signal.SIGKILL))
            events = queue.control(None, 1, 2)
            assert len(events) == 1 and events[0].ident == pid
            assert events[0].fflags & select.KQ_NOTE_EXIT and not events[0].flags & select.KQ_EV_ERROR
            record["note_exit"] = True
            if mode == "already-exited":
                record["signals"].append(signal_group(pid, signal.SIGTERM))
            if mode != "ignore-term":
                record["signals"].append(signal_group(pid, signal.SIGKILL))
            status = reap(pid, 0)
            record["reaped"] = True
            record["returncode"] = os.waitstatus_to_exitcode(status)
            assert record["returncode"] == {"already-exited": 0, "live-term": -15, "ignore-term": -9}[mode]
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            record["group_absent"] = True
        else:
            record["group_absent"] = False
    except ChildProcessError as exc:
        record["ownership_lost"] = True
        record["error"] = type(exc).__name__ + ": " + str(exc)
    except BaseException as exc:
        record["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if not record["reaped"] and not record.get("ownership_lost"):
            try:
                if certified:
                    record["cleanup_signal"] = signal_group(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)
                record["cleanup_status"] = reap(pid, 0)
                record["reaped"] = True
            except BaseException as exc:
                record["cleanup_error"] = type(exc).__name__ + ": " + str(exc)
    return record


if __name__ == "__main__":
    assert sys.platform == "darwin" and sys.version_info[:3] == (3, 10, 11)
    assert sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
    assert signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL
    output = Path(sys.argv[1])
    output.mkdir(mode=0o700)
    start = time.monotonic()
    results = []
    for mode in ("already-exited", "live-term", "ignore-term"):
        assert time.monotonic() - start < 30
        results.append(trial(mode))
        if results[-1].get("error") or results[-1].get("cleanup_error"):
            break
    report = {"schema": "962-owned-group-diagnostic/v1", "results": results,
              "seconds": time.monotonic() - start,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "controller_qualified": False, "engineering_phase_accepted": False,
              "manufacturing_authorized": False}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    assert len(results) == 3 and all(r["reaped"] and r["group_absent"] is True and not r.get("error") for r in results)
    assert time.monotonic() - start < 30
