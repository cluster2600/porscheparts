"""Copy a completed mesh and its actual native-volume reference without changing it."""
import hashlib,json,re,shutil,sys
from pathlib import Path
source,out=map(Path,sys.argv[1:]);assert not out.exists() and json.loads((source/'execution.json').read_text())['exit']==0
out.mkdir();(out/'constant/polyMesh').mkdir(parents=True)
for n in ['points','faces','boundary']:shutil.copyfile(source/'constant/polyMesh'/n,out/'constant/polyMesh'/n)
for n in ['execution.json','preparation.json','log.checkMesh.allGeometry']:shutil.copyfile(source/n,out/n)
text=(source/'log.checkMesh.allGeometry').read_text();info={'native_volume_m3':float(re.search(r'Total volume = (\S+)',text)[1].rstrip('.')),'native_cells':int(re.search(r'cells:\s+(\d+)',text)[1]),'source_length_unit':'m','physical_scale_verified':False,'snapshot_source_sha256':hashlib.file_digest(Path(__file__).open('rb'),'sha256').hexdigest()}
assert 0<info['native_volume_m3']<1 and 0<info['native_cells']<5_000_000
(out/'snapshot-info.json').write_text(json.dumps(info,indent=2)+'\n')
manifest={str(p.relative_to(out)):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in sorted(out.rglob('*')) if p.is_file()};(out/'snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n');print(info)
