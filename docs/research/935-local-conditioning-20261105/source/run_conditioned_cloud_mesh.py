"""Hash-bound, bounded cube/head worker for the admitted conditioned surface."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import gmsh
import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def write(path,value):
    with path.open("x") as stream:stream.write(json.dumps(value,indent=2)+'\n')


def main():
    root=Path(__file__).resolve().parent;os.chdir(root)
    if (root/"terminal-state.json").exists() or (root/"worker-pid.json").exists():
        raise RuntimeError("Existing worker output refused")
    plan=json.loads((root/"mesh-plan.json").read_text())
    manifest=json.loads((root/"input-manifest.json").read_text())
    for row in manifest["files"]:
        assert sha(root/row["path"])==row["sha256"],"Worker input hash mismatch"
    geometry=json.loads((root/"geometry-admission.json").read_text())
    preservation=json.loads((root/"preservation-admission.json").read_text())
    expected="7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(root/"candidate.npz")==geometry["input_sha256"]==preservation["candidate_sha256"]==expected
    assert geometry["geometry_export_gate_passed"] and geometry["intersection_pairs"]==0
    assert preservation["preservation_checks_passed"] and preservation["quality_reduction_gate_passed"]
    assert gmsh.__version__=="4.12.1" and len(os.sched_getaffinity(0))>=plan["threads"]
    assert plan["algorithm"]==10 and plan["interior_size_mm"]==2 and plan["threads"]==32
    assert plan["head_deadline_seconds"]==1800 and plan["child_address_space_gib"]==48
    write(root/"worker-pid.json",{"pid":os.getpid(),"started_epoch":time.time()})
    write(root/"runtime-verification.json",{"python":os.sys.version.split()[0],"numpy":np.__version__,"gmsh":gmsh.__version__,
          "gmsh_module_sha256":sha(Path(gmsh.__file__)),"cpu_affinity_count":len(os.sched_getaffinity(0)),
          "source_sha256":sha(Path(__file__)),"mesh_sha256":expected,"child_address_space_gib":48})
    def memory_limit():resource.setrlimit(resource.RLIMIT_AS,(48*1024**3,48*1024**3))
    steps=[]
    def run(name,argv,timeout):
        started=time.monotonic();timed_out=False
        with (root/(name+".log")).open("x") as stream:
            try:x=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,preexec_fn=memory_limit);code=x.returncode
            except subprocess.TimeoutExpired:code=None;timed_out=True
        result={"argv":argv,"exit_code":code,"timeout":timed_out,"seconds":time.monotonic()-started,
                "log_sha256":sha(root/(name+".log"))}
        write(root/(name+"-execution.json"),result);steps.append(result)
        if timed_out or code!=0:raise RuntimeError("Bounded worker step failed: "+name)
    python=os.sys.executable
    run("cube",[python,"-B","mesh_solid.py","cube","cube","--size",".4","--threads","2"],90)
    with np.load(root/"cube/solid.npz",allow_pickle=False) as data:
        v,t=data["nodes"],data["tets"]
    signed=np.einsum('ij,ij->i',v[t[:,1]]-v[t[:,0]],np.cross(v[t[:,2]]-v[t[:,0]],v[t[:,3]]-v[t[:,0]]))/6
    assert np.all(signed>0) and abs(signed.sum()-1)<1e-10
    write(root/"cube-control.json",{"unit_volume_positive_cells":True,"volume_mm3":float(signed.sum())})
    run("head",[python,"-B","mesh_solid.py","candidate.npz","head","--size","2.0","--algorithm","10","--threads","32"],1800)
    run("independent-head",[python,"-B","inspect_tetrahedra.py","--mesh","head/solid.npz","--source-mesh","candidate.npz",
                            "--source-report","geometry-admission.json","--output","independent-head"],600)
    independent=json.loads((root/"independent-head/report.json").read_text())
    assert independent["diagnostic_geometry_consistency_passed"] and not independent["physics_admitted"]
    return {"terminal":"native_and_independent_geometry_checks_completed","steps":steps,
            "physics_admitted":False,"manufacturing_qualified":False}


if __name__=="__main__":
    root=Path(__file__).resolve().parent
    try:state=main()
    except Exception as error:
        state={"terminal":"worker_failed_closed","exception_type":type(error).__name__,"error":str(error),
               "physics_admitted":False,"manufacturing_qualified":False}
    write(root/"terminal-state.json",state)
    files=[]
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.name not in ('result-manifest.json','worker.log'):
            files.append({"path":str(path.relative_to(root)),"sha256":sha(path),"bytes":path.stat().st_size})
    write(root/"result-manifest.json",{"files":files,"terminal":state["terminal"]})
    print(json.dumps(state),flush=True)
    if state["terminal"]!="native_and_independent_geometry_checks_completed":raise SystemExit(1)
