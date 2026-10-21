"""Install the exact clipped-CSG wrapper using an explicit verified PyMesh runtime."""
import argparse,hashlib,json,shutil
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--pymesh-runtime',required=True,type=Path);args=p.parse_args()
    prefix=args.prefix.resolve();base=args.pymesh_runtime.resolve();assert not prefix.exists()
    manifest=base/'installation-receipt.json';runtime=json.loads(manifest.read_text());root=base/'rootfs'
    assert runtime['image_id']=='sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e'
    assert all(sha(root/name)==value for name,value in runtime['runtime_files_sha256'].items())
    assert all(str((root/name).readlink())==value for name,value in runtime['rootfs_symlinks'].items())
    prefix.mkdir(parents=True);(prefix/'jobs').mkdir()
    for name in ['run.py','setup.py']:shutil.copyfile(SOURCE/name,prefix/name)
    runtime.update(rootfs_path=str(root),base_installation_receipt=str(manifest),base_installation_receipt_sha256=sha(manifest),
      source_files_sha256={name:sha(prefix/name) for name in ['run.py','setup.py']},
      operation='difference(intersection(chain,mask),intersection(part,strict_bbox(chain)))',
      bbox_rule='nextafter of all six original chain IEEE bounds toward exterior infinity; verify strict containment of every chain vertex')
    (prefix/'installation-receipt.json').write_text(json.dumps(runtime,indent=2)+'\n');print(json.dumps({'prefix':str(prefix),'rootfs_path':str(root)}))
if __name__=='__main__':main()
