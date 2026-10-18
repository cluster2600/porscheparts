"""Extract the pinned experimental archive only; no installer or download."""
import hashlib,json,sys,tarfile
from pathlib import Path
root=Path(sys.argv[1]);archive=Path(sys.argv[2]);expected=sys.argv[3]
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for b in iter(lambda:stream.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
if sha(archive)!=expected:raise ValueError('Source archive changed')
target=root/'src';target.mkdir(exist_ok=False)
with tarfile.open(archive)as source:source.extractall(target,filter='data')
cgal=target/'cgal-b4e8c1887ce6a0abeb618634125e5cfcd301ce16'
api=cgal/'PMP_Boolean_operations/include/CGAL/Polygon_mesh_processing/triangle_soup_boolean_operations_3.h'
if sha(api)!='15ac79840d22479570d0284fb7b4dc5b1b508ced0f3d76c2fe817e2d84f4d69d':
    raise ValueError('The experimental API source differs')
files={str(p.relative_to(target)):sha(p)for p in sorted(target.rglob('*'))if p.is_file()and not p.is_symlink()}
links={str(p.relative_to(target)):str(p.readlink())for p in sorted(target.rglob('*'))if p.is_symlink()}
report=dict(status='pinned_experimental_source_restored',archive_sha256=sha(archive),
    CGAL_commit='b4e8c1887ce6a0abeb618634125e5cfcd301ce16',API_header_sha256=sha(api),
    source_files_sha256=files,source_symlinks=links,archive_unchanged=sha(archive)==expected)
(root/'source-restoration.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],files=len(files),symlinks=len(links))))
