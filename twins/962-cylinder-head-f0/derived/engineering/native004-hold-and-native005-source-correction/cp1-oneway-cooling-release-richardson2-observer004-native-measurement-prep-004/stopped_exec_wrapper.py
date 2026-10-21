"""HELD/UNRUN same-PID stopped wrapper for the fixed owned native capture."""
import time
ENTRY_NS = time.monotonic_ns()
import hashlib, json, os, re, signal, sys
from pathlib import Path

ROOT = Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993")
E = ROOT/"work/962-engineering"
S = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-004"
P = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-004"
D = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-004"
PY = "/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python"
RESOLVED = "/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12"


def token(value):
    now = time.monotonic_ns()
    if type(value) is not str or not re.fullmatch("[1-9][0-9]*",value,flags=re.ASCII):
        raise ValueError("Canonical ASCII owner-start token required")
    if len(value) > len(str(now)):
        raise ValueError("Future/oversize token")
    result = int(value)
    if str(result) != value or not 0 < result <= now:
        raise ValueError("Future/noncanonical token")
    return result


def guard(until):
    if time.monotonic_ns() >= until:
        raise ValueError("Wrapper original normal95 deadline")


def record(path,until):
    guard(until)
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != path:
        raise ValueError("Canonical fixed wrapper/control source required")
    guard(until)
    data = path.read_bytes()
    guard(until)
    return dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))


def read_json(path,until):
    guard(until)
    raw = path.read_bytes()
    guard(until)
    def pairs(rows):
        out = {}
        for key,value in rows:
            if key in out:
                raise ValueError("Duplicate key")
            out[key] = value
        return out
    def invalid(value):
        raise ValueError("Nonfinite JSON constant")
    result = json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    guard(until)
    return result


def main():
    if len(sys.argv) != 4 or sys.argv[2] != "--owner-start-ns" or not re.fullmatch("[0-9a-f]{64}",sys.argv[1]):
        raise ValueError("Exact admission digest and literal owner-start token required")
    original = sys.argv[3]
    start = token(original)
    until = start+95_000_000_000
    guard(until)
    if os.path.realpath(sys.executable) != RESOLVED or sys.version_info[:3] != (3,12,11):
        raise ValueError("Exact original3.12 wrapper required")
    if not (sys.flags.isolated == sys.flags.no_site == sys.flags.dont_write_bytecode == 1
            and sys.flags.optimize == 0 and "site" not in sys.modules and "_distutils_hack" not in sys.modules):
        raise ValueError("Exact -B-I-S startup required")
    guard(until)
    pid,pgid,sid = os.getpid(),os.getpgrp(),os.getsid(0)
    guard(until)
    if not pid == pgid == sid:
        raise ValueError("Wrapper is not the new-session leader")
    authorization = D/"authorization.json"
    if record(authorization,until)["sha256"] != sys.argv[1]:
        raise ValueError("Changed external admission")
    auth = read_json(authorization,until)
    if (auth["schema"] != "962-observer004-owned-native-root-admission/v2"
            or auth["native_once_authorized"] is not True or auth["automatic_retry"] is not False):
        raise ValueError("No exact native authority")
    if ("argv" in auth or "authorization_sha256" in auth
            or auth["argv_prefix"] != [PY,"-B","-I","-S",str(S/"stopped_exec_wrapper.py")]):
        raise ValueError("Stable prefix only; admission digest supplied externally")
    actual = P/"actual-contract.json"
    c = read_json(actual,until)
    wrapper_pin = record(S/"stopped_exec_wrapper.py",until)
    caller_pin = record(S/"run_native_capture.py",until)
    actual_pin = record(actual,until)
    if not (auth["direct_roles"]["wrapper"] == wrapper_pin
            and auth["direct_roles"]["caller"] == c["source"] == caller_pin
            and auth["direct_roles"]["actual"] == actual_pin):
        raise ValueError("Wrapper/caller/actual association failed")
    hello = dict(schema="962-observer004-owned-native-wrapper-hello/v1",status="ABOUT_TO_STOP",
                 root_admission_sha256=sys.argv[1],owner_start_ns=original,PID=pid,PGID=pgid,SID=sid,
                 wrapper_source=wrapper_pin,caller_source=caller_pin,caller_actual=actual_pin)
    text = json.dumps(hello,separators=(",",":"),allow_nan=False)
    guard(until)
    sys.stdout.write(text+"\n")
    sys.stdout.flush()
    guard(until)
    os.kill(pid,signal.SIGSTOP)
    # Same PID after parent certification + preregistered NOTE_EXIT + single CONT.
    if token(original) != start:
        raise ValueError("Changed original token")
    guard(until)
    os.execv(PY,[PY,"-B","-I","-S",str(S/"run_native_capture.py"),
        "--stage","coupon","--contract",str(actual),"--contract-sha256",actual_pin["sha256"],
        "--root-admission-sha256",sys.argv[1],"--owner-start-ns",original,"--execute"])
    raise RuntimeError("execv returned unexpectedly")


if __name__ == "__main__":
    main()

