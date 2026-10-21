"""Install the pinned experimental CGAL soup adapter in a fresh Linux prefix."""
import argparse,hashlib,json,re,shutil,subprocess,tarfile,uuid
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
PIN='b4e8c1887ce6a0abeb618634125e5cfcd301ce16'
ARCHIVE_SHA='1a5c2e9e3aa2b5e699536135ea7c1b0c46cde3343da9347720ad068632019a7f'
API_SHA='15ac79840d22479570d0284fb7b4dc5b1b508ced0f3d76c2fe817e2d84f4d69d'
FILES=['soup_boolean.cpp','CMakeLists.txt','worker.py','run.py','setup.py']
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--support-runtime',type=Path,required=True)
    p.add_argument('--audit-python',type=Path,required=True);args=p.parse_args()
    root=args.prefix.resolve();support=args.support_runtime.resolve();archive=args.archive.resolve()
    assert not root.exists() and sha(archive)==ARCHIVE_SHA
    assert args.audit_python.is_file(), 'Explicit audit Python does not exist'
    support_receipt=support/'installation-receipt.json';base=json.loads(support_receipt.read_text())
    assert base['CGAL_commit']=='109ed62eeaa7e38eb383e9444700e6ff7bd4c449'
    assert all(sha(path)==value for path,value in base['runtime_files_sha256'].items())
    mpfr_header=support/'sysroot/usr/include/mpfr.h';mpfr_header_sha=sha(mpfr_header)
    root.mkdir(parents=True);(root/'jobs').mkdir();(root/'src').mkdir()
    for name in FILES:shutil.copyfile(SOURCE/name,root/name)
    with tarfile.open(archive) as tar:tar.extractall(root/'src',filter='data')
    cgal=root/'src'/('cgal-'+PIN)
    api=cgal/'PMP_Boolean_operations/include/CGAL/Polygon_mesh_processing/triangle_soup_boolean_operations_3.h'
    assert sha(api)==API_SHA
    command=['cmake','-S',str(root),'-B',str(root/'build'),'-DCGAL_DIR='+str(cgal),
      '-DMPFR_INCLUDE_DIR='+str(mpfr_header.parent),'-DMPFR_LIBRARIES=/usr/lib/x86_64-linux-gnu/libmpfr.so.6',
      '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1']
    with (root/'configure.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    unit='carrier-experimental-soup-setup-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G',
      '-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610','timeout','--kill-after=10s','600',
      'cmake','--build',str(root/'build'),'--parallel','1']
    code=None
    try:
        with (root/'compile.log').open('w') as log:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=630).returncode
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
    assert code==0, 'Compilation failed; preserve compile.log and prefix'
    binary=root/'build/carrier_soup_boolean'
    audit_code='''import hashlib,json,pathlib,sys,numpy,igl
from importlib.metadata import version
files=[pathlib.Path(sys.executable).resolve(),pathlib.Path(numpy.__file__),pathlib.Path(igl.__file__)]
files+=list(pathlib.Path(igl.__file__).parent.glob('*.so'))
files+=list(pathlib.Path(numpy.__file__).parent.glob('_core/_multiarray_umath*.so'))
print(json.dumps(dict(python=sys.version,numpy=numpy.__version__,libigl=version('libigl'),files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})))'''
    audit=json.loads(subprocess.run([str(args.audit_python.absolute()),'-c',audit_code],
      capture_output=True,text=True,check=True).stdout)
    assert audit['libigl']=='2.6.3'
    libraries=dict(audit['files'])
    for line in subprocess.run(['ldd',str(binary)],capture_output=True,text=True,check=True).stdout.splitlines():
        for name in re.findall(r'(/[^\s()]+)',line):
            path=Path(name)
            if path.is_file():libraries[str(path.resolve())]=sha(path.resolve())
    dependencies=root/'build/CMakeFiles/carrier_soup_boolean.dir/soup_boolean.cpp.o.d'
    header_paths=dependencies.read_text().replace('\\\n',' ').split()[1:]
    used_headers={str(Path(path).resolve()):sha(path) for path in header_paths if Path(path).is_file()}
    receipt={'status':'installed','experimental':True,'CGAL_commit':PIN,'CGAL_archive':str(archive),
      'CGAL_archive_sha256':ARCHIVE_SHA,'CGAL_archive_bytes':archive.stat().st_size,
      'CGAL_source_url':'https://github.com/sloriot/cgal/tree/'+PIN,
      'CGAL_archive_url':'https://codeload.github.com/sloriot/cgal/tar.gz/'+PIN,
      'upstream_PR':'https://github.com/CGAL/cgal/pull/9363','upstream_patch_applied':False,
      'API_header_sha256':sha(api),'binary_sha256':sha(binary),
      'source_files_sha256':{name:sha(root/name) for name in FILES},
      'compiled_dependency_files_sha256':used_headers,'runtime_files_sha256':libraries,
      'audit_python':str(args.audit_python.absolute()),'audit_runtime':audit,
      'support_runtime_receipt':str(support_receipt),'support_runtime_receipt_sha256':sha(support_receipt),
      'MPFR_header_sha256':mpfr_header_sha,'MPFR_header_path':str(mpfr_header),
      'compiler':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],
      'system_development_packages':subprocess.run(['dpkg-query','-W','libboost-dev','libgmp-dev'],capture_output=True,text=True,check=True).stdout,
      'cmake_release_flags':'-O1; CGAL assertions/preconditions remain enabled',
      'licenses':{'CGAL_soup_boolean_operations':'GPL-3.0-or-later OR commercial','CGAL_core':'LGPL-3.0-or-later OR commercial','MPFR':'LGPL-3.0-or-later'},
      'limits':{'compile_cpu':2,'compile_memory':'4G','compile_swap':0,'compile_timeout_seconds':600},
      'scope':'Unmerged experimental upstream API. Installation only; no carrier admission.'}
    assert sha(mpfr_header)==mpfr_header_sha and sha(archive)==ARCHIVE_SHA
    (root/'installation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'prefix':str(root),'status':receipt['status'],'binary_sha256':receipt['binary_sha256']}))

if __name__=='__main__':main()
