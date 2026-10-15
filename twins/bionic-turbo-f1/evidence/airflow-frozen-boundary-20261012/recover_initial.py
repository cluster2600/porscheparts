"""Materialize exact prepared bytes, accepting only manifest SHA matches."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh
import hashlib
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012');parent=base/'full-collar-063'
p,f,i,n=read_mesh(parent);ids=np.unique(np.concatenate(f[n:]));records={}
for name in ('snap-control-068','snap-frozen-069','snap-frozen-nosmooth-070'):
 case=base/name;m=json.loads((case/'manifest.json').read_text());out=w/'initial-inputs'/name;assert not out.exists();out.mkdir(parents=True)
 methods={}
 for path,digest in m['file_sha256'].items():
  candidates=[('unchanged_current_file',case/path),('pinned_parent_063',parent/path)]
  found=[(how,q.read_bytes()) for how,q in candidates if q.is_file() and sha(q)==digest]
  if found:how,data=found[0]
  else:
   assert path=='constant/polyMesh/pointZones'
   frozen=[] if name=='snap-control-068' else ids.tolist()
   data=('FoamFile {version 2.0; format ascii; class regIOobject; object pointZones;}\n1\n(\nfrozenPoints {type pointZone; pointLabels List<label> '+str(len(frozen))+'\n(\n'+'\n'.join(map(str,frozen))+'\n);}\n)\n').encode()
   how='reconstructed_exact_pointZone_from_pinned_parent_boundary_labels'
  assert hashlib.sha256(data).hexdigest()==digest
  dest=out/path;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as stream:stream.write(data)
  assert sha(dest)==digest;methods[path]=how
 (out/'manifest.json').write_bytes((case/'manifest.json').read_bytes());records[name]=methods
with (w/'initial-readback.json').open('x') as stream:json.dump(dict(source_sha256=sha(Path(__file__)),all_prepared_bytes_verified=True,methods=records,no_native_operation_repeated=True),stream,indent=2)
print('All prepared inputs materialized and verified against original manifests')
