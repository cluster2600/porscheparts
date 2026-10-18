"""Retain overview003 and add real-pose zooms with a VisPy pixel-scale witness."""
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from vispy import scene
from vispy.scene.cameras import TurntableCamera
from vispy.scene.cameras.perspective import PerspectiveCamera
from vispy.visuals.transforms import MatrixTransform

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STORE = ROOT/'work/carrier-process-20261016/sealed-envelopes-v2-001'
REFERENCE = HERE/'reference-003'
RECEIPT_SHA = '6eb5a23dc31325c832004e48425be05a1ccd9a8b378d724a4888fb65c0d9c894'
RASTER = ROOT/'scripts/render_carrier_progress.py'
RASTER_SHA = 'ed589c99365537eb165ecffbd48a70200507a005c2e3be7a22dfc6c2681f4eaf'
DETAIL_RASTER = HERE/'raster_unlit.py'
DETAIL_SHA = '262e766aee94a0244037f89194453726953ddc4016c7bdccda63ff9ac866f6e0'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def basis(el,az):
    e,a=np.radians([el,az])
    right=np.array([np.cos(a),np.sin(a),0.])
    up=np.array([-np.sin(e)*np.sin(a),np.sin(e)*np.cos(a),np.cos(e)])
    bound=64*np.finfo(np.float64).eps
    assert abs(np.dot(right,up))<=bound
    assert abs(np.linalg.norm(right)-1)<=bound and abs(np.linalg.norm(up)-1)<=bound
    return right,up


def calibrate(center,el,az,scale,bar_mm):
    """Map a world-space100mm image-horizontal segment with installed VisPy."""
    right,up=basis(el,az)
    canvas=scene.SceneCanvas(show=False,size=(2000,720),bgcolor='white')
    try:
        view=canvas.central_widget.add_view()
        camera=TurntableCamera(fov=0,elevation=el,azimuth=az)
        view.camera=camera;camera.center=center;camera.scale_factor=scale
        pixels=canvas.render()
        assert tuple(pixels.shape[:2])==(720,2000)
        matrix=camera.transform.matrix
        assert np.max(np.abs(matrix[0,:3]-right))<=64*np.finfo(np.float64).eps
        assert np.max(np.abs(matrix[1,:3]-up))<=64*np.finfo(np.float64).eps
        world=np.array([center,center+100*right])
        mapped=view.scene.node_transform(canvas.scene).map(world)
        mapped=mapped[:,:2]/mapped[:,3,None]
        delta=mapped[1]-mapped[0];expected=100*720/scale
        # A display-only float32 transform budget, fixed before the comparison.
        # This adds no distance allowance to any CAD/mesh/contact decision.
        bound_px=64*np.finfo(np.float32).eps*max(2000.,float(np.abs(mapped).max()))
        error=float(np.max(np.abs(delta-[expected,0.])))
        assert error<=bound_px
        return dict(elevation_degrees=el,azimuth_degrees=az,camera_scale_factor_mm=float(scale),
            right_world=right.tolist(),up_world=up.tolist(),orthogonality_dot=float(np.dot(right,up)),
            camera_matrix_basis_verified=True,world_segment_mm=100.,world_endpoints_mm=world.tolist(),
            projected_endpoints_pixels=mapped.tolist(),projected_delta_pixels=delta.tolist(),
            predicted_horizontal_pixels=float(expected),maximum_pixel_error=error,
            display_rounding_bound_pixels=float(bound_px),drawn_bar_mm=bar_mm,
            drawn_bar_pixels=float(bar_mm*720/scale),passed=True)
    finally:canvas.close()


def main(output):
    own=sha(__file__)
    if sha(REFERENCE/'render-receipt.json')!=RECEIPT_SHA or sha(RASTER)!=RASTER_SHA or sha(DETAIL_RASTER)!=DETAIL_SHA:
        raise ValueError('The accepted overview or original raster differs')
    original=json.loads((REFERENCE/'render-receipt.json').read_text())
    inputs=original['input_sha256']
    if len(inputs)!=187 or any(sha(p)!=h for p,h in inputs.items()):
        raise ValueError('The same187 retained inputs are required')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    for name,digest in original['outputs_sha256'].items():
        if sha(REFERENCE/name)!=digest:raise ValueError('The accepted global image differs')
        shutil.copyfile(REFERENCE/name,output/name)
    shutil.copyfile(REFERENCE/'render-receipt.json',output/'global-view-receipt.json')
    spec=importlib.util.spec_from_file_location('_envelope_zoom_raster',DETAIL_RASTER)
    renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
    center=np.mean(np.array([[-225.56706319850866,-225.56706319850863,0.],
                              [225.56706319850866,225.56706319850863,62.]]),axis=0)
    checks=[dict(kind='retained_global_view',**calibrate(center,r['elevation_degrees'],r['azimuth_degrees'],
        r['camera_scale_factor_mm'],100.))for r in original['views']]
    fig,axes=plt.subplots(1,2,figsize=(13,7),facecolor='#f5f7f9')
    for ax,index,color in zip(axes,[3,9],['#CC79A7','#56B4E9']):
        row=next(r for r in original['meshes']if r['source_index']==index)
        with np.load(STORE/row['file'],allow_pickle=False)as data:
            vertices,faces=data['vertices'],data['faces']
        box=np.array([vertices.min(0),vertices.max(0)])
        el,az=23,135;right,up=basis(el,az)
        extent=2*np.abs((vertices-box.mean(0))@np.stack([right,up],axis=1)).max(0)
        scale=max(extent[1],extent[0]/(2000/720))*1.10
        proof=calibrate(box.mean(0),el,az,scale,10.)
        checks.append(dict(kind='isolated_region_zoom',source_index=index,**proof))
        pixels=renderer.raster(vertices,faces,np.tile(matplotlib.colors.to_rgba(color),(len(faces),1)),el,az,box)
        height,width=pixels.shape[:2]
        ax.imshow(pixels);ax.axis('off');ax.set_ylim(height+100,-10);ax.set_xlim(-.5,width-.5)
        length=proof['drawn_bar_pixels'];start=(width-length)/2
        ax.plot([start,start+length],[height+25]*2,color='#20364a',lw=2.5)
        ax.text(width/2,height+63,'10 mm',ha='center',va='center',fontsize=11,color='#20364a')
        ax.set_title(f'Région {index:03d} seule · {len(faces):,} triangles'.replace(',',' '),
            loc='center',fontsize=15,weight='bold',color=color)
        bounds=' ; '.join(f'{axis} [{lo:.2f} ; {hi:.2f}]'for axis,lo,hi in zip('XYZ',box[0],box[1])).replace('.',',')
        ax.text(.5,-.065,bounds+' mm',transform=ax.transAxes,ha='center',fontsize=9,color='#536477')
    fig.suptitle('DEUX PETITES ENVELOPPES  /  ZOOMS EN POSITION RÉELLE',x=.045,ha='left',
        fontsize=20,weight='bold',color='#173249')
    fig.text(.045,.91,'Régions 003 et 009 seules — aucune explosion, translation ou modification des triangles',
        fontsize=12,color='#98600b')
    fig.text(.045,.055,'Enveloppes volumiques de construction · aucune grille, dent ou couche finale représentée',
        fontsize=11,color='#536477')
    fig.text(.045,.025,'Les caméras zooment ; les coordonnées des sommets restent celles du magasin natif admis.',
        fontsize=10,color='#536477')
    fig.subplots_adjust(left=.04,right=.97,top=.835,bottom=.18,wspace=.20)
    for suffix in ('png','svg','pdf'):
        fig.savefig(output/('small-envelopes-details.'+suffix),dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)
    sources={str(Path(inspect.getfile(obj))):sha(inspect.getfile(obj))for obj in [TurntableCamera,PerspectiveCamera,MatrixTransform,scene.Node]}
    if sha(__file__)!=own or sha(DETAIL_RASTER)!=DETAIL_SHA or any(sha(p)!=h for p,h in inputs.items()):raise ValueError('A source changed')
    receipt=dict(status='rendered_envelope_overview_and_two_real_pose_zooms',
        global_view_receipt_sha256=RECEIPT_SHA,global_views_byte_copied=True,source_sha256=own,
        detail_raster_source_sha256=DETAIL_SHA,baseline_raster_source_sha256=RASTER_SHA,installed_VisPy_sources_sha256=sources,
        input_sha256=inputs,inputs_unchanged=True,geometry_modified=False,native_cases_rerun=False,
        full_support_preparation_admitted=False,scale_projection_checks=checks,
        outputs_sha256={p.name:sha(p)for p in output.iterdir()if p.is_file()})
    (output/'render-receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=receipt['status'],projection_checks=len(checks),passed=all(r['passed']for r in checks))))


if __name__=='__main__':main(sys.argv[1])
