"""Bound exact source-chart construction and independent STEP checks per chunk."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import gzip
import hashlib
import json
import importlib
import importlib.metadata
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

from chart_common import job, save, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4); parser.add_argument("--deadline-seconds", type=int, default=2700)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--controls-only", action="store_true"); mode.add_argument("--chunk", type=int)
    mode.add_argument("--all-chunks", action="store_true")
    args = parser.parse_args(); initial_job_sha = sha(args.job); value, root = job(args.job)
    assert 1 <= args.workers <= 4 and 60 <= args.deadline_seconds <= 3000
    args.output.mkdir(mode=0o700, exist_ok=False); started = time.monotonic()
    import OCP
    import numpy
    import scipy
    packages = {}
    for name in ("cadquery-ocp-novtk", "cadquery-ocp"):
        try:packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:pass
    native = sys.modules.get("OCP.OCP")
    save(args.output/"runtime.json", {"python": sys.version.split()[0], "machine": os.uname().machine,
         "numpy": numpy.__version__, "scipy": scipy.__version__, "ocp": getattr(OCP, "__version__", None),
         "distributions": packages, "ocp_core_sha256": sha(Path(native.__file__)) if native is not None else None,
         "job_sha256": initial_job_sha})
    stop = threading.Event(); lock = threading.Lock(); children = {}; complete = False; completed = []
    def stopped(signum, frame):
        stop.set()
    signal.signal(signal.SIGTERM, stopped); signal.signal(signal.SIGINT, stopped)
    environment = os.environ.copy()
    environment.update(PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    def run(name, command):
        assert not stop.is_set()
        before = time.monotonic(); peak = 0; limited = False
        with (args.output/(name+".log")).open("x") as stream:
            child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=environment,
                                     start_new_session=True)
            with lock:children[child.pid] = command
            save(args.output/(name+"-running.json"), {"pid": child.pid, "argv": command, "epoch": time.time()})
            try:
                while child.poll() is None:
                    time.sleep(.5)
                    sample = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)], capture_output=True, text=True)
                    if sample.stdout.strip():peak = max(peak, int(sample.stdout.strip()))
                    if (stop.is_set() or time.monotonic()-started > args.deadline_seconds
                            or time.monotonic()-before > 615 or peak > 4*1024**2
                            or shutil.disk_usage(args.output).free < 4*1024**3):
                        limited = True; os.killpg(child.pid, signal.SIGTERM); break
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid, signal.SIGKILL); child.wait()
            finally:
                if child.poll() is None:os.killpg(child.pid, signal.SIGKILL); child.wait()
                with lock:children.pop(child.pid)
        result = {"exit_code": child.returncode, "controller_limit_reached": limited,
                  "seconds": time.monotonic()-before, "sampled_peak_rss_kib": peak,
                  "log_sha256": sha(args.output/(name+".log")), "exact_owned_child_reaped": True}
        save(args.output/(name+"-execution.json"), result); return result
    def command(script, *arguments):
        return [sys.executable, "-B", str(root/script), "--job", str(args.job), *map(str, arguments)]
    def success(result):
        assert result["exit_code"] == 0 and not result["controller_limit_reached"]
    try:
        result = run("build-controls", command("build_chart.py", "--controls", "--output", args.output/"controls")); success(result)
        for name, filename in (("square", "shared-square-control.step"), ("point-contact", "point-contact-control.step")):
            result = run("verify-control-"+name, command("verify_chart.py", "--control", name,
                "--step", args.output/"controls"/filename, "--output", args.output/("verified-control-"+name+".json")))
            success(result)
        result = run("refuse-unsewn-control", command("verify_chart.py", "--control", "square",
            "--step", args.output/"controls/unsewn-square-negative.step", "--output", args.output/"forbidden-unsewn-success.json"))
        assert result["exit_code"] != 0 and not result["controller_limit_reached"]
        assert "Native source edge was duplicated or introduced" in (args.output/"refuse-unsewn-control.log").read_text()
        assert not (args.output/"forbidden-unsewn-success.json").exists()
        save(args.output/"control-admission.json", {"positive_square_and_point_contact_actual_STEP_verified": True,
             "unsewn_same_geometry_refused_for_expected_topology_reason": True, "head_admitted_for_reference_trial": True})
        chunks = [] if args.controls_only else ([args.chunk] if args.chunk is not None else list(range(value["chunk_count"])))
        def task(index):
            prefix = "chunk-"+str(index).zfill(4); destination = args.output/prefix
            result = run(prefix+"-build", command("build_chart.py", "--chunk", index, "--output", destination)); success(result)
            step = destination/"source-chart.step"
            result = run(prefix+"-verify", command("verify_chart.py", "--chunk", index, "--step", step,
                                                  "--output", destination/"independent-verification.json")); success(result)
            original_sha = sha(step); raw_bytes = step.stat().st_size; packed = destination/"source-chart.step.gz"
            with step.open("rb") as source, packed.open("xb") as target:
                with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as archive:
                    while data := source.read(1024**2):
                        assert not stop.is_set() and time.monotonic()-started <= args.deadline_seconds
                        assert shutil.disk_usage(args.output).free >= 4*1024**3
                        archive.write(data)
            digest = hashlib.sha256(); byte_count = 0
            with gzip.open(packed, "rb") as source:
                while data := source.read(1024**2):digest.update(data); byte_count += len(data)
            assert digest.hexdigest() == original_sha and byte_count == raw_bytes
            save(destination/"compression-proof.json", {"verified_raw_step_sha256": original_sha,
                 "verified_raw_step_bytes": raw_bytes, "gzip_sha256": sha(packed), "gzip_bytes": packed.stat().st_size,
                 "complete_decompressed_bytes_rehashed": True, "uncompressed_transient_removed_only_after_check": True})
            step.unlink()
            report = json.loads((destination/"independent-verification.json").read_text())
            return {"chunk": index, "source_faces": report["source_faces"], "report_sha256": sha(destination/"independent-verification.json"),
                    "step_gzip_sha256": sha(packed), "step_gzip_bytes": packed.stat().st_size}
        remaining = iter(chunks)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {}
            for _ in range(min(args.workers, len(chunks))):
                index = next(remaining); pending[pool.submit(task, index)] = index
            try:
                while pending:
                    ready, _ = wait(pending, timeout=1, return_when=FIRST_COMPLETED)
                    if time.monotonic()-started > args.deadline_seconds:stop.set()
                    assert not stop.is_set(), "Global job deadline or stop request"
                    for future in ready:
                        pending.pop(future); completed.append(future.result())
                        print(json.dumps({"chunks_verified": len(completed), "chunks_requested": len(chunks),
                                          "last_chunk": completed[-1]["chunk"]}), flush=True)
                        index = next(remaining, None)
                        if index is not None:pending[pool.submit(task, index)] = index
            except BaseException:
                stop.set()
                for future in pending:future.cancel()
                raise
        assert len(completed) == len(chunks); job(args.job)
        assert sha(args.job) == initial_job_sha; complete = True
    finally:
        stop.set()
        assert not children, "Owned children not reaped"
        summary = {"source_sha256": sha(Path(__file__)), "job_sha256": sha(args.job), "complete": complete,
             "requested_all_chunks": args.all_chunks, "controls_only": args.controls_only,
             "completed_chunks": sorted(completed, key=lambda r: r["chunk"]), "workers": args.workers,
             "all_owned_children_reaped": True, "original_inputs_rehashed_unchanged": complete,
             "physical_acceptance": False, "manufacturing_authorized": False, "seconds": time.monotonic()-started}
        save(args.output/"terminal.json", summary)
        files = [{"path": str(p.relative_to(args.output)), "bytes": p.stat().st_size, "sha256": sha(p)}
                 for p in sorted(args.output.rglob("*")) if p.is_file()]
        save(args.output/"manifest.json", {"complete": complete, "files": files})
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
