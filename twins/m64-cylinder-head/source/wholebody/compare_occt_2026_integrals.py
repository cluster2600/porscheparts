#!/usr/bin/env python3
"""Repeat the old numerical volume gate in isolated OCCT versions; no repair."""
import argparse
import json
from pathlib import Path
import time

from audit_partition_integrals import BODY_SHA, CANDIDATE, integral_gate, native


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopoDS import TopoDS_Shape
    pins={args.input:BODY_SHA,args.candidate:CANDIDATE,Path(__file__):native.sha256(__file__)}
    if (args.output.exists() or OCP.__version__ not in ('7.9.3.1','8.0.1.0')
            or any(p.is_symlink() or native.sha256(p)!=s for p,s in pins.items())):
        raise ValueError('exact_inputs_fresh_receipt_and_supported_runtime_required')
    started=time.monotonic()
    report={'schema':'m64-occt-2026-integral-comparison/v1','status':'incomplete',
        'OCP_version':OCP.__version__,'source_sha256':pins[Path(__file__)],
        'input_sha256':BODY_SHA,'candidate_sha256':CANDIDATE,'relative_gate':1e-10,
        'results':[],'default_integrals':{},'same_kernel_family':True,
        'native_BRep_replaced':False,'manufacturing_authorized':False}
    native.save(args.output,report)
    try:
        for label,path in (('source',args.input),('candidate',args.candidate)):
            shape=TopoDS_Shape()
            if not BRepTools.Read_s(shape,str(path),BRep_Builder()): raise ValueError('native_read_failed')
            props=GProp_GProps(); BRepGProp.VolumeProperties_s(shape,props)
            report['default_integrals'][label]=props.Mass()
            for method in ('Gauss','GaussKronrod'):
                for epsilon in (1e-10,1e-12):
                    props=GProp_GProps(); begin=time.monotonic()
                    if method=='Gauss': error=BRepGProp.VolumeProperties_s(shape,props,epsilon,True,False)
                    else: error=BRepGProp.VolumePropertiesGK_s(shape,props,epsilon,True,True,False,False,False)
                    report['results'].append(dict(shape=label,method=method,epsilon=epsilon,
                        volume=props.Mass(),estimated_relative_error=error,elapsed_seconds=time.monotonic()-begin))
                    native.save(args.output,report)
        report.update(status='completed',passed=integral_gate(report['results']))
    except Exception as exc: report.update(status='failed',error_type=type(exc).__name__,error=str(exc),passed=False)
    finally:
        report['inputs_and_source_unchanged']=all(native.sha256(p)==s for p,s in pins.items())
        report['elapsed_seconds']=time.monotonic()-started; native.save(args.output,report)
    print(json.dumps(report))
    return 0 if report['passed'] and report['inputs_and_source_unchanged'] else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','candidate','output'): p.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
