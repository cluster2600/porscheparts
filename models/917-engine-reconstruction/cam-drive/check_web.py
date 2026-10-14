#!/usr/bin/env python3
"""Independent containment check: bionic webs must stay inside their dense controls."""
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
import trimesh
from reconstruct import save, sha256


def run(directory):
    checks=[]
    for teeth in (27,48,54):
        bionic=directory/f'drive_{teeth}_2_5.stl';dense=directory/f'drive_{teeth}_dense.stl'
        a,aa=study.prior.inspect(bionic,allow_exact_zero=True);b,bb=study.prior.inspect(dense,allow_exact_zero=True)
        if not aa['passed'] or not bb['passed']:raise ValueError('Invalid containment input')
        extra=trimesh.boolean.difference([a,b],engine='manifold',check_volume=True)
        volume=float(extra.volume)
        if not math.isfinite(volume) or volume<0:raise ValueError('Invalid Boolean result')
        checks.append({'teeth':teeth,'bionic_sha256':sha256(bionic),'dense_sha256':sha256(dense),
                       'outside_dense_mm3':volume,'outside_bounds_mm':extra.bounds.tolist() if len(extra.faces) else None,
                       'outside_radial_bounds_mm':([min(math.hypot(v[1],v[2]) for v in extra.vertices),max(math.hypot(v[1],v[2]) for v in extra.vertices)] if len(extra.faces) else None),
                       'passed':volume==0,'method':'Manifold_float_triangle_boolean_not_exact_BRep'})
    save(directory.parent/'web-envelope-checks.json',checks)
    if not all(r['passed'] for r in checks):raise ValueError('Bionic web protrudes outside dense control')
    return checks


if __name__=='__main__':print(json.dumps(run(Path(sys.argv[1])),indent=2))
