"""Unpublished read-only reconstruction of native face-plane flags in saved091."""
import json,sys,tarfile
from pathlib import Path
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/regional-castellation-fixed-091');r=json.loads((case/'report.json').read_text());assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
a=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(a)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
member='OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshCheck.C'
with tarfile.open(a) as t:raw=t.extractfile(member).read()
import hashlib
assert 'planarCosAngle_   = 1.0e-6;' in raw.decode() and '(pC & fN) > -planarCosAngle_' in raw.decode()
m=case/'2.6e-06/polyMesh';p=ascii_list((m/'points').read_text(),True);f=[np.array(v,int) for v in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int);lev=ascii_list((m/'cellLevel').read_text()).astype(int)
cf=np.empty((len(f),3));sf=cf.copy()
for width in sorted(set(map(len,f))):
 ix=np.array([i for i,v in enumerate(f) if len(v)==width]);cf[ix],sf[ix],_=geometry(p[np.array([f[i] for i in ix])])
cells=[[] for _ in lev]
for i,c in enumerate(o):cells[c].append(i)
for i,c in enumerate(n):cells[c].append(i)
scores=np.empty(len(lev));pairs=[]
for c,ids in enumerate(cells):
 ids=np.array(ids);normal=sf[ids]/np.linalg.norm(sf[ids],axis=1)[:,None];normal*=np.where(o[ids]==c,1,-1)[:,None];delta=cf[ids][None,:,:]-cf[ids][:,None,:];dots=np.einsum('ijk,ik->ij',delta,normal)/np.maximum(np.linalg.norm(delta,axis=2),1e-300);np.fill_diagonal(dots,-1);ij=np.unravel_index(np.argmax(dots),dots.shape);scores[c]=dots[ij]
 if scores[c]>-1e-6:pairs.append((c,int(ids[ij[0]]),int(ids[ij[1]]),float(scores[c])))
bad=ascii_list((m/'sets/concaveCells').read_text()).astype(int);assert set(np.flatnonzero(scores>-1e-6))==set(bad)
nonorth=ascii_list((m/'sets/nonOrthoFaces').read_text()).astype(int);assert np.all(nonorth<len(n))
result=dict(reader_sha256=sha(Path(__file__)),source_member=member,source_sha256=hashlib.sha256(raw).hexdigest(),source_threshold_line=43,threshold=1e-6,all_payloads_verified=True,native_flag_labels_exact=True,flagged_cells=len(bad),flagged_score_min=float(scores[bad].min()),flagged_score_max=float(scores[bad].max()),flagged_cell_face_counts=dict(Counter(len(cells[c]) for c in bad)),nonorth_level_pairs=dict(Counter(str(sorted([int(lev[o[i]]),int(lev[n[i]])])) for i in nonorth)),worst_pair=max(pairs,key=lambda x:x[3]),scope='Unpublished exploration; exact native label reconstruction, not proof of unique cause or strict geometric concavity; no native rerun')
(w/'next-transition-planes.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
