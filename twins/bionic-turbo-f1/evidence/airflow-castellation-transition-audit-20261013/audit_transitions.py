"""Reconstruct native cell centres, face angles and concavity tuples from saved meshes."""
import csv,hashlib,json,re,sys,tarfile
from pathlib import Path
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');case=root/'regional-castellation-fixed-091';parent=root/'outer-wall-bisect-086'
for c in (case,parent):
 r=json.loads((c/'report.json').read_text());assert not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
members=['OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshCheck.C','OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshTools.C','OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCellCentresAndVols.C','OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveMesh/primitiveMeshFaceCentresAndAreas.C']
with tarfile.open(archive) as t:
 sources=[dict(member=n,sha256=hashlib.sha256(t.extractfile(n).read()).hexdigest()) for n in members]
 source=t.extractfile(members[0]).read().decode();assert 'planarCosAngle_   = 1.0e-6;' in source
(w/'source-references.json').write_text(json.dumps(dict(url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',archive_sha256=sha(archive),members=sources),indent=2)+'\n')
def load(m):
 p=ascii_list((m/'points').read_text(),True);f=[np.array(v,int) for v in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int);nc=int(max(o.max(),n.max())+1);cf=np.empty((len(f),3));sf=cf.copy()
 for width in sorted(set(map(len,f))):
  ids=np.array([i for i,v in enumerate(f) if len(v)==width]);cf[ids],sf[ids],_=geometry(p[np.array([f[i] for i in ids])])
 cells=[[] for _ in range(nc)]
 for i,c in enumerate(o):cells[c].append(i)
 for i,c in enumerate(n):cells[c].append(i)
 # Native estimate is mean of face centres, then signed pyramid-weighted centre.
 est=np.zeros((nc,3));np.add.at(est,o,cf);np.add.at(est,n,cf[:len(n)]);est/=np.array(list(map(len,cells)))[:,None]
 vc=np.zeros(nc);cc=np.zeros((nc,3))
 for labels,centres,areas,sgn in ((o,cf,sf,1),(n,cf[:len(n)],sf[:len(n)],-1)):
  pv=sgn*np.einsum('ij,ij->i',areas,centres-est[labels]);np.add.at(vc,labels,pv);np.add.at(cc,labels,pv[:,None]*(.75*centres+.25*est[labels]))
 assert np.all(vc>1e-300);cc/=vc[:,None];vc/=3
 d=cc[n]-cc[o[:len(n)]];norm=sf[:len(n)]/np.linalg.norm(sf[:len(n)],axis=1)[:,None];normal=np.einsum('ij,ij->i',d,norm);length=np.linalg.norm(d,axis=1);angle=np.degrees(np.arccos(np.clip(normal/length,-1,1)));assert np.all(normal>0)
 return p,f,o,n,cells,cf,sf,cc,vc,angle,d,norm,normal
reports=[]
for title,m in [('parent086',parent/'constant/polyMesh'),('first091',case/'1e-07/polyMesh'),('final091',case/'2.6e-06/polyMesh')]:
 p,f,o,n,cells,cf,sf,cc,vc,angle,d,norm,normal=load(m);bad=[];rows=[];level=ascii_list((m/'cellLevel').read_text()).astype(int) if (m/'cellLevel').exists() else np.zeros(len(cells),int)
 for c,ids in enumerate(cells):
  ids=np.array(ids);nn=sf[ids]/np.linalg.norm(sf[ids],axis=1)[:,None];nn*=np.where(o[ids]==c,1,-1)[:,None];delta=cf[ids][None,:,:]-cf[ids][:,None,:];dist=np.linalg.norm(delta,axis=2);dots=np.einsum('ijk,ik->ij',delta,nn)/np.maximum(dist,1e-300);np.fill_diagonal(dots,-1);ij=np.unravel_index(np.argmax(dots),dots.shape);score=float(dots[ij])
  if score>-1e-6:
   bad.append(c);i,j=ij;rows.append((c,int(level[c]),len(ids),int(ids[i]),int(ids[j]),score,float(np.dot(delta[i,j],nn[i])),float(np.dot(nn[i],nn[j]))))
 severe=np.flatnonzero(angle>70);native_bad=ascii_list((m/'sets/concaveCells').read_text()).astype(int) if (m/'sets/concaveCells').exists() else np.array([],int);native_non=ascii_list((m/'sets/nonOrthoFaces').read_text()).astype(int) if (m/'sets/nonOrthoFaces').exists() else np.array([],int)
 assert set(bad)==set(native_bad);assert set(severe)==set(native_non)
 if title!='parent086':assert len(bad)==6700 and len(severe)==14080
 else:assert not bad and not len(severe)
 with (w/(title+'-concavity.csv')).open('x') as out:
  cw=csv.writer(out);cw.writerow(['cell','level','cell_faces','face_i','face_j','max_normalized_score','signed_centre_plane_distance_m','outward_normals_dot']);cw.writerows(rows)
 with (w/(title+'-nonorthogonality.csv')).open('x') as out:
  cw=csv.writer(out);cw.writerow(['face','owner','neighbour','owner_level','neighbour_level','angle_deg','normal_centre_separation_m','tangential_centre_separation_m']);cw.writerows((int(i),int(o[i]),int(n[i]),int(level[o[i]]),int(level[n[i]]),float(angle[i]),float(normal[i]),float(np.linalg.norm(d[i]-normal[i]*norm[i]))) for i in severe)
 maxface=int(angle.argmax());scores=np.array([row[5] for row in rows]);worst=max(rows,key=lambda row:row[5]) if rows else None
 # Compare saved native summary at the same stage; no new native command.
 log=(parent/'log.checkMesh').read_text() if title=='parent086' else (case/'log.checkMesh').read_text().split('Time = '+m.parent.name+'\n',1)[1].split('Time = ',1)[0]
 native_max=float(re.search(r'Mesh non-orthogonality Max:\s*([0-9.eE+-]+)',log)[1]);assert abs(float(angle.max())-native_max)<1e-9
 reports.append(dict(stage=title,mesh=str(m),cells=len(cells),faces=len(f),volume_m3=float(vc.sum()),minimum_cell_volume_m3=float(vc.min()),native_concavity_labels_exact=True,flagged=len(bad),flagged_score_range=[float(scores.min()),float(scores.max())] if len(scores) else [],flagged_scores_le_positive_native_threshold=int((scores<=1e-6).sum()),flagged_scores_gt_positive_native_threshold=int((scores>1e-6).sum()),worst_concavity_tuple=worst,cell_faces_histogram=dict(Counter(len(cells[c]) for c in bad)),native_nonorthogonality_labels_exact=True,severe=len(severe),level_pairs=dict(Counter(str(sorted([int(level[o[i]]),int(level[n[i]])])) for i in severe)),max_angle_deg=float(angle.max()),native_max_angle_deg=native_max,worst_face=dict(label=maxface,owner=int(o[maxface]),neighbour=int(n[maxface]),owner_centre_m=cc[o[maxface]].tolist(),neighbour_centre_m=cc[n[maxface]].tolist(),face_centre_m=cf[maxface].tolist(),unit_normal=norm[maxface].tolist(),normal_separation_m=float(normal[maxface]),tangential_separation_m=float(np.linalg.norm(d[maxface]-normal[maxface]*norm[maxface])))))
result=dict(reader_sha256=sha(Path(__file__)),geometry_helper_sha256=sha(Path('twins/bionic-turbo-f1/cfd/frame_balance_batches.py')),source_receipts={str(c):sha(c/'report.json') for c in (parent,case)},all_source_payloads_verified=True,native_rerun=False,thresholds_unchanged=True,reports=reports,limitations='Native face-plane label reconstruction, not strict-concavity certification. Counts split at +1e-6 only describe score distribution; acceptance still uses >-1e-6. No correction, flow or performance qualification.')
(w/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
