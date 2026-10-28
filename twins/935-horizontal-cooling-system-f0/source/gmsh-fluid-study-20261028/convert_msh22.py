"""Re-encode the retained Gmsh MSH 4.1 fluid volume as OpenFOAM-readable MSH 2.2 ASCII."""
import gmsh
from pathlib import Path
import sys
source, output=map(lambda s:Path(s).resolve(),sys.argv[1:])
if output.exists():raise SystemExit('Output must be fresh')
gmsh.initialize()
gmsh.option.setNumber('General.Terminal',1)
gmsh.open(str(source))
groups=gmsh.model.getPhysicalGroups()
if groups != [(2,1),(2,2),(2,3),(2,4),(3,1)]:
    raise SystemExit(f'Unexpected physical groups: {groups}')
gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
gmsh.option.setNumber('Mesh.Binary',0)
gmsh.option.setNumber('Mesh.SaveAll',0)
gmsh.write(str(output))
gmsh.finalize()
