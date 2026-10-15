"""Record the native empty-patch cleanup used by 067."""
import hashlib,json,tarfile
from pathlib import Path
w=Path(__file__).parent;p=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
n='OpenFOAM-v2406/applications/utilities/mesh/manipulation/createPatch/createPatch.C'
with tarfile.open(p) as t:b=t.extractfile(n).read()
s=b.decode();assert 'fvMeshTools::removeEmptyPatches(mesh, true)' in s and 'if (!pointSync)' in s
with (w/'createPatch.C').open('xb') as f:f.write(b)
with (w/'cleanup-source.json').open('x') as f:json.dump(dict(member=n,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),source_url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',configuration='pointSync false; patches ();',scope='Native empty patch cleanup, no point synchronisation requested; independently compare output geometry.'),f,indent=2)
