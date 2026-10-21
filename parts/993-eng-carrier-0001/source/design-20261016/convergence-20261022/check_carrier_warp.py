"""Exercise PR274's unchanged query kernel on a real carrier and libigl oracle."""
import argparse
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import time
import traceback


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--pilot',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--oracle-report',type=Path,required=True);p.add_argument('--device',choices=['cpu','cuda:0'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);report=dict(status='incomplete',requested_device=a.device,gpu_validated=False,geometry_only=True,manufacturing_authorized=False,application_validated=False,source_sha256={str(x):sha(x)for x in [a.pilot,a.pilot.with_name('kernels.py'),a.bundle,a.oracle_report,Path(__file__)]})
    try:
        import numpy as np
        reference=json.loads(a.oracle_report.read_text())
        if sha(a.bundle)!=reference['bundle_sha256']or reference['fixed_absolute_error_limit_mm']!=.0001:raise ValueError('Fixed oracle input contract differs')
        with np.load(a.bundle,allow_pickle=False)as data:v=data['vertices'].copy();f=data['triangles'].copy();probes=data['probes'].copy();expected=data['expected_distances_mm'].copy()
        spec=importlib.util.spec_from_file_location('_unchanged_PR274_pilot',a.pilot);pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
        cold=time.perf_counter();import warp as wp
        wp.init();device=wp.get_device(a.device)
        if (a.device=='cuda:0')!=device.is_cuda:raise ValueError('Requested device mismatch; no fallback')
        if wp.__version__!='1.18.0'or np.__version__!='2.2.6':raise ValueError('Pinned runtime versions differ')
        kernel=pilot.load_kernel();assessments=[];timings=[];last=None;hits_last=None
        for repeat in range(6):
            start=cold if repeat==0 else time.perf_counter();mesh=wp.Mesh(points=wp.array(v,dtype=wp.vec3,device=device),indices=wp.array(f.reshape(-1),dtype=wp.int32,device=device));q=wp.array(probes,dtype=wp.vec3,device=device);distance=wp.empty(len(probes),dtype=wp.float32,device=device);hits=wp.empty(len(probes),dtype=wp.int32,device=device)
            wp.launch(kernel,dim=len(probes),inputs=[mesh.id,q],outputs=[distance,hits],device=device);wp.synchronize_device(device);last=distance.numpy();hits_last=hits.numpy();timings.append(time.perf_counter()-start);assessments.append(pilot.assess_distances(last,expected,hits_last))
        passed=all(x['passed']for x in assessments);np.savez_compressed(a.output/'distances.npz',distances_mm=last,hits=hits_last)
        report.update(status='passed'if passed else'failed',gpu_validated=bool(device.is_cuda and passed),cuda_dispatch_completed=bool(device.is_cuda),actual_device=str(device),device_name=device.name,device_arch=getattr(device,'arch',None),versions=dict(python=platform.python_version(),numpy=np.__version__,warp=wp.__version__),vertices=len(v),triangles=len(f),queries=len(probes),fixed_absolute_error_limit_mm=.0001,maximum_absolute_error_mm=max(x['max_abs_error_mm']for x in assessments),checks=assessments,timing=dict(cold_full_pipeline_seconds=timings[0],warm_full_pipeline_seconds=timings[1:],scope='fresh mesh/BVH, arrays, transfers, query, synchronization and host readback; cold includes init/JIT; input loading and oracle assessment excluded',speedup_claimed=False),output_distances_sha256=sha(a.output/'distances.npz'),query_groups=reference['query_groups'])
    except Exception as error:report.update(status='error',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report.get(k)for k in ['status','gpu_validated','actual_device','maximum_absolute_error_mm','error']}));return 0 if report['status']=='passed'else 1

if __name__=='__main__':raise SystemExit(main())
