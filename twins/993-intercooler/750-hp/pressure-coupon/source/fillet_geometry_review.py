"""Independent check of the Linux PicoGK coupon with assumed rib-root fillets; no qualification.

Runs inside the cadsim image (trimesh, matplotlib). Each native run directory holds the
output of picogk-fillet/Program.cs plus the runtime.json written by the host runner. The
channel widths, topology and volumes are measured on the exported STLs and compared with the
analytical section; the fillet area is measured as the volume a filleted run loses against the
sharp run at the same voxel size, which cancels the common voxelization bias.
"""
import argparse
import gc
import gzip
import hashlib
import json
import math
from pathlib import Path
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
WIDTHS=[1.8,5.2,5.2,5.2,1.8];HEIGHT=3.;LENGTH=24.;CORNERS=4
WIDTH_TOLERANCE=.02
# The differential fillet area must match the analytical (1 - pi/4) r**2 per corner within this fraction.
FILLET_AREA_TOLERANCE=.15


def corner_area(radius):
    return (1-math.pi/4)*radius*radius


def inspect(run):
    receipt=json.loads((run/'receipt.json').read_text());parts={}
    for name,bodies in [('solid_mm',1),('hot_fluid_mm',5),('cold_fluid_mm',1)]:
        path=run/(name+'.stl');m=trimesh.load_mesh(path,process=True);before=m.volume;count=len(m.faces);raw=m.is_watertight
        m.update_faces(m.nondegenerate_faces() & m.unique_faces());m.remove_unreferenced_vertices()
        error=abs(m.volume/before-1)
        if not m.is_watertight or not m.is_winding_consistent or m.body_count!=bodies or error>1e-7:raise ValueError(f'Native topology rejected {run.name} {name}')
        part={'native_sha256':sha(path),'raw_closed':raw,'removed_faces':count-len(m.faces),'cleanup_volume_error':error,'closed_after_cleanup':True,'components':m.body_count,'volume_mm3':float(m.volume),'area_mm2':float(m.area),'bounds_mm':m.bounds.tolist()}
        if name=='hot_fluid_mm':
            channels=sorted(m.split(),key=lambda c:c.bounds[0,1]);rows=[]
            for c,width in zip(channels,WIDTHS):
                length=float(c.bounds[1,0]-c.bounds[0,0])
                rows.append({'width_y_mm':float(c.bounds[1,1]-c.bounds[0,1]),'height_z_mm':float(c.bounds[1,2]-c.bounds[0,2]),'length_x_mm':length,'volume_mm3':float(c.volume),'mean_section_mm2':float(c.volume)/length,
                             'analytic_section_mm2':width*HEIGHT-CORNERS*corner_area(receipt['fillet_radius_mm'])})
            for row,width in zip(rows,WIDTHS):
                if abs(row['width_y_mm']-width)>WIDTH_TOLERANCE or abs(row['height_z_mm']-HEIGHT)>WIDTH_TOLERANCE or abs(row['length_x_mm']-LENGTH)>WIDTH_TOLERANCE:raise ValueError(f'Hot channel differs from the section contract in {run.name}')
            part['channels']=rows
            # Section of the hot channels at mid-length, as raw plane-intersection segments.
            part['_section']=trimesh.intersections.mesh_plane(m,plane_normal=[1,0,0],plane_origin=[0,0,0])
        parts[name]=part
        # The 0.05 mm solid has about 5.5 million faces: free each mesh before loading the next one.
        del m;gc.collect()
    return receipt,parts


def run(native,output):
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);runs=[]
    for directory in sorted(p for p in native.iterdir() if p.is_dir()):
        receipt,parts=inspect(directory);runtime=json.loads((directory/'runtime.json').read_text())
        runs.append({'name':directory.name,'voxel_mm':receipt['voxel_mm'],'fillet_radius_mm':receipt['fillet_radius_mm'],'native_receipt':receipt,'runtime':runtime,'parts':parts,
                     'vdb_sha256':sha(directory/'coupon-fields.vdb'),'vdb_gzip_bytes':len(gzip.compress((directory/'coupon-fields.vdb').read_bytes(),mtime=0)),
                     'volume_partition_error':abs(sum(p['volume_mm3'] for p in parts.values())/(24*24*11.4)-1)})
        if receipt['vdb_sha256']!=runs[-1]['vdb_sha256']:raise ValueError('VDB does not match its receipt')
        if receipt['manufacturing_authorized'] or not receipt['fillet_radius_is_assumption']:raise ValueError('Receipt overclaims')
    fillets=[]
    for r in runs:
        if r['fillet_radius_mm']==0:continue
        sharp=next((s for s in runs if s['fillet_radius_mm']==0 and s['voxel_mm']==r['voxel_mm']),None)
        if sharp is None:raise ValueError('No sharp reference at voxel size '+str(r['voxel_mm']))
        measured=[(a['mean_section_mm2']-b['mean_section_mm2'])/CORNERS for a,b in zip(sharp['parts']['hot_fluid_mm']['channels'],r['parts']['hot_fluid_mm']['channels'])]
        expected=corner_area(r['fillet_radius_mm']);errors=[m/expected-1 for m in measured]
        row={'name':r['name'],'fillet_radius_mm':r['fillet_radius_mm'],'voxel_mm':r['voxel_mm'],'radius_over_voxel':r['fillet_radius_mm']/r['voxel_mm'],'analytic_corner_area_mm2':expected,'measured_corner_area_mm2':measured,'relative_errors':errors,
             'solid_volume_gain_mm3':r['parts']['solid_mm']['volume_mm3']-sharp['parts']['solid_mm']['volume_mm3'],'analytic_solid_volume_gain_mm3':20*expected*LENGTH,
             'within_tolerance':all(abs(e)<=FILLET_AREA_TOLERANCE for e in errors)}
        # A failed comparison is recorded, not hidden and not re-toleranced: the run stays in the report as unresolved.
        fillets.append(row)
    mac=json.loads((ROOT/'derived/review.json').read_text());mac_fine=next(g for g in mac['geometry_runs'] if g['voxel_mm']==.1)
    linux_sharp=next((r for r in runs if r['fillet_radius_mm']==0 and abs(r['voxel_mm']-.1)<1e-9),None)
    comparison=None
    if linux_sharp:
        comparison={name:{'mac_volume_mm3':mac_fine['parts'][name]['volume_mm3'],'linux_volume_mm3':linux_sharp['parts'][name]['volume_mm3'],'relative_difference':linux_sharp['parts'][name]['volume_mm3']/mac_fine['parts'][name]['volume_mm3']-1} for name in ['solid_mm','hot_fluid_mm','cold_fluid_mm']}
    figure,axes=plt.subplots(len(runs),1,figsize=(11,1.9*len(runs)),squeeze=False)
    for ax,r in zip(axes[:,0],runs):
        for (a,b) in r['parts']['hot_fluid_mm'].pop('_section'):ax.plot([a[1],b[1]],[a[2],b[2]],color='#2a6f97',lw=.6)
        ax.set_aspect('equal');ax.set_xlim(-11.6,11.6);ax.set_ylim(.4,4.2);ax.set_ylabel('Z (mm)')
        ax.set_title(f"Hot channels at X = 0, voxel {r['voxel_mm']} mm, assumed root fillet r = {r['fillet_radius_mm']} mm",fontsize=9)
    for r in runs:r['parts']['hot_fluid_mm'].pop('_section',None)
    axes[-1,0].set_xlabel('Y (mm)');figure.suptitle('Linux PicoGK coupon, assumed fillets: geometry only, not a printed or qualified part',fontsize=10);figure.tight_layout()
    figure.savefig(output/'fillet-geometry-sections.png',dpi=150);plt.close(figure)
    sources=[ROOT/'source/picogk-fillet/Program.cs',ROOT/'source/picogk-fillet/CouponFillet.csproj',Path(__file__)]
    report={'status':'conditional_filleted_native_geometry_research','fillet_radii_are_assumptions':True,'runs':runs,'fillet_area_checks':fillets,'fillet_area_tolerance':FILLET_AREA_TOLERANCE,'fillet_area_checks_failed':[f['name'] for f in fillets if not f['within_tolerance']],'width_tolerance_mm':WIDTH_TOLERANCE,
            'linux_sharp_vs_mac_0_1mm':comparison,
            'runtime_differs_from_mac_receipts':'Linux host stack in ~/picogk (see each runtime record); the Mac receipts in review.json and runtime.json are unchanged and remain the record of the Mac runs.',
            'stl_and_vdb_committed':False,'pressure_qualified':False,'manufacturing_authorized':False,'thermal_or_hydraulic_solver_executed':False,
            'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in sources},'output_hashes':{'fillet-geometry-sections.png':sha(output/'fillet-geometry-sections.png')}}
    (output/'fillet-geometry.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.native,a.output)
