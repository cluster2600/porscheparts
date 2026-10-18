"""Compute a pinned experimental soup operation; keep independent gates visible."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from importlib.metadata import version
import numpy as np
import igl
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(path):
    data=np.load(path,allow_pickle=False);v=data['vertices'];f=data['faces']
    assert v.dtype==np.float64 and v.ndim==2 and v.shape[1]==3 and np.isfinite(v).all()
    assert np.issubdtype(f.dtype,np.integer) and f.ndim==2 and f.shape[1]==3
    assert len(v)>0 and len(f)>0 and f.min()>=0 and f.max()<len(v)
    faces=np.ascontiguousarray(f,dtype=np.int64);assert np.array_equal(f,faces)
    return data,np.ascontiguousarray(v),faces

def write_mesh(path,v,f):
    with path.open('w') as stream:
        stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')

def read_mesh(path):
    with path.open() as stream:
        nv,nf=map(int,stream.readline().split())
        v=np.loadtxt(stream,max_rows=nv,dtype=np.float64).reshape(nv,3) if nv else np.empty((0,3))
        f=np.loadtxt(stream,max_rows=nf,dtype=np.int64).reshape(nf,3) if nf else np.empty((0,3),dtype=np.int64)
    return v,f

def topology(v,f):
    if not len(v) or not len(f):return {'pass':False,'reason':'empty_mesh'}
    edges=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);unique,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    sums=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1,-1),minlength=len(unique))
    nonmanifold_vertices=int(np.count_nonzero(~np.asarray(igl.is_vertex_manifold(f))))
    boundary=int(np.count_nonzero(counts==1));nonmanifold=int(np.count_nonzero(counts>2))
    winding=int(np.count_nonzero((counts==2)&(sums!=0)));unused=len(v)-len(np.unique(f))
    a,b,c=v[f[:,0]]-v[0],v[f[:,1]]-v[0],v[f[:,2]]-v[0]
    volume=float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
    return dict(boundary_edges=boundary,nonmanifold_edges=nonmanifold,nonmanifold_vertices=nonmanifold_vertices,
      inconsistent_orientation_edges=winding,unused_vertices=unused,signed_volume_mm3=volume,
      **{'pass':boundary==nonmanifold==nonmanifold_vertices==winding==unused==0 and volume>0})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['self_union','union','intersection','difference','prism_free'])
    p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('binary',type=Path);p.add_argument('--second-input',type=Path)
    p.add_argument('--part-input',type=Path)
    args=p.parse_args();assert (args.mode=='self_union')==(args.second_input is None)
    assert (args.mode=='prism_free')==(args.part_input is not None)
    assert version('libigl')=='2.6.3';out=args.output
    data,v,f=load(args.input);write_mesh(out/'input-A.mesh64',v,f)
    inputs=[args.input];sources=[data];face_counts=[len(f)]
    command=[str(args.binary),args.mode,str(out/'input-A.mesh64')]
    if args.second_input is not None:
        d2,v2,f2=load(args.second_input);write_mesh(out/'input-B.mesh64',v2,f2)
        inputs.append(args.second_input);sources.append(d2);face_counts.append(len(f2));command.append(str(out/'input-B.mesh64'))
    if args.part_input is not None:
        d3,v3,f3=load(args.part_input);write_mesh(out/'input-part.mesh64',v3,f3)
        inputs.append(args.part_input);sources.append(d3);face_counts.append(len(f3));command.append(str(out/'input-part.mesh64'))
    command += [str(out/'result.mesh64'),str(out/'native.json')]
    with (out/'native.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    (out/'native-invocation.json').write_text(json.dumps({'returncode':r.returncode,'command':command},indent=2)+'\n')
    audit={'experimental':True,'operation':args.mode,'native_returncode':r.returncode,
      'input_sha256':[sha(path) for path in inputs],'numpy_version':np.__version__,'libigl_version':version('libigl'),
      'admitted':False,'scope':'Experimental computation. Native completion does not replace independent shape/contact/volume admission.'}
    try:native=json.loads((out/'native.json').read_text())
    except (FileNotFoundError,ValueError):
        audit.update(status='native_failure',local_geometry_gates_pass=False)
        (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');return 2
    nv,nf=read_mesh(out/'result.mesh64')
    arrays={'vertices':nv,'faces':nf};transferred=[]
    if native['source_face_lineage_complete']:
        parent=np.loadtxt(out/'result.mesh64.source_faces',dtype=np.int64).reshape(-1)
        counts=[len(f)*8,*face_counts[1:],12] if args.mode=='prism_free' else face_counts
        assert len(parent)==len(nf) and (not len(parent) or parent.min()>=0 and parent.max()<sum(counts))
        arrays['self_union_input_face']=parent
        all_rows=[np.asarray(list(map(int,line.split())),dtype=np.int64) for line in (out/'result.mesh64.all_source_faces').read_text().splitlines()]
        assert len(all_rows)==len(nf) and all(row[0]==len(row)-1 and row[0]>0 for row in all_rows)
        arrays['all_parent_offsets']=np.concatenate([[0],np.cumsum([len(row)-1 for row in all_rows])])
        arrays['all_parent_faces']=np.concatenate([row[1:] for row in all_rows]) if all_rows else np.empty(0,dtype=np.int64)
        if args.mode=='prism_free':
            arrays['source_face']=parent
            arrays['source']=np.searchsorted(np.cumsum(counts),parent,side='right').astype(np.int64)
            arrays['original_roof_id']=np.full(len(nf),-1,dtype=np.int64)
            selected=arrays['source']==0;ids=data['source_face_ids'] if 'source_face_ids' in data else np.arange(len(f))
            assert ids.shape==(len(f),) and np.issubdtype(ids.dtype,np.integer)
            arrays['original_roof_id'][selected]=ids[parent[selected]//8]
            transferred=['source_face','source','original_roof_id','all_parent_offsets','all_parent_faces']
        else:
            for name in ['source_face','source','face_sources','autorefine_input_face']:
                if all(name in d and d[name].shape==(n,) for d,n in zip(sources,face_counts)):
                    arrays[name]=np.concatenate([d[name] for d in sources])[parent];transferred.append(name)
    np.savez_compressed(out/'result.npz',**arrays)
    topo=topology(nv,nf);native_gate=(r.returncode==0 and native['operation_completed'] and native['exact_output_self_intersection_free'] and native['exact_collinear_output_triangles']==0 and native['source_face_lineage_complete'])
    audit.update(status='computed',native=native,output_topology=topo,retained_face_attributes=transferred,
      native_exact_gate_pass=native_gate,rounded_exact_contact_gate_pass=native['rounded_output_self_intersection_free'],
      local_geometry_gates_pass=bool(native_gate and topo['pass'] and native['rounded_output_self_intersection_free']),
      result_sha256=sha(out/'result.npz'),exact_result_sha256=sha(out/'result.mesh64.exact'))
    if args.mode=='prism_free':audit.update(leaf_role_order=['positive_roof_prisms','mask','part','clip_bbox'],leaf_face_counts=counts,
      proof='Union of original positive closed common-floor prisms; every intermediate binary input is checked for an exact clean closed oriented cycle; masked union minus local cutter equals masked union minus part.')
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:audit[k] for k in ['status','native_returncode','local_geometry_gates_pass','admitted']}))
    return 0 if native_gate else 2

if __name__=='__main__':sys.exit(main())
