#!/usr/bin/env python3
"""Plot the actual CAD section before/after a private rejected-or-pending trial."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'report', 'patches', 'helpers', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    report = json.loads(args.report.read_text())
    patches = json.loads(args.patches.read_text())
    if hashlib.sha256(args.baseline.read_bytes()).hexdigest() != report['source_sha256']['step']:
        raise ValueError('baseline provenance mismatch')
    if hashlib.sha256(args.candidate.read_bytes()).hexdigest() != report['candidate_sha256']:
        raise ValueError('candidate provenance mismatch')
    if patches['source_sha256'] != report['source_sha256']:
        raise ValueError('patch provenance mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import trimesh
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt, gp_Dir, gp_Pln
    probe = next(p for patch in patches['patches_private'] for p in patch['probes_private']
                 if p['index'] == report['probe_private'])
    row = next(r for r in report['fixed_rays_private'] if r['probe_private'] == probe['index'])
    if row['status'] != 'resolved':
        raise ValueError('selected ray unresolved')
    first = np.array(probe['entry_xyz_scan_units'])
    u = np.array(probe['direction']); u /= np.linalg.norm(u)
    ref = np.array([0.,0.,1.]) if abs(u[2]) < .9 else np.array([0.,1.,0.])
    normal = np.cross(u, ref); normal /= np.linalg.norm(normal)
    v = np.cross(normal, u)
    curves, shapes = [], []
    for path in (args.baseline, args.candidate):
        shape = read_step(path)[0]; shapes.append(shape)
        section = BRepAlgoAPI_Section(shape, gp_Pln(gp_Pnt(*first), gp_Dir(*normal)), False)
        section.Build()
        if not section.IsDone():
            raise RuntimeError('CAD section failed')
        edges = indexed(section.Shape(), TopAbs_EDGE)
        lines = []
        for i in range(1, edges.Extent()+1):
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
            points = [curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(), curve.LastParameter(), 101)]
            xyz = np.array([[p.X(),p.Y(),p.Z()] for p in points])-first
            lines.append(np.column_stack((xyz@u, xyz@v)))
        curves.append(lines)
    fig = plt.figure(figsize=(13,13))
    grid = fig.add_gridspec(2,2,height_ratios=[1,1.1])
    for index, shape in enumerate(shapes):
        ax = fig.add_subplot(grid[0,index],projection='3d',computed_zorder=False)
        mesh_path = args.output.with_name(args.output.stem+f'-{index}-private.stl')
        if mesh_path.exists(): raise FileExistsError(mesh_path)
        if not BRepMesh_IncrementalMesh(shape,.15,False,.2,False).IsDone():
            raise RuntimeError('CAD tessellation failed')
        if not StlAPI_Writer().Write(shape,str(mesh_path)):
            raise RuntimeError('STL export failed')
        mesh = trimesh.load_mesh(mesh_path)
        light = np.array([.3,-.4,.85]); light /= np.linalg.norm(light)
        intensity = .4+.5*np.clip(mesh.face_normals@light,0,1)
        colors = np.column_stack((.82*intensity,.90*intensity,intensity,np.ones(len(intensity))))
        ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolor='none',zorder=1))
        bounds = mesh.bounds
        ax.set_xlim(bounds[0,0],bounds[1,0]); ax.set_ylim(bounds[0,1],bounds[1,1]); ax.set_zlim(bounds[0,2],bounds[1,2])
        ax.set_box_aspect(mesh.extents.copy()); ax.set_proj_type('ortho'); ax.view_init(elev=27,azim=-55)
        ax.set_axis_off(); ax.set_title(('CAO avant — F53','CAO après — essai non libéré')[index],fontsize=15)
        ax.scatter(*first,color='#d55e00',s=55,depthshade=False,zorder=10)
        ax.text(*first,'  Zone testée',color='#a63c00',fontsize=10,zorder=11)
    axes = [fig.add_subplot(grid[1,index]) for index in range(2)]
    for ax, label, lines in zip(axes, ('Avant — F53', 'Après — essai local'), curves):
        for line in curves[0]:
            ax.plot(line[:,0],line[:,1],color='#999999',ls='--',lw=1)
        for line in lines:
            ax.plot(line[:,0],line[:,1],color='#0072b2',lw=1.8)
        ax.set_title(label,fontsize=15)
        ax.set_aspect('equal'); ax.set_xlim(-2.5,4); ax.set_ylim(-2,5)
        ax.grid(alpha=.2); ax.set_xlabel('Position le long du rayon — unité du scan')
    old_length = probe['cad_ray_scan_units']; new_length = row['ray_scan_units']
    new_start = old_length-new_length
    for ax, start, length in zip(axes, (0,new_start), (old_length,new_length)):
        ax.plot([start,old_length],[0,0],color='#d55e00',lw=4,marker='o')
        ax.annotate(f'{length:.3f}', xy=((start+old_length)/2,0), xytext=(1,1.5),
                    arrowprops={'arrowstyle':'->'}, fontsize=16, color='#a63c00')
    axes[0].set_ylabel('Coordonnée de coupe — unité du scan')
    fig.suptitle('Réparation locale construite — CAO et coupe avant/après', fontsize=18,weight='bold')
    fig.text(.5,.06,'Même rayon : frontière locale déplacée, contours de référence en pointillé.\n'
             'Référence 935 ; échelle et interfaces M64 non validées. Essai non libéré pour fabrication.',
             ha='center',fontsize=11,color='#713e3e')
    fig.subplots_adjust(top=.92,bottom=.14,wspace=.12,hspace=.08)
    fig.savefig(args.output,dpi=150,bbox_inches='tight'); plt.close(fig)
    print(json.dumps({'image_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      'baseline_ray':old_length,'candidate_ray':new_length,
                      'manufacturing_authorized':False}))


if __name__ == '__main__':
    main()
