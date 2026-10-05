#!/usr/bin/env python3
"""Compare actual reference solver outputs with the frozen acceptance protocol."""
import argparse,hashlib,json,math,re
from pathlib import Path
import numpy as np


def summarize(case,output):
    protocol=json.loads((case/'reference-protocol.json').read_text());criteria=protocol['acceptance_all_required'];n=criteria['last_window_iterations']
    log=(case/'log.foamRun').read_text();residuals=[]
    blocks=re.split(r'(?m)^Time = ',log)[1:]
    for block in blocks:
        iteration=float(re.match(r'([\d.eE+-]+)',block)[1]);row={'iteration':iteration}
        for field,value in re.findall(r'Solving for (\w+), Initial residual = ([\d.eE+-]+)',block):row[field]=max(row.get(field,0),float(value))
        residuals.append(row)
    if len(residuals)<n or 'End' not in log or 'FOAM FATAL' in log:raise ValueError('Incomplete/failed reference run')
    def table(relative):
        rows=[list(map(float,re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',line))) for line in (case/relative).read_text().splitlines() if line.strip() and not line.startswith('#')]
        return np.array(rows)
    pp=case/'postProcessing'
    start=sorted((pp/'inletFlow').iterdir(),key=lambda p:float(p.name))[-1].name
    inlet=table('postProcessing/inletFlow/'+start+'/surfaceFieldValue.dat')[-n:]
    outlet=table('postProcessing/outletFlow/'+start+'/surfaceFieldValue.dat')[-n:]
    force=table('postProcessing/rotorForces/'+start+'/forces.dat')[-n:]
    if not np.array_equal(inlet[:,0],outlet[:,0]) or not np.array_equal(inlet[:,0],force[:,0]):raise ValueError('Measurement iteration mismatch')
    torque=force[:,9]+force[:,12];qin=inlet[:,1];qout=outlet[:,1]
    residual_max={key:max(r[key] for r in residuals[-n:]) for key in ['p','Ux','Uy','Uz','k','omega']}
    ratio=lambda x:float(np.std(x)/abs(np.mean(x)))
    imbalance=np.abs(qin+qout)/((np.abs(qin)+np.abs(qout))*.5)
    final=case/format(residuals[-1]['iteration'],'.12g')
    fields_finite=True;field_counts={};max_speed=None
    cell_count=max(int(x) for x in re.search(r'(?m)^\d+\s*\n\((.*?)\n\)',(case/'constant/polyMesh/owner').read_text(),re.S)[1].split())+1
    # The maximum neighbour may exceed the maximum owner in a sorted mesh.
    neighbor_text=(case/'constant/polyMesh/neighbour').read_text()
    cell_count=max(cell_count,max(int(x) for x in re.search(r'(?m)^\d+\s*\n\((.*?)\n\)',neighbor_text,re.S)[1].split())+1)
    for field in ['U','p','k','omega','nut']:
        text=(final/field).read_text()
        match=re.search(r'internalField\s+nonuniform\s+List<(?:scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
        if not match:raise ValueError('Expected complete final nonuniform field '+field)
        numbers=re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',match[2]);values=np.asarray(list(map(float,numbers)))
        components=3 if field=='U' else 1
        fields_finite=fields_finite and int(match[1])==cell_count and len(values)==cell_count*components and bool(np.isfinite(values).all()) and not bool(re.search(r'(?i)\b(?:nan|inf)\b',match[2]))
        field_counts[field]=int(match[1])
        if field=='U':max_speed=float(np.linalg.norm(values.reshape(-1,3),axis=1).max())
    initial_times=[float(p.split('/')[0]) for p in protocol.get('initial_fields_sha256',{})]
    expected_first=min(initial_times)+1 if initial_times else 1
    checks={'initial_time_matches_frozen_continuation':residuals[0]['iteration']==expected_first,'residual_p':residual_max['p']<=criteria['maximum_initial_residual_p'],
            'residual_U':max(residual_max[k] for k in ['Ux','Uy','Uz'])<=criteria['maximum_initial_residual_U_components'],
            'residual_turbulence':max(residual_max['k'],residual_max['omega'])<=criteria['maximum_initial_residual_k_and_omega'],
            'mass_balance':float(imbalance.max())<=criteria['maximum_absolute_inlet_plus_outlet_flow_over_mean_absolute_flow'],
            'flow_stability':max(ratio(qin),ratio(qout))<=criteria['maximum_flow_relative_standard_deviation'],
            'torque_stability':ratio(torque)<=criteria['maximum_rotor_torque_relative_standard_deviation'],
            'declared_flow_direction':bool((qin<0).all() and (qout>0).all()),
            'complete_finite_fields':bool(fields_finite),
            'finite_measurements':bool(np.isfinite(inlet).all() and np.isfinite(outlet).all() and np.isfinite(force).all())}
    r={'status':'reference_pilot_admitted_numerically' if all(checks.values()) else 'reference_pilot_not_converged_to_frozen_criteria',
       'protocol_id':protocol['protocol_id'],'first_iteration':residuals[0]['iteration'],'expected_first_iteration':expected_first,'final_field_cell_counts':field_counts,'maximum_final_speed_m_s':max_speed,'maximum_final_local_Mach_assuming_343m_s':max_speed/343,'iterations_completed':residuals[-1]['iteration'],'window_size':n,'criteria_checks':checks,
       'maximum_initial_residual_last_window':residual_max,'last_window_mean_outlet_flow_m3_s':float(qout.mean()),
       'last_window_mean_inlet_flow_m3_s':float(qin.mean()),'last_window_max_mass_imbalance_ratio':float(imbalance.max()),
       'last_window_outlet_flow_relative_std':ratio(qout),'last_window_rotor_torque_relative_std':ratio(torque),
       'last_window_mean_fluid_on_rotor_torque_Nm':float(torque.mean()),'last_window_mean_rotor_input_power_W':float(-torque.mean()*protocol['rpm_assumed']*math.pi/30),
       'aerodynamic_mesh_independence_established':False,'wall_resolution_qualified':False,'physical_validation_established':False,'performance_improvement_proven':False,
       'file_sha256':{str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [case/'log.foamRun',case/'reference-protocol.json',pp/'inletFlow'/start/'surfaceFieldValue.dat',pp/'outletFlow'/start/'surfaceFieldValue.dat',pp/'rotorForces'/start/'forces.dat']}}
    output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('output',type=Path);a=p.parse_args();summarize(a.case,a.output)
