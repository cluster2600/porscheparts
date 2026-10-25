"""Screen all accepted refined T4 centroids; retain the separate full-field energy proof."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import prepare_cellular_screen as base


def cell_fields(vertices,cells,stress,E,nu):
    if cells.ndim!=2 or cells.shape[1]!=4 or cells.dtype.kind not in 'iu' or cells.min()<0 or cells.max()>=len(vertices) or stress.shape!=(len(cells),6) or not 0<len(cells)<=4000000 or not E>0 or not -1<nu<.5:raise ValueError('Bounded complete linear cells and elastic material required')
    centres=np.empty((len(cells),3));radii=np.empty(len(cells));volumes=np.empty(len(cells));energy=np.empty(len(cells))
    for start in range(0,len(cells),65536):
        stop=min(start+65536,len(cells));points=vertices[cells[start:stop]];c=points.mean(1);edges=points[:,1:]-points[:,0,None];vol=np.sum(edges[:,0]*np.cross(edges[:,1],edges[:,2]),axis=1)/6;s=stress[start:stop];d=s[:,:3];pairs=d[:,0]*d[:,1]+d[:,1]*d[:,2]+d[:,2]*d[:,0]
        density=(np.sum(d*d,1)-2*nu*pairs+2*(1+nu)*np.sum(s[:,3:]**2,1))/(2*E)
        if not np.all(np.isfinite(points)) or not np.all(np.isfinite(density)&(density>=0)) or not np.all(vol>0):raise ValueError('Finite positive cells and nonnegative elastic energy required')
        centres[start:stop]=c;radii[start:stop]=np.linalg.norm(points-c[:,None,:],axis=2).max(1);volumes[start:stop]=vol;energy[start:stop]=vol*density
    return centres,radii,volumes,energy


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['preparation','mechanics','energy-proof','raw-volume','exact-proof','study','parameters','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    if np.__version__!='2.2.6' or importlib.metadata.version('libigl')!='2.6.3':raise ValueError('Pinned numerical environment required')
    import igl
    mesh=a.preparation/'transport.npz';results=a.mechanics/'results.npz';report=json.loads((a.mechanics/'assessment.json').read_text());energy_proof=json.loads(a.energy_proof.read_text());prepared=json.loads((a.preparation/'assessment.json').read_text());raw=json.loads((a.raw_volume/'assessment.json').read_text());exact=json.loads(a.exact_proof.read_text());parameters=json.loads(a.parameters.read_text());study=json.loads(a.study.read_text())
    if report['status']!='complete_linear_C3D4_results_and_equilibrium_passed' or base.sha(results)!=report['output_sha256'] or base.sha(mesh)not in report['source_sha256'].values():raise ValueError('Accepted complete linear mechanics required')
    if energy_proof['status']!='complete_independent_stress_energy_check_passed' or energy_proof['fixed_relative_limit']!=.0001 or energy_proof['relative_energy_residual']>.0001 or not all(base.sha(x)in energy_proof['source_sha256'].values()for x in [mesh,results,a.mechanics/'assessment.json',a.preparation/'assessment.json']):raise ValueError('Source-bound complete independent energy proof required')
    raw_mesh=a.raw_volume/'transport.npz'
    if exact['status']!='full_exact_orientation_and_indexed_volume_screens_passed' or base.sha(raw_mesh)not in exact['source_sha256'].values() or base.sha(raw_mesh)!=raw['output_sha256']['transport.npz'] or raw['whole_surface_distance_upper_mm']>.06:raise ValueError('Exact source-bound nested geometry proof required')
    if parameters!=json.loads(Path(base.__file__).with_name('cellular-screen-parameters.json').read_text()) or prepared['material']!=study['material']:raise ValueError('Retained screen parameters and material required')
    with np.load(mesh,allow_pickle=False)as data:fields={k:data[k].copy()for k in ['vertices','tetrahedra','boundary']}
    with np.load(raw_mesh,allow_pickle=False)as data:
        if not all(np.array_equal(fields[k],data[k])for k in fields):raise ValueError('Mechanics and exact-audited geometry arrays differ')
    v=fields['vertices'];cells=fields['tetrahedra'];faces=fields['boundary']
    with np.load(results,allow_pickle=False)as data:stress=data['stress'].copy()
    material=prepared['material'];centres,radii,volumes,energy=cell_fields(v,cells,stress,material['E_MPa'],material['nu'])
    if abs(energy.sum()-energy_proof['internal_stress_compliance_energy_Nmm'])/energy.sum()>1e-12:raise ValueError('Independent integrated energy identity refused')
    used=np.unique(faces);mapping=np.full(len(v),-1,dtype=np.int64);mapping[used]=np.arange(len(used));surface=v[used];vertices=surface.astype(np.float32);triangles=mapping[faces].astype(np.int32);probes=centres.astype(np.float32);vd=vertices.astype(np.float64);tree=igl.AABB();tree.init(vd,triangles.astype(np.int64));squared,_,_=tree.squared_distance(vd,triangles.astype(np.int64),probes.astype(np.float64));expected=np.sqrt(np.maximum(0,np.asarray(squared).reshape(-1)))
    if not np.isfinite(expected).all():raise ValueError('Nonfinite independent oracle')
    a.output.mkdir(parents=True);bundle=a.output/'carrier-queries.npz';np.savez_compressed(bundle,vertices=vertices,triangles=triangles,probes=probes,expected_distances_mm=expected)
    np.savez_compressed(a.output/'screen-fields.npz',centres=centres,radii=radii,volumes_mm3=volumes,energy_Nmm=energy,probe_transport_L1_mm=abs(centres-probes.astype(np.float64)).sum(1),interface_allowed=base.protected_cells(centres,radii,study['geometry'],parameters))
    metadata=dict(status='accepted_linear_analysis_centroid_screen_prepared',queries=len(centres),vertices=len(vertices),triangles=len(triangles),bundle_sha256=base.sha(bundle),fixed_absolute_error_limit_mm=.0001,query_groups={'all_refined_linear_cell_centroids':[0,len(centres)]},surface_float32_transport_L1_bound_mm=float(abs(surface-vd).sum(1).max()),source_sha256={str(x):base.sha(x)for x in [mesh,results,a.energy_proof,a.exact_proof,raw_mesh,a.raw_volume/'assessment.json',a.study,a.parameters,a.mechanics/'assessment.json',a.preparation/'assessment.json',Path(__file__),Path(base.__file__)]},screen_fields_sha256=base.sha(a.output/'screen-fields.npz'),parameters=parameters,material=material,geometry_role='auxiliary refined linear analysis volume; R2 reference stays unchanged',exact_arithmetic_certificate=False,cellular_geometry_generated=False)
    (a.output/'oracle-report.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(dict(status=metadata['status'],queries=len(centres))))


if __name__=='__main__':main()
