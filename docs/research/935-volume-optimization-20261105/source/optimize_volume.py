"""Apply one native Netgen optimization call to a preserved raw checkpoint.

The boundary must remain exactly identical. Orientation canonicalization and
unused internal-node pruning are representation operations, separately logged
and subsequently checked by the complete independent volume inspector.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import gmsh
import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def arrays():
    tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags)
    sorted_tags=tags[order];nodes=xyz.reshape(-1,3)[order]
    _,cells=gmsh.model.mesh.getElementsByType(4)
    _,faces=gmsh.model.mesh.getElementsByType(2)
    tets=np.searchsorted(sorted_tags,cells).reshape(-1,4)
    boundary=np.searchsorted(sorted_tags,faces).reshape(-1,3)
    return nodes,tets,boundary


def build_fixture(nodes,tets,boundary,path):
    gmsh.model.add("optimizer_control")
    gmsh.model.addDiscreteEntity(2,1)
    gmsh.model.addDiscreteEntity(3,1,[1])
    outer=np.unique(boundary);inner=np.setdiff1d(np.arange(len(nodes)),outer)
    gmsh.model.mesh.addNodes(2,1,outer+1,nodes[outer].ravel())
    if len(inner):gmsh.model.mesh.addNodes(3,1,inner+1,nodes[inner].ravel())
    gmsh.model.mesh.addElementsByType(1,2,np.arange(1,len(boundary)+1),(boundary+1).ravel())
    gmsh.model.mesh.addElementsByType(1,4,np.arange(len(boundary)+1,len(boundary)+len(tets)+1),(tets+1).ravel())
    gmsh.model.addPhysicalGroup(2,[1],2,"fixed_boundary")
    gmsh.model.addPhysicalGroup(3,[1],1,"diagnostic_solid")
    gmsh.write(str(path));gmsh.clear()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-msh",type=Path)
    for name in ("input-arrays","surface","interval-inspector","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--deadline-seconds",type=int,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert 1<=args.deadline_seconds<=900
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(args.deadline_seconds)
    assert gmsh.__version__=="4.12.1"
    assert sha(args.interval_inspector)=="b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    spec=importlib.util.spec_from_file_location("frozen_exact_orientation",args.interval_inspector)
    orient=importlib.util.module_from_spec(spec);spec.loader.exec_module(orient)
    with np.load(args.input_arrays,allow_pickle=False) as d:expected=[d[k] for k in ("nodes","tets","boundary")]
    with np.load(args.surface,allow_pickle=False) as d:surface_vertices=d["vertices"]
    gmsh.initialize();gmsh.option.setNumber("General.NumThreads",8);gmsh.option.setNumber("Mesh.Binary",1)
    assert "Netgen" in gmsh.option.getString("General.BuildOptions")
    msh=args.input_msh
    if msh is None:
        msh=args.output/"fixture-input.msh";build_fixture(*expected,msh)
    gmsh.open(str(msh))
    imported=arrays()
    for label,before,after in zip(("nodes","tets","boundary"),expected,imported):
        assert np.array_equal(before,after),"Checkpoint MSH/NPZ mismatch: "+label
    assert np.array_equal(imported[0][:len(surface_vertices)],surface_vertices)
    del expected,imported
    options={"General.NumThreads":8,"Mesh.MeshSizeMax":2.,"Mesh.MeshSizeFromPoints":0,
             "Mesh.MeshSizeFromCurvature":0,"Mesh.MeshSizeExtendFromBoundary":0}
    for name,value in options.items():gmsh.option.setNumber(name,value)
    field=gmsh.model.mesh.field.add("MathEval")
    gmsh.model.mesh.field.setString(field,"F","2.0");gmsh.model.mesh.field.setAsBackgroundMesh(field)
    plan={"source_sha256":sha(Path(__file__)),"input_msh_sha256":sha(msh),"input_arrays_sha256":sha(args.input_arrays),
          "surface_sha256":sha(args.surface),"gmsh_version":gmsh.__version__,"checkpoint_arrays_match_exactly":True,
          "method":"Netgen","force_discrete_entities":True,"api_niter_argument":1,
          "native_iteration_count_not_claimed":True,"one_api_call":True,"options":options,
          "kernel_alarm_seconds":args.deadline_seconds,"physics_admitted":False}
    (args.output/"before-optimization.json").write_text(json.dumps(plan,indent=2)+"\n")
    gmsh.model.mesh.optimize("Netgen",force=True,niter=1)
    nodes,tets,boundary=arrays();raw_count=len(nodes)
    used=np.unique(np.r_[tets.ravel(),boundary.ravel()]);nodes=nodes[used]
    tets=np.searchsorted(used,tets);boundary=np.searchsorted(used,boundary)
    assert np.array_equal(nodes[:len(surface_vertices)],surface_vertices),"Boundary node coordinates/order changed"
    # Canonicalize connectivity using proven signs, never a rounded determinant.
    swapped=ambiguous=0
    for start in range(0,len(tets),50000):
        cells=tets[start:start+50000];xyz=nodes[cells]
        low,high=orient.determinant_interval(xyz)
        negative=high<0
        uncertain=np.flatnonzero((low<=0)&(high>=0));ambiguous+=len(uncertain)
        for i in uncertain:
            exact=orient.exact_determinant(xyz[i]);assert exact!=0,"Zero-volume optimizer cell"
            negative[i]=exact<0
        if negative.any():
            replacement=cells[negative].copy();replacement[:,[1,2]]=replacement[:,[2,1]]
            cells[negative]=replacement;swapped+=int(negative.sum())
    # Only canonical arrays are candidates for downstream inspection.
    np.savez_compressed(args.output/"candidate.npz",nodes=nodes,tets=tets,boundary=boundary)
    result={"source_sha256":sha(Path(__file__)),"candidate_sha256":sha(args.output/"candidate.npz"),
            "nodes":len(nodes),"tetrahedra":len(tets),"boundary_faces":len(boundary),
            "unused_internal_nodes_pruned":raw_count-len(nodes),"negative_connectivities_reordered":swapped,
            "exact_orientation_fallbacks":ambiguous,"boundary_vertices_exact":True,
            "independent_complete_inspection_pending":True,"physics_admitted":False,
            "manufacturing_qualified":False,"seconds":time.monotonic()-started}
    (args.output/"worker-report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True);gmsh.finalize();signal.alarm(0)


if __name__=="__main__":main()
