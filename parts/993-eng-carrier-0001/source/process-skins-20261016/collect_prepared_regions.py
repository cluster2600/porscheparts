"""Collect mandatory successful region checkpoints in admitted envelope order."""
import argparse
import json
from pathlib import Path
import os

from admitted_regions_v2 import EnvelopeStore
from prepared_regions import PreparedRegions
from region_checkpoints import sha


def collect(store_path,regions_path,output):
    store_path=Path(store_path).resolve();regions_path=Path(regions_path).resolve();output=Path(output).resolve()
    report=json.loads((store_path/'envelopes.json').read_text());store=EnvelopeStore(store_path,report['input_sha256'],report['parameters'])
    rows=[]
    for region in store.report['regions']:
        source=region['source_index'];path=regions_path/f'source-{source:03d}/region-checkpoint.json'
        if not path.is_file():raise ValueError(f'Required region {source} has no successful checkpoint')
        receipt=json.loads(path.read_text())
        if receipt.get('status')!='region_geometry_completed_no_global_admission' or receipt['source_index']!=source:
            raise ValueError('A diagnostic without its successful region checkpoint cannot be collected')
        rows.append(dict(source_index=source,checkpoint=os.path.relpath(path,output.parent),checkpoint_sha256=sha(path)))
    manifest=dict(schema='prepared-support-regions-1',status='frozen_region_manifest_no_global_admission',
        envelope_store_sha256=store.manifest_sha256,regions=rows)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as target:target.write(json.dumps(manifest,separators=(',',':'),allow_nan=False)+'\n')
    PreparedRegions(output,[r['source_index'] for r in store.report['regions']]).verify();store.verify()
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['envelopes','regions','output']:parser.add_argument(name,type=Path)
    args=parser.parse_args();result=collect(args.envelopes,args.regions,args.output)
    print(json.dumps(dict(status=result['status'],regions=len(result['regions']))))
