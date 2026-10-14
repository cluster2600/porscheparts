"""Reread pinned native determinant sources from the exact official archive."""
import hashlib,json,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
w=Path(__file__).parent;source=Path('work/bionic-selective-boundary-20261012');archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
refs=[]
with tarfile.open(archive) as t:
 for tail in ('primitiveMeshCheck/primitiveMeshTools.C','polyMeshCheck/polyMeshCheck.C'):
  members=[m for m in t.getmembers() if m.name.endswith(tail)];assert len(members)==1
  m=members[0];data=t.extractfile(m).read();assert data==(source/Path(m.name).name).read_bytes()
  refs.append(dict(member=m.name,sha256=hashlib.sha256(data).hexdigest(),pinned_local_source=str(source/Path(m.name).name)))
assert 'mag(det(areaTensor))/8.0' in (source/'primitiveMeshTools.C').read_text()
assert 'getInternalOrCoupledFaces' in (source/'polyMeshCheck.C').read_text()
(w/'source-readback.json').write_text(json.dumps(dict(archive_sha256=sha(archive),official_url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',members=refs,reader_sha256=sha(Path(__file__)),native_source_unchanged=True),indent=2)+'\n')
