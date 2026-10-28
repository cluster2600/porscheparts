#!/usr/bin/env python3
"""Audit every tetrahedral result and independent centrifugal equilibrium."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from prepare_conforming_surface import sha


def fields(path, nodes, elements, fixed, gauss):
    displacement=np.zeros((nodes,3)); reaction=np.zeros((nodes,3)); peak=np.zeros(elements)
    seen_u=np.zeros(nodes,dtype=bool); seen_r=np.zeros(nodes,dtype=bool); seen_s=np.zeros(elements,dtype=np.uint8)
    headings={'forces (fx,fy,fz) for set BORE':'RF', 'displacements (vx,vy,vz) for set NALL':'U',
              'stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set ROTOR':'S'}
    active=None; sections=[]
    with Path(path).open() as stream:
        for line in stream:
            text=line.strip()
            if not text:continue
            heading=next((mode for prefix,mode in headings.items() if text.startswith(prefix+' and time ')),None)
            if heading:
                if heading in sections:raise ValueError('Repeated result section')
                sections.append(heading);active=heading;continue
            if text.startswith('total force (fx,fy,fz) for set BORE and time '):active=None;continue
            if active is None:continue
            row=text.split()
            if not row[0].isdigit():raise ValueError('Malformed result record')
            index=int(row[0])-1
            if active in ('U','RF'):
                if len(row)!=4 or not 0<=index<nodes:raise ValueError('Unexpected node result')
                seen,target=(seen_u,displacement) if active=='U' else (seen_r,reaction)
                if seen[index] or active=='RF' and not fixed[index]:raise ValueError('Duplicate or unsupported node result')
                value=np.asarray(list(map(float,row[1:])))
                if not np.isfinite(value).all():raise ValueError('Nonfinite node result')
                seen[index]=True;target[index]=value
            else:
                if len(row)!=8 or not 0<=index<elements:raise ValueError('Unexpected stress result')
                point=int(row[1])
                if not 1<=point<=gauss or seen_s[index] & (1<<(point-1)):raise ValueError('Duplicate or unexpected integration point')
                xx,yy,zz,xy,xz,yz=map(float,row[2:])
                vm=math.sqrt(.5*((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)+3*(xy*xy+xz*xz+yz*yz))
                if not all(math.isfinite(x) for x in (xx,yy,zz,xy,xz,yz,vm)):raise ValueError('Nonfinite stress result')
                seen_s[index] |= 1<<(point-1);peak[index]=max(peak[index],vm)
    if sections!=['RF','U','S'] or not seen_u.all() or not np.array_equal(seen_r,fixed) or np.any(seen_s!=(1<<gauss)-1):
        raise ValueError('Complete unique displacement, support reaction and integration-point coverage required')
    return displacement,reaction,peak


def centrifugal(vertices,cells,rho,omega2):
    force=np.zeros(3);moment=np.zeros(3);force_scale=np.zeros(3);moment_scale=np.zeros(3);volume=0.
    for start in range(0,len(cells),100000):
        tet=vertices[cells[start:start+100000,:4]]
        dv=np.linalg.det(np.swapaxes(tet[:,1:]-tet[:,0,None],1,2))/6
        if not np.isfinite(dv).all() or np.any(dv<=0):raise ValueError('Positive linear parent cells required')
        centre=tet.mean(axis=1);resultant=centre*(rho*omega2*dv[:,None]);resultant[:,2]=0
        sums=tet.sum(axis=1)
        mixed=(sums[:,:2]*sums[:,2,None]+(tet[:,:,:2]*tet[:,:,2,None]).sum(axis=1))/20
        couples=np.zeros_like(resultant);couples[:,0]=-mixed[:,1]*rho*omega2*dv;couples[:,1]=mixed[:,0]*rho*omega2*dv
        force+=resultant.sum(axis=0);moment+=couples.sum(axis=0)
        force_scale+=abs(resultant).sum(axis=0);moment_scale+=abs(couples).sum(axis=0);volume+=float(dv.sum())
    return force,moment,float(np.linalg.norm(force_scale)),float(np.linalg.norm(moment_scale)),volume


def nodal_centrifugal(vertices,cells,rho,omega2):
    # CCX linstatic intscheme=0: one-point C3D4 or four-point C3D10 body loads.
    if cells.shape[1]==4:coefficients=np.full((4,4),1/16)
    elif cells.shape[1]==10:
        low=.138196601125011;high=.585410196624968
        barycentric=np.full((4,4),low);np.fill_diagonal(barycentric,high)
        shapes=np.column_stack((barycentric*(2*barycentric-1),
            *[4*barycentric[:,i]*barycentric[:,j] for i,j in ((0,1),(1,2),(0,2),(0,3),(1,3),(2,3))]))
        coefficients=shapes.T@barycentric/4
    else:raise ValueError('C3D4 or straight C3D10 required')
    loads=np.zeros_like(vertices)
    for start in range(0,len(cells),100000):
        block=cells[start:start+100000];tet=vertices[block[:,:4]]
        volume=np.linalg.det(np.swapaxes(tet[:,1:]-tet[:,0,None],1,2))/6
        local=np.einsum('ij,njk->nik',coefficients,tet)*(rho*omega2*volume[:,None,None]);local[:,:,2]=0
        for j in range(block.shape[1]):np.add.at(loads,block[:,j],local[:,j])
    return loads


def assess(prepared,solved,execution,output):
    prepared,solved,execution,output=map(Path,(prepared,solved,execution,output))
    proof=json.loads((prepared/'receipt.json').read_text());job=json.loads(execution.read_text())
    if (proof['schema']!='935-conforming-fea-preparation-v1' or proof['numeric_geometry_admitted_for_solver'] is not True
            or proof['scale_verified'] is not False or proof['support_is_measured'] is not False
            or proof['physical_validation'] is not False or proof['manufacturing_authorized'] is not False
            or proof['formulation'] not in ('C3D4','C3D10') or job['schema']!='935-bounded-native-solve-v1'
            or job['solver_finished'] is not True or job['exit']!=0 or job['stop_reason'] is not None
            or job['deck_sha256']!=proof['deck_sha256']):raise ValueError('Successful matching bounded hypothesis solve required')
    if (sha(prepared/'rotor.inp')!=proof['deck_sha256'] or sha(solved/'rotor.inp')!=proof['deck_sha256']
            or sha(prepared/'geometry.npz')!=proof['geometry_npz_sha256'] or (solved/'ccx.exit').read_text().strip()!='0'):
        raise ValueError('Prepared geometry, deck or execution changed')
    log=(solved/'ccx.log').read_text()
    if 'Job finished' not in log or '*ERROR' in log:raise ValueError('Solver completion missing')
    if output.exists() or not output.parent.is_dir():raise ValueError('Fresh private output required')
    for parent in output.resolve().parents:
        if (parent/'.git').exists() and output.resolve().relative_to(parent).parts[0]!='work':raise ValueError('Private work/ output required')
    with np.load(prepared/'geometry.npz',allow_pickle=False) as data:vertices=data['vertices'];cells=data['tetrahedra']
    if len(vertices)!=proof['nodes'] or len(cells)!=proof['elements']:raise ValueError('Prepared dimensions differ')
    fixed=abs(np.linalg.norm(vertices[:,:2],axis=1)-proof['bore_radius_assumed_mm'])<proof['bore_band_assumed_mm']
    if int(fixed.sum())!=proof['clamped_bore_nodes']:raise ValueError('Support node set differs')
    gauss=1 if proof['formulation']=='C3D4' else 4
    displacement,reaction,peak=fields(solved/'rotor.dat',len(vertices),len(cells),fixed,gauss)
    force,moment,force_scale,moment_scale,volume=centrifugal(vertices,cells,proof['material_density_tonne_mm3'],(proof['rotor_rpm']*math.pi/30)**2)
    # RF is external nodal force, including DLOAD at the constrained nodes.
    nodal_body=nodal_centrifugal(vertices,cells,proof['material_density_tonne_mm3'],(proof['rotor_rpm']*math.pi/30)**2)
    raw_rf=reaction.copy();reaction[fixed]-=nodal_body[fixed]
    discrete_moment=np.cross(vertices,nodal_body).sum(axis=0)
    reactions=reaction.sum(axis=0);couples=np.cross(vertices[fixed],reaction[fixed]).sum(axis=0)
    force_error=float(np.linalg.norm(force+reactions)/max(force_scale,1e-30))
    moment_error=float(np.linalg.norm(discrete_moment+couples)/max(moment_scale,1e-30))
    away=np.linalg.norm(vertices[cells[:,:4]].mean(axis=1)[:,:2],axis=1)>=25
    report=dict(schema='935-conforming-result-audit-v1',status='complete_result_audited',source_sha256=sha(__file__),
                preparation_sha256=sha(prepared/'receipt.json'),execution_sha256=sha(execution),deck_sha256=proof['deck_sha256'],
                parent_geometry_sha256=proof['parent_geometry_sha256'],binary_sha256=job['binary_sha256'],
                formulation=proof['formulation'],nodes=len(vertices),elements=len(cells),integration_points_checked=len(cells)*gauss,
                conditional_volume_mm3=volume,conditional_mass_kg=volume*proof['material_density_tonne_mm3']*1000,
                maximum_displacement_mm=float(np.linalg.norm(displacement,axis=1).max()),von_mises_max_MPa=float(peak.max()),
                element_peak_p95_outside_r25_MPa=float(np.percentile(peak[away],95)) if away.any() else None,
                support_displacement_max_mm=float(abs(displacement[fixed]).max()),
                body_force_N=force.tolist(),reaction_force_N=reactions.tolist(),body_moment_Nmm=moment.tolist(),reaction_moment_Nmm=couples.tolist(),
                raw_RF_sum_N=raw_rf.sum(axis=0).tolist(),body_force_at_support_N=nodal_body[fixed].sum(axis=0).tolist(),
                discrete_body_moment_Nmm=discrete_moment.tolist(),
                continuum_moment_discretization_error=float(np.linalg.norm(discrete_moment-moment)/max(moment_scale,1e-30)),
                relative_force_balance_error=force_error,relative_moment_balance_error=moment_error,
                equilibrium_pass=force_error<1e-5 and moment_error<1e-5,rotor_rpm=proof['rotor_rpm'],material_id=proof['material_id'],
                source_unit='uncalibrated_scan_unit',solver_units=proof['solver_units'],scale_verified=False,support_is_measured=False,
                material_process_qualified=False,mesh_convergence_established=False,physical_validation=False,manufacturing_authorized=False,
                output_sha256={name:sha(solved/name) for name in ('rotor.dat','ccx.log','ccx.exit')})
    output.mkdir(mode=0o700);np.savez_compressed(output/'fields.npz',displacement=displacement,reaction=reaction,raw_RF=raw_rf,element_peak_von_mises=peak)
    report['fields_npz_sha256']=sha(output/'fields.npz');(output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','solved','execution','new_output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();assess(args.prepared,args.solved,args.execution,args.new_output)
