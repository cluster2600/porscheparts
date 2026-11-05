"""Repeat the controlled path with explicit native node-label verification."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("root","input-msh","input-arrays","input-inspection","surface","surface-report",
                 "cube-arrays","cube-surface","cube-report","repository","python","scientific-site"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.root.mkdir(mode=0o700,exist_ok=False)
    recipe=Path(__file__).with_name("optimize_volume.py")
    controller=Path(__file__).with_name("run_optimization.py")
    wrapper=Path(__file__).with_name("optimize_numbered_volume.py")
    spec=importlib.util.spec_from_file_location("retained_bounded_execution",controller)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    sha,save,run=helper.sha,helper.save,helper.run
    assert sha(args.input_msh)=="dd06871fe45c765836d9690b5e6dd4bc00cc62cd9389b2ae16b5a4aa9831ba08"
    assert sha(args.input_arrays)=="b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.surface)=="5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    before=json.loads(args.input_inspection.read_text());geometry=json.loads(args.surface_report.read_text())
    assert before["all_cells_positive_for_stored_binary_coordinates"] and before["actual_complete_boundary_and_orientation_exact"]
    assert before["mesh_sha256"]==sha(args.input_arrays) and before["surface_sha256"]==sha(args.surface)==geometry["input_sha256"]
    assert geometry["geometry_export_gate_passed"]
    inspector=args.repository/"docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    frozen=args.repository/"docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    assert sha(inspector)=="b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    assert sha(args.cube_arrays)=="7f51242e375ecfd2f69e4c399724c697e873bea9fed43a15f3d36c86deb414e7"
    policy={"source_sha256":sha(Path(__file__)),"wrapper_sha256":sha(wrapper),"retained_recipe_sha256":sha(recipe),
            "retained_controller_sha256":sha(controller),"input_msh_sha256":sha(args.input_msh),"input_arrays_sha256":sha(args.input_arrays),
            "surface_sha256":sha(args.surface),"upstream_verdict":"Initial optimizer control rejected for face pairing; test node-label hypothesis without changing geometry or gates",
            "method":"Netgen","one_api_call":True,"head_kernel_alarm_seconds":900,"rss_limit_gib":40,
            "head_bin_reduction_min_fraction":.5,"diagnostic_bin":.01,"ultra_low_bin_must_not_increase":.0001,
            "minimum_quality_must_not_worsen":True,"parameter_sweep":False,"new_paid_compute_usd":0,"physics_admitted":False}
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
            save(args.root/"terminal.json",{"terminal":"independent_inspection_failed","stage":name,"raw_checkpoint_preserved":True,
                "physics_admitted":False,"new_paid_compute_usd":0});raise SystemExit(1)
        return json.loads((args.root/name/"report.json").read_text())
    control_before=inspect("control-before",args.root/"distorted-cube.npz",args.cube_surface,args.cube_report)
    base=[str(args.python),"-B",str(wrapper),"--recipe",str(recipe),"--interval-inspector",str(inspector)]
    command=base+["--input-arrays",str(args.root/"distorted-cube.npz"),"--surface",str(args.cube_surface),
        "--output",str(args.root/"control-optimized"),"--deadline-seconds","60"]
    done=run(args.root,"control-native",command,environment,60)
    if done["exit_code"]!=0:
        save(args.root/"terminal.json",{"terminal":"control_native_rejected_no_head_run","new_paid_compute_usd":0});raise SystemExit(1)
    after=inspect("control-after",args.root/"control-optimized/candidate.npz",args.cube_surface,args.cube_report)
    if after["mean_ratio_quantiles"]["minimum"]<max(.01,10*control_before["mean_ratio_quantiles"]["minimum"]):
        save(args.root/"terminal.json",{"terminal":"control_quality_rejected_no_head_run","new_paid_compute_usd":0});raise SystemExit(1)
    save(args.root/"control-admission.json",{"native_optimizer_executed":True,"full_boundary_and_cells_pass":True,
         "minimum_before":control_before["mean_ratio_quantiles"]["minimum"],"minimum_after":after["mean_ratio_quantiles"]["minimum"]})
    command=base+["--input-msh",str(args.input_msh),"--input-arrays",str(args.input_arrays),"--surface",str(args.surface),
        "--output",str(args.root/"head-optimized"),"--deadline-seconds","900"]
    result=run(args.root,"head-native",command,environment,900)
    if result["exit_code"]!=0:
        save(args.root/"terminal.json",{"terminal":"head_optimizer_failed_closed","execution":result,"raw_checkpoint_preserved":True,
            "new_paid_compute_usd":0,"physics_admitted":False});raise SystemExit(1)
    after=inspect("head-inspection",args.root/"head-optimized/candidate.npz",args.surface,args.surface_report)
    reduction=1-after["mean_ratio_below"]["0.01"]/before["mean_ratio_below"]["0.01"]
    checks={"bin_reduction":reduction>=.5,"ultra_low_count":after["mean_ratio_below"]["0.0001"]<=before["mean_ratio_below"]["0.0001"],
            "minimum_quality":after["mean_ratio_quantiles"]["minimum"]>=before["mean_ratio_quantiles"]["minimum"]}
    result={"terminal":"optimized_volume_checked","checks":checks,"diagnostic_target_passed":all(checks.values()),
            "before_below":before["mean_ratio_below"],"after_below":after["mean_ratio_below"],"below_0p01_reduction_fraction":reduction,
            "physics_admitted":False,"manufacturing_qualified":False,"new_paid_compute_usd":0}
    save(args.root/"terminal.json",result);print(json.dumps(result),flush=True)


if __name__=="__main__":main()
