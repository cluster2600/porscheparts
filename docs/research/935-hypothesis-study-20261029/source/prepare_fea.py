"""Prepare explicitly hypothetical pressure and thermal studies; never a release gate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('mesh', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--frame', type=Path)
p.add_argument('--cube', action='store_true')
args = p.parse_args()
args.output.mkdir()
d = np.load(args.mesh)
x, e, f = d['nodes'], d['tets'], d['boundary']
assert e.shape[1] == 4 and f.shape[1] == 3 and np.isfinite(x).all()
v6 = np.einsum('ij,ij->i', np.cross(x[e[:,1]]-x[e[:,0]], x[e[:,2]]-x[e[:,0]]), x[e[:,3]]-x[e[:,0]])
assert (v6 > 0).all(), 'Nonpositive tetrahedra are not accepted even for a study'
centres = x[f].mean(axis=1)
area_vector = np.cross(x[f[:,1]]-x[f[:,0]], x[f[:,2]]-x[f[:,0]])/2
areas = np.linalg.norm(area_vector, axis=1)
assert (areas > 0).all()
surface_volume = np.einsum('ij,ij->', centres, area_vector)/3
assert abs(surface_volume-v6.sum()/6)/(v6.sum()/6) < 1e-6, 'Boundary orientation/volume mismatch'
if args.cube:
    q, qc = x, centres
    loaded = np.isclose(qc[:,2], 1)
    hot = np.isclose(q[:,0], 1)
    cold = np.isclose(q[:,0], 0)
    fixed = np.isclose(q[:,2], 0)
    pressure = 1.
else:
    assert args.frame is not None
    frame = np.load(args.frame)
    assert frame.shape == (3,3) and np.allclose(frame.T @ frame, np.eye(3), atol=1e-7)
    q, qc = x @ frame.T, centres @ frame.T
    normals = (area_vector / areas[:,None]) @ frame.T
    # Assumed gas-side footprint, NOT specimen-measured chamber/interface evidence.
    radius = np.linalg.norm(qc[:,:2] - [125., -160.], axis=1)
    loaded = (radius < 47) & (qc[:,2] > -135) & (normals[:,2] > .25)
    hot = np.zeros(len(x), bool)
    hot[np.unique(f[loaded])] = True
    skin = np.zeros(len(x), bool)
    skin[np.unique(f)] = True
    cold = skin & ~hot & (q[:,2] < -140)
    # Rigid back-plane support is a declared stiffness-bound assumption.
    fixed = skin & (q[:,2] >= -172) & (q[:,2] <= -170)
    pressure = 10.
assert loaded.any() and hot.any() and cold.any() and fixed.any()
force = np.zeros_like(x)
for j in range(3):
    np.add.at(force, f[loaded,j], -pressure*area_vector[loaded]/3)
assert np.linalg.norm(force.sum(axis=0)+pressure*area_vector[loaded].sum(axis=0)) < 1e-7 * max(1,np.linalg.norm(force.sum(axis=0)))

def node_set(out, name, mask):
    out.write('*NSET,NSET='+name+'\n')
    ids = np.flatnonzero(mask)+1
    for chunk in range(0,len(ids),16):
        out.write(','.join(map(str,ids[chunk:chunk+16]))+'\n')

with (args.output/'mesh.inp').open('w') as out:
    out.write('** Units: mm, N, s, degrees Celsius. Assumed material.\n*NODE,NSET=ALL\n')
    for i, row in enumerate(x,1): out.write(f'{i},{row[0]:.12g},{row[1]:.12g},{row[2]:.12g}\n')
    out.write('*ELEMENT,TYPE=C3D4,ELSET=BODY\n')
    for i,row in enumerate(e+1,1): out.write(str(i)+','+','.join(map(str,row))+'\n')
    for name,mask in [('HOT',hot),('COLD',cold),('FIXED',fixed)]:node_set(out,name,mask)
    out.write('*MATERIAL,NAME=ASSUMED_ALUMINIUM\n*ELASTIC\n70000.,0.33\n*EXPANSION,ZERO=80.\n23.e-6\n*CONDUCTIVITY\n150.\n*SOLID SECTION,ELSET=BODY,MATERIAL=ASSUMED_ALUMINIUM\n')
    # Conductivity is N/(s K) = 1e-3 W/(mm K): 150 W/(m K) => 150 in consistent mm,N,s units.

with (args.output/'pressure.inp').open('w') as out:
    out.write('*INCLUDE,INPUT=mesh.inp\n*BOUNDARY\n')
    if args.cube:
        out.write('FIXED,3,3\n')
        origin = int(np.argmin(np.linalg.norm(x,axis=1)))+1
        axis = int(np.argmin(np.linalg.norm(x-[1,0,0],axis=1)))+1
        out.write(f'{origin},1,2\n{axis},2,2\n')
    else:out.write('FIXED,1,3\n')
    out.write('*STEP\n*STATIC,SOLVER=ITERATIVE CHOLESKY\n*CLOAD\n')
    for i in np.flatnonzero(np.linalg.norm(force,axis=1)):
        for j in range(3):
            if abs(force[i,j])>1e-15:out.write(f'{i+1},{j+1},{force[i,j]:.12g}\n')
    out.write('*NODE FILE\nU,RF\n*EL FILE\nS\n*NODE PRINT,NSET=FIXED,TOTALS=YES\nRF\n*END STEP\n')
with (args.output/'thermal.inp').open('w') as out:
    out.write('*INCLUDE,INPUT=mesh.inp\n*STEP\n*HEAT TRANSFER,STEADY STATE,SOLVER=ITERATIVE CHOLESKY\n*BOUNDARY\n')
    out.write('HOT,11,11,100.\nCOLD,11,11,0.\n' if args.cube else 'HOT,11,11,250.\nCOLD,11,11,80.\n')
    out.write('*NODE FILE\nNT,RFL\n*NODE PRINT,NSET=HOT,TOTALS=YES\nRFL\n*NODE PRINT,NSET=COLD,TOTALS=YES\nRFL\n*END STEP\n')
report = {'status':'conditional numerical study only','mesh_sha256':hashlib.sha256(args.mesh.read_bytes()).hexdigest(),'nodes':len(x),'tetrahedra':len(e),'volume_mm3':float(v6.sum()/6),'surface_volume_mm3':float(surface_volume),'pressure_mpa':pressure,'loaded_area_mm2':float(areas[loaded].sum()),'pressure_force_N':force.sum(axis=0).tolist(),'hot_nodes':int(hot.sum()),'cold_nodes':int(cold.sum()),'fixed_nodes':int(fixed.sum()),'assumed_material':{'name':'generic AlSi10Mg-like aluminium; not specimen identification','E_MPa':70000,'nu':.33,'CTE_per_K':23e-6,'k_W_m_K':150},'thermal_condition':'prescribed 250 C gas-side and 80 C back/fin surfaces; remaining boundary adiabatic','structural_condition':'all displacement fixed at assumed back-plane band; no measured bolt preload/contact','mesh_convergence_established':False,'physical_geometry_accepted':False,'manufacturing_qualified':False}
(args.output/'assumptions.json').write_text(json.dumps(report,indent=2)+'\n')
np.savez_compressed(args.output/'boundary-assignments.npz',hot=hot,cold=cold,fixed=fixed,loaded_triangles=loaded,force=force)
print(json.dumps(report))
