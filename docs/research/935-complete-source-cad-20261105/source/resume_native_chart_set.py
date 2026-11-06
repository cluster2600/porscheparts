"""Resume native references after the shared Python executable disappeared.

Preserve the failed first attempt, reuse its 35 complete document/export bytes,
construct only the other 48 documents, and independently inspect all 83 actual
saved shapes on a separately frozen private Python runtime. No geometric guard
or source coordinate is changed. No paid resource is created.
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
        for data in iter(lambda:stream.read(1024**2), b""):h.update(data)
    return h.hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:json.dump(value, stream, indent=2); stream.write("\n")


def verify_manifest(directory, complete):
    record = json.loads((directory/"manifest.json").read_text()); assert record["complete"] is complete
    expected = {item["path"]:item for item in record["files"]}; assert len(expected) == len(record["files"])
    actual = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    assert actual == set(expected)|{"manifest.json"}
    for name, item in expected.items():
        path = directory/name
        assert path.resolve().is_relative_to(directory.resolve()) and not path.is_symlink()
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]


def verify_runtime(root, digest):
    assert sha(root/"manifest.json") == digest
    record = json.loads((root/"manifest.json").read_text())
    for item in record["files"]:
        path = root/item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    for item in record["links"]:
        path = root/item["path"]
        assert path.is_symlink() and os.readlink(path) == item["target"] and path.resolve().is_relative_to(root.resolve())


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args(); spec = json.loads(args.job.read_text()); job_sha = sha(args.job)
    assert spec["schema"] == "935-native-source-chart-set-resume-1"
    assert (spec["workers"], spec["deadline_seconds"], spec["child_seconds"], spec["child_rss_gib"]) == (4, 7200, 600, 4)
    assert [i["chunk"] for i in spec["items"]] == list(range(83))
    assert sum(i["counts"][2] for i in spec["items"]) == 2465836
    prior = Path(spec["prior_root"]); prior_terminal = json.loads((prior/"terminal.json").read_text())
    assert not prior_terminal["complete"] and prior_terminal["all_owned_children_reaped"]
    assert [i["chunk"] for i in prior_terminal["completed"]] == list(range(35))
    assert "FileNotFoundError" in Path(spec["prior_log"]).read_text()
    assert sha(prior/"manifest.json") == spec["prior_manifest_sha256"]
    verify_manifest(prior, False); runtime = Path(spec["runtime_root"])
    verify_runtime(runtime, spec["runtime_manifest_sha256"])
    assert Path(spec["cad_python"]).resolve().is_relative_to(runtime.resolve())
    for item in spec["inputs"]:assert sha(item["path"]) == item["sha256"]
    for item in spec["items"]:assert sha(item["gzip"]) == item["gzip_sha256"]
    output = Path(spec["output"]); output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic(); stop = threading.Event(); lock = threading.Lock(); children = {}; completed = []; complete = False
    def interrupt(signum, frame):stop.set()
    signal.signal(signal.SIGTERM, interrupt); signal.signal(signal.SIGINT, interrupt)
    environment = os.environ.copy(); environment.update(PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    def run(directory, name, command, extra_environment=None, marker=None):
        assert not stop.is_set(); peak = 0; limited = False; before = time.monotonic()
        env = environment.copy(); env.update(extra_environment or {})
        with (directory/(name+".log")).open("x") as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            with lock:children[child.pid] = command
            save(directory/(name+"-running.json"), {"pid":child.pid,"argv":command,"epoch":time.time()})
            try:
                while child.poll() is None:
                    time.sleep(.5)
                    sample = subprocess.run(["ps","-o","rss=","-p",str(child.pid)],capture_output=True,text=True)
                    if sample.stdout.strip():peak = max(peak,int(sample.stdout.strip()))
                    if (stop.is_set() or time.monotonic()-started > 7200 or time.monotonic()-before > 600
                            or peak > 4*1024**2 or shutil.disk_usage(output).free < 4*1024**3):
                        limited = True;os.killpg(child.pid,signal.SIGTERM);break
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            finally:
                if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
                with lock:children.pop(child.pid)
        result = {"exit_code":child.returncode,"controller_limit_reached":limited,"seconds":time.monotonic()-before,
                  "sampled_peak_rss_kib":peak,"log_sha256":sha(directory/(name+".log")),"exact_owned_child_reaped":True}
        save(directory/(name+"-execution.json"),result);assert child.returncode == 0 and not limited
        if marker is not None:assert marker in (directory/(name+".log")).read_text()
    def task(item):
        index = item["chunk"];directory = output/("chunk-"+str(index).zfill(4));directory.mkdir(mode=0o700)
        reused = index < 35
        if reused:
            original = prior/directory.name
            proof = json.loads((original/"actual-saved-feature-independent.json").read_text())
            assert proof["chunk"] == index and proof["source_faces"] == item["counts"][2]
            assert all(proof["native_source_comparison"]["checks"].values())
            assert proof["native_source_comparison"]["vertex_roundtrip_maximum_mm"] == 0
            assert proof["native_support_plane_residual_maximum_nominal_mm"] <= 1e-8
            renamed = {"actual-saved-feature-independent.json":"prior-runtime-source-comparison.json",
                       **{("verify-saved"+suffix):("prior-verify-saved"+suffix) for suffix in (".log","-running.json","-execution.json")}}
            copied = []
            for source in sorted(original.rglob("*")):
                assert not source.is_symlink()
                if source.is_dir():continue
                relative = source.relative_to(original);name = renamed.get(str(relative),str(relative));target = directory/name
                target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(source,target)
                assert sha(target) == sha(source);copied.append({"from":str(relative),"to":name,"sha256":sha(target)})
            save(directory/"reused-document-provenance.json", {"prior_manifest_sha256":spec["prior_manifest_sha256"],
                 "copied_bytes_unchanged":True,"no_native_document_reconstruction_or_export_replay":True,"files":copied})
        else:
            native_job = {"source_arrays_sha256":spec["source_arrays_sha256"],"source_plan_sha256":spec["source_plan_sha256"],
                          "items":[item],"output":str(directory/"acquired-source-reference.FCStd"),
                          "report":str(directory/"native-document.json"),"staging":str(directory/"staging"),
                          "roundtrip_output":str(directory/"saved-feature-export")}
            job_path = directory/"job.json";save(job_path,native_job);env = {"PORSCHE_COMPLETE_SOURCE_CAD_JOB":str(job_path)}
            for name,script,marker in (("create",spec["create_macro"],"COMPLETE_SOURCE_REFERENCE_DOCUMENT_OK"),
                                       ("export",spec["export_macro"],"COMPLETE_SOURCE_REFERENCE_SAVED_EXPORT_OK")):
                run(directory,name,["/usr/bin/sandbox-exec","-f",spec["network_policy"],spec["freecad"],script],env,marker)
        document = directory/"acquired-source-reference.FCStd";record = json.loads((directory/"native-document.json").read_text())
        assert sha(document) == record["output_sha256"]
        report = json.loads((directory/"saved-feature-export/report.json").read_text())
        exported = report["actual_saved_features_exported"];assert len(exported) == 1 and exported[0]["chunk"] == index
        saved = exported[0];packed = directory/"saved-feature-export"/saved["gzip"]
        assert sha(packed) == saved["gzip_sha256"]
        temporary = directory/"actual-saved-feature.step";h = hashlib.sha256();size = 0
        with gzip.open(packed,"rb") as incoming,temporary.open("xb") as outgoing:
            for data in iter(lambda:incoming.read(1024**2),b""):
                assert not stop.is_set() and shutil.disk_usage(output).free >= 4*1024**3
                outgoing.write(data);h.update(data);size += len(data)
        assert h.hexdigest() == saved["actual_saved_feature_raw_step_sha256"] and size == saved["actual_saved_feature_raw_step_bytes"]
        verified = directory/"actual-saved-feature-independent.json"
        run(directory,"verify-saved",[spec["cad_python"],"-B",spec["verifier"],"--job",spec["chart_job"],
            "--chunk",str(index),"--step",str(temporary),"--output",str(verified)])
        proof = json.loads(verified.read_text());assert proof["source_faces"] == item["counts"][2]
        assert sha(temporary) == saved["actual_saved_feature_raw_step_sha256"] and sha(packed) == saved["gzip_sha256"]
        assert sha(document) == record["output_sha256"];temporary.unlink()
        return {"chunk":index,"source_faces":proof["source_faces"],"native_document_sha256":record["output_sha256"],
                "native_document_bytes":record["output_bytes"],"actual_saved_feature_verification_sha256":sha(verified),
                "reused_prior_document_bytes":reused,"new_runtime_original_source_inspection":True}
    try:
        remaining = iter(spec["items"])
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            pending = {pool.submit(task,next(remaining)) for _ in range(4)}
            try:
                while pending:
                    ready,_ = concurrent.futures.wait(pending,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
                    if time.monotonic()-started > 7200:stop.set()
                    assert not stop.is_set()
                    for future in ready:
                        pending.remove(future);completed.append(future.result())
                        print(json.dumps({"native_documents_independently_verified":len(completed),"requested":83}),flush=True)
                        item = next(remaining,None)
                        if item is not None:pending.add(pool.submit(task,item))
            except BaseException:
                stop.set()
                for future in pending:future.cancel()
                raise
        assert len(completed) == 83 and sum(i["source_faces"] for i in completed) == 2465836
        assert sum(i["reused_prior_document_bytes"] for i in completed) == 35
        for item in spec["inputs"]:assert sha(item["path"]) == item["sha256"]
        for item in spec["items"]:assert sha(item["gzip"]) == item["gzip_sha256"]
        assert sha(args.job) == job_sha and sha(prior/"manifest.json") == spec["prior_manifest_sha256"]
        verify_runtime(runtime,spec["runtime_manifest_sha256"]);complete = True
    finally:
        stop.set();assert not children
        save(output/"terminal.json",{"source_sha256":sha(__file__),"job_sha256":job_sha,"complete":complete,
            "completed":sorted(completed,key=lambda i:i["chunk"]),"seconds":time.monotonic()-started,
            "all_owned_children_reaped":True,"original_inputs_rehashed_unchanged":complete,
            "prior_attempt_preserved":True,"reused_native_document_count":sum(i["reused_prior_document_bytes"] for i in completed),
            "shared_runtime_unchanged_not_claimed":True,"isolated_runtime_rehashed_unchanged":complete,
            "independent_documents_not_sewn_full_head":True,"physical_acceptance":False,"manufacturing_authorized":False})
        save(output/"manifest.json",{"complete":complete,"files":[{"path":str(p.relative_to(output)),"bytes":p.stat().st_size,
             "sha256":sha(p)} for p in sorted(output.rglob("*")) if p.is_file()]})


if __name__ == "__main__":main()
