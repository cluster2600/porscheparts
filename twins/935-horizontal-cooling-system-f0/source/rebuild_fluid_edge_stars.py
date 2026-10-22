"""Probe interior-edge star replacement with the existing normalized LP kernel."""
from collections import Counter
from fractions import Fraction
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
import scipy
import reconnect_fluid_tetrahedra as base
from import_conforming_volume import exact_orientation
from optimize_interior_stars import kernel_target

def outer_oriented(cells):
    oriented=cells[:,base.FACE_NODES].reshape(-1,3)
    _,first,count=np.unique(np.sort(oriented,axis=1),axis=0,return_index=True,return_counts=True)
    if np.any(count>2):raise ValueError('Manifold cavity required')
    return oriented[first[count==1]]

def kernel_proposal(vertices,cells,initial):
    ids=np.unique(cells);node=len(vertices);faces=outer_oriented(cells)
    children=np.column_stack([np.full(len(faces),node,dtype=np.int64),faces])
    if not np.array_equal(base.outer_faces(cells),base.outer_faces(children)):
        raise ValueError('Cavity boundary changed')
    local_ids=np.r_[ids,node];local_cells=np.searchsorted(local_ids,children)
    global_points=np.vstack([vertices[ids],initial]);origin=global_points[:-1].mean(axis=0)
    scale=float(np.ptp(global_points[:-1],axis=0).max())
    if not scale>0:raise ValueError('Positive normalization scale required')
    initial_proof=exact_orientation(global_points,local_cells)
    if initial_proof['negative'] or initial_proof['zero']:return None
    normalized=(global_points-origin)/scale
    target=kernel_target(normalized,local_cells,len(ids))
    if target is None:return None
    return origin+scale*target,children,ids,local_cells

def positive_partition(vertices,cells,point,children,ids,local_cells):
    local=np.vstack([vertices[ids],point]);new=exact_orientation(local,local_cells)
    old=exact_orientation(vertices[ids],np.searchsorted(ids,cells))
    if old['negative'] or old['zero']:raise ValueError('Positive parent cavity required')
    return (not new['negative'] and not new['zero']
            and Fraction(new['signed_volume_exact'])==Fraction(old['signed_volume_exact']))

def self_test():
    for scale,origin in [(1.,np.zeros(3)),(.001,np.array([.2,-.3,.4]))]:
        vertices=origin+scale*np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        cells=np.array([[0,1,2,3]])
        result=kernel_proposal(vertices,cells,vertices.mean(axis=0));assert result is not None
        point,children,ids,local_cells=result
        radius=(3-np.sqrt(3))/6
        assert np.allclose(point,origin+scale*radius,rtol=0,atol=1e-12*scale)
        assert positive_partition(vertices,cells,point,children,ids,local_cells)
        assert kernel_proposal(vertices,cells,vertices[0]) is None
    print('Unit and translated millimetre-scale kernel controls passed',flush=True)

def run(audited,limit,out):
    audited,out=Path(audited),Path(out);limit=int(limit)
    if not 1<=limit<=5000:raise ValueError('Edge sample bound must be between 1 and 5000')
    if out.exists():raise ValueError('Fresh private output required')
    sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
    proof=json.loads((audited/'assessment.json').read_text())
    assert proof['volume_npz_sha256']==sha(audited/'volume.npz') and proof['exact_PLC_volume_equal']
    assert not proof['exact_cell_orientation']['negative'] and not proof['exact_cell_orientation']['zero']
    z=np.load(audited/'volume.npz');vertices=z['vertices'];cells=z['tetrahedra']
    assert 0<len(cells)<=2_000_000 and 0<len(vertices)<=1_000_000
    out.mkdir(mode=0o700);started=time.monotonic()
    rows,owners,cell_faces=base.incidence(cells)
    bad=(owners[cell_faces,1]<0).sum(axis=1)>=2
    centres=vertices[cells].mean(axis=1);xyz=vertices[cells]
    volumes=np.einsum('ij,ij->i',xyz[:,1]-xyz[:,0],np.cross(xyz[:,2]-xyz[:,0],xyz[:,3]-xyz[:,0]))/6
    edges=np.sort(cells[:,base.EDGE_NODES].reshape(-1,2),axis=1);keys=edges[:,0]*len(vertices)+edges[:,1]
    order=np.argsort(keys,kind='stable');sorted_keys=keys[order]
    wanted=np.unique(keys.reshape(-1,6)[bad].ravel())
    left=np.searchsorted(sorted_keys,wanted);right=np.searchsorted(sorted_keys,wanted,side='right')
    bf=z['boundary'];be=np.sort(bf[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1)
    boundary_keys=np.unique(be[:,0]*len(vertices)+be[:,1])
    eligible=wanted[(right-left>=3)&(right-left<=32)&(~np.isin(wanted,boundary_keys))]
    chosen=eligible[np.linspace(0,len(eligible)-1,min(limit,len(eligible)),dtype=int)] if len(eligible) else eligible
    reserved=np.zeros(len(cells),dtype=bool);removed=reserved.copy();added=[];points=[];decisions=Counter();detail=[]
    for key in chosen:
        lo=np.searchsorted(sorted_keys,key);hi=np.searchsorted(sorted_keys,key,side='right');parent_ids=order[lo:hi]//6
        face_ids=np.unique(cell_faces[parent_ids]);region=np.unique(owners[face_ids]);region=region[region>=0]
        if reserved[region].any():decisions['reserved_neighbourhood']+=1;continue
        edge=(int(key//len(vertices)),int(key%len(vertices)));initial=vertices[list(edge)].mean(axis=0)
        proposal=kernel_proposal(vertices,cells[parent_ids],initial)
        if proposal is None:decisions['no_positive_kernel_proposal']+=1;continue
        target,children,ids,local_cells=proposal;outside={}
        for fid in face_ids:
            other=set(map(int,owners[fid]))-set(map(int,parent_ids))
            if other:
                assert len(other)==1;outside[tuple(rows[fid])]=other.pop()
        before=base.patch_quality(vertices,cells[parent_ids],outside,centres,volumes)
        best=None;counts_for_trials=[]
        for fraction in [1.,.75,.5,.25]:
            point=initial+fraction*(target-initial)
            if not positive_partition(vertices,cells[parent_ids],point,children,ids,local_cells):
                decisions['trial_not_exact_positive_partition']+=1;continue
            extended=np.vstack([vertices,point]);after=base.patch_quality(extended,children,outside,centres,volumes)
            counts_for_trials.append(after[0].tolist())
            if not base.improves(before,after):continue
            priority=(int(after[0][-1]),int(after[0].sum()),float(after[1].sum()))
            if best is None or priority<best[0]:best=(priority,point.copy(),fraction,after)
        detail.append({'source_cells':len(parent_ids),'before_counts':before[0].tolist(),'trial_counts':counts_for_trials,'accepted':best is not None})
        if best is None:decisions['no_monotone_FV_trial']+=1;continue
        _,point,fraction,after=best
        result=children.copy();result[result==len(vertices)]=len(vertices)+len(points)
        added.append(result);points.append(point);removed[parent_ids]=True;reserved[region]=True
        decisions['accepted_disjoint_star']+=1
    result_cells=np.vstack([cells[~removed],*added]) if added else cells.copy()
    result_vertices=np.vstack([vertices,*points]) if points else vertices.copy()
    assert np.array_equal(result_vertices[:len(vertices)],vertices)
    np.savez_compressed(out/'candidate.npz',vertices=result_vertices,tetrahedra=result_cells,boundary=z['boundary'],markers=z['markers'])
    import optimize_interior_stars
    report={'status':'kernel_star_candidate_pending_complete_independent_audits','source_sha256':sha(__file__),'helper_sha256':{'reconnect_fluid_tetrahedra.py':sha(base.__file__),'optimize_interior_stars.py':sha(optimize_interior_stars.__file__)},'parent_assessment_sha256':sha(audited/'assessment.json'),'eligible_internal_edges':len(eligible),'sampled_edges':len(chosen),'sample_selection':'index_stratified_without_replacement','maximum_edge_valence':32,'fixed_trial_fractions':[1.,.75,.5,.25],'decisions':dict(decisions),'detail':detail,'input_vertices':len(vertices),'output_vertices':len(result_vertices),'input_cells':len(cells),'output_cells':len(result_cells),'original_vertices_unchanged':True,'boundary_triangles_and_markers_unchanged':True,'candidate_sha256':sha(out/'candidate.npz'),'elapsed_s':time.monotonic()-started,'NumPy':np.__version__,'SciPy':scipy.__version__,'CFD_accepted':False,'manufacturing_authorized':False}
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='detail'}),flush=True)

if __name__=='__main__':
    self_test()
    if sys.argv[1:]!=['--self-test']:run(*sys.argv[1:])
