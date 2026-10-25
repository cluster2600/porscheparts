"""Prepare all accepted T10 cell-centroid queries and independent strain-energy weights."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import compare_accepted_fields as comparison


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_cells(centres,radii,geometry,parameters):
    allowed=abs(centres[:,0])+radii<=parameters['end_inboard_limit_abs_X_mm']
    for key,radius in [('central_bolt_centres_xy_mm',geometry['central_bore_radius_mm']),('secondary_centres_xy_mm',geometry['secondary_radius_mm'])]:
        for x,y in geometry[key]:allowed &= np.hypot(centres[:,0]-x,centres[:,1]-y)-radii>=radius+parameters['bore_keepout_mm']
    return allowed


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['preparation','mechanics','mapping-proof','study','parameters','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    if np.__version__!='2.2.6'or importlib.metadata.version('libigl')!='2.6.3':raise ValueError('Pinned numerical environment required')
    import igl
    report=json.loads((a.mechanics/'assessment.json').read_text());prepared=json.loads((a.preparation/'assessment.json').read_text());proof=json.loads(a.mapping_proof.read_text());parameters=json.loads(a.parameters.read_text());study=json.loads(a.study.read_text());mesh=a.preparation/'transport.npz';results=a.mechanics/'results.npz'
    if report['status']!='complete_linear_C3D10_results_equilibrium_and_energy_passed'or report['relative_energy_residual']>1e-4:raise ValueError('Accepted complete T10 mechanics required')
    if sha(results)!=report['output_sha256']or sha(mesh)not in report['source_sha256'].values()or sha(mesh)not in proof['source_sha256'].values()or proof['status']!='complete_C3D10_mapping_and_geometry_budget_passed':raise ValueError('Source-bound complete geometry/mechanics proof required')
    if parameters['distance_error_limit_mm']!=.0001 or not 0<parameters['maximum_selected_volume_fraction']<1 or not 0<parameters['relative_density_scenario']<1 or parameters['skin_mm']<=0 or parameters['bore_keepout_mm']<=0:raise ValueError('Fixed valid screen parameters required')
    if prepared['material']!=study['material']:raise ValueError('Retained material differs')
    with np.load(mesh,allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy();faces=data['boundary'][:,:3].copy()
    with np.load(results,allow_pickle=False)as data:stress=data['stress'].copy()
    if cells.shape[1]!=10 or len(cells)>3000000 or stress.shape!=(len(cells),4,6):raise ValueError('Bounded complete T10 roster required')
    corners=v[cells[:,:4]];centres=corners.mean(1);radii=np.linalg.norm(corners-centres[:,None,:],axis=2).max(1)+proof['complete_curved_to_corner_surface_L1_bound_mm']
    _,weights=comparison.samples(v,cells,stress);weights=weights.reshape(-1,4);volumes=weights.sum(1);material=prepared['material'];d=stress[:,:,:3];s=stress[:,:,3:];pairs=d[:,:,0]*d[:,:,1]+d[:,:,1]*d[:,:,2]+d[:,:,2]*d[:,:,0]
    density=(np.sum(d*d,2)-2*material['nu']*pairs+2*(1+material['nu'])*np.sum(s*s,2))/(2*material['E_MPa']);energy=np.sum(weights*density,axis=1)
    if not np.all(volumes>0)or not np.all(np.isfinite(energy)&(energy>=0))or abs(energy.sum()-report['independent_stress_compliance_energy_Nmm'])/energy.sum()>1e-12:raise ValueError('Independent integrated energy identity refused')
    used=np.unique(faces);mapping=np.full(len(v),-1,dtype=np.int64);mapping[used]=np.arange(len(used));surface=v[used];triangles=mapping[faces].astype(np.int32);vertices=surface.astype(np.float32);probes=centres.astype(np.float32);vd=vertices.astype(np.float64);tree=igl.AABB();tree.init(vd,triangles.astype(np.int64));squared,_,_=tree.squared_distance(vd,triangles.astype(np.int64),probes.astype(np.float64));expected=np.sqrt(np.maximum(0,np.asarray(squared).reshape(-1)))
    if not np.isfinite(expected).all():raise ValueError('Nonfinite independent oracle')
    a.output.mkdir(parents=True);bundle=a.output/'carrier-queries.npz';np.savez_compressed(bundle,vertices=vertices,triangles=triangles,probes=probes,expected_distances_mm=expected)
    np.savez_compressed(a.output/'screen-fields.npz',centres=centres,radii=radii,volumes_mm3=volumes,energy_Nmm=energy,probe_transport_L1_mm=abs(centres-probes.astype(np.float64)).sum(1),interface_allowed=protected_cells(centres,radii,study['geometry'],parameters))
    metadata=dict(status='accepted_analysis_centroid_screen_prepared',queries=len(centres),vertices=len(vertices),triangles=len(triangles),bundle_sha256=sha(bundle),fixed_absolute_error_limit_mm=.0001,query_groups={'all_analysis_cell_centroids':[0,len(centres)]},surface_float32_transport_L1_bound_mm=float(abs(surface-vd).sum(1).max()),source_sha256={str(path):sha(path)for path in [mesh,results,a.mapping_proof,a.study,a.parameters,a.mechanics/'assessment.json',a.preparation/'assessment.json',Path(__file__),Path(comparison.__file__)]},screen_fields_sha256=sha(a.output/'screen-fields.npz'),parameters=parameters,material=material,geometry_role='auxiliary analysis volume; reference R2 stays unchanged',exact_arithmetic_certificate=False,cellular_geometry_generated=False)
    (a.output/'oracle-report.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps({'status':metadata['status'],'queries':len(centres)}))


if __name__=='__main__':main()
