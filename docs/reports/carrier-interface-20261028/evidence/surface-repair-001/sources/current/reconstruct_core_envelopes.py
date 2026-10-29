"""Regularize the four largest frozen core components using native solid unions."""
import argparse
import hashlib
import json
import signal
import time
from importlib.metadata import version
from pathlib import Path
import numpy as np


def canonical_surface(vertices, faces):
    unique, inverse = np.unique(vertices, axis=0, return_inverse=True)
    triangles = inverse[faces]
    first = triangles.argmin(axis=1)
    triangles = np.take_along_axis(triangles, (first[:,None]+np.arange(3))%3, axis=1)
    return unique, triangles[np.lexsort(triangles.T[::-1])]


def boundary_clearance(vertices, faces, raw_vertices, raw_cells):
    import igl
    import pyvista as pv
    grid = pv.UnstructuredGrid({pv.CellType.TETRA:raw_cells}, raw_vertices)
    raw_faces = np.concatenate([raw_cells[:,f] for f in [[0,1,2],[0,1,3],[0,2,3],[1,2,3]]])
    _, first, counts = np.unique(np.sort(raw_faces,axis=1),axis=0,return_index=True,return_counts=True)
    assert counts.max() <= 2
    raw_faces = raw_faces[first[counts == 1]]
    raw_x = raw_vertices[raw_cells]
    raw_inverse = np.linalg.inv((raw_x[:,1:]-raw_x[:,0,None,:]).transpose(0,2,1))
    pending = vertices[faces]; queries = 0; fallbacks = 0; lower_bound = float('inf')
    for depth in range(11):
        centre = pending.mean(1); queries += len(centre)
        assert queries <= 1000000
        cell = grid.find_containing_cell(centre)
        assert np.all(cell >= 0)
        candidate = np.einsum('nij,nj->ni',raw_inverse[cell],centre-raw_x[cell,0])
        rejected = (candidate.min(1) < -1e-10) | (candidate.sum(1) > 1+1e-10)
        # VTK's candidate locator admits nearby cells; retain the strict barycentric gate.
        for i in np.flatnonzero(rejected):
            b = np.einsum('nij,nj->ni',raw_inverse,centre[i]-raw_x[:,0])
            matches = np.flatnonzero((b.min(1) >= -1e-11) & (b.sum(1) <= 1+1e-11))
            assert len(matches)
            cell[i] = matches[0]; fallbacks += 1
        x = raw_vertices[raw_cells[cell]]
        J = (x[:,1:]-x[:,0,None,:]).transpose(0,2,1)
        b = np.linalg.solve(J,(centre-x[:,0])[...,None])[...,0]
        assert b.min() >= -1e-10 and b.sum(1).max() <= 1+1e-10
        assert abs(np.einsum('nij,nj->ni',J,b)+x[:,0]-centre).max() <= 1e-10
        d,_,_ = igl.point_mesh_squared_distance(centre,raw_vertices,raw_faces)
        radius = np.linalg.norm(pending-centre[:,None,:],axis=2).max(1)
        bound = np.sqrt(d)-radius
        accepted = bound >= .0001
        if accepted.any():lower_bound = min(lower_bound,float(bound[accepted].min()))
        if accepted.all():
            return dict(floating_point_whole_boundary_clearance_lower_bound_mm=lower_bound,
                        verified_subtriangle_centres=queries, maximum_subdivision_depth=depth,
                        approximate_locator_candidates_replaced=fallbacks,
                        distance_guard_mm=.0001, membership_residual_limit_mm=1e-10,
                        formal_interval_certificate=False)
        t = pending[~accepted]; a,b,c = t[:,0],t[:,1],t[:,2]
        ab,bc,ca = (a+b)/2,(b+c)/2,(c+a)/2
        pending = np.concatenate([np.stack(q,axis=1)for q in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]])
    raise ValueError('Bounded whole-boundary clearance proof did not finish')


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
    erosion = mf.Manifold.cube((.2,.2,.2),True)
    assert abs(mf.Manifold.cube((1,1,1),True).minkowski_difference(erosion).volume()-.8**3) < 1e-12
    a.output.mkdir(); start = time.monotonic(); signal.alarm(300)
    plan = dict(scope='Four largest analysis-core envelopes with conservative cube erosion; no carrier cut or lattice', wall_limit_seconds=300,
                erosion_cube_side_mm=.2, erosion_minimum_inset_mm=.1, exported_triangle_geometry_must_roundtrip_exactly=True,
                retain_only_dominant_positive_connected_body_per_region=True,
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
        expected_volume = float(determinant.sum()/6)
        union_error = abs(solid.volume()-expected_volume)/expected_volume
        assert union_error <= 1e-10
        solid = solid.minkowski_difference(erosion)
        assert solid.status() == mf.Error.NoError and 0 < solid.volume() < expected_volume
        pieces = solid.decompose()
        assert all(part.volume() > 0 for part in pieces)
        eroded_volume = solid.volume()
        solid = max(pieces,key=lambda part:part.volume())
        assert len(solid.decompose()) == 1
        mesh = solid.to_mesh64(); v = np.asarray(mesh.vert_properties)[:,:3]+origin; f = np.array(mesh.tri_verts,dtype=np.uint64,copy=True)
        imported = mf.Manifold(mf.Mesh64(v,f))
        assert imported.status() == mf.Error.NoError
        back = imported.to_mesh64(); canonical = canonical_surface(v,f)
        assert all(np.array_equal(a,b)for a,b in zip(canonical,canonical_surface(np.asarray(back.vert_properties)[:,:3],np.asarray(back.tri_verts))))
        t = v[f]-origin
        independent_volume = float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
        relative_volume_error = max(abs(independent_volume-solid.volume()),abs(imported.volume()-solid.volume()))/solid.volume()
        assert relative_volume_error <= 1e-10
        used, raw_inverse = np.unique(c,return_inverse=True)
        clearance = boundary_clearance(v,f,vertices[used],raw_inverse.reshape(-1,4))
        edges = np.concatenate([f[:,e] for e in [[0,1],[1,2],[2,0]]]); _, incidence = np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
        assert np.all(incidence == 2)
        row = dict(rank=rank, parent_component=component['component'], tetrahedra=len(c), triangles=len(f), vertices=len(v),
                   native_status=str(solid.status()), native_components=len(solid.decompose()), volume_mm3=solid.volume(),
                   original_component_volume_mm3=expected_volume, union_relative_volume_error=union_error,
                   eroded_components_before_selection=len(pieces), discarded_eroded_component_volume_mm3=eroded_volume-solid.volume(),
                   relative_export_volume_error=relative_volume_error, exact_oriented_triangle_roundtrip=True,
                   native_component_signed_volumes_mm3=[part.volume()for part in solid.decompose()], clearance=clearance,
                   boundary_edge_incidence_two=True, source_envelope_only=True)
        rows.append(row)
        with (a.output/f'envelope-{rank}.obj').open('w') as out:
            np.savetxt(out,v,fmt='v %.17g %.17g %.17g'); np.savetxt(out,f+1,fmt='f %d %d %d')
        all_faces.append(f+sum(len(q) for q in all_vertices)); all_vertices.append(v)
        (a.output/'progress.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(row),flush=True)
    np.savez_compressed(a.output/'envelopes.npz', vertices=np.concatenate(all_vertices), triangles=np.concatenate(all_faces))
    signal.alarm(0)
    report = dict(status='four_largest_core_envelopes_conservatively_eroded_and_transfer_checked', components=rows,
                  retained_volume_mm3=sum(row['volume_mm3'] for row in rows), original_selected_volume_mm3=r['selected_volume_mm3'],
                  discarded_small_component_count=r['face_connected_components']-4, source_sha256=plan['source_sha256'],
                  manifold_version=version('manifold3d'), elapsed_seconds=time.monotonic()-start,
                  erosion_cube_side_mm=.2, minimum_erosion_inset_mm=.1, relative_export_volume_limit=1e-10,
                  carrier_geometry_changed=False, cellular_carrier_generated=False, manufacturing_authorized=False,
                  output_sha256={f.name:sha(f) for f in a.output.glob('*.obj')})
    report['output_sha256']['envelopes.npz'] = sha(a.output/'envelopes.npz')
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
