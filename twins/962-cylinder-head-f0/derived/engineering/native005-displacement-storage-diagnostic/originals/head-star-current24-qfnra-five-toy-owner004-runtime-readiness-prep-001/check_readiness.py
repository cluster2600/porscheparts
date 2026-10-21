"""HELD SOURCE ONLY. One future selected-3.10 readiness process; no child or solver."""
import time
START = time.monotonic()
import fractions, hashlib, importlib.util, json, os, re, resource, select, selectors
import signal, struct, subprocess, sys, traceback
from pathlib import Path

SECONDS = 10
STREAM_CAP = 1048576
BINDINGS = Path(__file__).with_name("bindings.json")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def gate():
    need(time.monotonic() - START < SECONDS, "Readiness process exceeded internal ten-second reservation")


def record_file(pin):
    gate()
    p = Path(pin["path"])
    need(p.is_absolute() and p.is_file() and not p.is_symlink(), "Expected exact regular body only")
    h = hashlib.sha256()
    size = 0
    with p.open("rb") as handle:
        while True:
            gate()
            chunk = handle.read(1048576)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
            need(size <= pin["bytes"], "Body grew beyond fixed expected size")
    value = dict(path=str(p), sha256=h.hexdigest(), bytes=size)
    need(value == pin, "Changed fixed body identity")
    return value


def path_record(path):
    gate()
    p = Path(path)
    linked = p.is_symlink()
    return dict(is_symlink=linked, raw_target=os.readlink(p) if linked else None,
                resolved=str(p.resolve(strict=True)))


def identities(expected):
    bodies = {path: record_file(pin) for path, pin in expected["runtime_files"].items()}
    paths = {path: path_record(path) for path in expected["runtime_path_metadata"]}
    need(paths == expected["runtime_path_metadata"], "Changed cached runtime path metadata")
    z3 = record_file(expected["Z3_body"])
    alias = path_record(expected["Z3_alias_path"])
    need(alias["resolved"] == z3["path"], "Changed exact Z3 alias-to-body route")
    return dict(bodies=bodies, paths=paths, Z3_body=z3, Z3_alias=alias)


def module_origins(expected):
    out = {}
    for name, module in sorted(sys.modules.items()):
        if name == "__main__":
            continue
        gate()
        value = dict(file=getattr(module, "__file__", None),
                     origin=getattr(getattr(module, "__spec__", None), "origin", None))
        need(name in expected and value == expected[name], "Unbound or changed module origin: " + name)
        out[name] = value
    return out


def main():
    report = dict(schema="962-five-toy-owner004-single-process-readiness/v1", status="INCOMPLETE",
                  failure=None, kqueue_create_close=None, child_processes_created=0,
                  Z3_invoked=False, source_modules_imported=False, runtime_root_accepted=False,
                  ownership_event_delivery_or_reap_behavior_proven=False, ABI_qualified=False)
    try:
        need(len(sys.argv) == 2 and re.fullmatch("[0-9a-f]{64}", sys.argv[1]), "Externally pinned expectation digest required")
        raw = BINDINGS.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == sys.argv[1], "Changed expectation metadata")
        expected = json.loads(raw)
        need(expected["schema"] == "962-five-toy-owner004-readiness-expectations/v1" and expected["status"] == "HELD_UNRUN", "Fixed held expectation schema required")
        need(sys.version_info[:3] == (3, 10, 11) and sys.implementation.name == "cpython", "Exact selected CPython3.10.11 required")
        need(sys.executable == expected["selected_interpreter"]["path"] and str(Path(sys.executable).resolve(strict=True)) == expected["selected_interpreter"]["path"], "Changed interpreter route")
        flags = {name: getattr(sys.flags, name) for name in expected["flags"]}
        need(flags == expected["flags"] and "site" not in sys.modules and "_distutils_hack" not in sys.modules, "Exact no-site isolated startup required")
        need(sys.prefix == sys.base_prefix == expected["prefix"] and sys.byteorder == "little" and struct.calcsize("P") == 8, "Changed selected implementation metadata")
        need(all(os.environ.get(k) == v for k, v in expected["environment"].items()), "Fixed thread-one environment required")
        need(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL, "Default SIGCHLD required; no disposition changed")
        before = identities(expected)
        report["before"] = before
        required = {
            "os": ["WUNTRACED", "WNOHANG", "WIFSTOPPED", "WSTOPSIG", "WIFEXITED", "WIFSIGNALED", "waitstatus_to_exitcode", "waitpid", "getpid", "getpgrp", "getpgid", "getsid", "kill", "killpg", "execv", "readlink", "set_blocking", "read", "write", "_exit"],
            "select": ["kqueue", "kevent", "KQ_FILTER_PROC", "KQ_NOTE_EXIT", "KQ_EV_ADD", "KQ_EV_ENABLE", "KQ_EV_ONESHOT", "KQ_EV_ERROR"],
            "signal": ["SIGCHLD", "SIG_DFL", "SIGSTOP", "SIGCONT", "SIGTERM", "SIGKILL", "SIGINT", "getsignal", "signal", "Signals"],
            "resource": ["RLIMIT_CORE", "RLIMIT_FSIZE", "setrlimit"],
            "selectors": ["DefaultSelector", "EVENT_READ", "EVENT_WRITE"],
            "importlib.util": ["spec_from_file_location", "module_from_spec"],
            "subprocess": ["Popen", "run", "PIPE", "DEVNULL", "TimeoutExpired"]}
        modules = {"os": os, "select": select, "signal": signal, "resource": resource,
                   "selectors": selectors, "importlib.util": importlib.util, "subprocess": subprocess}
        report["API_presence"] = {name: {item: hasattr(modules[name], item) for item in items} for name, items in required.items()}
        need(all(all(rows.values()) for rows in report["API_presence"].values()), "Required3.10/platform API unavailable")
        h = hashlib.sha256(); h.update(b"abc")
        need(h.hexdigest() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "Literal SHA256 API check failed")
        kq = None
        try:
            gate(); kq = select.kqueue()
            event = select.kevent(os.getpid(), filter=select.KQ_FILTER_PROC,
                                 flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE | select.KQ_EV_ONESHOT,
                                 fflags=select.KQ_NOTE_EXIT)
            report["kevent_constructed_without_registration"] = dict(ident=event.ident, filter=event.filter, flags=event.flags, fflags=event.fflags)
        finally:
            if kq is not None:
                kq.close(); report["kqueue_create_close"] = True
        gate()
        report["module_origins"] = module_origins(expected["module_origins"])
        report["after"] = identities(expected)
        need(report["after"] == before, "Finite identities or Z3 alias changed during readiness")
        report.update(status="COMPLETE_READINESS_CANDIDATE_ONLY", Python_version_info=list(sys.version_info[:3]),
                      selected_interpreter=expected["selected_interpreter"], declared_provider=expected["selected_provider"],
                      provider_loader_attribution_observed=False, flags=flags, SIGCHLD_default=True,
                      Z3_alias_prior_raw_target_baseline_available=False)
    except BaseException:
        report["failure"] = traceback.format_exc()
    report["elapsed_before_encode_seconds"] = time.monotonic() - START
    encoded = (json.dumps(report, indent=2, allow_nan=False) + "\n").encode()
    if len(encoded) > STREAM_CAP:
        sys.stderr.write("Complete readiness receipt exceeds1MiB; refuse without truncation\n")
        return 2
    sys.stdout.buffer.write(encoded); sys.stdout.buffer.flush()
    return 0 if report["status"] == "COMPLETE_READINESS_CANDIDATE_ONLY" and report["failure"] is None and time.monotonic() - START < SECONDS else 2


if __name__ == "__main__":
    raise SystemExit(main())
