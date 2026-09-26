"""Prepared Linux x86_64 CCX build/reference qualification; no rental or fine solve."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
THREAD_ENV = {k:'1' for k in ('OMP_NUM_THREADS', 'CCX_NPROC_EQUATION_SOLVER', 'CCX_NPROC_STIFFNESS',
    'CCX_NPROC_RESULTS', 'NUMBER_OF_CPUS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}
ARCHIVES = ('ccx_2.21.src.tar.bz2', 'spooles.2.2.tgz', 'arpack-ng-3.9.1.tar.gz')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def publish(path, value):
    with path.open('x') as f: json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def inputs(repo):
    manifest = json.loads((HERE/'inputs.json').read_text())
    for name, expected in manifest['files_sha256'].items():
        path = (repo/name).resolve()
        if not path.is_relative_to(repo) or sha(path) != expected:
            raise ValueError('input fingerprint mismatch: '+name)
    return manifest


def extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            target = (destination/member.name).resolve()
            if (not target.is_relative_to(destination.resolve()) or not (member.isfile() or member.isdir())):
                raise ValueError('unsupported archive member: '+member.name)
        source.extractall(destination, members=members)


def replace(path, old, new, count):
    before = path.read_text()
    if before.count(old) != count: raise ValueError('unexpected source to patch: '+str(path))
    path.write_text(before.replace(old, new))
    return dict(path=str(path), before_sha256=hashlib.sha256(before.encode()).hexdigest(), after_sha256=sha(path), replacements=count)


def run(args):
    manifest = inputs(args.repo)
    if args.check:
        print(json.dumps(dict(inputs_verified=True, files=len(manifest['files_sha256']), executed=False))); return 0
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise ValueError('native Linux x86_64 required; never execute through Mac emulation')
    if args.deadline is None or args.deadline-time.time() < 300 or args.deadline-time.time() > 10800:
        raise ValueError('controller deadline must leave 300..10800 seconds')
    os.environ.update(THREAD_ENV)
    sys.path.insert(0, str(args.repo/'twins/m64-cylinder-head/source/fourvalve'))
    import numpy as np
    import scipy
    import g13_reference as reference
    if np.__version__ != '2.2.6' or scipy.__version__ != '1.14.1':
        raise ValueError('requires numpy 2.2.6 and scipy 1.14.1')
    g9, bench = reference.g9, reference.bench
    for tool in ('gcc', 'gfortran', 'cmake', 'make', 'ctest', 'patch', 'pkg-config', 'perl', 'ldd', 'ar'):
        if not shutil.which(tool): raise ValueError('missing prerequisite: '+tool)
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(classification='Linux_x86_64_CCX221_hashfix_build_and_reference_only', complete=False,
        error=None, build_passed=False, cube_passed=False, reference_passed=False, fine_solve_executed=False,
        mesh_convergence_qualified=False, manufacturing_authorized=False, engine_start_authorized=False,
        inputs_sha256=sha(HERE/'inputs.json'), source_sha256=sha(Path(__file__)), commands=[], references=[],
        image_reference_supplied_by_controller=args.image_ref, image_runtime_digest_verified=False,
        runtime=dict(platform=platform.platform(), architecture=platform.machine(), python=sys.version,
            numpy=np.__version__, scipy=scipy.__version__, thread_environment=THREAD_ENV,
            os_release=Path('/etc/os-release').read_text()), deadline_epoch=args.deadline)
    shutil.copyfile(__file__, args.output/'linux_job.py'); shutil.copyfile(HERE/'inputs.json', args.output/'inputs.json')
    def remaining(cap):
        seconds = min(cap, args.deadline-time.time()-30)
        if seconds <= 0: raise TimeoutError('qualification deadline reserve exhausted')
        return seconds
    def command(argv, label, cwd, cap=600):
        start = time.monotonic(); log = args.output/(label+'.log')
        with log.open('x') as f:
            process = subprocess.Popen(list(map(str, argv)), cwd=cwd, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
            try: process.wait(timeout=remaining(cap))
            finally:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                process.wait()
        report['commands'].append(dict(argv=list(map(str, argv)), cwd=str(cwd), returncode=process.returncode,
            seconds=time.monotonic()-start, log=log.name, log_sha256=sha(log)))
        if process.returncode: raise ValueError('command failed: '+label)
        return log.read_text()
    def ccx(case, name, cap=900):
        label=case.name+'-'+name
        text=command([binary, name], label, case, cap)
        if '*ERROR' in text or 'Job finished' not in text or 'CalculiX Version 2.21' not in text or set(map(int, re.findall(r'Using (?:up to )?(\d+) cpu\(s\)', text))) != {1}:
            raise ValueError('serial CCX completion failed: '+label)
    try:
        report['runtime']['gcc']=command(['gcc','--version'],'gcc-version',args.output)
        report['runtime']['gfortran']=command(['gfortran','--version'],'gfortran-version',args.output)
        report['runtime']['cmake']=command(['cmake','--version'],'cmake-version',args.output)
        if shutil.which('dpkg-query'):
            report['runtime']['debian_packages']=command(['dpkg-query','-W'], 'packages', args.output)
        libdir=command(['pkg-config','--variable=libdir','openblas'],'openblas-location',args.output).strip()
        blas=(Path(libdir)/'libopenblas.so').resolve()
        if not blas.is_file(): raise ValueError('OpenBLAS shared library not found')
        archive_root=args.repo/'work/m64-g13/native-ccx'
        extract(archive_root/ARCHIVES[0], args.output/'ccx-source')
        extract(archive_root/ARCHIVES[1], args.output/'spooles')
        extract(archive_root/ARCHIVES[2], args.output/'arpack-source')
        spooles=args.output/'spooles'; src=args.output/'ccx-source/CalculiX/ccx_2.21/src'
        changes=[replace(spooles/'Make.inc','/usr/lang-4.0/bin/cc','gcc',1),
            replace(spooles/'Tree/src/makeGlobalLib','drawTree.c','tree.c',1),
            replace(spooles/'ETree/src/transform.c','IVinit(nfront, NULL)','IVinit(nfront, 0)',3)]
        util=spooles/'I2Ohash/src/util.c'
        if sha(util) != '1121b2d3650fc103f6009188db5fe31ef7f579ab12682d306082a99469ed3a01':
            raise ValueError('original hash implementation differs')
        changes.append(replace(util,'loc  = (loc1*loc2) % hashtable->nlist ;',
            'loc  = (int) (((long long) loc1*loc2) % hashtable->nlist) ;',3))
        if sha(util) != '7f0cd7472afa3a2b411a36721aa79120d88234ac33241795c4706c532185b2f2':
            raise ValueError('three-line hashfix differs from qualified patch')
        recipe=(archive_root/'calculix-ccx-3f7bd193.rb').read_text()
        patch=args.output/'calculix-header.patch'; patch.write_text(recipe.split('__END__\n',1)[1])
        command(['patch','-p1','-i',patch], 'header-patch', src.parent.parent)
        report['source_changes']=changes
        report['compatibility_header_patch_sha256']=sha(patch)
        report['licenses']={'ccx':dict(declaration='GPL-2.0',file='ccx-source/CalculiX/ccx_2.21/src/ccx_2.21.c',sha256=sha(src/'ccx_2.21.c')),
            'spooles':dict(declaration='Public domain, no warranty',file='spooles/spooles.2.2.html',sha256=sha(spooles/'spooles.2.2.html')),
            'arpack-ng':dict(declaration='BSD',file='arpack-source/arpack-ng-3.9.1/COPYING',sha256=sha(args.output/'arpack-source/arpack-ng-3.9.1/COPYING'))}
        command(['make','lib'], 'spooles-build', spooles)
        command(['make','makeLib'], 'spooles-mt-build', spooles/'MT/src')
        arpack=args.output/'arpack-build'
        command(['cmake','-S',args.output/'arpack-source/arpack-ng-3.9.1','-B',arpack,
            '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_COMPILER=gcc','-DCMAKE_Fortran_COMPILER=gfortran',
            '-DBUILD_SHARED_LIBS=OFF','-DMPI=OFF','-DICB=OFF','-DTESTS=ON','-DEXAMPLES=OFF','-DINTERFACE64=OFF',
            '-DBLAS_LIBRARIES='+str(blas),'-DLAPACK_LIBRARIES='+str(blas)], 'arpack-configure', args.output)
        command(['cmake','--build',arpack,'-j','4'], 'arpack-build', args.output)
        command(['ctest','--output-on-failure'], 'arpack-tests', arpack)
        command(['make','-j','4','ccx_2.21','CC=gcc','FC=gfortran',
            'CFLAGS=-O2 -I'+str(spooles)+' -DARCH=Linux -DSPOOLES -DARPACK -DMATRIXSTORAGE -DUSE_MT=1',
            'FFLAGS=-O2 -fopenmp -cpp',
            'LIBS='+str(spooles/'spooles.a')+' '+str(arpack/'libarpack.a')+' '+str(blas)+' -lpthread -lm'], 'ccx-build', src, 1800)
        binary=src/'ccx_2.21'
        linkage=command(['ldd',binary],'binary-linkage',args.output)
        if 'not found' in linkage: raise ValueError('unresolved dynamic library')
        libraries={}
        for line in linkage.splitlines():
            fields=line.strip().split(); candidate=fields[2] if '=>' in fields else fields[0] if fields else ''
            if candidate.startswith('/') and Path(candidate).is_file(): libraries[str(Path(candidate).resolve())]=sha(Path(candidate))
        report.update(build_passed=True,binary_sha256=sha(binary),dynamic_libraries_sha256=libraries)
        smoke=args.output/'cube'; smoke.mkdir()
        for name in ('static','matrix'):
            shutil.copyfile(args.repo/'work/m64-g14/native-ccx-hashfix-v1/smoke'/(name+'.inp'),smoke/(name+'.inp')); ccx(smoke,name,120)
        points={1:(0.,0.,0.),2:(1.,0.,0.),3:(1.,1.,0.),4:(0.,1.,0.),5:(0.,0.,1.),6:(1.,0.,1.),7:(1.,1.,1.),8:(0.,1.,1.)}
        support=[1,4,5,8]; loaded=[2,3,6,7]
        u=bench.g8.vectors(smoke/'static.dat','displacements ('); rf=bench.g8.vectors(smoke/'static.dat','forces (')
        if set(u)!=set(points) or set(rf)!=set(support): raise ValueError('incomplete cube output')
        matrix,mapping=bench.read_matrix(smoke/'matrix.sti',smoke/'matrix.dof',points,support)
        rhs=np.array([250. if n in loaded and d==1 else 0. for n,d in mapping])
        solved,timing=bench.solve(matrix,rhs,'cpu',max_seconds=remaining(60))
        residual=float(np.linalg.norm(matrix@solved-rhs)/np.linalg.norm(rhs)); agreement=bench.comparison(matrix,rhs,mapping,solved,u)
        analytic=max(abs(u[n][0]/(1000/70000)-1) for n in loaded)
        equilibrium=float(np.linalg.norm(np.sum(list(rf.values()),axis=0)+[1000,0,0])/1000)
        cube_passed=bool(analytic<=1e-5 and equilibrium<=1e-4 and timing['info']==0 and residual<=1e-8
            and agreement['max_nodal_difference_over_max_reference_U']<=1e-4
            and agreement['printed_dat_relative_residual']<=agreement['printed_dat_rounding_residual_bound'])
        report['cube']=dict(passed=cube_passed,analytic_relative_error=analytic,force_balance_relative_error=equilibrium,
            relative_residual=residual,solver=timing,agreement=agreement)
        report['cube_passed']=cube_passed
        if not cube_passed: raise ValueError('analytic cube failed')
        original=args.repo/'work/m64-g13/native-fea/run-1'
        decks={'x':original/'serial-x-control/x.inp','minus_z':original/'serial-z-r1/minus_z.inp'}
        text=decks['x'].read_text(); points,_,support=g9.deck(text); prefix=text.split('*STEP\n')[0]
        if decks['minus_z'].read_text().split('*STEP\n')[0]!=prefix: raise ValueError('reference geometry differs')
        exported=args.output/'reference-matrix'; exported.mkdir()
        with (exported/'matrix.inp').open('x') as f:
            f.write(prefix.replace('*SOLID SECTION','*DENSITY\n2.7e-9\n*SOLID SECTION')+'*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
        ccx(exported,'matrix')
        matrix,mapping=bench.read_matrix(exported/'matrix.sti',exported/'matrix.dof',points,support)
        for label,name in (('serial-z-r1','minus_z'),('serial-z-r2','minus_z'),('serial-x-control','x')):
            case=args.output/label; case.mkdir(); shutil.copyfile(decks[name],case/(name+'.inp')); ccx(case,name)
            _,loads,fixed=g9.deck((case/(name+'.inp')).read_text())
            if fixed!=support: raise ValueError('reference support differs')
            rhs=g9.rhs_for(mapping,loads); solved,timing=bench.solve(matrix,rhs,'cpu',max_seconds=remaining(900))
            residual=float(np.linalg.norm(matrix@solved-rhs)/np.linalg.norm(rhs))
            compared=reference.compare(case,name,matrix,mapping,
                dict(u=solved,passed=bool(timing['info']==0 and np.isfinite(solved).all() and residual<=1e-8)),rhs,points,support)
            row=dict(id=label,direction=name,relative_residual=residual,solver=timing,**compared,
                hashes={p.name:sha(p) for p in sorted(case.iterdir()) if p.is_file()})
            publish(case/'case.json',row); report['references'].append(row)
            publish(args.output/('checkpoint-'+label+'.json'),report)
            if not row['passed']: raise ValueError('unchanged project reference gates failed: '+label)
        report['repeat_minus_z_DAT_identical']=sha(args.output/'serial-z-r1/minus_z.dat')==sha(args.output/'serial-z-r2/minus_z.dat')
        if inputs(args.repo)!=manifest or sha(binary)!=report['binary_sha256'] or any(sha(Path(p))!=h for p,h in libraries.items()):
            raise ValueError('inputs/runtime changed during qualification')
        report.update(reference_passed=True,complete=True)
    except BaseException as exc:
        report['error']=type(exc).__name__+': '+str(exc)
    finally:
        report['artifacts_sha256']={str(p.relative_to(args.output)):sha(p) for p in sorted(args.output.rglob('*'))
            if p.is_file() and not p.is_symlink()}
        publish(args.output/'summary.json',report)
    print(json.dumps({k:report[k] for k in ('complete','error','build_passed','cube_passed','reference_passed')}))
    return 0 if report['complete'] else 2


if __name__=='__main__':
    def interrupted(signum, frame):
        raise InterruptedError('Linux job interrupted by controller')
    signal.signal(signal.SIGTERM, interrupted)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--deadline',type=int); parser.add_argument('--image-ref',default='not-yet-supplied')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(); args.repo=args.repo.resolve(); args.output=args.output.resolve()
    if args.output==args.repo or not args.output.is_relative_to(HERE): parser.error('new output under linux512 required')
    raise SystemExit(run(args))
