#!/usr/bin/env python3
"""Prepare matched P1/P2 935 centrifugal studies with audited numeric transport."""
import argparse
from fractions import Fraction as Q
import json
import math
from pathlib import Path
import time

import numpy as np
from import_conforming_volume import ROOT, helper, integer_points
from prepare_conforming_surface import sha

SHARED=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'


def quadratic_nodes(vertices,cells,edges):
    pairs=np.concatenate([np.sort(cells[:,[i,j]],axis=1) for i,j in edges])
    unique,inverse=np.unique(pairs,axis=0,return_inverse=True)
    mids=(vertices[unique[:,0]]+vertices[unique[:,1]])/2
    return np.vstack((vertices,mids)),np.column_stack((cells,len(vertices)+inverse.reshape(6,-1).T))


def prepare(case_path,output):
    case_path,output=Path(case_path),Path(output);start=time.monotonic();c=json.loads(case_path.read_text())
    if any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) for k in
           ('rotor_rpm','bore_radius_assumed_mm','bore_band_assumed_mm')):raise ValueError('Finite numeric conditions required')
    if (c['purpose']!='hypothesis_screen' or c['scale_verified'] is not False or c['support_is_measured'] is not False
            or not 1<=c['rotor_rpm']<=12000 or not 5<=c['bore_radius_assumed_mm']<=20
            or not 0<c['bore_band_assumed_mm']<=2):raise ValueError('Bounded uncalibrated rotor hypothesis required')
    if output.exists() or not output.parent.is_dir():raise ValueError('Fresh private output required')
    audit_path,volume_path=Path(c['audit_path']),Path(c['volume_path'])
    a=json.loads(audit_path.read_text())
    if (sha(audit_path)!=c['audit_sha256'] or a['status']!='topology_and_exact_orientation_passed'
            or sha(volume_path)!=a['volume_npz_sha256'] or a['geometry_sha256']!=c['geometry_sha256']):
        raise ValueError('Matching complete conforming-volume audit required')
    cards=ROOT/'twins/935-horizontal-cooling-system-f0/vast-omniverse-screen/materials.json'
    card=next(x for x in json.loads(cards.read_text())['materials'] if x['id']==c['material_id'])
    if c['material_id']!='alsi10mg':raise ValueError('First matched formulation study retains AlSi10Mg')
    codec_path=SHARED/'prepare_tetgen_mechanics_ccx.py';mapping_path=SHARED/'audit_quadratic_mapping.py'
    codec=helper(codec_path,'_935_ccx_codec');mapping=helper(mapping_path,'_935_quadratic_bound')
    with np.load(volume_path,allow_pickle=False) as d:v=d['vertices'].copy();linear=d['tetrahedra'].copy()
    parent_nodes=len(v);vertices,quadratic=quadratic_nodes(v,linear,mapping.EDGES);transport=vertices.copy()
    output.mkdir(mode=0o700);(output/'case.json').write_bytes(case_path.read_bytes())
    for name in ('P1','P2'):(output/name).mkdir(mode=0o700)
    maximum_corner_error=Q(0)
    with (output/'P1/rotor.inp').open('x') as p1,(output/'P2/rotor.inp').open('x') as p2:
        for stream in (p1,p2):stream.write('*HEADING\n935 uncalibrated centrifugal formulation study; assumed N-mm-tonne-s\n*NODE\n')
        for i,row in enumerate(vertices):
            tokens=[codec.ccx_field(x) for x in row];parsed=list(map(float,tokens));transport[i]=parsed
            text=str(i+1)+','+','.join(tokens)+'\n';p2.write(text)
            if i<parent_nodes:
                p1.write(text)
                if any(float(x)!=y for x,y in zip(row,parsed)):
                    maximum_corner_error=max(maximum_corner_error,sum(abs(Q(float(x))-Q(y)) for x,y in zip(row,parsed)))
        p1.write('*ELEMENT,TYPE=C3D4,ELSET=ROTOR\n');p2.write('*ELEMENT,TYPE=C3D10,ELSET=ROTOR\n')
        for i,(lo,hi) in enumerate(zip(linear,quadratic),1):
            p1.write(str(i)+','+','.join(str(int(x)+1) for x in lo)+'\n')
            p2.write(str(i)+','+','.join(str(int(x)+1) for x in hi)+'\n')
        groups={}
        for name,stream,count in (('P1',p1,parent_nodes),('P2',p2,len(vertices))):
            fixed=np.flatnonzero(abs(np.linalg.norm(transport[:count,:2],axis=1)-c['bore_radius_assumed_mm'])<c['bore_band_assumed_mm'])+1
            if len(fixed)<12:raise ValueError('Assumed bore support is empty')
            groups[name]=len(fixed);stream.write('*NSET,NSET=BORE\n')
            for i in range(0,len(fixed),16):stream.write(','.join(map(str,fixed[i:i+16]))+'\n')
            stream.write('*NSET,NSET=NALL,GENERATE\n'+f'1,{count},1\n')
            stream.write('*MATERIAL,NAME=SCREEN\n*ELASTIC\n'+f'{card["young_modulus_GPa"]*1000},0.33\n')
            stream.write('*DENSITY\n'+codec.ccx_field(card['density_g_cm3']*1e-9)+'\n')
            stream.write('*SOLID SECTION,ELSET=ROTOR,MATERIAL=SCREEN\n*BOUNDARY\nBORE,1,3,0\n*STEP\n*STATIC,SOLVER=SPOOLES\n*DLOAD\n')
            stream.write(f'ROTOR,CENTRIF,{(c["rotor_rpm"]*math.pi/30)**2:.17g},0,0,0,0,0,1\n')
            stream.write('*NODE PRINT,NSET=BORE,TOTALS=YES\nRF\n*NODE PRINT,NSET=NALL\nU\n*EL PRINT,ELSET=ROTOR\nS\n*END STEP\n')
    integers,scale=integer_points(transport);maximum_num=0;maximum_den=1;max_delta=0;refused=0;minimum_det=None
    for i,cell in enumerate(quadratic):
        bound=mapping.integer_cell_bound([integers[int(j)] for j in cell])
        if bound is None:refused+=1;continue
        numerator,denominator,delta=bound;refused+=numerator>=denominator
        minimum_det=denominator if minimum_det is None else min(minimum_det,denominator);max_delta=max(max_delta,delta)
        if numerator*maximum_den>maximum_num*denominator:maximum_num,maximum_den=numerator,denominator
        if (i+1)%100000==0:(output/'progress.json').write_text(json.dumps(dict(phase='whole_simplex_Jacobian',cells=i+1,refused=refused))+'\n')
    eta=Q(maximum_num,maximum_den);curvature=Q(3*max_delta,4*scale);distance=maximum_corner_error+curvature
    admitted=not refused and distance<=Q(1,10**9)
    np.savez_compressed(output/'P1/geometry.npz',vertices=transport[:parent_nodes],tetrahedra=linear)
    np.savez_compressed(output/'P2/geometry.npz',vertices=transport,tetrahedra=quadratic)
    for name,form,count in (('P1','C3D4',parent_nodes),('P2','C3D10',len(vertices))):
        record=dict(schema='935-conforming-fea-preparation-v1',formulation=form,nodes=count,elements=len(linear),
                    deck_sha256=sha(output/name/'rotor.inp'),geometry_npz_sha256=sha(output/name/'geometry.npz'),
                    parent_geometry_sha256=c['geometry_sha256'],volume_audit_sha256=sha(audit_path),
                    material_id=c['material_id'],material_cards_sha256=sha(cards),rotor_rpm=c['rotor_rpm'],
                    material_density_tonne_mm3=card['density_g_cm3']*1e-9,clamped_bore_nodes=groups[name],
                    bore_radius_assumed_mm=c['bore_radius_assumed_mm'],bore_band_assumed_mm=c['bore_band_assumed_mm'],
                    poisson_ratio_assumed=.33,source_unit='uncalibrated_scan_unit',solver_units='N_mm_tonne_s_assumed_scale',
                    whole_simplex_positive=not refused,complete_numeric_geometry_transport_bound_native_units=float(distance),
                    numeric_geometry_admitted_for_solver=admitted,mesh_convergence_established=False,scale_verified=False,
                    support_is_measured=False,physical_validation=False,manufacturing_authorized=False)
        (output/name/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    report=dict(status='matched_solver_geometry_prepared' if admitted else 'solver_geometry_refused',linear_nodes=parent_nodes,
                quadratic_nodes=len(vertices),elements=len(linear),whole_simplex_refused_cells=refused,
                exact_maximum_relative_Jacobian_perturbation=str(eta),exact_corner_transport_L1_bound=str(maximum_corner_error),
                exact_curvature_L1_bound=str(curvature),exact_complete_numeric_transport_L1_bound=str(distance),
                numeric_transport_budget_native_units=1e-9,physical_or_machining_tolerance=False,
                source_sha256=sha(__file__),helper_sha256={str(p.relative_to(ROOT)):sha(p) for p in (codec_path,mapping_path)},
                elapsed_s=time.monotonic()-start,mesh_convergence_established=False,physical_validation=False,manufacturing_authorized=False)
    (output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    return admitted


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('new_output',type=Path)
    a=p.parse_args();raise SystemExit(0 if prepare(a.case,a.new_output) else 2)
