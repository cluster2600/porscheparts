"""Build and independently check a sharp-clipped finite gyroid void baseline.

This creates internal void tools only; transitions, escape paths and full-carrier
mechanics remain separate checks. All output directories must be new.
"""
import argparse,hashlib,json,math,signal,time
from pathlib import Path
import numpy as np


def triangle_witness_distance(p,tri):
    p=np.asarray(p,dtype=np.longdouble);tri=np.asarray(tri,dtype=np.longdouble);distances=[]
    for j in range(3):
        origin=tri[:,j];edge=tri[:,(j+1)%3]-origin;length2=np.sum(edge*edge,axis=1)
        t=np.divide(np.sum((p-origin)*edge,axis=1),length2,out=np.zeros_like(length2),where=length2>0)
        witness=origin+np.clip(t,0,1)[:,None]*edge
        distances.append(np.sqrt(np.sum((p-witness)**2,axis=1)))
    u=tri[:,1]-tri[:,0];v=tri[:,2]-tri[:,0];normal=np.cross(u,v);n2=np.sum(normal*normal,axis=1)
    safe=n2>0
    b1=np.divide(np.sum(np.cross(p-tri[:,0],v)*normal,axis=1),n2,out=np.zeros_like(n2),where=safe)
    b2=np.divide(np.sum(np.cross(u,p-tri[:,0])*normal,axis=1),n2,out=np.zeros_like(n2),where=safe)
    valid=safe & (b1>=0) & (b2>=0) & (b1+b2<=1)
    witness=tri[:,0]+b1[:,None]*u+b2[:,None]*v
    plane_distance=np.sqrt(np.sum((p-witness)**2,axis=1));plane_distance[~valid]=np.inf
    return np.minimum(np.min(distances,axis=0),plane_distance)


def geometry_controls(mf, plan):
    rows=[];radius=plan['sphere_radius_mm'];expected=4*math.pi*radius**3/3
    for size in plan['sphere_sizes_mm']:
        sphere=mf.Manifold.level_set(lambda x,y,z:radius-math.sqrt((x-.5)**2+(y-.5)**2+(z-.5)**2),(0,0,0,1,1,1),size,tolerance=1e-5)
        error=abs(sphere.volume()-expected)/expected
        rows.append(dict(size_mm=size,native_status=str(sphere.status()),volume_mm3=sphere.volume(),relative_volume_error=error,passed=sphere.status()==mf.Error.NoError and error<=plan['maximum_relative_sphere_volume_error']))
    return rows


def main():
    import manifold3d as mf
    import igl
    from reconstruct_core_envelopes import canonical_surface
    p=argparse.ArgumentParser(__doc__);p.add_argument('--envelope-directory',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--rank',type=int,required=True);p.add_argument('--size',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    SOURCE=Path(__file__).resolve().parent;contract=a.contract;plan=json.loads(contract.read_text());assert 0<=a.rank<4 and a.size in plan['finite_sizes_mm'] and not a.output.exists()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    source_identity=sha(Path(__file__))
    archive=a.envelope_directory/'envelopes.npz';assert sha(archive)==plan['envelope_source_sha256']
    r=json.loads((archive.parent/'assessment.json').read_text());z=np.load(archive);row=r['components'][a.rank];vstart=sum(c['vertices']for c in r['components'][:a.rank]);fstart=sum(c['triangles']for c in r['components'][:a.rank]);v=np.array(z['vertices'][vstart:vstart+row['vertices']],dtype=np.float64);f=np.array(z['triangles'][fstart:fstart+row['triangles']]-vstart,dtype=np.uint64)
    core=mf.Manifold(mf.Mesh64(v,f));assert core.status()==mf.Error.NoError and abs(core.volume()-row['volume_mm3'])/row['volume_mm3']<1e-10
    controls=geometry_controls(mf,plan);assert all(c['passed']for c in controls[1:])
    outer=mf.Manifold.cube((2,2,2),True);inner=mf.Manifold.cube((1,1,1),True);assert abs(mf.Manifold.batch_boolean([outer,inner],mf.OpType.Intersect).volume()-1)<1e-12 and mf.Manifold.batch_boolean([inner,outer],mf.OpType.Subtract).is_empty()
    a.output.mkdir();(a.output/'analytic-controls.json').write_text(json.dumps(controls,indent=2)+'\n');start=time.monotonic();signal.alarm(plan['maximum_job_seconds']);pitch=plan['finite_pitch_mm'];threshold=plan['gyroid_threshold'];k=2*math.pi/pitch;scale=pitch/(4*math.pi*math.sqrt(3))
    def field(x,y,z):
        x*=k;y*=k;z*=k
        return (abs(math.sin(x)*math.cos(y)+math.sin(y)*math.cos(z)+math.sin(z)*math.cos(x))-threshold)*scale
    margin=plan['operative_core_inset_mm'];clip=core.minkowski_difference(mf.Manifold.cube((2*margin,)*3,True));assert clip.status()==mf.Error.NoError and 0<clip.volume()<core.volume();cm=clip.to_mesh64();cv=np.array(cm.vert_properties)[:,:3];cf=np.array(cm.tri_verts,dtype=np.uint64)
    low=cv.min(0)-.5;high=cv.max(0)+.5
    (a.output/'contract.json').write_text(json.dumps(dict(parameters=plan,rank=a.rank,size_mm=a.size,bounds_mm=[low.tolist(),high.tolist()],source_sha256={str(q):sha(q)for q in [Path(__file__),contract,archive,SOURCE/'reconstruct_core_envelopes.py']}),indent=2)+'\n')
    periodic_void=mf.Manifold.level_set(field,tuple(low)+tuple(high),a.size,tolerance=1e-5)
    assert periodic_void.status()==mf.Error.NoError
    void=mf.Manifold.batch_boolean([clip,periodic_void],mf.OpType.Intersect);assert void.status()==mf.Error.NoError and 0<void.volume()<core.volume()
    pre_normalization_volume=void.volume();native_normalization_tolerance=void.get_tolerance();assert native_normalization_tolerance<=plan['maximum_native_normalization_tolerance_mm']
    void=void.as_original().simplify(0);assert void.status()==mf.Error.NoError and abs(void.volume()-pre_normalization_volume)/pre_normalization_volume<=plan['normalization_relative_volume_limit']
    outside=mf.Manifold.batch_boolean([void,core],mf.OpType.Subtract)
    (a.output/'containment-observation.json').write_text(json.dumps(dict(void_volume_mm3=void.volume(),outside_volume_mm3=outside.volume(),outside_triangles=outside.num_tri(),outside_status=str(outside.status()),outside_is_empty=outside.is_empty()),indent=2)+'\n')
    assert outside.is_empty()
    mesh=void.to_mesh64();points=np.array(mesh.vert_properties)[:,:3];triangles=np.array(mesh.tri_verts,dtype=np.uint64);back=mf.Manifold(mf.Mesh64(points,triangles));assert back.status()==mf.Error.NoError
    b=back.to_mesh64();same=all(np.array_equal(x,y)for x,y in zip(canonical_surface(points,triangles),canonical_surface(np.array(b.vert_properties)[:,:3],np.array(b.tri_verts,dtype=np.uint64))))
    np.savez_compressed(a.output/'before-roundtrip.npz',vertices=points,triangles=triangles)
    np.savez_compressed(a.output/'after-roundtrip.npz',vertices=np.array(b.vert_properties)[:,:3],triangles=np.array(b.tri_verts,dtype=np.uint64))
    (a.output/'roundtrip-observation.json').write_text(json.dumps(dict(exact_oriented_triangles=same,before_volume_mm3=void.volume(),after_volume_mm3=back.volume(),before_triangles=len(triangles),after_triangles=len(b.tri_verts),native_status=str(back.status())),indent=2)+'\n')
    assert same
    relative_volume_error=abs(back.volume()-void.volume())/void.volume();assert relative_volume_error<=1e-10
    d,nearest,_=igl.point_mesh_squared_distance(points,cv,cf.astype(np.int64));interior=np.sqrt(d)>plan['minimum_core_cap_distance_for_phi_check_mm']
    q=points*k;phi=np.sin(q[:,0])*np.cos(q[:,1])+np.sin(q[:,1])*np.cos(q[:,2])+np.sin(q[:,2])*np.cos(q[:,0]);phase_error=abs(abs(phi)-threshold)
    rejected=np.flatnonzero(interior & (phase_error>plan['phase_field_surface_residual_limit']))
    # Skinny cap triangles can lose precision in the general closest-point query.
    control_tri=np.array([[[0,0,0],[1,0,0],[0,1,0]]],dtype=float)
    assert triangle_witness_distance([[.5,0,0]],control_tri)[0]==0
    assert abs(triangle_witness_distance([[.5,0,2]],control_tri)[0]-2)<1e-15
    assert triangle_witness_distance([[.25,.25,0]],control_tri)[0]==0
    assert abs(triangle_witness_distance([[.25,.25,2]],control_tri)[0]-2)<1e-15
    witness=triangle_witness_distance(points[rejected],cv[cf[nearest[rejected]]]) if len(rejected) else np.array([])
    full_mesh_queries=np.flatnonzero(witness>plan['minimum_core_cap_distance_for_phi_check_mm']);assert len(full_mesh_queries)<=256
    for j in full_mesh_queries:
        witness[j]=triangle_witness_distance(np.broadcast_to(points[rejected[j]],(len(cf),3)),cv[cf]).min()
    recovered=rejected[witness<=plan['minimum_core_cap_distance_for_phi_check_mm']];interior[recovered]=False
    (a.output/'phase-observation.json').write_text(json.dumps(dict(initially_rejected_vertices=len(rejected),full_mesh_witness_queries=len(full_mesh_queries),independent_cap_triangle_witnesses=len(recovered),witness_distances_mm=witness.astype(float).tolist(),unrelaxed_cap_distance_limit_mm=plan['minimum_core_cap_distance_for_phi_check_mm'],unrelaxed_phase_residual_limit=plan['phase_field_surface_residual_limit']),indent=2)+'\n')
    residual=float(phase_error[interior].max());assert residual<=plan['phase_field_surface_residual_limit']
    np.savez_compressed(a.output/'void-tool.npz',vertices=points,triangles=triangles);signal.alarm(0)
    report=dict(status='finite_sharp_clipped_gyroid_void_baseline_passed',rank=a.rank,size_mm=a.size,pitch_mm=pitch,core_volume_mm3=core.volume(),operative_core_volume_mm3=clip.volume(),operative_core_inset_mm=margin,void_volume_mm3=void.volume(),finite_retained_solid_fraction=1-void.volume()/core.volume(),vertices=len(points),triangles=len(triangles),phase_surface_vertices_checked=int(interior.sum()),maximum_abs_phase_residual=residual,native_normalization_tolerance_mm=native_normalization_tolerance,normalization_relative_volume_change=abs(void.volume()-pre_normalization_volume)/pre_normalization_volume,exact_oriented_triangle_roundtrip=True,relative_export_volume_error=relative_volume_error,native_positive_components=sum(part.volume()>0 for part in void.decompose()),elapsed_seconds=time.monotonic()-start,source_sha256=source_identity,output_sha256=sha(a.output/'void-tool.npz'),smooth_transition_generated=False,carrier_geometry_changed=False,powder_escape_demonstrated=False,manufacturing_authorized=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
