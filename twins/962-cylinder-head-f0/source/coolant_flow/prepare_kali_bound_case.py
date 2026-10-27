"""Bind the volume/surface receipts and hard-limit the unmodified first case recipe."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(mesh,surface,budget,output):
    record=json.loads((mesh/'mesh-report.json').read_text())
    audit=json.loads((mesh/'saved-readback.json').read_text())
    if record['surface_receipt_sha256']!=sha(surface/'surface-report.json'):
        raise ValueError('Volume belongs to a different surface receipt')
    if record['mesh_sha256']!=audit['mesh_sha256'] or record['mesh_sha256']!=sha(mesh/'coolant.msh'):
        raise ValueError('Volume/audit binding changed')
    # The first preparation source is pinned by case-001, so retain it and add this binding.
    from prepare_kali_case import prepare as original_prepare
    original_prepare(mesh,surface,budget,output)
    runner=output/'Allrun.sh'
    runner.write_text('''#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 - "$case_dir" <<'PYVERIFY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);record=json.loads((root/'case-report.json').read_text())
for name,digest in record['case_hashes'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Case input changed: '+name)
PYVERIFY
exec timeout --signal=TERM --kill-after=30s 1800 bash "$case_dir/run_kali_case.sh"
''')
    report_path=output/'case-report.json'
    report=json.loads(report_path.read_text())
    report['source_hashes'][Path(__file__).name]=sha(Path(__file__))
    report['source_hashes']['mesh-report.json']=sha(mesh/'mesh-report.json')
    report['case_hashes']['Allrun.sh']=sha(runner)
    report['maximum_job_seconds_including_kill_grace']=1830
    report['surface_volume_receipts_bound']=True
    report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','surface','budget','output'):parser.add_argument(name,type=Path)
    a=parser.parse_args();prepare(*(p.resolve() for p in (a.mesh,a.surface,a.budget,a.output)))
