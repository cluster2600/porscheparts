#!/usr/bin/env python3
"""Compare admitted operating points; preserve the distinction from efficiency."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(root,output):
    records={};hashes={}
    def read(name):
        p=root/name;hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
    for variant in ['R0','V2']:
        for grid in ['h7','h5p6']:
            base='results/cfd/'+variant+'-common-'+grid
            mesh=read(base+'-mesh-report.json');gate=read(base+'-independent-mesh-gate.json')
            flow=read(base+'-flow-summary.json' if grid=='h7' else ('results/cfd/R0-fine-pressure015-750-summary.json' if variant=='R0' else 'results/cfd/V2-fine-pressure015-900-summary.json'))
            balance=read(base+'-balance-v4.json')
            if not gate['accepted_for_bounded_pilot'] or not flow['criteria_checks']['complete_finite_fields']:raise ValueError('Mesh or native field coverage failed '+base)
            admitted=all(flow['criteria_checks'].values())
            if (flow['status']=='reference_pilot_admitted_numerically')!=admitted:raise ValueError('Flow status contradicts its unchanged criteria')
            q=flow['last_window_mean_outlet_flow_m3_s'];power=flow['last_window_mean_rotor_input_power_W'];outlet=balance['port_results']['outlet']
            records[variant+'-'+grid]={'cells':mesh['volume_elements'],'final_iteration':flow['iterations_completed'],'mean_last20_Q_m3_s':q,'mean_last20_input_power_W':power,'mean_last20_fluid_on_rotor_torque_Nm':flow['last_window_mean_fluid_on_rotor_torque_Nm'],'Q_per_input_power_m3_per_J_screen':q/power,'final_signed_flux_total_pressure_rise_Pa':balance['signed_flux_mean_total_pressure_rise_Pa'],'final_open_port_mechanical_energy_flux_W':balance['net_open_port_mechanical_energy_flux_W'],'final_port_energy_to_input_power_ratio_not_qualified_efficiency':balance['open_port_mechanical_energy_flux_to_input_power_ratio'],'final_outlet_gross_reverse_flow_m3_s':outlet['gross_incoming_flow_m3_s'],'final_absolute_Mach_max':balance['maximum_local_Mach'],'final_MRF_relative_Mach_max':balance['maximum_MRF_relative_Mach'],'final_mean_energy_balance_residual_after_modeled_transfer_W':balance['mean_mechanical_balance_residual_after_modeled_transfer_W'],'final_energy_balance_residual_fraction_input_power':balance['mean_mechanical_balance_residual_after_modeled_transfer_W']/balance['final_rotor_input_power_torque_times_omega_W'],'all_frozen_flow_gates_passed':admitted,'failed_frozen_criteria':[k for k,v in flow['criteria_checks'].items() if not v]}
    metrics=['mean_last20_Q_m3_s','mean_last20_input_power_W','Q_per_input_power_m3_per_J_screen','final_signed_flux_total_pressure_rise_Pa','final_port_energy_to_input_power_ratio_not_qualified_efficiency']
    change=lambda new,old:{k:100*(new[k]/old[k]-1) for k in metrics}
    r={'status':'actual_operating_points_with_explicit_frozen_admission_and_grid_limits','operating_point':'Isolated 6000 rpm; top total pressure 0 gauge, bottom static pressure 0 gauge; steady incompressible kOmegaSST MRF, first-order convection; no installed engine resistance curve','records':records,'V2_vs_R0_percent_change':{grid:change(records['V2-'+grid],records['R0-'+grid]) if all(records[v+'-'+grid]['all_frozen_flow_gates_passed'] for v in ['R0','V2']) else None for grid in ['h7','h5p6']},'fine_vs_coarse_percent_change':{variant:change(records[variant+'-h5p6'],records[variant+'-h7']) if records[variant+'-h5p6']['all_frozen_flow_gates_passed'] else None for variant in ['R0','V2']},'paired_fine_grid_admitted':all(records[v+'-h5p6']['all_frozen_flow_gates_passed'] for v in ['R0','V2']),'source_sha256':hashes,'grid_independence_established':False,'physical_validation_established':False,'qualified_efficiency_established':False,'installed_cooling_improvement_proven':False,'interpretation':'Reduced power must be read with reduced flow and achieved pressure at these boundary conditions. Q/P and port-energy ratios are screening metrics. Two differently refined unstructured tetrahedral grids without wall layers, a closed total-energy audit or compressible sensitivity do not establish grid independence or installed performance.'}
    output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();compare(a.study,a.output)
