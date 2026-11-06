"""Run fixed explicit-edge CGAL trials, preserving raw refusals and owned-child witnesses."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def write_obj(path,vertices,faces):
    with path.open('x') as stream:
        for p in vertices:stream.write('v '+' '.join(format(float(x),'.17g') for x in p)+'\n')
        for f in faces:stream.write('f '+' '.join(str(int(x)+1) for x in f)+'\n')


def run(binary,source,targets,output,global_started):
    output.mkdir(mode=0o700,exist_ok=False);started = time.monotonic();peak = None;reason = None
    before = (sha(binary),sha(source),sha(targets));command = [str(binary),str(source),str(output/'candidate.obj'),str(targets)]
    with (output/'stdout.log').open('xb') as stdout,(output/'stderr.log').open('xb') as stderr:
        child = subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
        try:
            while child.poll() is None:
                probe = subprocess.run(['ps','-o','rss=','-p',str(child.pid)],capture_output=True,text=True)
                assert probe.returncode==0 or child.poll() is not None
                if probe.stdout.strip():peak = max(peak or 0,int(probe.stdout.strip()))
                if time.monotonic()-started>60:reason='60_second_child_limit'
                elif time.monotonic()-global_started>300:reason='shared_300_second_limit'
                elif (peak or 0)>4*1024**2:reason='4_GiB_child_RSS_limit'
                elif shutil.disk_usage(output).free<4*1024**3:reason='4_GiB_disk_floor'
                if reason:break
                time.sleep(.05)
        finally:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
            code = child.wait()
    assert before==(sha(binary),sha(source),sha(targets))
    target = output/'candidate.obj'
    report = dict(exit_code=code,seconds=time.monotonic()-started,maximum_sampled_child_RSS_KiB=peak,
                  stop_reason=reason,owned_child_reaped=True,input_OBJ_sha256=before[1],target_sha256=before[2],
                  binary_sha256=before[0],input_files_unchanged=True,output_exists=target.is_file(),
                  output_OBJ_sha256=sha(target) if target.is_file() else None,
                  constructor_success_requires_independent_inspection=True)
    (output/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
    assert reason is None,'Resource-bound stop; no more trials scheduled'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--controls-only',action='store_true')
    for name in ('prepared','control-proof','control-checker'):parser.add_argument('--'+name,type=Path)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-acquisition-gap-trials-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False);binary = Path(job['cgal_binary']);rows = []
    if args.controls_only:
        points = np.array([[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.],[0.,0.,1.],[1.,0.,1.],[1.,1.,1.],[0.,1.,1.]])
        faces = np.array([[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
        source = args.output/'control-input.obj';write_obj(source,points,faces)
        np.savez_compressed(args.output/'private-control-map.npz',points=points,triangles=faces,
                            ordered_hole_nodes=np.arange(4),expected_source_boundary_edges=np.array([[0,1],[1,2],[2,3],[3,0]]))
        positive = args.output/'positive-target.txt';positive.write_text('0 0 1\n')
        negative = args.output/'negative-target.txt';negative.write_text('1 0 5\n')
        a = run(binary,source,positive,args.output/'positive',started)
        b = run(binary,source,negative,args.output/'negative',started)
        assert a['exit_code']==0 and a['output_exists']
        assert b['exit_code']!=0 and not b['output_exists']
        assert 'selected edge not a boundary' in (args.output/'negative/stderr.log').read_text()
        rows = [dict(control='positive',**a),dict(control='negative',**b)]
    else:
        assert args.prepared is not None and args.control_proof is not None and args.control_checker is not None
        control = json.loads(args.control_proof.read_text())
        assert control['source_sha256']==sha(args.control_checker) and control['job_sha256']==sha(args.job)
        assert control['native_controls_independently_verified'] and control['constructor_source_sha256']==sha(__file__)
        report = json.loads((args.prepared/'report.json').read_text())
        assert report['source_sha256']=='11ffdce128a171224f1787d338ba2b09fc1c41d970fd970e4b3f042224c029a7'
        assert report['job_sha256']==sha(args.job) and report['complete_target_denominator']==286
        for item in report['private_targets']:
            if not item['admitted']:continue
            name = 'curve-'+str(item['curve']).zfill(4);source = args.prepared/name/'input.obj';target = args.prepared/name/'target-edges.txt'
            assert sha(source)==item['input_OBJ_sha256'] and sha(target)==item['target_sha256']
            assert sha(args.prepared/name/'private-halo-map.npz')==item['halo_map_sha256']
            outcome = run(binary,source,target,args.output/name,started)
            rows.append(dict(curve=item['curve'],**outcome))
            print(json.dumps(dict(curve=item['curve'],native_exit=outcome['exit_code'],owned_child_reaped=True)),flush=True)
        assert len(rows)==report['admitted_local_trials']
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),controls_only=args.controls_only,
                  trials=rows,all_owned_children_reaped=True,raw_constructor_failures_retained=True,
                  independent_inspection_required=True,physical_acceptance=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
