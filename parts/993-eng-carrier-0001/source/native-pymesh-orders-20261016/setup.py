"""Install two explicit historical CSG orders over an immutable existing rootfs."""
import argparse,hashlib,json,shutil
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--pymesh-runtime',type=Path,required=True);a=p.parse_args()
    root=a.prefix.resolve();base=a.pymesh_runtime.resolve();receipt=base/'installation-receipt.json';assert not root.exists()
    d=json.loads(receipt.read_text());assert d['image_id']=='sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e'
    assert d['export_archive_sha256']=='536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56'
    assert all(sha(base/n)==value for n,value in d['source_files_sha256'].items())
    assert all(sha(base/'rootfs'/n)==value for n,value in d['runtime_files_sha256'].items())
    assert all(str((base/'rootfs'/n).readlink())==value for n,value in d['rootfs_symlinks'].items())
    root.mkdir(parents=True);(root/'jobs').mkdir();(root/'rootfs').symlink_to(base/'rootfs',target_is_directory=True)
    for n in ['run.py','setup.py']:shutil.copyfile(SOURCE/n,root/n)
    d.update(source_files_sha256={n:sha(root/n) for n in ['run.py','setup.py']},external_rootfs_path=str(base/'rootfs'),parent_runtime_receipt=str(receipt),parent_runtime_receipt_sha256=sha(receipt),scope='Explicit historical order adapter; same image/native modules, no upstream or rootfs modification.')
    (root/'installation-receipt.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'status':'installed','prefix':str(root),'parent_unchanged':True}))

if __name__=='__main__':main()
