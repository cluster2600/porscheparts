"""Contract short mesh edges with an accumulated exact L1 surface-error bound.

A vertex contraction displaces every point of every incident triangle by at
most the contracted edge's L1 length (barycentric convexity). Redundant images
must be covered by retained triangles. Summing these bounds gives a conservative
bidirectional Hausdorff bound, including all intermediate surfaces. The final
mesh still requires an independent self-intersection audit.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import struct


def load_stl(path,np):
    raw=path.read_bytes();count=int.from_bytes(raw[80:84],'little')
    if len(raw)!=84+50*count:raise ValueError('Unexpected binary STL length')
    dtype=np.dtype([('normal','<f4',(3,)),('xyz','<f4',(3,3)),('attribute','<u2')])
    xyz=np.frombuffer(raw,offset=84,count=count,dtype=dtype)['xyz']
    vertices,inverse=np.unique(xyz.reshape(-1,3),axis=0,return_inverse=True)
    return vertices,inverse.reshape(-1,3)


def ratios(v,f,np):
    t=v[f].astype(np.float64)
    cross=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)
    longest=np.max(np.sum((t-np.roll(t,-1,axis=1))**2,axis=2),axis=1)
    return cross/longest


def closed_oriented(f,np):
    edges=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
    _,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    signed=np.where(edges[:,0]<edges[:,1],1,-1)
    return bool(np.all(counts==2)and np.all(np.bincount(inverse,weights=signed)==0)
                and len(np.unique(np.sort(f,axis=1),axis=0))==len(f))


def simplify(v,f,remaining,cleanup,np):
    spent=F(0);steps=[]
    while True:
        bad=np.flatnonzero(ratios(v,f,np)<.001)
        if not len(bad):break
        edges=sorted({tuple(sorted((int(t[i]),int(t[(i+1)%3]))))for t in f[bad]for i in range(3)},key=lambda e:float(np.abs(v[e[0]].astype(float)-v[e[1]]).sum()))
        choice=None
        for a,b in edges:
            cost=sum(abs(F(float(x))-F(float(y)))for x,y in zip(v[a],v[b]))
            if spent+cost>remaining:continue
            for keep,remove in [(a,b),(b,a)]:
                changed=f.copy();changed[changed==remove]=keep
                try:retained,certificate=cleanup.cleanup_certificate(changed.tolist())
                except ValueError:continue
                if retained is None:continue
                changed=changed[retained]
                if not closed_oriented(changed,np):continue
                quality=ratios(v,changed,np)
                if not np.isfinite(quality).all()or np.any(quality==0):continue
                count=int((quality<.001).sum())
                if count>=len(bad):continue
                score=(count,cost,keep,remove)
                if choice is None or score<choice[0]:choice=(score,changed,certificate)
            if choice is not None and choice[0][0]==0:break
        if choice is None:raise ValueError(f'No admissible contraction for {len(bad)} remaining needle triangles')
        (count,cost,keep,remove),f,certificate=choice;spent+=cost
        steps.append(dict(retained_vertex=keep,removed_vertex=remove,L1_displacement_mm=str(cost),accumulated_L1_bound_mm=str(spent),needles_before=len(bad),needles_after=count,redundant_image_coverage=certificate))
    used=np.unique(f);mapping=np.full(len(v),-1,dtype=int);mapping[used]=np.arange(len(used))
    return v[used],mapping[f],dict(accumulated_L1_bound_mm=str(spent),steps=steps,needle_ratio_threshold=.001,needle_triangles=0,minimum_ratio=float(ratios(v,f,np).min()))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--meshes',type=Path,nargs=2,required=True);p.add_argument('--bounds',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('Fresh output required')
    args.output.mkdir(parents=True)
    import numpy as np
    spec=importlib.util.spec_from_file_location('_collapse_cleanup',Path(__file__).with_name('exact_triangle_cleanup.py'));cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
    original=json.loads(args.bounds.read_text());report=dict(status='incomplete',patches=[],sources={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [*args.meshes,args.bounds,Path(__file__)]})
    try:
        for i,path in enumerate(args.meshes):
            bound=original['patches'][i];raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=bound['STL_sha256']:raise ValueError('Certified input mesh hash differs')
            prior=F(bound['maximum_complete_cell_L1_bound_mm']);remaining=F(.06)-prior
            v,f=load_stl(path,np);v,f,proof=simplify(v,f,remaining,cleanup,np)
            total=prior+F(proof['accumulated_L1_bound_mm'])
            if total>F(.06):raise ValueError('Complete source-to-output error exceeds unchanged tolerance')
            t=v[f].astype('<f4');normal=np.cross(t[:,1].astype(float)-t[:,0],t[:,2].astype(float)-t[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
            dtype=np.dtype([('normal','<f4',(3,)),('xyz','<f4',(3,3)),('attribute','<u2')]);records=np.zeros(len(f),dtype=dtype);records['normal']=normal;records['xyz']=t
            target=args.output/f'patch-{i}.stl';target.write_bytes(b'Certified source-bounded edge contractions'.ljust(80,b' ')+struct.pack('<I',len(f))+records.tobytes())
            proof.update(source_parametric_L1_bound_mm=str(prior),complete_source_to_output_L1_bound_mm=str(total),complete_source_to_output_L1_bound_mm_float=float(total),vertices=len(v),triangles=len(f),STL_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            report['patches'].append(proof)
        report['status']='complete_surface_bound_and_local_topology_passed'
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error));raise
    finally:(args.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status']}))

if __name__=='__main__':main()
