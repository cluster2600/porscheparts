"""Retain native FEA files and inspect generated ribbed coupon exports."""
import argparse,gzip,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
import trimesh
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[3]
sys.path.insert(0,str(REPO/'models/horizontal-fan-reconstruction/source'))
from summarize_analytical_fem import read_frd
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def run(work,fea,output):
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);rows=[];r=json.loads((fea/'study.json').read_text())
    for case in sorted(p for p in fea.iterdir() if p.is_dir()):
        folder=output/'fea'/case.name;folder.mkdir(parents=True)
        for name in ['case.inp','case.frd','case.dat','solver.log','receipt.json']:
            if name.endswith(('.frd','.dat')):(folder/(name+'.gz')).write_bytes(gzip.compress((case/name).read_bytes(),mtime=0))
            else:shutil.copyfile(case/name,folder/name)
    shutil.copyfile(fea/'study.json',output/'study.json')
    for h in [.2,.1]:
        native=work/f'ribbed-native-{h}-002';receipt=json.loads((native/'receipt.json').read_text());parts={}
        for name,bodies in [('solid_mm',1),('hot_fluid_mm',5),('cold_fluid_mm',1)]:
            path=native/(name+'.stl');m=trimesh.load_mesh(path,process=True);before=m.volume;count=len(m.faces);raw=m.is_watertight
            m.update_faces(m.nondegenerate_faces() & m.unique_faces());m.remove_unreferenced_vertices()
            error=abs(m.volume/before-1)
            if not m.is_watertight or not m.is_winding_consistent or m.body_count!=bodies or error>1e-7:raise ValueError('Native topology rejected '+name)
            parts[name]={'native_sha256':sha(path),'raw_closed':raw,'removed_faces':count-len(m.faces),'cleanup_volume_error':error,'closed_after_cleanup':True,'components':m.body_count,'volume_mm3':float(m.volume),'area_mm2':float(m.area),'bounds_mm':m.bounds.tolist()}
            if h==.1 and name=='hot_fluid_mm':
                parts[name]['channel_widths_y_mm']=sorted(float(v.bounds[1,1]-v.bounds[0,1]) for v in m.split())
                if not np.allclose(parts[name]['channel_widths_y_mm'],[1.8,1.8,5.2,5.2,5.2],atol=.02):raise ValueError('Hot channels differ from independent section contract')
            if h==.1 and name=='solid_mm':
                plot=pv.Plotter(shape=(1,2),off_screen=True,window_size=(1400,650));poly=pv.PolyData(m.vertices,np.column_stack((np.full(len(m.faces),3),m.faces)))
                for i,z in enumerate([3,8]):
                    plot.subplot(0,i);plot.set_background('#19232e');plot.add_mesh(poly.clip(normal=(0,0,1),origin=(0,0,z)),color='#61b4c7');plot.add_text(f'Cut Z={z} mm — '+('hot longitudinal ribs' if i==0 else 'cold BCC lattice')+'\nPressure qualification blocked',font_size=13,color='white');plot.camera_position=[(35,-38,32),(0,0,4),(0,0,1)]
                plot.show(screenshot=str(output/'coupon.png'),auto_close=True)
                (output/'ribbed-solid.stl.gz').write_bytes(gzip.compress(m.export(file_type='stl'),mtime=0))
        vdb=f'ribbed-{h}-fields.vdb.gz';(output/vdb).write_bytes(gzip.compress((native/'coupon-fields.vdb').read_bytes(),mtime=0))
        rows.append({'voxel_mm':h,'native_receipt':receipt,'parts':parts,'vdb_gzip':vdb,'volume_partition_error':abs(sum(p['volume_mm3'] for p in parts.values())/(24*24*11.4)-1)})
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for count in [0,2,4]:
        rr=[c for c in r['cases'] if c['rib_count']==count]
        axes[0].plot([c['mesh_mm'] for c in rr],[c['maximum_nodal_von_mises_mpa'] for c in rr],'o-',label=f'{count} ribs')
        axes[1].semilogy([c['mesh_mm'] for c in rr],[c['maximum_displacement_mm'] for c in rr],'o-',label=f'{count} ribs')
    axes[0].axhline(40,color='crimson',ls='--',label='Assumed 40 MPa');axes[0].set_ylabel('Peak nodal von Mises (MPa)');axes[1].set_ylabel('Maximum displacement (mm)')
    for ax in axes:ax.invert_xaxis();ax.set_xlabel('Element target size (mm) — refinement →');ax.legend()
    fig.suptitle('CalculiX plane strain, 0.375 MPa — sharp-corner peaks do not converge');fig.tight_layout();fig.savefig(output/'mesh-sensitivity.png',dpi=160);plt.close(fig)
    sources=[ROOT/'source/study.py',Path(__file__),ROOT/'source/picogk/Program.cs',ROOT/'source/picogk/Coupon.csproj']
    report={'status':'conditional_pressure_and_native_geometry_research','geometry_runs':rows,'pressure_qualified':False,'manufacturing_authorized':False,'root_stress_converged':False,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in sources},'output_hashes':{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('Native fields, 5 hot passages and 12 CalculiX runs retained.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--fea',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.work,a.fea,a.output)
