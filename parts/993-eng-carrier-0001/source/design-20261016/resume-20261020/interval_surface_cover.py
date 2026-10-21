"""Complete two-sided surface cover with outward-rounded convex witnesses.

libigl chooses a candidate triangle only. Each admitted leaf independently
bounds all three true source vertices against convex combinations inside one
actual target triangle. Convexity covers the whole leaf. Exact quadtree address
coverage checks exclude missing triangles. No sampled-point result admits a mesh.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

DEN=2**24


def convex_weights(points,triangles,np):
    """Heuristic candidates; quantized nonnegative weights always sum to DEN."""
    a=triangles[:,0];b=triangles[:,1];c=triangles[:,2];ab=b-a;ac=c-a;delta=points-a
    aa=np.sum(ab*ab,axis=1);bb=np.sum(ac*ac,axis=1);dot=np.sum(ab*ac,axis=1);pa=np.sum(delta*ab,axis=1);pb=np.sum(delta*ac,axis=1);det=aa*bb-dot*dot
    safe=np.where(det>0,det,1.);u=(pa*bb-pb*dot)/safe;v=(pb*aa-pa*dot)/safe;plane=np.maximum(np.stack([1-u-v,u,v],axis=1),0.);total=plane.sum(1);plane/=np.where(total>0,total,1.)[:,None]
    options=[plane]
    for i,j in [(0,1),(1,2),(2,0)]:
        edge=triangles[:,j]-triangles[:,i];norm=np.sum(edge*edge,axis=1);t=np.clip(np.sum((points-triangles[:,i])*edge,axis=1)/np.where(norm>0,norm,1.),0.,1.);w=np.zeros_like(plane);w[:,i]=1-t;w[:,j]=t;options.append(w)
    candidates=np.stack(options,axis=1);locations=np.sum(candidates[:,:,:,None]*triangles[:,None,:,:],axis=2);cost=np.sum((locations-points[:,None,:])**2,axis=2);selected=candidates[np.arange(len(points)),np.argmin(cost,axis=1)]
    first=np.clip(np.floor(selected[:,0]*DEN),0,DEN).astype(np.uint32);second=np.minimum(np.clip(np.floor(selected[:,1]*DEN),0,DEN).astype(np.uint32),DEN-first);third=np.uint32(DEN)-first-second
    return np.stack([first,second,third],axis=1)


def witness_bound_squared(source_lo,source_hi,target_triangles,weights,np):
    """Every arithmetic operation is separately widened by one binary64 ULP."""
    qlo=np.zeros_like(source_lo);qhi=np.zeros_like(source_hi)
    # source arrays: leaf, source vertex, XYZ; weights: leaf, source vertex, target vertex
    for j in range(3):
        product=weights[:,:,j,None].astype(np.float64)*target_triangles[:,None,j,:]
        qlo=np.nextafter(qlo+np.nextafter(product,-np.inf),-np.inf)
        qhi=np.nextafter(qhi+np.nextafter(product,np.inf),np.inf)
    qlo=np.nextafter(qlo/DEN,-np.inf);qhi=np.nextafter(qhi/DEN,np.inf)
    dlo=np.nextafter(source_lo-qhi,-np.inf);dhi=np.nextafter(source_hi-qlo,np.inf);absolute=np.maximum(np.abs(dlo),np.abs(dhi));squared=np.zeros(source_lo.shape[:2])
    for axis in range(3):squared=np.nextafter(squared+np.nextafter(absolute[:,:,axis]*absolute[:,:,axis],np.inf),np.inf)
    return squared.max(axis=1)


def children(lo,hi,np):
    midlo=[np.nextafter(np.nextafter(lo[:,i]+lo[:,j],-np.inf)/2,-np.inf)for i,j in [(0,1),(1,2),(2,0)]]
    midhi=[np.nextafter(np.nextafter(hi[:,i]+hi[:,j],np.inf)/2,np.inf)for i,j in [(0,1),(1,2),(2,0)]]
    def expand(v,m):return np.stack([np.stack([v[:,0],m[0],m[2]],axis=1),np.stack([m[0],v[:,1],m[1]],axis=1),np.stack([m[2],m[1],v[:,2]],axis=1),np.stack([m[0],m[1],m[2]],axis=1)],axis=1).reshape(-1,3,3)
    return expand(lo,midlo),expand(hi,midhi)


def coverage(face,path,depth,nfaces,maxdepth,np):
    shift=(2*(maxdepth-depth.astype(np.int64))).astype(np.uint64);lo=path<<shift;hi=(path+1)<<shift;order=np.lexsort((lo,face));ff=face[order];ll=lo[order];hh=hi[order]
    first=np.r_[True,ff[1:]!=ff[:-1]];last=np.r_[ff[:-1]!=ff[1:],True];same=~first[1:];end=np.uint64(1)<<np.uint64(2*maxdepth)
    return bool(np.array_equal(ff[first],np.arange(nfaces,dtype=np.uint32))and np.all(ll[first]==0)and np.all(hh[last]==end)and np.all(ll[1:][same]==hh[:-1][same]))


def cover(source_v,source_f,target_v,target_f,limit,out,side,np,igl,maxdepth=12,maxleaves=20000000):
    lo=source_v[source_f].copy();hi=lo.copy();face=np.arange(len(source_f),dtype=np.uint32);path=np.zeros(len(face),dtype=np.uint64);saved={k:[]for k in ['face','path','depth','target','weights','upper_squared']};threshold=np.nextafter(limit*limit,-np.inf);start=time.monotonic();total=0
    for depth in range(maxdepth+1):
        failed=[]
        for begin in range(0,len(face),131072):
            end=min(begin+131072,len(face));l=lo[begin:end];h=hi[begin:end];points=(l+h)/2;centres=points.mean(1);_,target_ids,_=igl.point_mesh_squared_distance(centres,target_v,target_f);target_ids=np.asarray(target_ids,dtype=np.uint32);triangles=target_v[target_f[target_ids]]
            weights=np.stack([convex_weights(points[:,i],triangles,np)for i in range(3)],axis=1);bound=witness_bound_squared(l,h,triangles,weights,np);passed=np.isfinite(bound)&(bound<=threshold);count=int(passed.sum());total+=count
            if count:
                for key,value in [('face',face[begin:end]),('path',path[begin:end]),('depth',np.full(end-begin,depth,dtype=np.uint8)),('target',target_ids),('weights',weights),('upper_squared',bound)]:saved[key].append(value[passed].copy())
            if not np.all(passed):failed.append(np.flatnonzero(~passed)+begin)
        unresolved=np.concatenate(failed)if failed else np.empty(0,dtype=np.int64)
        if out:(out/(side+'-progress.json')).write_text(json.dumps(dict(depth=depth,accepted_leaves=total,unresolved=len(unresolved),elapsed_seconds=time.monotonic()-start))+'\n')
        if not len(unresolved):
            data={key:np.concatenate(value)for key,value in saved.items()};complete=coverage(data['face'],data['path'],data['depth'],len(source_f),maxdepth,np)
            if not complete:raise ValueError('Exact quadtree coverage roster refused')
            if out:np.savez_compressed(out/(side+'-cover.npz'),**data)
            return dict(passed=True,source_triangles=len(source_f),target_triangles=len(target_f),leaves=total,deepest_level=depth,exact_quadtree_coverage=True,maximum_outward_squared_distance_mm2=float(data['upper_squared'].max()),certified_distance_upper_mm=float(np.nextafter(np.sqrt(data['upper_squared'].max()),np.inf)),elapsed_seconds=time.monotonic()-start)
        if depth==maxdepth or total+4*len(unresolved)>maxleaves:return dict(passed=False,reason='unresolved_cover_at_resource_bound',depth=depth,accepted_leaves=total,unresolved=len(unresolved),elapsed_seconds=time.monotonic()-start)
        lo,hi=children(lo[unresolved],hi[unresolved],np);face=np.repeat(face[unresolved],4);path=np.repeat(path[unresolved]*4,4)+np.tile(np.arange(4,dtype=np.uint64),len(unresolved))
    raise AssertionError('Coverage loop fell through')


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--first',type=Path,required=True);p.add_argument('--second',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic()
    import numpy as np
    import igl
    def read(path):
        with path.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
        if v.shape!=(nv,3)or f.shape!=(nf,3)or not np.isfinite(v).all():raise ValueError('Whole finite indexed meshes required')
        return v,f
    # Identity and same-vertex/different-interior adversarial controls.
    cv=np.array([[0,0,0],[1,0,0],[1,1,1],[0,1,0]],dtype=np.float64);ca=np.array([[0,1,2],[0,2,3]]);cb=np.array([[0,1,3],[1,2,3]])
    identity=cover(cv,ca,cv,ca,.06,None,'identity',np,igl,maxdepth=4,maxleaves=10000)
    interior=cover(cv,ca,cv,cb,.06,None,'interior',np,igl,maxdepth=4,maxleaves=10000)
    if not identity['passed']or interior['passed']:raise ValueError('Whole-interior control refused')
    v1,f1=read(a.first);v2,f2=read(a.second);results={}
    for side,sv,sf,tv,tf in [('first-to-second',v1,f1,v2,f2),('second-to-first',v2,f2,v1,f1)]:
        results[side]=cover(sv,sf,tv,tf,.06,a.output,side,np,igl)
        if not results[side]['passed']:break
    passed=len(results)==2 and all(r['passed']for r in results.values())
    report=dict(status='complete_interval_surface_distance_certified'if passed else'complete_surface_distance_not_certified',fixed_distance_limit_mm=.06,interval_arithmetic='Each binary64 scalar multiply/add/subtract/divide/square is separately widened with nextafter; source subdivision coordinates enclosed recursively',convex_weight_denominator=DEN,libigl_role='Candidate triangle heuristic only; never an admission distance',whole_triangle_argument='All three true source vertices are within the admitted distance of points in one convex target triangle; affine convex combinations cover each whole source leaf',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.first,a.second,Path(__file__)]},analytic_controls=dict(identity=identity,same_vertices_different_interior=interior),directions=results,output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.output.glob('*cover.npz')},geometry_adopted=False,elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],directions=results)));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
