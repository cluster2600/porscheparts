#!/usr/bin/env python3
"""Measure native corner tangents and render an actual rejected surface triangle."""
import argparse
import itertools
import json
import math
from pathlib import Path
import signal
import sys

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_fixed_face_quality import MESH_SHA, tetra_ceiling
from run_parallel_cad_trials import BODY_SHA, native
from trial_fixed_boundary_seam import indexed, read_native


def angle_degrees(a, b):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    if a.shape!=(3,) or b.shape!=(3,) or not np.isfinite([a,b]).all() or min(np.linalg.norm(a),np.linalg.norm(b))==0:
        raise ValueError('finite_nonzero_tangents_required')
    return math.degrees(math.acos(float(np.clip(np.dot(a/np.linalg.norm(a),b/np.linalg.norm(b)),-1,1))))


def run(args):
    import gmsh
    import OCP
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE,TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt,gp_Vec
    pins={args.body:BODY_SHA,args.mesh:MESH_SHA,args.binding:native.sha256(args.binding),
          Path(__file__):native.sha256(__file__)}
    if (args.output.exists() or any(p.is_symlink() or native.sha256(p)!=h for p,h in pins.items())
            or OCP.__version__!='7.9.3.1' or gmsh.__version__!='4.15.2'):
        raise ValueError('exact_qualified_inputs_and_fresh_output_required')
    binding=json.loads(args.binding.read_text())
    if (binding['native_BRep_sha256']!=BODY_SHA or binding['mesh']['sha256']!=MESH_SHA
            or binding['import']['face_correspondence']['descriptor_bijection_verified'] is not True):
        raise ValueError('native_mesh_binding_required')
    matches=binding['import']['face_correspondence']['matches_private']
    tags=[r['gmsh_face_tag'] for r in matches if r['source_face_index']==1648]
    if len(tags)!=1:raise ValueError('one_bound_surface_required')
    args.output.mkdir(mode=0o700)
    faces=indexed(read_native(args.body),TopAbs_FACE);rows=[];curves=[]
    for face_id in (141,143,1411,1413,1648):
        ends=[]
        for edge_id,edge in enumerate(indexed(faces[face_id-1],TopAbs_EDGE)):
            curve=BRepAdaptor_Curve(TopoDS.Edge_s(edge));lo,hi=curve.FirstParameter(),curve.LastParameter()
            for u,sign in ((lo,1),(hi,-1)):
                point,vector=gp_Pnt(),gp_Vec();curve.D1(u,point,vector)
                ends.append((edge_id,np.array(point.Coord()),sign*np.array(vector.Coord())))
            if face_id==1648:
                curves.append(np.array([curve.Value(float(u)).Coord() for u in np.linspace(lo,hi,101)]))
        angles=[angle_degrees(a[2],b[2]) for a,b in itertools.combinations(ends,2)
                if a[0]!=b[0] and np.linalg.norm(a[1]-b[1])<=1e-7]
        if not angles:raise ValueError('joined_native_tangents_required')
        rows.append(dict(source_face_index=face_id,minimum_ray_angle_degrees=min(angles)))
    gmsh.initialize(['acute-render','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        gmsh.open(str(args.mesh));types,elements,nodes=gmsh.model.mesh.getElements(2,tags[0])
        if list(types)!=[2]:raise ValueError('linear_surface_triangles_required')
        q=gmsh.model.mesh.getElementQualities(elements[0],'minSICN');worst=int(np.argmin(q))
        triangle=np.array([gmsh.model.mesh.getNode(int(n))[0] for n in nodes[0].reshape(-1,3)[worst]])
    finally:gmsh.finalize()
    centre=triangle.mean(0);_,_,axes=np.linalg.svd(triangle-centre)
    projected=(triangle-centre)@axes[:2].T
    fig,plots=plt.subplots(1,2,figsize=(12,5))
    for ax in plots:
        for line in curves:
            xy=(line-centre)@axes[:2].T;ax.plot(xy[:,0],xy[:,1],color='#234e70',lw=1)
        closed=np.vstack([projected,projected[0]])
        ax.plot(closed[:,0],closed[:,1],color='#d55336',lw=1.6)
        ax.set(aspect='equal',xlabel='Projected scan units',ylabel='Projected scan units')
        ax.grid(alpha=.2)
    plots[0].set_aspect('auto')
    tip=projected[np.argmin(projected[:,0])]
    plots[1].set_xlim(tip[0]-.025,tip[0]+.075);plots[1].set_ylim(tip[1]-.05,tip[1]+.05)
    plots[0].set_title('Native face 1648: Y enlarged, unequal scales')
    plots[1].set_title('Actual acute tip: equal axis scale')
    fig.suptitle(f'Fixed triangle q2={q[worst]:.6f}  |  best possible tetra q3≤{tetra_ceiling(float(q[worst])):.6f} < 0.1')
    fig.text(.5,.02,'Blue: native edge samples. Red: saved mesh triangle. Diagnostic projection, not metrology or a thermal simulation.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.92));image=args.output/'acute-native-face.png';fig.savefig(image,dpi=160);plt.close(fig)
    if any(native.sha256(p)!=h for p,h in pins.items()):raise ValueError('input_changed')
    native.save(args.output/'report.json',dict(schema='m64-native-acute-face-audit/v1',
        input_sha256=BODY_SHA,mesh_sha256=MESH_SHA,binding_sha256=pins[args.binding],
        source_sha256=pins[Path(__file__)],native_corners=rows,triangle_private=triangle.tolist(),
        triangle_quality=float(q[worst]),tetra_ceiling=tetra_ceiling(float(q[worst])),
        image_sha256=native.sha256(image),geometry_modified=False,inputs_unchanged=True,
        anatomical_roles_assigned=False,manufacturing_authorized=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('body','mesh','binding','output'):parser.add_argument('--'+key,type=Path,required=True)
    signal.alarm(120);run(parser.parse_args())
