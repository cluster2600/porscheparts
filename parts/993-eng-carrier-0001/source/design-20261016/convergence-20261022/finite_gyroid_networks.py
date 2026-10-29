"""Retain the dominant finite void component for each analytic gyroid sign.

Disconnected remnants are filled with material. The resulting two chambers still
need explicit escape routes and transition design before a carrier is modified.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np


def main():
    import manifold3d as mf
    from reconstruct_core_envelopes import canonical_surface
    p=argparse.ArgumentParser(__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
    r=json.loads((a.directory/'assessment.json').read_text());assert r['status']=='finite_sharp_clipped_gyroid_void_baseline_passed';archive=a.directory/'void-tool.npz';assert sha(archive)==r['output_sha256'];z=np.load(archive);void=mf.Manifold(mf.Mesh64(np.array(z['vertices']),np.array(z['triangles'],dtype=np.uint64)));assert void.status()==mf.Error.NoError
    rows=[];families={1:[],-1:[]}
    for component in void.decompose():
        assert component.volume()>0
        mesh=component.to_mesh64();q=np.array(mesh.vert_properties)[:,:3]*(2*math.pi/r['pitch_mm']);phi=np.sin(q[:,0])*np.cos(q[:,1])+np.sin(q[:,1])*np.cos(q[:,2])+np.sin(q[:,2])*np.cos(q[:,0]);branch=1 if phi.min()>0 else -1 if phi.max()<0 else 0
        assert branch!=0
        row=dict(volume_mm3=component.volume(),branch=branch,minimum_vertex_phi=float(phi.min()),maximum_vertex_phi=float(phi.max()));rows.append(row);families[branch].append(component)
    assert abs(sum(x['volume_mm3']for x in rows)-void.volume())/void.volume()<=1e-10
    assert all(families.values());a.output.mkdir();kept=[]
    for branch in [1,-1]:
        component=max(families[branch],key=lambda c:c.volume());initial=component.volume();assert component.get_tolerance()<=1e-8;component=component.as_original().simplify(0);assert abs(component.volume()-initial)/initial<=1e-10
        m=component.to_mesh64();v=np.array(m.vert_properties)[:,:3];f=np.array(m.tri_verts,dtype=np.uint64);back=mf.Manifold(mf.Mesh64(v,f));assert back.status()==mf.Error.NoError
        b=back.to_mesh64();assert all(np.array_equal(x,y)for x,y in zip(canonical_surface(v,f),canonical_surface(np.array(b.vert_properties)[:,:3],np.array(b.tri_verts,dtype=np.uint64))))
        path=a.output/('positive.npz'if branch==1 else'negative.npz');np.savez_compressed(path,vertices=v,triangles=f);kept.append(dict(branch=branch,volume_mm3=component.volume(),file=path.name,sha256=sha(path),exact_oriented_triangle_roundtrip=True))
    saved=sum(x['volume_mm3']for x in kept);out=dict(status='dominant_void_network_per_analytic_sign_retained',rank=r['rank'],size_mm=r['size_mm'],pitch_mm=r['pitch_mm'],components=sorted(rows,key=lambda x:-x['volume_mm3']),selected=kept,raw_void_volume_mm3=void.volume(),retained_void_volume_mm3=saved,discarded_void_pockets=len(rows)-2,filled_pocket_volume_mm3=void.volume()-saved,finite_retained_solid_fraction=1-saved/r['core_volume_mm3'],carrier_geometry_changed=False,smooth_transition_generated=False,powder_escape_demonstrated=False,manufacturing_authorized=False,source_sha256={str(q):sha(q)for q in [Path(__file__),a.directory/'assessment.json',archive]})
    (a.output/'assessment.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['components','selected','source_sha256']}))


if __name__=='__main__':main()
