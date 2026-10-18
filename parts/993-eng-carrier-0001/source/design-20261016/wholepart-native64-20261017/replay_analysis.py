"""Reanalyse restored real four-frame outputs, without Docker or a solver."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

spec=importlib.util.spec_from_file_location('_fixed_native64_restore',Path(__file__).with_name('restore.py'))
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)


def replay(root,expected):
    started=time.monotonic();report=restore.verify(expected);root=Path(root).resolve()
    import numpy as np
    versions=dict(python=sys.version.split()[0],numpy=np.__version__)
    if versions!=report['analysis_runtime']:raise ValueError('Historical analysis runtime versions differ')
    for row in report['payloads']:
        if restore.sha(root/row['restored'])!=row['original_sha256']:raise ValueError('Restored evidence differs')
    output=root/'reanalysis-001'
    if output.exists()or output.is_symlink():raise FileExistsError('Preserve an existing reanalysis')
    output.mkdir(exist_ok=False)
    case=root/report['restored_case'];solver=case/'execution-001/solver-execution-receipt.json'
    command=[sys.executable,'-I','-B',str(case/'assess.py'),str(case/'prepared-001'),str(output/'numerical-assessment.json'),
        '--solver-receipt',str(solver),'--solver-receipt-sha256',report['solver_receipt_sha256']]
    env=dict(PATH='/usr/bin:/bin',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
    timed_out=False
    with(output/'stdout.log').open('xb')as stdout,(output/'stderr.log').open('xb')as stderr:
        try:result=subprocess.run(command,cwd='/',env=env,stdout=stdout,stderr=stderr,timeout=60);actual_rc=result.returncode
        except subprocess.TimeoutExpired:timed_out=True;actual_rc=None
    path=output/'numerical-assessment.json';actual_sha=restore.sha(path)if path.is_file()else None
    unchanged=all(restore.sha(root/r['restored'])==r['original_sha256']for r in report['payloads'])
    restore.verify(expected)
    passed=actual_rc==0 and not timed_out and unchanged and actual_sha==report['expected_analysis_sha256']
    receipt=dict(status='actual_four_frame_reanalysis_byte_identical'if passed else'reanalysis_refused',
        actual_returncode=actual_rc,timed_out=timed_out,analysis_timeout_seconds=60,
        original_expected_analysis_sha256=report['expected_analysis_sha256'],actual_analysis_sha256=actual_sha,
        all_controls_and_measures_byte_identical=passed,restored_inputs_unchanged=unchanged,
        capsule_manifest_sha256=expected,analysis_python=sys.executable,command=command,cwd='/',
        analysis_runtime_versions=versions,
        new_solver_run=False,new_CCX_execution=False,section_workers=0,global_admission=False,seconds=time.monotonic()-started)
    with(output/'receipt.json').open('x')as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps(receipt));return 0 if passed else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('restored_root',type=Path);p.add_argument('--manifest-sha256',required=True)
    a=p.parse_args();raise SystemExit(replay(a.restored_root,a.manifest_sha256))
