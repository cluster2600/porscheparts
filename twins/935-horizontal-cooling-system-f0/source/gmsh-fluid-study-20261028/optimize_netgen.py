"""Private bounded Netgen optimizer trial, preserving the exploratory Gmsh source."""
import hashlib
import json
from pathlib import Path
import sys,time
import gmsh
source,output=map(lambda s:Path(s).resolve(),sys.argv[1:])
if output.exists():raise SystemExit('Output must be fresh')
if hashlib.sha256(source.read_bytes()).hexdigest()!='2a7346eb7696b67c59ffd23d791f1d8ddd82f69ab22f87986e1b1ac43b0006e7':raise SystemExit('Unexpected source mesh')
gmsh.initialize();gmsh.option.setNumber('General.Terminal',1)
gmsh.open(str(source))
before={str(i):len(gmsh.model.mesh.getElementsByType(2,i)[0]) for i in range(1,5)}
start=time.monotonic();gmsh.model.mesh.optimize('Netgen')
after={str(i):len(gmsh.model.mesh.getElementsByType(2,i)[0]) for i in range(1,5)}
if after!=before:raise SystemExit('Boundary face counts changed')
gmsh.write(str(output))
print(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'seconds':time.monotonic()-start,'boundary_counts_before':before,'boundary_counts_after':after}),flush=True)
gmsh.finalize()
