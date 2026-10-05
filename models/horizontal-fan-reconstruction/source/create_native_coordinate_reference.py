#!/usr/bin/env python3
"""Create an independent scale-one point reference from checked native field bundles."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def create(bundle,output):
    receipt=json.loads(bundle.with_suffix('.json').read_text())
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=receipt['field_bundle_sha256']:raise ValueError('Native bundle integrity')
    if output.exists():raise FileExistsError('Preserve coordinate reference')
    fields=np.load(bundle);points=(fields['xyz_mm']+fields['released_displacement_mm'])*.001
    if len(points)!=receipt['boundary_nodes'] or not np.isfinite(points).all():raise ValueError('Native coordinate coverage')
    result={'source_field_sha256':receipt['source_field_sha256'],'field_bundle_sha256':receipt['field_bundle_sha256'],'native_released_points_m':points.tolist()}
    output.write_text(json.dumps(result)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('output',type=Path);a=p.parse_args();create(a.bundle,a.output)
