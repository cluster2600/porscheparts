"""Build pinned CalculiX 2.21 privately on Apple Silicon, including Debian's hash fix."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tarfile
import time
from run_local_ccx_serial import stop_and_reap

UBUNTU='https://archive.ubuntu.com/ubuntu/pool/universe/'
ASSETS={
    'calculix-ccx_2.21.orig.tar.bz2':(UBUNTU+'c/calculix-ccx/calculix-ccx_2.21.orig.tar.bz2','51d229aee320cf685216d360f7c04f9a57af0148fbe840483a964c86c315da82','.'),
    'calculix-ccx_2.21-1.debian.tar.xz':(UBUNTU+'c/calculix-ccx/calculix-ccx_2.21-1.debian.tar.xz','6c2a934b66491c9e916cbf6328167d417f7e985b380e200facf92c3e953d255f','CalculiX'),
    'spooles.2.2.tgz':('https://www.netlib.org/linalg/spooles/spooles.2.2.tgz','a84559a0e987a1e423055ef4fdf3035d55b65bbe4bf915efaa1a35bef7f8c5dd','spooles'),
    'spooles_2.2-14.debian.tar.xz':(UBUNTU+'s/spooles/spooles_2.2-14.debian.tar.xz','de4dbe2ef28320d1b58a1e5ca2b0bccd413039e8b769f7ba97658d0bf34900b4','spooles-patches')}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(path,destination):
    with tarfile.open(path)as archive:
        for item in archive.getmembers():
            name=Path(item.name)
            if name.is_absolute()or'..'in name.parts or not(item.isfile()or item.isdir()):
                raise ValueError('Regular relative source members required')
        destination.mkdir(parents=True,exist_ok=True)
        archive.extractall(destination)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists()or platform.system()!='Darwin'or platform.machine()!='arm64':raise ValueError('Fresh native Apple Silicon build required')
    compiler=Path('/opt/homebrew/bin/gfortran');pkg=Path('/opt/homebrew/bin/pkg-config')
    version=subprocess.check_output([str(compiler),'--version'],text=True)
    arpack_version=subprocess.check_output([str(pkg),'--modversion','arpack'],text=True).strip()
    if'16.2.0'not in version or arpack_version!='3.9.1':raise ValueError('Retained GCC 16.2.0 and ARPACK 3.9.1 toolchain required')
    libs=subprocess.check_output([str(pkg),'--libs','arpack'],text=True).split()
    a.output.mkdir(parents=True);root=a.output.resolve();records=[]
    (root/'toolchain.json').write_text(json.dumps(dict(fortran_version=version,arpack_version=arpack_version,arpack_link_flags=libs,platform=platform.platform()),indent=2)+'\n')
    for name,(url,digest,directory)in ASSETS.items():
        path=root/name
        subprocess.run(['/usr/bin/curl','-fL','--max-time','60','--silent','--show-error',url,'-o',str(path)],check=True)
        if sha(path)!=digest:raise ValueError('Pinned source archive differs: '+name)
        unpack(path,root/directory)
    (root/'source-assets.json').write_text(json.dumps(ASSETS,indent=2)+'\n')
    for name in(root/'CalculiX/debian/patches/series').read_text().splitlines():
        with(root/'CalculiX/debian/patches'/name).open('rb')as stream:
            subprocess.run(['patch','-d',str(root/'CalculiX'),'-p1'],stdin=stream,check=True,stdout=subprocess.DEVNULL)
    changes=[]
    for name,old,new in [
        ('Make.inc','/usr/lang-4.0/bin/cc','/usr/bin/clang -Wno-error=implicit-function-declaration -Wno-error=int-conversion'),
        ('Tree/src/makeGlobalLib','drawTree.c','tree.c'),
        ('ETree/src/transform.c','IVinit(nfront, NULL)','IVinit(nfront, 0)')]:
        path=root/'spooles'/name;text=path.read_text()
        if old not in text:raise ValueError('Expected source compatibility edit absent')
        before=sha(path);path.write_text(text.replace(old,new));changes.append(dict(path=name,before_sha256=before,after_sha256=sha(path)))
    patch=root/'spooles-patches/debian/patches/I2Ohash-64bit.patch'
    with patch.open('rb')as stream:subprocess.run(['patch','-d',str(root/'spooles'),'-p1'],stdin=stream,check=True,stdout=subprocess.DEVNULL)
    (root/'source-edits.json').write_text(json.dumps(dict(compatibility=changes,official_hash_patch_sha256=sha(patch)),indent=2)+'\n')
    commands=[['make','-C',str(root/'spooles'),'lib'],['make','-C',str(root/'spooles/MT/src'),'makeLib'],
        ['make','-C',str(root/'CalculiX/ccx_2.21/src'),'-j2','CC=/usr/bin/clang','FC='+str(compiler),
        'CFLAGS=-O2 -I'+str(root/'spooles')+' -DARCH="Linux" -DSPOOLES -DARPACK -DMATRIXSTORAGE -DUSE_MT=1',
        'FFLAGS=-O2 -fallow-argument-mismatch -frecursive -std=legacy',
        'LIBS='+str(root/'spooles/spooles.a')+' '+' '.join(libs)+' -framework Accelerate -lpthread -lm']]
    (root/'build-plan.json').write_text(json.dumps(dict(commands=commands,per_step_wall_seconds=600,source_sha256=sha(Path(__file__))),indent=2)+'\n')
    for i,command in enumerate(commands):
        start=time.monotonic();timeout=False
        with(root/(str(i)+'-build.stdout')).open('w')as stdout,(root/(str(i)+'-build.stderr')).open('w')as stderr:
            child=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
            try:child.wait(timeout=600)
            except subprocess.TimeoutExpired:timeout=True
            finally:stop_and_reap(child)
        records.append(dict(step=i,returncode=child.returncode,outer_timeout=timeout,process_reaped=True,seconds=time.monotonic()-start))
        (root/'build-progress.json').write_text(json.dumps(records,indent=2)+'\n')
        if timeout or child.returncode:raise RuntimeError('Native build step refused; logs retained')
    binary=root/'CalculiX/ccx_2.21/src/ccx_2.21'
    report=dict(status='native_CalculiX_2_21_build_completed_numeric_qualification_pending',steps=records,
        binary=str(binary),binary_sha256=sha(binary),source_sha256=sha(Path(__file__)),numeric_qualification=False)
    (root/'build-terminal.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
