"""Measure existing snap geometry exactly; never rerun or alter its construction."""
import argparse,hashlib,json,math,subprocess,sys
from pathlib import Path
from importlib.metadata import version
import numpy as np
import igl
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def topology(v,f):
    edges=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);unique,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    sums=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1,-1),minlength=len(unique))
    boundary=int(np.count_nonzero(counts==1));nonmanifold=int(np.count_nonzero(counts>2))
    winding=int(np.count_nonzero((counts==2)&(sums!=0)));bad_vertex=int(np.count_nonzero(~np.asarray(igl.is_vertex_manifold(f))))
    unused=len(v)-len(np.unique(f));a,b,c=(v[f[:,i]]-v[0] for i in range(3))
    volume=float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
    return dict(boundary_edges=boundary,nonmanifold_edges=nonmanifold,nonmanifold_vertices=bad_vertex,
        inconsistent_orientation_edges=winding,unused_vertices=unused,signed_volume_mm3=volume,
        **{'pass':boundary==nonmanifold==winding==bad_vertex==unused==0 and volume>0})

def mesh(path):
    data=np.load(path,allow_pickle=False);v=data['vertices'];f=data['faces']
    assert v.dtype==np.float64 and f.dtype==np.int64
    assert v.ndim==f.ndim==2 and v.shape[1]==f.shape[1]==3 and np.isfinite(v).all()
    assert len(v)>0 and len(f)>0 and f.min()>=0 and f.max()<len(v)
    return data,np.ascontiguousarray(v),np.ascontiguousarray(f)

def write(path,v,f):
    with path.open('w') as out:
        out.write(f'{len(v)} {len(f)}\n');np.savetxt(out,v,fmt='%.17g');np.savetxt(out,f,fmt='%d')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('result',type=Path);p.add_argument('output',type=Path);p.add_argument('binary',type=Path)
    args=p.parse_args();out=args.output
    assert version('libigl')=='2.6.3'
    origin=json.loads((out/'origin-audit.json').read_text());native=json.loads((out/'origin-native.json').read_text())
    execution=json.loads((out/'origin-execution-receipt.json').read_text())
    assert native==origin['native'] and sha(args.input)==origin['input_sha256'] and sha(args.result)==origin['result_sha256']
    assert execution['identities_unchanged'] and execution['owned_scope_inactive']
    assert origin['native_gate_pass'] and origin['topology_gate_pass']
    assert native['native_return'] and native['post_double_self_intersection_free'] and native['all_output_coordinates_exactly_double']
    assert native['source_face_lineage_complete'] and native['exact_collinear_output_triangles']==0
    assert origin['shape_drift_limit_source']=='iterations*norm(native_grid_step)/2'
    limit=origin['shape_drift_limit_mm'];assert math.isfinite(limit) and limit>=0 and limit==native['cumulative_rounding_budget_mm']
    before,v,f=mesh(args.input);after,w,g=mesh(args.result)
    lineage=after['autorefine_input_face'];saved=np.loadtxt(out/'origin-source-faces.txt',dtype=np.int64).reshape(-1)
    assert lineage.dtype==np.int64 and lineage.shape==(len(g),) and np.array_equal(lineage,saved)
    assert lineage.min()>=0 and lineage.max()<len(f)
    retained=[]
    for name in ['source_face','source','face_sources']:
        if name in before and before[name].shape==(len(f),):
            assert name in after and np.array_equal(before[name][lineage],after[name]);retained.append(name)
    write(out/'input.mesh64',v,f);write(out/'result.mesh64',w,g)
    command=[str(args.binary),str(out/'input.mesh64'),str(out/'result.mesh64'),str(out/'exact-distance.json'),repr(limit)]
    with (out/'native-distance.log').open('w') as log:run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    current=topology(w,g);measurement=json.loads((out/'exact-distance.json').read_text()) if (out/'exact-distance.json').is_file() else None
    passed=bool(run.returncode==0 and measurement and measurement['pass'] and current['pass'])
    receipt={'input_sha256':sha(args.input),'result_sha256':sha(args.result),'native_returncode':run.returncode,
       'origin_geometry_execution_status':execution['status'],'origin_native_gate_pass':origin['native_gate_pass'],
       'origin_native_sha256':sha(out/'origin-native.json'),'origin_execution_receipt_sha256':sha(out/'origin-execution-receipt.json'),
       'origin_audit_sha256':sha(out/'origin-audit.json'),'origin_libigl_drift_gate_pass':origin['drift_gate_pass'],
       'source_face_lineage_complete':True,'retained_face_attributes':retained,'output_topology':current,
       'exact_distance':measurement,'shape_drift_limit_mm':limit,'shape_drift_limit_source':origin['shape_drift_limit_source'],
       'native_geometry_gate_pass':True,'topology_gate_pass':bool(current['pass']),
       'drift_gate_pass':bool(run.returncode==0 and measurement and measurement['pass']),
       'pass':passed,'status':'accepted_geometric_screen' if passed else 'rejected',
       'numpy_version':np.__version__,'libigl_version':version('libigl'),
       'scope':'Remeasurement of unchanged existing snap geometry; exact Epeck distances at all vertices and rational face centroids, explicit collinear segments/points. No continuous Hausdorff certificate.'}
    (out/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return 0 if passed else 2
if __name__=='__main__':sys.exit(main())
