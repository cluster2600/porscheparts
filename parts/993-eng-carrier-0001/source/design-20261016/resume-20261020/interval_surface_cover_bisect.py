"""Resume the reverse cover using cached queries and recorded binary bisections.

The already complete forward cover is reused by hash, not recalculated. The
same outward interval/convex-distance predicate remains fixed at 0.06 mm.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def split(lo,hi,edge,np):
    n=len(lo);row=np.arange(n);i=edge;j=(edge+1)%3;k=(edge+2)%3
    ml=np.nextafter(np.nextafter(lo[row,i]+lo[row,j],-np.inf)/2,-np.inf);mh=np.nextafter(np.nextafter(hi[row,i]+hi[row,j],np.inf)/2,np.inf)
    def expand(v,m):return np.stack([np.stack([v[row,i],m,v[row,k]],axis=1),np.stack([m,v[row,j],v[row,k]],axis=1)],axis=1).reshape(-1,3,3)
    return expand(lo,ml),expand(hi,mh)


def binary_coverage(face,path,depth,history,nfaces,np):
    maximum=int(depth.max());shift=(maximum-depth.astype(np.int64)).astype(np.uint64);lo=path<<shift;hi=(path+1)<<shift;order=np.lexsort((lo,face));ff=face[order];ll=lo[order];hh=hi[order];dd=depth[order].astype(np.int64);ee=history[order]
    first=np.r_[True,ff[1:]!=ff[:-1]];last=np.r_[ff[:-1]!=ff[1:],True];same=ff[1:]==ff[:-1];end=np.uint64(1)<<np.uint64(maximum)
    if not(np.array_equal(ff[first],np.arange(nfaces,dtype=np.uint32))and np.all(ll[first]==0)and np.all(hh[last]==end)and np.all(ll[1:][same]==hh[:-1][same])):return False
    if np.any(same):
        # Normalized binary addresses fit <=24 bits, exactly representable in
        # binary64; frexp's exponent is their exact integer bit length.
        xor=(ll[:-1]^ll[1:])[same];lengths=np.frexp(xor.astype(np.float64))[1];common=maximum-lengths;levels=common+1;a=dd[:-1][same];b=dd[1:][same]
        if np.any(levels>a)or np.any(levels>b):return False
        left=ee[:-1][same]>>((a-levels)*2).astype(np.uint64);right=ee[1:][same]>>((b-levels)*2).astype(np.uint64)
        if not np.array_equal(left,right):return False
    return True


class CachedQueries:
    def __init__(self,igl):self.igl=igl;self.v=None;self.f=None;self.tree=None
    def point_mesh_squared_distance(self,points,v,f):
        if self.v is not v or self.f is not f:self.tree=self.igl.AABB();self.tree.init(v,f);self.v=v;self.f=f
        return self.tree.squared_distance(v,f,points)


def cover(v,f,tv,tf,out,np,query,core,maxdepth=24,maxleaves=20000000):
    lo=v[f].copy();hi=lo.copy();face=np.arange(len(f),dtype=np.uint32);path=np.zeros(len(face),dtype=np.uint64);history=path.copy();saved={k:[]for k in ['face','path','depth','edge_history','target','weights','upper_squared']};limit=np.nextafter(.06*.06,-np.inf);start=time.monotonic();total=0
    for depth in range(maxdepth+1):
        failed=[]
        for begin in range(0,len(face),131072):
            end=min(begin+131072,len(face));l=lo[begin:end];h=hi[begin:end];points=(l+h)/2;_,target,_=query.point_mesh_squared_distance(points.mean(1),tv,tf);target=np.asarray(target,dtype=np.uint32);triangles=tv[tf[target]];weights=np.stack([core.convex_weights(points[:,i],triangles,np)for i in range(3)],axis=1);bound=core.witness_bound_squared(l,h,triangles,weights,np);passed=np.isfinite(bound)&(bound<=limit);count=int(passed.sum());total+=count
            if count:
                for key,value in [('face',face[begin:end]),('path',path[begin:end]),('depth',np.full(end-begin,depth,dtype=np.uint8)),('edge_history',history[begin:end]),('target',target),('weights',weights),('upper_squared',bound)]:saved[key].append(value[passed].copy())
            if not np.all(passed):failed.append(np.flatnonzero(~passed)+begin)
        unresolved=np.concatenate(failed)if failed else np.empty(0,dtype=np.int64)
        if out:(out/'reverse-progress.json').write_text(json.dumps(dict(depth=depth,accepted_leaves=total,unresolved=len(unresolved),elapsed_seconds=time.monotonic()-start))+'\n')
        if not len(unresolved):
            del lo,hi,face,path,history
            data={k:np.concatenate(value)for k,value in saved.items()}
            if not binary_coverage(data['face'],data['path'],data['depth'],data['edge_history'],len(f),np):raise ValueError('Complete binary partition/edge history refused')
            if out:np.savez_compressed(out/'second-to-first-binary-cover.npz',**data)
            return dict(passed=True,source_triangles=len(f),target_triangles=len(tf),leaves=total,deepest_level=depth,exact_binary_partition=True,recorded_edge_choices_consistent=True,maximum_outward_squared_distance_mm2=float(data['upper_squared'].max()),certified_distance_upper_mm=float(np.nextafter(np.sqrt(data['upper_squared'].max()),np.inf)),elapsed_seconds=time.monotonic()-start)
        if depth==maxdepth or total+2*len(unresolved)>maxleaves:return dict(passed=False,reason='unresolved_binary_cover_at_resource_bound',depth=depth,accepted_leaves=total,unresolved=len(unresolved),elapsed_seconds=time.monotonic()-start)
        lo=lo[unresolved];hi=hi[unresolved];mid=(lo+hi)/2;edge=np.argmax(np.stack([np.sum((mid[:,i]-mid[:,j])**2,axis=1)for i,j in [(0,1),(1,2),(2,0)]],axis=1),axis=1).astype(np.uint64)
        lo,hi=split(lo,hi,edge.astype(np.int64),np);face=np.repeat(face[unresolved],2);path=np.repeat(path[unresolved]*2,2)+np.tile(np.arange(2,dtype=np.uint64),len(unresolved));history=np.repeat(history[unresolved]*4+edge,2)
    raise AssertionError('Coverage loop fell through')


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--first',type=Path,required=True);p.add_argument('--second',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import igl
    core_path=Path(__file__).with_name('interval_surface_cover.py');spec=importlib.util.spec_from_file_location('_unchanged_interval_core',core_path);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);query=CachedQueries(igl)
    def read(path):
        with path.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
        if v.shape!=(nv,3)or f.shape!=(nf,3)or not np.isfinite(v).all():raise ValueError('Complete finite source rosters required')
        return v,f
    v1,f1=read(a.first);v2,f2=read(a.second);reuse=Path('/reuse');record=json.loads((reuse/'assessment.json').read_text());proof=reuse/'first-to-second-cover.npz'
    if sha(a.first)!=record['source_sha256']['/input/first.mesh64']or sha(a.second)!=record['source_sha256']['/input/second.mesh64']or sha(core_path)!=record['source_sha256']['/source/worker.py']or sha(proof)!=record['output_sha256'][proof.name]:raise ValueError('Immutable forward proof/source identities differ')
    if not record['directions']['first-to-second']['passed']or record['fixed_distance_limit_mm']!=.06:raise ValueError('Complete matching forward proof required')
    with np.load(proof,allow_pickle=False)as data:
        face=data['face'];path=data['path'];depth=data['depth'];upper=data['upper_squared']
        if not core.coverage(face,path,depth,len(f1),int(depth.max()),np)or not np.all(np.isfinite(upper)&(upper<=np.nextafter(.06*.06,-np.inf))):raise ValueError('Reused complete forward roster/bounds refused')
    del face,path,depth,upper
    cv=np.array([[0,0,0],[1,0,0],[1,1,1],[0,1,0]],dtype=np.float64);ca=np.array([[0,1,2],[0,2,3]]);cb=np.array([[0,1,3],[1,2,3]]);planar=cv.copy();planar[:,2]=0
    positive=cover(planar,ca,planar,cb,None,np,query,core,maxdepth=12,maxleaves=10000);negative=cover(cv,ca,cv,cb,None,np,query,core,maxdepth=8,maxleaves=10000)
    if not positive['passed']or negative['passed']:raise ValueError('Binary full-interior controls refused')
    reverse=cover(v2,f2,v1,f1,a.output,np,query,core);passed=reverse['passed'];report=dict(status='complete_interval_surface_distance_certified'if passed else'complete_surface_distance_not_certified',fixed_distance_limit_mm=.06,first_to_second=record['directions']['first-to-second'],second_to_first=reverse,forward_proof_reused_without_recomputation=True,reused_forward_proof_sha256=sha(proof),reused_forward_record_sha256=sha(reuse/'assessment.json'),reused_forward_full_quadtree_and_bounds_verified=True,analytic_controls=dict(planar_retriangulation=positive,same_vertices_different_interior=negative),interval_predicate_unchanged=True,source_sha256={str(p):sha(p)for p in [a.first,a.second,core_path,Path(__file__)]},output_sha256={p.name:sha(p)for p in a.output.glob('*cover.npz')},geometry_adopted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],second_to_first=reverse)));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
