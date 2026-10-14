"""Audit native background interfaces and localize rejected cells, without a solver claim."""
import json,sys,re
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from audit_frame_interface import face_geometry
from audit_frame_interface_v2 import cell_flags
from run_case import ascii_faces
from prepare_case import sha
case,output=map(Path,sys.argv[1:]);m=json.loads((case/'manifest.json').read_text());r=json.loads((case/'report.json').read_text())
assert r['manifest_sha256']==sha(case/'manifest.json')
assert all(sha(case/name)==digest for name,digest in r['output_sha256'].items())
mesh=case/'constant/polyMesh';points=ascii_list((mesh/'points').read_text(),True)
owner=ascii_list((mesh/'owner').read_text()).astype(np.int64);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(np.int64)
x=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);assert x
zone=np.fromstring(x[2],sep=' ',dtype=np.int64);assert len(zone)==int(x[1])==m['mesh']['expected_rotating_cells']
rotating=cell_flags(owner,neighbour,zone);assert len(rotating)==m['mesh']['expected_cells']
selected=set(np.flatnonzero(rotating[owner[:len(neighbour)]]^rotating[neighbour]))
badpath=mesh/'sets/underdeterminedCells';bad=ascii_list(badpath.read_text()).astype(np.int64) if badpath.exists() else np.array([],dtype=np.int64)
lut=np.full(len(rotating),-1,dtype=np.int64);lut[bad]=np.arange(len(bad))
lows=np.full((len(bad),3),np.inf);highs=-lows.copy();normals=[];fluxes=[];lateral=cap=0;max_radius_error=0.
nodes=np.array(m['simplified_profile_nodes_mm']);seen=0
for i,face in enumerate(ascii_faces((mesh/'faces').read_text())):
    seen+=1
    if i in selected:
        p=points[list(face)];c,s=face_geometry(p);q=float(np.dot(np.cross([0,0,10471.975511966],c),s));normals.append(abs(q)/np.linalg.norm(s));fluxes.append(abs(q))
        if any(np.max(np.abs(p[:,2]-z))<1e-14 for z in (-.004,.033)):cap+=1
        else:
            lateral+=1;error=np.max(np.abs(np.linalg.norm(p[:,:2],axis=1)*1000-np.interp(p[:,2]*1000,nodes[:,0],nodes[:,1])))
            max_radius_error=max(max_radius_error,float(error))
    for cell in (owner[i],neighbour[i]) if i<len(neighbour) else (owner[i],):
        row=lut[cell]
        if row>=0:
            p=points[list(face)];lows[row]=np.minimum(lows[row],p.min(axis=0));highs[row]=np.maximum(highs[row],p.max(axis=0))
assert seen==len(owner) and len(normals)==len(selected) and cap and lateral
result=dict(source_sha256=sha(Path(__file__)),manifest_sha256=sha(case/'manifest.json'),receipt_sha256=sha(case/'report.json'),all_native_payloads_read_and_hashed=True,cells=len(rotating),rotating_cells=len(zone),interface_faces=len(selected),lateral_faces=lateral,cap_faces=cap,max_normal_frame_speed_m_s=max(normals),gross_geometric_frame_flux_m3_s=sum(fluxes),max_lateral_vertex_radius_error_mm=max_radius_error,mesh_gate_passed=r['mesh_gate_passed'],solver_admission_granted=False,physical_walls_meshed=False,performance_ranking_authorized=False)
if len(bad):
    assert np.isfinite(lows).all() and np.isfinite(highs).all()
    mid=(lows+highs)/2;radius=np.linalg.norm(mid[:,:2],axis=1)*1000
    dz=(highs[:,2]-lows[:,2])*1000
    result['rejected_cells']=dict(count=len(bad),bounds_m=[lows.min(axis=0).tolist(),highs.max(axis=0).tolist()],bbox_midpoint_radius_mm=[float(radius.min()),float(radius.max())],axial_width_mm=[float(dz.min()),float(dz.max())],all_outside_rotor_zone=bool(np.all(~rotating[bad])))
    csv=output.with_suffix('.cells.csv')
    with csv.open('x') as f:np.savetxt(f,np.column_stack((bad,lows,highs)),delimiter=',',header='cell,xmin_m,ymin_m,zmin_m,xmax_m,ymax_m,zmax_m',comments='',fmt=['%d']+['%.17g']*6)
    result['rejected_cell_bounds_sha256']=sha(csv)
with output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(result,indent=2),flush=True)
