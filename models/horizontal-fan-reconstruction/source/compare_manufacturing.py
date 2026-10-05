#!/usr/bin/env python3
"""Verify native fields and compare gauge-independent elastic build scenarios."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from prepare_engineering_sensitivities import parse_mesh
from summarize_engineering_sensitivities import displacement_blocks


def analyze(case):
    r=json.load(open(case/'summary.json'));prep=r['assumptions'];nodes,elements=parse_mesh((case/'rotor.inp').read_text());tags=sorted(nodes);x=np.array([nodes[n] for n in tags]);fields=displacement_blocks(case/'rotor.frd');u=np.array([fields[-1][n] for n in tags]);xc=x-x.mean(axis=0)
    # Least-squares infinitesimal rigid translation/rotation removal; no scale fit.
    A=np.zeros((len(tags),3,6));A[:,:,:3]=np.eye(3)
    A[:,0,4]=xc[:,2];A[:,0,5]=-xc[:,1];A[:,1,3]=-xc[:,2];A[:,1,5]=xc[:,0];A[:,2,3]=xc[:,1];A[:,2,4]=-xc[:,0]
    coeff,_,rank,_=np.linalg.lstsq(A.reshape(-1,6),u.ravel(),rcond=None)
    if rank!=6:raise ValueError('Incomplete rigid-motion gauge')
    residual=u-np.einsum('ijk,k->ij',A,coeff);m=np.linalg.norm(residual,axis=1);n=np.array(prep['build_direction']);first=np.array([1.,0.,0.]) if abs(n[0])<.9 else np.array([0.,1.,0.]);first-=n*np.dot(first,n);first/=np.linalg.norm(first);second=np.cross(n,first)
    th=np.deg2rad(prep['support_raster_inplane_deg']);first,second=first*np.cos(th)+second*np.sin(th),-first*np.sin(th)+second*np.cos(th);basis=np.array([first,second,n]);extent=np.ptp(x@basis.T,axis=0)
    metrics={'case':case.name,'configuration_id':prep['configuration_id'],'assumed_strain_amplitude':prep['strain_amplitude_assumed'],'build_direction':prep['build_direction'],'support_raster_pitch_mm':prep['support_raster_pitch_mm'],'attachment_nodes':prep['support_attachment_nodes'],'nodes':len(tags),'C3D10':len(elements),'build_bounding_box_from_native_mesh_mm':extent.tolist(),'nominal_BLTS400_450x300x400_envelope_with_10mm_margin_each_side_fits':bool(np.all(extent+20<=np.array([450,300,400]))),'maximum_released_displacement_mm':r['states'][-1]['maximum_displacement_mm'],'maximum_release_increment_mm':r['maximum_release_displacement_mm'],'maximum_rigid_motion_removed_displacement_mm':float(m.max()),'rms_rigid_motion_removed_displacement_mm':float(np.sqrt(np.mean(m*m))),'released_build_height_change_mm':float(np.ptp((x+u)@n)-np.ptp(x@n)),'attached_peak_elastic_stress_MPa_not_build_allowable':r['states'][0]['von_mises_max_MPa'],'released_peak_elastic_stress_MPa_not_build_allowable':r['states'][1]['von_mises_max_MPa'],'summary_sha256':hashlib.sha256((case/'summary.json').read_bytes()).hexdigest(),'source_step_sha256':prep['source_step_sha256'],'physical_or_process_validation_established':False}
    return metrics,u


def compare(root,output):
    rows=[];controls={};changes={}
    for v in ['R0','V5']:
        data={}
        for name in ['diagonal-edge','half-strain','zero-strain','upright','sparse-support','finer-mesh']:
            metrics,u=analyze(root/('manufacturing-'+v+'-'+name));rows.append(metrics);data[name]=(metrics,u)
        full=data['diagonal-edge'][1];half=data['half-strain'][1];zero=data['zero-strain'][1]
        err=float(np.linalg.norm(full-2*half)/np.linalg.norm(full));zm=float(np.linalg.norm(zero,axis=1).max())
        zstress=max(s['von_mises_max_MPa'] for s in json.load(open(root/('manufacturing-'+v+'-zero-strain')/'summary.json'))['states'])
        if err>2e-5 or zm>1e-8 or zstress>1e-7:raise ValueError('Linear scaling or zero-strain native control failed '+v)
        controls[v]={'relative_full_vs_twice_half_native_displacement_error':err,'maximum_zero_strain_displacement_mm':zm,'maximum_zero_strain_elastic_stress_MPa':zstress,'limits':{'relative_scaling':2e-5,'zero_displacement_mm':1e-8,'zero_stress_MPa':1e-7},'passed':True}
        coarse=data['diagonal-edge'][0];fine=data['finer-mesh'][0]
        changes[v]={k:(fine[k]/coarse[k]-1)*100 for k in ['maximum_released_displacement_mm','maximum_release_increment_mm','maximum_rigid_motion_removed_displacement_mm','rms_rigid_motion_removed_displacement_mm']}
    r={'status':'completed_matched_uncalibrated_elastic_support_release_sensitivity','cases':rows,'native_zero_and_linear_scaling_controls':controls,'finer_vs_coarse_percent_change':changes,'mesh_independence_established':False,'process_calibrated':False,'fabrication_validated':False,'service_validated':False,'interpretation':'Assumed strain and rigid point/column attachment sensitivity; no calibrated machine/process/material card, activation, plasticity, thermal field or qualified build-stress/distortion prediction. Six rigid modes removed for comparable global deformation; no scale removed.'}
    output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r));return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();compare(a.root,a.output)
