"""Restore a geometry-owned region before invoking the retained Netgen recipe.

Gmsh 4.12.1 skips deMeshGRegion cleanup for fully discrete regions. Rebuilding
the exact imported arrays on a GEO region avoids retaining the input cell set.
This changes entity ownership only, not geometry or mesh connectivity.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import gmsh
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe",type=Path,required=True)
    args,forward=parser.parse_known_args();output=Path(forward[forward.index("--output")+1])
    spec=importlib.util.spec_from_file_location("retained_netgen_recipe",args.recipe)
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    original=gmsh.model.mesh.optimize
    def optimize(*positional,**keywords):
        expected=legacy.arrays();nodes,tets,boundary=expected
        types_before=[gmsh.model.getType(dim,tag) for dim,tag in gmsh.model.getEntities(3)]
        assert len(types_before)==1
        gmsh.clear();gmsh.model.add("exact_checkpoint_geometric_region")
        gmsh.model.addDiscreteEntity(2,1)
        outer=np.unique(boundary);inner=np.setdiff1d(np.arange(len(nodes)),outer)
        gmsh.model.mesh.addNodes(2,1,outer+1,nodes[outer].ravel())
        gmsh.model.mesh.addElementsByType(1,2,np.arange(1,len(boundary)+1),(boundary+1).ravel())
        loop=gmsh.model.geo.addSurfaceLoop([1]);volume=gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        if len(inner):gmsh.model.mesh.addNodes(3,volume,inner+1,nodes[inner].ravel())
        gmsh.model.mesh.addElementsByType(volume,4,np.arange(len(boundary)+1,len(boundary)+len(tets)+1),(tets+1).ravel())
        gmsh.model.addPhysicalGroup(2,[1],2,"fixed_boundary")
        gmsh.model.addPhysicalGroup(3,[volume],1,"diagnostic_solid")
        actual=legacy.arrays()
        for before,after in zip(expected,actual):assert np.array_equal(before,after),"Entity conversion changed checkpoint arrays"
        after_type=gmsh.model.getType(3,volume);assert "discrete" not in after_type.lower()
        for name,value in {"General.NumThreads":8,"Mesh.MeshSizeMax":2.,"Mesh.MeshSizeFromPoints":0,
                           "Mesh.MeshSizeFromCurvature":0,"Mesh.MeshSizeExtendFromBoundary":0}.items():
            gmsh.option.setNumber(name,value)
        field=gmsh.model.mesh.field.add("MathEval")
        gmsh.model.mesh.field.setString(field,"F","2.0");gmsh.model.mesh.field.setAsBackgroundMesh(field)
        record={"wrapper_sha256":legacy.sha(Path(__file__)),"recipe_sha256":legacy.sha(args.recipe),
                "region_types_before":types_before,"region_type_after":after_type,
                "all_checkpoint_arrays_identical_after_entity_conversion":True,
                "remeshing_performed_during_conversion":False,"boundary_motion_allowed":False,
                "full_independent_inspection_still_required":True}
        with (output/"entity-conversion.json").open("x") as stream:stream.write(json.dumps(record,indent=2)+"\n")
        del expected,actual,nodes,tets,boundary,outer,inner
        return original(*positional,**keywords)
    gmsh.model.mesh.optimize=optimize
    old=sys.argv;sys.argv=[str(args.recipe),*forward]
    try:legacy.main()
    finally:gmsh.model.mesh.optimize=original;sys.argv=old


if __name__=="__main__":main()
