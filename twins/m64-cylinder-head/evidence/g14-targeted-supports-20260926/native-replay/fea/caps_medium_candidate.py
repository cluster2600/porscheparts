"""Private 1.5mm caps CPU recipe; prepared only, no automatic 1mm refinement or AMG."""
import argparse
from collections import defaultdict
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

HERE=Path(__file__).resolve().parent
PREFLIGHT=HERE/'caps_mesh_preflight.py'
PREFLIGHT_SHA='4a4e93ab0304c8be5775f183ecb16c6eb0edd35c1ff91ef6cd57538256082e1c'
if hashlib.sha256(PREFLIGHT.read_bytes()).hexdigest()!=PREFLIGHT_SHA:raise ValueError('mesh preflight source changed')
spec=importlib.util.spec_from_file_location('g14_caps_preflight',PREFLIGHT)
pre=importlib.util.module_from_spec(spec);spec.loader.exec_module(pre)
c=pre.c;np=c.np
PILOT=HERE/'caps-mesh-1p5-v1'
PILOT_SHA='5074583735c316a65060d3ab758de7cbb62ce775a8cf7de8a763c0a8cfd85a27'
CONTROLLER_SHA='1aee3044992d78d334387211bc6dd9315ede4f64727ac9adcddf56f2f9d11ed8'
RECIPE='G14-caps-medium-CPU-direct1800-export1200-CG1200-v1'
DIRECT_SECONDS,EXPORT_SECONDS,CG_SECONDS,TOTAL_SECONDS=1800,1200,1200,7200
RSS_LIMIT,FREE_DISK_MIN=28*1024**3,12*1024**3


def inputs():
    baseline,variant,proof=pre.inputs()
    receipt=PILOT/'mesh.json';controller=PILOT.with_name(PILOT.name+'-controller.json')
    if c.g8.sha256(PREFLIGHT)!=PREFLIGHT_SHA or c.g8.sha256(receipt)!=PILOT_SHA or c.g8.sha256(controller)!=CONTROLLER_SHA:
        raise ValueError('accepted medium preflight changed')
    row=json.loads(receipt.read_text());control=json.loads(controller.read_text())
    if (row['complete'] is not True or row['error'] is not None or row['proof']!=proof
            or row['source_sha256']!=PREFLIGHT_SHA or row['step_sha256']!=variant['step_sha256']
            or row['mesh']['size_mm']!=1.5 or row['mesh']['nominal_journal_width_mm']!=11
            or control['complete'] is not True or control['returncode']!=0 or control['error'] is not None
            or control['worker_reaped'] is not True or control['mesh_receipt_sha256']!=PILOT_SHA):
        raise ValueError('completed bound medium preflight required')
    for name,sha in row['artifacts_sha256'].items():
        if c.g8.sha256(c.g13.confined(PILOT,name))!=sha:raise ValueError('preflight artifact changed')
    return baseline,variant,dict(coarse=proof,preflight_receipt_sha256=PILOT_SHA,preflight_controller_sha256=CONTROLLER_SHA,
        source_sha256=c.g8.sha256(Path(__file__)),recipe=RECIPE,preflight_nodes=row['mesh']['nodes'],
        limits=dict(direct_seconds=DIRECT_SECONDS,export_seconds=EXPORT_SECONDS,CG_RHS_seconds=CG_SECONDS,
                    total_seconds=TOTAL_SECONDS,group_RSS_bytes=RSS_LIMIT,minimum_free_disk_bytes=FREE_DISK_MIN))


def write_deck(case,points,elements,support,weights,forces,direction,name):
    """Exactly g8.solve's serialized deck; exclusive output and execution kept separate."""
    applied=defaultdict(float)
    for side,zone in weights.items():
        for n,w in zone.items():applied[n]+=forces[side]*w
    with (case/(name+'.inp')).open('x') as f:
        f.write('*HEADING\nG8 generic linear compliance pilot, not strength qualification\n*NODE\n')
        for n,q in sorted(points.items()):f.write(f'{n},'+','.join(f'{v:.12g}' for v in q)+'\n')
        f.write('*ELEMENT,TYPE=C3D10,ELSET=EALL\n')
        for n,q in elements:f.write(f'{n},'+','.join(map(str,q))+'\n')
        c.g8.write_set(f,'NSET','NALL',sorted(points));c.g8.write_set(f,'NSET','SUPPORT',support)
        f.write(f'*MATERIAL,NAME=GENERIC\n*ELASTIC\n{c.g8.E},{c.g8.NU}\n*SOLID SECTION,ELSET=EALL,MATERIAL=GENERIC\n')
        f.write('*STEP\n*STATIC\n*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n')
        for n,force in sorted(applied.items()):
            for d,v in enumerate(direction,1):
                if v:f.write(f'{n},{d},{force*v:.12g}\n')
        f.write('*NODE PRINT,NSET=SUPPORT\nRF\n*EL PRINT,ELSET=EALL\nS\n*NODE PRINT,NSET=NALL\nU\n*END STEP\n')


def ccx(case,name,seconds):
    start=time.monotonic()
    with (case/(name+'.log')).open('x') as log:
        # Deliberately inherit this worker's process group: the controller owns cleanup.
        done=subprocess.run(['ccx',name],cwd=case,stdout=log,stderr=subprocess.STDOUT,
            timeout=seconds,env=dict(os.environ,**c.THREAD_ENV))
    if done.returncode:raise ValueError('CalculiX nonzero exit')
    c.g13.serial_log(case/(name+'.log'))
    return time.monotonic()-start


def remaining(deadline,limit):
    value=min(limit,deadline-time.monotonic()-30)
    if value<=0:raise TimeoutError('medium worker reserve exhausted')
    return value


def audit(case,deadline):
    text=(case/'x.inp').read_text();points,_,support=c.g9.deck(text);prefix=text.split('*STEP\n')[0]
    with (case/'matrix.inp').open('x') as f:
        f.write(prefix.replace('*SOLID SECTION','*DENSITY\n2.7e-9\n*SOLID SECTION')+
            '*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
    exported=ccx(case,'matrix',remaining(deadline,EXPORT_SECONDS))
    matrix,mapping=c.g9.bench.read_matrix(case/'matrix.sti',case/'matrix.dof',points,support);rows=[]
    for name,_ in c.g11.DIRECTIONS:
        current=(case/(name+'.inp')).read_text();_,loads,fixed=c.g9.deck(current)
        if current.split('*STEP\n')[0]!=prefix or fixed!=support:raise ValueError('stiffness or supports changed between RHS')
        rhs=c.g9.rhs_for(mapping,loads)
        u,timing=c.g9.bench.solve(matrix,rhs,'cpu',max_seconds=remaining(deadline,CG_SECONDS))
        residual=float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
        solution=dict(u=u,passed=bool(timing['info']==0 and np.isfinite(u).all() and residual<=1e-8))
        compared=c.prior.reference.compare(case,name,matrix,mapping,solution,rhs,points,support)
        row=dict(direction=name,numerical_crosscheck_passed=compared['passed'],mechanics=compared['mechanics'],
            solver=timing,relative_residual=residual,fresh_direct=compared['agreement'],export_seconds=exported,
            free_dofs=len(mapping),matrix_nnz=matrix.nnz,
            comparison_method='unchanged g13_reference.compare, same discretization; not independent physics')
        rows.append(row);c.g11.publish(case/(name+'-crosscheck.json'),row)
        if not compared['passed']:break
    return rows


def worker(output):
    if any(os.environ.get(k)!='1' for k in c.THREAD_ENV):raise ValueError('single-thread native environment required')
    start=time.monotonic();deadline=start+TOTAL_SECONDS
    baseline,variant,proof=inputs();identity=json.loads((output/'identity.json').read_text())
    if identity!=proof:raise ValueError('worker input or recipe changed')
    os.environ['PATH']=str(c.native.WRAPPER.parent)+os.pathsep+os.environ.get('PATH','')
    case=output/'native-mac-g14-caps-1.5';case.mkdir()
    report=dict(classification='native_Mac_G14_caps_medium_CPU_not_physical_qualification',id=c.IDENT,proof=proof,
        step_sha256=variant['step_sha256'],complete=False,error=None,numerically_qualified=False,cases=[],
        FEA_executed=False,CUDA_executed=False,AMG_executed=False,manufacturing_authorized=False,engine_start_authorized=False,
        mesh_convergence_qualified=False,assembled_stiffness_qualified=False,hot_material_qualified=False,
        boundary_hypothesis='Same ideal fixed whole foot; E70000MPa,nu0.33; not bolt/contact or selected hot alloy')
    try:
        points,elements,support,weights,mesh=c.g11.mesh(variant['step_path'],1.5,baseline['values'],variant,case)
        report['mesh']=mesh;report['mesh_is_new_not_preflight_reused']=True
        loads=c.g11.forces(baseline,variant['component']);report['journal_forces_N']=loads
        for name,direction in c.g11.DIRECTIONS:
            write_deck(case,points,elements,support,weights,loads,direction,name)
            report['FEA_executed']=True;seconds=ccx(case,name,remaining(deadline,DIRECT_SECONDS))
            p,f,s=c.g9.deck((case/(name+'.inp')).read_text());_,mechanics=c.g9.mechanics(case,name,p,f,s)
            c.g11.publish(case/(name+'-direct.json'),dict(seconds=seconds,mechanics=mechanics))
            if not mechanics['equilibrium_passed']:raise ValueError('direct equilibrium failed')
        report['cases']=audit(case,deadline)
        if inputs()[2]!=proof:raise ValueError('native runtime, CAD or source changed during solve')
        report['complete']=len(report['cases'])==2;report['numerically_qualified']=c.g11.qualified_rows(report)
        report['maximum_journal_motion_mm']=c.g11.motion(report) if report['numerically_qualified'] else None
        coarse=json.loads((pre.COARSE/json.loads((pre.COARSE/'summary.json').read_text())['result']).read_text())
        report['coarse_to_medium']=c.g11.assessment(coarse,report)
        report['medium_does_not_authorize_1mm']=True
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:
        report['wall_seconds']=time.monotonic()-start;report['worker_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['hashes']={p.name:c.g8.sha256(p) for p in sorted(case.iterdir()) if p.is_file()}
        c.g11.publish(case/'case.json',report)
    return 0 if report['error'] is None and report['numerically_qualified'] else 2


def control(output):
    proof=inputs()[2]
    if shutil.disk_usage(HERE).free<FREE_DISK_MIN:raise ValueError('minimum 12GiB free disk not available')
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/Path(__file__).name)
    c.g11.publish(output/'identity.json',proof)
    start=time.monotonic();peak=0;lowest_free=shutil.disk_usage(output).free;reason=None
    with (output/'worker.log').open('x') as log:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--output',str(output.resolve())],
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,**c.THREAD_ENV))
        try:
            while process.poll() is None:
                rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True,timeout=5).splitlines()
                rss=sum(int(r.split()[2])*1024 for r in rows if int(r.split()[1])==process.pid)
                free=shutil.disk_usage(output).free;peak=max(peak,rss);lowest_free=min(lowest_free,free)
                if rss>RSS_LIMIT or free<FREE_DISK_MIN or time.monotonic()-start>TOTAL_SECONDS:
                    reason='28GiB_RSS_limit' if rss>RSS_LIMIT else '12GiB_free_disk_limit' if free<FREE_DISK_MIN else '7200s_deadline';break
                time.sleep(1)
        except BaseException as exc:reason=type(exc).__name__+': '+str(exc)
        finally:
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:pass
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait()
    path=output/'native-mac-g14-caps-1.5/case.json';result=json.loads(path.read_text()) if path.is_file() else {}
    passed=process.returncode==0 and reason is None and result.get('error') is None and result.get('numerically_qualified') is True
    summary=dict(classification='bounded_G14_medium_execution_only',proof=proof,complete=passed,returncode=process.returncode,error=reason,
        worker_reaped=True,worker_pgid=process.pid,observed_group_RSS_peak_bytes=peak,lowest_observed_free_disk_bytes=lowest_free,
        wall_seconds=time.monotonic()-start,monitor_interval_seconds=1,numerically_qualified=passed,
        result=str(path.relative_to(output)) if path.is_file() else None,
        artifact_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
        artifacts_sha256={str(p.relative_to(output)):c.g8.sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},
        mesh_convergence_qualified=False,manufacturing_authorized=False,engine_start_authorized=False)
    c.g11.publish(output/'summary.json',summary)
    return 0 if passed else 2


if __name__=='__main__':
    def interrupted(signum,frame):raise InterruptedError('medium process interrupted')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--check',action='store_true');parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();args.output=args.output.resolve()
    if sys.platform!='darwin' or not args.output.is_relative_to(HERE) or args.output==HERE:parser.error('native Mac and new private output required')
    signal.signal(signal.SIGTERM,interrupted)
    if args.check:print(json.dumps(dict(check_only=True,proof=inputs()[2])));raise SystemExit(0)
    raise SystemExit(worker(args.output) if args.worker else control(args.output))
