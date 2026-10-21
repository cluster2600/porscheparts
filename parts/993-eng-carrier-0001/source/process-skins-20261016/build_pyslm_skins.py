"""Prepare actual free-interval support surfaces and inspectable LPBF vectors."""
import argparse
import importlib.util
import json
from pathlib import Path
from exact_regions import identify
from peripheral_skins import geometry

SOURCE=Path(__file__).resolve().parent
CORE=SOURCE.parent/'process-coverage-20261016/build_pyslm.py'


def build(input_path,output,expected_sha256=None,identity_receipt=None,reuse_supports=None,
          supports_only=False,layer_generator=None,extra_sources=()):
    spec=importlib.util.spec_from_file_location('carrier_coverage_build',CORE)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    extensions=[SOURCE/name for name in ['build_pyslm_skins.py','exact_regions.py',
                'prismatic_envelopes.py','peripheral_skins.py','grid_intervals.py']]
    return core.build(input_path,output,expected_sha256,reuse_supports,identity_receipt,supports_only,
        identify_generator=identify,geometry_generator=geometry,layer_generator=layer_generator,
        source_extensions=[*extensions,*extra_sources])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    identity=parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--sha256');identity.add_argument('--identity-receipt',type=Path)
    parser.add_argument('--reuse-supports',type=Path);parser.add_argument('--supports-only',action='store_true')
    args=parser.parse_args()
    report=build(args.input,args.output,args.sha256,args.identity_receipt,args.reuse_supports,args.supports_only)
    print(json.dumps({'status':report.get('status'),'region_coverage_complete':report.get('region_coverage_complete')},allow_nan=False))
