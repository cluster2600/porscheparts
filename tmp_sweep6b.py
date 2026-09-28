import json, re, subprocess
from pathlib import Path
import gmsh

workdir=Path('/workspace')
interfaces=json.loads((workdir/'work/993-cylinder-head-fast/reports/interfaces.json').read_text())
base=workdir/'work/993-cylinder-head-fast/cfd-sweep6b'
base.mkdir(parents=True,exist_ok=True)


def parse_det(txt):
    for ln in txt.splitlines():
        if 'Cells with small determinant' in ln and 'number of cells:' in ln:
            return int(re.search(r'number of cells:\s*(\d+)', ln).group(1))
    return None

def run(name,label,mn,mx,cont):
    outdir=base/name/label
    outdir.mkdir(parents=True,exist_ok=True)
    msh=outdir/'fluid-domain.msh'
    rings=sorted([r for r in interfaces['port_sections'][name] if 'diameter_obj_units' in r], key=lambda r: float(r['plane_B']))

    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal',0)
    gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
    gmsh.option.setNumber('Mesh.Binary',0)
    gmsh.option.setNumber('Mesh.MeshSizeMin',mn)
    gmsh.option.setNumber('Mesh.MeshSizeMax',mx)
    gmsh.option.setNumber('Mesh.Algorithm3D',1)
    gmsh.model.add(f'{name}_{label}')

    wires=[]
    for ring in rings:
        a,c=ring['center']
        cir=gmsh.model.occ.addCircle(float(a), float(ring['plane_B']), float(c), float(ring['diameter_obj_units'])/2.0, zAxis=[0,1,0], xAxis=[1,0,0])
        wires.append(gmsh.model.occ.addWire([cir], checkClosed=True))
    ents=gmsh.model.occ.addThruSections(wires, makeSolid=True, makeRuled=False, continuity=cont, smoothing=True)
    gmsh.model.occ.synchronize()
    vols=[t[1] for t in ents if t[0]==3]
    if len(vols)!=1:
        gmsh.finalize(); return None
    b=gmsh.model.getBoundary([(3,vols[0])],oriented=False,recursive=False)
    surfs=[t[1] for t in b if t[0]==2]
    gmsh.model.addPhysicalGroup(3,vols,1,'fluid')
    gmsh.model.addPhysicalGroup(2,surfs,2,'boundary')
    gmsh.model.mesh.generate(3)
    for m in ['Netgen','UntangleMeshGeometry','Relocate3D','OptimizeMesh']:
        try: gmsh.model.mesh.optimize(m, force=True)
        except Exception: pass
    gmsh.write(str(msh)); gmsh.finalize()

    case=outdir/'openfoam'
    cmd=['bash','-lc',f'cd /workspace && twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh {msh} {case}']
    try:
        out=subprocess.check_output(cmd,text=True,stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        out=e.output
    (outdir/'checkMesh.log').write_text(out)
    return parse_det(out)

for mn,mx in [(3,9),(3,10),(3,12),(4,10),(4,12),(5,10),(5,12),(2.5,8),(2.5,9),(2.8,9.5)]:
    for cont in ['C0','C1','C2']:
        lab=f'r0_{cont}_{mn}_{mx}'
        d=run('high_B',lab,mn,mx,cont)
        print('high_B',lab,d)
