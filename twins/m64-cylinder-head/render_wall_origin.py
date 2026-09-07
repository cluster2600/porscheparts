#!/usr/bin/env python3
"""Render exact-input CAD tessellation and diagnostic cut, with private probes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'envelope', 'probes', 'attribution', 'origin-report'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--helpers', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.origin_report.read_text())
    for name in ('step', 'envelope', 'probes', 'attribution'):
        if hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() != report['source_sha256'][name]:
            raise ValueError(name+' provenance mismatch')
    args.output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import trimesh
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    meshes = []
    for name in ('step', 'envelope'):
        shape = read_step(getattr(args, name))[0]
        mesher = BRepMesh_IncrementalMesh(shape, .15, False, .2, False)
        if not mesher.IsDone():
            raise RuntimeError('CAD tessellation failed')
        path = args.output / (name+'-private.stl')
        writer = StlAPI_Writer()
        if not writer.Write(shape, str(path)):
            raise RuntimeError('STL export failed')
        meshes.append(trimesh.load_mesh(path))
    probes = np.load(args.probes)
    attribution = json.loads(args.attribution.read_text())
    old = {r['probe_index_private']: r for r in attribution['records_private']}
    rows = [r for r in report['records_private'] if r.get('faces_share_edge') is False
            and r['origin'] in ('inherited_envelope', 'candidate_cut_boundary')]
    if not rows:
        raise ValueError('no resolved nonadjacent wall probe for cut')
    selected = min(rows, key=lambda r: r['candidate_ray_scan_units'])
    i = selected['probe_index_private']
    point, ray = probes['points'][i], -probes['normals'][i]
    first = point + ray*old[i]['entry_offset_scan_units']
    second = first + ray*selected['candidate_ray_scan_units']
    u = ray / np.linalg.norm(ray)
    reference = np.array([0., 0., 1.]) if abs(u[2]) < .9 else np.array([0., 1., 0.])
    normal = np.cross(u, reference)
    normal /= np.linalg.norm(normal)
    v = np.cross(normal, u)

    fig = plt.figure(figsize=(16, 8), facecolor='#f4f6f7')
    grid = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=.05)
    ax = fig.add_subplot(grid[0], projection='3d')
    mesh = meshes[0]
    # All tessellated faces are rendered, without geometrical decimation.
    triangles = mesh.triangles
    light = np.array([.3, -.4, .85]); light /= np.linalg.norm(light)
    intensity = .40 + .50*np.clip(mesh.face_normals @ light, 0, 1)
    colors = np.column_stack((intensity*.82, intensity*.90, intensity, np.ones(len(intensity))))
    ax.add_collection3d(Poly3DCollection(triangles, facecolors=colors, edgecolor='none'))
    bounds = mesh.bounds
    center = bounds.mean(axis=0)
    radius = max(mesh.extents)*.53
    ax.set_xlim(center[0]-radius, center[0]+radius)
    ax.set_ylim(center[1]-radius, center[1]+radius)
    ax.set_zlim(center[2]-radius, center[2]+radius)
    ax.set_box_aspect((1,1,1)); ax.view_init(elev=28, azim=-55)
    ax.set_axis_off()
    ax.set_title('CAO 4V F53 actuelle\nAucune modification dans cet audit', fontsize=14)
    ax.scatter(*first, color='#d55e00', s=90, depthshade=False)
    ax.text(*first, '  Coupe locale', color='#d55e00', fontsize=11)

    cut = fig.add_subplot(grid[1])
    for item, color, label, style in zip(meshes, ('#0072b2', '#d55e00'),
                                       ('Candidat 4V F53', 'Enveloppe source F43'), ('-', '--')):
        section = item.section(plane_origin=first, plane_normal=normal)
        if section is None:
            raise RuntimeError('empty diagnostic section')
        for n, line in enumerate(section.discrete):
            relative = line-first
            cut.plot(relative@u, relative@v, color=color, linestyle=style,
                     lw=1.6, label=label if n==0 else None)
    cut.plot([0, selected['candidate_ray_scan_units']], [0, 0], color='#cc0000', lw=4,
             marker='o', markersize=5, label='Trajet faible OCCT exact')
    cut.annotate(f"{selected['candidate_ray_scan_units']:.3f} unité du scan",
                 xy=(selected['candidate_ray_scan_units']*.5, 0), xytext=(2, 2),
                 arrowprops={'arrowstyle':'->', 'color':'#cc0000'}, color='#a00000', fontsize=11)
    cut.set_xlim(-6, 7); cut.set_ylim(-6, 7); cut.set_aspect('equal')
    cut.set_xlabel('Coordonnée locale le long du rayon — unité du scan')
    cut.set_ylabel('Coordonnée locale dans la coupe — unité du scan')
    cut.set_title('Même coupe dans les deux géométries\nPoint choisi parmi les faces non adjacentes', fontsize=14)
    cut.grid(alpha=.2); cut.legend(loc='lower left', fontsize=10)
    fig.suptitle('Référence 935 issue du scan — diagnostic des faibles épaisseurs',
                 fontsize=20, weight='bold', y=.97)
    counts = report['summary']['origin_counts']
    fig.text(.5, .08,
             f"Trajets hérités de l’enveloppe : {counts.get('inherited_envelope', 0)}   |   "
             f"Créés par les découpes : {counts.get('candidate_cut_boundary', 0)}   |   "
             f"Non résolus : {counts.get('prior_unresolved', 0)}",
             ha='center', fontsize=13)
    fig.text(.5, .035, 'Compatibilité M64 et échelle absolue non validées — fabrication non autorisée.\n'
             'Coupe affichée sur tessellation CAO (déflexion 0,15) ; longueur rouge mesurée sur STEP par OCCT.',
             ha='center', fontsize=11, color='#6b3131')
    fig.subplots_adjust(top=.83, bottom=.19)
    path = args.output / '935-reference-wall-origin-diagnostic.png'
    fig.savefig(path, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    metadata = {'source_sha256': report['source_sha256'],
                'origin_report_sha256': hashlib.sha256(args.origin_report.read_bytes()).hexdigest(),
                'output_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'triangle_counts': [len(m.faces) for m in meshes],
                'geometry_modified': False, 'manufacturing_authorized': False}
    (args.output/'render-report.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
