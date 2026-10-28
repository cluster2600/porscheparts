"""Search interior cavity point placement against finite-volume quality; retain exact boundaries."""
from collections import Counter
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
import scipy
from scipy.optimize import differential_evolution,LinearConstraint
import rebuild_fluid_edge_stars as kernel
from rebuild_fluid_edge_stars import base,kernel_proposal,positive_partition


def search_placement(vertices,cells,initial,proposal,outside,centres,volumes,before):
    target,children,ids,local_cells=proposal
    origin=initial;scale=float(np.ptp(vertices[ids],axis=0).max())
    local=np.vstack([vertices[ids],initial]);normalized=(local-origin)/scale
    faces=normalized[local_cells[:,1:]]
    normals=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    rhs=np.einsum('ij,ij->i',normals,faces[:,0]);assert np.all(rhs>0)
    local_outside={tuple(np.searchsorted(ids,face)):neighbour for face,neighbour in outside.items()}
    counts=[];best=None;exact_refused=0;original=vertices[ids].copy()
    severity_scale=1+before[1]
    def objective(x):
        nonlocal best,exact_refused
        point=origin+scale*x;local[-1]=point
        try:after=base.patch_quality(local,local_cells,local_outside,centres,volumes)
        except ValueError:return 1e12
        counts.append(after[0].tolist())
        if base.improves(before,after):
            priority=(int(after[0][-1]),int(after[0].sum()),float(after[1].sum()))
            if best is None or priority<best[0]:
                if positive_partition(vertices,cells,point,children,ids,local_cells):
                    best=(priority,point.copy(),'direct_FV_search',after)
                else:exact_refused+=1
        excess=np.maximum((after[1]-before[1])/severity_scale,0)
        return float((after[1]/severity_scale).sum()+1000*excess.sum()+100*np.maximum(after[0]-before[0],0).sum())
    for fraction in [0.,1.,.75,.5,.25]:objective(fraction*(target-origin)/scale)
    # shortcut: one seeded 256-evaluation search per cavity; widen only after a complete native audit.
    result=differential_evolution(objective,list(zip(normalized[:-1].min(axis=0),normalized[:-1].max(axis=0))),constraints=LinearConstraint(normals,-np.inf,rhs),x0=(target-origin)/scale,rng=0,maxiter=15,popsize=5,init='sobol',polish=False,tol=0,atol=0,workers=1)
    assert result.nfev<=256 and np.array_equal(local[:-1],original)
    return best,counts,{'DE_objective_evaluations':int(result.nfev),'generations':int(result.nit),'DE_success':bool(result.success),'DE_message':str(result.message),'total_quality_evaluations':len(counts),'exact_partition_refusals':exact_refused}


def self_test():
    kernel.self_test()
    for scale,origin in [(1.,np.zeros(3)),(.001,np.array([.2,-.3,.4]))]:
        vertices=origin+scale*np.array([[0.,0,-1],[0,0,1],[1,0,0],[-.5,np.sqrt(3)/2,0],[-.5,-np.sqrt(3)/2,0]])
        cells=np.array([[0,1,2,3],[0,1,3,4],[0,1,4,2]])
        initial=(vertices[0]+vertices[1])/2;proposal=kernel_proposal(vertices,cells,initial)
        outside={tuple(face):-1 for face in base.outer_faces(cells)}
        before=base.patch_quality(vertices,cells,outside,np.empty((0,3)),np.empty(0))
        best,counts,stats=search_placement(vertices,cells,initial,proposal,outside,np.empty((0,3)),np.empty(0),before)
        assert best is not None and base.improves(before,best[-1]) and before[0][-1]==3 and best[-1][0][-1]==0
        assert stats['DE_objective_evaluations']<=256 and len(counts)<=261
    print('Direct finite-volume placement controls passed',flush=True)


def run(audited,limit,out):
    audited,out=Path(audited),Path(out);limit=int(limit)
    if not 1<=limit<=512:raise ValueError('Edge sample bound must be between 1 and 512')
    if out.exists():raise ValueError('Fresh private output required')
    sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
    proof=json.loads((audited/'assessment.json').read_text())
    assert proof['volume_npz_sha256']==sha(audited/'volume.npz') and proof['exact_PLC_volume_equal']
    assert proof['complete_boundary_coordinate_triangle_marker_bijection']
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
        best,counts_for_trials,search=search_placement(vertices,cells[parent_ids],initial,proposal,outside,centres,volumes,before)
        detail.append({'source_cells':len(parent_ids),'before_counts':before[0].tolist(),'trial_counts':counts_for_trials,'accepted':best is not None,'search':search})
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
    report={'status':'kernel_star_candidate_pending_complete_independent_audits','source_sha256':sha(__file__),'helper_sha256':{'reconnect_fluid_tetrahedra.py':sha(base.__file__),'optimize_interior_stars.py':sha(optimize_interior_stars.__file__),'rebuild_fluid_edge_stars.py':sha(kernel.__file__)},'parent_assessment_sha256':sha(audited/'assessment.json'),'eligible_internal_edges':len(eligible),'sampled_edges':len(chosen),'sample_selection':'index_stratified_without_replacement','maximum_edge_valence':32,'optimizer':{'method':'SciPy_differential_evolution','maxiter':15,'popsize':5,'initialization':'sobol','rng':0,'workers':1,'polish':False,'maximum_DE_objective_evaluations':256},'decisions':dict(decisions),'detail':detail,'input_vertices':len(vertices),'output_vertices':len(result_vertices),'input_cells':len(cells),'output_cells':len(result_cells),'original_vertices_unchanged':True,'boundary_triangles_and_markers_unchanged':True,'candidate_sha256':sha(out/'candidate.npz'),'elapsed_s':time.monotonic()-started,'NumPy':np.__version__,'SciPy':scipy.__version__,'CFD_accepted':False,'manufacturing_authorized':False}
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='detail'}),flush=True)


if __name__=='__main__':
    self_test()
    if sys.argv[1:]!=['--self-test']:run(*sys.argv[1:])
