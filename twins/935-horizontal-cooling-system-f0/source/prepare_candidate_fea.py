#!/usr/bin/env python3
"""Prepare a full-rotor PicoGK hexahedral centrifugal pilot for CalculiX."""
import argparse
import json
import math
from pathlib import Path
import sys

import gmsh
import numpy as np

from build_system_twin import positive
from run_reconstruction import ROOT, fresh, save, sha

sys.path.insert(0, str(ROOT / 'twins/reference-917-engine/source'))
from run_scan_conforming_calculix_f36 import largest_face_connected_component

STUDY = Path(__file__).resolve().parents[1]


def prepare(case_path, output):
    case = json.loads(Path(case_path).read_text())
    if case.get('purpose') != 'hypothesis_screen' or case.get('scale_verified') is not False:
        raise ValueError('Explicit uncalibrated structural hypothesis required')
    source = Path(case['grid_path'])
    if sha(source) != case['grid_sha256']:
        raise ValueError('PicoGK grid hash mismatch')
    grid = json.loads(source.read_text())
    if grid['schema'] != '935-signed-distance-hexa-grid-v1' or grid['input_sha256'] != case['rotor_stl_sha256']:
        raise ValueError('Grid must reference the pinned rotor')
    size, bore, rpm = positive(grid['pitch_mm']), positive(case['bore_radius_mm']), positive(case['rotor_rpm'])
    raw = grid['cells']
    if not raw or len(raw) > case['maximum_elements'] or any(len(c) != 3 or any(type(x) is not int for x in c) for c in raw):
        raise ValueError('Bounded integer cell indices required')
    occupied = {tuple(c) for c in raw}
    _, count = largest_face_connected_component(occupied)
    if count != 1 or len(occupied) != len(raw):
        raise ValueError('Grid is disconnected or has duplicate cells; no component is discarded')
    volume = len(raw) * size ** 3
    volume_error = abs(volume - positive(case['expected_volume_mm3'])) / case['expected_volume_mm3']
    if volume_error > positive(case['maximum_volume_relative_error']):
        raise ValueError('Voxel geometry exceeds the allowed volume discrepancy')
    centers = (np.asarray(raw) + .5) * size
    if np.any(np.linalg.norm(centers[:,:2],axis=1) < bore - 1e-6):
        raise ValueError('The functional central bore was filled')
    corners = np.asarray(raw)[:,None,:] + np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
    keys, indices = np.unique(corners.reshape(-1,3),axis=0,return_inverse=True)
    tags = np.arange(1,len(keys)+1); xyz = keys * size
    element_tags = np.arange(1,len(raw)+1); connectivity = indices.reshape(-1,8)+1
    cards_path = STUDY / 'vast-omniverse-screen/materials.json'
    card = next(c for c in json.loads(cards_path.read_text())['materials'] if c['id'] == case['material_id'])
    out = fresh(output); save(out / 'case.json', case)
    gmsh.initialize()
    try:
        gmsh.model.add('935RotorHypothesis')
        entity = gmsh.model.addDiscreteEntity(3,1)
        gmsh.model.mesh.addNodes(3,entity,tags,xyz.reshape(-1))
        gmsh.model.mesh.addElementsByType(entity,5,element_tags,connectivity.reshape(-1))
        minimum_quality = float(np.min(gmsh.model.mesh.getElementQualities(element_tags, 'minSJ')))
        if minimum_quality <= 0:
            raise ValueError('Nonpositive hexahedron Jacobian')
        fixed = tags[np.abs(np.linalg.norm(xyz[:,:2],axis=1) - bore) < positive(case['bore_selection_tolerance_mm'])]
        if len(fixed) < 12:
            raise ValueError('Bore clamp cannot be identified on the analytic surface')
        gmsh.write(str(out / 'rotor.msh'))
        deck = ['*HEADING','935 scan-based rotor hypothesis; artificial cup; rigid bore clamp; N-mm-tonne-s', '*NODE']
        deck += [f'{int(tag)},{x:.12g},{y:.12g},{z:.12g}' for tag,(x,y,z) in zip(tags,xyz)]
        deck += ['*ELEMENT,TYPE=C3D8,ELSET=ROTOR']
        deck += [','.join(str(int(x)) for x in [tag,*nodes]) for tag,nodes in zip(element_tags,connectivity)]
        deck += ['*NSET,NSET=BORE'] + [','.join(str(int(x)) for x in fixed[i:i+12]) for i in range(0,len(fixed),12)]
        deck += ['*NSET,NSET=NALL,GENERATE',f'1,{len(tags)},1']
        deck += ['*MATERIAL,NAME=SCREEN','*ELASTIC',f'{card["young_modulus_GPa"]*1000:.12g},0.33',
                 '*DENSITY',f'{card["density_g_cm3"]*1e-9:.12g}',
                 '*SOLID SECTION,ELSET=ROTOR,MATERIAL=SCREEN','*BOUNDARY','BORE,1,3,0',
                 '*STEP','*STATIC','*DLOAD',f'ROTOR,CENTRIF,{(rpm*math.pi/30)**2:.12g},0,0,0,0,0,1',
                 '*NODE PRINT,NSET=BORE,TOTALS=YES','RF','*NODE PRINT,NSET=NALL','U','*EL PRINT,ELSET=ROTOR','S',
                 '*NODE FILE','U,RF','*EL FILE','S','*END STEP']
        (out / 'rotor.inp').write_text('\n'.join(deck)+'\n')
        if sha(source) != case['grid_sha256']:
            raise ValueError('Input changed during meshing')
        save(out / 'receipt.json', {'status':'full_rotor_centrifugal_pilot_prepared_not_solved',
            'geometry_sha256':case['rotor_stl_sha256'], 'grid_sha256':sha(source), 'material_cards_sha256':sha(cards_path), 'case_sha256':sha(case_path),
            'Gmsh_version':gmsh.__version__, 'material_id':card['id'], 'units':'N_mm_tonne_s_MPa',
            'nodes':len(tags), 'C3D8_elements':len(element_tags), 'minimum_scaled_Jacobian':minimum_quality,
            'clamped_bore_nodes':len(fixed), 'grid_volume_mm3':volume, 'CAD_volume_relative_error':volume_error,
            'bore_clamp_is_assumption':True, 'mesh_convergence_established':False,
            'allowable_speed_or_fatigue_validated':False, 'manufacturing_authorized':False,
            'deck_sha256':sha(out / 'rotor.inp')})
    finally:
        gmsh.finalize()
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(prepare(args.case,args.output))
