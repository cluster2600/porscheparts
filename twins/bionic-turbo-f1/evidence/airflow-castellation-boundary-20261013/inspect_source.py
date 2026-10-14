"""Read-only exact-source inventory for a future regional castellation witness."""
import hashlib,json,tarfile
from pathlib import Path
w=Path(__file__).parent;a=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(a.read_bytes())=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
records=[]
with tarfile.open(a) as t:
 for suffix,tokens in [('/refinementSurfaces/refinementSurfaces.C',['regionMinLevel[surfI].insert','regionMaxLevel[surfI].insert']),('/snappyHexMeshDriver/snappyRefineDriver.C',['surfaceOnlyRefine','danglingCellRefine','refinementInterfaceRefine'])]:
  matches=[m for m in t.getmembers() if m.name.endswith(suffix)];assert len(matches)==1;m=matches[0];b=t.extractfile(m).read();s=b.decode();assert all(x in s for x in tokens)
  records.append(dict(member=m.name,sha256=sha(b),occurrences={tok:[i for i,line in enumerate(s.splitlines(),1) if tok in line] for tok in tokens}))
(w/'next-castellation-source.json').write_text(json.dumps(dict(archive_sha256=sha(a.read_bytes()),url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',members=records,scope='Source inspection only; regional requests do not prove frozen join through all subsequent operations; no native case prepared.'),indent=2)+'\n')
