import json, math, subprocess
from pathlib import Path
import gmsh

workdir=Path('/workspace')
interfaces=json.loads((workdir/'work/993-cylinder-head-fast/reports/interfaces.json').read_text())
base=workdir/'work/993-cylinder-head-fast/cfd-sweep7'
base.mkdir(parents=True,exist_ok=True)

def run(name,segments):
    rings=[r for r in interfaces['port_sections'][name] if 'diameter_obj_units' in r]
    rings=sorted(rings,key=lambda r: float(r['plane_B']))
    outdir=base/name/f'seg{segments}'
    outdir.mkdir(parents=True,exist_ok=True)
    msh=outdir/'fluid-domain.msh'
    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal',0)
    gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
    gmsh.option.setNumber('Mesh.Binary',0)
    gmsh.option.setNumber('Mesh.MeshSizeMin',2.5)
    gmsh.option.setNumber('Mesh.MeshSizeMax',8.0)
    gmsh.option.setNumber('Mesh.Algorithm3D',1)

    gmsh.model.add(f'{name}_seg{segments}')
    wires=[]
    for ring in rings:
        cx,cz=ring['center']
        r=ring['diameter_obj_units']/2.0
        b=float(ring['plane_B'])
        pt_ids=[]
        for i in range(segments):
            ang=2*math.pi*i/segments
            pid=gmsh.model.occ.addPoint(cx+r*math.cos(ang), b, cz+r*math.sin(ang))
            pt_ids.append(pid)
        edge_ids=[]
        for i in range(segments):
            a=pt_ids[i]
            bpt=pt_ids[(i+1)%segments]
            edge_ids.append(gmsh.model.occ.addLine(a,bpt))
        wires.append(gmsh.model.occ.addWire(edge_ids, checkClosed=True))
    ents=gmsh.model.occ.addThruSections(wires,makeSolid=True,makeRuled=True,continuity='C2',smoothing=True)
    gmsh.model.occ.synchronize()
    vols=[tag for dim,tag in ents if dim==3]
    if len(vols)!=1:
        print('bad',name,segments,len(vols))
        gmsh.finalize(); return None
    bnd=gmsh.model.getBoundary([(3,vols[0])],oriented=False,recursive=False)
    surfs=[tag for dim,tag in bnd if dim==2]
    gmsh.model.addPhysicalGroup(3,vols,1,'fluid')
    gmsh.model.addPhysicalGroup(2,surfs,2,'boundary')
    gmsh.model.mesh.generate(3)
    for m in ['Netgen','UntangleMeshGeometry','Relocate3D','OptimizeMesh']:
        try: gmsh.model.mesh.optimize(m,force=True)
        except Exception: pass
    gmsh.write(str(msh))
    gmsh.finalize()
    case=outdir/'openfoam'
    cmd=['bash','-lc',f'cd /workspace && twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh {msh} {case}']
    try:
        out=subprocess.check_output(cmd,text=True,stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        out=e.output
    (outdir/'checkMesh.log').write_text(out)
    det=None
    for ln in out.splitlines():
        if 'number of cells:' in ln and 'small determinant' in ln:
            import re
            det=int(re.search(r'number of cells: (\d+)',ln).group(1)); break
    return det

for name in ('low_B','high_B'):
    for s in (16,24,32,48):
        d=run(name,s)
        print(name,'seg',s,'det',d)
