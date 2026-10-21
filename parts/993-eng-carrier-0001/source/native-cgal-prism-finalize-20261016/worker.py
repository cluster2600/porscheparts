"""Compute a pinned experimental soup operation; keep independent gates visible."""
import argparse,hashlib,json,shutil,subprocess,sys
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
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['roofs','mask','part','exact','quantized','output','binary']:p.add_argument(name,type=Path)
    args=p.parse_args();out=args.output;assert version('libigl')=='2.6.3'
    inputs=[args.roofs,args.mask,args.part];meshes=[load(path) for path in inputs]
    for name,(_,v,f) in zip(['roofs','mask','part'],meshes):write_mesh(out/(name+'.mesh64'),v,f)
    shutil.copyfile(args.exact,out/'result.mesh64.exact');shutil.copyfile(args.quantized,out/'result.mesh64')
    command=[str(args.binary),str(out/'roofs.mesh64'),str(out/'mask.mesh64'),str(out/'part.mesh64'),str(args.exact),str(args.quantized),str(out/'result.mesh64'),str(out/'native.json')]
    with (out/'native.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    (out/'native-invocation.json').write_text(json.dumps({'returncode':r.returncode,'command':command},indent=2)+'\n')
    audit={'experimental':True,'operation':'finalize_existing_sealed_checkpoint_only','CSG_recomputed':False,'native_returncode':r.returncode,
      'input_sha256':[sha(path) for path in inputs],'origin_geometry_checkpoint_sha256':sha(args.exact),'origin_quantized_checkpoint_sha256':sha(args.quantized),
      'admitted':False,'scope':'Standalone finalization/audit of unchanged sealed geometry; original failed receipts retained. Snap/drift/contacts remain separate required gates.'}
    try:native=json.loads((out/'native.json').read_text())
    except (FileNotFoundError,ValueError):
        audit.update(status='native_failure',native_exact_gate_pass=False,local_geometry_gates_pass=False)
        (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');return 2
    v,f=read_mesh(out/'result.mesh64');data,_,roofs=meshes[0];counts=[8*len(roofs),len(meshes[1][2]),len(meshes[2][2]),12]
    arrays={'vertices':v,'faces':f};attrs=[]
    if native['source_face_lineage_complete']:
        primary=np.loadtxt(out/'result.mesh64.source_faces',dtype=np.int64).reshape(-1)
        rows=[np.array(list(map(int,line.split())),dtype=np.int64) for line in (out/'result.mesh64.all_source_faces').read_text().splitlines()]
        assert len(primary)==len(f)==len(rows) and all(row[0]==len(row)-1 and row[0]>0 for row in rows)
        assert primary.min()>=0 and primary.max()<sum(counts)
        arrays.update(self_union_input_face=primary,source_face=primary,source=np.searchsorted(np.cumsum(counts),primary,side='right').astype(np.int64),
          all_parent_offsets=np.concatenate([[0],np.cumsum([len(row)-1 for row in rows])]),all_parent_faces=np.concatenate([row[1:] for row in rows]))
        ids=data['source_face_ids'] if 'source_face_ids' in data else np.arange(len(roofs),dtype=np.int64)
        assert ids.shape==(len(roofs),) and np.issubdtype(ids.dtype,np.integer)
        arrays['original_roof_id']=np.full(len(f),-1,dtype=np.int64);selected=arrays['source']==0
        arrays['original_roof_id'][selected]=ids[primary[selected]//8]
        attrs=['source_face','source','original_roof_id','all_parent_offsets','all_parent_faces']
    np.savez_compressed(out/'result.npz',**arrays);topo=topology(v,f)
    gate=bool(r.returncode==0 and native['operation_completed'] and native['exact_output_self_intersection_free'] and native['exact_collinear_output_triangles']==0 and native['source_face_lineage_complete'] and native['bbox_parent_matches']==0)
    audit.update(status='computed',native=native,output_topology=topo,native_exact_gate_pass=gate,
      rounded_exact_contact_gate_pass=native['rounded_output_self_intersection_free'],local_geometry_gates_pass=gate and topo['pass'] and native['rounded_output_self_intersection_free'],
      result_sha256=sha(out/'result.npz'),exact_result_sha256=sha(out/'result.mesh64.exact'),retained_face_attributes=attrs,
      leaf_role_order=['positive_roof_prisms','mask','part','clip_bbox'],leaf_face_counts=counts,
      proof='Same sealed exact/float coordinates and indices; all geometric parent matches recomputed; volume uses exact rational balanced reduction. No CSG or geometry modification.')
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'native_exact_gate_pass':gate,'local_geometry_gates_pass':audit['local_geometry_gates_pass'],'volume_mm3':native['signed_volume_mm3']}))
    return 0 if gate else 2

if __name__=='__main__':sys.exit(main())
