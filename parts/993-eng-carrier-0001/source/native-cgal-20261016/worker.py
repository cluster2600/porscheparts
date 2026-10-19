"""Run CGAL snap rounding, preserving refusal, source-face lineage and metrics."""
import argparse,hashlib,json,math,re,subprocess,sys
from importlib.metadata import version
from pathlib import Path
import numpy as np
import igl

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def mesh64_write(path,v,f):
    with path.open('w') as stream:
        stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')

def mesh64_read(path):
    with path.open() as stream:
        nv,nf=map(int,stream.readline().split())
        v=np.loadtxt(stream,max_rows=nv,dtype=np.float64).reshape(nv,3)
        f=np.loadtxt(stream,max_rows=nf,dtype=np.int64).reshape(nf,3)
    return v,f

def topology(v,f):
    if not len(v) or not len(f):return {'pass':False,'reason':'empty_mesh'}
    if f.min()<0 or f.max()>=len(v):return {'pass':False,'reason':'invalid_indices'}
    edges=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);undirected=np.sort(edges,axis=1)
    unique,inverse,counts=np.unique(undirected,axis=0,return_inverse=True,return_counts=True)
    signs=np.where(edges[:,0]<edges[:,1],1,-1)
    sums=np.bincount(inverse,weights=signs,minlength=len(unique))
    vertices=np.asarray(igl.is_vertex_manifold(np.ascontiguousarray(f,dtype=np.int64)))
    unused=len(v)-len(np.unique(f));bad_vertex=int(np.count_nonzero(~vertices))
    boundary=int(np.count_nonzero(counts==1));nonmanifold=int(np.count_nonzero(counts>2))
    bad_winding=int(np.count_nonzero((counts==2)&(sums!=0)))
    origin=v[0];a,b,c=v[f[:,0]]-origin,v[f[:,1]]-origin,v[f[:,2]]-origin
    volume=float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
    return {'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'nonmanifold_vertices':bad_vertex,
            'unused_vertices':unused,'inconsistent_orientation_edges':bad_winding,'signed_volume_mm3':volume,
            'pass':boundary==0 and nonmanifold==0 and bad_vertex==0 and unused==0 and bad_winding==0 and volume>0}

def distance_samples(v,f,target_v,target_f):
    # All vertices and face centroids, with bounded native allocations.
    maximum=0.;location=None;count=0
    for kind,points in [('vertices',v),('face_centroids',v[f].mean(axis=1))]:
        for start in range(0,len(points),65536):
            part=np.ascontiguousarray(points[start:start+65536],dtype=np.float64)
            squared,_,_=igl.point_mesh_squared_distance(part,target_v,target_f)
            distances=np.sqrt(np.maximum(squared,0));index=int(np.argmax(distances));value=float(distances[index]);count+=len(part)
            if value>maximum:maximum=value;location={'kind':kind,'index':start+index,'point_mm':part[index].tolist()}
    return {'maximum_mm':maximum,'samples':count,'worst':location,'sampling':'All vertices and all face centroids; not a continuous Hausdorff certificate'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('binary',type=Path)
    p.add_argument('--grid-bits',required=True,type=int);p.add_argument('--iterations',required=True,type=int)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--max-drift-mm',type=float);group.add_argument('--cumulative-grid-bound',action='store_true')
    args=p.parse_args();out=args.output
    assert version('libigl')=='2.6.3'
    data=np.load(args.input,allow_pickle=False);v=np.ascontiguousarray(data['vertices'],dtype=np.float64);f=np.ascontiguousarray(data['faces'],dtype=np.int64)
    assert v.ndim==f.ndim==2 and v.shape[1]==f.shape[1]==3 and np.isfinite(v).all()
    assert len(v)>0 and len(f)>0 and f.min()>=0 and f.max()<len(v)
    original_topology=topology(v,f);mesh64_write(out/'input.mesh64',v,f)
    command=[str(args.binary),str(out/'input.mesh64'),str(out/'result.mesh64'),str(out/'native.json'),str(args.grid_bits),str(args.iterations)]
    with (out/'native.log').open('w') as log:run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    receipt={'input_sha256':sha(args.input),'native_returncode':run.returncode,'input_topology':original_topology,
             'input_float_bbox_mm':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],
             'input_vertices':len(v),'input_faces':len(f),'numpy_version':np.__version__,'libigl_version':version('libigl')}
    if not (out/'native.json').is_file():
        receipt.update({'status':'rejected_native_failure','pass':False})
        (out/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');return 2
    native=json.loads((out/'native.json').read_text());receipt['native']=native
    receipt['iterations_started']=len(re.findall(r'^Start Iteration \d+$',(out/'native.log').read_text(),re.MULTILINE))
    nv,nf=mesh64_read(out/'result.mesh64');assert np.isfinite(nv).all()
    arrays={'vertices':nv,'faces':nf};lineage_complete=native['source_face_lineage_complete'];transferred=[]
    if lineage_complete:
        lineage=np.loadtxt(out/'result.mesh64.source_faces',dtype=np.int64).reshape(-1)
        assert len(lineage)==len(nf) and (len(lineage)==0 or (lineage.min()>=0 and lineage.max()<len(f)))
        arrays['autorefine_input_face']=lineage
        for name in ['source_face','source','face_sources']:
            if name in data and data[name].shape==(len(f),):arrays[name]=data[name][lineage];transferred.append(name)
    np.savez_compressed(out/'result.npz',**arrays)
    current=topology(nv,nf);receipt['output_topology']=current
    receipt.update(output_vertices=len(nv),output_faces=len(nf),retained_face_attributes=transferred,
                   source_face_lineage_complete=lineage_complete,result_sha256=sha(out/'result.npz'))
    limit=float(native['cumulative_rounding_budget_mm']) if args.cumulative_grid_bound else args.max_drift_mm
    assert limit is not None and math.isfinite(limit) and limit>=0
    receipt.update(shape_drift_limit_mm=limit,shape_drift_limit_source='iterations*norm(native_grid_step)/2' if args.cumulative_grid_bound else 'explicit_user_value')
    native_gate=(run.returncode==0 and native['native_return'] and native['all_output_coordinates_exactly_double']
                 and native['post_double_self_intersection_free'] and native['exact_collinear_output_triangles']==0 and lineage_complete)
    # Invalid/partial output remains visible, but cannot enter downstream stages.
    drift_pass=False
    if native_gate and len(nf)>0:
        a=distance_samples(v,f,nv,nf);b=distance_samples(nv,nf,v,f)
        receipt.update(input_to_output=a,output_to_input=b)
        drift_pass=max(a['maximum_mm'],b['maximum_mm'])<=limit
    receipt['native_gate_pass']=bool(native_gate);receipt['topology_gate_pass']=bool(current['pass']);receipt['drift_gate_pass']=bool(drift_pass)
    passed=bool(native_gate and current['pass'] and drift_pass)
    receipt.update({'status':'accepted_geometric_screen' if passed else 'rejected','pass':passed,
       'scope':'CGAL kernel return, actual float64 exact-contact check, indexed manifold/orientation checks, and deterministic sampled shape drift. No process qualification implied.'})
    (out/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
    return 0 if passed else 2

if __name__=='__main__':sys.exit(main())
