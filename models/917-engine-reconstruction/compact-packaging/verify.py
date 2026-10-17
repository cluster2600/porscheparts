"""Screen every changed cover against posed inherited families at the cold state."""
from collections import defaultdict
import numpy as np
import trimesh
import study
from reconstruct import save


def run(output,meshes,rows,native):
    grouped=defaultdict(list)
    for r in rows:grouped[r['family']].append(r)
    new=[n for n in meshes if n.startswith(('bank_valve_cover_','bank_adapter_'))]
    checks=[]
    def check(label,a,b,members):
        hit=study.contact(a,b)
        checks.append({'group':label,'volume_mm3':hit['volume_mm3'],'passed':hit['volume_mm3']==0,'method':hit['method'],'members':members})
        print('CHECK '+label+' '+str(hit['volume_mm3']),flush=True)
    for name in new:
        body=meshes[name]
        for family,group in sorted(grouped.items()):
            if family==name or (family in new and family<name):continue
            posed=[];members=[]
            for row in group:
                matrix=np.asarray(row['matrix_mm']);lo,hi=meshes[family].bounds
                corners=np.array([[x,y,z,1] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])@matrix.T
                if np.any(corners[:,:3].max(axis=0)<body.bounds[0]) or np.any(corners[:,:3].min(axis=0)>body.bounds[1]):continue
                m=meshes[family].copy();m.apply_transform(matrix);posed.append(m);members.append(row['instance_id'])
            if posed:check(name+'/'+family,body,trimesh.util.concatenate(posed),members)
            else:checks.append({'group':name+'/'+family,'passed':True,'method':'disjoint_transformed_AABB','members':[]})
    for suffix in ('negative','positive'):
        charge=meshes['charge_pipe_'+suffix]
        for family in ['drive_housing','drive_cover','drive_bionic_frame']+new:
            check('charge_pipe_'+suffix+'/'+family,charge,meshes[family],[])
    reserves={n:m for n,m in native.items() if n.startswith('bank_cam_reserve_')}
    for name,reserve in reserves.items():
        suffix='negative' if '_negative_' in name else 'positive'
        for family in ('bank_valve_cover_','bank_adapter_'):check('cam_rotation/'+name+'/'+family,reserve,meshes[family+suffix],[])
    result={'checks':checks,'passed':all(r['passed'] for r in checks),'changed_covers_against_all_posed_families':True,
            'cam_rotation_envelopes_checked':len(reserves)==4,
            'unchanged_pairs_retested':False,'full_assembly_interference_checked':False,'thermal_or_fatigue_validated':False,
            'material_qualified':False,'manufacturing_authorized':False,'engine_start_authorized':False}
    save(output/'verification.json',result)
    if not result['passed']:raise ValueError('Changed cover or pipe contacts rejected; preserve output')
    return result
