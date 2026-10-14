#!/usr/bin/env python3
"""Measure native polygonal MRF interfaces without granting a solver admission."""
import json
from pathlib import Path
import re
import sys
import numpy as np
from audit_diagnostic import ascii_list
from run_case import ascii_faces,inspect_mesh
from prepare_case import sha

GEOMETRY_SOURCE='https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshTools.C'


from audit_frame_interface import face_geometry


def cell_flags(owner,neighbour,zone):
    if not len(owner) or len(neighbour)>len(owner) or np.any(owner<0) or np.any(neighbour<0):
        raise ValueError('Invalid native cell addressing')
    count=int(max(owner.max(),neighbour.max(initial=-1)))+1
    if not len(zone) or zone.min()<0 or zone.max()>=count or len(np.unique(zone))!=len(zone):
        raise ValueError('Invalid rotor zone')
    result=np.zeros(count,dtype=bool);result[zone]=True
    return result


def audit(case):
    manifest=json.loads((case/'case-manifest.json').read_text())
    receipt=json.loads((case/'run-mesh.json').read_text())
    if receipt['case_manifest_sha256']!=sha(case/'case-manifest.json'):
        raise ValueError('Mesh receipt does not match current inputs')
    completed={x['name'] for x in receipt['stages'] if x['exit_code']==0}
    if 'snappyHexMesh' not in completed:
        raise ValueError('A completed native surface meshing stage is required')
    for name,digest in manifest['file_sha256'].items():
        if not (case/name).resolve().is_relative_to(case.resolve()) or sha(case/name)!=digest:
            raise ValueError('Changed or escaping prepared input: '+name)
    for stage in receipt['stages']:
        if sha(case/stage['log'])!=stage['sha256']:
            raise ValueError('Changed native stage log')
    inputs={}
    def read(name):
        p=case/'constant/polyMesh'/name;inputs[name]=sha(p);return p.read_text()
    owner=ascii_list(read('owner')).astype(np.int64)
    neighbour=ascii_list(read('neighbour')).astype(np.int64)
    points=ascii_list(read('points'),True)
    match=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',read('cellZones'),re.S)
    if not match:raise ValueError('Missing rotor zone')
    zone=np.fromstring(match[2],sep=' ',dtype=np.int64)
    if len(zone)!=int(match[1]):
        raise ValueError('Invalid rotor zone')
    rotating=cell_flags(owner,neighbour,zone)
    outgoing=rotating[owner[:len(neighbour)]]
    selected=set(np.flatnonzero(outgoing^rotating[neighbour]))
    mrf=(case/'constant/MRFProperties').read_text()
    for name,expected in (('origin',[0,0,0]),('axis',[0,0,1])):
        value=re.search(name+r'\s*\(([^()]*)\)',mrf)
        if not value or not np.array_equal(np.fromstring(value[1],sep=' '),expected):
            raise ValueError('Only rotation about the declared Z axis is supported')
    omega=float(re.search(r'omega\s+constant\s+([^;]+)',mrf)[1])
    if not np.isfinite(omega):raise ValueError('Finite rotation required')
    result=[]
    for i,face in enumerate(ascii_faces(read('faces'))):
        if i in selected:
            centre,area=face_geometry(points[list(face)])
            q=float(np.dot(np.cross([0,0,omega],centre),area));normal=q/np.linalg.norm(area)
            result.append((abs(normal),q,centre,i,float(np.linalg.norm(area))))
    if not selected or len(result)!=len(selected):raise ValueError('Incomplete or absent internal frame interface')
    worst=sorted(result,key=lambda x:x[0],reverse=True)[:20]
    try:
        topology=inspect_mesh(case,manifest['surface']['boundary_topology'])
    except ValueError as error:
        topology={'status':'rejected','reason':str(error)}
    return {'source_sha256':sha(Path(__file__)),'case_manifest_sha256':sha(case/'case-manifest.json'),
        'polygon_source_sha256':sha(Path(__file__).with_name('audit_frame_interface.py')),'geometry_formula_reference':GEOMETRY_SOURCE,'geometry_reference_sha256':'db2868dc5ccb66f8e3e8c4b919afb8abf8bb3b0fc290c704f9ad4c65b645a712','input_mesh_sha256':inputs,
        'native_mesh_gate_passed':receipt.get('mesh_gate_passed',False),'native_error':receipt.get('error'),
        'topology':topology,'rotating_cells':len(zone),'internal_frame_interface_faces':len(result),
        'gross_geometric_frame_flux_m3_s':sum(abs(x[1]) for x in result),
        'net_outward_geometric_frame_flux_m3_s':sum(x[1]*(1 if outgoing[x[3]] else -1) for x in result),
        'max_normal_frame_speed_m_s':worst[0][0],
        'worst_faces':[{'face':x[3],'normal_frame_speed_m_s':x[0],'centre_m':x[2].tolist(),'area_m2':x[4]} for x in worst],
        'performance_ranking_authorized':False,'solver_admission_granted':False,
        'interpretation':'Geometric rotation through the frame interface, not physical leakage or performance. Native mesh admission and stationary equilibrium remain separate requirements.'}


if __name__=='__main__':
    result=audit(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
