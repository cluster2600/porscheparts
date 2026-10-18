"""Evaluate the predeclared contour-2 objectives against the retained ad12 fields."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE.parent.parent/'revalidation-20261016'))
from audit_energy import read_mesh,EDGE_PAIRS,COORDINATE_ROUNDOFF_MM


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(folder,mesh,case):
    folder=Path(folder)/mesh
    tags,xyz,eids,conn=read_mesh(folder/'mesh.inp')
    points=xyz[conn]
    assert np.max(np.abs(points[:,4:]-(points[:,EDGE_PAIRS[:,0]]+points[:,EDGE_PAIRS[:,1]])/2))<=1e-10
    volume=np.linalg.det(points[:,1:4]-points[:,[0]])/6
    assert np.isfinite(volume).all() and np.all(volume>0)
    with np.load(folder/(case+'.npz'),allow_pickle=False) as data:
        assert np.array_equal(data['tags'],tags)
        assert np.array_equal(data['element_ids'],np.repeat(eids,4))
        # The deck stores decimal coordinates; use the existing audited
        # serialization-roundoff bound, never a geometric tolerance.
        assert np.allclose(data['xyz'],xyz,rtol=0,atol=COORDINATE_ROUNDOFF_MM)
        s=data['stress'];sx,sy,sz,xy,xz,yz=s.T
        vm=np.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy**2+xz**2+yz**2))
        assert np.isfinite(vm).all() and np.allclose(vm,data['VM'],rtol=1e-12,atol=1e-12)
        result={'displacement_max_mm':float(np.linalg.norm(data['displacement'],axis=1).max()),
                'integration_point_VM_max_MPa':float(vm.max()),
                'volume_above_900_mm3':float(np.sum((vm.reshape(-1,4)>900)*volume[:,None]/4))}
    receipt=json.loads((folder/(case+'.json')).read_text())
    for key in ('displacement_max_mm','integration_point_VM_max_MPa'):
        assert receipt[key]==result[key]
    return result


def decide(rows,mass,ceiling,v6f_pass,peak_ratio,volume_ratio):
    failures=[];objective_failures=[]
    expected={(mesh,case) for mesh in ('mesh-9','mesh-7')
              for case in ('combined-rigid-static','combined-spring-1000-static')}
    if len(rows)!=4 or {(r['mesh'],r['case']) for r in rows}!=expected:
        failures.append('Four distinct combined comparisons are required')
    if not math.isfinite(mass) or not 0<mass<=ceiling:
        failures.append('Mass ceiling failed')
    if not v6f_pass: failures.append('Independent V6f comparison failed')
    for row in rows:
        for key in ('displacement_max_mm','integration_point_VM_max_MPa'):
            value=row['ratios'][key]
            if not math.isfinite(value) or not 0<value<=1:
                failures.append(f"{row['mesh']}/{row['case']}: {key} regressed versus ad12")
        if 'spring' in row['case']:
            for key,limit in (('integration_point_VM_max_MPa',peak_ratio),('volume_above_900_mm3',volume_ratio)):
                value=row['ratios'][key]
                if not math.isfinite(value) or not 0<=value<=limit:
                    objective_failures.append(f"{row['mesh']}: {key} did not reach ratio {limit}")
    return {'comparative_non_regression_pass':not failures,
            'reinforcement_objectives_pass':not failures and not objective_failures,
            'failures':failures,'objective_failures':objective_failures}


def compare(candidate,baseline,v6f_report,output,criteria):
    candidate,baseline,v6f_report,output,criteria=map(Path,(candidate,baseline,v6f_report,output,criteria))
    assert not output.exists()
    rule=json.loads(criteria.read_text())
    assert sha(candidate/'carrier.step')==rule['candidate_STEP_sha256']
    assert sha(baseline/'carrier.step')==rule['baseline_STEP_sha256']
    before=json.loads((baseline/'study.json').read_text());after=json.loads((candidate/'study.json').read_text())
    assert before['material']==after['material'] and before['load_cases']==after['load_cases']
    v6f=json.loads(v6f_report.read_text())
    assert v6f['STEP_sha256']==rule['candidate_STEP_sha256']
    assert v6f['linear_consistency_pass']
    assert len(v6f['energy_checks'])==6 and all(row['energy_closure_pass'] for row in v6f['energy_checks'])
    geometry=json.loads((candidate/'geometry.json').read_text())
    assert geometry['geometry_sha256']['carrier.step']==rule['candidate_STEP_sha256']
    inspection=json.loads((candidate/'protected-interfaces.json').read_text())
    assert inspection['candidate_STEP_sha256']==rule['candidate_STEP_sha256']
    assert inspection['central_pad_symmetric_difference_mm3']==0
    assert len(inspection['end_interface_symmetric_difference_mm3'])==6
    assert not any(inspection['end_interface_symmetric_difference_mm3'].values())
    assert inspection['study_assembly_screen_pass']
    rows=[]
    for reference in rule['baseline_cases']:
        mesh,case=reference['mesh'],reference['case']
        assert sha(baseline/mesh/(case+'.json'))==reference['result_json_sha256']
        assert sha(baseline/mesh/(case+'.npz'))==reference['NPZ_sha256']
        original,current=metrics(baseline,mesh,case),metrics(candidate,mesh,case)
        for key in ('displacement_max_mm','integration_point_VM_max_MPa'):
            assert original[key]==reference[key]
        if 'spring' in case:
            assert math.isclose(original['volume_above_900_mm3'],reference['volume_above_900_mm3'],rel_tol=1e-13)
        ratios={key:current[key]/original[key] for key in current if original[key]>0}
        rows.append({'mesh':mesh,'case':case,'reference':original,'candidate':current,'ratios':ratios,
            'candidate_JSON_sha256':sha(candidate/mesh/(case+'.json')),
            'candidate_NPZ_sha256':sha(candidate/mesh/(case+'.npz'))})
    selection=decide(rows,geometry['dense_reference_mass_kg'],rule['mass_kg_max'],
                     v6f['selection']['selection_pass'],rule['K1000_peak_VM_ratio_max'],
                     rule['K1000_volume_above_900MPa_ratio_max'])
    report={'candidate_STEP_sha256':rule['candidate_STEP_sha256'],'baseline_STEP_sha256':rule['baseline_STEP_sha256'],
            'source_sha256':sha(__file__),'criteria_sha256':sha(criteria),
            'V6f_comparison_sha256':sha(v6f_report),'mass_kg':geometry['dense_reference_mass_kg'],
            'cases':rows,'selection':selection,'mesh_peak_convergence_established':False,
            'volume_scope':rule['volume_scope']}
    output.mkdir();(output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    if not selection['reinforcement_objectives_pass']:raise SystemExit(1)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','baseline','v6f_report','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--criteria',type=Path,default=SOURCE/'mechanical-criteria.json')
    args=parser.parse_args();compare(args.candidate,args.baseline,args.v6f_report,args.output,args.criteria)
