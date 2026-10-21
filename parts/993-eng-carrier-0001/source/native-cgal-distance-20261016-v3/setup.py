"""Compile the exact distance adapter against a pinned existing CGAL installation."""
import argparse,hashlib,json,re,shutil,subprocess,uuid
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def record(prefix,cgal_runtime):
    original=cgal_runtime/'installation-receipt.json';base=json.loads(original.read_text())
    assert base['CGAL_commit']=='109ed62eeaa7e38eb383e9444700e6ff7bd4c449'
    assert all(sha(path)==value for path,value in base['runtime_files_sha256'].items())
    runtime_files=dict(base['runtime_files_sha256'])
    ldd=subprocess.run(['ldd',str(prefix/'build/carrier_exact_distance')],capture_output=True,text=True,check=True).stdout
    for line in ldd.splitlines():
        for name in re.findall(r'(/[^\s()]+)',line):
            path=Path(name)
            if path.is_file():runtime_files[str(path.resolve())]=sha(path.resolve())
    headers=['CGAL/AABB_tree.h','CGAL/AABB_traits_3.h','CGAL/AABB_triangle_primitive_3.h',
             'CGAL/AABB_segment_primitive_3.h','CGAL/squared_distance_3.h']
    result={'CGAL_version':base['CGAL_version'],'CGAL_commit':base['CGAL_commit'],
      'CGAL_installation_receipt':str(original),'CGAL_installation_receipt_sha256':sha(original),
      'CGAL_archive_sha256':base['CGAL_archive_sha256'],'CGAL_header_sha256':base['CGAL_header_sha256'],
      'MPFR_deb_sha256':base['MPFR_deb_sha256'],
      'licenses':{**base['licenses'],'CGAL_AABB_tree':'GPL-3.0-or-later OR commercial'},
      'compiler':base['compiler'],'cmake_release_flags':'-O1 -DNDEBUG',
      'audit_python':base['audit_python'],'runtime_files_sha256':runtime_files,
      'distance_header_sha256':{name:sha(cgal_runtime/'src/CGAL-6.1.3/include'/name) for name in headers},
      'source_files_sha256':{name:sha(prefix/name) for name in ['distance.cpp','CMakeLists.txt','run.py','worker.py','setup.py']},
      'binary_sha256':sha(prefix/'build/carrier_exact_distance'),
      'scope':'Exact Epeck/AABB measurement only; no geometry repair or snap construction'}
    (prefix/'installation-receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--cgal-runtime',required=True,type=Path)
    args=p.parse_args();prefix=args.prefix.resolve();cgal=args.cgal_runtime.resolve();assert not prefix.exists()
    base=json.loads((cgal/'installation-receipt.json').read_text());assert base['CGAL_commit']=='109ed62eeaa7e38eb383e9444700e6ff7bd4c449'
    for name,value in base['CGAL_header_sha256'].items():assert sha(cgal/'src/CGAL-6.1.3/include'/name)==value
    prefix.mkdir(parents=True);(prefix/'jobs').mkdir()
    for name in ['distance.cpp','CMakeLists.txt','run.py','worker.py','setup.py']:shutil.copyfile(SOURCE/name,prefix/name)
    command=['cmake','-S',str(prefix),'-B',str(prefix/'build'),'-DCGAL_DIR='+str(cgal/'src/CGAL-6.1.3/lib/cmake/CGAL'),
      '-DMPFR_INCLUDE_DIR='+str(cgal/'sysroot/usr/include'),'-DMPFR_LIBRARIES=/usr/lib/x86_64-linux-gnu/libmpfr.so.6',
      '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG']
    with (prefix/'configure.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    unit='carrier-exact-distance-setup-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0',
      '-p','TasksMax=128','-p','RuntimeMaxSec=610','timeout','--kill-after=10s','600','cmake','--build',str(prefix/'build'),'--parallel','1']
    try:
        with (prefix/'compile.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=630)
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
    receipt=record(prefix,cgal);print(json.dumps({'prefix':str(prefix),'binary_sha256':receipt['binary_sha256']}))
if __name__=='__main__':main()
