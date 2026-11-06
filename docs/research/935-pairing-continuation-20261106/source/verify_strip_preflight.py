"""Exercise the unchanged native halo/incidence controls with this constructor."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text())
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    spec=importlib.util.spec_from_file_location('frozen_native_strip_controls',job['native_control_helper'])
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    count=helper.controls(job)
    assert count==9
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False)
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),constructor_source_sha256=sha(job['constructor_source']),
                control_helper_sha256=sha(job['native_control_helper']),native_mask_and_incidence_controls_passed=count,
                full_current_mesh_or_manufacturing_admission_granted=False,physical_acceptance=False,manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
