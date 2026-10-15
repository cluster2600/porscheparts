"""Source-only verification of the archived wall patch contract, not a binary audit."""
import hashlib,json,re,tarfile
from pathlib import Path
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
 paths=['OpenFOAM-v2406/src/OpenFOAM/meshes/polyMesh/polyPatches/derived/wall/wallPolyPatch.H','OpenFOAM-v2406/src/OpenFOAM/meshes/polyMesh/polyPatches/polyPatch/polyPatch.H'];rows=[]
 with tarfile.open(archive) as tar:
  for member in paths:
   data=tar.extractfile(member).read();assert data==(W/Path(member).name).read_bytes();rows.append({'member':member,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 wall=(W/'wallPolyPatch.H').read_text();base=(W/'polyPatch.H').read_text()
 clean=lambda x:re.sub(r'//[^\n]*|/\*.*?\*/','',x,flags=re.S)
 assert re.search(r'class\s+wallPolyPatch\s*:\s*public\s+polyPatch',clean(wall)) and 'TypeName("wall");' in clean(wall) and not re.search(r'\bcoupled\s*\(',clean(wall))
 assert re.search(r'virtual\s+bool\s+coupled\(\)\s+const\s*\{\s*return\s+false;\s*\}',clean(base))
 r={'source_sha256':sha(Path(__file__)),'archive_sha256':sha(archive),'members':rows,'wall_derives_from_polyPatch':True,'wall_does_not_override_coupled':True,'base_coupled_returns_false':True,'source_contract_only':True,'future_binary_inspected':False,'independent_ratio_readback_sha256':sha(W/'independent-readback.json')}
 (W/'boundary-type-readback.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
