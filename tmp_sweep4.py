import json, re, subprocess
from pathlib import Path
import gmsh

workdir = Path('/workspace')
interfaces = json.loads((workdir / 'work/993-cylinder-head-fast/reports/interfaces.json').read_text())
base = workdir / 'work/993-cylinder-head-fast/cfd-sweep4'
base.mkdir(parents=True, exist_ok=True)

def parse_cells(out: str):
    for ln in out.splitlines():
        if 'number of cells' in ln and 'small determinant' in ln:
            m = re.search(r'number of cells: (\d+)', ln)
            if m:
                return int(m.group(1))
    return None


def run_case(name, label, mins, mmax, alg, ruled, continuity, opt):
    outdir = base / name / label
    outdir.mkdir(parents=True, exist_ok=True)
    msh = outdir / 'fluid-domain.msh'
    rings = [r for r in interfaces['port_sections'][name] if 'diameter_obj_units' in r]
    rings = sorted(rings, key=lambda r: float(r['plane_B']))

    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)
    gmsh.option.setNumber('Mesh.Binary', 0)
    gmsh.option.setNumber('Mesh.MeshSizeMin', mins)
    gmsh.option.setNumber('Mesh.MeshSizeMax', mmax)
    gmsh.option.setNumber('Mesh.Algorithm3D', alg)

    gmsh.model.add(f'{name}_{label}')

    wires = []
    for ring in rings:
        a, c = ring['center']
        cir = gmsh.model.occ.addCircle(float(a), float(ring['plane_B']), float(c), float(ring['diameter_obj_units']) / 2.0, zAxis=[0, 1, 0], xAxis=[1, 0, 0])
        wires.append(gmsh.model.occ.addWire([cir], checkClosed=True))

    ents = gmsh.model.occ.addThruSections(wires, makeSolid=True, makeRuled=ruled, continuity=continuity, smoothing=True)
    gmsh.model.occ.synchronize()
    vols = [tag for dim, tag in ents if dim == 3]
    if len(vols) != 1:
        gmsh.finalize()
        return None
    bnd = gmsh.model.getBoundary([(3, vols[0])], oriented=False, recursive=False)
    surfs = [tag for dim, tag in bnd if dim == 2]
    gmsh.model.addPhysicalGroup(3, vols, 1, 'fluid')
    gmsh.model.addPhysicalGroup(2, surfs, 2, 'boundary')

    try:
        gmsh.model.mesh.generate(3)
    except Exception as e:
        gmsh.finalize()
        return None
    # fixed optimization chain, fallback if unsupported
    for m in ['Netgen', 'UntangleMeshGeometry', 'Relocate3D', 'Laplace3D']:
        try:
            gmsh.model.mesh.optimize(m, force=True)
        except Exception:
            pass

    gmsh.write(str(msh))
    gmsh.finalize()

    case = outdir / 'openfoam'
    cmd = ['bash', '-lc', f'cd /workspace && twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh {msh} {case}']
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        out = e.output
    (outdir / 'checkMesh.log').write_text(out)
    return parse_cells(out)

params=[]
for alg in [1,2,3,5,6,7,8,9,10,11]:
    for ruled in [True, False]:
        for cont in ['C0','C1','C2']:
            for mn,mx in [(1.5,6.0),(2.0,6.0),(2.5,6.0),(2.0,7.0),(3.0,7.5),(3.5,8.0)]:
                params.append((f'a{alg}_r{int(ruled)}_{cont}_{mn}_{mx}', alg, ruled, cont, mn, mx))

for name in ('low_B','high_B'):
    best=(10**9, None)
    print('===',name)
    for label, alg, ruled, cont, mn, mx in params:
        det = run_case(name,label,mn,mx,alg,ruled,cont,True)
        print(name,label,det)
        if det is not None and det < best[0]:
            best=(det,label)
    print('BEST',name,best)
