"""Private mesh-only sizing for the accepted caps CAD; no CCX, CG or convergence claim."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ENTRY=HERE/'caps_candidate.py'
ENTRY_SHA='ef77599f3347d581fae179ff0d7563082fd5decf0f078e2b4a5be1973b92d623'
if hashlib.sha256(ENTRY.read_bytes()).hexdigest()!=ENTRY_SHA:raise ValueError('frozen caps entry changed')
spec=importlib.util.spec_from_file_location('g14_caps_mesh_entry',ENTRY)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
COARSE=HERE/'candidate-centre-caps-2'
COARSE_SHA='d9bf5d969b74ccca1bbfa575d4c761f0ceb955348008f56276a19d8cef9ec77b'
REFERENCE=c.REPO/'work/m64-g13/native-fea/run-1/summary-0001.json'
LIMIT_SECONDS=600
LIMIT_RSS_BYTES=16*1024**3
PEER_PGIDS=(8345,4710)  # Existing outer/AMG jobs supplied by root; never signalled here.
LIMIT_COMBINED_RSS_BYTES=28*1024**3


def inputs():
    if COARSE_SHA is None:raise ValueError('coarse numerical proof is not yet pinned')
    summary_path=COARSE/'summary.json'
    if c.g8.sha256(summary_path)!=COARSE_SHA:raise ValueError('coarse summary changed')
    summary=json.loads(summary_path.read_text())
    baseline,variant,proof=c.trust(SimpleNamespace(reference=REFERENCE,id=c.IDENT))
    if (summary['status']!='completed' or summary['returncode']!=0 or summary['error'] is not None
            or summary['numerically_qualified'] is not True or summary['id']!=c.IDENT
            or summary['mesh_mm']!=2. or summary['step_sha256']!=variant['step_sha256']
            or summary['proof']!=proof):raise ValueError('qualified unchanged coarse result required')
    for name,want in summary['retained_artifacts_sha256'].items():
        if c.g8.sha256(c.g13.confined(COARSE,name))!=want:raise ValueError('coarse artifact changed: '+name)
    path=c.g13.confined(COARSE,summary['result'])
    if summary['result'] not in summary['retained_artifacts_sha256']:raise ValueError('unbound coarse result')
    result=json.loads(path.read_text())
    if (result['id']!=c.IDENT or result['step_sha256']!=variant['step_sha256'] or result['proof']!=proof
            or result['mesh']['size_mm']!=2. or result['numerically_qualified'] is not True
            or not c.g11.qualified_rows(result)):raise ValueError('coarse case binding or numerical check failed')
    motion=c.g11.motion(result)
    if motion>.04 or motion!=result['maximum_journal_motion_mm'] or motion!=summary['maximum_journal_motion_mm']:
        raise ValueError('coarse journal screen above 0.040mm or inconsistent')
    return baseline,variant,dict(coarse_summary_sha256=COARSE_SHA,coarse_case_sha256=c.g8.sha256(path),
        coarse_maximum_journal_motion_mm=motion,candidate_proof=proof,mesher_source_sha256=c.g11.source_hashes())


def worker(output,size):
    if sys.platform!='darwin':raise ValueError('this private sizing recipe records native macOS RSS bytes')
    if size not in (1.5,1.):raise ValueError('only the two agreed mesh levels')
    if any(os.environ.get(k)!='1' for k in c.THREAD_ENV):raise ValueError('serial numerical environment required')
    baseline,variant,proof=inputs();output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,output/Path(__file__).name)
    c.g11.publish(output/'identity.json',dict(id=c.IDENT,mesh_size_mm=size,proof=proof,
        source_sha256=c.g8.sha256(Path(__file__)),step_sha256=variant['step_sha256']))
    start=time.monotonic()
    report=dict(classification='G14_caps_mesh_only_resource_preflight',complete=False,error=None,id=c.IDENT,
        mesh_size_mm=size,proof=proof,step_sha256=variant['step_sha256'],source_sha256=c.g8.sha256(Path(__file__)),
        FEA_executed=False,CCX_executed=False,CG_executed=False,mesh_convergence_qualified=False,
        manufacturing_authorized=False,engine_start_authorized=False,
        scope='Actual mesh counts and meshing resources only; not direct-solver RAM or runtime prediction',
        mesher_scope='Unchanged g11.mesh, Gmsh General.NumThreads=4, quadratic tetrahedra, Gauss4 Jacobian and unchanged journal selection')
    try:
        points,elements,support,weights,mesh=c.g11.mesh(variant['step_path'],size,baseline['values'],variant,output)
        report.update(mesh=mesh,kinematic_free_dofs=3*(len(points)-len(support)),
            loaded_nodes={side:len(w) for side,w in weights.items()},
            expected_full_cylinder_area_mm2=2*c.np.pi*(baseline['values']['rocker_pivot_radius']+
                baseline['values']['carrier_journal_radial_clearance'])*variant['journal_width_mm'])
        if inputs()[2]!=proof or c.g8.sha256(Path(__file__))!=report['source_sha256']:
            raise ValueError('source, CAD or coarse proof changed during meshing')
        report['complete']=True
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:
        report['wall_seconds']=time.monotonic()-start
        report['worker_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['RSS_units']='bytes on native macOS; controller separately samples group RSS'
        report['artifact_bytes_before_receipt']=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        report['artifacts_sha256']={p.name:c.g8.sha256(p) for p in sorted(output.iterdir()) if p.is_file()}
        c.g11.publish(output/'mesh.json',report)
    return 0 if report['complete'] else 2


def control(output,size):
    inputs()  # No output or process before the pinned coarse numerical gate.
    if output.exists():raise FileExistsError('new private mesh directory required')
    start=time.monotonic();peak=0;combined_peak=0;reason=None
    with output.with_name(output.name+'-worker.log').open('x') as log:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--mesh',str(size),'--output',str(output.resolve())],
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,**c.THREAD_ENV))
        try:
            while process.poll() is None:
                rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True,timeout=5).splitlines()
                rss=sum(int(r.split()[2])*1024 for r in rows if int(r.split()[1])==process.pid)
                combined=sum(int(r.split()[2])*1024 for r in rows if int(r.split()[1]) in (process.pid,*PEER_PGIDS))
                peak=max(peak,rss);combined_peak=max(combined_peak,combined)
                if rss>LIMIT_RSS_BYTES or combined>LIMIT_COMBINED_RSS_BYTES or time.monotonic()-start>LIMIT_SECONDS:
                    reason=('observed_16GiB_RSS_limit' if rss>LIMIT_RSS_BYTES else
                            'observed_28GiB_combined_RSS_limit' if combined>LIMIT_COMBINED_RSS_BYTES else '600_second_deadline');break
                time.sleep(1)
        except BaseException as exc:reason=type(exc).__name__+': '+str(exc)
        finally:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait()
    receipt=output/'mesh.json';result=json.loads(receipt.read_text()) if receipt.is_file() else {}
    passed=process.returncode==0 and reason is None and result.get('complete') is True and result.get('error') is None
    c.g11.publish(output.with_name(output.name+'-controller.json'),dict(returncode=process.returncode,error=reason,complete=passed,
        observed_group_RSS_peak_bytes=peak,monitor_interval_seconds=1,wall_seconds=time.monotonic()-start,
        observed_combined_RSS_peak_bytes=combined_peak,observed_peer_pgids=list(PEER_PGIDS),
        source_sha256=c.g8.sha256(Path(__file__)),worker_pgid=process.pid,worker_reaped=True,
        mesh_receipt_sha256=c.g8.sha256(receipt) if receipt.is_file() else None,
        retained_directory_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()) if output.exists() else 0,
        worker_log_bytes=output.with_name(output.name+'-worker.log').stat().st_size,FEA_executed=False))
    return 0 if passed else 2


if __name__=='__main__':
    def interrupted(signum,frame):raise InterruptedError('mesh preflight interrupted')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=float,choices=(1.5,1.),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();args.output=args.output.resolve()
    if not args.output.is_relative_to(HERE) or args.output==HERE:parser.error('new output below private fea required')
    signal.signal(signal.SIGTERM,interrupted)
    if args.check:
        print(json.dumps(dict(check_only=True,proof=inputs()[2])));raise SystemExit(0)
    raise SystemExit(worker(args.output,args.mesh) if args.worker else control(args.output,args.mesh))
