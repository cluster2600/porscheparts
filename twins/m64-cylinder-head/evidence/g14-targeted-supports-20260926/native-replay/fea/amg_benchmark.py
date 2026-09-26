"""Bounded retained-matrix CPU benchmark; no meshing, CCX or design acceptance."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ENTRY=HERE/'next_candidates.py'
ENTRY_SHA='2feb0779cbec984f75d50418d535a2e067792fe0261d3c18254f5d11a01d93bb'
if hashlib.sha256(ENTRY.read_bytes()).hexdigest()!=ENTRY_SHA:raise ValueError('frozen entry changed')
spec=importlib.util.spec_from_file_location('g14_next',ENTRY)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
np=c.np
ORIGINAL=HERE/'candidate-outer-extended-2'
SUMMARY_SHA='d749e308289f2232333e0a2b3b70d1df2605d58609ad6a9f0386d6155a307396'
NATIVE_REFERENCE=c.REPO/'work/m64-g13/native-fea/run-1/summary-0001.json'


def inputs():
    if c.g8.sha256(ORIGINAL/'summary.json')!=SUMMARY_SHA:raise ValueError('retained summary changed')
    summary=json.loads((ORIGINAL/'summary.json').read_text())
    if summary['status']!='completed' or summary['numerically_qualified'] is not True:raise ValueError('qualified coarse witness required')
    for name,want in summary['retained_artifacts_sha256'].items():
        if c.g8.sha256(c.g13.confined(ORIGINAL,name))!=want:raise ValueError('retained artifact changed: '+name)
    proof=c.trust(SimpleNamespace(reference=NATIVE_REFERENCE,id=c.EXTERIOR))[2]
    if proof!=summary['proof']:raise ValueError('runtime or source proof changed')
    case=c.g13.confined(ORIGINAL,summary['result']).parent
    return case,dict(original_summary_sha256=SUMMARY_SHA,original_proof=proof)


def modes(points,mapping):
    """Reorder complete free XYZ triples; six rigid modes are near-null candidates only."""
    nodes=sorted({n for n,d in mapping});index={pair:i for i,pair in enumerate(mapping)}
    expected=[(n,d) for n in nodes for d in (1,2,3)]
    if len(index)!=len(mapping) or set(index)!=set(expected):raise ValueError('complete free XYZ triples required')
    perm=np.array([index[pair] for pair in expected])
    xyz=np.array([points[n] for n in nodes],dtype=np.float64)
    if not np.isfinite(xyz).all():raise ValueError('nonfinite coordinates')
    xyz-=xyz.mean(axis=0);scale=np.linalg.norm(xyz,axis=1).max()
    if scale<=0:raise ValueError('nondegenerate geometry required')
    x,y,z=(xyz/scale).T
    b=np.zeros((len(mapping),6),dtype=np.float64)
    b[0::3,0]=1;b[1::3,1]=1;b[2::3,2]=1
    b[0::3,3]=-y;b[1::3,3]=x
    b[0::3,4]=-z;b[2::3,4]=x
    b[1::3,5]=-z;b[2::3,5]=y
    if np.linalg.matrix_rank(b)!=6:raise ValueError('six independent near-null candidates required')
    return perm,b


def self_check():
    points={1:(0,0,0),2:(1,0,0),3:(0,1,0),4:(0,0,1)}
    mapping=[(n,d) for n in points for d in (1,2,3)][::-1]
    perm,b=modes(points,mapping)
    assert [mapping[i] for i in perm]==[(n,d) for n in points for d in (1,2,3)]
    assert b.shape==(12,6) and np.linalg.matrix_rank(b)==6
    assert np.array_equal(b[0::3,0],np.ones(4)) and np.count_nonzero(b[1::3,0])==0
    try:modes(points,mapping[:-1])
    except ValueError:pass
    else:raise AssertionError('partial XYZ map accepted')


def run(output):
    import pyamg
    import scipy
    from scipy.sparse.linalg import cg
    if pyamg.__version__!='5.3.0' or scipy.__version__!='1.14.1' or np.__version__!='2.2.6':raise ValueError('pinned benchmark versions required')
    if any(os.environ.get(k)!='1' for k in c.THREAD_ENV):raise ValueError('serial numerical environment required')
    case,proof=inputs();output.mkdir(parents=True,exist_ok=False)
    self_check();started=time.monotonic()
    report=dict(classification='CPU_preconditioner_benchmark_only',source_sha256=c.g8.sha256(Path(__file__)),proof=proof,
        versions=dict(pyamg=pyamg.__version__,numpy=np.__version__,scipy=scipy.__version__),cases=[],complete=False,error=None,
        CCX_rerun=False,meshing_rerun=False,CUDA_executed=False,production_recipe_promoted=False,
        mesh_convergence_qualified=False,manufacturing_authorized=False,engine_start_authorized=False,
        near_nullspace_scope='Six restricted rigid modes; not null modes of the clamped problem',
        solver_scope='Same stiffness, two RHS, FP64 CG rtol1e-10 maxiter20000; symmetric fixed V-cycle versus Jacobi')
    try:
        points,_,support=c.g9.deck((case/'x.inp').read_text())
        matrix,mapping=c.bench.read_matrix(case/'matrix.sti',case/'matrix.dof',points,support)
        prepare=time.monotonic()
        perm,b=modes(points,mapping);a=matrix[perm,:][:,perm].tobsr(blocksize=(3,3))
        preparation=time.monotonic()-prepare
        np.random.seed(0);begin=time.monotonic()
        ml=pyamg.smoothed_aggregation_solver(a,B=b,symmetry='symmetric',strength='symmetric',aggregate='standard',
            smooth=('jacobi',{'omega':4/3}),presmoother=('block_gauss_seidel',{'sweep':'symmetric'}),
            postsmoother=('block_gauss_seidel',{'sweep':'symmetric'}),max_levels=10,max_coarse=100,coarse_solver='pinv')
        setup=time.monotonic()-begin
        if not ml.symmetric_smoothing:raise ValueError('nonsymmetric smoothing')
        for level in ml.levels[:-1]:
            difference=level.R-level.P.T
            if difference.nnz and np.max(np.abs(difference.data))>1e-12:raise ValueError('restriction not transpose of prolongation')
        preconditioner=ml.aspreconditioner(cycle='V')
        rng=np.random.default_rng(0);v,w=rng.normal(size=(2,a.shape[0]));mv,mw=preconditioner@v,preconditioner@w
        symmetry_error=abs(v@mw-w@mv)/max(abs(v@mw),abs(w@mv),1.)
        if not np.isfinite(mv).all() or not np.isfinite(mw).all() or not np.isfinite(symmetry_error) or symmetry_error>1e-10 or v@mv<=0 or w@mw<=0:raise ValueError('preconditioner symmetry/positivity smoke failed')
        report['hierarchy']=dict(preparation_seconds=preparation,setup_seconds=setup,levels=len(ml.levels),operator_complexity=ml.operator_complexity(),grid_complexity=ml.grid_complexity(),
            symmetry_smoke_relative_error=float(symmetry_error),positivity_smoke_only=True)
        report['free_dofs']=len(mapping);report['matrix_nnz']=matrix.nnz
        for name in ('x','minus_z'):
            _,loads,fixed=c.g9.deck((case/(name+'.inp')).read_text())
            if fixed!=support:raise ValueError('changed support')
            rhs=c.g9.rhs_for(mapping,loads)
            for method in ('jacobi','amg'):
                begin=time.monotonic();iterations=0
                if method=='jacobi':u,timing=c.bench.solve(matrix,rhs,'cpu',max_seconds=900)
                else:
                    def callback(_):
                        nonlocal iterations
                        iterations+=1
                        if time.monotonic()-begin>900:raise TimeoutError('AMG CG RHS limit')
                    ordered,info=cg(a,rhs[perm],M=preconditioner,rtol=1e-10,atol=0.,maxiter=20000,callback=callback)
                    u=np.empty_like(ordered);u[perm]=ordered
                    timing=dict(info=int(info),iterations=iterations,solve_seconds=time.monotonic()-begin)
                residual=float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
                solution=dict(u=u,passed=bool(timing['info']==0 and np.isfinite(u).all() and residual<=1e-8))
                compared=c.reference.compare(case,name,matrix,mapping,solution,rhs,points,support)
                row=dict(direction=name,method=method,timing=timing,relative_residual=residual,passed=compared['passed'],agreement=compared['agreement'])
                report['cases'].append(row);c.g11.publish(output/(name+'-'+method+'.json'),row)
                print(json.dumps(row),flush=True)
                if not compared['passed']:raise ValueError('unchanged numerical acceptance failed')
        if inputs()[1]!=proof:raise ValueError('retained inputs changed during benchmark')
        report['complete']=True
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:
        report['wall_seconds']=time.monotonic()-started
        report['peak_process_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['RSS_units']='bytes on this native macOS process, not group RSS'
        c.g11.publish(output/'report.json',report)
    return 0 if report['complete'] else 2


def control(output):
    if output.exists():raise FileExistsError('new benchmark directory required')
    start=time.monotonic();peak=0;reason=None
    with output.with_name(output.name+'-worker.log').open('x') as log:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--output',str(output.resolve())],
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while process.poll() is None:
                rows=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True,timeout=5).splitlines()
                rss=sum(int(r.split()[2])*1024 for r in rows if int(r.split()[1])==process.pid)
                peak=max(peak,rss)
                if rss>12*1024**3 or time.monotonic()-start>1200:
                    reason='observed_12GiB_RSS_limit' if rss>12*1024**3 else '1200_second_deadline';break
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
    c.g11.publish(output.with_name(output.name+'-controller.json'),dict(returncode=process.returncode,error=reason,
        observed_group_RSS_peak_bytes=peak,monitor_interval_seconds=1,wall_seconds=time.monotonic()-start,
        source_sha256=c.g8.sha256(Path(__file__)),worker_pgid=process.pid,worker_reaped=True))
    return 0 if process.returncode==0 and reason is None else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--self-check',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.self_check:self_check()
    else:
        if args.output is None or not args.output.resolve().is_relative_to(HERE) or args.output.resolve()==HERE:parser.error('new private output below fea required')
        def timeout(signum,frame):raise TimeoutError('1200-second benchmark deadline')
        signal.signal(signal.SIGTERM,timeout)
        if args.worker:
            signal.signal(signal.SIGALRM,timeout);signal.alarm(1200)
            raise SystemExit(run(args.output))
        raise SystemExit(control(args.output))
