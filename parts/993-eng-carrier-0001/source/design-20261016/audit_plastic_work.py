"""Independent small-strain J2 work check: elastic compliance plus 900*PEEQ dissipation."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
from analyze_plastic900 import fields
sys.path.insert(0,str(SOURCE.parent/'revalidation-20261016'))
from audit_energy import sha,read_mesh,strain_energy

RELATIVE_TOLERANCE=1e-3


def audit(folder,analysis_path,output):
    folder,output=Path(folder),Path(output)
    assert not output.exists()
    runtime=json.loads((folder/'runtime.json').read_text())
    assert not runtime['constitutive_model']['geometric_nonlinearity']
    assert runtime['constitutive_model']['true_VM_yield_MPa']==900
    assert runtime['constitutive_model']['E_MPa']==107000 and runtime['constitutive_model']['nu']==.31
    previous=json.loads(Path(analysis_path).read_text())
    name=runtime['name'];values=fields(folder/(name+'.dat'))
    assert previous['inputs_sha256'][name+'.dat']==sha(folder/(name+'.dat'))
    assert runtime['mesh_sha256']==sha(folder/'mesh.inp')
    assert runtime['input_sha256']==sha(folder/(name+'.inp'))
    tags,xyz,eids,conn=read_mesh(folder/'mesh.inp')
    points=xyz[conn];volume=np.linalg.det(points[:,1:4]-points[:,[0]])/6
    rows=[]
    for frame in previous['frames']:
        time=frame['load_factor'];stress=values['stresses'][time][:,2:].reshape(-1,4,6)
        elastic,_=strain_energy(points,stress,107000,.31)
        peeq=values['equivalent plastic strain'][time][:,2].reshape(-1,4)
        dissipated=float(900*np.sum(peeq*volume[:,None]/4))
        total=elastic+dissipated+frame['spring_energy_Nmm']
        error=abs(total/frame['external_incremental_trapezoid_work_Nmm']-1)
        rows.append({'load_factor':time,'elastic_compliance_energy_Nmm':elastic,
                     'perfect_plastic_dissipation_Nmm':dissipated,
                     'spring_energy_Nmm':frame['spring_energy_Nmm'],
                     'external_incremental_trapezoid_work_Nmm':frame['external_incremental_trapezoid_work_Nmm'],
                     'relative_closure_error':error,'tolerance':RELATIVE_TOLERANCE,
                     'closure_pass':error<=RELATIVE_TOLERANCE})
    coupon=fields(folder/'coupon/coupon.dat')['equivalent plastic strain'][1.][:,2]
    expected=.02-900/107000
    coupon_error=float(np.max(np.abs(coupon-expected)))
    assert coupon.shape==(8,) and coupon_error<=1e-6
    report={'source_sha256':sha(__file__),'field_parser_sha256':sha(SOURCE/'analyze_plastic900.py'),
            'analysis_sha256':sha(analysis_path),'solver_dat_sha256':sha(folder/(name+'.dat')),
            'frames':rows,'all_frames_pass':all(row['closure_pass'] for row in rows),
            'coupon_expected_PEEQ':expected,'coupon_max_absolute_PEEQ_error':coupon_error,
            'coupon_PEEQ_tolerance':1e-6,'coupon_PEEQ_pass':True,
            'scope':'Additive small-strain J2, constant900MPa perfectly plastic stress. Dissipation=900*integral(PEEQ). External work uses retained increments; tighten increments if this diagnostic fails. Not applied to finite-deformation Cauchy stresses.'}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    parser.add_argument('analysis',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();audit(args.folder,args.analysis,args.output)
