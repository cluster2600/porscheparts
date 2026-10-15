#!/usr/bin/env python3
"""Prepare a mesh-only trial with a snapped internal cylindrical MRF face zone."""
import json
from pathlib import Path
import sys

import prepare_case as base
from run_cartesian_pilot import verify


def zone_dictionary(text):
    replacements={
        'geometry {domain {': 'geometry {mrfInterface {type searchableCylinder; point1 (0 0 -.004); point2 (0 0 .033); radius .038;}\ndomain {',
        'refinementSurfaces {domain {': 'refinementSurfaces {mrfInterface {level (1 1); faceZone mrfInterface; cellZone rotorZone; cellZoneInside inside; faceType internal;}\ndomain {',
        'allowFreeStandingZoneFaces true;': 'allowFreeStandingZoneFaces false;'}
    for before,after in replacements.items():
        if text.count(before)!=1:
            raise ValueError('Expected unique frozen dictionary entry: '+before)
        text=text.replace(before,after)
    return text


def prepare(parent,output):
    verify(parent)
    prior=json.loads((parent/'case-manifest.json').read_text())
    surface=parent/'constant/triSurface/domain.stl'
    if base.sha(surface)!=prior['surface']['sha256']:
        raise ValueError('Parent surface hash mismatch')
    files=base.case_files(prior['surface'],'medium',100000,1,1.2,800)
    files['system/snappyHexMeshDict']=zone_dictionary(files['system/snappyHexMeshDict'])
    files['system/topoSetDict']=base.header('topoSetDict')+'actions ();\n'
    output.mkdir(parents=True,exist_ok=False)
    for name,content in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    target=output/'constant/triSurface/domain.stl';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(surface.read_bytes())
    if base.sha(target)!=prior['surface']['sha256']:
        raise ValueError('Copied surface changed')
    manifest={'schema':'bionic-turbo-compressible-mrf/v1','status':'mesh_only_trial_not_solver_ready',
        'image':base.IMAGE,'solver':'rhoSimpleFoam','source_sha256':base.sha(Path(__file__)),
        'parent_manifest_sha256':base.sha(parent/'case-manifest.json'),'surface':prior['surface'],
        'mesh_level':'medium','background_cell_m':base.LEVELS['medium'],'seed_m':[.015,0,.040],
        'rotor_zone':{'radius_m':.038,'z_min_m':-.004,'z_max_m':.033,'construction':'snappyHexMesh internal faceZone; no cell-centre reselection'},
        'file_sha256':{name:base.sha(output/name) for name in files}|{'constant/triSurface/domain.stl':base.sha(target)},
        'canonical_source_sha256':base.sha(Path(base.__file__)),
        'mesh_only':True,'stationary_equilibrium_verified':False,'surface_distance_error_quantified':False,
        'actual_gap_cell_count_verified':False,'wall_layers_present':False,'mesh_independence_established':False,
        'performance_ranking_authorized':False,'engineering_validated':False,'manufacturing_authorized':False,
        'limitations':['Mesh trial only: no solver launch before independent interface, geometry and equilibrium checks.',
            'Snapping a cylinder does not prove face tangency; measure the resulting native faces.',
            'Source surfaces are byte-identical; mesh approximation and gaps require fresh inspection.'],
        'references':['https://doc.openfoam.com/2306/tools/pre-processing/mesh/generation/snappyhexmesh/searchableObjects/searchablecylinder/',
            'https://api.openfoam.com/2406/surfaceZonesInfo_8C_source.html']}
    (output/'case-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    result=prepare(*map(Path,sys.argv[1:]))
    print(json.dumps({'status':result['status'],'surface_sha256':result['surface']['sha256']}))
