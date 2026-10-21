"""One reviewed compile OR fixture phase; never chain phases or run a head."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
PREP = "work/962-engineering/finest-surface-endpoint-preflight-002/preflight-contract-002.json"
PREP_SHA = "ae3b3130dd1a2b3e6244b8ccb7474e3d215d4027ce8eea5db2d71e5f940f85b5"
IMAGE = "sha256:57c6b17ed0bd093a61a3d3cecb7563e912caeb3832fd59e8cec2d4d9d4d1e2f8"
SOURCE = "twins/962-cylinder-head-f0/source/analysis-cgal/"
FIXTURES = "work/962-engineering/finest-surface-endpoint-preflight-002/fixture-inputs/"
TEST = "tests/test_962_finest_endpoint_controller.py"
INSPECT = ('{"Id":{{json .Id}},"Image":{{json .Image}},'
           '"Owner":{{json (index .Config.Labels "io.962-finest.owner")}},"State":{{json .State}},'
           '"Controls":{"NanoCpus":{{json .HostConfig.NanoCpus}},"Memory":{{json .HostConfig.Memory}},'
           '"MemorySwap":{{json .HostConfig.MemorySwap}},"NetworkMode":{{json .HostConfig.NetworkMode}},'
           '"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Tmpfs":{{json .HostConfig.Tmpfs}}},'
           '"Mounts":[{{range $i,$m := .Mounts}}{{if $i}},{{end}}{"Type":{{json $m.Type}},'
           '"Source":{{json $m.Source}},"Destination":{{json $m.Destination}},"RW":{{json $m.RW}}}{{end}}]}')


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")


def file_hashes(directory):
    return {str(p.relative_to(directory)): digest(p) for p in directory.rglob("*") if p.is_file()}


def limits(phase):
    compile_phase = phase == "compile"
    return dict(cpus=2, memory_bytes=4294967296 if compile_phase else 536870912,
                swap_bytes=0, tmpfs_bytes=1073741824 if compile_phase else 0,
                hard_wall_seconds_each=300 if compile_phase else 60, network="none")


def inspect(reference, calls):
    result = subprocess.run(["docker", "inspect", reference, "--format", INSPECT],
                            capture_output=True, text=True, timeout=10)
    calls.append(dict(operation="inspect", returncode=result.returncode,
                      stdout=result.stdout, stderr=result.stderr))
    if result.returncode:
        raise RuntimeError("Owned container metadata unavailable")
    return json.loads(result.stdout)


def monitor(process, deadline_at, started):
    last_progress = started
    while process.poll() is None:
        now = time.monotonic()
        if now >= deadline_at:
            raise TimeoutError("Declared native wall deadline")
        if now-last_progress >= 30:
            print(json.dumps(dict(status="bounded_native_phase_running", elapsed_seconds=now-started)), flush=True)
            last_progress = now
        try:
            process.wait(timeout=min(1, deadline_at-now))
        except subprocess.TimeoutExpired:
            pass
    # A completed poll/wait must not race an expired absolute setup-started budget.
    if time.monotonic() >= deadline_at:
        raise TimeoutError("Declared native wall deadline")


def execute(command, name, owner, output, label, deadline, expected_controls, expected_mounts):
    """Always clean up the exact owned ID, including failed setup/observers."""
    calls = []; process = None; container = None; final = None; error = None
    cleanup_errors = []; removed = False; reaped = True; initial = None
    started = time.monotonic(); deadline_at = started+deadline
    log = output/(label+".native.log")
    try:
        created = subprocess.run(command, capture_output=True, text=True, timeout=20)
        calls.append(dict(operation="create", returncode=created.returncode,
                          stdout=created.stdout, stderr=created.stderr))
        if created.returncode or not re.fullmatch(r"[0-9a-f]{64}", created.stdout.strip()):
            raise RuntimeError("Container creation refused")
        metadata = inspect(created.stdout.strip(), calls)
        if metadata["Id"] != created.stdout.strip() or metadata["Owner"] != owner or metadata["Image"] != IMAGE:
            raise RuntimeError("Unverified container ownership/image; no native start")
        container = metadata["Id"]; initial = metadata
        if metadata["State"]["Running"] or metadata["State"]["Pid"] != 0 or metadata["Controls"] != expected_controls:
            raise RuntimeError("Created container state/resources changed")
        actual_mounts = {(m["Source"], m["Destination"], m["RW"], m["Type"]) for m in metadata["Mounts"]}
        if actual_mounts != set(expected_mounts):
            raise RuntimeError("Declared read-only inputs/owned writable output changed")
        with log.open("x") as stream:
            if time.monotonic() >= deadline_at:
                raise TimeoutError("Declared native wall deadline before attach")
            process = subprocess.Popen(["docker", "start", "--attach", container], stdout=stream,
                stderr=subprocess.STDOUT, start_new_session=True)
            reaped = False
            monitor(process, deadline_at, started)
    except BaseException as exc:
        error = type(exc).__name__+": "+str(exc)
    finally:
        # A create timeout can leave only an unstarted container. Recover it by
        # its fresh name only when the exact per-run ownership label matches.
        if container is None:
            try:
                metadata = inspect(name, calls)
                if metadata["Owner"] == owner and metadata["Image"] == IMAGE:
                    container = metadata["Id"]; initial = metadata
            except BaseException as exc:
                cleanup_errors.append("ownership_lookup:"+type(exc).__name__+": "+str(exc))
        if container is not None:
            try:
                final = inspect(container, calls)
            except BaseException as exc:
                cleanup_errors.append("pre_kill_inspect:"+type(exc).__name__+": "+str(exc))
            # Unknown state is not permission to leave an already verified ID running.
            if final is None or final["State"]["Running"]:
                try:
                    killed = subprocess.run(["docker", "kill", container], capture_output=True, text=True, timeout=10)
                    calls.append(dict(operation="kill", returncode=killed.returncode,
                                      stdout=killed.stdout, stderr=killed.stderr))
                    if killed.returncode:
                        cleanup_errors.append("docker_kill_nonzero")
                except BaseException as exc:
                    cleanup_errors.append("kill:"+type(exc).__name__+": "+str(exc))
        if process is not None:
            try:
                process.wait(timeout=10); reaped = True
            except BaseException as exc:
                cleanup_errors.append("attach_wait:"+type(exc).__name__+": "+str(exc))
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3); reaped = True
                except BaseException as stop_error:
                    cleanup_errors.append("attach_reap:"+type(stop_error).__name__+": "+str(stop_error))
        if container is not None:
            try:
                final = inspect(container, calls)
                if (final["Id"] != container or final["Owner"] != owner or final["Image"] != IMAGE
                        or final["State"]["Running"] or final["State"]["Pid"] != 0):
                    raise RuntimeError("Final stopped ownership/state not established; preserve container")
                removed_result = subprocess.run(["docker", "rm", container], capture_output=True, text=True, timeout=10)
                calls.append(dict(operation="remove_stopped_owned", returncode=removed_result.returncode,
                                  stdout=removed_result.stdout, stderr=removed_result.stderr))
                removed = removed_result.returncode == 0
                if not removed:
                    cleanup_errors.append("remove_stopped_owned_nonzero")
            except BaseException as exc:
                cleanup_errors.append("final_state_or_remove:"+type(exc).__name__+": "+str(exc))
        # Synchronous final latch also covers poll/wait/cleanup completion after expiry.
        elapsed = time.monotonic()-started
        if elapsed >= deadline and error is None:
            error = "TimeoutError: Declared native wall deadline at completion"
        result = dict(label=label, command=command, error=error, cleanup_errors=cleanup_errors,
                      attach_returncode=process.returncode if process else None,
                      attach_process_started=process is not None, attach_reaped=reaped,
                      initial_metadata=initial, final_metadata=final,
                      owned_container_removed=removed, control_calls=calls,
                      wall_seconds=elapsed,
                      native_log_sha256=digest(log) if log.exists() else None)
        save(output/(label+".execution.json"), result)
    return result


def verified_child(path, expected):
    if digest(path) != expected or digest(ROOT/PREP) != PREP_SHA:
        raise ValueError("Exact reviewed child/preparation required")
    child = json.loads(path.read_text()); preparation = json.loads((ROOT/PREP).read_text())
    if child.get("schema") != "962-finest-endpoint-execution/v1" or child.get("root_authorized") is not True:
        raise ValueError("A separate root-authorized execution child is required")
    if child.get("phase") not in ("compile", "fixtures") or child.get("image_id") != IMAGE:
        raise ValueError("Only the two fixed non-head phases and pinned image are supported")
    if child.get("limits") != limits(child["phase"]):
        raise ValueError("The reviewed fixed phase resource controls changed")
    pins = dict(preparation["input_sha256"])
    for name in [PREP, str(Path(__file__).resolve().relative_to(ROOT)), TEST]:
        pins[name] = digest(ROOT/name)
    if child.get("input_sha256") != pins:
        raise ValueError("All35preparation/source/test/controller inputs must be bound exactly")
    if child["phase"] == "fixtures":
        binding = child["compile_summary"]
        summary_path = ROOT/binding["path"]
        if digest(summary_path) != binding["sha256"]:
            raise ValueError("Actual completed compilation summary changed")
        summary = json.loads(summary_path.read_text())
        if (summary.get("phase") != "compile" or summary.get("complete") is not True
                or summary.get("controller_sha256") != digest(Path(__file__))
                or summary.get("preparation_sha256") != PREP_SHA or summary.get("image_id") != IMAGE
                or summary.get("all_inputs_unchanged") is not True or summary.get("all_prior_outputs_unchanged") is not True
                or summary.get("execution_contract_sha256") == expected
                or summary.get("compiled_binaries") != child["compiled_binaries"]):
            raise ValueError("Separate child must freeze the two actual compiled binary hashes")
        if set(child["compiled_binaries"]) != {"001", "002"}:
            raise ValueError("Exactly the two declared compiled programs required")
        pins[binding["path"]] = binding["sha256"]
        for row in child["compiled_binaries"].values():
            pins[row["path"]] = row["sha256"]
    return child, pins


def run(contract_path, expected, output):
    child, pins = verified_child(contract_path, expected)
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to(ROOT/"work/962-engineering"):
        raise ValueError("Fresh task-owned engineering output required")
    def snapshot():
        observed = {}
        for p in pins:
            try:
                observed[p] = digest(ROOT/p) if (ROOT/p).is_file() and not (ROOT/p).is_symlink() else None
            except OSError:
                observed[p] = None
        return observed
    def verify():
        return digest(contract_path) == expected and snapshot() == pins
    if not verify():
        raise ValueError("A frozen source/input/binary changed before execution")
    output.mkdir(parents=True); output = output.resolve()
    (output/"frozen-execution-contract.json").write_bytes(contract_path.read_bytes())
    (output/"controller-executed.py").write_bytes(Path(__file__).read_bytes())
    compile_phase = child["phase"] == "compile"; memory = 4294967296 if compile_phase else 536870912
    controls = dict(NanoCpus=2000000000, Memory=memory, MemorySwap=memory,
                    NetworkMode="none", ReadonlyRootfs=True,
                    Tmpfs={"/tmp": "rw,size=1073741824"} if compile_phase else None)
    jobs = [("compile-001", "001"), ("compile-002", "002")] if compile_phase else [
        ("common-neighbor-source001", "001"), ("common-neighbor-source002", "002"), ("all-fixed-source002", "002")]
    rows = []; binaries = {}; all_artifacts_preserved = True
    for label, version in jobs:
        before_hashes = snapshot()
        if before_hashes != pins or digest(contract_path) != expected:
            break
        prior_outputs = file_hashes(output); owner = uuid.uuid4().hex
        name = "962-finest-"+label+"-"+owner[:10]
        mounts = [(str(output), "/out", True, "bind")]
        command = ["docker", "create", "--name", name, "--label", "io.962-finest.owner="+owner,
                   "--network", "none", "--read-only", "--cpus", "2", "--memory", str(memory),
                   "--memory-swap", str(memory)]
        if compile_phase:
            (output/label).mkdir()
            command += ["--tmpfs", "/tmp:rw,size=1073741824"]
            filename = "finest_endpoint.cpp" if version == "001" else "finest_endpoint_002.cpp"
            mounts += [(str((ROOT/(SOURCE+filename)).resolve()), "/src/finest.cpp", False, "bind"),
                       (str((ROOT/(SOURCE+"quality_patch.cpp")).resolve()), "/src/quality_patch.cpp", False, "bind")]
            entrypoint = "/usr/bin/c++"
            arguments = ["-std=c++17", "-O2", "-DNDEBUG", "/src/finest.cpp", "-o", "/out/"+label+"/finest-endpoint", "-lgmp", "-lmpfr"]
        else:
            fixture = "all-fixed-rotated.bin" if label == "all-fixed-source002" else "common-fixed-neighbor.bin"
            mounts += [(str((ROOT/child["compiled_binaries"][version]["path"]).resolve()), "/finest-endpoint", False, "bind"),
                       (str((ROOT/(FIXTURES+fixture)).resolve()), "/input.bin", False, "bind")]
            entrypoint = "/finest-endpoint"; arguments = ["/input.bin", "/out/"+label]
        for source, target, writable, _ in mounts:
            command += ["--mount", "type=bind,src="+source+",dst="+target+("" if writable else ",readonly")]
        command += ["--entrypoint", entrypoint, IMAGE]+arguments
        row = execute(command, name, owner, output, label, 300 if compile_phase else 60, controls, mounts)
        after_hashes = snapshot()
        row["all_inputs_unchanged"] = after_hashes == pins and digest(contract_path) == expected
        row["prior_outputs_unchanged"] = all((output/p).is_file() and digest(output/p) == h for p, h in prior_outputs.items())
        all_artifacts_preserved &= row["prior_outputs_unchanged"]
        save(output/(label+".bindings.json"), dict(input_sha256=pins, actual_before_sha256=before_hashes,
             actual_after_sha256=after_hashes, execution_contract_sha256=digest(contract_path), all_inputs_unchanged=row["all_inputs_unchanged"],
             prior_artifact_sha256=prior_outputs, prior_outputs_unchanged=row["prior_outputs_unchanged"],
             current_artifact_sha256=file_hashes(output)))
        state = row["final_metadata"]["State"] if row["final_metadata"] else {}
        expected_rc = 0 if compile_phase or label == "common-neighbor-source002" else 3
        good = (not row["error"] and not row["cleanup_errors"] and row["attach_reaped"]
                and row["owned_container_removed"] and row["attach_returncode"] == expected_rc
                and state.get("ExitCode") == expected_rc and state.get("Running") is False
                and state.get("OOMKilled") is False and row["all_inputs_unchanged"] and row["prior_outputs_unchanged"])
        row["execution_passed"] = good; rows.append(row)
        if not good:
            break
        if compile_phase:
            binary = output/label/"finest-endpoint"
            if not binary.is_file() or binary.is_symlink() or not binary.stat().st_size:
                break
            binaries[version] = dict(path=str(binary.relative_to(ROOT)), sha256=digest(binary))
        print(json.dumps(dict(label=label, stopped=True, returncode=row["attach_returncode"], next_phase_authorized=False)), flush=True)
    complete = len(rows) == len(jobs) and all_artifacts_preserved and verify() and all(
        r["execution_passed"] for r in rows)
    if compile_phase:
        complete &= set(binaries) == {"001", "002"}
    result = dict(schema="962-finest-bounded-phase-summary/v1", phase=child["phase"], complete=complete,
                  execution_contract_sha256=expected, preparation_sha256=PREP_SHA, image_id=IMAGE,
                  controller_sha256=digest(Path(__file__)), compiled_binaries=binaries,
                  all_inputs_unchanged=verify(), all_prior_outputs_unchanged=all_artifacts_preserved,
                  jobs=[dict(label=r["label"], execution_passed=r["execution_passed"],
                             execution_receipt_sha256=digest(output/(r["label"]+".execution.json"))) for r in rows],
                  artifact_sha256=file_hashes(output), next_phase_authorized=False,
                  fixture_numerical_acceptance_established=False, head_trial_authorized=False,
                  solver_admission_established=False, manufacturing_authorized=False)
    save(output/"phase-summary.json", result)
    return 0 if complete else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def interrupt(signum, _frame):
        raise InterruptedError("Controller signal "+str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(run(args.contract.resolve(), args.contract_sha256, args.output))
