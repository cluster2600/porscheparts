"""Bound one exact-boundary Gmsh diagnostic; no parameter sweep or physics admission."""
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
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "repository", "mesh", "geometry-report", "wall-report", "python", "scientific-site"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    stage = args.root / "gmsh-diagnostic"
    stage.mkdir(mode=0o700, exist_ok=False)
    expected = "05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    geometry = json.loads(args.geometry_report.read_text())
    walls = json.loads(args.wall_report.read_text())
    assert sha(args.mesh) == expected == geometry["input_sha256"] == walls["normal_chords"]["mesh_sha256"]
    assert geometry["geometry_export_gate_passed"] and geometry["intersection_pairs"] == 0
    assert geometry["connected_components"] == 1 and geometry["vertex_manifold"]
    script = args.repository / "docs/research/935-hypothesis-study-20261029/source/mesh_solid.py"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(args.scientific_site)
    runtime = subprocess.check_output([str(args.python), "-B", "-c",
        "import gmsh,numpy,json,platform;gmsh.initialize();gmsh.finalize();print(json.dumps({'gmsh':gmsh.__version__,'gmsh_file':gmsh.__file__,'numpy':numpy.__version__,'numpy_file':numpy.__file__,'python':platform.python_version(),'machine':platform.machine()}))"],
        env=environment, text=True, timeout=30)
    identity = json.loads(runtime)
    assert identity["gmsh"] == "4.12.1" and Path(identity["gmsh_file"]).is_relative_to(args.python.parent.parent)
    assert Path(identity["numpy_file"]).is_relative_to(args.scientific_site)
    write(stage / "runtime.json", identity)
    policy = {"scope":"One diagnostic conforming tetrahedralization of the actual delivered mesh; no geometry coarsening",
              "mesh_sha256":expected,"geometry_report_sha256":sha(args.geometry_report),"wall_report_sha256":sha(args.wall_report),
              "source_sha256":sha(Path(__file__)),"mesher_source_sha256":sha(script),
              "upstream_verdict":"Closed manifold geometry admitted for diagnostic meshing only. Sampled short material paths and sharp features remain unresolved for process/physics admission.",
              "interior_size_mm":2.0,"algorithm":10,"threads":8,"wall_limit_seconds":900,"rss_limit_gib":40,
              "minimum_remaining_disk_gib":4,"parameter_sweep":False,"physics_admitted":False,"new_paid_compute_usd":0}
    write(stage / "predeclared-policy.json", policy)
    command = [str(args.python),"-B",str(script),"cube",str(stage / "cube"),"--size","0.4","--threads","2"]
    with (stage / "cube.log").open("x") as log:
        control = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    assert control.returncode == 0, "Cube control failed"
    with np.load(stage / "cube/solid.npz",allow_pickle=False) as data:
        nodes,tets=data["nodes"],data["tets"]
    signed=np.linalg.det(nodes[tets[:,1:]]-nodes[tets[:,0,None]])/6
    assert np.all(signed>0) and abs(signed.sum()-1)<1e-10
    write(stage / "controls.json", {"gmsh_cube_terminal_exit_zero":True,"independent_positive_cells":True,
          "independent_analytic_volume":True,"cube_volume_mm3":float(signed.sum()),"argv":command})
    assert shutil.disk_usage(args.root).free > 10*1024**3, "Insufficient start disk space"
    command=[str(args.python),"-B",str(script),str(args.mesh),str(stage / "fine"),"--size","2.0","--algorithm","10","--threads","8"]
    peak=0; started=time.monotonic(); terminal="running"
    with (stage / "fine.log").open("x") as log:
        child=subprocess.Popen(command,env=environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        write(stage / "running.json",{"pid":child.pid,"argv":command,"policy":policy})
        try:
            while child.poll() is None:
                time.sleep(2)
                usage=subprocess.run(["ps","-o","rss=","-p",str(child.pid)],capture_output=True,text=True)
                if usage.stdout.strip():peak=max(peak,int(usage.stdout.strip()))
                elapsed=time.monotonic()-started
                if elapsed>900 or peak>40*1024**2 or shutil.disk_usage(args.root).free<4*1024**3:
                    terminal="bounded_limit_reached"
                    os.killpg(child.pid,signal.SIGTERM)
                    break
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
        finally:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
    if terminal=="running":terminal="native_success" if child.returncode==0 else "native_failure"
    result={"terminal":terminal,"argv":command,"exit_code":child.returncode,"seconds":time.monotonic()-started,
            "peak_rss_kib":peak,"log_sha256":sha(stage / "fine.log"),"input_mesh_sha256":expected,
            "physics_admitted":False,"manufacturing_qualified":False,"new_paid_compute_usd":0}
    write(stage / "execution.json",result)
    print(json.dumps(result),flush=True)
    if terminal!="native_success":raise SystemExit(1)


if __name__ == "__main__":
    main()
