"""Private native Mac CPU pilot; run only after root accepts the exact build."""
import argparse
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time

repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'twins/m64-cylinder-head/source/fourvalve'))
import g13_reference as reference
import scipy
g8,g9,bench,np=reference.g8,reference.g9,reference.bench,reference.np
HELPER_SHA='30eab2794ca04260ab4b4ba5f3d78de5c3f8dce9536ca9ecb2ec5c69740c8cbf'
INVENTORY_SHA='82a729772dc14b1c5e80e31fc4038a95448a68ad1a19941f4684e7d75412923c'
PLAN=(('serial-z-r1','minus_z'),('serial-z-r2','minus_z'),('serial-x-control','x'))


def verified_dependencies(inventory,binary_sha):
    if reference.sha(inventory)!=INVENTORY_SHA:
        raise ValueError('accepted dependency inventory fingerprint mismatch')
    dependencies=json.loads(inventory.read_text())
    if dependencies['binary']['sha256']!=binary_sha:
        raise ValueError('accepted inventory binary mismatch')
    for name,info in dependencies['dynamic_libraries'].items():
        if str(Path(name).resolve())!=info['resolved_path'] or reference.sha(Path(name))!=info['sha256']:
            raise ValueError('accepted dynamic library fingerprint mismatch: '+name)
    return dependencies


def run(args):
    if sys.platform!='darwin' or platform.machine()!='arm64':
        raise ValueError('native arm64 macOS required; emulation is excluded')
    if reference.sha(Path(reference.__file__))!=HELPER_SHA:
        raise ValueError('frozen G13 helper fingerprint changed')
    if reference.sha(args.binary)!=args.binary_sha256 or reference.sha(args.build_receipt)!=args.build_receipt_sha256:
        raise ValueError('accepted build fingerprint mismatch')
    inventory=args.build_receipt.parent/'build-inventory.json'
    dependencies=verified_dependencies(inventory,args.binary_sha256)
    kind=subprocess.run(['/usr/bin/file','--brief',str(args.binary)],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
    if 'Mach-O' not in kind or 'arm64' not in kind:
        raise ValueError('accepted binary is not native arm64 Mach-O')
    texts=reference.inputs(args.input)
    args.deadline=min(args.deadline,time.time()+2700)
    reference.remaining(args,1200)
    args.output.mkdir(parents=True,exist_ok=False)
    provenance=args.output/'provenance';provenance.mkdir()
    shutil.copyfile(__file__,provenance/'reference.py')
    shutil.copyfile(args.build_receipt,provenance/'accepted-build.json')
    shutil.copyfile(inventory,provenance/'accepted-build-inventory.json')
    binary_dir=args.output/'bin';binary_dir.mkdir()
    shutil.copy2(args.binary,binary_dir/'ccx')
    os.environ['PATH']=str(binary_dir.resolve())+os.pathsep+os.environ['PATH']
    original=args.output/'original-rejected';original.mkdir()
    for name in reference.INPUTS:
        shutil.copyfile(args.input/name,original/name)
    reference.inputs(original)
    report=dict(classification='native_arm64_macOS_CPU_reference_pilot_not_G13_Linux_GPU_qualification',
                native_binary_sha256=args.binary_sha256,build_receipt_sha256=args.build_receipt_sha256,
                build_inventory_sha256=INVENTORY_SHA,dynamic_libraries=dependencies['dynamic_libraries'],
                helper_sha256=HELPER_SHA,source_sha256=reference.SOURCES,original_sha256=reference.INPUTS,
                script_sha256=reference.sha(Path(__file__)),platform=platform.platform(),
                software=dict(python=sys.version.split()[0],numpy=np.__version__,scipy=scipy.__version__),
                deadline=args.deadline,CCX_timeout_seconds=1200,CPU_CG_timeout_seconds=900,
                whole_pilot_limit_seconds=2700,threads=1,memory_limit_enforced=False,
                expected_memory_scope='One 196914-node original B1.5 case; no finer geometry; anticipated below 16GiB, not a measured peak.',
                rows=[],references={},complete=False,error=None,original_failure_preserved=True,
                dynamic_libraries_verified_before=True,dynamic_libraries_verified_after=False,
                CUDA_executed=False,G13_Linux_reference_promoted=False,manufacturing_authorized=False,engine_start_authorized=False)
    reference.publish(args.output/'identity.json',{k:v for k,v in report.items() if k not in ('rows','references','error')})
    signal.setitimer(signal.ITIMER_REAL,max(1,args.deadline-time.time()))
    solutions={}
    try:
        for label,name in PLAN:
            case=args.output/label;case.mkdir()
            shutil.copyfile(original/(name+'.inp'),case/(name+'.inp'))
            print(json.dumps({'stage':'native_CCX','case':label}),flush=True)
            direct=reference.ccx(case,name,1,reference.remaining(args,1200))
            if not solutions:
                matrix_case=args.output/'matrix';matrix_case.mkdir()
                points,_,support=g9.deck(texts['x'])
                prefix=texts['x'].split('*STEP\n')[0]
                with (matrix_case/'matrix.inp').open('x') as stream:
                    stream.write(prefix.replace('*SOLID SECTION','*DENSITY\n2.7e-9\n*SOLID SECTION')
                                 +'*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
                export=reference.ccx(matrix_case,'matrix',1,reference.remaining(args,1200))
                matrix,mapping=bench.read_matrix(matrix_case/'matrix.sti',matrix_case/'matrix.dof',points,support)
                matrix_hashes={p.name:reference.sha(p) for p in matrix_case.iterdir() if p.is_file()}
                for direction in ('x','minus_z'):
                    rhs=g9.rhs_for(mapping,g9.deck(texts[direction])[1])
                    print(json.dumps({'stage':'SciPy_FP64_CG','direction':direction}),flush=True)
                    u,timing=bench.solve(matrix,rhs,'cpu',max_seconds=reference.remaining(args,900))
                    residual=float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
                    solutions[direction]=dict(u=u,rhs=rhs,passed=bool(timing['info']==0 and np.isfinite(u).all() and residual<=1e-8))
                    proof=dict(direction=direction,solver=timing,relative_residual=residual,passed=solutions[direction]['passed'],
                               matrix_sha256=matrix_hashes,matrix_export=export,
                               original_rejected_comparison=reference.compare(original,direction,matrix,mapping,solutions[direction],rhs,points,support))
                    reference.publish(matrix_case/(direction+'-reference.json'),proof)
                    report['references'][direction]=proof
                if not all(s['passed'] for s in solutions.values()):
                    raise ValueError('native CPU reference fails unchanged algebraic gate')
            row=dict(id=label,direction=name,threads=1,direct=direct,
                     **reference.compare(case,name,matrix,mapping,solutions[name],solutions[name]['rhs'],points,support))
            row['hashes']={p.name:reference.sha(p) for p in case.iterdir() if p.is_file()}
            reference.publish(case/'case.json',row)
            report['rows'].append(row)
            reference.publish(args.output/('checkpoint-%02d.json'%len(report['rows'])),report)
            print(json.dumps({'case':label,'numerical_passed':row['passed']}),flush=True)
        verified_dependencies(inventory,args.binary_sha256)
        if reference.sha(binary_dir/'ccx')!=args.binary_sha256:
            raise ValueError('executed native binary fingerprint changed')
        report['dynamic_libraries_verified_after']=True
        report['complete']=len(report['rows'])==3
        report['all_native_CPU_comparisons_passed']=report['complete'] and all(r['passed'] for r in report['rows'])
    except BaseException as exc:
        report['error']=type(exc).__name__+': '+str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        report.update(finished_epoch=time.time(),controller_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,
                      maximum_child_RSS_MiB_not_sum=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024**2)
        reference.publish(args.output/'summary-0001.json',report)
        print(json.dumps({'complete':report['complete'],'error':report['error']}),flush=True)
    return 0 if report.get('all_native_CPU_comparisons_passed') else 2


if __name__=='__main__':
    def interrupted(signum,frame):
        raise TimeoutError('native Mac pilot interrupted or 45-minute deadline reached')
    for sig in (signal.SIGTERM,signal.SIGALRM):
        signal.signal(sig,interrupted)
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('input','output','binary','build-receipt'):
        parser.add_argument('--'+flag,type=Path,required=True)
    for flag in ('binary-sha256','build-receipt-sha256'):
        parser.add_argument('--'+flag,required=True)
    parser.add_argument('--deadline',type=float,required=True)
    raise SystemExit(run(parser.parse_args()))
