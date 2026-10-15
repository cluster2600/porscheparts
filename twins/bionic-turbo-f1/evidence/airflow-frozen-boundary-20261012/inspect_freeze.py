"""Reproduce the bounded official-source reading used by the snap witness."""
import hashlib,json,tarfile
from pathlib import Path
w=Path(__file__).parent;p=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(p.read_bytes())=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
paths={
 'src/mesh/snappyHexMesh/snappyHexMeshDriver/snappySnapDriver.C':[(743,809),(868,955),(2742,2753),(2864,2877)],
 'src/mesh/snappyHexMesh/meshRefinement/meshRefinementBaffles.C':[(5051,5089)],
 'src/mesh/snappyHexMesh/meshRefinement/meshRefinement.C':[(2163,2216)],
}
records=[]
with tarfile.open(p) as tar:
 for name,ranges in paths.items():
  member='OpenFOAM-v2406/'+name;b=tar.extractfile(member).read();s=b.decode();lines=s.splitlines()
  if name.endswith('snappySnapDriver.C'):
   assert sha(b)=='f24b217c8d25c88dd74d7c9655949a3a546f9e8d0ffa6bff8888477c8e906e45'
   assert 'smoothIter < snapParams.nSmoothPatch()' in s
   assert s.index('        preSmoothPatch\n',s.index('Constructing mesh displacer'))<s.index('            freezeExposedPoints\n',s.index('Constructing mesh displacer'))
  with (w/Path(name).name).open('xb') as f:f.write(b)
  records.append(dict(member=member,sha256=sha(b),bytes=len(b),excerpts=[dict(first=a,last=z,text='\n'.join(lines[a-1:z])) for a,z in ranges]))
with (w/'source-reference.json').open('x') as f:json.dump(dict(archive_sha256=sha(p.read_bytes()),url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',members=records,scope='Order and scope of point freezing; not a full refinement or motion qualification'),f,indent=2)
