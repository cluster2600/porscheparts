"""Reconstruct the pinned PyMesh rootfs from the retained verified Docker export."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
IMAGE='sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e'
ARCHIVE_SHA='536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56'
NATIVE='usr/local/lib/python3.6/site-packages/pymesh/lib/PyMesh.cpython-36m-x86_64-linux-gnu.so'
NATIVE_SHA='17cd2bb3a74539b1f913501f49a362f65cb395a62ab65bc5a6e8815ccc585d8a'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--rootfs-archive',type=Path,required=True)
    args=p.parse_args();prefix=args.prefix.resolve();archive=args.rootfs_archive.resolve();assert not prefix.exists() and archive.is_file()
    assert sha(archive)==ARCHIVE_SHA,'Only the retained exact pinned image export is accepted'
    prefix.mkdir(parents=True);(prefix/'rootfs').mkdir();(prefix/'jobs').mkdir()
    for name in ['run.py','setup.py','original_v4.py']:shutil.copyfile(SOURCE/name,prefix/name)
    # Archive identity is checked before extraction. Docker images contain
    # legitimate absolute symlinks; these are consumed only inside bwrap.
    command=['tar','--extract','--gzip','--no-same-owner','--no-same-permissions','--file',str(archive),'--directory',str(prefix/'rootfs')]
    with (prefix/'extract.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    assert sha(prefix/'rootfs'/NATIVE)==NATIVE_SHA
    # Pin the native module, its wrapper and every ELF shared library bundled
    # in the image. The checked archive records the remaining rootfs contents.
    root=prefix/'rootfs';files={};links={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            # Do not follow absolute rootfs symlinks on the host.
            links[str(path.relative_to(root))]=str(path.readlink());continue
        if path.is_file() and ('.so' in path.name or path.suffix in ['.py','.pyc'] or str(path.relative_to(root))=='usr/local/bin/python3.6'):
            files[str(path.relative_to(root))]=sha(path)
    receipt={'image_id':IMAGE,'export_archive_sha256':ARCHIVE_SHA,'retained_archive':str(archive),
      'native_module_sha256':NATIVE_SHA,'runtime_files_sha256':files,'rootfs_symlinks':links,
      'source_files_sha256':{name:sha(prefix/name) for name in ['run.py','setup.py','original_v4.py']},
      'operation':'intersection(difference(chain,part),mask), one exact CSGTree, final float64 export only',
      'pymesh_version':'0.3','python_version':'3.6.11','numpy_version':'1.19.0',
      'license_metadata':'PyMesh2 METADATA declares MPL without version; bundled dependencies retain their licences',
      'source_url':'https://github.com/PyMesh/PyMesh','exact_installed_Cpp_commit':None,
      'scope':'Reproduction from the exact retained Docker export; no system installation, no secret or paid resource'}
    (prefix/'installation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'prefix':str(prefix),'runtime_files':len(files),'native_module_sha256':NATIVE_SHA}))
if __name__=='__main__':main()
