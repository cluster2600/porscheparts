"""Bounded local FreeCAD reference documents with independent saved-shape checks.

Run only after complete recovered STEP provenance has been verified. Each chart
has its own document to bound native import memory. This does not sew charts,
identify anatomical parts, create parametric head features or qualify a build.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):h.update(data)
    return h.hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:json.dump(value, stream, indent=2); stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args(); spec = json.loads(args.job.read_text()); job_sha = sha(args.job)
    assert spec["schema"] == "935-native-source-chart-set-1"
    assert spec["workers"] == 4 and spec["deadline_seconds"] == 7200
    assert spec["child_seconds"] == 600 and spec["child_rss_gib"] == 4
    assert len(spec["items"]) == 83 and [x["chunk"] for x in spec["items"]] == list(range(83))
    assert sum(x["counts"][2] for x in spec["items"]) == 2465836
    assert all(x["counts"][4] == 0 for x in spec["items"])
    for item in spec["inputs"]:assert sha(item["path"]) == item["sha256"]
    for item in spec["items"]:assert sha(item["gzip"]) == item["gzip_sha256"]
    output = Path(spec["output"]); output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic(); stop = threading.Event(); lock = threading.Lock(); children = {}
    completed = []; complete = False
    def interrupt(signum, frame):stop.set()
    signal.signal(signal.SIGTERM, interrupt); signal.signal(signal.SIGINT, interrupt)
    environment = os.environ.copy()
    environment.update(PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    def run(directory, name, command, extra_environment=None, marker=None):
        assert not stop.is_set(); peak = 0; limited = False; before = time.monotonic()
        env = environment.copy(); env.update(extra_environment or {})
        with (directory/(name+".log")).open("x") as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     env=env, start_new_session=True)
            with lock:children[child.pid] = command
            save(directory/(name+"-running.json"), {"pid": child.pid, "argv": command, "epoch": time.time()})
            try:
                while child.poll() is None:
                    time.sleep(.5)
                    sample = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)], capture_output=True, text=True)
                    if sample.stdout.strip():peak = max(peak, int(sample.stdout.strip()))
                    if (stop.is_set() or time.monotonic()-started > spec["deadline_seconds"]
                            or time.monotonic()-before > spec["child_seconds"]
                            or peak > spec["child_rss_gib"]*1024**2
                            or shutil.disk_usage(output).free < 4*1024**3):
                        limited = True; os.killpg(child.pid, signal.SIGTERM); break
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid, signal.SIGKILL); child.wait()
            finally:
                if child.poll() is None:os.killpg(child.pid, signal.SIGKILL); child.wait()
                with lock:children.pop(child.pid)
        result = {"exit_code": child.returncode, "controller_limit_reached": limited,
                  "seconds": time.monotonic()-before, "sampled_peak_rss_kib": peak,
                  "log_sha256": sha(directory/(name+".log")), "exact_owned_child_reaped": True}
        save(directory/(name+"-execution.json"), result)
        assert child.returncode == 0 and not limited, name+" failed"
        if marker is not None:assert marker in (directory/(name+".log")).read_text()
    def task(item):
        index = item["chunk"]; directory = output/("chunk-"+str(index).zfill(4)); directory.mkdir(mode=0o700)
        native = {"source_arrays_sha256": spec["source_arrays_sha256"],
                  "source_plan_sha256": spec["source_plan_sha256"], "items": [item],
                  "output": str(directory/"acquired-source-reference.FCStd"),
                  "report": str(directory/"native-document.json"), "staging": str(directory/"staging"),
                  "roundtrip_output": str(directory/"saved-feature-export")}
        native_job = directory/"job.json"; save(native_job, native)
        env = {"PORSCHE_COMPLETE_SOURCE_CAD_JOB": str(native_job)}
        for name, script, marker in (("create", spec["create_macro"], "COMPLETE_SOURCE_REFERENCE_DOCUMENT_OK"),
                                     ("export", spec["export_macro"], "COMPLETE_SOURCE_REFERENCE_SAVED_EXPORT_OK")):
            run(directory, name, ["/usr/bin/sandbox-exec", "-f", spec["network_policy"], spec["freecad"], script], env, marker)
        record = json.loads((directory/"native-document.json").read_text())
        assert sha(native["output"]) == record["output_sha256"]
        report = json.loads((directory/"saved-feature-export/report.json").read_text())
        exports = report["actual_saved_features_exported"]; assert len(exports) == 1 and exports[0]["chunk"] == index
        saved = exports[0]; packed = directory/"saved-feature-export"/saved["gzip"]
        assert sha(packed) == saved["gzip_sha256"]
        temporary = directory/"actual-saved-feature.step"; h = hashlib.sha256(); size = 0
        with gzip.open(packed, "rb") as incoming, temporary.open("xb") as outgoing:
            for data in iter(lambda: incoming.read(1024**2), b""):
                assert not stop.is_set() and shutil.disk_usage(output).free >= 4*1024**3
                outgoing.write(data); h.update(data); size += len(data)
        assert h.hexdigest() == saved["actual_saved_feature_raw_step_sha256"]
        assert size == saved["actual_saved_feature_raw_step_bytes"]
        verified = directory/"actual-saved-feature-independent.json"
        run(directory, "verify-saved", [spec["cad_python"], "-B", spec["verifier"], "--job", spec["chart_job"],
            "--chunk", str(index), "--step", str(temporary), "--output", str(verified)])
        proof = json.loads(verified.read_text()); assert proof["source_faces"] == item["counts"][2]
        assert sha(temporary) == saved["actual_saved_feature_raw_step_sha256"]
        assert sha(packed) == saved["gzip_sha256"] and sha(native["output"]) == record["output_sha256"]
        temporary.unlink()
        return {"chunk": index, "source_faces": proof["source_faces"],
                "native_document_sha256": record["output_sha256"], "native_document_bytes": record["output_bytes"],
                "actual_saved_feature_verification_sha256": sha(verified), "saved_feature_gzip_sha256": sha(packed),
                "verified_actual_saved_shape_against_original_source": True}
    try:
        remaining = iter(spec["items"])
        with concurrent.futures.ThreadPoolExecutor(max_workers=spec["workers"]) as pool:
            pending = {pool.submit(task, next(remaining)) for _ in range(spec["workers"])}
            try:
                while pending:
                    ready, _ = concurrent.futures.wait(pending, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
                    if time.monotonic()-started > spec["deadline_seconds"]:stop.set()
                    assert not stop.is_set(), "Native chart set deadline or stop request"
                    for future in ready:
                        pending.remove(future); completed.append(future.result())
                        print(json.dumps({"native_documents_independently_verified": len(completed), "requested": 83}), flush=True)
                        item = next(remaining, None)
                        if item is not None:pending.add(pool.submit(task, item))
            except BaseException:
                stop.set()
                for future in pending:future.cancel()
                raise
        assert len(completed) == 83 and sum(i["source_faces"] for i in completed) == 2465836
        assert sha(args.job) == job_sha
        for item in spec["inputs"]:assert sha(item["path"]) == item["sha256"]
        for item in spec["items"]:assert sha(item["gzip"]) == item["gzip_sha256"]
        complete = True
    finally:
        stop.set(); assert not children
        save(output/"terminal.json", {"source_sha256": sha(__file__), "job_sha256": job_sha, "complete": complete,
            "completed": sorted(completed, key=lambda x:x["chunk"]), "seconds": time.monotonic()-started,
            "all_owned_children_reaped": True, "original_inputs_rehashed_unchanged": complete,
            "independent_documents_not_sewn_full_head": True, "physical_acceptance": False, "manufacturing_authorized": False})
        save(output/"manifest.json", {"complete": complete, "files": [
            {"path": str(p.relative_to(output)), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted(output.rglob("*")) if p.is_file()]})


if __name__ == "__main__":main()
