"""Compile exact-centroid parent queries using an explicit immutable CGAL soup runtime."""
import argparse,hashlib,json,re,shutil,subprocess,uuid
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
PIN='b4e8c1887ce6a0abeb618634125e5cfcd301ce16'
FILES=['soup_boolean.cpp','CMakeLists.txt','worker.py','run.py','setup.py']
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path)
    p.add_argument('--boolean-runtime',type=Path,required=True);args=p.parse_args()
    root=args.prefix.resolve();base_root=args.boolean_runtime.resolve();manifest=base_root/'installation-receipt.json'
    assert not root.exists();base=json.loads(manifest.read_text());assert base['CGAL_commit']==PIN
    assert sha(base_root/'build/carrier_soup_boolean')==base['binary_sha256']
    assert all(sha(base_root/name)==value for name,value in base['source_files_sha256'].items())
    dependencies={**base['runtime_files_sha256'],**base['compiled_dependency_files_sha256']}
    assert all(sha(path)==value for path,value in dependencies.items())
    before={str(manifest):sha(manifest),**dependencies}
    cgal=base_root/'src'/('cgal-'+PIN);assert cgal.is_dir()
    archive=Path(base['CGAL_archive']);assert sha(archive)==base['CGAL_archive_sha256']
    root.mkdir(parents=True);(root/'jobs').mkdir()
    for name in FILES:shutil.copyfile(SOURCE/name,root/name)
    command=['cmake','-S',str(root),'-B',str(root/'build'),'-DCGAL_DIR='+str(cgal),
      '-DMPFR_INCLUDE_DIR='+str(Path(base['MPFR_header_path']).parent),'-DMPFR_LIBRARIES=/usr/lib/x86_64-linux-gnu/libmpfr.so.6',
      '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1']
    with (root/'configure.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    unit='carrier-exact-centroid-setup-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G',
      '-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610','timeout','--kill-after=10s','600',
      'cmake','--build',str(root/'build'),'--parallel','1']
    code=None
    try:
        with (root/'compile.log').open('w') as log:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=630).returncode
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
    assert code==0,'Compile failed; keep the prefix and logs'
    binary=root/'build/carrier_soup_boolean';libraries=dict(base['runtime_files_sha256'])
    for line in subprocess.run(['ldd',str(binary)],capture_output=True,text=True,check=True).stdout.splitlines():
        for name in re.findall(r'(/[^\s()]+)',line):
            path=Path(name)
            if path.is_file():libraries[str(path.resolve())]=sha(path.resolve())
    dependency_file=root/'build/CMakeFiles/carrier_soup_boolean.dir/soup_boolean.cpp.o.d'
    paths=dependency_file.read_text().replace('\\\n',' ').split()[1:]
    used={str(Path(path).resolve()):sha(path) for path in paths if Path(path).is_file()}
    result={**base,'binary_sha256':sha(binary),'source_files_sha256':{name:sha(root/name) for name in FILES},
      'compiled_dependency_files_sha256':used,'runtime_files_sha256':libraries,
      'boolean_runtime_receipt':str(manifest),'boolean_runtime_receipt_sha256':sha(manifest),
      'parent_candidate_query':'Exact Point_3 child centroid; unchanged exact three-vertex containment; all matching parent IDs retained',
      'geometry_checkpoint':'Only reads an explicit previously sealed exact/float checkpoint; CSG is never recomputed',
      'base_runtime_dependencies_unchanged':all(sha(path)==value for path,value in before.items()),
      'scope':'Independent finalization/audit of a sealed existing exact checkpoint; direct balanced rational volume reduction; no CSG or geometry modification.'}
    assert result['base_runtime_dependencies_unchanged']
    (root/'installation-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'prefix':str(root),'binary_sha256':result['binary_sha256'],'status':'installed'}))

if __name__=='__main__':main()
