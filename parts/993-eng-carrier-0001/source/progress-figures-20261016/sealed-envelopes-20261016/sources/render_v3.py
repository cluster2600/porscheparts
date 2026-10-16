"""Render the unchanged seven sealed construction envelopes and posed real part."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'parts/993-eng-carrier-0001/source/process-skins-20261016'
STORE = ROOT/'work/carrier-process-20261016/sealed-envelopes-v2-001'
STORE_SHA = '63391aa2b74094887155346841db493f57c0eb0a0b8d8998c4c748c95bf13ec4'
STL_SHA = '443b5ae20f7f1b2fd19a210aa5347890086523bc66749dfc95fa3560b85e9a6e'
RENDERER = ROOT/'scripts/render_carrier_progress.py'
RENDERER_SHA = 'ed589c99365537eb165ecffbd48a70200507a005c2e3be7a22dfc6c2681f4eaf'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity = lambda a: dict(dtype=a.dtype.str, shape=list(a.shape), sha256=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest())


def main(output):
    started = time.monotonic()
    if sha(STORE/'envelopes.json') != STORE_SHA or sha(RENDERER) != RENDERER_SHA:
        raise ValueError('The retained store or unchanged rendering helper differs')
    sys.path.insert(0, str(SOURCE))
    from admitted_regions_v2 import EnvelopeStore
    report = json.loads((STORE/'envelopes.json').read_text())
    store = EnvelopeStore(STORE, STL_SHA, report['parameters'])
    if [r['source_index'] for r in report['regions']] != [0,1,2,3,8,9,10]:
        raise ValueError('All seven original envelope regions are required')
    adapted_raster = Path(__file__).with_name('raster_ghost.py')
    spec = importlib.util.spec_from_file_location('_retained_envelope_raster', adapted_raster)
    renderer = importlib.util.module_from_spec(spec); spec.loader.exec_module(renderer)
    geometry_path = ROOT/'work/part-workflow/run-001/cad/geometry.json'
    step_path = geometry_path.with_name('carrier.step')
    cache_path = ROOT/'work/carrier-process-20261016/part-layer-cache-001/report.json'
    geometry = json.loads(geometry_path.read_text()); cache = json.loads(cache_path.read_text())
    if geometry['geometry_sha256']['carrier.step'] != sha(step_path) or cache['input_sha256'] != STL_SHA:
        raise ValueError('The current CAD/part cache does not bind this candidate')
    paths = {**store.files, RENDERER:RENDERER_SHA, Path(__file__):sha(__file__),
        geometry_path:sha(geometry_path), step_path:sha(step_path), cache_path:sha(cache_path), adapted_raster:sha(adapted_raster)}
    palette = ['#E69F00','#0072B2','#009E73','#CC79A7','#7B61A8','#56B4E9','#D55E00']
    meshes, colors, rows = [], [], []
    for index,name,color in [('part','input-part.npz','#718093')]+[
            (r['source_index'],r['envelope'],c)for r,c in zip(report['regions'],palette)]:
        with np.load(STORE/name,allow_pickle=False)as data:
            vertices,faces=data['vertices'].copy(),data['faces'].copy()
        if index=='part' and (identity(vertices)!=cache['part_pose_and_arrays']['vertices'] or
                identity(faces)!=cache['part_pose_and_arrays']['faces']):
            raise ValueError('The posed part arrays differ from the complete part cache')
        rgba=matplotlib.colors.to_rgba(color)
        meshes.append((vertices,faces));colors.append(np.tile(rgba,(len(faces),1)))
        rows.append(dict(source_index=index,file=name,sha256=sha(STORE/name),vertices=len(vertices),
            triangles=len(faces),bounds_mm=[vertices.min(0).tolist(),vertices.max(0).tolist()],color=color))
    vertices=np.concatenate([v for v,f in meshes]);cursor=0;offset=[]
    for v,f in meshes:offset.append(f+cursor);cursor+=len(v)
    faces=np.concatenate(offset);colors=np.concatenate(colors)
    box=np.array([vertices.min(0),vertices.max(0)])
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(2,1,figsize=(16,10),facecolor='#f5f7f9')
    views=[(-67,45,'Vue depuis le dessous · sept domaines libres dans la pose conservée'),
           (-19,225,'Vue oblique opposée · même pièce et mêmes sept enveloppes')]
    view_rows=[]
    for ax,(el,az,label)in zip(axes,views):
        pixels=renderer.raster(vertices,faces,colors,el,az,box,part_faces=len(meshes[0][1]))
        e,a=np.radians([el,az]);right=np.array([np.cos(a),np.sin(a),0.])
        up=np.array([-np.sin(e)*np.sin(a),np.sin(e)*np.cos(a),np.cos(e)])
        extent=2*np.abs((vertices-box.mean(0))@np.stack([right,up],axis=1)).max(0)
        scale=max(extent[1],extent[0]/(2000/720))*1.10
        length=100/scale*720
        ax.imshow(pixels);height,width=pixels.shape[:2]
        ax.plot([35,35+length],[height+22]*2,color='#20364a',lw=2.5)
        ax.text(35+length/2,height+49,'100 mm',ha='center',va='center',fontsize=9,color='#20364a')
        ax.set_ylim(height+70,-8);ax.set_xlim(-.5,width-.5);ax.axis('off')
        ax.set_title(label,loc='left',fontsize=12,color='#20364a')
        view_rows.append(dict(elevation_degrees=el,azimuth_degrees=az,orthographic=True,
            viewport_pixels=[2000,720],camera_scale_factor_mm=float(scale),scale_bar_mm=100,
            scale_bar_pixels=float(length)))
    fig.suptitle('993 TURBO  /  SEPT ENVELOPPES NATIVES ADMISES',x=.045,ha='left',
        fontsize=23,weight='bold',color='#173249')
    fig.text(.045,.918,'Enveloppes de construction — surfaces de supports et couches encore en cours',
        fontsize=14,weight='bold',color='#98600b')
    fig.text(.955,.965,'1,262 kg / 1,30 kg',ha='right',fontsize=17,color='#167269',weight='bold')
    fig.legend(handles=[Patch(facecolor='#718093',alpha=.35,label='Pièce (translucide)')]+[
        Patch(facecolor=c,label=f'Région {r["source_index"]:03d}')for r,c in zip(report['regions'],palette)],
        loc='lower center',bbox_to_anchor=(.5,.054),ncol=8,frameon=False,fontsize=9)
    fig.text(.045,.026,'Repère réel en millimètres · rotation 45° · écart pièce / plateau 10 mm · tous les triangles conservés',
        fontsize=10,color='#536477')
    fig.text(.045,.008,'Enveloppes volumiques opaques, pièce translucide · aucune grille, dent ou couche finale représentée',
        fontsize=10,color='#536477')
    fig.subplots_adjust(left=.035,right=.975,top=.875,bottom=.12,hspace=.18)
    for suffix in ('png','svg','pdf'):
        fig.savefig(output/('sealed-envelopes-overview.'+suffix),dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig);store.verify()
    if any(sha(p)!=h for p,h in paths.items()):raise ValueError('A rendering input changed')
    receipt=dict(status='rendered_sealed_envelopes_no_final_support_admission',
        visible_status='Enveloppes de construction — surfaces de supports et couches encore en cours',
        source_sha256=sha(__file__),raster_source_sha256=RENDERER_SHA,sealed_store_sha256=STORE_SHA,
        private_raster_adapter_sha256=sha(adapted_raster),
        raster_changes='Unlit opaque volume envelopes, posed part drawn last at alpha .18 with depth test and no depth write; all unchanged triangles',
        input_sha256={str(p):h for p,h in paths.items()},inputs_unchanged=True,meshes=rows,
        native_cases_rerun=False,support_surfaces_generated=False,full_layers_generated=False,
        geometry_modified=False,mass_kg=geometry['dense_reference_mass_kg'],mass_limit_kg=1.30,
        source_STEP_sha256=sha(step_path),source_STL_sha256=STL_SHA,views=view_rows,
        versions=dict(numpy=np.__version__,matplotlib=matplotlib.__version__),
        outputs_sha256={p.name:sha(p)for p in output.iterdir()if p.is_file()},
        elapsed_seconds=time.monotonic()-started)
    (output/'render-receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=receipt['status'],triangles=int(len(faces)),seconds=receipt['elapsed_seconds'])))


if __name__=='__main__':main(sys.argv[1])
