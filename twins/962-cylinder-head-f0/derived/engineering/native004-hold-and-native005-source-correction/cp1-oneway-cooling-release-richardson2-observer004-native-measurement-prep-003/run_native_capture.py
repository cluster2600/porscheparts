"""Held passive RICH2 observer004 capture caller; root exact admission is mandatory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time
SOURCE_PREP = Path(__file__).resolve().parent
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
ROOT_EXECUTION = ENGINEERING / "cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-003"
OUTPUT = ENGINEERING / "cp1-oneway-cooling-release-richardson2-observer004-native-measurement-003"
TRANSFER_FILES = ("old-end.grid", "born-end.grid", "born-begin80.grid", "transfer-manifest.json")
FEATURES = ("GeneratedMeshGenerator", "SubdomainBoundingBoxGenerator", "BoundingBoxNodeSetGenerator",
            "ADTimeDerivative", "FunctionIC", "PiecewiseMultilinear", "FunctionAux", "TimedSubdomainModifier",
            "ADDirichletBC", "ADStressDivergenceTensors", "ADComputeIncrementalStrain",
            "ADComputeIsotropicElasticityTensor", "ADComputeThermalExpansionEigenstrain",
            "ADComputeFiniteStrainElasticStress", "RankTwoTensorMaterialADConverter", "RankTwoCartesianComponent",
            "NodalValueSampler", "ElementMaterialSampler", "TimePeriod", "SMP", "Transient", "CSV", "Console", "Exodus")




def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def same(path, expected):
    try:
        return sha(path) == expected
    except OSError:
        return False


def check_pins(pins):
    for name, expected in pins.items():
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative selected pin required")
        path = ROOT / name
        need(path.is_file() and not path.is_symlink() and same(path, expected), "Selected input changed")


def runtime_unchanged(c):
    for name, expected in c["runtime_sha256s"].items():
        path = PREFIX / name
        need(not Path(name).is_absolute() and ".." not in Path(name).parts,
             "Relative installed-runtime file required")
        if not path.is_file() or path.is_symlink() or path.resolve() != path or not same(path, expected):
            return False
    for name, target in c["runtime_symlinks"].items():
        path = PREFIX / name
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "Relative runtime link required")
        if not path.is_symlink() or os.readlink(path) != target or not path.resolve().is_relative_to(PREFIX):
            return False
    return True


def registry_features(text):
    rows = [line.split("\t") for line in text.splitlines()]
    need(["Label", "Type", "Name", "Class", "File"] in rows, "Documented registry header missing")
    objects = {row[2] for row in rows if len(row) == 5 and row[1] == "object"}
    need(set(FEATURES) <= objects, "Required explicit deck object is not registered")
    return {name: True for name in FEATURES}


def commands(stage):
    need(stage == "coupon", "Only the unchanged fixed RICH2 coupon is available")
    return [("native", [str(EXECUTABLE), "-skip_petscrc", "--n-threads=1", "-i", "thermoelastic-birth-observer-registration.i"])]


def root_admission(c, actual, actual_sha, expected):
    path = ROOT_EXECUTION / "authorization.json"
    need(re.fullmatch("[0-9a-f]{64}", expected) and path.is_file() and not path.is_symlink() and same(path, expected), "Exact separate root admission required")
    a = json.loads(path.read_text())
    need(a.get("schema") == "962-observer004-native-measurement-root-admission/v1" and a.get("native_once_authorized") is True and a.get("independent_exact_child_complete") is True and a.get("root_source_review_complete") is True and a.get("freshness_and_staging_complete") is True, "Held source has no native authority")
    need(all(a.get(k) is False for k in ("automatic_retry", "assessment_execution_authorized", "solver_change_authorized", "head_execution_authorized", "engineering_accepted", "physics_qualified", "material_qualified", "process_calibrated", "manufacturing_authorized")), "No additional scientific authority")
    need(set(a["direct_roles"]) == set(c["future_root_direct_roles"]), "Exact nine external control roles required")
    for pin in a["direct_roles"].values():
        name = pin["path"]; p = ROOT / name
        need(not Path(name).is_absolute() and ".." not in Path(name).parts and p.is_file() and not p.is_symlink() and p.resolve() == p and same(p, pin["sha256"]) and p.stat().st_size == pin["bytes"], "Root direct control identity changed")
    need(a["direct_roles"]["actual"] == {"path":str(actual.relative_to(ROOT)), "sha256":actual_sha, "bytes":actual.stat().st_size}, "Root admission actual mismatch")
    need(a["direct_roles"]["caller"] == c["source"] and same(Path(__file__), c["source"]["sha256"]), "Exact caller identity required")
    need(a["resources"] == c["resources"] and a["outer_wall_seconds"] == 115 and a["root_TERM_grace_seconds"] == 10, "No resource-cap change")
    stage = json.loads((ROOT / a["direct_roles"]["staging_receipt"]["path"]).read_text())
    need(stage.get("schema") == "962-observer004-native-measurement-four-input-staging/v1" and stage.get("all_four_copies_byte_exact") is True and stage.get("no_execution") is True and stage["staged_inputs"] == c["staged_inputs"], "Separate complete root four-input staging required")
    return a


def checked_contract(stage, path, expected, admission_sha):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and path.resolve() == path
         and re.fullmatch("[0-9a-f]{64}", expected) and same(path, expected), "Exact external actual child required")
    c = json.loads(path.read_text())
    need(stage == "coupon" and c.get("schema") == "962-observer004-native-measurement-actual/v1" and c.get("stage") == stage and c.get("native_execution_authorized") is False and c.get("authority_at_freeze") == "HELD_ROOT_ADMISSION_REQUIRED", "Exact held measurement actual required")
    need(all(c.get(k) is False for k in ("head_authorized", "engineering_accepted", "physics_qualified", "material_qualified", "process_calibrated", "manufacturing_authorized", "automatic_retry", "assessment_execution_authorized")), "No additional authority")
    root_admission(c, path, expected, admission_sha)
    original = json.loads((ROOT / c["original_native_actual"]["path"]).read_text())
    need(all(c["input_sha256"].get(k) == v for k,v in original["input_sha256"].items()) and c["runtime_sha256s"] == original["runtime_sha256s"] and c["runtime_symlinks"] == original["runtime_symlinks"] and c["solver_profile"] == original["solver_profile"], "All original168 pins/runtime19/13/solver controls must be retained")
    pins = c["input_sha256"]
    need(pins.get(str(HELD.relative_to(ROOT))) == sha(HELD), "Held preparation is not directly bound")
    held = json.loads(HELD.read_text())
    need(all(pins.get(k) == v for k, v in held["input_sha256"].items()), "Prepared input omitted")
    check_pins(pins)
    need(c["runtime_sha256s"] == held["runtime_sha256s"] and len(c["runtime_sha256s"]) == 19
         and c["runtime_symlinks"] == held["runtime_symlinks"] and len(c["runtime_symlinks"]) == 13
         and runtime_unchanged(c) and os.access(EXECUTABLE, os.X_OK), "Exact selected19/13 current runtime required")
    need(c["resources"] == held["coupon_resources"], "Exact100s/2GiB/512MiB fixed-case limits required")
    for key in ("installation_result_peer", "installation_receipt", "data_preparation_root_closed",
                "data_preparation_result_peer", "independent_assessment_source",
                "independent_assessment_source_peer", "independent_assessment_source_root_review"):
        need(isinstance(c.get(key), str) and c[key] in pins, "Independent installation/3D assessment source gates required")
    registry = c["registry"]
    need(set(registry)=={"presence_record","root_closed","runtime_bindings","stdout"}
         and all(isinstance(v,str) and v in pins for v in registry.values()),
         "Separate completed exact24-object registry closure required")
    presence = json.loads((ROOT / registry["presence_record"]).read_text())
    closed = json.loads((ROOT / registry["root_closed"]).read_text())
    need(closed.get("returncode") == 0 and closed.get("stop_reason") is None
         and closed.get("selected19_files13_links_before_after_unchanged") is True
         and closed["runtime_bindings_sha256"] == pins[registry["runtime_bindings"]]
         and closed["registry_sha256"] == pins[registry["stdout"]]
         and presence["registry_sha256"] == closed["registry_sha256"]
         and presence["root_closed_sha256"] == pins[registry["root_closed"]]
         and presence.get("all_present_once") is True and set(presence["exact_rows"]) == set(FEATURES),
         "Cached exact selected-runtime registry presence joins required; not a semantic/ABI proof")
    registry_features((ROOT / registry["stdout"]).read_text())
    manifest_path = TRANSFER / "transfer-manifest.json"
    need(c.get("transfer_manifest") == str(manifest_path.relative_to(ROOT))
         and pins.get(c["transfer_manifest"]) == c.get("transfer_manifest_sha256"), "Exact completed transfer manifest required")
    manifest = json.loads(manifest_path.read_text())
    source_index = json.loads((PREP / "thermal-input-index.json").read_text())
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
    frozen = json.loads(PHYSICS.read_text())
    need(frozen["card"] == json.loads(CARD.read_text()) and frozen["card_sha256"] == sha(CARD)
         and frozen["source_input_sha256"]["thermoelastic-birth.i"] == sha(CASE / "thermoelastic-birth.i"),
         "Exact separate source physics contract required")
    output = Path(c["output"])
    need(output == OUTPUT and output.resolve() == output and output.is_dir() and not output.is_symlink(), "Fixed separately staged output directory required")
    need(set(p.name for p in output.iterdir()) == set(c["staged_inputs"]), "Only four staged original inputs may precede capture")
    for name, pin in c["staged_inputs"].items():
        p = output/name
        need(p.is_file() and not p.is_symlink() and p.stat().st_size == pin["bytes"] and same(p,pin["sha256"]), "Staged input identity changed")
    need(c["argv"] == commands(stage)[0][1] and c["environment"]["TMPDIR"] == str(output/"tmp"), "Exact fixed command and private temporary directory required")
    return c, output


def growth_bytes(output, root_execution, baseline):
    total = 0
    for root in (output, root_execution):
        for p in root.rglob("*"):
            if p.is_symlink():
                raise ValueError("Unexpected output symlink")
            if p.is_file():
                allowance = baseline.get(str(p.relative_to(output)), 0) if root == output else 0
                total += max(0, p.stat().st_size - allowance)
    return total


def owned_size(output):
    total = 0
    for root in (output, ROOT_EXECUTION):
        for p in root.rglob("*"):
            need(not p.is_symlink(), "Unexpected output symlink")
            if p.is_file():
                total += p.stat().st_size
    return total


def run(stage, contract, expected, admission_sha):
    started = time.monotonic()
    c, output = checked_contract(stage, contract, expected, admission_sha)
    historical = json.loads((ROOT/c["historical_native_closed"]["path"]).read_text())
    baseline = {name:pin["bytes"] for name,pin in historical["outputs"].items()}
    deadline = started + c["resources"]["wall_seconds"]
    need(time.monotonic() < deadline, "Native100s deadline expired before capture")
    shutil.copyfile(contract, output/"actual-contract.json")
    shutil.copyfile(PHYSICS, output/"frozen-contract.json")
    shutil.copyfile(CARD, output/"card.json")
    shutil.copyfile(TRANSFER/"transfer-manifest.json", output/"transfer-manifest.json")
    snapshots = output/"source-snapshots"; snapshots.mkdir()
    for path in (Path(__file__), SOURCE_PREP/"held-preparation.json", SOURCE_PREP/"METHOD.md", PRIMARY_API):
        destination = snapshots/path.relative_to(ROOT); destination.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,destination)
    inputs = {str(p.relative_to(output)):sha(p) for p in output.rglob("*") if p.is_file()}
    receipt = dict(schema="962-observer004-native-measurement-caller-receipt/v1",status="running",command=c["argv"],actual_contract_sha256=expected,root_admission_sha256=admission_sha,physics_contract_sha256=sha(PHYSICS),input_sha256=inputs,resources=c["resources"],RSS_scope="sampled_owned_native_leader_only",hard_OS_quota=False,automatic_retry=False,independent_assessment_performed=False,native_execution_completed_candidate=False,completion_requires_caller_RC0_and_outer_RC0=True,science_or_vector_association_accepted=False,RSS_samples=[],resource_observation_exit_races=[],controller_stop_requests=[],jobs=[])
    process = None; failure = None; term_requested = False; stopped = {"reason":None}; lock = threading.Lock()
    previous = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        nonlocal term_requested
        term_requested = True
        receipt["controller_stop_requests"].append(dict(signal=signum,elapsed_seconds=time.monotonic()-started))
    def stop(reason):
        with lock:
            stopped["reason"] = stopped["reason"] or reason
            if process is not None and process.poll() is None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
    timer = threading.Timer(max(0.,deadline-time.monotonic()),lambda:stop("stage_deadline"));timer.daemon=True
    signal.signal(signal.SIGTERM,interrupted);timer.start()
    try:
        (output/"tmp").mkdir()
        need(not term_requested and not stopped["reason"] and time.monotonic()<deadline,"Refuse before native Popen")
        with (output/"native.log").open("xb") as log:
            process = subprocess.Popen(c["argv"],cwd=output,env=c["environment"],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            receipt["native_PID"] = process.pid
            while process.poll() is None and not term_requested and not stopped["reason"]:
                try:
                    observation = subprocess.run(["/bin/ps","-o","rss=","-p",str(process.pid)],capture_output=True,text=True,timeout=2)
                    direct_RC = process.poll()
                    if direct_RC is not None:
                        receipt["resource_observation_exit_races"].append(dict(observation_returncode=observation.returncode,reported_RSS=observation.stdout.strip(),direct_returncode=direct_RC,elapsed_seconds=time.monotonic()-started))
                        break
                    rss = int(observation.stdout.strip())*1024
                    need(observation.returncode==0 and rss>=0,"Missing/nonnumeric owned native RSS")
                    receipt["RSS_samples"].append(dict(wall_seconds=time.monotonic()-started,RSS_bytes=rss))
                    if rss>=c["resources"]["sampled_RSS_stop_bytes"]:stop("sampled_RSS_stop")
                    if owned_size(output)>=c["resources"]["sampled_output_stop_bytes"]:stop("inclusive_output_stop")
                    if growth_bytes(output,ROOT_EXECUTION,baseline)>=33554432:stop("incremental_growth_stop")
                except (OSError,ValueError,subprocess.SubprocessError) as exc:
                    direct_RC = process.poll()
                    if direct_RC is None:stop("RSS_observation_failed")
                    else:receipt["resource_observation_exit_races"].append(dict(error=repr(exc),direct_returncode=direct_RC,elapsed_seconds=time.monotonic()-started))
                try:process.wait(timeout=.1)
                except subprocess.TimeoutExpired:pass
            if process.poll() is None:stop("controller_SIGTERM" if term_requested else stopped["reason"] or "controller_interrupted")
            process.wait()
        need(process.returncode==0 and not stopped["reason"] and not term_requested,"Native failure retained without retry")
    except BaseException as exc:
        failure = dict(type=type(exc).__name__,message=str(exc))
    finally:
        timer.cancel()
        if process is not None:
            if process.poll() is None:stop("controller_interrupted")
            process.wait()
    if process is not None:
        try:
            os.killpg(process.pid,0)
            stopped["reason"] = stopped["reason"] or "lingering_owned_native_group"
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            until = time.monotonic()+10
            while time.monotonic()<until:
                try:os.killpg(process.pid,0)
                except ProcessLookupError:break
                time.sleep(.05)
        except ProcessLookupError:pass
    unchanged = all(same(output/name,h) for name,h in inputs.items()) and same(contract,expected) and same(ROOT_EXECUTION/"authorization.json",admission_sha)
    try:check_pins(c["input_sha256"]); stable=runtime_unchanged(c)
    except (OSError,ValueError) as exc:stable=False;receipt["identity_error"]=repr(exc)
    native_group_absent = False
    if process is not None:
        try:os.killpg(process.pid,0)
        except ProcessLookupError:native_group_absent=True
    required = {name:dict(present=(output/name).is_file(),bytes=(output/name).stat().st_size if (output/name).is_file() else None) for name in ("rich2-END181-dof-map.json","physical-X.petsc","physical-F.petsc","physical-Y.petsc")}
    presence = all(v["present"] and v["bytes"]>0 for v in required.values()) and required["rich2-END181-dof-map.json"]["bytes"]<=1048576 and not (output/"rich2-END181-dof-map.json.part").exists()
    if time.monotonic()>=deadline:stopped["reason"]=stopped["reason"] or "stage_deadline"
    before_receipt_bytes=owned_size(output)
    if before_receipt_bytes>=c["resources"]["sampled_output_stop_bytes"]:stopped["reason"]=stopped["reason"] or "inclusive_output_stop"
    if growth_bytes(output,ROOT_EXECUTION,baseline)>=33554432:stopped["reason"]=stopped["reason"] or "incremental_growth_stop"
    completed=bool(process is not None and process.returncode==0 and failure is None and stopped["reason"] is None and not term_requested and unchanged and stable and native_group_absent and presence)
    receipt.update(status="stopped_outputs_preserved",returncode=process.returncode if process else None,process_reaped=process is not None and process.poll() is not None,native_group_absent=native_group_absent,controller_error=failure,controller_SIGTERM_requested=term_requested,stop_reason=stopped["reason"],wall_seconds=time.monotonic()-started,max_observed_RSS_bytes=max((s["RSS_bytes"] for s in receipt["RSS_samples"]),default=None),inputs_unchanged=unchanged,binary_and_runtime_unchanged=stable,required_output_presence_only=required,complete_stream_map_or_field_association_proved=False,native_execution_completed_candidate=completed,inclusive_bytes_before_receipt=before_receipt_bytes,incremental_growth_bytes_before_receipt=growth_bytes(output,ROOT_EXECUTION,baseline),receipt_signal_scope="SIGTERM latch retained through receipt write; flags prefinal; caller0 and outer0 plus inclusive postchecks required")
    receipt["complete_artifact_sha256"]={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file() and not p.is_symlink()}
    with (output/"native-execution.json").open("x") as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write("\n")
    inclusive=owned_size(output);growth=growth_bytes(output,ROOT_EXECUTION,baseline);elapsed=time.monotonic()-started
    signal.signal(signal.SIGTERM,previous)
    # Signals after restoration are outside the saved latch; any nonzero caller status refuses capture.
    need(completed and not term_requested and not receipt["controller_stop_requests"] and inclusive<c["resources"]["sampled_output_stop_bytes"] and growth<33554432 and elapsed<100,"Post-receipt native closure refused; retain prefinal receipt and require caller/outer RC0")
    return dict(receipt="native-execution.json",returncode=process.returncode,prefinal_candidate=completed,postreceipt_inclusive_bytes=inclusive,postreceipt_growth_bytes=growth,wall_seconds=elapsed)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",choices=("coupon",),required=True)
    parser.add_argument("--contract",type=Path,required=True)
    parser.add_argument("--contract-sha256",required=True)
    parser.add_argument("--root-admission-sha256",required=True)
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    if not args.execute:raise SystemExit("Held source; separate exact root authority required")
    print(json.dumps(run(args.stage,args.contract,args.contract_sha256,args.root_admission_sha256)),flush=True)
