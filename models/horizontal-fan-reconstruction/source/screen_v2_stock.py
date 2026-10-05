#!/usr/bin/env python3
"""Machine-envelope/orientation screening of the actual stock mesh; no LPBF solver."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from screen_lpbf_geometry import triangles


def screen(geometry,output):
    report=json.loads((geometry/'stock-report.json').read_text());mesh=geometry/'V2-stock-scenario.stl'
    if hashlib.sha256(mesh.read_bytes()).hexdigest()!=report['blank_stl_sha256']:raise ValueError('Stock geometry identity')
    tri0=triangles(mesh);rows=[]
    for tilt,yaw in [(0,0),(30,0),(45,0),(60,0),(90,0),(90,45)]:
        a,b=map(math.radians,[tilt,yaw]);rx=np.array([[1,0,0],[0,math.cos(a),-math.sin(a)],[0,math.sin(a),math.cos(a)]])
        rz=np.array([[math.cos(b),-math.sin(b),0],[math.sin(b),math.cos(b),0],[0,0,1]])
        tri=tri0@(rz@rx).T;tri[:,:,2]-=tri[:,:,2].min();extent=np.ptp(tri.reshape(-1,3),axis=0)
        n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);mag=np.linalg.norm(n,axis=1);nz=n[:,2]/mag
        over=(nz<-math.cos(math.pi/4))&(tri[:,:,2].mean(axis=1)>.05)
        area=float((mag[over]/2).sum());column=float((mag[over]/2*abs(nz[over])*tri[over,:,2].mean(axis=1)).sum())
        fits={m['id']:bool(np.all(extent+20<=m['workspace_mm'])) for m in report['machine_scenarios']}
        rows.append({'tilt_X_deg':tilt,'yaw_Z_deg':yaw,'bounds_extent_mm':extent.tolist(),
                     'workspace_fit_with_10mm_each_side':fits,'geometric_layers_at_assumed50um':math.ceil(extent[2]/.05),
                     'downward_surface_area_over45deg_mm2':area,'independent_vertical_support_column_proxy_mm3':column})
    meshvol=abs(float(np.einsum('ij,ij->i',tri0[:,0],np.cross(tri0[:,1],tri0[:,2])).sum()/6))
    error=abs(meshvol/report['stock_blank_volume_mm3']-1)
    if error>.005:raise ValueError('Stock tessellation volume screen failed')
    result={'status':'actual_stock_orientation_screen_no_process_simulation','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'stock_report_sha256':hashlib.sha256((geometry/'stock-report.json').read_bytes()).hexdigest(),
            'STL_sha256':report['blank_stl_sha256'],'STL_volume_mm3':meshvol,'relative_STL_BRep_volume_error':error,
            'tessellation_volume_screen_relative':.005,'screen_is_not_manufacturing_tolerance':True,
            'orientations':rows,'margin_mm_each_side':10,'layer_thickness_scenario_mm':.05,
            'support_proxy_overlaps_and_clearance_not_resolved':True,
            'machine_reference_envelopes_not_actual_serial_or_build_qualification':True,
            'support_solids_toolpath_or_thermal_history_generated':False,
            'build_time_or_distortion_prediction_qualified':False,'process_qualification_established':False,
            'manufacturing_authorized':False,'physical_validation_established':False}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'relative_mesh_volume_error':error,'orientations':len(rows)}))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('geometry',type=Path);cli.add_argument('output',type=Path)
    a=cli.parse_args();screen(a.geometry,a.output)
