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
        # Cut only the view; keep native and exported review solids intact.
        plot.add_mesh(low.clip(normal=(0,0,1),origin=(0,0,m.bounds[1,2]*.65)),color=np.array(color[:3])/255)
        (output/(path.stem+'.stl.gz')).write_bytes(gzip.compress(v.export(file_type='stl'),mtime=0))
        v.visual.face_colors=color;v.apply_scale(.001);scene.add_geometry(v,node_name=path.stem)
    plot.add_text('PicoGK cutaway — hot-weather ribbed header study\nGrey: core envelopes; blue: charge inlets; orange: common outlet\nInternal core fins and tube/header joints are not resolved',font_size=13,color='white')
    plot.camera_position=[(1350,-1400,1100),(0,270,80),(0,0,1)]
    plot.show(screenshot=str(output/'layout.png'),auto_close=True)
    (output/'layout.glb').write_bytes(scene.export(file_type='glb'))
    r=json.loads((ROOT/'results/study.json').read_text());fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for frac in [0,.05,.1]:
        rows=[c for c in r['sensitivity'] if c['recirculation_fraction']==frac]
        axes[0].plot([c['ambient_c'] for c in rows],[c['charge_outlet_c'] for c in rows],'o-',label=f'{frac:.0%} exhaust recirculation')
    axes[0].axhline(60,color='crimson',ls='--');axes[0].set(xlabel='Ambient (°C)',ylabel='Charge outlet (°C)',title='Fixed cooler speed; corrected compressor intake');axes[0].legend()
    rows=r['wall_screen']['cases'];panels=[x for x in rows if x['case']=='ribbed_panel']
    axes[1].bar(['2.5 bar','3.75 bar'],[x['stress_pa']/1e6 for x in panels]);axes[1].axhline(40,color='crimson',ls='--',label='Assumed allowable (not certified)')
    axes[1].set(ylabel='Ideal strip bending stress (MPa)',title='30 mm support pitch, 3 mm wall');axes[1].legend()
    fig.suptitle('Hypothesis study — neither thermal nor pressure qualification');fig.tight_layout();fig.savefig(output/'comparison.png',dpi=150);plt.close(fig)
    sources=[ROOT/'assumptions.json',ROOT/'layout-input.json',ROOT/'coupon-input.json',ROOT/'results/study.json',Path(__file__),ROOT/'source/picogk/Program.cs',ROOT/'source/picogk/Layout.csproj']
    manifest={'status':'native_header_topology_checked_packaging_only','generation':json.loads((native/'generation.json').read_text()),'parts':records,'header_mass_kg':sum(x['mass_kg'] or 0 for x in records),'manufacturing_authorized':False,'full_core_resolved':False,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in sources},'output_hashes':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'review.json').write_text(json.dumps(manifest,indent=2)+'\n');print('REVIEW COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.native,a.output)
