"""Held fixed SI prescribed cooling/clamp/release case; inherited Mac lifecycle, no automatic assessment."""

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

PREP = Path(__file__).resolve().parent
ENGINEERING = PREP.parent
ROOT = ENGINEERING.parent.parent
PREFIX = ENGINEERING / "moose-local-installed-002"
EXECUTABLE = PREFIX / "bin/combined-opt"
CASE = PREP
TRANSFER = ENGINEERING / "cp1-oneway-cooling-release-inputs-001"
CARD = CASE / "card.json"
PHYSICS = CASE / "case-contract.json"
PRIMARY_API = PREP / "source-evidence.json"
HELD = PREP / "held-preparation.json"
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "OMP_NUM_THREADS": "1",
               "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "FI_PROVIDER": "tcp"}
CASE_FILES = ("thermoelastic-birth.i",)
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


def commands(stage):
    need(stage == "coupon", "Only the fixed thermoelastic case is available")
    common = [str(EXECUTABLE), "-skip_petscrc", "--n-threads=1"]
    return [("native", common + ["-i", "thermoelastic-birth.i"])]

def registry_features(text):
    rows = [line.split("\t") for line in text.splitlines()]
    need(["Label", "Type", "Name", "Class", "File"] in rows, "Documented registry header missing")
    objects = {row[2] for row in rows if len(row) == 5 and row[1] == "object"}
    need(set(FEATURES) <= objects, "Required explicit deck object is not registered")
    return {name: True for name in FEATURES}


def checked_contract(stage, path, expected):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and path.resolve() == path
         and re.fullmatch("[0-9a-f]{64}", expected) and same(path, expected), "Exact external actual child required")
    c = json.loads(path.read_text())
    need(stage == "coupon" and c.get("schema") == "962-macos-oneway-cooling-release-richardson2-case-actual/v1"
         and c.get("stage") == stage and c.get("root_and_peer_review_complete") is True
         and c.get("native_launch_authorized") is True and c.get("coupon_solve_authorized") is True
         and all(c.get(k) is False for k in ("head_authorized", "engineering_accepted", "physics_qualified",
                                           "material_qualified", "process_calibrated", "manufacturing_authorized",
                                           "automatic_retry")), "Separate reviewed fixed-case authority required")
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
    need(output == ENGINEERING / "cp1-oneway-cooling-release-richardson2-001" and output.resolve() == output
         and not output.exists() and not output.is_symlink(), "Fresh fixed direct case output required")
    return c, output

def run(stage, contract, expected):
    started = time.monotonic()
    c, output = checked_contract(stage, contract, expected)
    deadline = started + c["resources"]["wall_seconds"]
    need(time.monotonic() < deadline, "Stage deadline expired before output creation")
    output.mkdir()
    shutil.copyfile(contract, output / "actual-contract.json")
    shutil.copyfile(PHYSICS if stage == "coupon" else contract, output / "frozen-contract.json")
    snapshots = output / "source-snapshots"
    snapshots.mkdir()
    selected = [Path(__file__), HELD, PREP / "METHOD.md", PRIMARY_API]
    if stage == "coupon":
        for name in CASE_FILES:
            shutil.copyfile(CASE / name, output / name)
        for name in TRANSFER_FILES:
            shutil.copyfile(TRANSFER / name, output / name)
        shutil.copyfile(CARD, output / "card.json")
        selected += [CASE / name for name in CASE_FILES] + [TRANSFER / name for name in TRANSFER_FILES] + [CARD, PHYSICS]
    for path in selected:
        destination = snapshots / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    inputs = {str(path.relative_to(output)): sha(path) for path in output.rglob("*") if path.is_file()}
    receipt = dict(status="running", passed=False,
                   command=commands(stage)[0][1] if stage == "coupon" else [argv for _, argv in commands(stage)],
                   stage=stage, contract_sha256=expected, actual_contract_sha256=expected,
                   physics_contract_sha256=sha(PHYSICS) if stage == "coupon" else None,
                   level=None, level_is_declared=False, thermal_input_level=2,
                   transfer_manifest_sha256=c["transfer_manifest_sha256"],
                   prescribed_temperature_and_born_reference=True, source_off_cooling_history_present=False,
                   prescribed_cooling_extension_present=True, build_clamp_then_release=True, input_sha256=inputs,
                   runtime_sha256s=c["runtime_sha256s"], runtime_symlinks=c["runtime_symlinks"],
                   network="not_requested_not_OS_sandboxed", rootfs="installed_prefix_not_sandboxed",
                   automatic_retry=False, head_input_read=False, independent_assessment_performed=False,
                   hard_OS_CPU_or_memory_quota=False, RSS_scope="sampled_owned_leader_only",
                   process_reaped=False, jobs=[], RSS_samples=[], native_execution_completed=False,
                   readiness_completed=False, required_object_presence=None)
    failure = None
    stopped = {"reason": None}
    lock = threading.Lock()
    process = None
    previous = signal.getsignal(signal.SIGTERM)
    term_requested = False

    def interrupted(*_):
        nonlocal term_requested
        term_requested = True

    def stop(reason):
        with lock:
            stopped["reason"] = stopped["reason"] or reason
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    timer = threading.Timer(max(0., deadline - time.monotonic()), lambda: stop("stage_deadline"))
    timer.daemon = True
    timer.start()
    with (output / "launch.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    try:
        signal.signal(signal.SIGTERM, interrupted)
        for name, argv in commands(stage):
            need(not term_requested and not stopped["reason"] and time.monotonic() < deadline,
                 "Stage refused before the next Popen")
            process = None
            with (output / f"{name}.log").open("xb") as log:
                try:
                    process = subprocess.Popen(argv, cwd=output, env=ENVIRONMENT, stdout=log,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    if stopped["reason"] or term_requested:
                        stop("controller_SIGTERM" if term_requested else stopped["reason"])
                    while process.poll() is None and not term_requested and not stopped["reason"]:
                        try:
                            sample = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(process.pid)],
                                                    capture_output=True, text=True, timeout=2)
                            if process.poll() is not None:
                                break
                            rss = int(sample.stdout.strip()) * 1024
                            need(sample.returncode == 0 and rss >= 0, "Invalid owned-leader RSS observation")
                            receipt["RSS_samples"].append(dict(job=name, wall_seconds=time.monotonic() - started, RSS_bytes=rss))
                            if rss >= c["resources"]["sampled_RSS_stop_bytes"]:
                                stop("sampled_RSS_stop")
                            if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) >= c["resources"]["sampled_output_stop_bytes"]:
                                stop("sampled_output_stop")
                        except (OSError, ValueError, subprocess.SubprocessError):
                            if process.poll() is None:
                                stop("RSS_observation_failed")
                        try:
                            process.wait(timeout=.1)
                        except subprocess.TimeoutExpired:
                            pass
                finally:
                    if process is not None:
                        if process.poll() is None:
                            stop("controller_SIGTERM" if term_requested else stopped["reason"] or "controller_interrupted")
                        process.wait()
            receipt["jobs"].append(dict(name=name, returncode=process.returncode if process else None,
                                        process_reaped=process is not None and process.poll() is not None))
            need(process is not None and process.returncode == 0 and not stopped["reason"] and not term_requested,
                 "Native command incomplete; preserve outputs without retry")
        if stage == "readiness":
            need((output / "help.log").stat().st_size > 0 and (output / "version.log").stat().st_size > 0,
                 "Help and version must be nonempty observations")
            receipt["required_object_presence"] = registry_features((output / "registry.log").read_text())
            receipt["readiness_completed"] = True
    except BaseException as error:
        failure = type(error).__name__ + ": " + str(error)
        raise
    finally:
        try:
            timer.cancel()
            if process is not None:
                if process.poll() is None:
                    stop("controller_interrupted")
                process.wait()
        finally:
            signal.signal(signal.SIGTERM, previous)
        if time.monotonic() >= deadline:
            stopped["reason"] = stopped["reason"] or "stage_deadline"
        size = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
        if size >= c["resources"]["sampled_output_stop_bytes"]:
            stopped["reason"] = stopped["reason"] or "sampled_output_stop"
        unchanged = all(same(output / name, h) for name, h in inputs.items()) and same(contract, expected)
        try:
            check_pins(c["input_sha256"])
        except (ValueError, OSError):
            unchanged = False
        try:
            stable = runtime_unchanged(c)
        except (ValueError, OSError) as error:
            stable = False
            receipt["runtime_verification_failure_type"] = type(error).__name__
        reaped = bool(receipt["jobs"]) and all(job["process_reaped"] for job in receipt["jobs"])
        completed = failure is None and stopped["reason"] is None and not term_requested and unchanged and stable and reaped
        receipt.update(status="native_stopped_outputs_preserved", returncode=process.returncode if process else None,
                       process_reaped=reaped, controller_error=failure, controller_SIGTERM_requested=term_requested,
                       wall_seconds=time.monotonic() - started, stop_reason=stopped["reason"],
                       max_observed_RSS_bytes=max((s["RSS_bytes"] for s in receipt["RSS_samples"]), default=None),
                       resources=c["resources"], final_output_bytes_before_receipt=size,
                       inputs_unchanged=unchanged, binary_and_runtime_unchanged=stable,
                       binary_sha256=c["runtime_sha256s"]["bin/combined-opt"], binary_unchanged=stable,
                       native_execution_completed=completed and stage == "coupon",
                       readiness_completed=completed and receipt["readiness_completed"])
        receipt["complete_artifact_sha256"] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*"))
                                     if p.is_file() and not p.is_symlink() and p.name not in ("native-execution.json", "readiness.json", "assessment.json")}
        receipt["artifact_sha256"] = {k: v for k, v in receipt["complete_artifact_sha256"].items() if Path(k).name == k}
        filename = "readiness.json" if stage == "readiness" else "native-execution.json"
        with (output / filename).open("x") as stream:
            json.dump(receipt, stream, indent=2, allow_nan=False)
            stream.write("\n")
    need(completed, "Stage controls or bindings failed; stopped outputs retained")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("coupon",), required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Held source; separate exact stage authority required")
    print(json.dumps(run(args.stage, args.contract, args.contract_sha256)))
