"""Bound the native source-envelope collapse trial; independently audit every candidate later."""
import argparse
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

import numpy as np

from mesh_head import ROOT, FAMILY, bound_head, canonical_oriented, new_output, read_binary_stl, save, sha
from prepare_head_analysis import validate_surface

CONTRACT = FAMILY / "engineering/analysis-envelope-contract.json"
CONTRACT_SHA256 = "52f57ec4126202907cae045323b9643525b8816ce60792051fafe5c62caac6d4"


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


def run(output):
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError("Frozen source-envelope method contract changed")
    contract = json.loads(CONTRACT.read_text())
    verify = lambda: all(sha(ROOT / p) == h for p, h in contract["input_hashes"].items())
    if not verify():
        raise ValueError("Bound source, runtime or fixture evidence changed")
    new_output(output)
    source = Path(__file__).resolve()
    (output / "source-executed.py").write_bytes(source.read_bytes())
    report = dict(status="preparing_exact_indexed_input", source_sha256=sha(source),
        contract_sha256=sha(CONTRACT), contract=contract, length_unit="mm",
        qualification=dict(analysis_surface_geometric_gate_passed=False,
            solver_admission_established=False, mesh_convergence_established=False,
            engineering_accepted=False, thermal_performance_validated=False,
            strength_validated=False, manufacturing_authorized=False))
    target = output / "receipt.json"
    started = time.monotonic()
    try:
        stl, _, _ = bound_head(95)
        _, points, faces = read_binary_stl(stl)
        write_surface(output / "exact-input.bin", points, faces)
        p, f = read_surface(output / "exact-input.bin")
        if not np.array_equal(p, points) or not np.array_equal(f, faces):
            raise ValueError("Exact source binary serialization changed")
        report.update(source_surface=validate_surface(points, faces), exact_input_sha256=sha(output / "exact-input.bin"))
        command = ["docker", "run", "--name", "962-cgal-envelope-head-001", "--network", "none", "--read-only",
            "--cpus", "2", "--memory", "4g", "--memory-swap", "4g",
            "--mount", f"type=bind,src={(output / 'exact-input.bin').resolve()},dst=/input.bin,readonly",
            "--mount", f"type=bind,src={output.resolve()},dst=/out",
            contract["runtime"]["helper_image_id"], "/input.bin", "/out/native", ".25", "285"]
        report.update(status="native_running", command=command, hard_native_deadline_s=300)
        save(target, report)
        native_started = time.monotonic()
        with (output / "native.log").open("x") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "kill", "962-cgal-envelope-head-001"], stdout=log,
                    stderr=subprocess.STDOUT, timeout=20)
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(); report["status"] = "hard_native_deadline_outputs_preserved"
        report.update(native_returncode=process.returncode, native_wall_s=time.monotonic()-native_started,
            native_log_sha256=sha(output / "native.log"))
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
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc))
    finally:
        report.update(wall_s=time.monotonic()-started, bound_inputs_unchanged=verify()
            and sha(CONTRACT) == CONTRACT_SHA256 and sha(source) == report["source_sha256"]
            and sha(output / "source-executed.py") == report["source_sha256"],
            native_surface_hashes={str(p.relative_to(output)):sha(p) for p in (output / "native").glob("*.bin")})
        if not report["bound_inputs_unchanged"]:
            report.update(status="failed_outputs_preserved", error="Bound method/source/runtime inputs changed")
        save(target, report)
    print(json.dumps({k:report.get(k) for k in ("status","native_returncode","native_wall_s","wall_s","error")}))
    return 0 if report["status"] == "candidate_prepared_all_independent_gates_pending" else 2


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();raise SystemExit(run(args.output))
