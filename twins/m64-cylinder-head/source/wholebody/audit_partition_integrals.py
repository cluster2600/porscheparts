#!/usr/bin/env python3
"""Two adaptive volume integrations for the exact coplanar-partition trial.

Keeps the failed default-integral receipt; never widens its 1e-10 limit.
Convergence of these numerical integrals is not surface equivalence.
"""
import argparse
import json
import math
from pathlib import Path
import signal
import time

from run_local_surface_trial import BODY_SHA,native

CANDIDATE='2c7483776c8ca618e122f4c5c0d08069cdd45005ebb5d975c0618f34f383f94a'


def integral_gate(rows):
    if len(rows)!=8 or {(r['method'],r['epsilon'],r['shape']) for r in rows}!={
        (m,e,s) for m in ('Gauss','GaussKronrod') for e in (1e-10,1e-12) for s in ('source','candidate')}:
        return False
    if any(not all(math.isfinite(r[k]) for k in ('volume','estimated_relative_error'))
           or r['volume']<=0 or not 0<=r['estimated_relative_error']<=1e-10 for r in rows): return False
    values=[r['volume'] for r in rows]
    return max(values)/min(values)-1<=1e-10


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopoDS import TopoDS_Shape
    pins={args.input:BODY_SHA,args.candidate:CANDIDATE,Path(__file__):native.sha256(__file__)}
    if args.output.exists() or OCP.__version__!='7.9.3.1' or any(p.is_symlink() or native.sha256(p)!=s for p,s in pins.items()):
        raise ValueError('fresh_receipt_and_exact_inputs_required')
    start=time.monotonic(); shapes={}
    for label,path in [('source',args.input),('candidate',args.candidate)]:
        shape=TopoDS_Shape()
        if not BRepTools.Read_s(shape,str(path),BRep_Builder()): raise ValueError('native_read_failed')
        shapes[label]=shape
    receipt={'schema':'m64-partition-adaptive-integrals/v1','status':'incomplete',
        'source_sha256':pins[Path(__file__)],'input_sha256':BODY_SHA,'candidate_sha256':CANDIDATE,
        'OCP_version':OCP.__version__,'relative_gate':1e-10,'results':[],
        'same_kernel_not_independent_CAD_engines':True,'continuous_deviation_certified':False,
        'old_failed_receipt_overwritten':False,'manufacturing_authorized':False}
    try:
        for method in ('Gauss','GaussKronrod'):
            for epsilon in (1e-10,1e-12):
                for label,shape in shapes.items():
                    props=GProp_GProps(); started=time.monotonic()
                    if method=='Gauss': error=BRepGProp.VolumeProperties_s(shape,props,epsilon,True,False)
                    else: error=BRepGProp.VolumePropertiesGK_s(shape,props,epsilon,True,True,False,False,False)
                    receipt['results'].append({'method':method,'epsilon':epsilon,'shape':label,
                        'volume':props.Mass(),'estimated_relative_error':error,'elapsed_seconds':time.monotonic()-started})
                    native.save(args.output,receipt)
        receipt['passed']=integral_gate(receipt['results']); receipt['status']='completed'
    except Exception as exc:
        receipt.update(status='failed',error_type=type(exc).__name__,error=str(exc),passed=False)
    finally:
        receipt['inputs_unchanged']=all(native.sha256(p)==s for p,s in pins.items())
        receipt['elapsed_seconds']=time.monotonic()-start
        native.save(args.output,receipt)
    print(json.dumps({k:receipt[k] for k in ('status','passed','elapsed_seconds')}))
    return 0 if receipt['passed'] and receipt['inputs_unchanged'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','candidate','output'): parser.add_argument('--'+name,type=Path,required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
