"""Independent finite-volume and transformed-mesh checks of the selected cold geometry."""
import math
import numpy as np
import study
from reconstruct import save


def run(output,prototypes,rows,native):
    checks=[]
    def contact(group,a,b):
        r=study.contact(a,b)
        row={'group':group,'volume_mm3':r['volume_mm3'],'passed':r['volume_mm3']==0,'method':r['method']}
        checks.append(row);print('CHECK '+group+' '+str(r['volume_mm3']),flush=True)
    for sweep in ('cam_sweep_intake','cam_sweep_exhaust'):
        contact('cam_rotation/'+sweep,native[sweep],prototypes['valve_cover'])
    for sweep in ('drive_sweep_intake','drive_sweep_exhaust'):
        for structure in ('drive_bionic_frame','drive_housing','drive_cover'):
            contact(sweep+'/'+structure,native[sweep],native[structure])
    for case in ('crankcase_negative','crankcase_positive'):
        contact('housing/'+case,native['drive_housing'],prototypes[case])
    for pipe in ('charge_pipe_negative','charge_pipe_positive','intake_negative','intake_positive'):
        for structure in ('drive_bionic_frame','drive_housing','drive_cover'):
            contact(pipe+'/'+structure,prototypes[pipe],native[structure])
    parts_by_head={}
    for r in rows:
        if 'cycle' in r and r['family'] in {'individual_head','valve_cover','rocker_carrier','cam_cap_bolted','rocker','cam_roller','cam_roller_pin','upper_spring_retainer','head_nut'}:
            c=r['cycle'];parts_by_head.setdefault((c['bank'],c['pair_index']),[]).append(r)
    for key,group in parts_by_head.items():
        cover=next(r for r in group if r['family']=='valve_cover');inverse=np.linalg.inv(cover['matrix_mm'])
        for r in group:
            if r['family'] in {'valve_cover','individual_head'}:continue
            mesh=prototypes[r['family']].copy();mesh.apply_transform(inverse@np.asarray(r['matrix_mm']))
            contact('cover/'+str(key)+'/'+r['family'],prototypes['valve_cover'],mesh)
    for bank in (-1,1):
        bracket=prototypes['intercooler_bionic_bracket_'+('negative' if bank<0 else 'positive')]
        for family in ('blower_shroud','cooling_blower'):
            row=next(r for r in rows if r['family']==family);mesh=prototypes[family].copy();mesh.apply_transform(row['matrix_mm'])
            contact('cooler_bracket/'+str(bank)+'/'+family,bracket,mesh)
    passed=all(c['passed'] for c in checks)
    result={'status':'sampled_cold_contacts_pass' if passed else 'cold_contacts_rejected','checks':checks,'passed':passed,
            'drive_clearance_uses_native_full_rotation_disc_envelopes':True,'full_assembly_interference_checked':False,
            'material_qualified':False,'thermal_or_fatigue_validated':False,'manufacturing_authorized':False,'engine_start_authorized':False}
    save(output/'verification.json',result)
    if not passed:raise ValueError('Independent cold contacts rejected; preserve output')
    return result
