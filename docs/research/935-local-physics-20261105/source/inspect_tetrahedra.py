"""Independently inspect all cells and their boundary; no physical acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def records(rows):
    return np.ascontiguousarray(rows, dtype="<u4").view(
        np.dtype([("a","<u4"),("b","<u4"),("c","<u4")])).reshape(-1)


def sign(rows):
    odd=(rows[:,0]>rows[:,1]) ^ (rows[:,0]>rows[:,2]) ^ (rows[:,1]>rows[:,2])
    return np.where(odd,-1,1).astype(np.int8)


def inspect(nodes, tets, declared_boundary, surface_vertices, surface_faces):
    if len(nodes) >= 2**32 or not len(tets):
        raise ValueError("Unsupported empty/oversized diagnostic")
    if not np.all(np.isfinite(nodes)) or tets.min()<0 or tets.max()>=len(nodes):
        raise ValueError("Nonfinite node or invalid cell index")
    if not np.array_equal(nodes[:len(surface_vertices)],surface_vertices):
        raise ValueError("Source nodes changed or reordered")
    source=records(np.sort(surface_faces,axis=1));source_order=np.argsort(source)
    source=source[source_order];source_sign=sign(surface_faces)[source_order]
    declared=records(np.sort(declared_boundary,axis=1))
    if not np.array_equal(np.sort(declared),source):
        raise ValueError("Declared Gmsh boundary differs from actual source triangles")
    patterns=np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]])
    all_faces=np.empty((4*len(tets),3),dtype="<u4")
    signs=np.empty(4*len(tets),dtype=np.int8)
    volumes=np.empty(len(tets));quality=np.empty(len(tets));used=np.zeros(len(nodes),bool)
    for start in range(0,len(tets),100000):
        cells=tets[start:start+100000];xyz=nodes[cells];used[cells]=True
        a,b,c=xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0],xyz[:,3]-xyz[:,0]
        volume=np.einsum("ij,ij->i",a,np.cross(b,c))/6
        if np.any(volume<=0):raise ValueError("Nonpositive tetrahedral cell")
        edges_squared=sum(np.sum((xyz[:,i]-xyz[:,j])**2,axis=1) for i,j in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)])
        volumes[start:start+len(cells)]=volume
        quality[start:start+len(cells)]=12*(3*volume)**(2/3)/edges_squared
        outward=cells[:,patterns].reshape(-1,3)
        first,last=4*start,4*(start+len(cells))
        signs[first:last]=sign(outward)
        all_faces[first:last]=np.sort(outward,axis=1)
    if not used.all():raise ValueError("Unused volume node")
    order=np.argsort(records(all_faces));ordered=all_faces[order]
    ordered_records=records(ordered)
    starts=np.r_[0,np.flatnonzero(ordered_records[1:]!=ordered_records[:-1])+1]
    counts=np.diff(np.r_[starts,len(ordered)])
    if np.any(counts>2):raise ValueError("Nonmanifold tetrahedral face")
    orientation=signs[order]
    internal=starts[counts==2]
    if np.any(orientation[internal]+orientation[internal+1]):
        raise ValueError("Interior cell faces do not have opposite orientations")
    external=starts[counts==1]
    if not np.array_equal(ordered_records[external],source):
        raise ValueError("Actual cell boundary differs from the source surface")
    if not np.array_equal(orientation[external],source_sign):
        raise ValueError("Actual cell boundary orientation differs from source")
    return {"nodes":len(nodes),"tetrahedra":len(tets),"boundary_faces":len(external),
            "internal_paired_faces":len(internal),"all_cells_positive":True,"all_nodes_used":True,
            "all_internal_faces_pair_with_opposite_orientation":True,
            "every_source_node_unchanged":True,"exact_source_triangle_boundary_and_orientation":True,
            "volume_mm3":float(volumes.sum()),"minimum_cell_volume_mm3":float(volumes.min()),
            "mean_ratio_quantiles":dict(zip(["minimum","p01","median","p99","maximum"],map(float,np.quantile(quality,[0,.01,.5,.99,1])))),
            "mean_ratio_below":{str(t):int((quality<t).sum()) for t in [.0001,.001,.01,.05,.1]},
            "tetrahedron_pair_intersections_exhaustively_checked":False,
            "physics_admitted":False,"manufacturing_qualified":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("mesh","source-mesh","source-report","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(mode=0o700,exist_ok=False)
    started=time.monotonic()
    source_report=json.loads(args.source_report.read_text())
    if sha(args.source_mesh)!=source_report["input_sha256"] or not source_report["geometry_export_gate_passed"]:
        raise ValueError("Source geometry receipt mismatch")
    # A positive tetrahedron, then distinct failures for inverted and missing cells.
    v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
    f=np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]])
    control=inspect(v,np.array([[0,1,2,3]]),f,v,f)
    assert abs(control["volume_mm3"]-1/6)<1e-15
    for cells,boundary in [(np.array([[0,2,1,3]]),f),(np.array([[0,1,2,3]]),f[:-1])]:
        try:inspect(v,cells,boundary,v,f)
        except ValueError:pass
        else:raise AssertionError("Deliberate invalid control was accepted")
    with np.load(args.source_mesh,allow_pickle=False) as data:
        surface_vertices,surface_faces=data["vertices"],data["triangles"]
    with np.load(args.mesh,allow_pickle=False) as data:
        nodes,tets,boundary=data["nodes"],data["tets"],data["boundary"]
    result=inspect(nodes,tets,boundary,surface_vertices,surface_faces)
    relative=abs(result["volume_mm3"]/source_report["signed_volume_mm3"]-1)
    if relative>1e-8:raise ValueError("Independent tetrahedral/surface volume mismatch")
    result.update(source_sha256=sha(Path(__file__)),mesh_sha256=sha(args.mesh),
                  source_mesh_sha256=sha(args.source_mesh),source_report_sha256=sha(args.source_report),
                  relative_volume_difference=relative,diagnostic_geometry_consistency_passed=True,
                  controls={"analytic_tetrahedron":True,"inverted_cell_refused":True,"missing_boundary_refused":True},
                  seconds=time.monotonic()-started)
    with (args.output/"report.json").open("x") as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
