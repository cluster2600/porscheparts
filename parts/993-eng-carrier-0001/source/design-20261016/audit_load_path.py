"""Locate high elastic demand and audit the frozen distributed eye springs."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE.parent/'revalidation-20261016'))
from audit_energy import sha,read_mesh,blocks


def rigid_matrix(r):
    a=np.zeros((len(r),3,6));a[:,:,:3]=np.eye(3)
    a[:,0,4]=r[:,2];a[:,0,5]=-r[:,1]
    a[:,1,3]=-r[:,2];a[:,1,5]=r[:,0]
    a[:,2,3]=r[:,1];a[:,2,4]=-r[:,0]
    return a


def audit(folder,output):
    folder,output=Path(folder),Path(output)
    assert not output.exists()
    rows=[]
    for mesh_name in ('mesh-9','mesh-7'):
        mesh=folder/mesh_name
        tags,xyz,eids,conn=read_mesh(mesh/'mesh.inp')
        points=xyz[conn[:,:4]]
        volume=np.linalg.det(points[:,1:]-points[:,[0]])/6
        assert np.all(volume>0)
        centre=points.mean(axis=1)
        masks={'central_pad_and_ribs':np.abs(centre[:,0])<65,
               'arm_root':(np.abs(centre[:,0])>=65)&(np.abs(centre[:,0])<105),
               'arms':(np.abs(centre[:,0])>=105)&(np.abs(centre[:,0])<255),
               'eye_blends_and_eyes':np.abs(centre[:,0])>=255}
        with np.load(mesh/'mesh.npz',allow_pickle=False) as surface:
            for case in ('combined-rigid-static','combined-spring-1000-static'):
                path=mesh/(case+'.npz')
                with np.load(path,allow_pickle=False) as data:
                    assert np.array_equal(data['element_ids'],np.repeat(eids,4))
                    vm=data['VM'].reshape(-1,4)
                    demand=[]
                    for label,mask in masks.items():
                        demand.append({'region':label,'volume_mm3':float(volume[mask].sum()),
                          'VM_max_MPa':float(vm[mask].max()),
                          'quadrature_volume_above_threshold_mm3':{
                              str(threshold):float(np.sum((vm[mask]>threshold)*volume[mask,None]/4))
                              for threshold in (880,900,1200,1500)}})
                    peak=np.unravel_index(vm.argmax(),vm.shape)
                    row={'mesh':mesh_name,'case':case,'NPZ_sha256':sha(path),
                         'mesh_sha256':sha(mesh/'mesh.inp'),'regions':demand,
                         'peak_element':int(eids[peak[0]]),'peak_element_corner_centroid_mm':centre[peak[0]].tolist(),
                         'total_quadrature_volume_above_900_mm3':float(np.sum((vm>900)*volume[:,None]/4)),
                         'total_mesh_volume_mm3':float(volume.sum()),'spring_audit':[]}
                    if 'spring' in case:
                        springs=[lines for key,lines in blocks(mesh/(case+'.inp')) if key.startswith('*SPRING,')]
                        assert len(springs)==6
                        reaction=np.zeros_like(xyz)
                        for eye in range(2):
                            indices=np.searchsorted(tags,surface[f'end{eye}'])
                            p,u=xyz[indices],data['displacement'][indices]
                            coefficients=[float(lines[1]) for lines in springs[eye*3:eye*3+3]]
                            assert np.allclose(coefficients,1000/len(indices),rtol=1e-14)
                            k=coefficients[0]
                            reaction[indices]=-k*u
                            local=p-np.array([-280 if eye==0 else 280,0,0])
                            matrix=rigid_matrix(local)
                            fixture=k*np.einsum('nai,naj->ij',matrix,matrix)
                            centred=p-p.mean(axis=0)
                            fit_matrix=rigid_matrix(centred).reshape(-1,6)
                            fit=np.linalg.lstsq(fit_matrix,u.reshape(-1),rcond=None)[0]
                            residual=u-(fit_matrix@fit).reshape(-1,3)
                            row['spring_audit'].append({'eye':eye,'nodes':len(indices),
                                'coefficient_per_node_dof_N_mm':k,
                                'translation_block_N_mm':fixture[:3,:3].tolist(),
                                'rotation_block_Nmm_rad':fixture[3:,3:].tolist(),
                                'translation_rotation_coupling_N':fixture[:3,3:].tolist(),
                                'best_fit_small_rotation_degree':np.degrees(fit[3:]).tolist(),
                                'best_fit_translation_mm':fit[:3].tolist(),
                                'bore_deformation_RMS_after_rigid_fit_mm':float(np.sqrt(np.mean(residual**2))),
                                'reaction_force_N':reaction[indices].sum(axis=0).tolist(),
                                'reaction_moment_about_eye_centre_Nmm':np.cross(local,reaction[indices]).sum(axis=0).tolist()})
                        assert np.allclose(reaction[np.searchsorted(tags,data['fixed'])],data['reaction'],atol=1e-9,rtol=1e-10)
                        row['applied_force_N']=data['force'].sum(axis=0).tolist()
                        row['applied_moment_about_model_origin_Nmm']=np.cross(xyz,data['force']).sum(axis=0).tolist()
                        row['force_residual_N']=(reaction+data['force']).sum(axis=0).tolist()
                        row['moment_residual_Nmm']=np.cross(xyz,reaction+data['force']).sum(axis=0).tolist()
                    rows.append(row)
    report={'source_sha256':sha(__file__),'STEP_sha256':sha(folder/'carrier.step'),'cases':rows,
            'volume_scope':'Equal four-point affine-C3D10 quadrature weights applied to threshold indicators; approximation, not an exact yielded volume.',
            'region_scope':'Assigned by element corner centroid; locations are not integration-point coordinates.',
            'threshold_scope':'880/900 MPa are reference diagnostic thresholds, not manufactured-material allowables.',
            'spring_scope':'1000 N/mm per eye and per translational axis, distributed equally to retained bore nodes. Rotation blocks are the induced rigid-bore spring stiffness, not a bushing measurement.'}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();audit(args.folder,args.output)
