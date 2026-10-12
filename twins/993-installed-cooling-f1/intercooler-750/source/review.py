#!/usr/bin/env python3
"""Inspect actual native coupons and retain review meshes and sizing plots."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
import trimesh

STUDY=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def run(native, output):
    if output.exists(): raise FileExistsError(output)
    generation=json.loads((native/'generation.json').read_text())
    output.mkdir(parents=True);records=[];scene=trimesh.Scene()
    for number,path in enumerate(sorted(native.glob('*.stl'))):
        print('AUDIT',path.name,flush=True)
        mesh=trimesh.load_mesh(path,process=True)
        before=mesh.volume;count=len(mesh.faces)
        mesh.update_faces(mesh.nondegenerate_faces() & mesh.unique_faces());mesh.remove_unreferenced_vertices()
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.body_count!=1 or mesh.volume<=0: raise ValueError(f'Native topology rejected: closed={mesh.is_watertight}, winding={mesh.is_winding_consistent}, bodies={mesh.body_count}, volume={mesh.volume}')
        if abs(mesh.volume/before-1)>1e-7: raise ValueError('Cleanup changed volume')
        g=generation['geometry'];x,y,z=generation['dimensions_mm'];wall=g['wall_mm'];period=g['hot_gap_mm']+2*wall+g['cold_gap_mm']
        routes=[]
        for tube in range(3):
            routes.extend([[u,tube*period+wall+g['hot_gap_mm']/2,wall+g['hot_pitch_mm']/4] for u in np.linspace(.2,x-.2,61)])
        for gap in range(2):
            routes.extend([[wall+g['cold_pitch_mm']/4,gap*period+g['hot_gap_mm']+2*wall+g['cold_gap_mm']/2,u] for u in np.linspace(.2,z-.2,61)])
        print('NATIVE TOPOLOGY PASSED',path.name,flush=True)
        poly=pv.PolyData(mesh.vertices,np.column_stack((np.full(len(mesh.faces),3),mesh.faces)))
        attempts=[]
        for target in (180000,600000,1800000):
            simplified=poly.decimate_pro(max(0,1-target/len(mesh.faces)),preserve_topology=True,splitting=False,boundary_vertex_deletion=False)
            review=trimesh.Trimesh(simplified.points,simplified.faces.reshape(-1,4)[:,1:],process=True)
            review.update_faces(review.nondegenerate_faces() & review.unique_faces());review.remove_unreferenced_vertices()
            error=abs(review.volume/mesh.volume-1)
            attempts.append({'target':target,'watertight':bool(review.is_watertight),'bodies':int(review.body_count),'volume_error':float(error)})
            print('SIMPLIFICATION',attempts[-1],flush=True)
            if review.is_watertight and review.body_count==1 and error<=.005: break
        else: raise ValueError('Review simplification rejected')
        if review.contains(np.array(routes)).any(): raise ValueError('Sampled review route blocked')
        if not review.contains([[x/2,wall/2,z/2]])[0]: raise ValueError('Review separating wall absent')
        stl=review.export(file_type='stl');(output/(path.stem+'.stl.gz')).write_bytes(gzip.compress(stl,mtime=0))
        record={'name':path.stem,'native_sha256':sha(path),'native_triangles':count,'clean_triangles':len(mesh.faces),'native_volume_mm3':float(mesh.volume),'native_watertight':True,'native_bodies':1,'sampled_open_route_points':len(routes),'route_witness_mesh':'topology-preserving simplified review mesh','all_voids_inspected':False,'simplification_attempts':attempts,'review_triangles':len(review.faces),'review_volume_relative_error':abs(review.volume/mesh.volume-1)}
        records.append(record)
        review.visual.face_colors=[180,195,212,255] if number==0 else [215,162,77,255]
        review.apply_translation([number*(x+12),0,0]);review.apply_scale(.001)
        scene.add_geometry(review,node_name=path.stem)
        print(json.dumps(record),flush=True)
        del mesh,poly,review
    (output/'coupons.glb').write_bytes(scene.export(file_type='glb'))
    plot=pv.Plotter(off_screen=True,window_size=(1400,800))
    for number,path in enumerate(sorted(output.glob('*.stl.gz'))):
        import io
        m=trimesh.load_mesh(io.BytesIO(gzip.decompress(path.read_bytes())),file_type='stl')
        m.apply_translation([number*(generation['dimensions_mm'][0]+12),0,0])
        poly=pv.PolyData(m.vertices,np.column_stack((np.full(len(m.faces),3),m.faces)))
        plot.add_mesh(poly,color='#c0d0df' if number==0 else '#d7a24d',smooth_shading=False)
    plot.add_text(f"PicoGK: offset fins / plain control\n{g['fin_mm']} mm fins; {g['wall_mm']} mm separating walls\nGeometry coupons only - not pressure qualified",font_size=13,color="white")
    plot.set_background('#18212c');plot.camera_position='iso';plot.show(screenshot=str(output/'coupons.png'),auto_close=True)
    report=json.loads((STUDY/'results/sizing.json').read_text());rows=list(csv.DictReader((STUDY/'results/sweep.csv').open()))
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for family,color in [('plain','#677789'),('offset','#1279b3')]:
        r=[v for v in rows if v['fin_family']==family and v['all_regimes_admissible']=='True']
        axes[0].scatter([float(v['max_cold_dp_pa']) for v in r],[float(v['max_charge_outlet_c']) for v in r],s=6,alpha=.25,c=color,label=family)
    axes[0].axhline(60,c='crimson',ls='--');axes[0].axvline(500,c='crimson',ls='--');axes[0].set(xscale='log',xlabel='Core ambient pressure loss (Pa)',ylabel='Worst charge outlet (°C)',title='Sizing screen with stress factors');axes[0].legend()
    thin=json.loads((STUDY/'results/thin-sizing.json').read_text())
    thin_rows=list(csv.DictReader((STUDY/'results/thin-sweep.csv').open()))
    tr=[v for v in thin_rows if v['all_regimes_admissible']=='True']
    axes[0].scatter([float(v['max_cold_dp_pa']) for v in tr],[float(v['max_outlet_c']) for v in tr],s=7,alpha=.3,c='#d78618',label='thin / 1-2 banks');axes[0].legend()
    r=thin['cooling_flow_sensitivity'];axes[1].plot([c['cooling_mass_flow_kg_s'] for c in r],[c['charge_outlet_c'] for c in r],'o-',label='Charge outlet')
    axes[1].plot([c['cooling_mass_flow_kg_s'] for c in r],[c['engine_inlet_c'] for c in r],'o-',label='Air arriving at engine')
    axes[1].axhline(60,c='crimson',ls='--');axes[1].set(xlabel='Assumed cooling airflow (kg/s)',ylabel='Temperature (°C)',title='High load; fixed flow, no fan coupling');axes[1].legend()
    fig.suptitle('750 metric hp - uncalibrated sizing, no physical performance acceptance');fig.tight_layout();fig.savefig(output/'sizing.png',dpi=150);plt.close(fig)
    sources=[Path(__file__),STUDY/'source/picogk/Program.cs',STUDY/'source/picogk/Core.csproj',STUDY/'results/sizing.json',STUDY/'results/thin-sizing.json',STUDY/'coupon-input.json']
    manifest={'status':'native_geometry_checked_not_print_or_flow_qualified','generation':generation,'parts':records,'manufacturing_authorized':False,
              'retention':'Full native meshes retained locally; committed STL.gz and GLB are topology-preserving review simplifications. Editable PicoGK source is master.',
              'source_hashes':{str(p.relative_to(STUDY)):sha(p) for p in sources},'output_hashes':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'review.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.native,a.output)
