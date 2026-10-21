"""Held Mac-local MOOSE metadata readiness, then a separately authorized fixed assumed thermal-birth coupon."""

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
CASE = ENGINEERING / "cp1-assumed-thermal-birth-linear-prep-001"
CARD = CASE / "card.json"
PHYSICS = CASE / "case-contract.json"
PRIMARY_API = ENGINEERING / "imported-elastic-cube-macos-prep-004/primary-api.json"
HELD = PREP / "held-preparation.json"
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "OMP_NUM_THREADS": "1",
               "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "FI_PROVIDER": "tcp"}
CASE_FILES = ("thermal-birth.i", "time-level.i", "assess.py")
FEATURES = ("GeneratedMeshGenerator", "SubdomainBoundingBoxGenerator", "FunctionIC",
            "ADTimeDerivative", "ADHeatConductionTimeDerivative", "ADHeatConduction", "ADMatHeatSource",
            "ADHeatConductionMaterial", "ADGenericConstantMaterial", "FunctionPathEllipsoidHeatSource",
            "TimedSubdomainModifier", "ADMaterialRealAux", "NodalValueSampler", "ElementValueSampler",
            "ADElementIntegralMaterialProperty", "SMP", "Transient", "CSV", "Console", "ParsedFunction")


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
    common = [str(EXECUTABLE), "-skip_petscrc", "--n-threads=1"]
    if stage == "readiness":
        return [("help", common + ["--help"]), ("version", common + ["--version"]),
                ("registry", common + ["--registry"])]
    need(stage == "coupon", "Only the two declared stages exist")
    return [("native", common + ["-i", "thermal-birth.i", "time-level.i"])]


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
    need(c.get("schema") == "962-macos-cp1-thermal-birth-stage-actual/v1" and c.get("stage") == stage
         and c.get("root_and_peer_review_complete") is True and c.get("native_launch_authorized") is True
         and c.get("head_authorized") is False and c.get("manufacturing_authorized") is False,
         "Separate reviewed stage authority required")
    need(c.get("coupon_solve_authorized") is (stage == "coupon"), "Readiness cannot authorize the coupon")
    pins = c["input_sha256"]
    need(pins.get(str(HELD.relative_to(ROOT))) == sha(HELD), "Held preparation is not directly bound")
    held = json.loads(HELD.read_text())
    need(all(pins.get(k) == v for k, v in held["input_sha256"].items()), "Prepared input omitted")
    check_pins(pins)
    need(c["runtime_sha256s"] == held["runtime_sha256s"] and len(c["runtime_sha256s"]) == 19
         and c["runtime_symlinks"] == held["runtime_symlinks"] and len(c["runtime_symlinks"]) == 13
         and "lib/combined/libheat_transfer-opt.0.dylib" in c["runtime_sha256s"],
         "Exact reviewed19 selected files/13 links including heat-transfer library required")
    need(all(c.get(k) is False for k in ["engineering_accepted", "physics_qualified", "material_qualified", "process_calibrated"])
         and c.get("automatic_retry") is False, "No qualification or retry authority")
    need("bin/combined-opt" in c["runtime_sha256s"] and c["runtime_symlinks"].get("bin/moose-opt") == "combined-opt"
         and runtime_unchanged(c) and os.access(EXECUTABLE, os.X_OK), "Actual installed runtime bindings required")
    need(c["installation_result_peer"] in pins and c["installation_receipt"] in pins,
         "Stopped installation review and receipt must be pinned")
    limits = c["resources"]
    need(set(limits) == {"wall_seconds", "sampled_RSS_stop_bytes", "sampled_output_stop_bytes"}
         and all(type(v) in (int, float) and not isinstance(v, bool) and v > 0
                 and v < float("inf") for v in limits.values()), "Explicit finite positive Mac sampled limits required")
    if stage == "coupon":
        need(limits == held["coupon_resources"], "Exact reviewed per-level coupon bounds required")
        need(all(c[k] in pins for k in ["readiness_receipt", "readiness_result_peer", "readiness_registry"]),
             "Stopped readiness, peer and exact cached registry required")
        ready = json.loads((ROOT / c["readiness_receipt"]).read_text())
        prior18 = {k: v for k, v in c["runtime_sha256s"].items() if k != "lib/combined/libheat_transfer-opt.0.dylib"}
        need(ready.get("readiness_completed") is True and len(prior18) == 18
             and ready["runtime_sha256s"] == prior18 and ready["runtime_symlinks"] == c["runtime_symlinks"]
             and all(v is True for v in ready["required_object_presence"].values())
             and pins[c["readiness_registry"]] == ready["artifact_sha256"]["registry.log"],
             "Exact old18 subset plus root-bound new heat library and cached registry required")
        registry_features((ROOT / c["readiness_registry"]).read_text())
    output = Path(c["output"])
    need(output.is_absolute() and output.parent == ENGINEERING and output.resolve() == output
         and not output.exists() and not output.is_symlink(), "Fresh direct task output required")
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
        shutil.copyfile(CARD, output / "card.json")
        selected += [CASE / name for name in CASE_FILES] + [CARD, PHYSICS]
    for path in selected:
        destination = snapshots / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    inputs = {str(path.relative_to(output)): sha(path) for path in output.rglob("*") if path.is_file()}
    receipt = dict(status="running", passed=False,
                   command=commands(stage)[0][1] if stage == "coupon" else [argv for _, argv in commands(stage)],
                   stage=stage, contract_sha256=expected, actual_contract_sha256=expected,
                   physics_contract_sha256=sha(PHYSICS) if stage == "coupon" else None,
                   level=2 if stage == "coupon" else None, level_is_declared=True, input_sha256=inputs,
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
    parser.add_argument("--stage", choices=("readiness", "coupon"), required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Held source; separate exact stage authority required")
    print(json.dumps(run(args.stage, args.contract, args.contract_sha256)))
