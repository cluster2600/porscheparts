"""Build pinned CGAL locally on Linux; no sudo or system installation."""
import argparse,hashlib,json,os,re,shutil,subprocess,tarfile,urllib.request,uuid
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
CGAL_SHA='7d8580bb2283e083ce53380d412d3a5f7c038b058b9cc4fe0984edeae41c8ed0'
MPFR_SHA='ce0b35d8bb458c4068473d3eb88f93198d7b4e0d8bdd202e0173253f2d781e56'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def record(prefix,audit_python):
    archive=prefix/'downloads/CGAL-6.1.3.tar.xz';deb=prefix/'downloads/libmpfr-dev_4.2.2-3_amd64.deb'
    assert sha(archive)==CGAL_SHA and sha(deb)==MPFR_SHA
    cgal=prefix/'src/CGAL-6.1.3';binary=prefix/'build/carrier_autorefine'
    module_code="""import hashlib,json,pathlib,sys,numpy,igl
from importlib.metadata import version
files=[pathlib.Path(sys.executable).resolve(),pathlib.Path(numpy.__file__),pathlib.Path(igl.__file__)]
files+=list(pathlib.Path(igl.__file__).parent.glob('*.so'))
files+=list(pathlib.Path(numpy.__file__).parent.glob('_core/_multiarray_umath*.so'))
print(json.dumps({'python':sys.version,'numpy':numpy.__version__,'libigl':version('libigl'),'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}))"""
    audit=json.loads(subprocess.run([str(audit_python),'-c',module_code],capture_output=True,text=True,check=True).stdout)
    assert audit['libigl']=='2.6.3'
    ldd=subprocess.run(['ldd',str(binary)],capture_output=True,text=True,check=True).stdout
    runtime_files=dict(audit['files'])
    for line in ldd.splitlines():
        paths=re.findall(r'(/[^\s()]+)',line)
        for name in paths:
            path=Path(name)
            if path.is_file():runtime_files[str(path.resolve())]=sha(path.resolve())
    headers=['CGAL/version.h','CGAL/Polygon_mesh_processing/autorefinement.h',
      'CGAL/Polygon_mesh_processing/internal/triangle_soup_snap_rounding.h']
    receipt={'CGAL_version':'6.1.3','CGAL_commit':'109ed62eeaa7e38eb383e9444700e6ff7bd4c449',
      'CGAL_archive_sha256':CGAL_SHA,'CGAL_release_url':'https://github.com/CGAL/cgal/releases/download/v6.1.3/CGAL-6.1.3.tar.xz',
      'CGAL_header_sha256':{name:sha(cgal/'include'/name) for name in headers},
      'MPFR_deb_sha256':MPFR_SHA,'MPFR_version':'4.2.2-3','MPFR_installation':'Local dpkg-deb extraction only; system packages unchanged',
      'binary_sha256':sha(binary),'adapter_source_sha256':sha(prefix/'autorefine.cpp'),
      'source_files_sha256':{name:sha(prefix/name) for name in ['autorefine.cpp','CMakeLists.txt','worker.py','run.py','setup.py']},
      'runtime_files_sha256':runtime_files,'audit_python':str(audit_python),'audit_runtime':audit,
      'compiler':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],
      'system_development_packages':subprocess.run(['dpkg-query','-W','libboost-dev','libgmp-dev'],capture_output=True,text=True,check=True).stdout,
      'cmake_release_flags':'-O1 -DNDEBUG','licenses':{'CGAL_autorefine':'GPL-3.0-or-later OR commercial','CGAL_core':'LGPL-3.0-or-later OR commercial','MPFR':'LGPL-3.0-or-later'},
      'snap_geometry_parameters':'Required per job, never selected by the installer',
      'source_url':'https://github.com/CGAL/cgal/tree/109ed62eeaa7e38eb383e9444700e6ff7bd4c449',
      'known_topology_constraint':'autorefine removes intersections but may retain/create non-manifold contact; separate topology guard is mandatory (#9192)'}
    (prefix/'installation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--audit-python',required=True,type=Path)
    args=p.parse_args();prefix=args.prefix.resolve();assert not prefix.exists();assert args.audit_python.is_file()
    prefix.mkdir(parents=True)
    for name in ['downloads','src','build','jobs','sysroot']:(prefix/name).mkdir()
    for name in ['autorefine.cpp','CMakeLists.txt','worker.py','run.py','setup.py']:shutil.copyfile(SOURCE/name,prefix/name)
    downloads=prefix/'downloads'
    url='https://github.com/CGAL/cgal/releases/download/v6.1.3/CGAL-6.1.3.tar.xz'
    with urllib.request.urlopen(url,timeout=120) as response,(downloads/'CGAL-6.1.3.tar.xz').open('wb') as stream:shutil.copyfileobj(response,stream)
    assert sha(downloads/'CGAL-6.1.3.tar.xz')==CGAL_SHA
    subprocess.run(['apt-get','download','libmpfr-dev=4.2.2-3'],cwd=downloads,check=True,timeout=120)
    assert sha(downloads/'libmpfr-dev_4.2.2-3_amd64.deb')==MPFR_SHA
    subprocess.run(['dpkg-deb','-x',str(downloads/'libmpfr-dev_4.2.2-3_amd64.deb'),str(prefix/'sysroot')],check=True)
    with tarfile.open(downloads/'CGAL-6.1.3.tar.xz') as archive:archive.extractall(prefix/'src',filter='data')
    configure=['cmake','-S',str(prefix),'-B',str(prefix/'build'),'-DCGAL_DIR='+str(prefix/'src/CGAL-6.1.3/lib/cmake/CGAL'),
      '-DMPFR_INCLUDE_DIR='+str(prefix/'sysroot/usr/include'),'-DMPFR_LIBRARIES=/usr/lib/x86_64-linux-gnu/libmpfr.so.6',
      '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG']
    with (prefix/'configure.log').open('w') as log:subprocess.run(configure,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    unit='carrier-cgal-setup-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G',
      '-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610','timeout','--kill-after=10s','600',
      'cmake','--build',str(prefix/'build'),'--parallel','1']
    try:
        with (prefix/'compile.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=630)
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
    # Preserve the venv entrypoint; resolving its symlink would discard its
    # site-packages and invoke the bare system interpreter instead.
    result=record(prefix,args.audit_python.absolute());print(json.dumps({'prefix':str(prefix),'binary_sha256':result['binary_sha256']}))

if __name__=='__main__':main()
