#!/usr/bin/env python3
"""Isolate castellation by disabling only snapping in a fresh pinned mesh trial."""
import json
from pathlib import Path
from prepare_case import sha


def disable_snap(text):
    before='castellatedMesh true; snap true; addLayers false;'
    if text.count(before)!=1:raise ValueError('Expected unique frozen meshing stages')
    return text.replace(before,'castellatedMesh true; snap false; addLayers false;')


def prepare(parent,output):
    manifest=json.loads((parent/'case-manifest.json').read_text());receipt=json.loads((parent/'run-mesh.json').read_text())
    if receipt['case_manifest_sha256']!=sha(parent/'case-manifest.json') or receipt['solver_launched'] is not False or receipt['native_exit_code']!=0:
        raise ValueError('Completed mesh-only parent required')
    for name,digest in manifest['file_sha256'].items():
        path=parent/name
        if not path.resolve().is_relative_to(parent.resolve()) or sha(path)!=digest:raise ValueError('Changed or escaping parent input')
    new_text=disable_snap((parent/'system/snappyHexMeshDict').read_text())
    output.mkdir(parents=True,exist_ok=False)
    for name in manifest['file_sha256']:
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((parent/name).read_bytes())
    (output/'system/snappyHexMeshDict').write_text(new_text)
    result=manifest|dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(parent/'case-manifest.json'),parent_receipt_sha256=sha(parent/'run-mesh.json'),
                        control_change='Only snap true -> false; all other prepared input bytes identical. Diagnostic only, no solver admission.',solver_admission_granted=False)
    result['file_sha256']={name:sha(output/name) for name in manifest['file_sha256']}
    assert [n for n,h in result['file_sha256'].items() if h!=manifest['file_sha256'][n]]==['system/snappyHexMeshDict']
    (output/'case-manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result
