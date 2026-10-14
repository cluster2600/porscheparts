#!/usr/bin/env python3
"""Independent mesh checks for the selected new head; operating qualification stays false."""
import argparse
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import study
import cams
from reconstruct import save,sha256


def verify(directory,previous):
    import numpy as np
    import trimesh
    config=json.loads((directory/'config.json').read_text());search=json.loads((directory/'search.json').read_text())
    report=json.loads((directory/'report.json').read_text())
    native=directory/'native-0.5'
    def mesh(name):
        m,a=study.prior.inspect(native/(name+'.stl'),True)
        if not a['passed']:raise ValueError('Topology rejected '+name)
        return m
    body=mesh(report['selected_head']);cylinder=trimesh.load_mesh(directory/'pieces/cylinder.stl',process=True)
    # The common cylinder template is rotated into the positive head frame, in millimetres.
    m=np.eye(4);m[:3,:3]=[[-1,0,0],[0,0,1],[0,1,0]];m[:3,3]=[0,0,-161.25]
    cylinder.apply_transform(m)
    old=json.loads((previous/'delivery-manifest.json').read_text())['files']
    path=previous/'pieces/piston.stl'
    if sha256(path)!=old['pieces/piston.stl']:raise ValueError('Piston changed')
    piston=trimesh.load_mesh(path,process=True)
    m[:3,3]=[0,0,132+33-211.25];piston.apply_transform(m)
    phi=np.linspace(0,4*math.pi,2881);checks=[]
    alpha=math.radians(8)
    for i in range(4):
        role='intake' if i<2 else 'exhaust';sign=1 if i<2 else -1
        n=np.array([0,sign*math.sin(alpha),math.cos(alpha)]);v=mesh(f'head_component_{i*3+1:02d}')
        law=cams.cam_law(role,search['timing']['roles'][role]);lift=law.valve_lift(phi)*1000
        gap=config['face_z_mm']-config[role+'_diameter_mm']/2*math.sin(alpha)+3.25
        gaps=gap+study.optimize.VT.piston_drop(phi,.066,.132)*1000-lift*math.cos(alpha)
        k=int(np.argmin(gaps));moving=v.copy();moving.apply_translation(-n*lift[k]);p=piston.copy()
        p.apply_translation([0,0,-study.optimize.VT.piston_drop(phi[k],.066,.132).item()*1000])
        valves=[v,moving]
        max_open=v.copy();max_open.apply_translation(-n*search['timing']['roles'][role]['max_lift_mm']);valves.append(max_open)
        checks.append({'valve':i+1,'role':role,'worst_sample_crank_deg':float(np.degrees(phi[k])),
                       'sample_axial_plane_gap_mm':float(gaps[k]),'worst_sample_valve_piston':study.contact(moving,p),
                       'valve_cylinder_closed_worst_and_maxlift':[study.contact(q,cylinder) for q in valves],
                       'valve_head_at_max_lift':study.contact(max_open,body)})
    collisions=[r['worst_sample_valve_piston']['volume_mm3'] for r in checks]+[c['volume_mm3'] for r in checks for c in r['valve_cylinder_closed_worst_and_maxlift']]
    if any(v>0 for v in collisions):raise ValueError('Valve piston/cylinder mesh intersection')
    if any(r['valve_head_at_max_lift']['volume_mm3']>0 for r in checks):raise ValueError('Valve/head mesh intersection')
    assembly=json.loads((directory/'assembly.json').read_text())
    head=next(r for r in assembly['instances'] if r['family']=='individual_head' and r['bank']==1)
    placed=body.copy();placed.apply_transform(head['matrix_mm'])
    mouths={name:study.contact(placed,trimesh.load_mesh(directory/'pieces'/(name+'.stl'),process=True))
            for name in ('intake_positive','exhaust_positive')}
    if any(r['volume_mm3']>0 for r in mouths.values()):raise ValueError('Head/manifold mouth interference')
    carrier=mesh('rocker_carrier');cap=mesh('cam_cap_bolted')
    selected={'head_stud','head_nut','upper_spring_retainer','rocker','cam_roller','cam_roller_pin','cam_cap_bolt'}
    mechanism=[];cache={};prototypes={}
    for cycle in cams.cycles():
        for family,pose in study.local_components(config,search,cycle):
            if family not in selected and not family.startswith(('outer_valve_spring_','inner_valve_spring_')):continue
            key=(family,pose.tobytes())
            if key not in cache:
                if family not in prototypes:prototypes[family]=trimesh.load_mesh(directory/'pieces'/(family+'.stl'),process=True)
                placed=prototypes[family].copy();placed.apply_transform(pose);cache[key]=study.contact(carrier,placed)
            mechanism.append({'cycle':cycle,'family':family,'carrier_contact':cache[key]})
        head=next(r for r in assembly['instances'] if r['family']=='individual_head' and r['cycle']==cycle)
        for role in ('intake','exhaust'):
            family=f'camshaft_{"negative" if cycle["bank"]<0 else "positive"}_{role}'
            if family not in prototypes:prototypes[family]=trimesh.load_mesh(directory/'pieces'/(family+'.stl'),process=True)
            cam=next(r for r in assembly['instances'] if r['family']==family)
            placed=prototypes[family].copy();placed.apply_transform(np.linalg.inv(head['matrix_mm'])@np.asarray(cam['matrix_mm']))
            mechanism.append({'cycle':cycle,'family':family,'carrier_contact':study.contact(carrier,placed),'cap_contact':study.contact(cap,placed)})
    if any(r['carrier_contact']['volume_mm3']>0 or r.get('cap_contact',{}).get('volume_mm3',0)>0 for r in mechanism):
        save(directory/'rejected-mechanism-contacts.json',mechanism)
        raise ValueError('Carrier/cap mechanism interference')
    chamber=mesh('chamber_envelope')
    clip=np.eye(4);clip[:3,3]=[0,0,20]
    chamber=trimesh.boolean.intersection([chamber,trimesh.creation.box([120,120,40],transform=clip)],engine='manifold',check_volume=True)
    cutters=[mesh(f'head_component_{i:02d}') for i in (1,2,4,5,7,8,10,11)]+[mesh('spark_plug')]
    # Positive volume chamber at the closed valve pose, excluding nominal solid inserts.
    closed=study.boolean_difference(chamber,cutters,'closed_chamber')
    deck_volume=math.pi*42.5**2*3.25
    clearance=closed.volume+deck_volume;swept=math.pi*42.5**2*66
    output={'classification':'independent_cold_nominal_mesh_screen_not_hot_or_physical_validation',
            'input_report_sha256':sha256(directory/'report.json'),'verifier_sha256':sha256(HERE/'verify.py'),
            'contacts':checks,'valve_piston_and_cylinder_sample_contacts_zero':not any(collisions),
            'positive_bank_front_head_manifold_contacts':mouths,
            'mechanism_contacts':mechanism,'twelve_cycle_pose_carrier_and_cam_contacts_zero':True,
            'closed_head_chamber_mm3':float(closed.volume),'assumed_deck_and_gasket_volume_mm3':deck_volume,
            'geometric_compression_ratio_hypothesis':float((swept+clearance)/clearance),
            'mesh_grid_mm':.5,'measured_hot_or_running_clearance_mm':None,
            'full_sweep_contact_checked':False,'measured_interfaces':None,
            'manufacturing_authorized':False,'engine_start_authorized':False}
    save(directory/'verification.json',output)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--previous',required=True,type=Path)
    args=parser.parse_args();verify(args.directory,args.previous)
