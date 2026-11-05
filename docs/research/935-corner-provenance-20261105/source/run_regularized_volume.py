"""Bound a comparable local raw-volume diagnostic after independent admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def save(path,value):
    with path.open("x") as stream:stream.write(json.dumps(value,indent=2)+"\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("surface","geometry-report","preservation","repository","python","scientific-site","cube-fixture","cube-report","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False)
    geometry=json.loads(args.geometry_report.read_text());proof=json.loads(args.preservation.read_text())
    h=sha(args.surface);assert h==geometry["input_sha256"]==proof["candidate_sha256"]
    assert geometry["geometry_export_gate_passed"] and geometry["intersection_pairs"]==0
    assert proof["preservation_checks_passed"] and proof["quality_gate_passed"] and proof["bad_face_count_not_increased"]
    assert proof["composed_complete_surface_correspondence_bound_mm"]<=.01
    assert sha(args.cube_fixture)=="931a470cb7cdb3f068969d44dc5ba5d818c124aa5ad323604eb017816c003955"
    assert sha(args.cube_report)=="591a4497574cfed937b4d6092a3ef45280638f62ce2f24b0c970328234825abd"
    wrapper=args.repository/"docs/research/935-unoptimized-volume-20261105/source/mesh_without_optimization.py"
    inspector=args.repository/"docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    recipe=args.repository/"docs/research/935-hypothesis-study-20261029/source/mesh_solid.py"
    assert sha(wrapper)=="9c146ca54cb8fd5e2e615e7baa98d77536e4eeefbde026c64e7f824b24ec41b3"
    policy={"source_sha256":sha(Path(__file__)),"surface_sha256":h,"geometry_report_sha256":sha(args.geometry_report),
            "preservation_sha256":sha(args.preservation),"wrapper_sha256":sha(wrapper),"recipe_sha256":sha(recipe),
            "inspector_sha256":sha(inspector),"upstream_verdict":"Regularization preservation and native geometry pass; diagnostic volume only; sixty forcing faces remain",
            "algorithm":10,"threads":8,"interior_size_mm":2.,"optimization":False,"head_timeout_seconds":900,
            "sampled_rss_limit_gib":40,"new_paid_compute_usd":0,"physics_admitted":False,"manufacturing_qualified":False}
    save(args.output/"plan.json",policy)
    env=os.environ.copy();env["PYTHONPATH"]=str(args.scientific_site)
    base=[str(args.python),"-B",str(wrapper),"--recipe",str(recipe)]
    with (args.output/"cube.log").open("x") as log:
        control=subprocess.run(base+["--input","cube","--output",str(args.output/"cube"),"--threads","2"],
            env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    assert control.returncode==0
    with (args.output/"cube-inspection.log").open("x") as log:
        control=subprocess.run([str(args.python),"-B",str(inspector),"--mesh",str(args.output/"cube/solid.npz"),
            "--source-mesh",str(args.cube_fixture),"--source-report",str(args.cube_report),"--output",str(args.output/"cube-inspection")],
            env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    assert control.returncode==0 and shutil.disk_usage(args.output).free>10*1024**3
    command=base+["--input",str(args.surface),"--output",str(args.output/"head"),"--threads","8"]
    started=time.monotonic();peak=0;terminal="running"
    with (args.output/"head.log").open("x") as log:
        child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(args.output/"running.json",{"pid":child.pid,"argv":command,"started_epoch":time.time()})
        try:
            while child.poll() is None:
                time.sleep(2)
                sample=subprocess.run(["ps","-o","rss=","-p",str(child.pid)],capture_output=True,text=True)
                if sample.stdout.strip():peak=max(peak,int(sample.stdout.strip()))
                if time.monotonic()-started>900 or peak>40*1024**2 or shutil.disk_usage(args.output).free<4*1024**3:
                    terminal="bounded_limit_reached";os.killpg(child.pid,signal.SIGTERM);break
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        finally:
            if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
    if terminal=="running":terminal="native_export_complete" if child.returncode==0 else "native_failure"
    result={"terminal":terminal,"exit_code":child.returncode,"seconds":time.monotonic()-started,
            "sampled_peak_rss_kib":peak,"mesh_exported":(args.output/"head/solid.npz").exists(),
            "head_log_sha256":sha(args.output/"head.log"),"independent_inspection_pending":True,
            "physics_admitted":False,"manufacturing_qualified":False,"new_paid_compute_usd":0}
    save(args.output/"execution.json",result);print(json.dumps(result),flush=True)
    if terminal!="native_export_complete":raise SystemExit(1)


if __name__=="__main__":main()
