"""Compare every physical node and every integration point against independent CCX."""
import hashlib,json
from pathlib import Path
import numpy as np
p=Path(__file__).parent;d=p/'adapted-n16';r=np.load(d/'result.npz');g=np.load(p/'n16-ccx-gold.npz');f=np.load(d/'fields.npz');stress=np.load(d/'stress-all-ip.npy',mmap_mode='r');perm=[0,1,2,3,5,4];ip=[0,4,2,6,1,5,3,7]
N=16;k,j,i=np.indices((N+1,)*3);xyz=np.column_stack([i.ravel(),j.ravel(),k.ravel()])/N;rows=[]
for mode in range(6):
 H=np.zeros((3,3))
 if mode<3:H[mode,mode]=.001
 else:
  a,b=[(0,1),(0,2),(1,2)][mode-3];H[a,b]=H[b,a]=.0005
 U=xyz@H.T-.001*f['xi'][:,:,perm[mode]]
 S=.001*stress[:,:,:,perm[mode]][:,ip,:][:,:,perm].reshape(-1,6)
 RF=.001*f['physical_forces'][:,:,perm[mode]]
 row=dict(mode=mode,physical_node_count=len(xyz),stress_integration_points=len(S),U_max_component_difference_mm=float(abs(U-g[f'displacements{mode}'][:len(xyz)]).max()),S_max_component_difference_MPa=float(abs(S-g[f'stresses{mode}']).max()),RF_max_component_difference_N=float(abs(RF-g[f'forces{mode}'][:len(xyz)]).max()));rows.append(row)
 assert row['U_max_component_difference_mm']<=1e-5 and row['S_max_component_difference_MPa']<=.01 and row['RF_max_component_difference_N']<=.01,row
C=r['CH'][np.ix_(perm,perm)];error=float(np.linalg.norm(C-g['C'])/np.linalg.norm(g['C']));assert error<=1e-5
report=dict(status='six_complete_CCX_field_crosschecks_passed',cases=rows,relative_tensor_difference=error,gold_sha256=hashlib.sha256((p/'n16-ccx-gold.npz').read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),stress_ip_mapping=ip,shear_mapping=perm,criteria_changed=False)
(p/'n16-crosscheck.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
