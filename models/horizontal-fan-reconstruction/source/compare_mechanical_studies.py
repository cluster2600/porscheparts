#!/usr/bin/env python3
"""Compare conditional mechanical studies without converting them to allowables."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def compare(root,output):
    records=[];hashes={}
    for variant in ['R0','V5','V2']:
        for size,h in [(4.5,'h4p5'),(3.6,'h3p6')]:
            name='results/mechanics/mesh-'+variant+'-'+h+'.json';p=root/name;r=json.loads(p.read_text());hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
            if r['safe_rpm_range'] is not None or r['mesh']['minimum_Gauss4_jacobian']<=0:raise ValueError('Mesh gate/qualification')
            volume=json.loads((root/'results/geometry'/f'{variant}.json').read_text())['components']['rotor']['volume_mm3']
            records.append({'variant':variant,'requested_size_mm':size,'C3D10':r['mesh']['volume_elements'],'mass_kg_assuming_density_2700':volume*2700e-9,'maximum_displacement_mm':r['maximum_displacement_mm'],'maximum_radial_extension_mm':r['maximum_radial_extension_mm'],'first_unprestressed_frequency_Hz':r['modes_unprestressed'][0]['frequency_Hz'],'nodal_vm_peak_MPa_not_converged':r['von_mises_nodal_max_MPa'],'nodal_vm_p99_MPa_node_weighted':r['von_mises_nodal_p99_MPa']})
    metrics=['maximum_displacement_mm','maximum_radial_extension_mm','first_unprestressed_frequency_Hz','nodal_vm_peak_MPa_not_converged','nodal_vm_p99_MPa_node_weighted']
    change=lambda new,old:{k:100*(new[k]/old[k]-1) for k in metrics}
    fine={v:next(r for r in records if r['variant']==v and r['requested_size_mm']==3.6) for v in ['R0','V5','V2']}
    result={'status':'conditional_three_variant_two_grid_mechanical_comparison','records':records,'fine_vs_coarse_percent_change':{v:change(fine[v],next(r for r in records if r['variant']==v and r['requested_size_mm']==4.5)) for v in fine},'fine_variant_vs_R0_percent_change':{v:{**change(fine[v],fine['R0']),'mass_kg_assuming_density_2700':100*(fine[v]['mass_kg_assuming_density_2700']/fine['R0']['mass_kg_assuming_density_2700']-1)} for v in ['V5','V2']},'source_sha256':hashes,'local_stress_convergence_established':False,'safe_rpm_or_fatigue_qualified':False,'material_or_bearing_qualification_established':False,'physical_validation_established':False,'assumptions':'6000rpm, isotropic E70GPa nu.33 rho2700, fixed bore; unprestressed modes; no rotating prestress/gyroscopic/contact/thermal/aero/fatigue qualification'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();compare(a.study,a.output)
