"""One projected isotropic study candidate with predeclared admission gates."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import pymeshlab as ml
from trial_planar_flips import sha, save_json, write_off, inspect, quality, samples, distances


def topology(python, script, path, output):
    run = subprocess.run([str(python), str(script), str(path)], capture_output=True,
                         text=True, timeout=300)
    result = json.loads(run.stdout); result['exit_code'] = run.returncode
    save_json(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-job', type=Path, required=True)
    parser.add_argument('--topology-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Existing output refused.')
    manifest = json.loads((args.prior_job/'manifest.json').read_text())['files']
    for name in ('inspect_surface', 'argv.json', 'trial-001/parent.off'):
        if sha(args.prior_job/name) != manifest[name]['sha256']:
            raise SystemExit('Prior artifact mismatch: '+name)
    argv = json.loads((args.prior_job/'argv.json').read_text())
    bound = {name: argv[argv.index(name)+1] for name in
             ('--solid', '--input-sha256', '--scan-arrays', '--scan-arrays-sha256')}
    for flag, expected in (('--solid', '--input-sha256'), ('--scan-arrays', '--scan-arrays-sha256')):
        if sha(Path(bound[flag])) != bound[expected]: raise SystemExit('Input hash mismatch: '+flag)
    args.output.mkdir(parents=True)
    inspector = args.prior_job/'inspect_surface'
    topology_script = Path(__file__).with_name('inspect_vertex_topology.py')
    parameters = {'iterations': 3, 'adaptive': False, 'selectedonly': False,
        'targetlen_mm': .5, 'featuredeg': 30., 'checksurfdist': True,
        'maxsurfdist_mm': .01, 'splitflag': True, 'collapseflag': True,
        'swapflag': True, 'smoothflag': True, 'reprojectflag': True}
    gates = {'parent_sampled_max_mm': .01, 'candidate_vertex_parent_max_mm': .01,
        'relative_volume_change_max': .0001, 'bad_triangle_reduction_min_fraction': .5,
        'vertex_and_closed_edge_manifold': True, 'same_euler_and_components': True,
        'zero_native_intersections_and_degeneracies': True}
    sources = [Path(__file__), Path(__file__).with_name('trial_planar_flips.py'), topology_script]
    save_json(args.output/'plan.json', {'parameters': parameters, 'gates': gates,
        'input_bindings': bound, 'source_hashes': {p.name: sha(p) for p in sources},
        'inspector_sha256': sha(inspector), 'topology_python': str(args.topology_python),
        'pymeshlab_version': importlib.metadata.version('pymeshlab'),
        'upstream_admissibility': 'Closed reconstructed assembly study; inferred closures, thin regions and unresolved anatomical identity persist.',
        'distance_limits_are_physical_tolerances': False})
    with np.load(bound['--solid'], allow_pickle=False) as a:
        used, inverse = np.unique(a['boundary'], return_inverse=True)
        v, f = a['nodes'][used], inverse.reshape((-1, 3))
    np.savez_compressed(args.output/'parent.npz', vertices=v, triangles=f)
    parent_topology = topology(args.topology_python, topology_script, args.output/'parent.npz', args.output/'parent-topology.json')
    if parent_topology['exit_code'] != 0: raise SystemExit('Parent topology failed; remesher not run.')
    # The parent CGAL audit is reused only with its exact OFF and native-report hashes.
    native_path = args.prior_job/'trial-001/parent-native.json'
    if sha(native_path) != manifest['trial-001/parent-native.json']['sha256']:
        raise SystemExit('Parent native assessment checksum mismatch.')
    if json.loads(native_path.read_text())['exit_code'] != 0: raise SystemExit('Parent native audit failed.')
    before = quality(v, f)
    # Closed tetrahedron smoke control checks this exact filter invocation first.
    cv = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,1]], float)
    cf = np.array([[0,2,1], [0,1,3], [0,3,2], [1,2,3]], np.int32)
    actual = {k: val for k, val in parameters.items() if not k.endswith('_mm')}
    actual['targetlen'] = ml.PureValue(parameters['targetlen_mm'])
    actual['maxsurfdist'] = ml.PureValue(parameters['maxsurfdist_mm'])
    control = ml.MeshSet(); control.add_mesh(ml.Mesh(cv, cf))
    control.apply_filter('meshing_isotropic_explicit_remeshing', **actual)
    write_off(args.output/'control.off', control.current_mesh().vertex_matrix(), control.current_mesh().face_matrix())
    if not inspect(inspector, args.output/'control.off', args.output/'control-native.json'):
        raise SystemExit('Remesher smoke control failed.')
    m = ml.MeshSet(); m.add_mesh(ml.Mesh(v, f.astype(np.int32)))
    started = time.time(); m.apply_filter('meshing_isotropic_explicit_remeshing', **actual)
    elapsed = time.time()-started
    v2, f2 = m.current_mesh().vertex_matrix(), m.current_mesh().face_matrix().astype(np.int64)
    np.savez_compressed(args.output/'candidate.npz', vertices=v2, triangles=f2)
    write_off(args.output/'candidate.off', v2, f2)
    native = inspect(inspector, args.output/'candidate.off', args.output/'candidate-native.json')
    candidate_topology = topology(args.topology_python, topology_script, args.output/'candidate.npz', args.output/'candidate-topology.json')
    after = quality(v2, f2)
    parent_points, candidate_points = samples(v, f, 9350501), samples(v2, f2, 9350502)
    p_to_c, c_to_p = distances(parent_points, v2, f2), distances(candidate_points, v, f)
    vertices_to_parent = distances(v2, v, f)
    with np.load(bound['--scan-arrays'], allow_pickle=False) as a: sv, sf = a['vertices'], a['triangles']
    s_to_c = distances(samples(sv, sf, 9350503), v2, f2)
    c_to_s = distances(candidate_points, sv, sf)
    reduction = 1-after['below_0p01']/before['below_0p01']
    checks = {'native': native, 'topology': candidate_topology['exit_code'] == 0,
        'same_euler_and_components': all(candidate_topology[k] == parent_topology[k] for k in ('euler_characteristic','edge_connected_components')),
        'parent_sampled_deviations': max(p_to_c['sampled_max_mm'], c_to_p['sampled_max_mm']) <= .01,
        'all_candidate_vertices_to_parent': vertices_to_parent['sampled_max_mm'] <= .01,
        'relative_volume_change': abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1) <= .0001,
        'material_quality_improvement': reduction >= .5}
    for flag, expected in (('--solid','--input-sha256'),('--scan-arrays','--scan-arrays-sha256')):
        if sha(Path(bound[flag])) != bound[expected]: raise SystemExit('Input changed during trial.')
    save_json(args.output/'assessment.json', {'before': before, 'after': after,
        'filter_seconds': elapsed, 'vertices': len(v2), 'triangles': len(f2),
        'bad_triangle_reduction_fraction': reduction, 'parent_to_candidate': p_to_c,
        'candidate_to_parent': c_to_p, 'all_candidate_vertices_to_parent': vertices_to_parent,
        'scan_to_candidate': s_to_c, 'candidate_to_scan': c_to_s, 'checks': checks,
        'accepted_for_volume_study': all(checks.values()), 'source_inputs_unchanged': True,
        'functional_geometry_accepted': False, 'manufacturing_authorized': False,
        'limitations': 'Surface samples are not Hausdorff bounds. No accepted anatomical crease/interface mask exists; feature-angle preservation and topology cannot prove physical feature fidelity.'})
    print(json.dumps({'output': str(args.output), 'checks': checks, 'filter_seconds': elapsed}))


if __name__ == '__main__':
    main()
