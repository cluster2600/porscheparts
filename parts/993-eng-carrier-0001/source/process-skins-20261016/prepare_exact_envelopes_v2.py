"""Freeze legacy chains and original positive-prism roofs with a fresh input receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

import numpy as np
import pyslm
import pyslm.support
import trimesh

from prepare_exact_envelopes import prepare as legacy_prepare
from region_checkpoints import runtime_identity

SOURCE=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_identity(input_path,expected_sha256=None,identity_receipt=None):
    if (expected_sha256 is None)==(identity_receipt is None):raise ValueError('Choose exactly one input identity')
    if identity_receipt is not None:
        expected_sha256=json.loads(Path(identity_receipt).read_text()).get('candidate_STL_sha256')
    if not isinstance(expected_sha256,str) or re.fullmatch('[0-9a-f]{64}',expected_sha256) is None:
        raise ValueError('Malformed candidate_STL_sha256 identity')
    if sha(input_path)!=expected_sha256:raise ValueError('Input SHA-256 mismatch')
    return expected_sha256


def export_original_roofs(part_path,source_indices,overhang_angle,output):
    output=Path(output)
    with np.load(part_path,allow_pickle=False) as p:
        part=pyslm.Part('carrier');part.setGeometry(trimesh.Trimesh(p['vertices'],p['faces'],process=False),fixGeometry=False,mergeVertices=False)
    sources=pyslm.support.utils.getOverhangMesh(part,overhang_angle,True)
    roofs={}
    for index in sorted(set(source_indices)):
        mesh=sources[index];name=f'source-{index:03d}-roofs.npz'
        np.savez_compressed(output/name,vertices=np.asarray(mesh.vertices,dtype=np.float64),
            faces=np.asarray(mesh.faces,dtype=np.int64),source_face_ids=np.arange(len(mesh.faces),dtype=np.int64))
        roofs[index]=dict(roofs=name,roofs_sha256=sha(output/name),positive_prism_roof_faces=len(mesh.faces),
            roof_source='Original getOverhangMesh component, before chain-only horizontal reduction; source_face_ids are its exact local face indices.')
    return roofs


def prepare(input_path,output,expected_sha256=None,identity_receipt=None,reduce_horizontal=False,unreduced_sources=()):
    expected_sha256=resolve_identity(input_path,expected_sha256,identity_receipt)
    output=Path(output).resolve();input_path=Path(input_path).resolve()
    frozen={str(p):sha(p) for p in [Path(__file__).resolve(),SOURCE/'prepare_exact_envelopes.py',SOURCE/'region_checkpoints.py']}
    if identity_receipt is not None:frozen[str(Path(identity_receipt).resolve())]=sha(identity_receipt)
    runtime_before=runtime_identity()
    legacy=legacy_prepare(input_path,output,expected_sha256,reduce_horizontal,unreduced_sources)
    roofs=export_original_roofs(output/'part.npz',[row['source_index'] for row in legacy['regions']],legacy['parameters']['overhang_angle_degrees'],output)
    report=dict(legacy,schema='carrier-exact-envelope-inputs-2',legacy_inputs='inputs.json',legacy_inputs_sha256=sha(output/'inputs.json'),
        regions=[dict(row,**roofs[row['source_index']]) for row in legacy['regions']])
    runtime_after=runtime_identity()
    if runtime_before!=runtime_after or sha(input_path)!=expected_sha256 or any(sha(p)!=h for p,h in frozen.items()):
        raise ValueError('Preparation input, source, receipt or runtime changed')
    for i,path in enumerate(frozen):shutil.copy2(path,output/'source'/f'v2-{i:02d}-{Path(path).name}')
    if identity_receipt is not None:
        shutil.copy2(identity_receipt,output/'input-identity.json')
        report['input_identity_receipt']=dict(receipt='input-identity.json',receipt_sha256=sha(output/'input-identity.json'))
    (output/'inputs-v2.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    receipt=dict(status='positive_roofs_and_legacy_inputs_frozen_no_envelope_admission',input_sha256=expected_sha256,
        output_manifest='inputs-v2.json',output_manifest_sha256=sha(output/'inputs-v2.json'),
        runtime_before=runtime_before,runtime_after=runtime_after,source_and_identity_sha256=frozen,
        identities_unchanged=True,positive_roof_source='original_overhang_components_without_simplification')
    (output/'preparation-v2.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    identity=parser.add_mutually_exclusive_group(required=True);identity.add_argument('--sha256');identity.add_argument('--identity-receipt',type=Path)
    parser.add_argument('--reduce-horizontal',action='store_true');parser.add_argument('--unreduced-source',type=int,action='append',default=[])
    args=parser.parse_args();result=prepare(args.input,args.output,args.sha256,args.identity_receipt,args.reduce_horizontal,args.unreduced_source)
    print(json.dumps(dict(expected_regions=result['expected_regions'],manifest='inputs-v2.json')))
