#!/usr/bin/env python3
"""Prepare a physical-wall mesh trial from an admitted structured background."""
import json
from pathlib import Path
import prepare_case as base


def snappy_dictionary(text):
    before='levels ((1e15 1));'
    if text.count(before)!=1:raise ValueError('Expected one global background refinement')
    # The structured background already resolves the interface; retain surface and gap refinement.
    return text.replace(before,'levels ((1e15 0));')


def prepare(parent,background,audit_path,output):
    prior=json.loads((parent/'case-manifest.json').read_text());bg=json.loads((background/'manifest.json').read_text())
    receipt=json.loads((background/'report.json').read_text());audit=json.loads(audit_path.read_text())
    if not receipt['mesh_gate_passed'] or receipt['manifest_sha256']!=base.sha(background/'manifest.json') or audit['receipt_sha256']!=base.sha(background/'report.json') or not audit['mesh_gate_passed'] or audit['max_normal_frame_speed_m_s']>=1e-8:
        raise ValueError('Admitted native background and tangent interface required')
    for name,digest in receipt['output_sha256'].items():
        p=background/name
        if not p.resolve().is_relative_to(background.resolve()) or base.sha(p)!=digest:raise ValueError('Changed or escaping native background input')
    surface=parent/'constant/triSurface/domain.stl'
    if bg['surface']['sha256']!=prior['surface']['sha256'] or base.sha(surface)!=prior['surface']['sha256']:raise ValueError('Background and parent surfaces differ')
    files=base.case_files(prior['surface'],'medium',100000,1,1.2,800)
    files['system/blockMeshDict']=(background/'system/blockMeshDict').read_text()
    files['system/snappyHexMeshDict']=snappy_dictionary(files['system/snappyHexMeshDict'])
    files['system/topoSetDict']=base.header('topoSetDict')+'actions ();\n'
    control=files['system/controlDict']
    if control.count('writePrecision 12;')!=1:raise ValueError('Expected frozen precision entry')
    files['system/controlDict']=control.replace('writePrecision 12;','writePrecision 16;')
    output.mkdir(parents=True,exist_ok=False)
    for name,content in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    target=output/'constant/triSurface/domain.stl';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(surface.read_bytes())
    assert base.sha(target)==prior['surface']['sha256']
    manifest=dict(schema='bionic-turbo-compressible-mrf/v1',source_sha256=base.sha(Path(__file__)),canonical_source_sha256=base.sha(Path(base.__file__)),image=base.IMAGE,solver='rhoSimpleFoam',surface=prior['surface'],parent_manifest_sha256=base.sha(parent/'case-manifest.json'),background_manifest_sha256=base.sha(background/'manifest.json'),background_audit_sha256=base.sha(audit_path),
                  mesh_only=True,stationary_equilibrium_verified=False,wall_layers_present=False,performance_ranking_authorized=False,solver_admission_granted=False,
                  refinement='Global level zero on already structured background; unchanged level-one physical surfaces and gapLevel (4 1 3). No face projection or repair after native meshing.',
                  rotor_zone=dict(construction='Direct block zones inherited by snappyHexMesh, no cell-centre reselection',profile_nodes_mm=bg['simplified_profile_nodes_mm']),
                  file_sha256={name:base.sha(output/name) for name in files}|{'constant/triSurface/domain.stl':base.sha(target)})
    (output/'case-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
