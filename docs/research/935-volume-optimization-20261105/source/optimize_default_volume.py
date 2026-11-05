"""Test Gmsh's own optimizer after the geometry-owned import conversion.

Retain native arrays before representation checks so a rejected cell remains
diagnosable. Independent complete inspection and all prior gates still apply.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import gmsh
import numpy as np


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe",type=Path,required=True)
    args,forward=parser.parse_known_args();output=Path(forward[forward.index("--output")+1])
    geometric=module(Path(__file__).with_name("optimize_geometric_volume.py"),"retained_region_adapter")
    io=module(args.recipe,"retained_checkpoint_io")
    native=gmsh.model.mesh.optimize
    def optimize(method="",force=False,niter=1,dimTags=[]):
        native("",force=force,niter=niter,dimTags=dimTags)
        nodes,tets,boundary=io.arrays()
        np.savez_compressed(output/"raw-native.npz",nodes=nodes,tets=tets,boundary=boundary)
        record={"wrapper_sha256":io.sha(Path(__file__)),"geometric_adapter_sha256":io.sha(Path(geometric.__file__)),
                "requested_by_retained_recipe":method,"actual_method":"Gmsh default",
                "one_native_api_call":True,"niter_argument":niter,"raw_native_sha256":io.sha(output/"raw-native.npz"),
                "raw_nodes":len(nodes),"raw_cells":len(tets),"raw_arrays_not_admitted_for_physics":True}
        with (output/"default-method-receipt.json").open("x") as stream:stream.write(json.dumps(record,indent=2)+"\n")
    gmsh.model.mesh.optimize=optimize
    old=sys.argv;sys.argv=[str(geometric.__file__),"--recipe",str(args.recipe),*forward]
    try:geometric.main()
    finally:gmsh.model.mesh.optimize=native;sys.argv=old


if __name__=="__main__":main()
