"""Rebuild the declared corner-slide CAD in a fresh directory using an existing runtime."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

H=Path(__file__).resolve().parent

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['verify','rebuild'])
    parser.add_argument('--output',required=True,type=Path,help='Fresh absolute directory outside this bundle; parent must already exist')
    parser.add_argument('--runtime-root',type=Path,help='Installed runtime tree containing design-standalone and cad-base; exact recorded bytes required')
    args=parser.parse_args(argv)
    path=H/'plan.json'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('_supplied_24af_native_replay',H/'generator/native_trial.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if args.mode=='verify':
        _,before,_=module.verify(path,digest,False,args.output,args.runtime_root)
        print(json.dumps(dict(status='SOURCE_AND_RUNTIME_BYTES_VERIFIED_NO_NATIVE',pins=len(before),native_executed=False)))
        return 0
    return module.run(path,digest,args.output,args.runtime_root)

if __name__=='__main__':raise SystemExit(main())
