"""HELD/UNRUN fixed RICH2 caller. No operation without a separate reviewed v2 admission."""
import time
START_NS = time.monotonic_ns()
import errno
import argparse, hashlib, json, math, os, re, select, shutil, signal, subprocess, sys, traceback
from pathlib import Path

SOURCE_PREP = Path(__file__).parent
ENGINEERING = SOURCE_PREP.parent
ROOT = ENGINEERING.parent.parent
PREFIX = ENGINEERING / "moose-local-installed-002"
EXECUTABLE = PREFIX / "bin/combined-opt"
CASE = ENGINEERING / "cp1-oneway-cooling-release-richardson2-prep-001"
PREP = CASE
TRANSFER = ENGINEERING / "cp1-oneway-cooling-release-inputs-001"
CARD = CASE / "card.json"
PHYSICS = CASE / "case-contract.json"
PRIMARY_API = CASE / "source-evidence.json"
HELD = CASE / "held-preparation.json"
ROOT_EXECUTION = ENGINEERING / "cp1-oneway-cooling-release-richardson3-observer004-native-measurement-root-execution-001"
OUTPUT = ENGINEERING / "cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001"
TRANSFER_FILES = ("old-end.grid", "born-end.grid", "born-begin80.grid", "transfer-manifest.json")
FEATURES = ("GeneratedMeshGenerator", "SubdomainBoundingBoxGenerator", "BoundingBoxNodeSetGenerator",
            "ADTimeDerivative", "FunctionIC", "PiecewiseMultilinear", "FunctionAux", "TimedSubdomainModifier",
            "ADDirichletBC", "ADStressDivergenceTensors", "ADComputeIncrementalStrain",
            "ADComputeIsotropicElasticityTensor", "ADComputeThermalExpansionEigenstrain",
            "ADComputeFiniteStrainElasticStress", "RankTwoTensorMaterialADConverter", "RankTwoCartesianComponent",
            "NodalValueSampler", "ElementMaterialSampler", "TimePeriod", "SMP", "Transient", "CSV", "Console", "Exodus")
QUERY_ROLE = "NATIVE_IDENTITY"
QUERY_ROOT = OUTPUT
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


class ChildRelationshipError(ValueError):
    """An exact wait returned an untrustworthy direct-child relationship."""


def retained_unreaped(record):
    return (record.get("status") == "unreaped"
            and record.get("direct_child_relationship") == "retained_unreaped")


def can_signal(record):
    return retained_unreaped(record) and record.get("numeric_signal_authority") is True


def lose_relationship(record, exc):
    # Permanent per-handle barrier; no later numeric query/wait restores ownership.
    record.update(status="unknown",direct_child_relationship="lost",
                  numeric_signal_authority=False)
    if record.get("relationship_error") is None:
        record["relationship_error"] = note_error(exc,"lost-direct-child-relationship")


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
    # A consumed terminal status is stored before the full-return deadline check.
    if record.get("direct_child_relationship") == "lost":
        raise ChildRelationshipError("Lost relationship; no numeric wait or signal authority")
    if record["status"] == "reaped":
        return True
    if not retained_unreaped(record):
        raise ChildRelationshipError("Unknown direct-child relationship; no numeric wait")
    guard(until, "exact-WNOHANG-reap", False)
    try:
        pid, status = os.waitpid(handle.pid, os.WNOHANG)
        if pid:
            if pid != handle.pid or not (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                raise ChildRelationshipError("Unexpected exact terminal wait status")
            raw = os.waitstatus_to_exitcode(status)
            handle.returncode = raw
            record.update(status="reaped",wait_status=status,raw_returncode=raw,
                          direct_child_relationship="reaped",numeric_signal_authority=False)
    except BaseException as exc:
        if isinstance(exc,(ChildProcessError,ChildRelationshipError)) or (
                isinstance(exc,OSError) and exc.errno == errno.ECHILD):
            lose_relationship(record,exc)
        raise
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


def positive_ns(value, maximum):
    """Canonical positive ASCII integer, bounded by its declared clock role."""
    if type(value) is not str or not re.fullmatch(r"[1-9][0-9]*",value,flags=re.ASCII):
        raise ValueError("Canonical positive ASCII nanoseconds required")
    if len(value) > len(str(maximum)):
        raise ValueError("Nanosecond value exceeds declared clock bound")
    result = int(value,10)
    if str(result) != value or not 0 < result <= maximum:
        raise ValueError("Nanosecond value exceeds declared clock bound")
    return result


def clock_token(token):
    # Observed times, unlike future deadlines, must not exceed the current clock.
    return positive_ns(token,time.monotonic_ns())

def need(condition, message):
    if not condition:
        raise ValueError(message)

def same(path, expected):
    try:
        return sha(path) == expected
    except OSError:
        return False

def registry_features(text):
    rows = [line.split("\t") for line in text.splitlines()]
    need(["Label", "Type", "Name", "Class", "File"] in rows, "Documented registry header missing")
    objects = {row[2] for row in rows if len(row) == 5 and row[1] == "object"}
    need(set(FEATURES) <= objects, "Required explicit deck object is not registered")
    return {name: True for name in FEATURES}

def validate_rich3_profile(current, baseline):
    need(len(baseline["petsc_options_iname"]) == 8
          and baseline["petsc_options_iname"][7] == "-ksp_max_it"
          and len(baseline["petsc_options_value"]) == 8
          and baseline["petsc_options_value"][7] == "2"
          and type(baseline["linear_updates_per_regular_solve"]) is int
          and baseline["linear_updates_per_regular_solve"] == 2
          and baseline["linear_stopping"] ==
              "KSPConvergedSkip count completion after exactly2 updates, not residual-accuracy acceptance",
          "Exact frozen RICH2 profile baseline required")
    expected = dict(baseline)
    expected["petsc_options_value"] = list(baseline["petsc_options_value"])
    expected["petsc_options_value"][7] = "3"
    expected["linear_updates_per_regular_solve"] = 3
    expected["linear_stopping"] = "KSPConvergedSkip count completion after exactly3 updates, not residual-accuracy acceptance"
    need(type(current["linear_updates_per_regular_solve"]) is int and current == expected,
          "Only the three fixed RICH3 profile fields may change")
    return True


def validate_rich3_staged(current, baseline):
    name = "thermoelastic-birth-observer-registration.i"
    expected = {n:(p["sha256"],p["bytes"]) for n,p in baseline.items()}
    need(set(expected) == {name,"old-end.grid","born-end.grid","born-begin80.grid"}
          and expected[name] == ("190296e6c2ad1627feca4b374efd2c49739e0c2628764cd92388392a78fd2682",15537),
          "Exact four-input frozen RICH2 baseline required")
    expected[name] = ("e351ee1be793120084464edab51fc96d36e5677e6bb8d2e05caccc1fa85cdbbd",15537)
    need({n:(p["sha256"],p["bytes"]) for n,p in current.items()} == expected,
          "Only the fixed RICH3 deck SHA may change; three grids remain exact")
    baseline_pin = dict(path="work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-host-registration-check-prep-001/thermoelastic-birth-observer-registration.i",
                        sha256="190296e6c2ad1627feca4b374efd2c49739e0c2628764cd92388392a78fd2682",bytes=15537)
    before = call(None,"rich3-baseline-deck-buffer",selected(baseline_pin).read_bytes)
    after = call(None,"rich3-current-deck-buffer",selected(current[name]).read_bytes)
    need(len(before) == len(after) == 15537
          and hashlib.sha256(before).hexdigest() == "190296e6c2ad1627feca4b374efd2c49739e0c2628764cd92388392a78fd2682"
          and hashlib.sha256(after).hexdigest() == "e351ee1be793120084464edab51fc96d36e5677e6bb8d2e05caccc1fa85cdbbd"
          and before[14954:14955] == b"2"
          and after == before[:14954] + b"3" + before[14955:],
          "Whole fixed deck must differ only at max_it byte14954:2-to3")
    return True


def commands(stage):
    need(stage == "coupon", "Only the unchanged fixed RICH2 coupon is available")
    return [("native", [str(EXECUTABLE), "-skip_petscrc", "--n-threads=1", "-i", "thermoelastic-birth-observer-registration.i"])]

def check_pins(pins):
    for name, expected in pins.items():
        guard(label="selected-input")
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative selected pin required")
        need(same(regular(ROOT / name), expected), "Selected input changed")
    guard(label="selected-inputs-complete")


def runtime_unchanged(c):
    for name, expected in c["runtime_sha256s"].items():
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative installed-runtime file required")
        if not same(regular(PREFIX / name), expected):
            return False
    for name, target in c["runtime_symlinks"].items():
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative runtime link required")
        path = PREFIX / name
        if not call(None, "runtime-link", path.is_symlink):
            return False
        if call(None, "runtime-target", os.readlink, path) != target:
            return False
        resolved = call(None, "runtime-resolved", path.resolve, strict=True)
        if not resolved.is_relative_to(PREFIX):
            return False
    guard(label="runtime-complete")
    return True


def root_admission(c, actual, actual_sha, expected):
    path = ROOT_EXECUTION / "authorization.json"
    need(re.fullmatch("[0-9a-f]{64}", expected) and same(regular(path), expected),
         "Exact separate root admission required")
    a = read_json(path)
    need(a.get("schema") == "962-observer004-owned-native-root-admission/v2"
         and a.get("native_once_authorized") is True
         and a.get("independent_exact_child_complete") is True
         and a.get("root_source_review_complete") is True
         and a.get("freshness_and_staging_complete") is True,
         "Held source has no native authority")
    need(all(a.get(k) is False for k in ("automatic_retry", "assessment_execution_authorized",
         "head_execution_authorized", "engineering_accepted",
         "physics_qualified", "material_qualified", "process_calibrated", "manufacturing_authorized")),
         "No additional scientific authority")
    need(a.get("solver_change_authorized") is True
         and a.get("fixed_solver_variant") == c.get("fixed_solver_variant") == dict(name="RICH2_TO_RICH3_ONE_ADDITIONAL_CORRECTION",
             scientific_basis="One additional correction after captured RICH2 and QP arithmetic; no convergence acceptance."),
         "Only the explicitly authorized fixed RICH2-to3 solver variant is available")
    need(set(a["direct_roles"]) == set(c["future_root_direct_roles"]),
         "Exact future independently reviewed finite role set required")
    need({"actual", "caller", "root_controller", "wrapper", "staging_receipt"} <= set(a["direct_roles"]),
         "Mandatory exact owned-source and staging roles required")
    need("argv" not in a and "authorization_sha256" not in a
         and a["argv_prefix"] == [c["outer_python"]["path"],"-B","-I","-S",
             str(SOURCE_PREP/"stopped_exec_wrapper.py")],
         "Stable prefix only; late admission digest is external")
    need(str(path.relative_to(ROOT)) not in c["input_sha256"]
         and str(actual.relative_to(ROOT)) not in c["input_sha256"]
         and all(pin["path"] != str(path.relative_to(ROOT)) for pin in a["direct_roles"].values()),
         "No admission/actual self-pin cycle")
    for pin in a["direct_roles"].values():
        name = Path(pin["path"])
        need(not name.is_absolute(), "Relative first-party direct controls required")
        selected(pin)
    need(a["direct_roles"]["actual"] == rec(actual) and actual_sha == sha(actual), "Actual association changed")
    need(a["direct_roles"]["caller"] == c["source"] == rec(Path(__file__)), "Exact caller required")
    need(a["resources"] == c["resources"] == dict(wall_seconds=100,
         sampled_RSS_stop_bytes=2147483648, sampled_output_stop_bytes=536870912),
         "No native resource-cap change")
    need(a["outer_wall_seconds"] == 115 and a["root_TERM_grace_seconds"] == 10
         and a["owned_phase_seconds"] == c["owned_phase_seconds"] ==
         dict(normal=95, TERM=105, KILL_reap=110, closure=115), "Exact shared deadlines required")
    stage = read_json(selected(a["direct_roles"]["staging_receipt"]))
    need(stage.get("schema") == "962-observer004-native-measurement-four-input-staging/v1"
         and stage.get("all_four_copies_byte_exact") is True and stage.get("no_execution") is True
         and stage["staged_inputs"] == c["staged_inputs"], "Separate complete four-input staging required")
    design = {
        "contract": ("work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-owned-control-choices-001/control-contract.json", "10aaa53acc3fbe15f07aeadd75f33c0edb886d8d79d4fe824f898907cb12a819"),
        "clarification": ("work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-owned-control-choices-clarification-001/CLARIFICATION.json", "df5ce24e733c94cfe5522c7a824f38c4739538e87e71f40831ef37aae83c1d5b"),
        "implementation_scope": ("work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-owned-control-choices-root-review-001/review.json", "dd7aed69ab59b24ce6dc2b2523b9a72d7ef0a30273302542f983d7eac69028bb")}
    for role, (name, digest) in design.items():
        need(c["ownership_design_records"][role]["path"] == name
             and c["ownership_design_records"][role]["sha256"] == digest
             and c["input_sha256"].get(name) == digest, "Changed or unpinned accepted control design")
        selected(c["ownership_design_records"][role])
    external = dict(c["inclusive_external_records"])
    external.update({role:pin for role,pin in a["direct_roles"].items()})
    external["root_authorization"] = rec(path)
    for pin in external.values():
        selected(pin)
    return a, external


def checked_contract(stage, path, expected, admission_sha):
    path = Path(path)
    need(call(None, "actual-file", path.is_file) and not call(None, "actual-link", path.is_symlink) and call(None, "actual-resolve", path.resolve) == path
         and re.fullmatch("[0-9a-f]{64}", expected) and same(path, expected), "Exact external actual child required")
    c = read_json(path)
    need(stage == "coupon" and c.get("schema") == "962-observer004-native-measurement-actual/v1" and c.get("stage") == stage and c.get("native_execution_authorized") is False and c.get("authority_at_freeze") == "HELD_ROOT_ADMISSION_REQUIRED", "Exact held measurement actual required")
    need(all(c.get(k) is False for k in ("head_authorized", "engineering_accepted", "physics_qualified", "material_qualified", "process_calibrated", "manufacturing_authorized", "automatic_retry", "assessment_execution_authorized")), "No additional authority")
    a, external = root_admission(c, path, expected, admission_sha)
    original = read_json(ROOT / c["original_native_actual"]["path"])
    need(all(c["input_sha256"].get(k) == v for k,v in original["input_sha256"].items()) and c["runtime_sha256s"] == original["runtime_sha256s"] and c["runtime_symlinks"] == original["runtime_symlinks"] and validate_rich3_profile(c["solver_profile"], original["solver_profile"]), "All original168 pins/runtime19/13/solver controls must be retained")
    pins = c["input_sha256"]
    need(pins.get(str(HELD.relative_to(ROOT))) == sha(HELD), "Held preparation is not directly bound")
    held = read_json(HELD)
    need(all(pins.get(k) == v for k, v in held["input_sha256"].items()), "Prepared input omitted")
    check_pins(pins)
    need(c["runtime_sha256s"] == held["runtime_sha256s"] and len(c["runtime_sha256s"]) == 19
         and c["runtime_symlinks"] == held["runtime_symlinks"] and len(c["runtime_symlinks"]) == 13
         and runtime_unchanged(c) and call(None, "native-executable", os.access, EXECUTABLE, os.X_OK), "Exact selected19/13 current runtime required")
    need(c["resources"] == held["coupon_resources"], "Exact100s/2GiB/512MiB fixed-case limits required")
    for key in ("installation_result_peer", "installation_receipt", "data_preparation_root_closed",
                "data_preparation_result_peer", "independent_assessment_source",
                "independent_assessment_source_peer", "independent_assessment_source_root_review"):
        need(isinstance(c.get(key), str) and c[key] in pins, "Independent installation/3D assessment source gates required")
    registry = c["registry"]
    need(set(registry)=={"presence_record","root_closed","runtime_bindings","stdout"}
         and all(isinstance(v,str) and v in pins for v in registry.values()),
         "Separate completed exact24-object registry closure required")
    presence = read_json(ROOT / registry["presence_record"])
    closed = read_json(ROOT / registry["root_closed"])
    need(closed.get("returncode") == 0 and closed.get("stop_reason") is None
         and closed.get("selected19_files13_links_before_after_unchanged") is True
         and closed["runtime_bindings_sha256"] == pins[registry["runtime_bindings"]]
         and closed["registry_sha256"] == pins[registry["stdout"]]
         and presence["registry_sha256"] == closed["registry_sha256"]
         and presence["root_closed_sha256"] == pins[registry["root_closed"]]
         and presence.get("all_present_once") is True and set(presence["exact_rows"]) == set(FEATURES),
         "Cached exact selected-runtime registry presence joins required; not a semantic/ABI proof")
    registry_features(call(None, "registry-text", (ROOT / registry["stdout"]).read_text))
    manifest_path = TRANSFER / "transfer-manifest.json"
    need(c.get("transfer_manifest") == str(manifest_path.relative_to(ROOT))
         and pins.get(c["transfer_manifest"]) == c.get("transfer_manifest_sha256"), "Exact completed transfer manifest required")
    manifest = read_json(manifest_path)
    source_index = read_json(PREP / "thermal-input-index.json")
    need(manifest.get("schema") == "962-oneway-cooling-release-prepared-transfer/v1"
         and manifest["source_manifest_sha256"] == source_index["source_manifest"]["sha256"]
         and manifest["original_table_sha256"] == {n:d["sha256"] for n,d in source_index["table_descriptors"].items()}
         and (manifest["old_node_count"],manifest["born_reference_DOF_count"],manifest["shared_node_count"],
              manifest["genuinely_new_node_count"]) == (225,225,25,200)
         and manifest["table_value_counts"] == {"old-end.grid":41175,"born-end.grid":23175,"born-begin80.grid":225}
         and manifest["original_tokens_preserved"] == 54675
         and manifest["new_assumed_cooling_hold_values"] == 9900
         and manifest["cooling_card_sha256"] == sha(CARD)
         and manifest.get("native_connectivity_or_ID_bijection_proven") is False
         and manifest.get("native_execution_authorized") is False
         and manifest.get("prescribed_cooling_not_heat_equation_or_process_calibration") is True,
         "Exact accepted-source/assumed-cooling transfer and unchanged birth-reference associations required")
    need(set(manifest["table_sha256"]) == set(TRANSFER_FILES) - {"transfer-manifest.json"}, "Exactly three tables required")
    for name in TRANSFER_FILES:
        need(str((TRANSFER / name).relative_to(ROOT)) in pins, "Every converted input must be directly pinned")
        if name != "transfer-manifest.json":
            need(pins[str((TRANSFER / name).relative_to(ROOT))] == manifest["table_sha256"][name], "Converted table drift")
    frozen = read_json(PHYSICS)
    need(frozen["card"] == read_json(CARD) and frozen["card_sha256"] == sha(CARD)
         and frozen["source_input_sha256"]["thermoelastic-birth.i"] == sha(CASE / "thermoelastic-birth.i"),
         "Exact separate source physics contract required")
    output = Path(c["output"])
    need(output == OUTPUT and call(None, "output-resolve", output.resolve) == output and call(None, "output-directory", output.is_dir) and not call(None, "output-link", output.is_symlink), "Fixed separately staged output directory required")
    need(set(p.name for p in call(None, "staged-list", lambda: list(output.iterdir()))) == set(c["staged_inputs"]), "Only four staged original inputs may precede capture")
    for name, pin in c["staged_inputs"].items():
        p = output/name
        need(call(None, "staged-file", p.is_file) and not call(None, "staged-link", p.is_symlink) and call(None, "staged-size", p.stat).st_size == pin["bytes"] and same(p,pin["sha256"]), "Staged input identity changed")
    need(c["argv"] == commands(stage)[0][1] and c["environment"]["TMPDIR"] == str(output/"tmp"), "Exact fixed command and private temporary directory required")
    parent_path = ROOT / "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-003/actual-contract.json"
    need(sha(parent_path) == "85a9195ed1a217eef6bad44518390f1b2dfdb879c9cdfc072b6e1465461a5198", "Preserved003 actual ancestry changed")
    parent = read_json(parent_path)
    need(all(c["input_sha256"].get(k) == v for k,v in parent["input_sha256"].items())
         and validate_rich3_profile(c["solver_profile"], parent["solver_profile"])
         and c["runtime_sha256s"] == parent["runtime_sha256s"]
         and c["runtime_symlinks"] == parent["runtime_symlinks"]
         and c["outer_python"] == parent["outer_python"]
         and c["outer_environment"] == parent["outer_environment"], "No003 science/runtime/outer-selection mutation")
    need({k:v for k,v in c["environment"].items() if k != "TMPDIR"} ==
         {k:v for k,v in parent["environment"].items() if k != "TMPDIR"}, "Only native TMPDIR namespace may differ")
    need(validate_rich3_staged(c["staged_inputs"], parent["staged_inputs"]),
         "Exact single-byte RICH3 deck variant required")
    guard(label="complete-original-and003-contract")
    return c, output, a, external

def native_identity(pid, purpose, on_error):
    """One fixed ps form; retained direct query PID only, never group authority."""
    query_started = guard(label="fixed-ps-start")
    until = min(query_started + 2_000_000_000, _UNTIL_NS)
    row = dict(role=QUERY_ROLE, purpose=purpose, started_ns=str(query_started),
               until_ns=str(until), PID=None, constructor_attempted=False,
               exit=dict(status="not_created", wait_status=None, raw_returncode=None,
                         direct_child_relationship="not_created",numeric_signal_authority=False),
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
        row["exit"].update(status="unknown",direct_child_relationship="unknown",numeric_signal_authority=False)
        handle = _RetainedPopen(["/bin/ps", "-o", "pid=,ppid=,pgid=", "-p", str(pid)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=False, env={"PATH":"/usr/bin:/bin","LC_ALL":"C"})
        _RETAINED.append(handle)
        row["PID"] = handle.pid
        row["exit"].update(status="unreaped",direct_child_relationship="retained_unreaped",numeric_signal_authority=True)
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
        values = data[0].decode("ascii").split()
        if len(values) != 3 or not all(re.fullmatch("[0-9]+", item) for item in values):
            raise ValueError("Missing/nonnumeric native PID/PPID/PGID")
        result = dict(PID=int(values[0]), PPID=int(values[1]), PGID=int(values[2]),
                      query_record=row)
    except BaseException as exc:
        error = exc
        row["error"] = note_error(exc, "fixed-ps")
        # Parent owner latches its TERM decision before cleaning this query.
        try:
            on_error(exc)
        except BaseException as callback_error:
            row["parent_error_callback"] = note_error(callback_error, "query-parent-refusal")
    finally:
        if handle is not None and can_signal(row["exit"]):
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
                    if not can_signal(row["exit"]):
                        raise ChildRelationshipError("Query relationship lost before own-PID KILL")
                    os.kill(handle.pid, signal.SIGKILL)
                    row["stop_actions"][-1]["returned"] = True
                except BaseException as kill_error:
                    row["stop_actions"][-1]["error"] = note_error(kill_error, "query-KILL")
                guard(int(row["KILL_until_ns"]), "query-KILL/full-return", False)
                reap_until(handle, row["exit"], int(row["KILL_until_ns"]))
            except BaseException as cleanup_error:
                row["cleanup_error"] = note_error(cleanup_error, "query-cleanup")
                error = error or cleanup_error
        if handle is not None and row["exit"]["status"] != "reaped" and not retained_unreaped(row["exit"]):
            row["cleanup_signal_and_wait_skipped"] = "Lost or unknown direct-child relationship; no numeric authority"
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


def run(stage, contract, expected, admission_sha, owner_token):
    global _OWNER_START_NS, _UNTIL_NS, _PHASE, _NORMAL, _EXTERNAL, _BASELINE
    _OWNER_START_NS = clock_token(owner_token)
    _UNTIL_NS = min(_OWNER_START_NS + 95_000_000_000, START_NS + 100_000_000_000)
    normal_until = _UNTIL_NS
    _PHASE = "normal95"
    guard(label="caller-entry")
    signals = {number: signal.signal(number, latch_signal)
               for number in (signal.SIGTERM, signal.SIGINT)}
    old_chld = signal.getsignal(signal.SIGCHLD)
    handle = None
    receipt = None
    can_preserve = False
    caller_identity = None
    native = dict(spawn_attempted=False, PID=None, start_new_session=False, preexec_fn_used=False,
                  identity_observation=None,
                  exit=dict(status="not_created", wait_status=None, raw_returncode=None,
                            direct_child_relationship="not_created",numeric_signal_authority=False))
    candidate = False
    receipt_pin = None
    saved_ns = hashed_ns = None
    failure = None
    try:
        need(old_chld == signal.SIG_DFL,"Already-default SIGCHLD required; no reset")
        c, output, auth, _EXTERNAL = checked_contract(stage, contract, expected, admission_sha)
        caller_identity = dict(PID=os.getpid(), PGID=call(None, "caller-PGID", os.getpgrp),
                               SID=call(None, "caller-SID", os.getsid, 0))
        need(caller_identity["PID"] == caller_identity["PGID"] == caller_identity["SID"],
             "Caller must be the exact unreaped certified leader")
        can_preserve = True
        historical = read_json(ROOT / c["historical_native_closed"]["path"])
        _BASELINE = {name:pin["bytes"] for name,pin in historical["outputs"].items()}
        receipt = dict(schema="962-observer004-owned-native-caller-receipt/v2",
            status="INCOMPLETE_PARTIAL", root_admission_sha256=admission_sha,
            actual=rec(Path(contract)), source=rec(Path(__file__)),
            clock=dict(owner_start_ns=owner_token, caller_entry_ns=str(START_NS),
                       normal_until_ns=str(normal_until), native_spawn_ns=None,
                       receipt_encoding_started_ns=None),
            caller_identity=caller_identity, native=native, native_signal_actions=[],
            group_absence_scope="OUTER_ONLY_NOT_OBSERVED_BY_CALLER",
            resources=dict(authority="outer_certified_group", sampled_RSS_by_caller=False,
                           native100_upper_bound=True, limits=c["resources"]),
            command=c["argv"], physics_contract_sha256=sha(PHYSICS),
            primary_refusal=None, secondary_errors=_ERRORS, stop_requests=_STOP_REQUESTS,
            query_records=_QUERY_RECORDS, inputs_and_outputs={},
            science_or_physical_qualification=False, opaque_native_containment_accepted=False,
            automatic_retry=False)
        for source, name in ((Path(contract), "actual-contract.json"), (PHYSICS, "frozen-contract.json"),
                             (CARD, "card.json"), (TRANSFER/"transfer-manifest.json", "transfer-manifest.json")):
            call(None, "preserved-original-copy", shutil.copyfile, source, output/name)
        snapshots = output/"source-snapshots"
        call(None, "source-snapshots", snapshots.mkdir)
        preparation = c["source_preparation_records"]
        need({str((SOURCE_PREP/name).relative_to(ROOT)) for name in
              ("run_root_once.py","run_native_capture.py","stopped_exec_wrapper.py",
               "METHOD.md","index.json","bindings.json")} <= set(preparation),
             "Complete later reviewed finite source packet required")
        for name, pin in preparation.items():
            need(name == pin["path"] and name in c["input_sha256"]
                 and pin["sha256"] == c["input_sha256"][name], "Direct source preparation pin required")
            source = selected(pin)
            destination = snapshots/source.relative_to(ROOT)
            call(None, "snapshot-parent", destination.parent.mkdir, parents=True, exist_ok=True)
            call(None, "snapshot-copy", shutil.copyfile, source, destination)
        destination = snapshots/PRIMARY_API.relative_to(ROOT)
        call(None, "primary-parent", destination.parent.mkdir, parents=True, exist_ok=True)
        call(None, "primary-copy", shutil.copyfile, PRIMARY_API, destination)
        initial = {str(path.relative_to(output)):sha(path) for path,size in file_rows(output)}
        call(None, "private-tmp", (output/"tmp").mkdir)
        budgets(_EXTERNAL, _BASELINE)
        guard(label="before-one-native-constructor")
        log = call(None, "native-log-open", (output/"native.log").open, "xb")
        try:
            native["spawn_attempted"] = True
            native["exit"].update(status="unknown",direct_child_relationship="unknown",numeric_signal_authority=False)
            receipt["clock"]["native_spawn_ns"] = str(time.monotonic_ns())
            handle = _RetainedPopen(c["argv"], cwd=output, env=c["environment"],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=False)
            _RETAINED.append(handle)
            native["PID"] = handle.pid
            native["exit"].update(status="unreaped",direct_child_relationship="retained_unreaped",numeric_signal_authority=False)
            guard(label="native-constructor/full-return")
            def identity_error(exc):
                global _NORMAL
                _NORMAL = False
            observed = native_identity(handle.pid, "one native identity before any native reap", identity_error)
            native["identity_observation"] = observed
            need((observed["PID"],observed["PPID"],observed["PGID"]) ==
                 (handle.pid,caller_identity["PID"],caller_identity["PGID"]),
                 "Native PID/PPID/PGID does not match configured inheritance")
            # Required positive identity -> running edge; failure/stop/late takes refusal.
            guard(label="NATIVE_IDENTITY-to-NATIVE_RUNNING")
            while True:
                guard(label="NATIVE_RUNNING")
                if exact_reap(handle, native["exit"], normal_until):
                    break
                call(normal_until, "native-observation-spacing", time.sleep,
                     timeout_seconds(normal_until, 10_000_000))
        finally:
            log.close()
        need(native["exit"]["raw_returncode"] == 0, "Native nonzero; preserve without replacement")
        need(all(same(output/name,digest) for name,digest in initial.items())
             and same(Path(contract),expected)
             and same(ROOT_EXECUTION/"authorization.json",admission_sha),
             "Initial/staged/control identity changed")
        check_pins(c["input_sha256"])
        need(runtime_unchanged(c), "Selected runtime identity changed")
        required = {}
        for name in ("rich2-END181-dof-map.json","physical-X.petsc","physical-F.petsc","physical-Y.petsc"):
            path = output/name
            exists = call(None, "required-output-present", path.is_file)
            need(not call(None, "required-output-symlink", path.is_symlink), "Unexpected output symlink")
            required[name] = dict(present=exists, bytes=call(None, "required-output-size", path.stat).st_size if exists else None)
        need(all(row["present"] and row["bytes"] > 0 for row in required.values())
             and required["rich2-END181-dof-map.json"]["bytes"] <= 1048576
             and not call(None, "map-partial-presence", (output/"rich2-END181-dof-map.json.part").exists),
             "Only required stream/map presence is a completion gate, not decoded fields")
        receipt["inputs_and_outputs"] = dict(initial_input_sha256=initial,
            inputs_unchanged=True, binary_and_runtime_unchanged=True,
            required_output_presence_only=required,
            artifact_sha256={str(path.relative_to(output)):sha(path) for path,size in file_rows(output)},
            complete_stream_map_or_field_association_proved=False)
        budgets(_EXTERNAL, _BASELINE)
        guard(label="caller-normal-validation-complete")
        candidate = True
    except BaseException as exc:
        failure = note_error(exc, "caller")
        if receipt is not None:
            receipt["primary_refusal"] = failure
    finally:
        _NORMAL = False
        # Refusal has no native signal authority and no replacement invocation.
        if handle is not None and retained_unreaped(native["exit"]):
            try:
                exact_reap(handle,native["exit"],_OWNER_START_NS+110_000_000_000)
            except BaseException as exc:
                note_error(exc,"caller-one-refusal-reap")
        if receipt is not None and can_preserve:
            try:
                if candidate and not _ERRORS and not _STOP_REQUESTS:
                    _PHASE = "normal95"
                    _UNTIL_NS = normal_until
                else:
                    candidate = False
                    _PHASE = "closure115/refusal-evidence-only"
                    _UNTIL_NS = _OWNER_START_NS+115_000_000_000
                receipt["status"] = ("COMPLETE_CANDIDATE" if candidate else
                    "REFUSED_METADATA" if native["exit"]["status"] == "reaped" else "INCOMPLETE_PARTIAL")
                receipt["primary_refusal"] = receipt["primary_refusal"] or (_ERRORS[0] if _ERRORS else None)
                receipt["clock"]["receipt_encoding_started_ns"] = str(time.monotonic_ns())
                receipt["prefinal_candidate"] = bool(candidate and not _STOP_REQUESTS)
                data = encode(receipt)
                need(len(data) <= 33554432, "Full receipt exceeds unchanged growth-derived ceiling")
                budgets(_EXTERNAL,_BASELINE,pending=len(data))
                write_full(output/"native-execution.json",data)
                saved_ns = str(time.monotonic_ns())
                receipt_pin = rec(output/"native-execution.json")
                hashed_ns = str(time.monotonic_ns())
                budgets(_EXTERNAL,_BASELINE)
                guard(label="caller-receipt-full-return")
            except BaseException as exc:
                candidate = False
                note_error(exc,"caller-receipt-preservation")
        try:
            if candidate and receipt_pin is not None and not _ERRORS and not _STOP_REQUESTS:
                _UNTIL_NS = normal_until
                _PHASE = "normal95"
                terminal = dict(schema="962-observer004-owned-native-caller-terminal/v1",
                    owner_start_ns=owner_token, caller_PID=caller_identity["PID"],
                    root_admission_sha256=admission_sha, caller_receipt=receipt_pin,
                    caller_receipt_saved_ns=saved_ns, caller_receipt_hashed_ns=hashed_ns,
                    prefinal_candidate=True)
                text = call(None,"terminal-encoding",json.dumps,terminal,
                            separators=(",",":"),allow_nan=False)
                call(None,"terminal-full-write",sys.stdout.write,text+"\n")
                call(None,"terminal-flush",sys.stdout.flush)
                guard(label="caller-entire-normal-return")
        except BaseException as exc:
            candidate = False
            note_error(exc,"caller-terminal")
        for number, previous in signals.items():
            signal.signal(number,previous)
        # SIGCHLD was required already default; do not reset or restore it.
    return 0 if candidate and not _ERRORS and not _STOP_REQUESTS else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",choices=("coupon",),required=True)
    parser.add_argument("--contract",type=Path,required=True)
    parser.add_argument("--contract-sha256",required=True)
    parser.add_argument("--root-admission-sha256",required=True)
    parser.add_argument("--owner-start-ns",required=True)
    parser.add_argument("--execute",action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("HELD: separate exact root authority required")
    raise SystemExit(run(args.stage,args.contract,args.contract_sha256,
                         args.root_admission_sha256,args.owner_start_ns))

