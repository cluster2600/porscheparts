#!/usr/bin/env python3
"""Compose the observed shaft frame into the observed support frame."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''): h.update(block)
    return h.hexdigest()


def rigid(matrix):
    m=np.asarray(matrix,dtype=float)
    if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1],atol=1e-10,rtol=0):
        raise ValueError('invalid homogeneous transform')
    r=m[:3,:3]
    if not np.allclose(r.T@r,np.eye(3),atol=1e-9,rtol=0) or not np.isclose(np.linalg.det(r),1,atol=1e-9,rtol=0):
        raise ValueError('non-rigid or reflected transform')
    return m


def compose(shaft_to_source, source_to_support):
    return rigid(rigid(source_to_support) @ rigid(shaft_to_source))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('shaft_report',type=Path); p.add_argument('support_report',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
    work=Path(__file__).resolve().parents[4]/'work'
    if a.output.exists() or not a.output.resolve().is_relative_to(work.resolve()):
        raise SystemExit('use fresh private work output')
    expected=('2cb88c11bb02f0d7ee5ea481a4887cd75d0cc48a718f22cc89a95ca8f8290e57','cb150f62fe4dbb683c06632a43245a9277e12e974c2925db123c01d3f1d25c67')
    if (digest(a.shaft_report),digest(a.support_report))!=expected: raise ValueError('report hash mismatch')
    shaft=json.loads(a.shaft_report.read_text()); support=json.loads(a.support_report.read_text())
    if shaft['source_sha256']!=support['source_sha256'] or shaft['scale_verified'] or support['scale_verified']:
        raise ValueError('source mismatch or unexpected scale status')
    if not np.allclose(rigid(support['transform_patch_to_candidate_frame']),np.eye(4),atol=1e-10,rtol=0):
        raise ValueError('support CAD frame is not the assumed normalized frame')
    forward=rigid(shaft['transform_source_to_candidate_shaft']); inverse=rigid(shaft['transform_candidate_shaft_to_source'])
    if not np.allclose(forward@inverse,np.eye(4),atol=1e-9,rtol=0): raise ValueError('shaft inverse mismatch')
    transform=compose(inverse,support['source_pose_transform']['transform_source_to_normalized'])
    result={'status':'same_scan_coordinate_mapping_not_fit_validation','shaft_report_sha256':expected[0],'support_report_sha256':expected[1],
        'source_sha256':shaft['source_sha256'],'shaft_cad_to_support_cad':transform.tolist(),'support_cad_to_shaft_cad':np.linalg.inv(transform).tolist(),
        'assumed_mm_per_source_unit':1.0,'scale_verified':False,'physical_registration_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n'); print('Private same-scan CAD-frame mapping created; physical fit remains unverified')

if __name__=='__main__': main()
