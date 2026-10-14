"""Exploratory localization only; no mesh mutation or native rerun."""
from pathlib import Path
import json,sys
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from uniform_interface_projection import read_mesh
from frame_balance_batches import geometry
root=Path('work/bionic-airflow-20261012');case=root/'star-partition-041';old=root/'internal-facets-040';p,faces,_,internal=read_mesh(old);m=old/'constant/polyMesh'
o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int)
labels=np.concatenate((o,n));baseids=np.concatenate((np.arange(len(faces)),np.arange(len(n))));order=np.argsort(labels,kind='stable');parents=np.load(case/'parent-cell-labels.npy',allow_pickle=False);assert np.array_equal(labels[order],parents)
baseids=baseids[order];bad=ascii_list((case/'constant/polyMesh/sets/underdeterminedCells').read_text()).astype(int);newp=ascii_list((case/'constant/polyMesh/points').read_text(),True);results=[]
for vertices in (3,4):
 selection=np.array([i for i in bad if len(faces[baseids[i]])==vertices],int);f=[faces[baseids[i]] for i in selection];v=p[np.asarray(f)];c,s,_=geometry(v);unit=s/np.linalg.norm(s,axis=1)[:,None];apex=newp[len(p)+parents[selection]];height=np.abs(np.einsum('ij,ij->i',c-apex,unit));edge=np.linalg.norm(v-np.roll(v,1,axis=1),axis=2).max(axis=1);horizontal=np.abs(unit[:,2])>1-1e-12
 results.append(dict(base_vertices=vertices,bad_cells=len(selection),horizontal_bases=int(horizontal.sum()),height_m_min=float(height.min()),height_m_max=float(height.max()),longest_base_edge_m_min=float(edge.min()),longest_base_edge_m_max=float(edge.max()),height_to_longest_edge_min=float((height/edge).min()),height_to_longest_edge_max=float((height/edge).max())))
r=dict(source_sha256=sha(Path(__file__)),scope='Exploratory geometric localization; not native solver qualification or a unique causal proof',parent_labels_sha256=sha(case/'parent-cell-labels.npy'),bad_set_sha256=sha(case/'constant/polyMesh/sets/underdeterminedCells'),results=results)
with Path(__file__).with_name('next-base-localization.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
