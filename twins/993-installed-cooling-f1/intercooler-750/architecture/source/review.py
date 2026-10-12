#!/usr/bin/env python3
"""Review actual PicoGK headers and explicitly solid core envelopes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def run(native,output):
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);records=[];scene=trimesh.Scene()
    plot=pv.Plotter(off_screen=True,window_size=(1500,850));plot.set_background('#19232e')
    for path in sorted(native.glob('*.stl')):
        print('AUDIT',path.name,flush=True)
        m=trimesh.load_mesh(path,process=True);before=m.volume
        m.update_faces(m.nondegenerate_faces() & m.unique_faces());m.remove_unreferenced_vertices()
        if not m.is_watertight or not m.is_winding_consistent or m.body_count!=1 or m.volume<=0 or abs(m.volume/before-1)>1e-7:raise ValueError('Native topology rejected: '+path.name)
        poly=pv.PolyData(m.vertices,np.column_stack((np.full(len(m.faces),3),m.faces)))
        for target in [20000,100000,400000]:
            low=poly.decimate_pro(max(0,1-target/len(m.faces)),preserve_topology=True,splitting=False,boundary_vertex_deletion=False)
            v=trimesh.Trimesh(low.points,low.faces.reshape(-1,4)[:,1:],process=True)
            v.update_faces(v.nondegenerate_faces() & v.unique_faces());v.remove_unreferenced_vertices()
            if v.is_watertight and v.is_winding_consistent and v.body_count==1 and abs(v.volume/m.volume-1)<.005:break
        else:raise ValueError('Review topology rejected: '+path.name)
        records.append({'name':path.stem,'native_sha256':sha(path),'native_triangles':len(m.faces),'native_closed':True,'native_bodies':1,'volume_mm3':float(m.volume),'mass_kg':float(m.volume*2.68e-6) if 'core' not in path.stem else None,'review_triangles':len(v.faces),'review_relative_volume_error':abs(v.volume/m.volume-1),'bounds_mm':m.bounds.tolist()})
        color=[185,200,213,255] if 'core' in path.stem else [230,146,55,255] if 'outlet' in path.stem else [55,152,220,255]
        plot.add_mesh(low,color=np.array(color[:3])/255)
        (output/(path.stem+'.stl.gz')).write_bytes(gzip.compress(v.export(file_type='stl'),mtime=0))
        v.visual.face_colors=color;v.apply_scale(.001);scene.add_geometry(v,node_name=path.stem)
    plot.add_text('PicoGK packaging study — 750 metric hp\nGrey: core envelopes; blue: charge inlets; orange: common outlet\nInternal fins and tube/header joints are not resolved',font_size=13,color='white')
    plot.camera_position=[(1350,-1400,1100),(0,270,80),(0,0,1)]
    plot.show(screenshot=str(output/'layout.png'),auto_close=True)
    (output/'layout.glb').write_bytes(scene.export(file_type='glb'))
    r=json.loads((ROOT/'results/comparison.json').read_text());fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    labels=['Serial','Shared bypass','Separate'];cases=[c for c in r['architecture_comparison'] if c['scenario']=='high']
    x=np.arange(3);axes[0].bar(x-.17,[c['charge_outlet_c'] for c in cases],.34,label='Charge outlet');axes[0].bar(x+.17,[c['engine_inlet_c'] for c in cases],.34,label='Engine intake')
    axes[0].set_xticks(x,labels);axes[0].axhline(60,color='crimson',ls='--');axes[0].set(ylabel='Temperature (°C)',title='High duty; assumed fan curves, 35°C');axes[0].legend()
    for temp in [25,35,45]:
        rows=[c for c in r['sensitivity'] if c['ambient_c']==temp];axes[1].plot([c['total_shaft_power_w']/1000 for c in rows],[c['charge_outlet_c'] for c in rows],'o-',label=f'{temp}°C ambient')
    axes[1].axhline(60,color='crimson',ls='--');axes[1].axvline(15,color='crimson',ls=':');axes[1].set(xlabel='Combined shaft power (kW)',ylabel='Charge outlet (°C)',title='Separate air circuits; speed sensitivity');axes[1].legend()
    fig.suptitle('Hypothesis study — no physical cooling acceptance');fig.tight_layout();fig.savefig(output/'comparison.png',dpi=150);plt.close(fig)
    sources=[ROOT/'assumptions.json',ROOT/'results/comparison.json',Path(__file__),ROOT/'source/picogk/Program.cs',ROOT/'source/picogk/Layout.csproj']
    manifest={'status':'native_header_topology_checked_packaging_only','generation':json.loads((native/'generation.json').read_text()),'parts':records,'header_mass_kg':sum(x['mass_kg'] or 0 for x in records),'manufacturing_authorized':False,'full_core_resolved':False,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in sources},'output_hashes':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'review.json').write_text(json.dumps(manifest,indent=2)+'\n');print('REVIEW COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.native,a.output)
