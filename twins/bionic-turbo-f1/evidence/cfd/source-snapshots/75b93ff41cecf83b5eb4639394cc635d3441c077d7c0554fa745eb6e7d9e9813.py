#!/usr/bin/env python3
"""Run one explicitly selected local CFD stage with a fixed image and time limit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from prepare_case import IMAGE, PATCHES, closed_boundary_topology


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label_list(text):
    text=re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match=re.search(r"\}\s*(\d+)\s*\(\s*([\d\s]*)\)\s*$",text)
    if not match:
        raise ValueError("Expected ASCII label list")
    values=list(map(int,match[2].split()))
    if len(values)!=int(match[1]):
        raise ValueError("Label count mismatch")
    return values


def inspect_mesh(case, expected_topology):
    mesh=case/"constant/polyMesh"
    boundary=(mesh/"boundary").read_text()
    patches={}
    for match in re.finditer(r"(\w+)\s*\{([^{}]*)\}",boundary):
        block=match[2]
        count=re.search(r"\bnFaces\s+(\d+)\s*;",block)
        start=re.search(r"\bstartFace\s+(\d+)\s*;",block)
        kind=re.search(r"\btype\s+(\w+)\s*;",block)
        if count and start and kind:
            patches[match[1]]={"faces":int(count[1]),"start":int(start[1]),"type":kind[1]}
    if {p for p,v in patches.items() if v["faces"]}!=set(PATCHES):
        raise ValueError("Only the four declared patches may have boundary faces")
    if any(patches[p]["type"] != ("patch" if p in ("inlet","outlet") else "wall") for p in PATCHES):
        raise ValueError("Open-port/wall patch type mismatch")
    face_labels={i:p for p,v in patches.items() for i in range(v["start"],v["start"]+v["faces"])}
    faces_text=(mesh/"faces").read_text()
    def boundary_records():
        found=0
        for index,match in enumerate(re.finditer(r"(\d+)\s*\(([\d\s]+)\)",faces_text)):
            if index in face_labels:
                face=tuple(map(int,match[2].split()))
                if len(face)!=int(match[1]):
                    raise ValueError("Boundary polygon vertex count mismatch")
                found+=1
                yield face,face_labels[index]
        if found!=len(face_labels):
            raise ValueError("Missing boundary polygons")
    topology=closed_boundary_topology(boundary_records())
    if any(topology[key]!=expected_topology[key] for key in ("surface_components","component_patch_sets")):
        raise ValueError("Surface shell count or component patch provenance changed during meshing")
    zones=(mesh/"cellZones").read_text()
    zone=re.search(r"\brotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\(\s*([\d\s]*)\)",zones,re.S)
    if not zone:
        raise ValueError("Explicit nonempty rotorZone missing")
    labels=list(map(int,zone[2].split()))
    if len(labels)!=int(zone[1]) or not labels or len(set(labels))!=len(labels):
        raise ValueError("Invalid rotorZone labels")
    owners=label_list((mesh/"owner").read_text())
    cells=set(labels)
    for name in PATCHES:
        p=patches[name]
        selected=owners[p["start"]:p["start"]+p["faces"]]
        if len(selected)!=p["faces"]:
            raise ValueError("Boundary face outside owner addressing")
        if name=="rotor" and not all(i in cells for i in selected):
            raise ValueError("Some rotor faces lie outside the rotating cell zone")
        if name in ("inlet","outlet") and any(i in cells for i in selected):
            raise ValueError("Measurement port intersects MRF cell zone")
    return {"patches":patches,"boundary_topology":topology,"surface_components_and_patch_provenance_preserved":True,
            "rotor_zone_cells":len(cells),"rotor_owner_cells_all_in_zone":True,
            "ports_outside_zone":True, "mesh_sha256":{str(p.relative_to(case)):sha(p) for p in mesh.iterdir() if p.is_file()}}


def run(case,stage,timeout,cpus,memory_gb):
    case=case.resolve()
    manifest_path=case/"case-manifest.json"
    manifest=json.loads(manifest_path.read_text())
    if manifest.get("schema")!="bionic-turbo-compressible-mrf/v1" or manifest.get("image")!=IMAGE or manifest.get("solver")!="rhoSimpleFoam":
        raise ValueError("Only the pinned OpenCFD 2406 case is supported")
    if not 1<=cpus<=4 or not 1<=memory_gb<=12 or not 1<=timeout<=7200:
        raise ValueError("CPU, memory or stage time limit outside local bounds")
    report_path=case/f"run-{stage}.json"
    if report_path.exists() or list(case.glob("FAILED*.json")):
        raise ValueError("Stage already attempted; prepare a new case instead")
    for relative,expected in manifest["file_sha256"].items():
        if not (case/relative).resolve().is_relative_to(case):
            raise ValueError("Input path escapes case")
        if sha(case/relative)!=expected:
            raise ValueError("Prepared input changed: "+relative)
    if stage=="mesh" and (case/"constant/polyMesh").exists():
        raise ValueError("Existing mesh: fresh case required")
    if stage=="solve":
        previous=json.loads((case/"run-mesh.json").read_text())
        if previous.get("status")!="completed" or not previous.get("mesh_gate_passed") or previous.get("case_manifest_sha256")!=sha(manifest_path):
            raise ValueError("Successful mesh gate required before solve")
        for relative,expected in previous["mesh_sha256"].items():
            if sha(case/relative)!=expected:
                raise ValueError("Mesh changed since mesh gate")
        if (case/"postProcessing").exists() or any(p.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?",p.name) and p.name!="0" for p in case.iterdir()):
            raise ValueError("Existing solve output: fresh case required")
    commands={"mesh":[("blockMesh","blockMesh"),("snappyHexMesh","snappyHexMesh -overwrite"),("topoSet","topoSet"),("checkMesh","checkMesh -allTopology -allGeometry")],
        "solve":[("rhoSimpleFoam","rhoSimpleFoam")],
        "config":[("dictionary-"+str(i),"foamDictionary "+name+" -keywords") for i,name in enumerate(manifest["file_sha256"]) if name!="constant/triSurface/domain.stl"]}[stage]
    report={"schema":"bionic-turbo-mrf-execution/v1","stage":stage,"status":"running","image":IMAGE,
        "case_manifest_sha256":sha(manifest_path),"runner_sha256":sha(Path(__file__)),"stages":[],
        "timeout_seconds":timeout,"cpus":cpus,"memory_gb":memory_gb,"mesh_gate_passed":False}
    started=time.monotonic()
    try:
        for name,command in commands:
            log=case/("log."+name)
            if log.exists():
                raise ValueError("Refusing to overwrite log: "+name)
            container="bionic-cfd-"+uuid.uuid4().hex[:12]
            argv=["docker","run","--rm","--pull=never","--platform","linux/arm64","--network","none","--read-only",
                "--name",container,"--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","256",
                "--cpus",str(cpus),"--memory",f"{memory_gb}g","--tmpfs","/tmp:rw,nosuid,size=256m",
                "--user",f"{os.getuid()}:{os.getgid()}","--mount",f"type=bind,source={case},target=/case",
                "--entrypoint","/bin/bash",IMAGE,"-c",
                "source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; exec "+command]
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:
                raise TimeoutError("Stage time budget exhausted")
            try:
                with log.open("x") as stream:
                    completed=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=remaining)
            finally:
                # This name was created by this invocation; never stop another task's container.
                subprocess.run(["docker","rm","-f",container],capture_output=True,timeout=15)
            record={"name":name,"exit_code":completed.returncode,"log":log.name,"sha256":sha(log)}
            report["stages"].append(record)
            text=log.read_text()
            if completed.returncode or "FOAM FATAL" in text:
                raise ValueError("Native stage failed: "+name)
            if name=="checkMesh" and "Mesh OK." not in text:
                raise ValueError("Extended checkMesh did not pass")
            if name=="checkMesh" and not re.search(r"Number of regions:\s+1\b",text):
                raise ValueError("Exactly one connected fluid region required")
        if stage=="mesh":
            report.update(inspect_mesh(case,manifest["surface"]["boundary_topology"]))
            report["mesh_gate_passed"]=True
        if sha(manifest_path)!=report["case_manifest_sha256"] or any(sha(case/name)!=expected for name,expected in manifest["file_sha256"].items()):
            raise ValueError("Case input changed during execution")
        report["status"]="completed"
    except Exception as error:
        report["status"]="failed"
        report["error"]=str(error)
        (case/f"FAILED-{stage}.json").write_text(json.dumps(report,indent=2)+"\n")
    report["elapsed_seconds"]=time.monotonic()-started
    with report_path.open("x") as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
        stream.write("\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case",type=Path)
    parser.add_argument("--stage",choices=("config","mesh","solve"),required=True)
    parser.add_argument("--timeout",type=int,default=300)
    parser.add_argument("--cpus",type=int,default=2)
    parser.add_argument("--memory-gb",type=int,default=4)
    args=parser.parse_args()
    report=run(args.case,args.stage,args.timeout,args.cpus,args.memory_gb)
    print(json.dumps({"status":report["status"],"stage":args.stage,"error":report.get("error")}))
    raise SystemExit(0 if report["status"]=="completed" else 1)
