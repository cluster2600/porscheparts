"""Verify inherited point-zone membership against original coordinates."""
import json,re,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from prepare_case import sha
root=Path('work/bionic-airflow-20261012');w=Path(__file__).parent
meshes=[root/n/'constant/polyMesh' for n in ('outer-wall-patch-085','outer-wall-bisect-086')]
def read(m):
 p=ascii_list((m/'points').read_text(),True)
 s=(m/'pointZones').read_text();r=re.search(r'frozenPoints\s*\{.*?pointLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',s,re.S)
 z=np.fromstring(r[2],sep=' ',dtype=int);assert len(z)==int(r[1]);return p,z
p,z=read(meshes[0]);q,y=read(meshes[1]);d,ix=cKDTree(p[z]).query(q[y]);assert np.all(d==0) and len(set(ix))==len(z)==len(y)==7424
result={'original_frozen_point_coordinates_exact':True,'all_original_members_once':True,'members':len(y),'new_members':0,'source_sha256':sha(Path(__file__)),'scope':'Native remapping preserves old members, but does not select new endpoint midpoints for a later projection.'}
(w/'zone-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
