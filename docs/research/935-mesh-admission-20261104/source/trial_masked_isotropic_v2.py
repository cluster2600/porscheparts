"""Retry from the immutable parent with diagnosed regions protected exactly."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import pymeshlab as ml
from trial_planar_flips import sha, save_json, write_off, inspect, quality, samples, distances
from trial_isotropic import topology


def triangle_keys(v, f):
    p = v[f]
    first = np.lexsort((p[:,:,2], p[:,:,1], p[:,:,0]), axis=1)[:,0]
    cyclic = (first[:,None] + np.arange(3)) % 3
    canonical = np.take_along_axis(p, cyclic[:,:,None], axis=1)
    return np.ascontiguousarray(canonical, dtype='<f8').reshape((-1,9)).view('V72').reshape(-1)


def expand(f, nvertices, seeds):
    pairs = np.concatenate((f[:,[0,1]], f[:,[1,2]], f[:,[2,0]]))
    keys = pairs.min(axis=1)*nvertices+pairs.max(axis=1)
    order = np.argsort(keys); sorted_keys = keys[order]
    if not np.all(sorted_keys[::2] == sorted_keys[1::2]):
        raise SystemExit('Parent does not have exactly paired boundary edges.')
    faces = np.tile(np.arange(len(f)), 3)[order].reshape(-1,2)
    protected = np.zeros(len(f), bool); protected[seeds] = True
    for _ in range(2):
        protected[faces[protected[faces].any(axis=1)].reshape(-1)] = True
    return protected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-isotropic', type=Path, required=True)
    parser.add_argument('--inspector', type=Path, required=True)
    parser.add_argument('--topology-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Existing output refused.')
    manifest = json.loads((args.prior_isotropic/'manifest.json').read_text())['files']
    for name in ('trial-001/parent.npz','diagnostics-001/defect-face-ids.npz','trial-001/plan.json','trial-001/parent-topology.json'):
        if sha(args.prior_isotropic/name) != manifest[name]['sha256']: raise SystemExit('Prior input changed: '+name)
    with np.load(args.prior_isotropic/'trial-001/parent.npz', allow_pickle=False) as a: v, f = a['vertices'], a['triangles']
    with np.load(args.prior_isotropic/'diagnostics-001/defect-face-ids.npz', allow_pickle=False) as a: seeds = a['parent_seed_face_ids']
    protected = expand(f, len(v), seeds)
    prior_plan = json.loads((args.prior_isotropic/'trial-001/plan.json').read_text())
    parameters = dict(prior_plan['parameters']); parameters['selectedonly'] = True
    args.output.mkdir(parents=True)
    np.save(args.output/'protected-parent-face-ids.npy', np.flatnonzero(protected))
    sources = [Path(__file__), Path(__file__).with_name('trial_isotropic.py'), Path(__file__).with_name('trial_planar_flips.py'), Path(__file__).with_name('inspect_vertex_topology.py')]
    save_json(args.output/'plan.json', {'parameters': parameters, 'gates': {**prior_plan['gates'], 'exact_oriented_protected_triangles': True},
        'source_hashes': {p.name: sha(p) for p in sources},
        'input_hashes': {name: manifest[name]['sha256'] for name in ('trial-001/parent.npz','diagnostics-001/defect-face-ids.npz')},
        'inspector_sha256': sha(args.inspector), 'seed_faces': len(seeds), 'expansion_edge_rings': 2,
        'protected_faces': int(protected.sum()), 'protected_fraction': float(protected.mean()),
        'scope': 'Study parent only; diagnostic region protection is not anatomical classification.'})
    # Mask-only witness: protected central faces of a slightly warped grid.
    cv = np.array([[x,y,.005*np.sin(x*y)] for y in range(5) for x in range(5)],float)
    cf = []
    for y in range(4):
        for x in range(4):
            a=y*5+x; cf.extend([[a,a+1,a+6],[a,a+6,a+5]])
    cf=np.array(cf,np.int32); select=np.ones(len(cf)); select[10:12]=0
    actual = {k: val for k,val in parameters.items() if not k.endswith('_mm')}
    actual['targetlen'] = ml.PureValue(parameters['targetlen_mm'])
    actual['maxsurfdist'] = ml.PureValue(parameters['maxsurfdist_mm'])
    control=ml.MeshSet(); control.add_mesh(ml.Mesh(cv,cf,f_scalar_array=select))
    control.compute_selection_by_condition_per_face(condselect='fq > 0.5')
    control.apply_filter('meshing_isotropic_explicit_remeshing', **actual)
    kept = np.isin(triangle_keys(cv,cf[10:12]), triangle_keys(control.current_mesh().vertex_matrix(), control.current_mesh().face_matrix())).all()
    if not kept: raise SystemExit('Protected-face control failed.')
    save_json(args.output/'selection-control.json', {'exact_protected_oriented_triangles': bool(kept), 'input_faces':len(cf), 'output_faces':control.current_mesh().face_number()})
    m=ml.MeshSet(); m.add_mesh(ml.Mesh(v,f.astype(np.int32),f_scalar_array=(~protected).astype(float)))
    m.compute_selection_by_condition_per_face(condselect='fq > 0.5')
    if int(m.current_mesh().face_selection_array().sum()) != int((~protected).sum()): raise SystemExit('Actual selection mismatch.')
    started=time.time(); m.apply_filter('meshing_isotropic_explicit_remeshing',**actual); elapsed=time.time()-started
    v2,f2=m.current_mesh().vertex_matrix(),m.current_mesh().face_matrix().astype(np.int64)
    np.savez_compressed(args.output/'candidate.npz',vertices=v2,triangles=f2)
    write_off(args.output/'candidate.off',v2,f2)
    protected_kept=np.isin(triangle_keys(v,f[protected]),triangle_keys(v2,f2))
    native=inspect(args.inspector,args.output/'candidate.off',args.output/'candidate-native.json')
    topo=topology(args.topology_python,Path(__file__).with_name('inspect_vertex_topology.py'),args.output/'candidate.npz',args.output/'candidate-topology.json')
    parent_topo=json.loads((args.prior_isotropic/'trial-001/parent-topology.json').read_text())
    before,after=quality(v,f),quality(v2,f2)
    cpoints=samples(v2,f2,9350602)
    p_to_c=distances(samples(v,f,9350601),v2,f2); c_to_p=distances(cpoints,v,f)
    vertex_distance=distances(v2,v,f)
    bound=prior_plan['input_bindings']
    if sha(Path(bound['--scan-arrays'])) != bound['--scan-arrays-sha256']: raise SystemExit('Scan hash mismatch.')
    with np.load(bound['--scan-arrays'],allow_pickle=False) as a: sv,sf=a['vertices'],a['triangles']
    s_to_c=distances(samples(sv,sf,9350603),v2,f2); c_to_s=distances(cpoints,sv,sf)
    checks={'native':native,'topology':topo['exit_code']==0,
        'same_euler_and_components':all(topo[k]==parent_topo[k] for k in ('euler_characteristic','edge_connected_components')),
        'exact_protected_oriented_triangles':bool(protected_kept.all()),
        'parent_sampled_deviations':max(p_to_c['sampled_max_mm'],c_to_p['sampled_max_mm'])<=.01,
        'all_candidate_vertices_to_parent':vertex_distance['sampled_max_mm']<=.01,
        'relative_volume_change':abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1)<=.0001,
        'material_quality_improvement':1-after['below_0p01']/before['below_0p01']>=.5}
    save_json(args.output/'assessment.json',{'before':before,'after':after,'vertices':len(v2),'triangles':len(f2),
        'filter_seconds':elapsed,'protected_triangles_missing_or_changed':int((~protected_kept).sum()),
        'parent_to_candidate':p_to_c,'candidate_to_parent':c_to_p,'all_candidate_vertices_to_parent':vertex_distance,
        'scan_to_candidate':s_to_c,'candidate_to_scan':c_to_s,'checks':checks,'accepted_for_volume_study':all(checks.values()),
        'functional_geometry_accepted':False,'manufacturing_authorized':False,
        'limitations':'Finite sampling is not a Hausdorff bound; diagnostic masks do not establish missing anatomy or physical feature identity.'})
    print(json.dumps({'output':str(args.output),'checks':checks,'filter_seconds':elapsed}))


if __name__ == '__main__':
    main()
