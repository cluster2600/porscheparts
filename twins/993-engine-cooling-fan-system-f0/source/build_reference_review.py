#!/usr/bin/env python3
"""Validate the reconstructed surfaces and export an uncalibrated OpenUSD reference."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh
from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils, UsdValidation

HELPERS = runpy.run_path(str(Path(__file__).with_name('build_fan_digital_twin.py')))


def build(source, output, rotor_faces=80000):
    if not 10000 <= rotor_faces <= 300000:
        raise ValueError("Review face count must be 10000..300000")
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'visual_reconstruction_only', 'geometry_checks': {},
              'pmb_fit_verified': False, 'cfd_run': False, 'gpu_render_run': False,
              'manufacturing_authorized': False, 'engine_operation_authorized': False}
    parameters = json.loads((source / 'generation.json').read_text())['parameters']
    meshes = {}
    for name in ['rotor', 'bearing-hub']:
        path = source / f'{name}-mm.stl'
        raw = trimesh.load_mesh(path, process=True)
        assert raw.is_watertight and raw.is_winding_consistent and raw.volume > 0, name
        assert len(raw.split(only_watertight=False)) == 1, name
        reduced = raw.simplify_quadric_decimation(face_count=rotor_faces if name == 'rotor' else 20000)
        assert reduced.is_watertight and reduced.is_winding_consistent
        assert abs(reduced.volume / raw.volume - 1) < .005
        meshes[name] = reduced
        report['geometry_checks'][name] = {'watertight': True, 'connected_components': 1,
            'original_triangles': len(raw.faces), 'review_triangles': len(reduced.faces),
            'volume_mm3': float(raw.volume), 'bounds_mm': raw.bounds.tolist(),
            'review_volume_error_fraction': float(abs(reduced.volume / raw.volume - 1)),
            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    # Check the exported mesh, not just the implicit function: each vent crosses the web.
    r = parameters['vent_radius_mm']
    a = np.arange(12) * 2 * np.pi / 12
    pts = np.column_stack([r*np.cos(a), r*np.sin(a), np.full(12, parameters['cup_front_z_mm'] + 8*(r/parameters['cup_radius_mm'])**2)])
    assert not meshes['rotor'].contains(pts).any(), 'Blocked vent after meshing'
    report['geometry_checks']['vent_centres_open'] = 12
    target = output / 'reference.usdc'
    stage = HELPERS['stage'](target)
    stage.GetDefaultPrim().SetCustomData({'status': 'uncalibrated_visual_reference',
        'target': '993_Turbo_M64_60', 'pmb240DimensionsVerified': False,
        'manufacturingAuthorized': False, 'flowValidated': False})
    for name, geometry in meshes.items():
        path = '/World/' + ('Rotor' if name == 'rotor' else 'BearingHub')
        prim = HELPERS['mesh'](stage, path, geometry.vertices*.001, geometry.faces,
                               [[.64,.68,.73]] if name == 'rotor' else [[.8,.57,.24]])
        prim.GetPrim().SetCustomData({'dimensionalStatus': 'hypotheses_see_reference_json',
            'referencePartNumber': '96410601522' if name == 'rotor' else '96410605131',
            'rotationGroup': 'fan', 'bearingInternalGeometryResolved': False})
    for name, part in [('Housing','99310666750'),('Alternator','PMB_Classic_Retrofit_240A'),
                       ('RearCone','93060304101'),('AuxiliaryImpeller','92860304501'),
                       ('PulleyAndSpacers','drive_variant_unresolved')]:
        p = UsdGeom.Scope.Define(stage, '/World/Unresolved/' + name).GetPrim()
        p.SetCustomData({'partNumber': part, 'status': 'identified_not_reconstructed_missing_interface_dimensions'})
    camera = UsdGeom.Camera.Define(stage, '/World/ReviewCamera')
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(.35,-.4,-.4),Gf.Vec3d(0),Gf.Vec3d(0,1,0)).GetInverse())
    camera.CreateClippingRangeAttr().Set(Gf.Vec2f(.001,10))
    stage.GetRootLayer().Save()
    issues = UsdValidation.ValidationContext(UsdValidation.ValidationRegistry().GetOrLoadAllValidators()).Validate(stage)
    assert not issues, [i.GetMessage() for i in issues]
    assert UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(target.resolve())), str(output/'reference.usdz'))
    assert Usd.Stage.Open(str(output/'reference.usdz'))
    report['openusd_validator_findings'] = []
    fig = plt.figure(figsize=(15,12), facecolor='#eef1f5')
    views = [('Front — 11 blades / 12 openings',-90,-90,False,False),
             ('Rear — cup and ribs',65,-70,False,False),
             ('Inspection section — open half-mesh',15,-90,True,False),
             ('Rotor / hub exploded view — illustrative offset',-35,-55,False,True)]
    for index,(title,elev,azim,section,explode) in enumerate(views,1):
        ax = fig.add_subplot(2,2,index,projection='3d')
        for name,geometry in meshes.items():
            triangles = geometry.triangles.copy()
            if section: triangles = triangles[triangles.mean(axis=1)[:,1] <= 0]
            if explode and name=='bearing-hub': triangles[:,:,2]-=65
            color = np.array([.60,.66,.73]) if name=='rotor' else np.array([.8,.55,.22])
            normal = np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
            normal /= np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
            shades = .5+.5*np.abs(normal @ np.array([.3,-.4,.866]))
            ax.add_collection3d(Poly3DCollection(triangles,facecolors=shades[:,None]*color,linewidths=0,rasterized=True))
        ax.set(xlim=(-130,130),ylim=(-130,130),zlim=(-135 if explode else -70,70),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]')
        if index == 1: ax.set_zticks([]); ax.set_zlabel('')
        ax.set_box_aspect((260,260,205 if explode else 140))
        ax.view_init(elev=elev,azim=azim); ax.set_title(title,fontsize=11)
    fig.suptitle(('Organic Turbo blade candidate' if parameters.get('organic') else 'Turbo reference reconstruction') + ' — not a validated part',fontsize=17)
    fig.text(.5,.025,'Geometry review from PicoGK meshes • dimensions unverified • housing and PMB not reconstructed',ha='center',fontsize=11)
    fig.savefig(output/'reference-review.png',dpi=140,bbox_inches='tight'); plt.close(fig)
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument("--rotor-faces", type=int, default=80000)
    args=parser.parse_args(); build(args.source,args.output,args.rotor_faces)
