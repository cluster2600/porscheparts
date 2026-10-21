"""Bound the native source-envelope collapse trial; independently audit every candidate later."""
import argparse
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import threading
import time

import numpy as np

from mesh_head import ROOT, FAMILY, bound_head, canonical_oriented, new_output, read_binary_stl, save, sha
from prepare_head_analysis import validate_surface

CONTRACT = FAMILY / "engineering/analysis-envelope-contract.json"
CONTRACT_SHA256 = "52f57ec4126202907cae045323b9643525b8816ce60792051fafe5c62caac6d4"
CONTRACT_HASHES = {CONTRACT: CONTRACT_SHA256,
    FAMILY / "engineering/analysis-envelope-8g-contract.json": "573ac964cecd77ef304088596a257df114fad0535a50a683fa71a78bc44cfedf"}


def write_surface(path, points, faces):
    with path.open("xb") as stream:
        stream.write(b"962SURF1"+struct.pack("<QQ", len(points), len(faces)))
        stream.write(np.ascontiguousarray(points, dtype="<f8").tobytes())
        stream.write(np.ascontiguousarray(faces, dtype="<u8").tobytes())


def read_surface(path):
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"962SURF1":
        raise ValueError("Complete indexed binary surface required")
    nv, nf = struct.unpack_from("<QQ", data, 8)
    if not nv or not nf or len(data) != 24+24*(nv+nf):
        raise ValueError("Indexed surface counts or byte length changed")
    points = np.frombuffer(data, dtype="<f8", count=3*nv, offset=24).reshape(-1, 3).copy()
    faces = np.frombuffer(data, dtype="<u8", count=3*nf, offset=24+24*nv).reshape(-1, 3).astype(np.int64)
    if not np.isfinite(points).all() or faces.min() < 0 or faces.max() >= nv:
        raise ValueError("Invalid binary surface coordinates or indices")
    return points, faces


def run(output, contract_path=CONTRACT):
    contract_path = contract_path.resolve()
    digest = CONTRACT_HASHES.get(contract_path)
    if digest is None or sha(contract_path) != digest:
        raise ValueError("Frozen source-envelope method contract changed")
    contract = json.loads(contract_path.read_text())
    validator_source = FAMILY / "source/prepare_head_analysis.py"
    validator_bound = contract["input_hashes"].get(str(validator_source.relative_to(ROOT))) == sha(validator_source)
    if not validator_bound:
        raise ValueError("Imported validator must be bound by a revised method contract")
    verify = lambda: all(sha(ROOT / p) == h for p, h in contract["input_hashes"].items())
    if not verify():
        raise ValueError("Bound source, runtime or fixture evidence changed")
    new_output(output)
    source = Path(__file__).resolve()
    (output / "source-executed.py").write_bytes(source.read_bytes())
    (output / "validator-source.py").write_bytes(validator_source.read_bytes())
    report = dict(status="preparing_exact_indexed_input", source_sha256=sha(source),
        contract_sha256=sha(contract_path), contract=contract, length_unit="mm",
        imported_validator_sha256=sha(validator_source), imported_validator_snapshot_sha256=sha(output / "validator-source.py"),
        qualification=dict(analysis_surface_geometric_gate_passed=False,
            solver_admission_established=False, mesh_convergence_established=False,
            engineering_accepted=False, thermal_performance_validated=False,
            strength_validated=False, manufacturing_authorized=False))
    target = output / "receipt.json"
    started = time.monotonic()
    process = None
    try:
        stl, _, _ = bound_head(95)
        _, points, faces = read_binary_stl(stl)
        write_surface(output / "exact-input.bin", points, faces)
        p, f = read_surface(output / "exact-input.bin")
        if not np.array_equal(p, points) or not np.array_equal(f, faces):
            raise ValueError("Exact source binary serialization changed")
        report.update(source_surface=validate_surface(points, faces), exact_input_sha256=sha(output / "exact-input.bin"))
        memory = contract["resource_limits"]["memory_bytes"]
        container = "962-cgal-envelope-head-002" if memory == 8589934592 else "962-cgal-envelope-head-001"
        command = ["docker", "run", "--name", container, "--network", "none", "--read-only",
            "--cpus", "2", "--memory", str(memory), "--memory-swap", str(memory),
            "--mount", f"type=bind,src={(output / 'exact-input.bin').resolve()},dst=/input.bin,readonly",
            "--mount", f"type=bind,src={output.resolve()},dst=/out",
            contract["runtime"]["helper_image_id"], "/input.bin", "/out/native", ".25", "285"]
        report.update(status="native_running", command=command, hard_native_deadline_s=300)
        save(target, report)
        native_started = time.monotonic()
        samples = []
        def memory_sample():
            sample = dict(elapsed_s=time.monotonic()-native_started)
            for key, cmd in (("host_vm_stat", ["vm_stat"]), ("container_stats", ["docker", "stats", "--no-stream", "--format", "{{json .}}", container])):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    sample[key] = result.stdout.strip()
                except (OSError, subprocess.SubprocessError) as exc:
                    sample[key] = "Observation failed: " + str(exc)
            samples.append(sample)
            save(output / "memory-observations.json", dict(samples=samples, monitoring_is_not_a_mesh_gate=True))
        memory_sample()
        with (output / "native.log").open("x") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            def hard_stop():
                report["status"] = "hard_native_deadline_outputs_preserved"
                try:
                    subprocess.run(["docker", "kill", container],stdout=log,stderr=subprocess.STDOUT,timeout=20)
                finally:
                    if process.poll() is None:
                        try:
                            os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:
                            pass
            watchdog = threading.Timer(300,hard_stop); watchdog.daemon=True; watchdog.start()
            try:
                while process.poll() is None:
                    remaining = 300-(time.monotonic()-native_started)
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(command,300)
                    try:
                        process.wait(timeout=min(2,remaining))
                    except subprocess.TimeoutExpired:
                        memory_sample()
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "kill", container], stdout=log,
                    stderr=subprocess.STDOUT, timeout=20)
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(); report["status"] = "hard_native_deadline_outputs_preserved"
            finally:
                watchdog.cancel()
        report.update(native_returncode=process.returncode, native_wall_s=time.monotonic()-native_started,
            native_log_sha256=sha(output / "native.log"))
        state = subprocess.run(["docker", "inspect", container, "--format", "{{json .State}}"],
            capture_output=True, text=True, timeout=5)
        report["container_state"] = json.loads(state.stdout) if state.returncode == 0 else None
        report["memory_observations_sha256"] = sha(output / "memory-observations.json")
        lines = (output / "native.log").read_text().splitlines()
        report["native_records"] = [json.loads(line) for line in lines if line.startswith("{")]
        before = output / "native/before-collapse.bin"
        if before.exists():
            p, f = read_surface(before)
            report["source_import_exact"] = bool(np.array_equal(p, points)
                and np.array_equal(canonical_oriented(f), canonical_oriented(faces)))
            if not report["source_import_exact"]:
                raise ValueError("CGAL source import changed exact coordinates or oriented triangles")
        candidate = output / "native/surface.bin"
        if not candidate.exists():
            checkpoints = sorted((output / "native").glob("checkpoint-*.bin"), key=lambda p: int(p.stem.split("-")[-1]))
            candidate = checkpoints[-1] if checkpoints else None
        if candidate:
            q, g = read_surface(candidate)
            np.savez_compressed(output / "analysis-surface.npz", points_mm=q, triangles=g)
            report.update(selected_native_candidate=str(candidate.relative_to(output)),
                candidate_surface=validate_surface(q, g),
                analysis_surface_npz_sha256=sha(output / "analysis-surface.npz"))
            report["relative_source_volume_change"] = report["candidate_surface"]["signed_volume_mm3"] / report["source_surface"]["signed_volume_mm3"] - 1
        if report["status"] == "native_running":
            report["status"] = "candidate_prepared_all_independent_gates_pending" if process.returncode == 0 else "native_stopped_outputs_preserved_no_admission"
    except Exception as exc:
        if process is not None and process.poll() is None:
            subprocess.run(["docker","kill",container],capture_output=True,timeout=20)
            try:
                os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc))
    finally:
        report.update(wall_s=time.monotonic()-started, bound_inputs_unchanged=verify()
            and sha(contract_path) == digest and sha(source) == report["source_sha256"]
            and sha(output / "source-executed.py") == report["source_sha256"]
            and sha(output / "validator-source.py") == report["imported_validator_sha256"],
            native_surface_hashes={str(p.relative_to(output)):sha(p) for p in (output / "native").glob("*.bin")})
        if not report["bound_inputs_unchanged"]:
            report.update(status="failed_outputs_preserved", error="Bound method/source/runtime inputs changed")
        save(target, report)
    print(json.dumps({k:report.get(k) for k in ("status","native_returncode","native_wall_s","wall_s","error")}))
    return 0 if report["status"] == "candidate_prepared_all_independent_gates_pending" else 2


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--contract",type=Path,default=CONTRACT)
    args=parser.parse_args();raise SystemExit(run(args.output,args.contract))
