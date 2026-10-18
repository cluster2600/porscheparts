"""Audit finite C3D10 internal work from retained Cauchy stresses and nodal deformation."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
from analyze_plastic900 import fields
from ccx_curve_reference import effective_curve
sys.path.insert(0,str(SOURCE.parent/'revalidation-20261016'))
from audit_energy import read_mesh,sha,blocks,EDGE_PAIRS

WORK_RELATIVE_TOLERANCE=1e-4


def gradients(points):
    """Reference gradients in official CCX2.21 gauss3d5 integration-point order."""
    points=np.asarray(points)
    assert points.ndim==3 and points.shape[1:]==(10,3) and np.isfinite(points).all()
    assert np.max(np.abs(points[:,4:]-(points[:,EDGE_PAIRS[:,0]]+points[:,EDGE_PAIRS[:,1]])/2))<=1e-10
    initial_jacobian=np.swapaxes(points[:,1:4]-points[:,[0]],1,2)
    determinant=np.linalg.det(initial_jacobian)
    assert np.all(determinant>0)
    a,b=.585410196624968,.138196601125011
    natural=np.array([[b,b,b],[a,b,b],[b,a,b],[b,b,a]])
    barycentric=np.column_stack((1-natural.sum(axis=1),natural))
    dl=np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    derivative=np.empty((4,10,3))
    derivative[:,:4]=(4*barycentric[:,:,None]-1)*dl[None,:,:]
    for index,(i,j) in enumerate(EDGE_PAIRS):
        derivative[:,index+4]=4*(barycentric[:,j,None]*dl[i]+barycentric[:,i,None]*dl[j])
    return np.einsum('qni,eij->eqnj',derivative,np.linalg.inv(initial_jacobian)),determinant/24


def first_piola(tensor,deformation):
    determinant=np.linalg.det(deformation)
    assert np.isfinite(deformation).all() and np.isfinite(tensor).all() and np.all(determinant>0)
    stress=np.zeros(tensor.shape[:-1]+(3,3))
    for i in range(3):stress[...,i,i]=tensor[...,i]
    for component,(i,j) in enumerate(((0,1),(0,2),(1,2)),3):
        stress[...,i,j]=stress[...,j,i]=tensor[...,component]
    return determinant[...,None,None]*(stress@np.swapaxes(np.linalg.inv(deformation),-1,-2)),determinant


def hardening_integral(plastic_strain,curve):
    """Exact integral of the model's piecewise-linear yield-stress curve."""
    strain,stress=curve[:,1],curve[:,0]
    assert np.isfinite(plastic_strain).all() and plastic_strain.min()>=0
    assert plastic_strain.max()<=strain[-1]+1e-8
    slopes=np.diff(stress)/np.diff(strain)
    cumulative=np.r_[0,np.cumsum(.5*(stress[1:]+stress[:-1])*np.diff(strain))]
    index=np.clip(np.searchsorted(strain,plastic_strain,side='right')-1,0,len(strain)-2)
    difference=plastic_strain-strain[index]
    return cumulative[index]+stress[index]*difference+.5*slopes[index]*difference*difference


def audit(folder,output):
    folder,output=Path(folder),Path(output)
    assert not output.exists()
    runtime=json.loads((folder/'runtime.json').read_text());plan=json.loads((folder/'plan.json').read_text())
    assert runtime['constitutive_model']['geometric_nonlinearity']
    name=runtime['name'];data=fields(folder/(name+'.dat'))
    assert runtime['mesh_sha256']==sha(folder/'mesh.inp')
    assert runtime['input_sha256']==sha(folder/(name+'.inp'))
    assert json.loads((folder/'mesh.json').read_text())['STEP_sha256']==plan['geometry_STEP_sha256']
    tags,xyz,eids,conn=read_mesh(folder/'mesh.inp')
    derivative,weights=gradients(xyz[conn])
    expected=np.column_stack((np.repeat(eids,4),np.tile(np.arange(1,5),len(eids))))
    load=np.zeros_like(xyz);spring_k=np.zeros_like(xyz);spring_nodes={}
    for key,rows in blocks(folder/(name+'.inp')):
        if key=='*CLOAD':
            for row in rows:
                node,dof,value=row.split(',');load[np.searchsorted(tags,int(node)),int(dof)-1]+=float(value)
        elif key.startswith('*ELEMENT,TYPE=SPRING1'):
            spring_nodes[key.split('ELSET=')[1]]=np.array([[int(v) for v in row.split(',')] for row in rows])[:,1]
        elif key.startswith('*SPRING,'):
            nodes=spring_nodes.pop(key.split('ELSET=')[1]);spring_k[np.searchsorted(tags,nodes),int(rows[0])-1]+=float(rows[1])
    assert not spring_nodes
    previous_f=np.broadcast_to(np.eye(3),(len(eids),4,3,3)).copy()
    previous_p=np.zeros_like(previous_f);previous_u=np.zeros_like(xyz)
    material_path=folder/'material-curve.inp'
    if material_path.is_file():
        assert runtime['constitutive_model']['curve_sha256']==sha(material_path)
        raw_curve=np.loadtxt(material_path,delimiter=',',comments='*')
    else:
        assert runtime['constitutive_model']['true_VM_yield_MPa']==900
        raw_curve=np.array([[900.,0],[900.,1]])
    curve=effective_curve(raw_curve)
    previous_plastic_integral=np.zeros((len(eids),4));previous_jacobian=np.ones((len(eids),4))
    plastic_work=0.;previous_load=0.;internal=0.;external=0.;gross_external=0.;frames=[]
    for time in sorted(data['displacements']):
        displacement=data['displacements'][time];stress=data['stresses'][time]
        assert np.array_equal(displacement[:,0],tags) and np.array_equal(stress[:,:2],expected)
        u=displacement[:,1:];tensor=stress[:,2:].reshape(-1,4,6)
        deformation=np.eye(3)+np.einsum('eni,eqnj->eqij',u[conn],derivative)
        piola,jacobian=first_piola(tensor,deformation)
        plastic_values=data['equivalent plastic strain'][time]
        assert np.array_equal(plastic_values[:,:2],expected)
        plastic_integral=hardening_integral(plastic_values[:,2].reshape(-1,4),curve)
        difference=plastic_integral-previous_plastic_integral
        assert difference.min()>=-1e-5
        plastic_work+=float(np.sum(.5*(jacobian+previous_jacobian)*difference*weights[:,None]))
        internal_increment=float(np.sum(.5*(piola+previous_p)*(deformation-previous_f)*weights[:,None,None,None]))
        spring_increment=float(.5*np.sum(spring_k*(u*u-previous_u*previous_u)))
        factor=2-time if plan.get('unload_to_zero') and time>1 else time
        external_increment=float(.5*(factor+previous_load)*np.sum(load*(u-previous_u)))
        internal+=internal_increment+spring_increment;external+=external_increment;gross_external+=abs(external_increment)
        residual=internal-external;relative=abs(residual)/max(gross_external,1e-30)
        frames.append({'total_time':time,'load_factor':factor,'minimum_detF_at_Gauss':float(jacobian.min()),
                       'solid_Piola_work_increment_Nmm':internal_increment,'spring_work_increment_Nmm':spring_increment,
                       'external_work_increment_Nmm':external_increment,'internal_cumulative_work_Nmm':internal,
                       'external_cumulative_work_Nmm':external,'gross_external_cumulative_work_Nmm':gross_external,
                       'plastic_work_curve_integral_J_trapezoid_estimate_Nmm':plastic_work,
                       'residual_Nmm':residual,'relative_to_gross_work':relative,'work_pass':relative<=WORK_RELATIVE_TOLERANCE})
        previous_f,previous_p,previous_u,previous_load=deformation,piola,u,factor
        previous_plastic_integral,previous_jacobian=plastic_integral,jacobian
    report={'source_sha256':sha(__file__),'field_parser_sha256':sha(SOURCE/'analyze_plastic900.py'),
            'solver_dat_sha256':sha(folder/(name+'.dat')),'mesh_sha256':sha(folder/'mesh.inp'),
            'runtime_sha256':sha(folder/'runtime.json'),'frames':frames,
            'material_curve_sha256':sha(material_path) if material_path.is_file() else None,
            'relative_work_tolerance':WORK_RELATIVE_TOLERANCE,'all_frames_pass':all(frame['work_pass'] for frame in frames),
            'plastic_work_scope':'Integrate the actual CCX-effective piecewise-linear yield curve over PEEQ, with endpoint-trapezoidal detF correction. This is a converged-increment estimate of plastic work, includes isotropic hardening work, and is not a heat or damage measurement.',
            'scope':'Independent reference-volume quadrature of trapezoidal first-Piola stress work, P=det(F)*CauchyStress*inv(F).T, using full quadratic nodal displacement gradients. Spring work is exact endpoint energy difference. Residual scaled by gross external work to retain meaning during unloading cancellation.',
            'quadrature_source':'Official CCX2.21 gauss.f142-147,339-341, shape10tet.f; release archiveSHA52a20ef7216c6e2de75eae460539915640e3140ec4a2f631a9301e01eda605ad'}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=audit(args.folder,args.output)
    if not result['all_frames_pass']:raise SystemExit(1)
