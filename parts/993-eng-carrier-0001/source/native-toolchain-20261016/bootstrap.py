"""Cold Linux native bootstrap; explicit Python and exact software archive only."""
import argparse,hashlib,json,platform,shutil,subprocess,sys,urllib.request
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
SOURCES=SOURCE.parent
ARCHIVE_SHA='536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56'
FOLDERS=['native-pymesh-20261016','native-cgal-20261016','native-cgal-distance-20261016',
 'native-cgal-distance-20261016-v2','native-cgal-distance-20261016-v3',
 'native-cgal-dominance-20261016','native-pymesh-clip-20261016','native-toolchain-20261016']
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def audit_environment(prefix,python):
    """Install only the three already-used audit packages into a new own venv."""
    version=json.loads(subprocess.run([str(python),'-c','import sys,json;print(json.dumps(list(sys.version_info[:2])))'],capture_output=True,text=True,check=True).stdout)
    assert version==[3,12],'Pinned wheels require explicit CPython3.12'
    assert not prefix.exists();prefix.mkdir(parents=True);wheel_dir=prefix/'wheels';wheel_dir.mkdir()
    manifest=SOURCE/'wheels-linux-cp312-x86_64.json';wheels=json.loads(manifest.read_text())['wheels']
    for item in wheels:
        target=wheel_dir/item['filename']
        with urllib.request.urlopen(item['url'],timeout=120) as response,target.open('wb') as stream:shutil.copyfileobj(response,stream)
        assert sha(target)==item['sha256'],'Pinned wheel hash mismatch'
    lock=prefix/'requirements.txt';lock.write_text(''.join(f"{w['project']}=={w['version']} --hash=sha256:{w['sha256']}\n" for w in wheels))
    subprocess.run([str(python),'-m','venv',str(prefix/'venv')],check=True,timeout=120)
    audit_python=prefix/'venv/bin/python'
    with (prefix/'pip.log').open('w') as log:subprocess.run([str(audit_python),'-m','pip','install','--no-index','--no-deps','--require-hashes','--find-links',str(wheel_dir),'-r',str(lock)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    smoke="""import sys,json,hashlib,pathlib,numpy as np,scipy,igl,igl.predicates
from importlib.metadata import version
v=np.array([[0.,0,0],[1,0,0],[0,1,0]]);f=np.array([[0,1,2]],dtype=np.int64)
d,_,_=igl.point_mesh_squared_distance(np.array([[.25,.25,1.]]),v,f);assert d[0]==1.
_,pairs,_=igl.predicates.find_self_intersections(v,f,False);assert len(pairs)==0
assert np.__version__=='2.2.6' and scipy.__version__=='1.15.3' and version('libigl')=='2.6.3'
files=[pathlib.Path(sys.executable).resolve(),pathlib.Path(np.__file__),pathlib.Path(scipy.__file__),pathlib.Path(igl.__file__)]
files+=list(pathlib.Path(igl.__file__).parent.glob('*.so'));files+=list(pathlib.Path(np.__file__).parent.glob('_core/_multiarray_umath*.so'))
print(json.dumps({'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'libigl':version('libigl'),'smoke_pass':True,'files_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}))"""
    result=json.loads(subprocess.run([str(audit_python),'-c',smoke],capture_output=True,text=True,check=True,timeout=60).stdout)
    result.update(wheels=wheels,wheel_manifest_sha256=sha(manifest),audit_python=str(audit_python),base_python=str(python),base_python_sha256=sha(python.resolve()))
    (prefix/'installation-receipt.json').write_text(json.dumps(result,indent=2)+'\n');return audit_python

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--python',type=Path,required=True);p.add_argument('--rootfs-archive',type=Path,required=True);p.add_argument('--copy-rootfs-archive',action='store_true')
    args=p.parse_args();assert sys.platform=='linux' and platform.machine()=='x86_64';assert sys.version_info>=(3,12)
    prefix=args.prefix.resolve();python=args.python.absolute();archive=args.rootfs_archive.resolve();assert not prefix.exists() and python.is_file() and archive.is_file()
    assert sha(archive)==ARCHIVE_SHA
    for command in ['g++','cmake','apt-get','dpkg-deb','tar','bwrap','systemd-run','systemctl']:assert shutil.which(command),f'Missing explicit Linux prerequisite: {command}'
    sources={str(path):sha(path) for folder in FOLDERS for path in (SOURCES/folder).iterdir() if path.is_file()}
    prefix.mkdir(parents=True);(prefix/'logs').mkdir();(prefix/'sources').mkdir()
    if args.copy_rootfs_archive:
        destination=prefix/'sources/rootfs.tar.gz';shutil.copyfile(archive,destination);assert sha(destination)==ARCHIVE_SHA;archive=destination
    plan={'source_files_sha256':sources,'rootfs_archive':str(archive),'rootfs_archive_sha256':ARCHIVE_SHA,'explicit_base_python':str(python),'scope':'Install the current five required native tools; historical distanceV1/V2 remain preserved in source and are not rebuilt.'}
    (prefix/'installation-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    audit=audit_environment(prefix/'audit',python)
    commands=[('pymesh','native-pymesh-20261016',[str(prefix/'pymesh'),'--rootfs-archive',str(archive)]),
      ('snap','native-cgal-20261016',[str(prefix/'snap'),'--audit-python',str(audit)]),
      ('distance','native-cgal-distance-20261016-v3',[str(prefix/'distance'),'--cgal-runtime',str(prefix/'snap')]),
      ('dominance','native-cgal-dominance-20261016',[str(prefix/'dominance'),'--cgal-runtime',str(prefix/'snap')]),
      ('clip','native-pymesh-clip-20261016',[str(prefix/'clip'),'--pymesh-runtime',str(prefix/'pymesh')])]
    receipts={}
    for name,folder,arguments in commands:
        command=[str(python),str(SOURCES/folder/'setup.py'),*arguments]
        with (prefix/'logs'/(name+'.log')).open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        receipts[name]={'prefix':str(prefix/name),'installation_receipt_sha256':sha(prefix/name/'installation-receipt.json')}
    assert all(sha(path)==value for path,value in sources.items()),'Frozen installer source changed'
    result={'status':'installed','audit_python':str(audit),'rootfs_archive':str(archive),'rootfs_archive_sha256':ARCHIVE_SHA,'tools':receipts,'source_files_sha256':sources,'scope':'Runtime installation only; does not execute a carrier or manufacture geometry.'}
    (prefix/'runtime.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
