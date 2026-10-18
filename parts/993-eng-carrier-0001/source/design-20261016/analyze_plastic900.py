"""Audit retained J2 reference increments, plastic zone, unloading and incremental work."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE.parent/'revalidation-20261016'))
from audit_energy import sha,read_mesh,blocks

# Four nominal load increments: this is a distinct incremental-work diagnostic,
# not the 1e-4 equality used for the retained linear elastic cases.
WORK_RELATIVE_TOLERANCE=1e-3
PEEQ_DETECTION_THRESHOLD=1e-8


def fields(path):
    widths={'displacements':4,'forces':4,'stresses':8,
            'equivalent plastic strain':3,'internal energy density':3}
    result={name:{} for name in widths};active=None;rows=[];time=None
    def finish():
        if active is not None:
            array=np.asarray(rows)
            assert array.ndim==2 and array.shape[1]==widths[active] and np.isfinite(array).all()
            assert time not in result[active]
            result[active][time]=array
    with Path(path).open() as stream:
        for line in stream:
            clean=line.strip()
            if 'for set ' in clean and 'time ' in clean:
                finish();active=next((name for name in widths if clean.startswith(name+' (')),None)
                rows=[];time=float(clean.rsplit('time',1)[1])
            elif active is not None:
                row=clean.split()
                if len(row)==widths[active] and row[0].isdigit():
                    rows.append([float(v.replace('D','E')) for v in row])
    finish()
    return result


def audit(folder,output):
    folder,output=Path(folder),Path(output)
    assert not output.exists()
    receipt=json.loads((folder/'runtime.json').read_text())
    plan=json.loads((folder/'plan.json').read_text())
    name=receipt['name'];data=fields(folder/(name+'.dat'))
    assert receipt['mesh_sha256']==sha(folder/'mesh.inp')
    assert receipt['input_sha256']==sha(folder/(name+'.inp'))
    assert json.loads((folder/'mesh.json').read_text())['STEP_sha256']==plan['geometry_STEP_sha256']
    tags,xyz,eids,conn=read_mesh(folder/'mesh.inp')
    points=xyz[conn[:,:4]];volume=np.linalg.det(points[:,1:]-points[:,[0]])/6
    assert np.all(volume>0)
    expected=np.column_stack((np.repeat(eids,4),np.tile(np.arange(1,5),len(eids))))
    force=np.zeros_like(xyz);stiffness=np.zeros_like(xyz);springs={}
    for key,rows in blocks(folder/(name+'.inp')):
        if key=='*CLOAD':
            for row in rows:
                node,dof,value=row.split(',');force[np.searchsorted(tags,int(node)),int(dof)-1]+=float(value)
        elif key.startswith('*ELEMENT,TYPE=SPRING1'):
            springs[key.split('ELSET=')[1]]=np.array([[int(v) for v in row.split(',')] for row in rows])[:,1]
        elif key.startswith('*SPRING,'):
            nodes=springs.pop(key.split('ELSET=')[1]);dof,k=int(rows[0]),float(rows[1])
            stiffness[np.searchsorted(tags,nodes),dof-1]+=k
    assert not springs and np.count_nonzero(stiffness)>0
    frame_times=sorted(data['displacements'])
    assert frame_times and frame_times==sorted(data['stresses'])==sorted(data['equivalent plastic strain'])==sorted(data['internal energy density'])
    frames=[];previous_u=np.zeros_like(xyz);previous_t=0.;external_work=0.;gross_external_work=0.
    for time in frame_times:
        load_factor=2-time if plan.get('unload_to_zero') and time>1 else time
        urows=data['displacements'][time]
        assert np.array_equal(urows[:,0],tags)
        u=urows[:,1:]
        stress=data['stresses'][time];pe=data['equivalent plastic strain'][time];energy=data['internal energy density'][time]
        for values in (stress,pe,energy): assert np.array_equal(values[:,:2],expected)
        tensor=stress[:,2:];sx,sy,sz,xy,xz,yz=tensor.T
        vm=np.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+xz*xz+yz*yz))
        peeq=pe[:,2].reshape(-1,4);assert peeq.min()>=0
        reaction=-stiffness*u
        external_increment=float(.5*(load_factor+previous_t)*np.sum(force*(u-previous_u)))
        external_work+=external_increment;gross_external_work+=abs(external_increment)
        spring_energy=float(.5*np.sum(stiffness*u*u))
        solid_energy=float(np.sum(energy[:,2].reshape(-1,4)*volume[:,None]/4))
        peak=int(vm.argmax());current_xyz=xyz+u if receipt['constitutive_model']['geometric_nonlinearity'] else xyz
        active=peeq>PEEQ_DETECTION_THRESHOLD
        centres=points.mean(axis=1);plast=active.any(axis=1)
        displacement_norm=np.linalg.norm(u,axis=1);peak_node=int(displacement_norm.argmax())
        peak_plastic=int(peeq.argmax())//4
        frame={'total_time':time,'load_factor':load_factor,'displacement_max_mm':float(displacement_norm.max()),
               'displacement_peak_node':int(tags[peak_node]),'displacement_peak_original_xyz_mm':xyz[peak_node].tolist(),
               'VM_max_MPa':float(vm.max()),'VM_peak_element':int(expected[peak,0]),
               'PEEQ_max':float(peeq.max()),'PEEQ_detection_threshold':PEEQ_DETECTION_THRESHOLD,
               'PEEQ_peak_element':int(eids[peak_plastic]),'PEEQ_peak_element_corner_centroid_mm':centres[peak_plastic].tolist(),
               'plastic_quadrature_volume_mm3':float(np.sum(active*volume[:,None]/4)),
               'plastic_element_centroid_bounds_mm':([centres[plast].min(axis=0).tolist(),centres[plast].max(axis=0).tolist()] if plast.any() else None),
               'spring_energy_Nmm':spring_energy,'CCX_solid_internal_energy_Nmm':solid_energy,
               'external_incremental_trapezoid_work_Nmm':external_work,
               'external_gross_trapezoid_work_Nmm':gross_external_work,
               'work_absolute_residual_Nmm':solid_energy+spring_energy-external_work,
               'work_relative_closure_error':(abs((solid_energy+spring_energy)/external_work-1) if abs(external_work)>1e-30 else None),
               'work_relative_to_gross_error':abs(solid_energy+spring_energy-external_work)/gross_external_work,
               'applied_force_N':(load_factor*force).sum(axis=0).tolist(),
               'applied_moment_about_model_origin_Nmm':np.cross(current_xyz,load_factor*force).sum(axis=0).tolist(),
               'force_residual_N':(reaction+load_factor*force).sum(axis=0).tolist(),
               'moment_residual_Nmm':np.cross(current_xyz,reaction+load_factor*force).sum(axis=0).tolist()}
        frames.append(frame);previous_t=load_factor;previous_u=u
    final=frames[-1]
    report={'source_sha256':sha(__file__),'runtime_sha256':sha(folder/'runtime.json'),
            'inputs_sha256':{n:sha(folder/n) for n in ('mesh.inp',name+'.inp',name+'.dat',name+'.sta')},
            'geometric_nonlinearity':receipt['constitutive_model']['geometric_nonlinearity'],
            'constitutive_model':receipt['constitutive_model'],
            'frames':frames,'target_load_factor_reached':any(abs(frame['load_factor']-1)<1e-7 for frame in frames),
            'planned_path_complete':abs(final['total_time']-(2 if plan.get('unload_to_zero') else 1))<1e-7,
            'mesh_volume_mm3':float(volume.sum()),'work_relative_tolerance':WORK_RELATIVE_TOLERANCE,
            'incremental_work_diagnostic_pass':final['work_relative_to_gross_error']<=WORK_RELATIVE_TOLERANCE,
            'maximum_ENER_relative_to_gross_error':max(frame['work_relative_to_gross_error'] for frame in frames),
            'all_frames_ENER_diagnostic_pass':all(frame['work_relative_to_gross_error']<=WORK_RELATIVE_TOLERANCE for frame in frames),
            'scope':'J2 reference sensitivity; no damage/fatigue model. Volume uses reference integration-point quadrature threshold; bounds use element centroids. Incremental external work follows the frozen loading/unloading path.'}
    maximum_domain=receipt['constitutive_model'].get('maximum_measured_equivalent_plastic_strain')
    if maximum_domain is not None:
        report['measured_plastic_domain_max']=maximum_domain
        report['within_measured_pre_necking_domain']=max(frame['PEEQ_max'] for frame in frames)<=maximum_domain
    if plan.get('unload_to_zero'):
        report['unloading_complete']=abs(final['total_time']-2)<1e-7 and abs(final['load_factor'])<1e-7
        report['unloaded_residual']=final
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();audit(args.folder,args.output)
