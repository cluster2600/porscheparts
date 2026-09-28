"""New native hashfix retry of the FAILED exact 1.5mm deck, never remesh or overwrite."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REFERENCE=HERE/'hashfix_reference.py'
REFERENCE_SHA='4c0eee9c4598c439702b5c46fa9ecc7f2118be7d2de296325290b7a9dbf97859'
if hashlib.sha256(REFERENCE.read_bytes()).hexdigest()!=REFERENCE_SHA:raise ValueError('frozen reference source changed')
spec=importlib.util.spec_from_file_location('hashfix_reference',REFERENCE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
m,c=r.m,r.c
OLD=HERE/'candidate-centre-caps-1p5-v1'
OLD_SUMMARY_SHA='6044294a6240dc70a4b9c0c7a5655a8392e3a6d9e470ee5be7068ce7c24cb59b'
OLD_CASE_SHA='818aa4419bec675f094774ef26df20e09cb98566e1864b52ff131fc284396f04'
X_SHA='49a055ea14ead0eb19a0a2586efa5d3a2d454236b322d3e3a323fd8d7bd4ae36'
CASE='native-mac-g14-caps-1.5-hashfix'


def minus_z(text):
    if text.count('*CLOAD\n')!=1:raise ValueError('one frozen CLOAD block required')
    head,tail=text.split('*CLOAD\n');rows,suffix=tail.split('*',1);transformed=[]
    for line in rows.splitlines():
        node,direction,value=line.split(',')
        if direction!='1' or not c.np.isfinite(float(value)) or float(value)<=0:
            raise ValueError('positive x nodal loads required')
        transformed.append(node+',3,-'+value+'\n')
    if not transformed:raise ValueError('nonempty CLOAD required')
    return head+'*CLOAD\n'+''.join(transformed)+'*'+suffix


def inputs(args):
    if REFERENCE_SHA is None or c.g8.sha256(REFERENCE)!=REFERENCE_SHA:
        raise ValueError('reviewed reference source not frozen')
    if c.g8.sha256(args.reference)!=args.reference_sha256:raise ValueError('qualified hashfix reference changed')
    qualified=json.loads(args.reference.read_text());inventory=qualified['proof']['runtime']['inventory_sha256']
    reference_proof=r.inputs(inventory)
    if (qualified['proof']!=reference_proof or qualified['complete'] is not True or qualified['error'] is not None
            or qualified['all_numerical_checks_passed'] is not True or qualified['runtime_verified_after'] is not True
            or tuple((row['id'],row['direction']) for row in qualified['rows'])!=r.PLAN
            or any(row['passed'] is not True or row['direct']['native_returncode']!=0
                   or row['direct']['error'] is not None or not c.native.bounded(row['relative_residual'],1e-8)
                   for row in qualified['rows'])):raise ValueError('two qualified hashfix G13 RHS required')
    for name,digest in qualified['artifacts_sha256'].items():
        if c.g8.sha256(c.g13.confined(args.reference.parent,name))!=digest:raise ValueError('hashfix reference artifact changed')
    baseline,variant,old_proof=m.inputs()
    if c.g8.sha256(OLD/'summary.json')!=OLD_SUMMARY_SHA:raise ValueError('failed medium summary changed')
    previous=json.loads((OLD/'summary.json').read_text());oldcase=OLD/previous['result']
    if c.g8.sha256(oldcase)!=OLD_CASE_SHA or c.g8.sha256(oldcase.parent/'x.inp')!=X_SHA:
        raise ValueError('frozen failed deck or case changed')
    for name,digest in previous['artifacts_sha256'].items():
        if c.g8.sha256(c.g13.confined(OLD,name))!=digest:raise ValueError('failed medium artifact changed')
    row=json.loads(oldcase.read_text())
    if row['proof']!=old_proof or row['numerically_qualified'] is not False or row['cases']!=[]:
        raise ValueError('expected retained rejected medium attempt')
    proof=dict(reference_sha256=args.reference_sha256,reference=reference_proof,old_failure_summary_sha256=OLD_SUMMARY_SHA,
        old_failure_case_sha256=OLD_CASE_SHA,original_x_deck_sha256=X_SHA,source_sha256=c.g8.sha256(Path(__file__)),
        recipe='G14-caps-exact-medium-hashfix-retry-v1',limits=old_proof['limits'],original_failure_preserved=True)
    return baseline,variant,row,proof,oldcase.parent


def audit(case,binary,deadline):
    text=(case/'x.inp').read_text();points,_,support=c.g9.deck(text);prefix=text.split('*STEP\n')[0]
    with (case/'matrix.inp').open('x') as f:
        f.write(prefix.replace('*SOLID SECTION','*DENSITY\n2.7e-9\n*SOLID SECTION')+
            '*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
    exported=r.ccx(case,'matrix',binary,m.remaining(deadline,m.EXPORT_SECONDS),new_session=False)
    matrix,mapping=c.g9.bench.read_matrix(case/'matrix.sti',case/'matrix.dof',points,support);rows=[]
    for name,_ in c.g11.DIRECTIONS:
        current=(case/(name+'.inp')).read_text();_,loads,fixed=c.g9.deck(current)
        if current.split('*STEP\n')[0]!=prefix or fixed!=support:raise ValueError('same stiffness/support required')
        rhs=c.g9.rhs_for(mapping,loads)
        u,timing=c.g9.bench.solve(matrix,rhs,'cpu',max_seconds=m.remaining(deadline,m.CG_SECONDS))
        residual=float(c.np.linalg.norm(matrix@u-rhs)/c.np.linalg.norm(rhs))
        solution=dict(u=u,passed=bool(timing['info']==0 and c.np.isfinite(u).all() and residual<=1e-8))
        compared=r.reference.compare(case,name,matrix,mapping,solution,rhs,points,support)
        row=dict(direction=name,numerical_crosscheck_passed=compared['passed'],mechanics=compared['mechanics'],
            solver=timing,relative_residual=residual,fresh_direct=compared['agreement'],export_seconds=exported['seconds'],
            free_dofs=len(mapping),matrix_nnz=matrix.nnz)
        rows.append(row);c.g11.publish(case/(name+'-crosscheck.json'),row)
        if not compared['passed']:break
    return rows


def worker(args):
    start=time.monotonic();deadline=start+m.TOTAL_SECONDS
    _,variant,previous,proof,oldcase=inputs(args)
    if json.loads((args.output/'identity.json').read_text())!=proof:raise ValueError('worker identity changed')
    case=args.output/CASE;case.mkdir()
    result=dict(id=c.IDENT,proof=proof,step_sha256=variant['step_sha256'],mesh=previous['mesh'],cases=[],
        complete=False,error=None,numerically_qualified=False,mesh_reused_from_failed_attempt=True,
        mesh_convergence_qualified=False,FEA_executed=False,CUDA_executed=False,AMG_executed=False,
        assembled_stiffness_qualified=False,hot_material_qualified=False,manufacturing_authorized=False,engine_start_authorized=False,
        boundary_hypothesis=previous['boundary_hypothesis'])
    try:
        shutil.copyfile(oldcase/'mesh.msh',case/'mesh.msh');shutil.copyfile(oldcase/'x.inp',case/'x.inp')
        with (case/'minus_z.inp').open('x') as f:f.write(minus_z((case/'x.inp').read_text()))
        result['frozen_decks_sha256']={n:c.g8.sha256(case/n) for n in ('x.inp','minus_z.inp','mesh.msh')}
        binary=proof['reference']['runtime']['binary']
        for name,_ in c.g11.DIRECTIONS:
            result['FEA_executed']=True
            direct=r.ccx(case,name,binary,m.remaining(deadline,m.DIRECT_SECONDS),new_session=False)
            points,loads,support=c.g9.deck((case/(name+'.inp')).read_text())
            _,mechanics=c.g9.mechanics(case,name,points,loads,support)
            c.g11.publish(case/(name+'-direct.json'),dict(execution=direct,mechanics=mechanics))
            print(json.dumps(dict(direction=name,seconds=direct['seconds'],mechanics=mechanics)),flush=True)
            if not mechanics['equilibrium_passed']:raise ValueError('direct equilibrium failed')
        result['cases']=audit(case,binary,deadline)
        if inputs(args)[3]!=proof:raise ValueError('runtime, source or frozen evidence changed')
        result['complete']=len(result['cases'])==2;result['numerically_qualified']=c.g11.qualified_rows(result)
        result['maximum_journal_motion_mm']=c.g11.motion(result) if result['numerically_qualified'] else None
        coarse=json.loads((m.pre.COARSE/json.loads((m.pre.COARSE/'summary.json').read_text())['result']).read_text())
        result['coarse_to_medium']=c.g11.assessment(coarse,result)
    except BaseException as exc:result['error']=type(exc).__name__+': '+str(exc)
    finally:
        result['wall_seconds']=time.monotonic()-start
        result['hashes']={p.name:c.g8.sha256(p) for p in sorted(case.iterdir()) if p.is_file()}
        c.g11.publish(case/'case.json',result)
    return 0 if result['error'] is None and result['numerically_qualified'] else 2


def control(args):
    proof=inputs(args)[3]
    if shutil.disk_usage(HERE).free<m.FREE_DISK_MIN:raise ValueError('minimum 12GiB free disk required')
    args.output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,args.output/Path(__file__).name)
    c.g11.publish(args.output/'identity.json',proof)
    start=time.monotonic();peak=0;free=shutil.disk_usage(args.output).free;lowest=free;reason=None
    with (args.output/'worker.log').open('x') as log:
        command=[sys.executable,str(Path(__file__).resolve()),'--worker','--output',str(args.output),
            '--reference',str(args.reference),'--reference-sha256',args.reference_sha256]
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,**c.THREAD_ENV))
        try:
            while process.poll() is None:
                rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True,timeout=5).splitlines()
                rss=sum(int(row.split()[2])*1024 for row in rows if int(row.split()[1])==process.pid)
                free=shutil.disk_usage(args.output).free;peak=max(peak,rss);lowest=min(lowest,free)
                if rss>m.RSS_LIMIT or free<m.FREE_DISK_MIN or time.monotonic()-start>m.TOTAL_SECONDS:
                    reason='28GiB_RSS_limit' if rss>m.RSS_LIMIT else '12GiB_free_disk_limit' if free<m.FREE_DISK_MIN else '7200s_deadline';break
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
    path=args.output/CASE/'case.json';result=json.loads(path.read_text()) if path.is_file() else {}
    passed=process.returncode==0 and reason is None and result.get('error') is None and result.get('numerically_qualified') is True
    summary=dict(classification='bounded_G14_exact_medium_hashfix_retry',proof=proof,complete=passed,returncode=process.returncode,
        error=reason,worker_reaped=True,worker_pgid=process.pid,observed_group_RSS_peak_bytes=peak,lowest_observed_free_disk_bytes=lowest,
        wall_seconds=time.monotonic()-start,numerically_qualified=passed,result=str(path.relative_to(args.output)) if path.is_file() else None,
        artifacts_sha256={str(p.relative_to(args.output)):c.g8.sha256(p) for p in sorted(args.output.rglob('*')) if p.is_file()},
        mesh_convergence_qualified=False,manufacturing_authorized=False,engine_start_authorized=False)
    c.g11.publish(args.output/'summary.json',summary)
    return 0 if passed else 2


if __name__=='__main__':
    def interrupted(signum,frame):raise InterruptedError('retry interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--reference-sha256',required=True);parser.add_argument('--check',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();args.output=args.output.resolve();args.reference=args.reference.resolve()
    if not args.output.is_relative_to(HERE) or args.output==HERE:parser.error('new private FEA output required')
    if args.check:print(json.dumps(inputs(args)[3]));raise SystemExit(0)
    raise SystemExit(worker(args) if args.worker else control(args))
