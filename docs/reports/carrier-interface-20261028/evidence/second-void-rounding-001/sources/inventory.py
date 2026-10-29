"""Inventory all eight frozen source voids before extending the rounding route."""
from pathlib import Path
import hashlib
import importlib.util
import json
import numpy as np

root=Path(__file__).resolve().parent
source=Path('parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/audit_void_material_side.py').resolve()
spec=importlib.util.spec_from_file_location('material_auditor',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
w=Path('/Users/maxime/.codex/worktrees/993-carrier-revalidation/3dprinting993/work/carrier-interface-20261028')
rows=[]
for rank in range(4):
    directory=w/f'meshlib-seed-p10-r{rank}-h0125-004'
    meta=directory/'assessment.json'; assessment=json.loads(meta.read_text())
    for item in assessment['selected']:
        path=directory/item['file']; digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==item['sha256']
        with np.load(path,allow_pickle=False)as z:
            v=z['vertices'];f=z['triangles']
            assert len(v)==item['vertices'] and len(f)==item['triangles']
            t=v[f]; volume=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
            assert abs(volume-item['volume_mm3'])<1e-6
            result=module.audit_material_side(v,f)
            row=dict(rank=rank,branch=item['branch'],input=str(path),input_sha256=digest,metadata_sha256=hashlib.sha256(meta.read_bytes()).hexdigest(),vertices=len(v),triangles=len(f),bbox_mm=[v.min(0).tolist(),v.max(0).tolist()],signed_volume_mm3=volume,nominal_displaced_titanium_grams=volume*.00442,material_side=result)
        rows.append(row)
        print(json.dumps({k:row[k]for k in ['rank','branch','triangles','signed_volume_mm3']}),flush=True)
report=dict(status='all_eight_source_void_features_inventoried',scope='Upstream feature inventory, not complete embedding or functional admission',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),numpy_version=np.__version__,rows=rows,total_void_volume_mm3=sum(x['signed_volume_mm3']for x in rows),manufacturing_authorized=False)
assert not (root/'assessment.json').exists()
(root/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
