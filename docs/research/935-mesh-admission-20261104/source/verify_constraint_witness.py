"""Verify geometric change independently of array/import ordering."""
import argparse
import json
from pathlib import Path
import numpy as np
from run_constraint_controls import read_off
from trial_planar_flips import sha, save_json
from trial_masked_isotropic_v2 import triangle_keys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','mask','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists(): raise SystemExit('Existing assessment refused.')
    v,f=read_off(args.before);v2,f2=read_off(args.after)
    protected=np.atleast_1d(np.loadtxt(args.mask,dtype=np.int64))
    original,actual=triangle_keys(v,f),triangle_keys(v2,f2)
    kept=np.isin(original,actual);unprotected=np.ones(len(f),bool);unprotected[protected]=False
    report={'original_faces':len(f),'output_faces':len(f2),
        'original_oriented_triangles_not_exactly_preserved':int((~kept).sum()),
        'protected_oriented_triangles_exact':bool(kept[protected].all()),
        'unprotected_original_triangles_changed':int((~kept&unprotected).sum()),
        'input_hashes':{name:sha(getattr(args,name)) for name in ('before','after','mask')}}
    report['passed']=report['protected_oriented_triangles_exact'] and report['unprotected_original_triangles_changed']>0
    save_json(args.output,report);print(json.dumps(report))
    if not report['passed']: raise SystemExit(1)


if __name__=='__main__':
    main()
