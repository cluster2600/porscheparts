"""Regularize the four largest frozen core components using native solid unions."""
import argparse
import hashlib
import json
import signal
import time
from importlib.metadata import version
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ['selected', 'reference', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Fresh output required')
    import manifold3d as mf
    assert version('manifold3d') == '3.5.4'
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    r = json.loads(a.reference.read_text())
    assert r['status'] == 'frozen_selected_core_face_connectivity_inspected' and sha(a.selected) == r['selected_volume_sha256']
    z = np.load(a.selected); vertices = z['vertices']; cells = z['tetrahedra']; labels = z['component_labels']
    faces = np.array([[0,2,1], [0,1,3], [0,3,2], [1,2,3]], dtype=np.uint64)
    control = np.array([[0.,0,0], [1,0,0], [0,1,0], [0,0,1]])
    test = mf.Manifold(mf.Mesh64(control, faces))
    assert test.status() == mf.Error.NoError and abs(test.volume()-1/6) < 1e-12
    assert abs(mf.Manifold.batch_boolean([test,test], mf.OpType.Add).volume()-1/6) < 1e-12
    a.output.mkdir(); start = time.monotonic(); signal.alarm(300)
    plan = dict(scope='Four largest analysis-core envelopes only; no carrier cut or lattice', wall_limit_seconds=300,
                retained_component_ids=[x['component'] for x in r['components'][:4]], source_sha256={str(f):sha(f) for f in [Path(__file__),a.selected,a.reference]})
    (a.output/'contract.json').write_text(json.dumps(plan, indent=2)+'\n')
    rows = []; all_vertices = []; all_faces = []
    for rank, component in enumerate(r['components'][:4]):
        c = cells[labels == component['component']]; x = vertices[c]; origin = (x.min((0,1))+x.max((0,1)))/2
        determinant = np.linalg.det((x[:,1:]-x[:,0,None,:]).transpose(0,2,1))
        assert np.all(determinant > 0)
        solids = [mf.Manifold(mf.Mesh64(t-origin, faces)) for t in x]
        assert all(s.status() == mf.Error.NoError for s in solids)
        solid = mf.Manifold.batch_boolean(solids, mf.OpType.Add)
        assert solid.status() == mf.Error.NoError
        mesh = solid.to_mesh64(); v = np.asarray(mesh.vert_properties)[:,:3]+origin; f = np.asarray(mesh.tri_verts)
        distance, _ = cKDTree(x.reshape(-1,3)).query(v)
        expected_volume = float(determinant.sum()/6)
        relative_volume_error = abs(solid.volume()-expected_volume)/expected_volume
        assert relative_volume_error <= 1e-10 and distance.max() <= 1e-10
        edges = np.concatenate([f[:,e] for e in [[0,1],[1,2],[2,0]]]); _, incidence = np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
        assert np.all(incidence == 2)
        row = dict(rank=rank, parent_component=component['component'], tetrahedra=len(c), triangles=len(f), vertices=len(v),
                   native_status=str(solid.status()), native_components=len(solid.decompose()), volume_mm3=solid.volume(),
                   relative_volume_error=relative_volume_error, maximum_vertex_distance_to_input_mm=float(distance.max()),
                   boundary_edge_incidence_two=True, source_envelope_only=True)
        rows.append(row)
        with (a.output/f'envelope-{rank}.obj').open('w') as out:
            np.savetxt(out,v,fmt='v %.17g %.17g %.17g'); np.savetxt(out,f+1,fmt='f %d %d %d')
        all_faces.append(f+sum(len(q) for q in all_vertices)); all_vertices.append(v)
        (a.output/'progress.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(row),flush=True)
    np.savez_compressed(a.output/'envelopes.npz', vertices=np.concatenate(all_vertices), triangles=np.concatenate(all_faces))
    signal.alarm(0)
    report = dict(status='four_largest_core_envelopes_regularized_by_native_solid_union', components=rows,
                  retained_volume_mm3=sum(row['volume_mm3'] for row in rows), original_selected_volume_mm3=r['selected_volume_mm3'],
                  discarded_small_component_count=r['face_connected_components']-4, source_sha256=plan['source_sha256'],
                  manifold_version=version('manifold3d'), elapsed_seconds=time.monotonic()-start,
                  vertex_motion_limit_mm=1e-10, relative_volume_limit=1e-10,
                  carrier_geometry_changed=False, cellular_carrier_generated=False, manufacturing_authorized=False,
                  output_sha256={f.name:sha(f) for f in a.output.glob('*.obj')})
    report['output_sha256']['envelopes.npz'] = sha(a.output/'envelopes.npz')
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
