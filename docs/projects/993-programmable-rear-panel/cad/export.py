#!/usr/bin/env python3
"""Inspect native PicoGK STL parts, then export a coloured GLB and review image."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

if len(sys.argv) != 3:
    raise SystemExit('Usage: export.py NATIVE_OUTPUT_DIR NEW_EXPORT_DIR')
native, output = map(Path, sys.argv[1:])
if output.exists() or output.is_symlink():
    raise SystemExit('Output already exists; refusing to overwrite.')
report = json.loads((native / 'geometry.json').read_text())
assert report['status'] == 'visual_concept_not_oem_not_for_manufacturing'
assert report['units'] == 'mm' and not report['is_manufacturing_release']
assert report['vehicle_interfaces'] is None and report['hardware_resolution'] is None
names = ['lens', 'housing', 'rear-cover', 'display-envelope']
assert [p['id'] for p in report['parts']] == names
colours = [(160, 12, 28, 255), (33, 37, 43, 255), (62, 69, 79, 255), (33, 112, 98, 255)]
meshes = []
checks = []
for part in report['parts']:
    path = native / (part['id'] + '.stl')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == part['sha256'], 'Native STL changed'
    mesh = trimesh.load_mesh(path, process=False)
    assert len(mesh.faces) == part['triangles'] and np.isfinite(mesh.vertices).all()
    bounds = mesh.bounds.copy()
    # STL repeats vertices per triangle; weld coincident vertices without changing the surface.
    mesh.merge_vertices(digits_vertex=5)
    mesh.update_faces(mesh.nondegenerate_faces(height=0.00001))
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    assert np.allclose(mesh.bounds, bounds, atol=0.00001)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, part['id']
    assert len(mesh.split(only_watertight=False)) == 1, part['id']
    assert mesh.euler_number == (0 if part['id'] == 'housing' else 2), part['id']
    p = report['parameters']
    assert abs(mesh.extents[0] - (p['width_mm'] - (2 * p['display_margin_mm'] if part['id'] == 'display-envelope' else 0))) <= 2 * p['voxel_mm']
    assert abs(mesh.extents[2] - (p['height_mm'] - (2 * p['display_margin_mm'] if part['id'] == 'display-envelope' else 0))) <= 2 * p['voxel_mm']
    meshes.append(mesh)
    checks.append(dict(id=part['id'], triangles_native=part['triangles'], triangles_export=len(mesh.faces),
                       watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
                       components=1, euler=int(mesh.euler_number), volume_mm3=float(mesh.volume),
                       bounds_mm=mesh.bounds.tolist(), self_intersection_checked=False))
output.mkdir(parents=True)
scene = trimesh.Scene()
# glTF uses metres and Y-up; native STL remains in millimetres and Z-up.
transform = np.array([[.001, 0, 0, 0], [0, 0, .001, 0], [0, -.001, 0, 0], [0, 0, 0, 1]])
for name, mesh, colour in zip(names, meshes, colours):
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name=name, baseColorFactor=colour, metallicFactor=0,
        roughnessFactor=.25 if name == 'lens' else .7))
    scene.add_geometry(mesh, geom_name=name, node_name=name, transform=transform)
scene.metadata['status'] = report['status']
scene.export(output / 'rear-panel-concept.glb')
reread = trimesh.load(output / 'rear-panel-concept.glb', force='scene')
assert len(reread.geometry) == 4
assert np.allclose(scene.bounds, reread.bounds, atol=1e-6), 'GLB unit/axis roundtrip failed'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
fig = plt.figure(figsize=(15, 10), facecolor='#edf0f2')
fig.text(.055, .96, '993 / Programmable rear panel', fontsize=24, color='#222b35', weight='bold')
fig.text(.055, .928, 'VISUAL CONCEPT · Provisional dimensions · No OEM fitment or manufacturing validation', fontsize=11, color='#a21324')
direction = np.array([.23, .91, .35]); direction /= np.linalg.norm(direction)
right = np.array([direction[1], -direction[0], 0]); right /= np.linalg.norm(right)
up = np.cross(right, direction)
light = np.array([-.25, .75, .6]); light /= np.linalg.norm(light)
for index, exploded in enumerate((False, True), 1):
    ax = fig.add_subplot(2, 1, index, facecolor='#edf0f2')
    polygons, depths, colours_2d = [], [], []
    for name, mesh, colour in zip(names, meshes, colours):
        vertices = mesh.vertices.copy()
        if exploded:
            vertices[:, 1] += {'lens': 90, 'display-envelope': 30, 'housing': -40, 'rear-cover': -105}[name]
        visible = mesh.face_normals @ direction > 0
        faces = mesh.faces[visible]
        triangles = vertices[faces]
        polygons.append(np.stack((triangles @ right, triangles @ up), axis=-1))
        depths.append(triangles.mean(axis=1) @ direction)
        shade = .45 + .55 * np.clip(mesh.face_normals[visible] @ light, 0, 1)
        colours_2d.append(shade[:, None] * np.array(colour[:3])[None, :] / 255)
    polygons = np.concatenate(polygons); order = np.argsort(np.concatenate(depths))
    ax.add_collection(PolyCollection(polygons[order], facecolors=np.concatenate(colours_2d)[order],
                                    edgecolors='none', antialiaseds=False, rasterized=True))
    ax.autoscale_view(); ax.margins(.055); ax.set_aspect('equal'); ax.set_axis_off()
    ax.set_title('EXPLODED · Lens / display space / housing / rear cover' if exploded else 'ASSEMBLED · Curved red front face', fontsize=11, loc='left', color='#394650', pad=8)
fig.text(.055, .052, f"Concept inputs: {p['width_mm']:g} × {p['height_mm']:g} mm front · {p['depth_mm']:g} mm body depth · {p['bow_mm']:g} mm bow", fontsize=12, color='#222b35')
fig.text(.055, .025, 'Display volume is a packaging allowance, not a routed PCB. Vehicle mounts and regulatory optics are not modelled.', fontsize=10, color='#5b646b')
fig.subplots_adjust(left=.05, right=.95, bottom=.09, top=.87, hspace=.1)
fig.savefig(output / 'preview.png', dpi=110, facecolor=fig.get_facecolor())
plt.close(fig)
(output / 'checks.json').write_text(json.dumps(dict(
    status=report['status'], parameters=report['parameters'], meshes=checks,
    glb_parts=4, glb_units='metres', glb_up_axis='Y', glb_roundtrip=True,
    physical_fit_checked=False, fastening_design_complete=False, optical_performance_checked=False,
    thermal_checked=False, manufacturing_authorized=False,
    source_hashes={name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                   for name in ('Program.cs', 'RearPanel.csproj', 'concept.json', 'packages.lock.json', 'export.py')},
    exports={name: hashlib.sha256((output / name).read_bytes()).hexdigest()
             for name in ('rear-panel-concept.glb', 'preview.png')}
), indent=2) + '\n')
print(json.dumps(checks, indent=2))
