"""Gate one bounded head optimization on an actual distorted-cube control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def save(path,value):
    with path.open("x") as stream:stream.write(json.dumps(value,indent=2)+"\n")


def run(root,name,command,environment,seconds):
    started=time.monotonic();peak=0;limited=False
    with (root/(name+".log")).open("x") as log:
        child=subprocess.Popen(command,env=environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(root/(name+"-running.json"),{"pid":child.pid,"argv":command,"started_epoch":time.time()})
        try:
            while child.poll() is None:
                time.sleep(1)
                usage=subprocess.run(["ps","-o","rss=","-p",str(child.pid)],capture_output=True,text=True)
                if usage.stdout.strip():peak=max(peak,int(usage.stdout.strip()))
                if time.monotonic()-started>seconds+15 or peak>40*1024**2 or shutil.disk_usage(root).free<4*1024**3:
                    limited=True;os.killpg(child.pid,signal.SIGTERM);break
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        finally:
            if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
    result={"exit_code":child.returncode,"controller_limit_reached":limited,"seconds":time.monotonic()-started,
            "sampled_peak_rss_kib":peak,"log_sha256":sha(root/(name+".log"))}
    save(root/(name+"-execution.json"),result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("root","input-msh","input-arrays","input-inspection","surface","surface-report",
                 "cube-arrays","cube-surface","cube-report","repository","python","scientific-site"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.root.mkdir(mode=0o700,exist_ok=False)
    assert sha(args.input_msh)=="dd06871fe45c765836d9690b5e6dd4bc00cc62cd9389b2ae16b5a4aa9831ba08"
    assert sha(args.input_arrays)=="b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.surface)=="5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    before=json.loads(args.input_inspection.read_text());geometry=json.loads(args.surface_report.read_text())
    assert before["mesh_sha256"]==sha(args.input_arrays) and before["all_cells_positive_for_stored_binary_coordinates"]
    assert before["actual_complete_boundary_and_orientation_exact"] and geometry["geometry_export_gate_passed"]
    assert before["surface_sha256"]==geometry["input_sha256"]==sha(args.surface)
    inspector=args.repository/"docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    frozen=args.repository/"docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    worker=Path(__file__).with_name("optimize_volume.py")
    assert sha(inspector)=="b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    assert sha(args.cube_arrays)=="7f51242e375ecfd2f69e4c399724c697e873bea9fed43a15f3d36c86deb414e7"
    policy={"source_sha256":sha(Path(__file__)),"worker_sha256":sha(worker),"input_arrays_sha256":sha(args.input_arrays),
            "input_msh_sha256":sha(args.input_msh),"input_inspection_sha256":sha(args.input_inspection),
            "surface_sha256":sha(args.surface),"surface_report_sha256":sha(args.surface_report),
            "upstream_verdict":"Consistent hypothetical raw volume; quality rejected. Boundary remains fixed; sixty forcing boundary faces preclude universal shape floor.",
            "method":"Netgen","one_api_call":True,"force_discrete_entities":True,"parameter_sweep":False,
            "head_worker_kernel_alarm_seconds":900,"sampled_rss_limit_gib":40,
            "head_bin_reduction_min_fraction":.5,"diagnostic_bin":.01,
            "ultra_low_bin_must_not_increase":.0001,"minimum_quality_must_not_worsen":True,
            "physics_admitted":False,"manufacturing_qualified":False,"new_paid_compute_usd":0}
    save(args.root/"plan.json",policy)
    with np.load(args.cube_arrays,allow_pickle=False) as d:fixture={k:d[k] for k in d.files}
    assert len(fixture["nodes"])==9 and np.all((fixture["tets"]==8).any(axis=1))
    fixture["nodes"][8]=[1e-6,1e-6,1e-6]
    np.savez_compressed(args.root/"distorted-cube.npz",**fixture)
    environment=os.environ.copy();environment["PYTHONPATH"]=str(args.scientific_site)
    def inspect(name,mesh,surface,report):
        command=[str(args.python),"-B",str(inspector),"--mesh",str(mesh),"--surface",str(surface),
            "--surface-report",str(report),"--frozen-inspector",str(frozen),"--output",str(args.root/name)]
        result=run(args.root,name,command,environment,600)
        if result["exit_code"]!=0:
            save(args.root/"terminal.json",{"terminal":"independent_inspection_failed","stage":name,
                 "raw_checkpoint_preserved":True,"physics_admitted":False,"new_paid_compute_usd":0})
            raise RuntimeError(name+" inspection failed")
        return json.loads((args.root/name/"report.json").read_text())
    control_before=inspect("control-before",args.root/"distorted-cube.npz",args.cube_surface,args.cube_report)
    command=[str(args.python),"-B",str(worker),"--input-arrays",str(args.root/"distorted-cube.npz"),
        "--surface",str(args.cube_surface),"--interval-inspector",str(inspector),"--output",str(args.root/"control-optimized"),"--deadline-seconds","60"]
    execution=run(args.root,"control-native",command,environment,60)
    if execution["exit_code"]!=0:
        save(args.root/"terminal.json",{"terminal":"control_native_rejected_no_head_run","new_paid_compute_usd":0})
        raise SystemExit(1)
    control_after=inspect("control-after",args.root/"control-optimized/candidate.npz",args.cube_surface,args.cube_report)
    if control_after["mean_ratio_quantiles"]["minimum"]<max(.01,10*control_before["mean_ratio_quantiles"]["minimum"]):
        save(args.root/"terminal.json",{"terminal":"control_quality_rejected_no_head_run",
             "physics_admitted":False,"new_paid_compute_usd":0})
        raise SystemExit(1)
    save(args.root/"control-admission.json",{"native_optimizer_executed":True,"boundary_and_full_cells_pass":True,
         "minimum_mean_ratio_before":control_before["mean_ratio_quantiles"]["minimum"],
         "minimum_mean_ratio_after":control_after["mean_ratio_quantiles"]["minimum"],"head_authorized_by_control":True})
    assert shutil.disk_usage(args.root).free>10*1024**3
    command=[str(args.python),"-B",str(worker),"--input-msh",str(args.input_msh),"--input-arrays",str(args.input_arrays),
        "--surface",str(args.surface),"--interval-inspector",str(inspector),"--output",str(args.root/"head-optimized"),"--deadline-seconds","900"]
    result=run(args.root,"head-native",command,environment,900)
    if result["exit_code"]!=0:
        save(args.root/"terminal.json",{"terminal":"head_optimizer_failed_closed","execution":result,"raw_checkpoint_preserved":True,
             "physics_admitted":False,"new_paid_compute_usd":0});raise SystemExit(1)
    after=inspect("head-inspection",args.root/"head-optimized/candidate.npz",args.surface,args.surface_report)
    reduction=1-after["mean_ratio_below"]["0.01"]/before["mean_ratio_below"]["0.01"]
    checks={"bin_reduction":reduction>=.5,"ultra_low_count":after["mean_ratio_below"]["0.0001"]<=before["mean_ratio_below"]["0.0001"],
            "minimum_quality":after["mean_ratio_quantiles"]["minimum"]>=before["mean_ratio_quantiles"]["minimum"]}
    save(args.root/"terminal.json",{"terminal":"optimized_volume_checked","checks":checks,"diagnostic_target_passed":all(checks.values()),
         "before_below":before["mean_ratio_below"],"after_below":after["mean_ratio_below"],"below_0p01_reduction_fraction":reduction,
         "physics_admitted":False,"manufacturing_qualified":False,"new_paid_compute_usd":0})
    print(json.dumps(json.loads((args.root/"terminal.json").read_text())),flush=True)


if __name__=="__main__":main()
