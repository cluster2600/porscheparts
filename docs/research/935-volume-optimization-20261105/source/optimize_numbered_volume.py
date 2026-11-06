"""Reinspect native node tags and repair duplicate labels before array export.

The original failed recipe remains unchanged. Renumbering changes node labels
only; the exact coordinate multiset must match and the full independent cell
inspection remains mandatory. This wrapper cannot waive boundary admission.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import gmsh
import numpy as np


def coordinate_hash(xyz):
    rows=np.ascontiguousarray(xyz).reshape(-1,3)
    records=rows.view(np.dtype([(str(i),rows.dtype) for i in range(3)])).ravel()
    return hashlib.sha256(np.sort(records).tobytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe",type=Path,required=True)
    args,forward=parser.parse_known_args()
    output=Path(forward[forward.index("--output")+1])
    spec=importlib.util.spec_from_file_location("retained_netgen_recipe",args.recipe)
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    original=gmsh.model.mesh.optimize
    def optimize(*positional,**keywords):
        original(*positional,**keywords)
        tags,xyz,_=gmsh.model.mesh.getNodes()
        duplicates=len(tags)-len(np.unique(tags))
        before=coordinate_hash(xyz)
        if duplicates:gmsh.model.mesh.renumberNodes()
        new_tags,new_xyz,_=gmsh.model.mesh.getNodes()
        assert len(new_tags)==len(np.unique(new_tags)),"Native node labels still ambiguous"
        assert coordinate_hash(new_xyz)==before,"Renumbering changed geometry"
        record={"wrapper_sha256":legacy.sha(Path(__file__)),"recipe_sha256":legacy.sha(args.recipe),
                "native_nodes":len(tags),"duplicate_node_tags_before":duplicates,
                "duplicate_node_tags_after":0,"renumbering_applied":bool(duplicates),
                "coordinate_multiset_sha256":before,"coordinates_preserved_exactly":True,
                "full_independent_cell_checks_still_required":True}
        with (output/"numbering-receipt.json").open("x") as stream:stream.write(json.dumps(record,indent=2)+"\n")
    gmsh.model.mesh.optimize=optimize
    old=sys.argv;sys.argv=[str(args.recipe),*forward]
    try:legacy.main()
    finally:gmsh.model.mesh.optimize=original;sys.argv=old


if __name__=="__main__":main()
