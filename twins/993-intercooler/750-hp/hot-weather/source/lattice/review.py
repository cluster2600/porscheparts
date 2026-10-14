"""Inspect native coupons before removing degenerate faces; compare geometry only."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import pyvista as pv
import trimesh

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def run(work,output):
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);rows=[]
    plot=pv.Plotter(shape=(1,2),off_screen=True,window_size=(1500,650))
    for index,variant in enumerate(['plain','bcc']):
        for voxel in [.2,.1]:
            native=work/f'lattice-{variant}-{voxel}-001';receipt=json.loads((native/'receipt.json').read_text());parts={}
            for name in ['solid_mm','hot_fluid_mm','cold_fluid_mm']:
                path=native/(name+'.stl');m=trimesh.load_mesh(path,process=True)
                raw_closed=m.is_watertight;before=m.volume;count=len(m.faces)
                m.update_faces(m.nondegenerate_faces() & m.unique_faces());m.remove_unreferenced_vertices()
                error=abs(m.volume/before-1)
                if not m.is_watertight or not m.is_winding_consistent or m.body_count!=1 or m.volume<=0 or error>1e-7:raise ValueError(f'Rejected mesh {path}')
                # Exclude the two artificial cold inlet/outlet caps, including border triangles.
                caps=np.all(np.abs(m.triangles[:,:,1]-12)<1e-4,axis=1)|np.all(np.abs(m.triangles[:,:,1]+12)<1e-4,axis=1)
                parts[name]={'native_sha256':sha(path),'raw_closed':raw_closed,'removed_degenerate_or_duplicate_faces':count-len(m.faces),'cleanup_volume_error':error,'closed_after_cleanup':True,'surface_components':m.body_count,'volume_mm3':float(m.volume),'area_mm2':float(m.area),'cold_wetted_area_mm2':float(m.area_faces[~caps].sum()) if name=='cold_fluid_mm' else None}
                if voxel==.1 and name=='solid_mm':
                    poly=pv.PolyData(m.vertices,np.column_stack((np.full(len(m.faces),3),m.faces)))
                    plot.subplot(0,index);plot.set_background('#19232e');plot.add_mesh(poly.clip(normal=(0,0,1),origin=(0,0,8)),color='#60b3c6')
                    plot.add_text(variant.upper()+' — cut at Z=8 mm\nGeometry only; no CFD result',font_size=13,color='white');plot.camera_position=[(36,-38,32),(0,0,5),(0,0,1)]
                    (output/(variant+'-solid.stl.gz')).write_bytes(gzip.compress(m.export(file_type='stl'),mtime=0))
            vdb=output/f'{variant}-{voxel}-fields.vdb.gz';vdb.write_bytes(gzip.compress((native/'coupon-fields.vdb').read_bytes(),mtime=0))
            rows.append({'variant':variant,'voxel_mm':voxel,'native_receipt':receipt,'native_receipt_sha256':sha(native/'receipt.json'),'parts':parts,'vdb_gzip':vdb.name,'volume_partition_relative_error':abs(sum(p['volume_mm3'] for p in parts.values())/(24*24*11.4)-1)})
    plot.show(screenshot=str(output/'comparison.png'),auto_close=True)
    fine={x['variant']:x for x in rows if x['voxel_mm']==.1};plain=fine['plain']['parts'];bcc=fine['bcc']['parts']
    convergence={v:{name:abs(next(r for r in rows if r['variant']==v and r['voxel_mm']==.2)['parts'][name]['volume_mm3']/fine[v]['parts'][name]['volume_mm3']-1) for name in plain} for v in fine}
    sources=[ROOT/'results/study.json',Path(__file__),Path(__file__).with_name('Program.cs'),Path(__file__).with_name('Coupon.csproj')]
    report={'status':'native_coupon_comparison_not_a_heat_transfer_result','runs':rows,'cold_wetted_area_ratio_bcc_to_plain':bcc['cold_fluid_mm']['cold_wetted_area_mm2']/plain['cold_fluid_mm']['cold_wetted_area_mm2'],'cold_void_volume_ratio_bcc_to_plain':bcc['cold_fluid_mm']['volume_mm3']/plain['cold_fluid_mm']['volume_mm3'],'solid_volume_ratio_bcc_to_plain':bcc['solid_mm']['volume_mm3']/plain['solid_mm']['volume_mm3'],'relative_volume_change_0p2_to_0p1':convergence,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in sources},'output_hashes':{p.name:sha(p) for p in output.iterdir()},'raw_mesh_accepted':False,'resolved_cfd':False,'thermal_improvement_demonstrated':False,'manufacturing_authorized':False}
    (output/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['runs','output_hashes','source_hashes']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.work,a.output)
