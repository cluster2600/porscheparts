from pathlib import Path
import array, hashlib, json, re, time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

case=Path("work/bionic-f1-20261011/cfd-baseline-medium-gap-002")
out=case/"independent-boundary-diagnostic.json"
assert not out.exists(), "Refusing overwrite"
receipt=json.loads((case/"run-mesh.json").read_text())
assert any(s.get("name")=="snappyHexMesh" and s.get("exit_code")==0 for s in receipt.get("stages",[])), "No completed native snappy stage"
assert re.search(r"(?m)^End\s*$",(case/"log.snappyHexMesh").read_text()), "No native End marker"
manifest=json.loads((case/"case-manifest.json").read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
    return h.hexdigest()
names=["run-mesh.json","case-manifest.json","constant/triSurface/domain.stl",
       "constant/polyMesh/points","constant/polyMesh/faces","constant/polyMesh/boundary",
       "constant/polyMesh/cellLevel","constant/polyMesh/owner","log.snappyHexMesh"]
if (case/"log.checkMesh").exists():names.append("log.checkMesh")
hashes={n:sha(case/n) for n in names}
assert hashes["constant/triSurface/domain.stl"]==manifest["surface"]["sha256"]
assert hashes["case-manifest.json"]==receipt["case_manifest_sha256"]
patch_names=["inlet","outlet","rotor","stator"]
def clean(s):
    return re.sub(r"/\*.*?\*/|//[^\n]*","",s,flags=re.S)
def foam_payload(path):
    text=clean(path.read_text())
    m=re.fullmatch(r"\s*FoamFile\s*\{([^{}]*)\}\s*(\d+)\s*([\s\S]*)",text)
    if not m or not re.search(r"\bformat\s+ascii\s*;",m[1]):raise ValueError("Bad ASCII list "+str(path))
    n=int(m[2]); body=m[3].strip()
    if body.startswith("(") and body.endswith(")"):return n,body[1:-1],False
    if re.fullmatch(r"\{\s*\d+\s*\}",body):return n,body[1:-1],True
    raise ValueError("Bad list body "+str(path))
def numeric_list(path,dimension=1):
    n,body,uniform=foam_payload(path)
    if uniform:
        if dimension!=1:raise ValueError("Unexpected uniform")
        a=np.full(n,int(body),dtype=np.int64)
    else:
        a=np.fromstring(body.translate(str.maketrans({"(":" ",")":" "})),sep=" ")
        if len(a)!=n*dimension or not np.all(np.isfinite(a)):raise ValueError("Bad numeric count")
        if dimension==1 and np.any(a!=np.floor(a)):raise ValueError("Nonintegral labels")
        a=a.reshape(n,dimension) if dimension>1 else a.astype(np.int64)
    return a
def loop_diagnostics(points,edges):
    if not len(edges):return []
    uv,inv=np.unique(edges,return_inverse=True)
    mapped=inv.reshape(-1,2)
    graph=coo_matrix((np.ones(len(edges),dtype=np.int8),(mapped[:,0],mapped[:,1])),shape=(len(uv),len(uv))).tocsr()
    count,label=connected_components(graph,directed=False)
    rows=[]
    for i in range(count):
        selected=label[mapped[:,0]]==i
        verts=uv[label==i]
        xyz=points[verts]*1000
        ids,degree=np.unique(edges[selected].ravel(),return_counts=True)
        degrees,freq=np.unique(degree,return_counts=True)
        rows.append({"vertices":len(verts),"edges":int(selected.sum()),
            "vertex_degree_histogram":{str(int(k)):int(v) for k,v in zip(degrees,freq)},
            "centroid_mm":xyz.mean(axis=0).tolist(),
            "bounds_mm":[xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist()],
            "radius_min_max_mm":[float(np.linalg.norm(xyz[:,:2],axis=1).min()),float(np.linalg.norm(xyz[:,:2],axis=1).max())],
            "edge_length_sum_mm":float(np.linalg.norm(points[edges[selected,0]]-points[edges[selected,1]],axis=1).sum()*1000)})
    return sorted(rows,key=lambda r:-r["edges"])
def topology(points,flat,lengths,patches):
    ends=np.cumsum(lengths,dtype=np.int64)-1
    starts=np.r_[0,ends[:-1]+1]
    following=np.roll(flat,-1); following[ends]=flat[starts]
    if np.any(flat==following):raise ValueError("Zero length topological edge")
    edges=np.sort(np.column_stack((flat,following)),axis=1)
    owner=np.repeat(np.arange(len(lengths),dtype=np.int64),lengths)
    order=np.lexsort((edges[:,1],edges[:,0]))
    es=edges[order]; own=owner[order]
    first=np.r_[True,np.any(es[1:]!=es[:-1],axis=1)]
    offsets=np.flatnonzero(first)
    counts=np.diff(np.r_[offsets,len(es)])
    uniq=es[offsets]
    incidence={str(int(k)):int(v) for k,v in zip(*np.unique(counts,return_counts=True))}
    # General adjacency, including pathological >2-face edges, without assuming manifoldness.
    anchor=np.repeat(own[offsets],counts)
    keep=anchor!=own
    graph=coo_matrix((np.ones(int(keep.sum()),dtype=np.int8),(anchor[keep],own[keep])),shape=(len(lengths),len(lengths))).tocsr()
    ncomp,labels=connected_components(graph,directed=False)
    edgelabels=labels[own[offsets]]
    components=[]
    for i in range(ncomp):
        fi=labels==i; ei=edgelabels==i
        verts=np.unique(uniq[ei])
        names,ncounts=np.unique(patches[fi],return_counts=True)
        xyz=points[verts]*1000
        components.append({"faces":int(fi.sum()),"vertices":len(verts),"edges":int(ei.sum()),
            "euler_characteristic":int(len(verts)-ei.sum()+fi.sum()),
            "patch_faces":{patch_names[int(k)]:int(v) for k,v in zip(names,ncounts)},
            "bounds_mm":[xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist()]})
    components.sort(key=lambda c:-c["faces"])
    loops=[]
    if np.all(counts==2):
        adj=own.reshape(-1,2)
        ps=np.sort(patches[adj],axis=1)
        rotor_stator=uniq[(ps[:,0]==2)&(ps[:,1]==3)]
        loops=loop_diagnostics(points,rotor_stator)
    return {"edge_connected_shells":int(ncomp),"all_edges_incident_to_two_faces":bool(np.all(counts==2)),
        "edge_incidence_histogram":incidence,"faces":len(lengths),"vertices":len(np.unique(flat)),"edges":len(uniq),
        "euler_characteristic":int(len(np.unique(flat))-len(uniq)+len(lengths)),"components":components,
        "rotor_stator_interface_loops":loops}
print("Input hashes linked; reading source STL",flush=True)
coords=array.array("d"); facets=array.array("B"); current=None; nvertices=0
with (case/"constant/triSurface/domain.stl").open() as f:
    for line in f:
        a=line.split()
        if not a:continue
        if a[0]=="solid":
            current=patch_names.index(a[1])
        elif a[0]=="vertex":
            if len(a)!=4 or current is None:raise ValueError("Bad STL vertex")
            coords.extend(map(float,a[1:])); nvertices+=1
        elif a[0]=="endfacet":
            if nvertices!=3:raise ValueError("Bad facet")
            facets.append(current); nvertices=0
assert len(coords)==len(facets)*9
raw=np.frombuffer(coords,dtype=np.float64).reshape(-1,3)
points,index=np.unique(raw,axis=0,return_inverse=True)
del raw,coords
surface=topology(points,index,np.full(len(facets),3,dtype=np.int32),np.frombuffer(facets,dtype=np.uint8))
del points,index,facets
print("Source topology",json.dumps({"shells":surface["edge_connected_shells"],"components":[{"patches":sorted(c["patch_faces"]),"Euler":c["euler_characteristic"]} for c in surface["components"]]}),flush=True)

n,bdy,uniform=foam_payload(case/"constant/polyMesh/boundary")
matches=list(re.finditer(r"(\w+)\s*\{([^{}]*)\}",bdy))
assert n==4 and len(matches)==n and not re.sub(r"(\w+)\s*\{([^{}]*)\}","",bdy).strip()
records=[]
for m in matches:
    name=m[1];body=m[2]
    count=int(re.search(r"\bnFaces\s+(\d+)\s*;",body)[1])
    start=int(re.search(r"\bstartFace\s+(\d+)\s*;",body)[1])
    records.append((start,count,name))
records.sort()
assert sorted(x[2] for x in records)==patch_names
assert all(records[i][0]+records[i][1]==records[i+1][0] for i in range(3))
start_face=records[0][0]; nboundary=sum(r[1] for r in records)
patches=np.concatenate([np.full(n,patch_names.index(name),dtype=np.uint8) for start,n,name in records])
print("Reading native boundary",nboundary,"faces",flush=True)
lengths=array.array("i"); flat=array.array("q")
with (case/"constant/polyMesh/faces").open() as f:
    header=""
    while True:
        line=next(f);header+=line
        if re.fullmatch(r"\s*\d+\s*",line):nfaces=int(line);break
    assert re.search(r"\bformat\s+ascii\s*;",header) and re.search(r"\bclass\s+faceList\s*;",header)
    assert next(f).strip()=="("
    assert start_face+nboundary==nfaces
    for i in range(nfaces):
        line=next(f)
        if i<start_face:continue
        m=re.fullmatch(r"\s*(\d+)\(([\d\s]+)\)\s*",line)
        if not m:raise ValueError("Bad native boundary face "+str(i))
        values=list(map(int,m[2].split()))
        if len(values)!=int(m[1]) or len(values)<3 or len(set(values))!=len(values):raise ValueError("Bad polygon")
        lengths.append(len(values));flat.extend(values)
    assert next(f).strip()==")"
    assert not clean(f.read()).strip()
points=numeric_list(case/"constant/polyMesh/points",3)
flat=np.frombuffer(flat,dtype=np.int64); lengths=np.frombuffer(lengths,dtype=np.int32)
assert flat.min()>=0 and flat.max()<len(points)
boundary=topology(points,flat,lengths,patches)
print("Native topology",json.dumps({"shells":boundary["edge_connected_shells"],"components":[{"patches":sorted(c["patch_faces"]),"Euler":c["euler_characteristic"]} for c in boundary["components"]]}),flush=True)
levels=numeric_list(case/"constant/polyMesh/cellLevel")
levelhist={str(int(k)):int(v) for k,v in zip(*np.unique(levels,return_counts=True))}
owners=numeric_list(case/"constant/polyMesh/owner")
assert len(owners)==nfaces and owners.min()>=0 and owners.max()<len(levels)
boundary_owners=owners[start_face:]
owner_levels={}
for i,name in enumerate(patch_names):
    selected=np.unique(boundary_owners[patches==i])
    owner_levels[name]={"owner_cell_count":len(selected),"level_histogram":{str(int(k)):int(v) for k,v in zip(*np.unique(levels[selected],return_counts=True))}}
del owners,levels,points,flat,lengths
def inv(result):
    return sorted([{"patches":sorted(c["patch_faces"]),"euler_characteristic":c["euler_characteristic"]} for c in result["components"]],key=lambda x:(x["patches"],x["euler_characteristic"]))
checks={"input_topology_matches_preparation": inv(surface)==manifest["surface"]["boundary_topology"]["component_invariants"],
        "all_native_edges_have_two_incident_faces":boundary["all_edges_incident_to_two_faces"],
        "surface_shell_count_preserved":surface["edge_connected_shells"]==boundary["edge_connected_shells"],
        "global_euler_preserved":surface["euler_characteristic"]==boundary["euler_characteristic"],
        "component_patch_and_euler_invariants_preserved":inv(surface)==inv(boundary)}
assert checks["input_topology_matches_preparation"]
snappy=(case/"log.snappyHexMesh").read_text()
native_finished=any(s.get("name")=="snappyHexMesh" and s.get("exit_code")==0 for s in receipt.get("stages",[]))
result={"schema":"bionic-turbo-independent-mesh-topology-diagnostic/v2",
    "status":"topology_invariants_preserved" if all(checks.values()) else "rejected_topology_not_preserved",
    "case":str(case),"method":"Independent streaming ASCII parsing and NumPy/SciPy. Exact-coordinate STL indexing. Face components use shared edges, not points. Euler=V-E+F without assuming vertex-manifold genus. Inputs hashed before and after analysis.",
    "input_sha256":hashes,"native_receipt_status":receipt["status"],"native_receipt_error":receipt.get("error"),
    "native_snappy_stage_completed":native_finished,"native_mesh_gate_passed":receipt.get("mesh_gate_passed",False),
    "input_surface":surface,"native_boundary":boundary,"checks":checks,
    "cell_count":sum(levelhist.values()),"cell_level_histogram":levelhist,
    "boundary_owner_cell_levels":owner_levels,
    "actual_cells_across_gaps_measured":False,
    "limitations_fr":["Les niveaux des cellules adjacentes aux patches ne mesurent pas le nombre de cellules traversant un jeu.",
      "L'égalité des invariants ne prouve ni la conservation des dimensions ni celle de chaque passage local.",
      "Aucun genre déduit : les liens des sommets ne sont pas contrôlés.",
      "Aucun maillage, solve ou modification de source exécuté pour ce diagnostic."],
    "solver_readiness_established":False,"performance_ranking_authorized":False}
for n,before in hashes.items():
    assert sha(case/n)==before,"Input changed during diagnostic: "+n
with out.open("x") as f:
    json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
print(json.dumps({"output":str(out),"sha256":sha(out),"status":result["status"],"checks":checks,"cell_level_histogram":levelhist,
    "native_boundary":boundary},indent=2),flush=True)

