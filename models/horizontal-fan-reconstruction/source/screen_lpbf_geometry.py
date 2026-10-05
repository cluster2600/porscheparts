#!/usr/bin/env python3
"""Geometry-only LPBF orientation/layer screening, not a process simulation."""
import argparse,csv,hashlib,json,math,struct
from pathlib import Path
import numpy as np


def triangles(path):
    data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0]
    if len(data)!=84+50*n:raise ValueError('Expected binary STL')
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    return np.frombuffer(data,offset=84,count=n,dtype=dtype)['vertices'].astype(float)


def screen(geometry,output):
    output.mkdir(parents=True,exist_ok=False)
    original=triangles(geometry/'rotor.stl');rows=[];poses=[]
    for tilt in [0,30,45,60,90]:
        for azimuth in [0,45]:
            t=math.radians(tilt);a=math.radians(azimuth)
            rx=np.array([[1,0,0],[0,math.cos(t),-math.sin(t)],[0,math.sin(t),math.cos(t)]])
            rz=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
            tri=original@(rz@rx).T;tri[:,:,2]-=tri[:,:,2].min()
            normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);mag=np.linalg.norm(normal,axis=1)
            nz=np.divide(normal[:,2],mag,out=np.zeros_like(mag),where=mag>0)
            extent=np.ptp(tri.reshape(-1,3),axis=0)
            overhang=(nz<-math.cos(math.radians(45))) & (tri[:,:,2].mean(axis=1)>.05)
            projected_area=mag*.5*np.abs(nz)
            row={'tilt_X_deg':tilt,'azimuth_Z_deg':azimuth,'bounding_box_mm':extent.tolist(),
                 'fits_hypothetical_250x250x300mm_envelope_with_10mm_each_side':bool(np.all(extent<=np.array([230,230,280]))),
                 'downward_overhang_surface_area_mm2':float((mag*.5)[overhang].sum()),
                 'vertical_support_column_proxy_mm3':float((projected_area*tri[:,:,2].mean(axis=1))[overhang].sum()),
                 'estimated_layers_at_50um':int(math.ceil(extent[2]/.05))}
            rows.append(row);poses.append(tri)
    # Slice the upright reference; oriented triangle-plane segments preserve the bore.
    tri=poses[0];levels=np.arange(.025,float(tri[:,:,2].max()),.05)
    layer_rows=[]
    for layer,z in enumerate(levels):
        active=tri[(tri[:,:,2].min(axis=1)<z)&(tri[:,:,2].max(axis=1)>z)]
        segments=[]
        for facet in active:
            hits=[]
            for i,j in [(0,1),(1,2),(2,0)]:
                if (facet[i,2]-z)*(facet[j,2]-z)<0:
                    hits.append(facet[i]+(facet[j]-facet[i])*(z-facet[i,2])/(facet[j,2]-facet[i,2]))
            if len(hits)!=2:continue
            normal=np.cross(facet[1]-facet[0],facet[2]-facet[0]);direction=np.cross([0,0,1],normal)
            if (hits[1]-hits[0])@direction<0:hits.reverse()
            segments.append(hits)
        segment=np.asarray(segments)
        area=abs(float(np.sum(segment[:,0,0]*segment[:,1,1]-segment[:,1,0]*segment[:,0,1])*.5)) if len(segment) else 0
        layer_rows.append((layer,z,area,len(segment)))
    csvpath=output/'R0-upright-layers.csv'
    with csvpath.open('w',newline='') as stream:
        writer=csv.writer(stream,lineterminator="\n");writer.writerow(['layer','z_mm','cross_section_area_mm2','intersection_segments']);writer.writerows(layer_rows)
    mesh_volume=abs(float(np.einsum('ij,ij->i',original[:,0],np.cross(original[:,1],original[:,2])).sum()/6))
    slice_volume=float(sum(r[2]*.05 for r in layer_rows))
    report={'status':'geometry_only_LPBF_screen','units':'mm','source_STL_sha256':hashlib.sha256((geometry/'rotor.stl').read_bytes()).hexdigest(),
            'material_scenario':'Hypothetical AlSi10Mg powder, properties and heat treatment not qualified; FEM assumed aluminium is a separate scenario',
            'machine_scenario':'Hypothetical 250 x 250 x 300 mm LPBF envelope; no specific machine, scan strategy or calibrated process selected',
            'layer_thickness_mm':.05,'overhang_threshold_deg_from_horizontal':45,'build_margin_mm_each_side':10,
            'orientations':rows,'upright_sliced_volume_mm3':slice_volume,'STL_signed_volume_absolute_mm3':mesh_volume,
            'slice_integrated_volume_relative_error':abs(slice_volume/mesh_volume-1),'layer_CSV_sha256':hashlib.sha256(csvpath.read_bytes()).hexdigest(),
            'support_proxy_limit':'Independent vertical columns; overlaps double counted, no generated support solids or laser toolpath',
            'thermal_history_residual_stress_distortion_porosity_microstructure_or_fatigue_simulated':False,
            'process_qualification_established':False,'manufacturing_authorized':False,
            'required_before_process_prediction':['Specific machine and qualified powder lot','Calibrated laser and scan strategy','Supports/baseplate/contact/thermal boundary conditions','Material temperature-dependent properties and calibration','Heat treatment, machining, CT/metallography and fatigue validation plan']}
    if report['slice_integrated_volume_relative_error']>.01:raise ValueError('Slice integration deviates from the STL volume by over 1%')
    (output/'lpbf-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('geometry',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args();screen(a.geometry,a.output)
