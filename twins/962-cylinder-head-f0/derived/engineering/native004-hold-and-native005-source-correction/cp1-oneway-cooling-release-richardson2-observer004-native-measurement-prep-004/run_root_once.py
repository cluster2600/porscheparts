"""HELD/UNRUN fixed owned-group RICH2 capture. Separate source/API/guard/actual/root gates remain."""
import time
START_NS = time.monotonic_ns()
import hashlib, json, math, os, re, select, signal, subprocess, sys, traceback
from pathlib import Path

ROOT = Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993")
R = ROOT
E = ROOT/"work/962-engineering"
S = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-004"
P = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-004"
ROOT_EXECUTION = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-004"
OUTPUT = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004"
QUERY_ROLE = "GROUP_ROWS"
QUERY_ROOT = ROOT_EXECUTION
_EXTERNAL = {}
_BASELINE = {}


class DeadlineRefusal(BaseException):
    """Control refusal bypassing the six conditionally exact donor catch blocks."""
    def __init__(self, phase, until, observed):
        self.phase = phase
        self.until_ns = str(until)
        self.observed_ns = str(observed)
        super().__init__(phase + ": original deadline reached")


class _RetainedPopen(subprocess.Popen):
    # Applies to leader, native and both fixed-query roles, including partial init.
    def __del__(self):
        pass


_RETAINED = []
_QUERY_RECORDS = []
_STOP_REQUESTS = []
_ERRORS = []
_NORMAL = True
_PHASE = "normal95"
_UNTIL_NS = START_NS + 95_000_000_000
_OWNER_START_NS = START_NS


def guard(until=None, label="control", honor_stop=True):
    bound = _UNTIL_NS if until is None else until
    now = time.monotonic_ns()
    if now >= bound:
        raise DeadlineRefusal(_PHASE + "/" + label, bound, now)
    if honor_stop and _NORMAL and _STOP_REQUESTS:
        raise ValueError("Latched controller stop: " + label)
    return now


def call(until, label, function, *args, honor_stop=True, **kwargs):
    guard(until, label, honor_stop)
    value = function(*args, **kwargs)
    guard(until, label + "/full-return", honor_stop)
    return value


def timeout_seconds(until, maximum_ns):
    remaining = until - guard(until, "timeout")
    value = math.nextafter(min(remaining, maximum_ns) / 1_000_000_000, 0.0)
    if value <= 0:
        raise DeadlineRefusal(_PHASE + "/timeout-conversion", until, time.monotonic_ns())
    return value


def strict_json(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value
    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    return call(None, "strict-json", json.loads, raw,
                object_pairs_hook=pairs, parse_constant=invalid)


def read_json(path, maximum=None):
    size = call(None, "json-stat", path.stat).st_size
    if maximum is not None and size > maximum:
        raise ValueError("JSON exceeds original metadata bound")
    return strict_json(call(None, "read-json", path.read_bytes))


def sha(path):
    h = hashlib.sha256()
    stream = call(None, "hash-open", Path(path).open, "rb")
    try:
        while True:
            block = call(None, "hash-read", stream.read, 1024 * 1024)
            if not block:
                break
            h.update(block)
            guard(label="hash-update")
    finally:
        stream.close()
    guard(label="hash-complete")
    return h.hexdigest()


def rec(path):
    path = Path(path)
    h = hashlib.sha256()
    size = 0
    stream = call(None, "record-open", path.open, "rb")
    try:
        while True:
            block = call(None, "record-read", stream.read, 1024 * 1024)
            if not block:
                break
            size += len(block)
            h.update(block)
            guard(label="record-update")
    finally:
        stream.close()
    return dict(path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                sha256=h.hexdigest(), bytes=size)


def regular(path):
    if call(None, "symlink-check", path.is_symlink):
        raise ValueError("Unexpected symlink: " + str(path))
    if not call(None, "regular-file-check", path.is_file):
        raise ValueError("Missing regular file: " + str(path))
    if call(None, "canonical-path", path.resolve, strict=True) != path:
        raise ValueError("Noncanonical fixed path")
    return path


def selected(pin):
    if type(pin) is not dict or set(pin) != {"path", "sha256", "bytes"}:
        raise ValueError("Exact path/hash/bytes descriptor required")
    if type(pin["path"]) is not str or not re.fullmatch("[0-9a-f]{64}", pin["sha256"]):
        raise ValueError("Invalid descriptor")
    if type(pin["bytes"]) is not int or pin["bytes"] < 0:
        raise ValueError("Invalid descriptor size")
    name = Path(pin["path"])
    if ".." in name.parts:
        raise ValueError("Parent traversal is forbidden")
    path = name if name.is_absolute() else ROOT / name
    if rec(regular(path)) != pin:
        raise ValueError("Changed selected descriptor: " + str(name))
    return path


def file_rows(root):
    if call(None, "owned-root-symlink", root.is_symlink):
        raise ValueError("Owned root is a symlink")
    if not call(None, "owned-root-exists", root.exists):
        return []
    rows = call(None, "owned-walk", lambda: sorted(root.rglob("*")))
    result = []
    for path in rows:
        guard(label="owned-row")
        if call(None, "owned-row-symlink", path.is_symlink):
            raise ValueError("Unexpected owned symlink")
        if call(None, "owned-row-file", path.is_file):
            result.append((path, call(None, "owned-row-size", path.stat).st_size))
    return result


def growth_bytes(output, root_execution, baseline):
    total = 0
    for root in (output, root_execution):
        for path, size in file_rows(root):
            allowance = baseline.get(str(path.relative_to(output)), 0) if root == output else 0
            total += max(0, size - allowance)
    guard(label="growth-complete")
    return total


def inclusive_bytes(external_records):
    files = {str(path): size for root in (OUTPUT, ROOT_EXECUTION) for path, size in file_rows(root)}
    for pin in external_records.values():
        path = Path(pin["path"])
        path = path if path.is_absolute() else ROOT / path
        regular(path)
        files[str(path)] = call(None, "inclusive-external-size", path.stat).st_size
    guard(label="inclusive-complete")
    return sum(files.values())


def budgets(external_records, baseline, pending=0):
    size = inclusive_bytes(external_records)
    growth = growth_bytes(OUTPUT, ROOT_EXECUTION, baseline)
    if size + pending >= 536870912 or growth + pending >= 33554432:
        raise ValueError("Unchanged inclusive512MiB/growth32MiB limit")
    return dict(inclusive_bytes=size, growth_bytes=growth)


def encode(value):
    data = call(None, "full-json-encoding", json.dumps, value, indent=2, allow_nan=False)
    data = (data + "\n").encode("utf-8")
    guard(label="full-json-bytes")
    return data


def write_full(path, data):
    stream = call(None, "exclusive-output-open", path.open, "xb")
    try:
        count = call(None, "full-output-write", stream.write, data)
        if count != len(data):
            raise ValueError("Partial output write retained")
        call(None, "full-output-flush", stream.flush)
    finally:
        stream.close()
    guard(label="output-close")


def exact_reap(handle, record, until):
    # A consumed exact terminal status is the sole recorded reap for this handle.
    if record["status"] == "reaped":
        return True
    guard(until, "exact-WNOHANG-reap", False)
    pid, status = os.waitpid(handle.pid, os.WNOHANG)
    if pid:
        if pid != handle.pid or not (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
            raise ValueError("Unexpected exact terminal wait status")
        raw = os.waitstatus_to_exitcode(status)
        handle.returncode = raw
        record.update(status="reaped", wait_status=status, raw_returncode=raw)
    # Preserve a consumed status even when the syscall itself returned late.
    guard(until, "exact-WNOHANG-reap/full-return", False)
    return pid != 0


def reap_until(handle, record, until):
    while guard(until, "reap-loop", False):
        if exact_reap(handle, record, until):
            return
        call(until, "reap-spacing", time.sleep,
             timeout_seconds(until, 10_000_000), honor_stop=False)


def note_error(exc, label):
    row = dict(type=type(exc).__name__, message=str(exc), phase=_PHASE,
               operation=label, time_ns=str(time.monotonic_ns()),
               traceback=traceback.format_exc())
    _ERRORS.append(row)
    return row


def latch_signal(signum, frame):
    _STOP_REQUESTS.append(dict(signal=signum, name=signal.Signals(signum).name,
                               time_ns=str(time.monotonic_ns())))


def clock_token(token):
    now = time.monotonic_ns()
    if type(token) is not str or not re.fullmatch(r"[1-9][0-9]*", token, flags=re.ASCII):
        raise ValueError("Canonical positive ASCII owner-start token required")
    if len(token) > len(str(now)):
        raise ValueError("Future/oversize owner-start token")
    value = int(token, 10)
    if str(value) != token or not 0 < value <= now:
        raise ValueError("Future/noncanonical owner-start token")
    return value

def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False

def capture(function):
 try:return dict(observed=function(),error=None)
 except Exception as exc:return dict(observed=None,error=repr(exc))

def require(condition, message):
    if not condition:
        raise ValueError(message)


def input_map(c):
    result = {}
    for name, digest in c["input_sha256"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative selected input required")
        pin = rec(regular(ROOT/name))
        require(pin["sha256"] == digest, "Changed selected input")
        result[name] = pin
    return result


def runtime_map(c):
    prefix = E/"moose-local-installed-002"
    files = {}
    links = {}
    for name, digest in c["runtime_sha256s"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative runtime file required")
        pin = rec(regular(prefix/name))
        require(pin["sha256"] == digest, "Changed selected runtime")
        files[name] = pin
    for name, target in c["runtime_symlinks"].items():
        path = prefix/name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative runtime alias required")
        require(call(None,"runtime-link",path.is_symlink)
                and call(None,"runtime-link-target",os.readlink,path) == target, "Changed runtime alias")
        resolved = call(None,"runtime-alias-resolve",path.resolve,strict=True)
        require(resolved.is_relative_to(prefix), "Runtime alias escaped fixed prefix")
        links[name] = dict(raw_target=target,resolved_relative=str(resolved.relative_to(prefix)))
    return dict(files=files,links=links)


def check(records):
    changed = {}
    digest = hashlib.sha256()
    for name,pin in sorted(records.items()):
        path = Path(name) if Path(name).is_absolute() else ROOT/name
        try:
            got = rec(path)
            digest.update(json.dumps(got,sort_keys=True).encode())
            if got != pin:
                changed[name] = dict(expected=pin,actual=got)
        except Exception as exc:
            changed[name] = repr(exc)
    guard(label="host-records-full-return")
    return dict(count=len(records),observed_sha256=digest.hexdigest(),changed=changed)


def provider_links(paths):
    rows = {}
    for name in paths:
        path = Path(name)
        link = call(None,"provider-link",path.is_symlink)
        raw = call(None,"provider-raw-target",os.readlink,path) if link else None
        resolved = call(None,"provider-canonical",path.resolve,strict=True)
        rows[name] = dict(is_symlink=link,raw_target=raw,resolved=str(resolved))
    return rows


def python_record(c):
    path = Path(c["outer_python"]["path"])
    resolved = call(None,"selected-Python-alias",path.resolve,strict=True)
    pin = rec(resolved)
    return dict(path=str(path),resolved_path=str(resolved),sha256=pin["sha256"],bytes=pin["bytes"])


def direct_map(auth):
    result = {}
    for role,pin in auth["direct_roles"].items():
        name = Path(pin["path"])
        require(not name.is_absolute(),"Relative first-party control required")
        result[role] = rec(selected(pin))
    return result


def event_record(event):
    return dict(ident=event.ident,filter=event.filter,flags=event.flags,
                fflags=event.fflags,data=event.data,udata=event.udata)


def caller_evidence(auth,actual,token,pid):
    raw = call(None,"full-adapter-stdout",(ROOT_EXECUTION/"adapter.stdout.log").read_bytes)
    lines = raw.splitlines()
    require(len(lines) == 2 and all(lines),"Exactly two typed adapter stdout lines required")
    hello,terminal = (strict_json(line) for line in lines)
    require(hello["schema"] == "962-observer004-owned-native-wrapper-hello/v1"
            and terminal["schema"] == "962-observer004-owned-native-caller-terminal/v1",
            "Exact wrapper/caller terminal schemas required")
    require(hello["owner_start_ns"] == terminal["owner_start_ns"] == token
            and hello["root_admission_sha256"] == terminal["root_admission_sha256"] ==
            auth["authorization_sha256"],"Exact token/authorization echo required")
    require(type(terminal["caller_PID"]) is int and terminal["caller_PID"] == pid
            and hello["PID"] == hello["PGID"] == hello["SID"] == pid,"Exact same-PID identities required")
    require(hello["wrapper_source"] == auth["direct_roles"]["wrapper"]
            and hello["caller_source"] == actual["source"]
            and hello["caller_actual"] == auth["direct_roles"]["actual"],"Wrapper source/actual join changed")
    require(terminal["prefinal_candidate"] is True,"Caller terminal is not a normal candidate")
    for key in ("caller_receipt_saved_ns","caller_receipt_hashed_ns"):
        require(clock_token(terminal[key]) < START_NS+95_000_000_000,"Late caller receipt/terminal")
    path = selected(terminal["caller_receipt"])
    require(path == OUTPUT/"native-execution.json","Exact caller receipt pathname required")
    value = read_json(path,33554432)
    require(value["schema"] == "962-observer004-owned-native-caller-receipt/v2"
            and value["status"] == "COMPLETE_CANDIDATE" and value["prefinal_candidate"] is True,
            "Complete typed caller candidate required")
    require(value["root_admission_sha256"] == auth["authorization_sha256"]
            and value["actual"] == auth["direct_roles"]["actual"]
            and value["source"] == actual["source"],"Caller receipt source/actual association changed")
    clock = value["clock"]
    for key,stamp in clock.items():
        if stamp is not None:
            clock_token(stamp)
    require(clock["owner_start_ns"] == token
            and int(clock["normal_until_ns"]) ==
            min(START_NS+95_000_000_000,int(clock["caller_entry_ns"])+100_000_000_000),
            "Shared original caller deadline mismatch")
    require(int(clock["caller_entry_ns"]) >= START_NS
            and int(clock["caller_entry_ns"]) <= int(clock["native_spawn_ns"])
            <= int(clock["receipt_encoding_started_ns"])
            <= int(terminal["caller_receipt_saved_ns"])
            <= int(terminal["caller_receipt_hashed_ns"]) < int(clock["normal_until_ns"]),
            "Caller source/complete-write/hash timing association failed")
    require(value["caller_identity"] == dict(PID=pid,PGID=pid,SID=pid),"Caller identity changed")
    native = value["native"]
    require(native["spawn_attempted"] is True and type(native["PID"]) is int and native["PID"] > 0
            and native["start_new_session"] is False and native["preexec_fn_used"] is False,
            "Exactly one inherited native identity required")
    observed = native["identity_observation"]
    require((observed["PID"],observed["PPID"],observed["PGID"]) == (native["PID"],pid,pid),
            "Native identity query association failed")
    query = observed["query_record"]
    require(value["query_records"] == [query] and query["role"] == "NATIVE_IDENTITY"
            and query["constructor_attempted"] is True and type(query["PID"]) is int and query["PID"] > 0
            and query["error"] is None and query["stop_actions"] == []
            and query["stdout_complete"] is True and query["stderr_complete"] is True
            and query["partial_capture"] is False and query["exit"]["status"] == "reaped"
            and type(query["exit"]["raw_returncode"]) is int and query["exit"]["raw_returncode"] == 0,
            "Exactly one complete normal inherited-native identity query required")
    require(native["exit"]["status"] == "reaped" and type(native["exit"]["raw_returncode"]) is int
            and type(native["exit"]["wait_status"]) is int
            and (os.WIFEXITED(native["exit"]["wait_status"]) or os.WIFSIGNALED(native["exit"]["wait_status"]))
            and os.waitstatus_to_exitcode(native["exit"]["wait_status"]) == native["exit"]["raw_returncode"] == 0,
            "Native must have actual decoded terminal wait status and reaped raw0")
    require(value["native_signal_actions"] == [] and value["group_absence_scope"] ==
            "OUTER_ONLY_NOT_OBSERVED_BY_CALLER","Caller must have no competing group authority")
    require(value["primary_refusal"] is None and value["secondary_errors"] == []
            and value["stop_requests"] == [] and value["automatic_retry"] is False
            and value["science_or_physical_qualification"] is False
            and value["opaque_native_containment_accepted"] is False,"Caller refuses or overclaims")
    require(value["inputs_and_outputs"]["inputs_unchanged"] is True
            and value["inputs_and_outputs"]["binary_and_runtime_unchanged"] is True
            and value["inputs_and_outputs"]["complete_stream_map_or_field_association_proved"] is False,
            "Caller input/presence scope mismatch")
    guard(label="caller-evidence-full-return")
    return dict(hello=hello,terminal=terminal,receipt=value,receipt_descriptor=terminal["caller_receipt"])

def loaded_trace(path,declared):
 text=call(None,'loaded-trace-bytes',path.read_bytes).decode('utf-8');rows=[];unparsed=[]
 for line in text.splitlines():
  if not line.startswith('dyld'):continue
  match=re.fullmatch(r'dyld(?:\[\d+\])?:\s+(?:loaded:\s+)?(?:<[^>]+>\s+)?(/.*)',line)
  if not match:unparsed.append(line);continue
  name=match.group(1);system=name.startswith(('/usr/lib/','/System/Library/','/System/Volumes/Preboot/Cryptexes/OS/'))
  resolved=str(call(None,'loaded-trace-canonical',Path(name).resolve)) if name.startswith(str(E/'moose-local-installed-002')+'/') else name
  rows.append(dict(raw=line,path=name,resolved=resolved,OS_system_image_attribution=system,shared_cache_placement_observed=False))
 observed={x['resolved'] for x in rows};expected={x['resolved'] for x in declared.values()}
 moose=str(E/'moose-local-installed-002/lib/combined/libmoose-opt.0.dylib')
 guard(label='loaded-trace-full-return')
 return dict(rows=rows,unparsed_dyld_rows=unparsed,declared_direct_provider_paths_observed=sorted(expected&observed),declared_direct_provider_paths_not_observed=sorted(expected-observed),expected_MOOSE_provider_observed=moose in observed,additional_non_system_paths=sorted({x['resolved'] for x in rows if not x['OS_system_image_attribution'] and x['resolved'] not in expected}),full_transitive_or_ABI_acceptance=False)

def sample_owned(group, purpose, on_error):
    """One fixed ps form; retained direct query PID only, never group authority."""
    query_started = guard(label="fixed-ps-start")
    until = min(query_started + 2_000_000_000, _UNTIL_NS)
    row = dict(role=QUERY_ROLE, purpose=purpose, started_ns=str(query_started),
               until_ns=str(until), PID=None, constructor_attempted=False,
               exit=dict(status="not_created", wait_status=None, raw_returncode=None),
               stop_actions=[], error=None, stdout_complete=False, stderr_complete=False)
    _QUERY_RECORDS.append(row)
    number = len(_QUERY_RECORDS)
    outpath = QUERY_ROOT / ("query-%03d.stdout" % number)
    errpath = QUERY_ROOT / ("query-%03d.stderr" % number)
    row.update(stdout_path=str(outpath.relative_to(ROOT)),
               stderr_path=str(errpath.relative_to(ROOT)))
    handle = None
    streams = []
    data = [bytearray(), bytearray()]
    error = None
    result = None
    try:
        streams.append(call(until, "query-stdout-open", outpath.open, "xb"))
        streams.append(call(until, "query-stderr-open", errpath.open, "xb"))
        guard(until, "query-constructor")
        row["constructor_attempted"] = True
        row["exit"]["status"] = "unknown"
        handle = _RetainedPopen(["/bin/ps", "-axo", "pid=,pgid=,rss=,stat="], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=False, env={"PATH":"/usr/bin:/bin","LC_ALL":"C"})
        _RETAINED.append(handle)
        row["PID"] = handle.pid
        row["exit"]["status"] = "unreaped"
        guard(until, "query-constructor/full-return")
        pending = {handle.stdout.fileno(): 0, handle.stderr.fileno(): 1}
        for fd in pending:
            call(until, "query-nonblocking", os.set_blocking, fd, False)
        while pending or row["exit"]["status"] != "reaped":
            guard(until, "query-drain")
            if row["exit"]["status"] != "reaped":
                exact_reap(handle, row["exit"], until)
            if pending:
                ready, _, _ = call(until, "query-select", select.select,
                                   list(pending), [], [], timeout_seconds(until, 10_000_000))
                for fd in ready:
                    try:
                        block = call(until, "query-read", os.read, fd, 65536)
                    except BlockingIOError:
                        continue
                    index = pending[fd]
                    if not block:
                        del pending[fd]
                        row["stdout_complete" if index == 0 else "stderr_complete"] = True
                    else:
                        data[index].extend(block)
                        count = call(until, "query-log-write", streams[index].write, block)
                        if count != len(block):
                            raise ValueError("Partial query log write")
                        budgets(_EXTERNAL, _BASELINE)
            else:
                call(until, "query-terminal-spacing", time.sleep,
                     timeout_seconds(until, 10_000_000))
        if row["exit"]["raw_returncode"] != 0:
            raise ValueError("Fixed ps returned nonzero")
        guard(until, "query-full-return")
        rows = []
        for line in data[0].decode("ascii").splitlines():
            values = line.split()
            if len(values) >= 2 and (values[1] == str(group) or values[0] == str(group)):
                if len(values) != 4 or not all(item.isdigit() for item in values[:3]):
                    raise ValueError("Missing/nonnumeric owned RSS row: " + repr(line))
                if int(values[1]) != group:
                    raise ValueError("Owned direct group changed: " + repr(line))
                rows.append(dict(raw=line,pid=int(values[0]),pgid=int(values[1]),
                                 RSS_bytes=int(values[2])*1024,state=values[3]))
        if not rows:
            raise ValueError("Owned group has unavailable RSS/member rows")
        result = dict(RSS_bytes=sum(item["RSS_bytes"] for item in rows),
                      owned_rows=rows,query_record=row)
    except BaseException as exc:
        error = exc
        row["error"] = note_error(exc, "fixed-ps")
        # Parent owner latches its TERM decision before cleaning this query.
        try:
            on_error(exc)
        except BaseException as callback_error:
            row["parent_error_callback"] = note_error(callback_error, "query-parent-refusal")
    finally:
        if handle is not None and row["exit"]["status"] != "reaped":
            try:
                kill_started = guard(_OWNER_START_NS + 110_000_000_000,
                                     "query-own-PID-KILL", False)
                row["KILL_started_ns"] = str(kill_started)
                row["KILL_until_ns"] = str(min(kill_started + 5_000_000_000,
                                               _OWNER_START_NS + 110_000_000_000))
                row["stop_actions"].append(dict(scope="own retained unreaped query PID",
                                                signal=int(signal.SIGKILL),
                                                attempted_ns=str(kill_started)))
                try:
                    os.kill(handle.pid, signal.SIGKILL)
                    row["stop_actions"][-1]["returned"] = True
                except BaseException as kill_error:
                    row["stop_actions"][-1]["error"] = note_error(kill_error, "query-KILL")
                guard(int(row["KILL_until_ns"]), "query-KILL/full-return", False)
                reap_until(handle, row["exit"], int(row["KILL_until_ns"]))
            except BaseException as cleanup_error:
                row["cleanup_error"] = note_error(cleanup_error, "query-cleanup")
                error = error or cleanup_error
        close_streams = streams + ([handle.stdout, handle.stderr] if handle is not None else [])
        for stream in close_streams:
            if stream is not None:
                try:
                    stream.close()
                except BaseException as close_error:
                    row.setdefault("close_errors", []).append(note_error(close_error, "query-file-close"))
                    error = error or close_error
        row["returned_ns"] = str(time.monotonic_ns())
        row["partial_capture"] = not (row["stdout_complete"] and row["stderr_complete"])
    if error is None:
        try:
            guard(until, "query-entire-function-return")
            if result is None:
                raise ValueError("Incomplete fixed ps observation")
            return result
        except BaseException as final_error:
            error = final_error
            row["error"] = note_error(final_error, "query-entire-function-return")
            try:
                on_error(final_error)
            except BaseException as callback_error:
                row["parent_error_callback"] = note_error(callback_error, "query-parent-refusal")
    raise error


def main():
    global _PHASE, _UNTIL_NS, _NORMAL, _EXTERNAL, _BASELINE
    handle = None
    kq = None
    auth = actual = None
    before = {}
    after = {}
    state = dict(leader_constructor_attempted=False,leader_handle_returned=False,leader_PID=None,certificate=None,
        continuation_attempted=False,SIGCONT_acknowledged=False,caller_exit_event=None,
        leader_reap=dict(status="not_created",wait_status=None,raw_returncode=None),
        further_group_signals_closed=False,first_TERM_ns=None,TERM_until_ns=None,
        first_KILL_ns=None,KILL_until_ns=None,TERM_decided=False,KILL_decided=False)
    samples = []
    actions = []
    members = []
    evidence = None
    evidence_attempted = False
    trace = None
    outputs = {}
    absence = dict(status="not_reached",error=None)
    candidate = False
    writable = False
    signal.signal(signal.SIGTERM,latch_signal)
    signal.signal(signal.SIGINT,latch_signal)
    previous_chld = signal.signal(signal.SIGCHLD,signal.SIG_DFL)

    def request_term(exc=None):
        global _NORMAL
        _NORMAL = False
        if exc is not None and not _ERRORS:
            note_error(exc,"owner-query-refusal")
        if state["TERM_decided"] or state["further_group_signals_closed"]:
            return
        state["TERM_decided"] = True
        require(handle is not None and state["certificate"] is not None
                and state["continuation_attempted"] and state["leader_reap"]["status"] != "reaped",
                "No retained certified group for TERM")
        now = guard(START_NS+105_000_000_000,"first-group-TERM",False)
        state["first_TERM_ns"] = str(now)
        state["TERM_until_ns"] = str(min(now+10_000_000_000,START_NS+105_000_000_000))
        action = dict(scope="certified unreaped caller group",signal=int(signal.SIGTERM),
                      attempted_ns=str(now),until_ns=state["TERM_until_ns"])
        actions.append(action)
        try:
            os.killpg(handle.pid,signal.SIGTERM)
            action["returned"] = True
        except BaseException as exc:
            action["error"] = note_error(exc,"group-TERM")
        guard(int(state["TERM_until_ns"]),"first-group-TERM/full-return",False)

    def query_error(exc):
        request_term(exc)

    def poll_event(until,maximum_ns=50_000_000):
        events = call(until,"nonreaping-exit-event",kq.control,None,1,
                      timeout_seconds(until,maximum_ns),honor_stop=False)
        for event in events:
            row = event_record(event)
            event_rows.append(row)
            require(event.ident == handle.pid and event.filter == select.KQ_FILTER_PROC
                    and not event.flags & select.KQ_EV_ERROR
                    and event.fflags & select.KQ_NOTE_EXIT,"Unexpected registered process event")
            state["caller_exit_event"] = row
        return state["caller_exit_event"] is not None

    def final_reap(until):
        state["further_group_signals_closed"] = True
        reap_until(handle,state["leader_reap"],until)

    def member_snapshot(purpose):
        result = sample_owned(handle.pid,purpose,query_error)
        members.append(dict(purpose=purpose,observed=result))
        rows = result["owned_rows"]
        return len(rows) == 1 and rows[0]["pid"] == handle.pid and rows[0]["state"].startswith("Z")

    def cleanup():
        global _NORMAL, _PHASE, _UNTIL_NS
        _NORMAL = False
        if handle is None or state["leader_reap"]["status"] == "reaped":
            return
        if state["certificate"] is None or not state["continuation_attempted"]:
            _PHASE = "KILL_reap110/preCONT-direct-PID-only"
            now = guard(START_NS+110_000_000_000,"preCONT-abort",False)
            until = min(now+5_000_000_000,START_NS+110_000_000_000)
            state["further_group_signals_closed"] = True
            if state["caller_exit_event"] is None:
                action = dict(scope="own unreaped direct wrapper PID before CONT",
                              signal=int(signal.SIGKILL),attempted_ns=str(now),until_ns=str(until))
                actions.append(action)
                try:
                    os.kill(handle.pid,signal.SIGKILL)
                    action["returned"] = True
                except BaseException as exc:
                    action["error"] = note_error(exc,"preCONT-own-PID-KILL")
                guard(until,"preCONT-KILL/full-return",False)
            reap_until(handle,state["leader_reap"],until)
            return
        try:
            request_term()
        except BaseException as exc:
            note_error(exc,"TERM-decision")
        until = int(state["TERM_until_ns"]) if state["TERM_until_ns"] else START_NS+105_000_000_000
        _PHASE = "TERM105"
        _UNTIL_NS = until
        try:
            # Reserve part of the original TERM phase for its one member query.
            while state["caller_exit_event"] is None and time.monotonic_ns() < until-2_000_000_000:
                poll_event(until)
            only_anchor = member_snapshot("one post-TERM member observation")
            if state["caller_exit_event"] is not None and only_anchor:
                final_reap(min(until,START_NS+110_000_000_000))
                return
        except BaseException as exc:
            note_error(exc,"TERM-member-or-event-observation")
        _PHASE = "KILL_reap110"
        if not state["KILL_decided"] and not state["further_group_signals_closed"]:
            state["KILL_decided"] = True
            now = guard(START_NS+110_000_000_000,"first-group-KILL",False)
            state["first_KILL_ns"] = str(now)
            until = min(now+5_000_000_000,START_NS+110_000_000_000)
            state["KILL_until_ns"] = str(until)
            action = dict(scope="certified unreaped caller group",signal=int(signal.SIGKILL),
                          attempted_ns=str(now),until_ns=str(until))
            actions.append(action)
            try:
                os.killpg(handle.pid,signal.SIGKILL)
                action["returned"] = True
            except BaseException as exc:
                action["error"] = note_error(exc,"group-KILL")
            guard(until,"first-group-KILL/full-return",False)
        until = int(state["KILL_until_ns"]) if state["KILL_until_ns"] else START_NS+110_000_000_000
        final_reap(until)

    event_rows = []
    try:
        require(len(sys.argv) == 2 and re.fullmatch("[0-9a-f]{64}",sys.argv[1]),
                "HELD: separate exact root admission digest required")
        authorization = ROOT_EXECUTION/"authorization.json"
        require(sha(regular(authorization)) == sys.argv[1],"Exact separate authorization required")
        writable = True
        require(set(path.name for path in call(None,"fresh-root-list",
                    lambda:list(ROOT_EXECUTION.iterdir()))) == {"authorization.json"},
                "Fresh fixed root; no retry")
        auth = read_json(authorization)
        actual_path = P/"actual-contract.json"
        actual = read_json(regular(actual_path))
        require(auth.get("schema") == "962-observer004-owned-native-root-admission/v2"
                and all(auth.get(key) is True for key in
                ("native_once_authorized","independent_exact_child_complete",
                 "root_source_review_complete","freshness_and_staging_complete")),
                "No reviewed once-only owned native authority")
        require(all(auth.get(key) is False for key in ("automatic_retry","assessment_execution_authorized",
                "solver_change_authorized","head_execution_authorized","engineering_accepted",
                "physics_qualified","material_qualified","process_calibrated","manufacturing_authorized")),
                "No added scientific authority")
        require(actual.get("schema") == "962-observer004-native-measurement-actual/v1"
                and actual.get("authority_at_freeze") == "HELD_ROOT_ADMISSION_REQUIRED"
                and actual.get("native_execution_authorized") is False,"Exact immutable held actual required")
        require(auth["resources"] == actual["resources"] == dict(wall_seconds=100,
                sampled_RSS_stop_bytes=2147483648,sampled_output_stop_bytes=536870912)
                and auth["outer_wall_seconds"] == 115 and auth["root_TERM_grace_seconds"] == 10
                and auth["owned_phase_seconds"] == actual["owned_phase_seconds"] ==
                dict(normal=95,TERM=105,KILL_reap=110,closure=115),"Unchanged controls required")
        require(set(auth["direct_roles"]) == set(actual["future_root_direct_roles"])
                and {"actual","caller","root_controller","wrapper","staging_receipt"} <= set(auth["direct_roles"]),
                "Exact future finite role set required, not a fabricated current count")
        require("argv" not in auth and "authorization_sha256" not in auth
                and auth["argv_prefix"] == [actual["outer_python"]["path"],"-B","-I","-S",
                    str(S/"stopped_exec_wrapper.py")],
                "Admission stores a stable prefix; its own digest remains external")
        require(str(authorization.relative_to(ROOT)) not in actual["input_sha256"]
                and str(actual_path.relative_to(ROOT)) not in actual["input_sha256"]
                and all(pin["path"] != str(authorization.relative_to(ROOT))
                        for pin in auth["direct_roles"].values()),
                "No admission/actual self-pin cycle")
        before["direct"] = direct_map(auth)
        require(auth["direct_roles"]["actual"] == rec(actual_path)
                and auth["direct_roles"]["root_controller"] == rec(Path(__file__))
                and auth["direct_roles"]["caller"] == actual["source"]
                and selected(auth["direct_roles"]["caller"]) == S/"run_native_capture.py"
                and selected(auth["direct_roles"]["wrapper"]) == S/"stopped_exec_wrapper.py",
                "Exact three source/actual associations required")
        parent_path = E/"cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-003/actual-contract.json"
        require(sha(parent_path) == "85a9195ed1a217eef6bad44518390f1b2dfdb879c9cdfc072b6e1465461a5198",
                "Preserved003 actual ancestry changed")
        parent = read_json(parent_path)
        for key in ("outer_python","outer_environment","expected_host_records","expected_provider_paths",
                    "outer_python_observed_metadata","runtime_sha256s","runtime_symlinks","solver_profile"):
            require(actual[key] == parent[key],"No preserved runtime/solver/provider selection mutation")
        require(all(actual["input_sha256"].get(key) == value
                for key,value in parent["input_sha256"].items()),"All003 ancestry pins retained")
        require(call(None,"staged-output-directory",OUTPUT.is_dir)
                and not call(None,"staged-output-link",OUTPUT.is_symlink)
                and set(path.name for path in call(None,"staged-output-list",
                    lambda:list(OUTPUT.iterdir()))) == set(actual["staged_inputs"]),
                "Exactly four separately staged inputs required")
        require(len(actual["staged_inputs"]) == 4
                and {name:(pin["sha256"],pin["bytes"]) for name,pin in actual["staged_inputs"].items()} ==
                    {name:(pin["sha256"],pin["bytes"]) for name,pin in parent["staged_inputs"].items()},
                "Only namespace may change four staged descriptors")
        for name,pin in actual["staged_inputs"].items():
            require(selected(pin) == OUTPUT/name,"Changed staged identity/path")
        historical = read_json(ROOT/actual["historical_native_closed"]["path"])
        _BASELINE = {name:pin["bytes"] for name,pin in historical["outputs"].items()}
        _EXTERNAL = dict(actual["inclusive_external_records"])
        _EXTERNAL.update(auth["direct_roles"])
        _EXTERNAL["root_authorization"] = rec(authorization)
        for pin in _EXTERNAL.values():
            selected(pin)
        before.update(authorization=rec(authorization),
            staged_inputs={name:rec(OUTPUT/name) for name in actual["staged_inputs"]},
            inputs=input_map(actual),runtime=runtime_map(actual),
            selected_host_records=check(actual["expected_host_records"]),
            provider_paths=provider_links(actual["expected_provider_paths"]),
            python=python_record(actual))
        require(not before["selected_host_records"]["changed"]
                and before["provider_paths"] == actual["expected_provider_paths"]
                and before["python"] == actual["outer_python_observed_metadata"],
                "Current finite selected identities required")
        require(str(call(None,"running-Python",Path(sys.executable).resolve,strict=True)) ==
                actual["outer_python_observed_metadata"]["resolved_path"]
                and sys.version_info[:3] == (3,12,11)
                and sys.flags.isolated == sys.flags.no_site == sys.flags.dont_write_bytecode == 1
                and sys.flags.optimize == 0 and "site" not in sys.modules
                and "_distutils_hack" not in sys.modules,"Original3.12-B-I-S required")
        require(all(hasattr(select,key) for key in ("kqueue","kevent","KQ_FILTER_PROC","KQ_NOTE_EXIT",
                "KQ_EV_ADD","KQ_EV_ENABLE","KQ_EV_ONESHOT","KQ_EV_ERROR")),"Required nonreaping APIs missing")
        budgets(_EXTERNAL,_BASELINE)
        auth["authorization_sha256"] = sys.argv[1]
        token = str(START_NS)
        argv = [actual["outer_python"]["path"],"-B","-I","-S",str(S/"stopped_exec_wrapper.py"),
                sys.argv[1],"--owner-start-ns",token]
        kq = call(None,"exit-queue-create",select.kqueue)
        out = call(None,"adapter-stdout-open",(ROOT_EXECUTION/"adapter.stdout.log").open,"xb")
        err = call(None,"adapter-stderr-open",(ROOT_EXECUTION/"adapter.stderr.log").open,"xb")
        try:
            guard(label="one-wrapper-constructor")
            state["leader_constructor_attempted"] = True
            state["leader_reap"]["status"] = "unknown"
            handle = _RetainedPopen(argv,cwd=ROOT,env=actual["outer_environment"],
                stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            _RETAINED.append(handle)
            state.update(leader_handle_returned=True,leader_PID=handle.pid)
            state["leader_reap"]["status"] = "unreaped"
            guard(label="wrapper-constructor/full-return")
            handshake_until = min(time.monotonic_ns()+5_000_000_000,START_NS+95_000_000_000)
            while True:
                guard(handshake_until,"stopped-certificate")
                pid,status = os.waitpid(handle.pid,os.WUNTRACED|os.WNOHANG)
                if pid:
                    if pid != handle.pid:
                        raise ValueError("Wrong direct-child wait status")
                    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                        raw = os.waitstatus_to_exitcode(status)
                        handle.returncode = raw
                        state["leader_reap"].update(status="reaped",wait_status=status,raw_returncode=raw)
                        state["further_group_signals_closed"] = True
                        raise ValueError("Early actual terminal reap before wrapper certification")
                    guard(handshake_until,"stopped-status/full-return")
                    require(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP,
                            "Exact stopped-before-exec handshake required")
                    break
                guard(handshake_until,"stopped-wait/full-return")
                call(handshake_until,"handshake-spacing",time.sleep,timeout_seconds(handshake_until,10_000_000))
            certificate = dict(PID=handle.pid,
                PGID=call(handshake_until,"certificate-PGID",os.getpgid,handle.pid),
                SID=call(handshake_until,"certificate-SID",os.getsid,handle.pid),
                wait_status=status,direct_child_unreaped_at_certificate=True)
            require(certificate["PID"] == certificate["PGID"] == certificate["SID"],"New-session certificate mismatch")
            state["certificate"] = certificate
            hello_raw = call(handshake_until,"stopped-hello",(ROOT_EXECUTION/"adapter.stdout.log").read_bytes)
            require(len(hello_raw.splitlines()) == 1,"Complete single wrapper hello required before CONT")
            hello = strict_json(hello_raw)
            require(hello["schema"] == "962-observer004-owned-native-wrapper-hello/v1"
                    and hello["owner_start_ns"] == token
                    and hello["root_admission_sha256"] == sys.argv[1]
                    and hello["PID"] == hello["PGID"] == hello["SID"] == handle.pid
                    and hello["wrapper_source"] == auth["direct_roles"]["wrapper"]
                    and hello["caller_source"] == actual["source"]
                    and hello["caller_actual"] == auth["direct_roles"]["actual"],"Stopped hello association failed")
            watch = select.kevent(handle.pid,filter=select.KQ_FILTER_PROC,
                flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
            events = call(handshake_until,"preregister-exit-event",kq.control,[watch],1,0)
            event_rows.extend(event_record(event) for event in events)
            require(not events,"Unexpected registration event before CONT")
            guard(label="CONT-intent")
            state["continuation_attempted"] = True
            os.kill(handle.pid,signal.SIGCONT)
            state["SIGCONT_acknowledged"] = True
            guard(label="CONT/full-return")
            last_sample = None
            while True:
                guard(label="normal-native-owner")
                now = time.monotonic_ns()
                if last_sample is None or now-last_sample >= 500_000_000:
                    observed = sample_owned(handle.pid,"normal sampled aggregate RSS",query_error)
                    samples.append(dict(time_ns=str(now),**observed))
                    last_sample = time.monotonic_ns()
                    require(observed["RSS_bytes"] < 2147483648,"Sampled aggregate2GiB stop")
                budgets(_EXTERNAL,_BASELINE)
                if poll_event(START_NS+95_000_000_000):
                    break
            evidence_attempted = True
            evidence = caller_evidence(auth,actual,token,handle.pid)
            require(member_snapshot("one normal-exit member observation"),"Normal group has nonanchor/missing members")
            guard(label="normal-positive-decision")
            require(samples and not _ERRORS and not _STOP_REQUESTS,"No normal resource sample or prior refusal")
            _NORMAL = False
            _PHASE = "KILL_reap110/normal-exact-reap-no-signal"
            _UNTIL_NS = START_NS+110_000_000_000
            final_reap(_UNTIL_NS)
            require(state["leader_reap"]["raw_returncode"] == 0,"Actual caller nonzero")
            candidate = True
        finally:
            out.close()
            err.close()
    except BaseException as exc:
        note_error(exc,"owner")
    finally:
        _NORMAL = False
        try:
            cleanup()
        except BaseException as exc:
            note_error(exc,"anchored-cleanup")
        if handle is not None and state["leader_reap"]["status"] == "reaped":
            if state["certificate"] is None:
                absence = dict(status="not_applicable_uncertified",error=None)
            else:
                try:
                    _PHASE = "KILL_reap110/one-postreap-absence-only"
                    _UNTIL_NS = START_NS+110_000_000_000
                    guard(label="absence-only",honor_stop=False)
                    present = group_exists(handle.pid)
                    absence = dict(status="present" if present else "ESRCH",error=None)
                    guard(label="absence-only/full-return",honor_stop=False)
                    require(not present,"Group present after final reap; never signal it again")
                except BaseException as exc:
                    absence["error"] = note_error(exc,"postreap-absence")
                    candidate = False
        if kq is not None and time.monotonic_ns() < START_NS+110_000_000_000:
            try:
                call(START_NS+110_000_000_000,"exit-queue-close",kq.close,honor_stop=False)
            except BaseException as exc:
                note_error(exc,"exit-queue-close")
        _PHASE = "closure115"
        _UNTIL_NS = START_NS+115_000_000_000
        try:
            if auth is not None and actual is not None and before:
                after = dict(authorization=capture(lambda:rec(ROOT_EXECUTION/"authorization.json")),
                    direct=capture(lambda:direct_map(auth)),
                    staged_inputs=capture(lambda:{name:rec(OUTPUT/name) for name in actual["staged_inputs"]}),
                    inputs=capture(lambda:input_map(actual)),runtime=capture(lambda:runtime_map(actual)),
                    selected_host_records=capture(lambda:check(actual["expected_host_records"])),
                    provider_paths=capture(lambda:provider_links(actual["expected_provider_paths"])),
                    python=capture(lambda:python_record(actual)))
                for root in (OUTPUT,ROOT_EXECUTION):
                    for path,size in file_rows(root):
                        outputs[str(path.relative_to(ROOT))] = rec(path)
                if call(None,"native-log-presence",(OUTPUT/"native.log").is_file):
                    trace = loaded_trace(OUTPUT/"native.log",actual["expected_provider_paths"])
        except BaseException as exc:
            note_error(exc,"closure-identity-or-output")
        identities = bool(before and set(before) == set(after) and
            all(after[key]["error"] is None and after[key]["observed"] == value for key,value in before.items()))
        if before and not identities:
            _ERRORS.append(dict(type="IdentityRefusal",message="Complete before/after identity equality unavailable or false",
                phase=_PHASE,operation="closure-identity-joins",time_ns=str(time.monotonic_ns()),traceback=None))
        plugin = str(E/"cp1-oneway-cooling-release-richardson2-END181-dof-map-observer-prep-004/build-001/libcoupon_end181_observer-opt.dylib")
        plugin_observed = bool(trace and plugin in {row["resolved"] for row in trace["rows"]})
        candidate = bool(candidate and state["leader_reap"]["status"] == "reaped"
            and state["leader_reap"]["raw_returncode"] == 0 and absence["status"] == "ESRCH"
            and absence["error"] is None and identities and plugin_observed and samples
            and not _ERRORS and not _STOP_REQUESTS)
        if writable:
            try:
                source_observations = {
                    "authorization":capture(lambda:rec(ROOT_EXECUTION/"authorization.json")),
                    "actual":capture(lambda:rec(P/"actual-contract.json")),
                    "controller":capture(lambda:rec(Path(__file__)))}
                for role,row in source_observations.items():
                    if row["error"] is not None:
                        _ERRORS.append(dict(type="DescriptorRefusal",message=row["error"],phase=_PHASE,
                            operation="closure-source-"+role,time_ns=str(time.monotonic_ns()),traceback=None))
                candidate = bool(candidate and all(row["error"] is None
                    for row in source_observations.values()))
                prefinal = budgets(_EXTERNAL,_BASELINE)
                closed = dict(schema="962-observer004-owned-native-root-closed/v2",
                    status=("COMPLETE_CANDIDATE" if candidate else
                        "REFUSED_COMPLETE_METADATA" if identities and state["leader_reap"]["status"] == "reaped"
                        and absence["error"] is None and all(row["error"] is None
                            for row in source_observations.values()) else "INCOMPLETE_PARTIAL"),
                    sources_actual_admission={role:row["observed"] for role,row in source_observations.items()},
                    source_descriptor_errors={role:row["error"] for role,row in source_observations.items()},
                    clock=dict(owner_start_ns=str(START_NS),normal_until_ns=str(START_NS+95_000_000_000),
                        TERM_cap_ns=str(START_NS+105_000_000_000),KILL_reap_cap_ns=str(START_NS+110_000_000_000),
                        closure_until_ns=str(START_NS+115_000_000_000),
                        first_TERM_ns=state["first_TERM_ns"],TERM_until_ns=state["TERM_until_ns"],
                        first_KILL_ns=state["first_KILL_ns"],KILL_until_ns=state["KILL_until_ns"]),
                    wrapper_argv_and_hello=dict(argv=locals().get("argv"),hello=locals().get("hello"),
                        terminal=evidence["terminal"] if evidence else None),
                    certificate=state["certificate"],
                    continuation=dict(attempted=state["continuation_attempted"],acknowledged=state["SIGCONT_acknowledged"],
                        error="CONT attempt not acknowledged" if state["continuation_attempted"]
                            and not state["SIGCONT_acknowledged"] else None),
                    caller_exit=dict(NOTE_EXIT_events=event_rows,reap=state["leader_reap"]),
                    native_receipt_and_terminal=evidence,ownership_state=state,
                    native_receipt_evidence_status=dict(status="observed" if evidence else
                        "failed" if evidence_attempted else "not_reached",
                        reason=None if evidence else "Complete typed caller evidence unavailable; raw logs/errors retained"),
                    joins=dict(before_after="observed" if identities else "failed",
                        clock_and_caller_source="observed" if evidence else "failed" if evidence_attempted else "not_reached",
                        certificate="observed" if state["certificate"] else "not_reached",
                        native_identity_and_actual_reap="observed" if evidence else "failed" if evidence_attempted else "not_reached",
                        caller_receipt_and_terminal="observed" if evidence else "failed" if evidence_attempted else "not_reached",
                        normal_member_decision="observed" if candidate else "failed" if members else "not_reached",
                        normal_RSS="observed" if samples else "not_reached",
                        final_reap_and_absence="observed" if state["leader_reap"]["status"] == "reaped"
                            and absence["status"] == "ESRCH" and absence["error"] is None else "failed"),
                    group_members=members,final_group_absence=absence,
                    resources=dict(samples=samples,valid_count=len(samples),
                        peak=max((row["RSS_bytes"] for row in samples),default=None),
                        query_records=_QUERY_RECORDS,prefinal_size_growth=prefinal,
                        full_postwrite_observations_are_external_root_facts=True,
                        hard_quota_or_true_peak=False),
                    errors_stops_signals=dict(primary=_ERRORS[0] if _ERRORS else None,
                        all_errors=_ERRORS,stop_requests=_STOP_REQUESTS,signal_actions=actions),
                    before=before,after=after,identities_unchanged=identities,
                    outputs_and_trace=dict(outputs=outputs,loaded_trace=trace,
                        expected_corrected_plugin_path_observed=plugin_observed),
                    handlers_remain_installed_through_return=True,prior_SIGCHLD_disposition=repr(previous_chld),
                    root_outer_RC0_fullreturn_finalcensus_required=True,
                    measurement_stream_map_and_field_completeness_accepted=False,
                    opaque_native_containment_accepted=False,science_or_physical_qualification=False,
                    automatic_retry=False)
                data = encode(closed)
                budgets(_EXTERNAL,_BASELINE,pending=len(data))
                write_full(ROOT_EXECUTION/"closed-result.json",data)
                budgets(_EXTERNAL,_BASELINE)
                guard(label="full-postreceipt-owner-return",honor_stop=False)
            except BaseException as exc:
                candidate = False
                print("Incomplete/refused owner preservation: "+repr(exc),file=sys.stderr,flush=True)
    return 0 if candidate and not _ERRORS and not _STOP_REQUESTS else 2


if __name__ == "__main__":
    raise SystemExit(main())

