#!/usr/bin/env python3
"""Actual incompressible port energy/pressure, wall work and velocity checks."""
import argparse,hashlib,json,math,re
from pathlib import Path
import numpy as np
from diagnose_and_merge_fv_cells import read,body


def field_values(text,key,count,components):
    match=re.search(r'\b'+re.escape(key)+r'\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\n\)\s*;',text,re.S)
    if match:
        values=np.asarray(list(map(float,re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',match[2]))))
        if int(match[1])!=count or len(values)!=count*components:raise ValueError('Field count mismatch '+key)
        return values.reshape((count,components)) if components>1 else values
    match=re.search(r'\b'+re.escape(key)+r'\s+uniform\s+(\([^;]*\)|[^;]+);',text)
    if not match:raise ValueError('Field not serialized '+key)
    values=np.asarray(list(map(float,re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',match[1]))))
    if len(values)!=components:raise ValueError('Uniform component mismatch')
    return np.tile(values,(count,1)) if components>1 else np.full(count,values[0])


def patch_block(text,name):
    match=re.search(r'(?m)^\s*'+re.escape(name)+r'\s*\{',text)
    if not match:raise ValueError('Missing patch '+name)
    depth=1;start=match.end();end=start
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return text[start:end-1]


def analyze(case,output,time_name='600'):
    points,faces,owner,neighbor,patches=read(case);ni=len(neighbor);nc=int(max(owner.max(),neighbor.max()))+1
    data={name:(case/time_name/name).read_text() for name in ['U','p','phi','nut']}
    U=field_values(data['U'],'internalField',nc,3);P=field_values(data['p'],'internalField',nc,1);speed=np.linalg.norm(U,axis=1)
    cf=[[] for _ in range(nc)]
    for i,c in enumerate(owner):cf[int(c)].append(i)
    for i,c in enumerate(neighbor):cf[int(c)].append(i)
    cell_xyz=[points[sorted(set(faces[ids].ravel()))] for ids in cf]
    volumes=np.array([abs(float(np.linalg.det((xyz[1:]-xyz[0]).T)))/6 for xyz in cell_xyz]);centers=np.array([xyz.mean(axis=0) for xyz in cell_xyz])
    rho=1.2;rpm=6000.;omega=rpm*math.pi/30;ports={};energy_flux=0.;pressure_flux=0.;kinetic_flux=0.;wall_mass=0.;rotor_pressure_moment=None;wall_velocity_error=None
    zone_text=(case/'constant/polyMesh/cellZones').read_text();zone=patch_block(zone_text,'rotorZone')
    zmatch=re.search(r'cellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)\s*;',zone,re.S)
    if not zmatch:raise ValueError('Actual MRF cell zone missing')
    labels=np.asarray(list(map(int,zmatch[2].split())))
    mrf_cell=np.zeros(nc,dtype=bool);mrf_cell[labels]=True
    for patch in patches:
        name=patch['name'];nf=patch['nFaces'];start=patch['startFace'];tri=points[faces[start:start+nf]]
        sf=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*.5;fc=tri.mean(axis=1);area=np.linalg.norm(sf,axis=1)
        ub=patch_block(data['U'],name);pb=patch_block(data['p'],name)
        u=np.zeros((nf,3)) if re.search(r'\btype\s+noSlip\s*;',ub) else field_values(ub,'value',nf,3)
        p=P[owner[start:start+nf]] if re.search(r'\btype\s+zeroGradient\s*;',pb) else field_values(pb,'value',nf,1)
        phi=field_values(patch_block(data['phi'],name),'value',nf,1);ke=.5*np.einsum('ij,ij->i',u,u)
        energy_flux+=float(rho*((p+ke)*phi).sum());pressure_flux+=float(rho*(p*phi).sum());kinetic_flux+=float(rho*(ke*phi).sum())
        if name in ['inlet','outlet']:
            q=float(phi.sum());radial=fc[:,:2]/np.linalg.norm(fc[:,:2],axis=1)[:,None];ur=np.einsum('ij,ij->i',u[:,:2],radial);ut=-u[:,0]*radial[:,1]+u[:,1]*radial[:,0]
            ports[name]={'net_flow_m3_s':q,'gross_incoming_flow_m3_s':float(-phi[phi<0].sum()),'gross_outgoing_flow_m3_s':float(phi[phi>0].sum()),'area_m2':float(area.sum()),
            'area_mean_static_pressure_Pa_gauge':float(rho*(p*area).sum()/area.sum()),'signed_flux_mean_static_pressure_Pa_gauge':float(rho*(p*phi).sum()/q),
            'signed_flux_mean_total_pressure_Pa_gauge':float(rho*((p+ke)*phi).sum()/q),'pressure_energy_flux_W':float(rho*(p*phi).sum()),'kinetic_energy_flux_W':float(rho*(ke*phi).sum()),'axial_kinetic_energy_flux_W':float(.5*rho*(u[:,2]**2*phi).sum()),'radial_kinetic_energy_flux_W':float(.5*rho*(ur**2*phi).sum()),'tangential_kinetic_energy_flux_W':float(.5*rho*(ut**2*phi).sum())}
        else:
            wall_mass+=float(np.abs(phi).sum())
            moving_flux=np.einsum('ij,ij->i',np.column_stack((-omega*fc[:,1],omega*fc[:,0],np.zeros(nf))),sf)
            absolute_phi=phi+moving_flux*mrf_cell[owner[start:start+nf]]
            ports[name]={'net_reconstructed_absolute_phi_m3_s':float(absolute_phi.sum()),'absolute_reconstructed_absolute_phi_m3_s':float(np.abs(absolute_phi).sum()),'absolute_frame_flux_interpretation':'Stored phi is relative to MRF on faces whose owner is in rotorZone; reconstructed absolute flux adds Omega cross Cf dot Sf only on those faces. Moving rotor face flux is not stationary wall leakage.','net_stored_phi_m3_s':float(phi.sum()),'absolute_stored_phi_m3_s':float(np.abs(phi).sum()),'absolute_U_dot_Sf_m3_s':float(np.abs(np.einsum('ij,ij->i',u,sf)).sum()),'boundary_mechanical_energy_flux_W':float(rho*((p+ke)*phi).sum())}
        if name=='rotor':
            moment=np.cross(fc,rho*p[:,None]*sf).sum(axis=0);rotor_pressure_moment=moment.tolist()
            rigid=np.column_stack((-omega*fc[:,1],omega*fc[:,0],np.zeros(nf)))
            wall_velocity_error=float(np.linalg.norm(u-rigid,axis=1).max())
    folders=sorted((case/'postProcessing/rotorForces').iterdir(),key=lambda p:float(p.name))
    lines=[line for line in (folders[-1]/'forces.dat').read_text().splitlines() if line.strip() and not line.startswith('#')]
    numbers=list(map(float,re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',lines[-1])));torque_p=numbers[9];torque_v=numbers[12];torque=torque_p+torque_v;power=-torque*omega
    grad_path=case/time_name/'grad(U)';dissipation=None
    if grad_path.is_file():
        gradient=field_values(grad_path.read_text(),'internalField',nc,9).reshape(nc,3,3);sym=.5*(gradient+gradient.transpose(0,2,1));trace=np.trace(sym,axis1=1,axis2=2)
        nu_eff=1.5e-5+field_values(data['nut'],'internalField',nc,1)
        dissipation=float((2*rho*nu_eff*(np.einsum('ijk,ijk->i',sym,sym)-trace*trace/3)*volumes).sum())
    relative=U[labels]-np.column_stack((-omega*centers[labels,1],omega*centers[labels,0],np.zeros(len(labels))))
    relative_M=np.linalg.norm(relative,axis=1)/343
    gamma=1.4;Mmax=float(speed.max()/343)
    net_port_energy=sum(ports[n]['pressure_energy_flux_W']+ports[n]['kinetic_energy_flux_W'] for n in ['inlet','outlet'])
    total_rise=ports['outlet']['signed_flux_mean_total_pressure_Pa_gauge']-ports['inlet']['signed_flux_mean_total_pressure_Pa_gauge']
    report={'status' :'actual_field_mechanical_energy_and_velocity_screen','analysis_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rpm_assumed':rpm,'omega_rad_s':omega,'density_kg_m3_assumed':rho,'speed_of_sound_m_s_assumed':343.,
    'minimum_local_static_pressure_Pa_gauge':float(rho*P.min()),'maximum_local_static_pressure_Pa_gauge':float(rho*P.max()),'signed_flux_mean_total_pressure_rise_Pa':total_rise,'open_port_mechanical_energy_flux_to_input_power_ratio':net_port_energy/power,'port_energy_ratio_is_not_qualified_fan_efficiency':True,
    'operating_point':'Isolated fan: top total pressure 0 gauge, bottom static pressure 0 gauge; no imposed flow or installed engine resistance curve',
    'port_results':ports,'final_pressure_torque_Nm':torque_p,'final_viscous_torque_Nm':torque_v,'final_total_fluid_on_rotor_torque_Nm':torque,
    'final_rotor_input_power_torque_times_omega_W':power,'recomputed_rotor_pressure_moment_Nm':rotor_pressure_moment,
    'pressure_torque_recomputation_relative_error':abs(rotor_pressure_moment[2]-torque_p)/max(abs(torque_p),1e-20),
    'maximum_rotor_wall_velocity_difference_from_omega_cross_r_m_s':wall_velocity_error,
    'net_boundary_mechanical_energy_flux_W':energy_flux,'net_open_port_mechanical_energy_flux_W':sum(ports[n]['pressure_energy_flux_W']+ports[n]['kinetic_energy_flux_W'] for n in ['inlet','outlet']),'net_boundary_pressure_energy_flux_W':pressure_flux,'net_boundary_kinetic_energy_flux_W':kinetic_flux,
    'modeled_mean_viscous_plus_eddy_energy_transfer_W':dissipation,'remaining_power_after_port_energy_flux_W':power-energy_flux,
    'mean_mechanical_balance_residual_after_modeled_transfer_W':None if dissipation is None else power-energy_flux-dissipation,
    'mean_mechanical_balance_limit':'Port fluxes are actual fields. The volume transfer uses the exported FV gradient; numerical diffusion, turbulent transport and pressure/viscous work terms are not a qualified total-energy closure.',
    'maximum_speed_m_s':float(speed.max()),'maximum_local_Mach':Mmax,'maximum_MRF_relative_Mach':float(relative_M.max()),'MRF_volume_fraction_relative_Mach_above_0p3':float(volumes[labels][relative_M>.3].sum()/volumes[labels].sum()),'isentropic_density_departure_from_stagnation_at_max_absolute_Mach_screen':1-(1+(gamma-1)*Mmax*Mmax/2)**(-1/(gamma-1)),'isentropic_screen_gamma_assumed':gamma,'isentropic_screen_source':'https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html',
    'volume_fraction_local_Mach_above_0p3':float(volumes[speed>343*.3].sum()/volumes.sum()),'volume_weighted_mean_Mach':float((speed*volumes).sum()/volumes.sum()/343),
    'tip_speed_m_s_assuming_275mm':omega*.1375,'tip_Mach_assuming_275mm':omega*.1375/343,
    'global_mass_imbalance_kg_s':rho*(ports['inlet']['net_flow_m3_s']+ports['outlet']['net_flow_m3_s']),
    'sum_absolute_stored_relative_wall_phi_m3_s_not_leakage':wall_mass,'compressibility_sensitivity_required':bool(speed.max()>343*.3),
    'physical_validation_established':False,'energy_balance_physically_qualified':False,
    'field_sha256':{str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [case/time_name/name for name in ['U','p','phi','nut']]}}
    if not all(np.isfinite(x).all() for x in [U,speed,volumes]) or power<=0 or wall_velocity_error>1e-5 or report['pressure_torque_recomputation_relative_error']>1e-6:raise ValueError('Wall work/torque identity or field checks failed')
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('output',type=Path);p.add_argument('--time',default='600');a=p.parse_args();analyze(a.case,a.output,a.time)
