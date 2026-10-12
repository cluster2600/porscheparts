#!/usr/bin/env python3
"""Prepare a local MRF termination on the independently verified rear stator plane."""
import json
import math
from pathlib import Path
import re
import profile_mrf_witness as mesh_builder
import static_mrf_witness as witness
from prepare_case import header,sha


def split_rear_wall(text,sectors):
    marker='boundary (walls {type wall; faces ('
    if text.count(marker)!=1 or not text.endswith(');});\n'):
        raise ValueError('Unexpected frozen mesh builder format')
    prefix,body=text.split(marker);body=body[:-6]
    matches=list(re.finditer(r'\((\d+ \d+ \d+ \d+)\)',body))
    if not matches or re.sub(r'\((\d+ \d+ \d+ \d+)\)','',body).strip():
        raise ValueError('Complete quadrilateral wall list required')
    rear=[];other=[]
    for match in matches:
        face=list(map(int,match[1].split()))
        (rear if max(face)<3*sectors else other).append('('+match[1]+')')
    if len(rear)!=2*sectors or not other:
        raise ValueError('Expected complete two-shell rear plane')
    return prefix+'boundary (stator {type wall; faces ('+' '.join(rear)+');} walls {type wall; faces ('+' '.join(other)+');});\n'


def prepare(parent,case,geometry_path,omega):
    report=json.loads(geometry_path.read_text())
    if report['schema']!='bionic-turbo-rear-interface/v1' or report['source_sha256']!=sha(Path(__file__).with_name('audit_rear_interface.py')) or report['geometric_interface_candidate_verified'] is not True:
        raise ValueError('Frozen verified rear geometry required')
    parent_info=json.loads((parent/'case-manifest.json').read_text())['surface']
    if report['variants']['baseline']['surface_sha256']!=parent_info['sha256']:
        raise ValueError('Parent geometry differs from the verified termination')
    spec=report['profile'];sectors=spec['sectors']
    nodes=[p for p in spec['nodes_z_radius_mm'] if -3.75<=p[0]<=-3.0]
    if sectors!=128 or len(nodes)!=7 or nodes[0]!=[-3.75,32.] or nodes[-1][0]!=-3:
        raise ValueError('Complete local rear profile required')
    width=spec['retained_radial_clearance_mm']/2
    for variant in report['variants'].values():
        a=variant['annulus']
        if not a['complete_angular_coverage'] or not a['annulus_inner_radius_mm']<(32-width)*math.cos(math.pi/sectors)<32+width<a['annulus_outer_radius_mm']:
            raise ValueError('Local rear wall not covered by the exact planar annulus')
    text=split_rear_wall(mesh_builder.mesh_text(nodes,width,sectors),sectors)
    manifest=witness.prepare(parent,case,omega)
    (case/'system/blockMeshDict').write_text(text)
    (case/'system/topoSetDict').write_text(header('topoSetDict')+'actions ();\n')
    path=case/'system/controlDict';content=path.read_text()
    if content.count('writePrecision 12;')!=1:raise ValueError('Expected frozen write precision')
    path.write_text(content.replace('writePrecision 12;','writePrecision 16;'))
    path=case/'constant/MRFProperties';content=path.read_text()
    if content.count('nonRotatingPatches (walls);')!=1:raise ValueError('Expected frozen fixed walls')
    path.write_text(content.replace('nonRotatingPatches (walls);','nonRotatingPatches (walls stator);'))
    for name,kind in (('U','noSlip'),('p','zeroGradient'),('T','zeroGradient')):
        path=case/'0'/name;content=path.read_text();marker='walls {type '+kind+';}'
        if content.count(marker)!=1:raise ValueError('Expected frozen field wall')
        path.write_text(content.replace(marker,marker+' stator {type '+kind+';}'))
    manifest['file_sha256']={name:sha(case/name) for name in manifest['file_sha256']}
    cells=2*sectors*(len(nodes)-1)
    manifest['rear_witness']=dict(source_sha256=sha(Path(__file__)),mesh_builder_source_sha256=sha(Path(mesh_builder.__file__)),
        geometry_report_sha256=sha(geometry_path),nodes_z_radius_mm=nodes,sectors=sectors,shell_half_width_mm=width,
        expected_cells=cells,expected_rotating_cells=cells//2,expected_interface_faces=cells//2,expected_stator_faces=2*sectors,
        stator_plane_z_mm=-3.75,native_write_precision=16,
        limitation='Rear wall is exactly covered by both source stator surfaces. Remaining walls are synthetic truncations; rotor, ports and complete turbo volume mesh are absent.')
    (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
