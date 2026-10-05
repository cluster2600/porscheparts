#!/usr/bin/env python3
"""Summarize actual CalculiX FRD nodal fields and unprestressed eigenvalues."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def read_frd(path):
    fields={};active=None
    with path.open() as stream:
        for line in stream:
            if line.startswith(' -4'):
                active=line.split()[1];fields[active]={}
            elif line.startswith(' -1') and active in {'DISP','STRESS'}:
                tag=int(line[3:13]);count=3 if active=='DISP' else 6
                fields[active][tag]=[float(line[13+12*i:25+12*i]) for i in range(count)]
    return fields


def summarize(case,output):
    import numpy as np
    mesh=json.loads((case/'mesh-report.json').read_text())
    for name in ['rotation','modal']:
        log=(case/('log.'+name)).read_text()
        if 'Job finished' not in log or '*ERROR' in log:raise ValueError(name+' did not finish normally')
    nodes={};active=False
    for line in (case/'rotation.inp').read_text().splitlines():
        if line.startswith('*'):active=line=='*NODE'
        elif active:
            values=line.split(',');nodes[int(values[0])]=list(map(float,values[1:4]))
    fields=read_frd(case/'rotation.frd')
    if set(nodes)!=set(fields.get('DISP',{})) or set(nodes)!=set(fields.get('STRESS',{})):
        raise ValueError('Incomplete nodal field output')
    ids=sorted(nodes);xyz=np.array([nodes[i] for i in ids]);disp=np.array([fields['DISP'][i] for i in ids]);s=np.array([fields['STRESS'][i] for i in ids])
    if not all(np.isfinite(v).all() for v in [xyz,disp,s]):raise ValueError('Nonfinite solver field')
    xx,yy,zz,xy,yz,zx=s.T
    vm=np.sqrt(.5*((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)+3*(xy*xy+yz*yz+zx*zx))
    radial=np.linalg.norm((xyz+disp)[:,:2],axis=1)-np.linalg.norm(xyz[:,:2],axis=1)
    modal=[]
    for line in (case/'modal.dat').read_text().split('P A R T I C I P A T I O N')[0].splitlines():
        values=line.split()
        if len(values)==5 and values[0].isdigit():
            number=int(values[0]);eigen,angular,freq,imag=map(float,values[1:])
            if min(eigen,angular,freq)<=0 or imag!=0 or not math.isclose(angular,freq*2*math.pi,rel_tol=1e-6):raise ValueError('Invalid mode')
            modal.append({'mode':number,'frequency_Hz':freq})
    if [m['mode'] for m in modal]!=list(range(1,13)):raise ValueError('Incomplete modes')
    peak=int(np.argmax(vm));version=re.search(r'Version ([0-9.]+)',(case/'log.rotation').read_text())
    result={'status':'completed_conditional_centrifugal_and_unprestressed_modal_FEM',
            'configuration_id':mesh['configuration_id'],'solver':'CalculiX','solver_version':version[1] if version else 'unknown',
            'rpm_assumed':mesh['rpm_assumed'],'mesh':mesh,'stress_recovery':'FRD extrapolated and nodally averaged stress; raw maxima retained; node-weighted percentile, not integration-point stress',
            'von_mises_nodal_max_MPa':float(vm.max()),'von_mises_nodal_p99_MPa':float(np.quantile(vm,.99)),
            'peak_stress_node':ids[peak],'peak_stress_position_mm':xyz[peak].tolist(),
            'maximum_displacement_mm':float(np.linalg.norm(disp,axis=1).max()),'maximum_radial_extension_mm':float(radial.max()),
            'modes_unprestressed':modal,'mesh_independence_established':False,
            'rotating_prestress_gyroscopic_contact_thermal_aero_and_fatigue_included':False,
            'material_or_bearing_qualification_established':False,'safe_rpm_range':None,'manufacturing_authorized':False,
            'file_sha256':{name:hashlib.sha256((case/name).read_bytes()).hexdigest() for name in
                          ['rotation.inp','rotation.frd','rotation.dat','log.rotation','modal.inp','modal.dat','log.modal','mesh-report.json']}}
    output.write_text(json.dumps(result,indent=2)+'\n')
    np.savez_compressed(output.with_suffix('.npz'),node_ids=np.array(ids),xyz_mm=xyz,displacement_mm=disp,von_mises_nodal_MPa=vm)
    print(json.dumps({k:v for k,v in result.items() if k not in ['mesh','file_sha256']}));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();summarize(a.case,a.output)
