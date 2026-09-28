#!/usr/bin/env python3
"""Localize Gauss/Gauss-Kronrod discrepancies with ONE shared flux origin.

Per-face signed fluxes are not enclosed volumes. Their sum is checked on an
analytic translated box before the exact head is inspected. No CAD mutation.
"""
import argparse
import json
import math
from pathlib import Path
import time
from run_local_surface_trial import BODY_SHA,native


def contributions(shape,origin,epsilon):
    from OCP.BRepGProp import BRepGProp_Face,BRepGProp_Domain,BRepGProp_Vinert,BRepGProp_VinertGK
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    explorer=TopExp_Explorer(shape,TopAbs_FACE); faces=[]
    while explorer.More():
        faces.append(TopoDS.Face(explorer.Current())); explorer.Next()
    rows=[]
    for i,face in enumerate(faces,1):
        values={}
        for name,kind in (('Gauss',BRepGProp_Vinert),('GaussKronrod',BRepGProp_VinertGK)):
            prop=kind(BRepGProp_Face(face,True),BRepGProp_Domain(face),origin,epsilon)
            error=prop.GetEpsilon() if name=='Gauss' else prop.GetErrorReached()
            values[name]={'signed_flux':prop.Mass(),'estimated_relative_error':error}
        rows.append({'face_index':i,'surface_type':str(BRepAdaptor_Surface(face).GetType()),**values,
            'absolute_method_difference':abs(values['Gauss']['signed_flux']-values['GaussKronrod']['signed_flux'])})
    return rows


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    pins={args.input:BODY_SHA,Path(__file__):native.sha256(__file__)}
    if args.output.exists() or OCP.__version__!='8.0.1.0' or any(native.sha256(p)!=s for p,s in pins.items()):
        raise ValueError('exact_inputs_runtime_and_new_output_required')
    start=time.monotonic(); origin=gp_Pnt(0,0,0)
    witness=contributions(BRepPrimAPI_MakeBox(gp_Pnt(31,-27,48),2,3,4).Shape(),origin,1e-12)
    volumes={name:math.fsum(r[name]['signed_flux'] for r in witness) for name in ('Gauss','GaussKronrod')}
    if any(abs(v-24)>1e-10 for v in volumes.values()): raise ValueError('analytic_flux_witness_failed')
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(args.input),BRep_Builder()): raise ValueError('native_read_failed')
    report={'schema':'m64-shared-origin-face-quadrature/v1','status':'incomplete',
        'OCP_version':OCP.__version__,'source_sha256':pins[Path(__file__)],'input_sha256':BODY_SHA,
        'reference_point':[0,0,0],'analytic_box_volume':24,'witness_computed_volumes':volumes,
        'CAD_modified':False,'manufacturing_authorized':False,'absolute_volume_certified':False,'runs':[]}
    native.save(args.output,report)
    for eps in (1e-10,1e-12):
        rows=contributions(shape,origin,eps)
        sums={name:math.fsum(r[name]['signed_flux'] for r in rows) for name in ('Gauss','GaussKronrod')}
        report['runs'].append({'epsilon':eps,'sum_signed_flux':sums,'faces_private':rows,
            'method_relative_difference':abs(sums['Gauss']/sums['GaussKronrod']-1)})
        native.save(args.output,report)
    report.update(status='completed',elapsed_seconds=time.monotonic()-start,
                  inputs_unchanged=all(native.sha256(p)==s for p,s in pins.items()))
    native.save(args.output,report)
    print(json.dumps({'status':report['status'],'volume_sums':[r['sum_signed_flux'] for r in report['runs']],
        'worst_faces':sorted(report['runs'][-1]['faces_private'],key=lambda r:r['absolute_method_difference'],reverse=True)[:12]}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','output'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
