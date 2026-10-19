"""Fixed storage preflight, then exec the unchanged697277 packer; no numerical import."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACKER=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/local-refinement-20261017/sources/package.py'
PACKER_SHA='697277ea5c4ccc10cec323f6815409e4d948726f55b52045c17d1be99bfa1a9a'

def run(path,expected):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Fixed pack plan differs')
    plan=json.loads(path.read_text());out=Path(plan['destination'])
    if (plan['source_root']!=str(ROOT) or out!=HERE/'archives' or
        set(plan['archives'])!={'c1-h2-common.zip','c1-h2-rigid.zip','c1-h2-spring.zip'}):raise ValueError('Only fixed H2 delta plan allowed')
    if out.exists() or any(p.is_symlink()for p in [out,*out.parents]):raise ValueError('Fresh regular archive directory required')
    # Both archive staging and the final capsule copy, each with3strict100MB bounds.
    required=2*3*100000000+10*1024**2
    if shutil.disk_usage(out.parent).free<required:raise ValueError('Insufficient free space for two bounded ZIP sets and auxiliary records')
    if hashlib.sha256(PACKER.read_bytes()).hexdigest()!=PACKER_SHA:raise ValueError('Unchanged packer differs')
    out.mkdir()
    os.execv(sys.executable,[sys.executable,'-I','-B',str(PACKER),str(path),expected])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--plan-sha256',required=True);a=p.parse_args();run(a.plan,a.plan_sha256)
