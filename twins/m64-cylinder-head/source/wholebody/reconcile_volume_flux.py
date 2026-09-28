#!/usr/bin/env python3
"""Reconcile complete native flux sums with independently integrated patches.

Estimated numerical errors are NOT rigorous bounds. This new receipt does not
rewrite the old whole-solid quadrature failure or promote a changed BRep.
"""
import argparse
import json
import math
from pathlib import Path
from run_local_surface_trial import BODY_SHA,native

SELECTED={582,710,711,712,713}
METHODS={('GaussLegendre',32),('GaussLegendre',64),('QUADPACK',64),('QUADPACK',128)}


def reconcile(base,patches):
    if (base.get('input_sha256')!=BODY_SHA or base.get('status')!='completed'
            or not base.get('inputs_unchanged') or base.get('reference_point')!=[0,0,0]
            or len(base.get('runs',[]))!=2 or {r['epsilon'] for r in base['runs']}!={1e-10,1e-12}):
        raise ValueError('complete_bound_native_flux_runs_required')
    corrected={}
    for patch in patches:
        if (patch.get('input_sha256')!=BODY_SHA or patch.get('status')!='completed'
                or patch.get('inputs_unchanged') is not True or len(patch.get('results',[]))!=4
                or not math.isfinite(patch.get('witness_volume',0))
                or abs(patch.get('witness_volume',0)-24)>1e-10):
            raise ValueError('complete_independent_patch_required')
        rows=patch['results'];indices={r['face_index'] for r in rows}
        if len(indices)!=1 or indices.intersection(corrected):raise ValueError('duplicate_or_mixed_patch_face')
        if {(r['outer_method'],r['inner_Gauss_order']) for r in rows}!=METHODS:
            raise ValueError('four_distinct_quadratures_required')
        values=[r['signed_flux'] for r in rows]
        errors=[r['outer_estimated_absolute_error'] for r in rows if r['outer_method']=='QUADPACK']
        if not all(math.isfinite(e) and e>=0 for e in errors):
            raise ValueError('invalid_patch_error_estimate')
        if not all(math.isfinite(v) for v in values) or max(values)-min(values)>1e-8:
            raise ValueError('patch_quadrature_did_not_converge')
        corrected[rows[0]['face_index']]=rows
    if set(corrected)!=SELECTED:raise ValueError('exact_five_bound_patches_required')
    comparisons=[]
    for run in base['runs']:
        rows=run['faces_private']
        if len(rows)!=4918 or {r['face_index'] for r in rows}!=set(range(1,4919)):
            raise ValueError('every_native_face_exactly_once_required')
        for method in ('Gauss','GaussKronrod'):
            for mode,order in sorted(METHODS):
                values=[];errors=[]
                for row in rows:
                    index=row['face_index']
                    if index in corrected:
                        patch=next(p for p in corrected[index] if (p['outer_method'],p['inner_Gauss_order'])==(mode,order))
                        value=patch['signed_flux']
                        # Same estimated-error allowance used for both fixed orders.
                        error=max(p['outer_estimated_absolute_error'] for p in corrected[index] if p['outer_method']=='QUADPACK')
                    else:
                        value=row[method]['signed_flux'];error=abs(value)*row[method]['estimated_relative_error']
                    if not math.isfinite(value) or not math.isfinite(error) or error<0:raise ValueError('invalid_flux_or_error')
                    values.append(value);errors.append(error)
                volume=math.fsum(values)
                if volume<=0:raise ValueError('positive_enclosed_volume_required')
                comparisons.append(dict(epsilon=run['epsilon'],native_method=method,patch_method=mode,
                    patch_order=order,volume=volume,estimated_absolute_error_sum=math.fsum(errors),
                    estimated_relative_error_sum=math.fsum(errors)/volume))
    values=[r['volume'] for r in comparisons];spread=max(values)/min(values)-1
    return {'comparisons':comparisons,'relative_spread':spread,'relative_gate':1e-10,
            'numerical_agreement_passed':spread<=1e-10 and all(r['estimated_relative_error_sum']<=1e-10 for r in comparisons)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--patches',type=Path,nargs=5,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    paths=[args.base,*args.patches,Path(__file__)]
    if any(path.is_symlink() for path in paths):raise ValueError('symlink_input_forbidden')
    hashes={str(path):native.sha256(path) for path in paths}
    report=reconcile(json.loads(args.base.read_text()),[json.loads(path.read_text()) for path in args.patches])
    report.update(schema='m64-reconciled-flux-control/v1',input_sha256=BODY_SHA,receipt_sha256=hashes,
        absolute_volume_certified=False,rigorous_error_bound=False,physical_scale_certified=False,
        old_failed_receipt_replaced=False,changed_partition_promoted=False,manufacturing_authorized=False,
        inputs_unchanged=all(native.sha256(path)==hashes[str(path)] for path in paths))
    native.save(args.output,report);print(json.dumps(report))
    raise SystemExit(0 if report['numerical_agreement_passed'] and report['inputs_unchanged'] else 2)
