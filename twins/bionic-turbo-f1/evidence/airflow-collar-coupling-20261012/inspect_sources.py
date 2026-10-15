"""Pin native coupling source and its preconditions; no runtime claims."""
import hashlib,json,tarfile
from pathlib import Path
w=Path(__file__).parent
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
names=['applications/utilities/mesh/manipulation/'+x+'/'+x+'.C' for x in ('splitMeshRegions','mergeMeshes','stitchMesh')]+['src/dynamicMesh/perfectInterface/perfectInterface.C','src/mesh/snappyHexMesh/snappyHexMeshDriver/snappySnapDriver.C','src/mesh/snappyHexMesh/meshRefinement/meshRefinement.C']
records=[]
with tarfile.open(archive) as t:
 for n in names:
  b=t.extractfile('OpenFOAM-v2406/'+n).read();s=b.decode()
  records.append(dict(member='OpenFOAM-v2406/'+n,sha256=sha(b),bytes=len(b)))
  with (w/Path(n).name).open('xb') as f:f.write(b)
  if n.endswith('perfectInterface.C'):
   assert 'tol_ = 1e-3' in s and 'polyRemoveFace(facei)' in s and 'polyModifyFace' in s
  if n.endswith('splitMeshRegions.C'):assert 'cellRegionAddressing' in s
result=dict(archive_sha256=sha(archive.read_bytes()),url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',members=records,native_test_performed=False,limitations=['perfect matches within 0.001 times minimum edge, not exact equality','independent full topology comparison required','splitting and stitching does not qualify boundary preservation during snappy'])
with (w/'source-reference.json').open('x') as f:json.dump(result,f,indent=2)
