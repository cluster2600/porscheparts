"""Build pinned Linux CCX/SPOOLES privately; preserve installed runtime libraries."""
import argparse
import json
from pathlib import Path
import platform
import re
import resource
import subprocess
import time
import build_macos_ccx as sources
import run_local_ccx_serial as serial

UPSTREAM_MANIFEST='4f47455622daded6cdd584f31a25c591ee37c54a134db79ca8ef25604db0282b'


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--sources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=int,default=1800);a=p.parse_args()
    if a.output.exists() or not 1<=a.seconds<=1800 or platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('Fresh bounded native Linux x86-64 build required')
    source=a.sources.resolve();manifest=source/'upstream/source-manifest.json'
    if sources.sha(manifest)!=UPSTREAM_MANIFEST:raise ValueError('Pinned upstream patch/test manifest differs')
    for row in json.loads(manifest.read_text()):
        if sources.sha(source/'upstream'/row['repository'].split('/')[-1]/row['path'])!=row['sha256']:raise ValueError('Pinned upstream recipe input differs')
    archives=['calculix-ccx_2.21.orig.tar.bz2','calculix-ccx_2.21-1.debian.tar.xz','spooles.2.2.tgz']
    for name in archives:
        if sources.sha(source/name)!=sources.ASSETS[name][1]:raise ValueError('Pinned original source archive differs')
    fc=Path('/usr/bin/gfortran-13');cc=Path('/usr/bin/gcc')
    versions={str(x):subprocess.check_output([str(x),'--version'],text=True)for x in [cc,fc]}
    if any('13.'not in text.splitlines()[0]for text in versions.values()):raise ValueError('Existing retained GCC/GFortran 13 toolchain required')
    libraries=subprocess.check_output(['ldd','/usr/bin/ccx'],text=True);paths={Path(x).resolve()for x in re.findall(r'/[^\s()]+',libraries)};identities={str(x):sources.sha(x)for x in paths}
    a.output.mkdir(parents=True);root=a.output.resolve();deadline=time.monotonic()+a.seconds;commands=[];status='refused';detail=None
    def run(argv,cwd,name,seconds,stdin=None):
        remaining=int(deadline-time.monotonic())
        if remaining<1:raise TimeoutError('Original build wall budget exhausted')
        def bounds():resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
        started=time.monotonic();timeout=False
        with(root/(name+'.stdout')).open('w')as out,(root/(name+'.stderr')).open('w')as err:
            child=subprocess.Popen(list(map(str,argv)),cwd=cwd,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=bounds)
            try:child.communicate(input=stdin,timeout=min(seconds,remaining))
            except subprocess.TimeoutExpired:timeout=True
            finally:serial.stop_and_reap(child)
        row=dict(argv=list(map(str,argv)),cwd=str(cwd),returncode=124 if timeout else child.returncode,process_reaped=child.returncode is not None,elapsed_seconds=time.monotonic()-started,stdout_sha256=sources.sha(root/(name+'.stdout')),stderr_sha256=sources.sha(root/(name+'.stderr')));commands.append(row);(root/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
        if row['returncode']:raise RuntimeError('Bounded build/test step refused: '+name)
    recipe=source/'upstream/spooles-feedstock/recipe';spool=root/'spooles';calc=root/'CalculiX/ccx_2.21/src'
    (root/'plan.json').write_text(json.dumps(dict(source_archives={n:sources.ASSETS[n][1]for n in archives},upstream_manifest_sha256=UPSTREAM_MANIFEST,source_sha256={str(x):sources.sha(x)for x in [Path(__file__),Path(sources.__file__),Path(serial.__file__)]},compiler_versions=versions,installed_runtime_library_sha256=identities,wall_limit_seconds=a.seconds,per_child_virtual_memory_GiB=4,make_parallel_jobs=2,packages_installed=False),indent=2)+'\n')
    try:
        sources.unpack(source/archives[0],root);sources.unpack(source/archives[1],root/'CalculiX');sources.unpack(source/archives[2],spool)
        for name in(root/'CalculiX/debian/patches/series').read_text().splitlines():
            if Path(name).name!=name:raise ValueError('Relative Debian patch basename required')
            run(['patch','-p1','--batch','--forward'],root/'CalculiX','debian-'+name,30,(root/'CalculiX/debian/patches'/name).read_bytes())
        patches=sorted((recipe/'patches').glob('000*.patch'))
        if len(patches)!=6:raise ValueError('Complete six-patch SPOOLES series required')
        for patch in patches:run(['patch','-p1','--batch','--forward'],spool,patch.stem,30,patch.read_bytes())
        edits=[]
        for name,old,new in [('Make.inc','/usr/lang-4.0/bin/cc','/usr/bin/gcc'),('Tree/src/makeGlobalLib','drawTree.c','tree.c'),('ETree/src/transform.c','IVinit(nfront, NULL)','IVinit(nfront, 0)')]:
            path=spool/name;text=path.read_text()
            if old not in text:raise ValueError('Expected source compatibility edit absent')
            before=sources.sha(path);path.write_text(text.replace(old,new));edits.append(dict(path=name,before_sha256=before,after_sha256=sources.sha(path)))
        (root/'compatibility-edits.json').write_text(json.dumps(edits,indent=2)+'\n')
        if not(spool/'Utilities/SPOOLESatomic.h').is_file():raise ValueError('Patched atomic-publication header required')
        run(['make','lib'],spool,'spooles-serial-build',600);run(['make'],spool/'MT/src','spooles-mt-build',300)
        test=root/'test-solve';run([cc,'-O2','-I',spool,recipe/'test_solve.c',spool/'MT/src/spoolesMT.a',spool/'spooles.a','-lpthread','-lm','-o',test],root,'known-solution-test-build',60)
        run([test,'500','8','20','2700'],root,'known-solution-test',2730)
        if not re.search(r'0/500 iterations wrong,', (root/'known-solution-test.stdout').read_text()):raise ValueError('All 500 known-solution repetitions required')
        runtime=[Path('/usr/lib/x86_64-linux-gnu')/name for name in ['libarpack.so.2','liblapack.so.3','libblas.so.3']]
        cflags='CFLAGS=-O2 -I'+str(spool)+' -DARCH="Linux" -DSPOOLES -DARPACK -DMATRIXSTORAGE -DUSE_MT=1';libs='LIBS='+' '.join(map(str,[spool/'MT/src/spoolesMT.a',spool/'spooles.a',*runtime]))+' -lpthread -lm'
        run(['make','-j2','CC='+str(cc),'FC='+str(fc),cflags,'FFLAGS=-O2 -fallow-argument-mismatch -frecursive -std=legacy',libs],calc,'ccx-build',900)
        binary=calc/'ccx_2.21';(root/'linked-libraries.txt').write_text(subprocess.check_output(['ldd',str(binary)],text=True))
        if identities!={str(x):sources.sha(x)for x in paths}:raise ValueError('Installed runtime library identity changed')
        (root/'binary-identity.json').write_text(json.dumps(dict(native_binary_sha256=sources.sha(binary),binary_path=str(binary),serial_library_sha256=sources.sha(spool/'spooles.a'),mt_library_sha256=sources.sha(spool/'MT/src/spoolesMT.a'),known_solution_test_binary_sha256=sources.sha(test),carrier_runtime_qualified=False,installed_runtime_libraries_unchanged=True),indent=2)+'\n');status='compiled_and_500_low_level_repeats_passed'
    except Exception as error:detail=type(error).__name__+': '+str(error);raise
    finally:(root/'build-terminal.json').write_text(json.dumps(dict(status=status,detail=detail,commands=commands,source_inputs_unchanged=all(sources.sha(source/n)==sources.ASSETS[n][1]for n in archives)),indent=2)+'\n')


if __name__=='__main__':main()
