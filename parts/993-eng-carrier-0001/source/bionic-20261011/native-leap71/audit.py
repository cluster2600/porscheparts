"""Independent raw-surface and assumed-interface checks; no physical approval."""
import json
from pathlib import Path
import sys

import numpy as np

from prepare import sha


def mesh_check(path):
    import trimesh
    raw = trimesh.load_mesh(path, process=False)
    assert np.isfinite(raw.vertices).all()
    vertices, inverse = np.unique(raw.vertices, axis=0, return_inverse=True)
    mesh = trimesh.Trimesh(vertices, inverse[raw.faces], process=False)
    # Keep raw topology separate from the explicitly reported zero-area cleanup.
    keep = mesh.area_faces > 0
    normalized = trimesh.Trimesh(vertices, mesh.faces[keep], process=False)
    return mesh, normalized, {'triangles': len(mesh.faces), 'exact_unique_vertices': len(vertices),
                  'degenerate_faces': int((mesh.area_faces <= 1e-12).sum()),
                  'watertight': bool(mesh.is_watertight),
                  'winding_consistent': bool(mesh.is_winding_consistent),
                  'surface_components': len(mesh.split(only_watertight=False)),
                  'volume_mm3': float(mesh.volume),
                  'nominal_mass_kg': float(mesh.volume)*4.42e-6,
                  'bounds_mm': mesh.bounds.tolist(),
                  'normalization': {'operation': 'Remove exactly zero-area faces only; original file unchanged',
                                    'removed_faces': int((~keep).sum()),
                                    'watertight': bool(normalized.is_watertight),
                                    'winding_consistent': bool(normalized.is_winding_consistent),
                                    'surface_components': len(normalized.split(only_watertight=False))}}


def protected_points(vertices):
    x, y, z = vertices.T
    mask = (abs(x) < 79) | ((abs(x) > 256) & (abs(y) < 29))
    for cx, cy in ((-160, -26), (-180, -23)):
        mask |= (x-cx)**2+(y-cy)**2 < 7**2
    return vertices[mask & (z > -21) & (z < 31)]


def audit(folder, transfer, original_stl):
    import trimesh
    from scipy.spatial import cKDTree
    folder, transfer = Path(folder), Path(transfer)
    native = json.loads((folder/'native-results.json').read_text())
    inputs = json.loads((transfer/'transfer.json').read_text())
    assert sha(folder/'carrier-fields.vdb') == native['vdb']['sha256']
    assert sha(transfer/'samples.json') == inputs['samples_sha256'] == native['source_samples_sha256']
    assert sha(original_stl) == native['source_geometry_sha256']
    meshes, normalized, checks = {}, {}, {}
    for name in ('baseline', 'candidate', 'addition'):
        assert sha(folder/(name+'.stl')) == native['exports'][name]['sha256']
        meshes[name], normalized[name], checks[name] = mesh_check(folder/(name+'.stl'))
    _, original, original_check = mesh_check(original_stl)
    probe_meshes_valid = all(m.is_watertight and m.is_winding_consistent
                             for m in [original, normalized['baseline'], normalized['candidate']])
    assert probe_meshes_valid, 'Closed consistently oriented meshes are required for interior probes'
    before, after = meshes['baseline'], meshes['candidate']
    distances = []
    for a, b in ((before, after), (after, before)):
        points = protected_points(a.vertices)
        assert len(points)>0
        distances.append({'samples': len(points), 'maximum_nearest_vertex_distance_mm': float(cKDTree(b.vertices).query(points)[0].max())})
    assert trimesh.creation.box().contains([[0, 0, 0], [5, 0, 0]]).tolist() == [True, False]
    angle = np.arange(32)*2*np.pi/32
    holes = []
    for x, y, radius, half_length, axis in [
            *[(x,y,4.5,6,'Z') for x in (-48,48) for y in (-23,23)],
            *[(x,0,5.75,25,'Y') for x in (-280,280)],
            (-160,-26,1,6,'Z'),(-180,-23,1,6,'Z')]:
        probes = np.array([[x+r*np.cos(a), y+r*np.sin(a), z] if axis=='Z'
                           else [x+r*np.cos(a),z,r*np.sin(a)]
                           for z in np.linspace(-half_length,half_length,9)
                           for r in (0,radius) for a in angle])
        hits = {name: mesh.contains(probes) for name, mesh in [('original',original),
                ('baseline',normalized['baseline']),('candidate',normalized['candidate'])]}
        holes.append({'centre_xy_mm': [x,y], 'axis': axis, 'interior_probe_radius_mm': radius,
                      'samples': len(probes), **{name+'_solid_hits': int(hit.sum()) for name, hit in hits.items()},
                      'first_candidate_hit_mm': probes[hits['candidate']][0].tolist() if hits['candidate'].any() else None})
    protected_pass = all(d['maximum_nearest_vertex_distance_mm'] < 1e-5 for d in distances)
    bores_pass = all(h['baseline_solid_hits']==0 and h['candidate_solid_hits']==0 for h in holes)
    surface_pass = all(checks[n]['watertight'] and checks[n]['winding_consistent']
                       and checks[n]['degenerate_faces']==0 for n in ('baseline','candidate'))
    connected = checks['candidate']['surface_components'] == checks['baseline']['surface_components'] == 1
    # Both native volume and exact-vertex STL volume must remain below the ceiling.
    mass = max(checks['candidate']['nominal_mass_kg'], native['exports']['candidate']['nominal_mass_kg'])
    report = {'status': 'rejected_mass_ceiling' if mass>1.2 else 'unqualified_trial',
              'original_STL_sha256': sha(original_stl), 'original_mesh': original_check,
              'meshes': checks, 'protected_surface_comparison': distances,
              'protected_surface_pass': protected_pass, 'eight_bore_probe_pass': bores_pass,
              'six_primary_bore_probe_pass': all(h['candidate_solid_hits']==0 for h in holes[:6]),
              'probe_meshes_closed_after_explicit_normalization': probe_meshes_valid,
              'bore_probes': holes, 'raw_surface_pass': surface_pass,
              'single_surface_component': connected,
              'mass_ceiling_kg': 1.2, 'mass_screen_pass': mass<=1.2,
              'nominal_added_mass_kg': checks['candidate']['nominal_mass_kg']-checks['baseline']['nominal_mass_kg'],
              'voxel_baseline_mass_error_vs_STEP_percent': 100*(checks['baseline']['nominal_mass_kg']/1.1847637923029735-1),
              'part_height_preserved': bool(np.allclose(before.bounds[:,2],after.bounds[:,2],atol=1e-5)),
              'topology_qualified': False, 'OEM_interfaces_measured': False,
              'field_mapping_is_sparse_diagnostic': True, 'candidate_solver_executed': False,
              'candidate_fatigue_life': None, 'manufacturing_authorized': False,
              'source_geometry_modified': False}
    if not (protected_pass and bores_pass and surface_pass and connected):
        report['status'] = 'rejected_geometry_audit'
    (folder/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    render(meshes, report, folder)
    print(json.dumps({k:report[k] for k in ('status','mass_screen_pass','nominal_added_mass_kg','protected_surface_pass','eight_bore_probe_pass','raw_surface_pass','single_surface_component')}))


def render(meshes, report, folder):
    import pyvista as pv
    plot = pv.Plotter(off_screen=True, shape=(2,1), window_size=(1600,1100))
    for row in (0,1):
        plot.subplot(row,0); plot.set_background('#f5f5f0')
        for name, colour, opacity in [('baseline','#91a0ab',.35),('addition','#087f8c',1.)]:
            m=meshes[name]
            poly=pv.PolyData(m.vertices,np.c_[np.full(len(m.faces),3),m.faces])
            plot.add_mesh(poly,color=colour,opacity=opacity)
        if row==0:
            plot.camera_position=[(620,-850,700),(0,0,0),(0,0,1)]
            title='Native Mac trial | ShapeKernel masks + LatticeLibrary BCC'
        else:
            plot.camera_position=[(185,-200,200),(175,0,0),(0,0,1)]
            title='2 mm beams / 16 mm cells | added material shown in teal'
        plot.enable_parallel_projection(); plot.reset_camera()
        if row==1: plot.camera.zoom(2.6)
        plot.add_text(title,font_size=15,color='#142834',position='upper_left')
        plot.add_text(f"Trial {report['meshes']['candidate']['nominal_mass_kg']:.3f} kg | ceiling 1.200 kg | {report['status']}\nProvisional dimensions; no new structural solve or manufacturing approval",font_size=12,color='#7b2929',position='lower_left')
    plot.screenshot(folder/'native-trial.png'); plot.close()


if __name__=='__main__':
    if len(sys.argv)!=4:
        raise SystemExit('Usage: audit.py NATIVE_OUTPUT TRANSFER_FOLDER ORIGINAL_V5_STL')
    audit(*sys.argv[1:])
