"""Run pinned native constructors on the complete independently admitted mask set."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'prepared', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['admission_proof']).read_text())
    assert proof['admission_independently_verified'] and proof['mesh_sha256'] == sha(job['mesh'])
    control = json.loads(Path(job['native_control_proof']).read_text())
    assert control['native_controls_independently_verified'] and control['job_sha256'] == sha(job['native_control_job'])
    preparation = json.loads((args.prepared/'report.json').read_text())
    assert preparation['job_sha256'] == sha(args.job) and preparation['complete_target_denominator'] == proof['admitted_trials']
    spec = importlib.util.spec_from_file_location('frozen_bounded_cgal_runner', job['constructor_helper'])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    args.output.mkdir(mode=0o700, exist_ok=False); rows = []
    for item in preparation['private_targets']:
        name = 'curve-'+str(item['curve']).zfill(4); path = args.prepared/name
        assert sha(path/'input.obj') == item['input_OBJ_sha256'] and sha(path/'target-edges.txt') == item['target_sha256']
        assert sha(path/'private-halo-map.npz') == item['halo_map_sha256']
        result = helper.run(Path(job['cgal_binary']), path/'input.obj', path/'target-edges.txt', args.output/name, started)
        rows.append(dict(curve=item['curve'], **result))
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), trials=rows,
                  native_trials=len(rows), native_successes=sum(row['exit_code'] == 0 for row in rows),
                  all_owned_children_reaped=True, independent_inspection_required=True,
                  physical_acceptance=False, manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'trials'}), flush=True)


if __name__ == '__main__':
    main()
