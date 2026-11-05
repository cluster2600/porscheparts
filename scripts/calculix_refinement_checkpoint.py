"""Lossless, atomic checkpoints for the existing disjoint edge-star selection only."""
from pathlib import Path
from collections import Counter
import hashlib,json,os,re,zipfile
import numpy as np

LIMIT=512*1024**2

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def array_hash(a):
 h=hashlib.sha256()
 for begin in range(0,len(a),65536):h.update(np.ascontiguousarray(a[begin:begin+65536]).tobytes())
 return h.hexdigest()

class Balanced:
 """The qualified least-covered-case traversal, with an explicit resumable cursor."""
 def __init__(self,vectors,totals,covered,blocked,protected,allowed,target=.5):
  self.vectors=vectors;self.totals=totals;self.covered=covered;self.blocked=blocked;self.protected=protected;self.allowed=allowed;self.target=target
  self.orders={name:np.argsort(values)[::-1] for name,values in vectors.items()};self.positions={name:0 for name in vectors};self.seen=np.zeros(len(blocked),dtype=bool);self.order_hashes={name:array_hash(a) for name,a in self.orders.items()}
 def __iter__(self):return self
 def __next__(self):
  while True:
   candidates=[name for name in self.orders if self.covered[name]<self.target*self.totals[name] and self.positions[name]<len(self.orders[name])]
   if not candidates:raise StopIteration
   name=min(candidates,key=lambda key:(self.covered[key]/self.totals[key],key))
   while self.positions[name]<len(self.orders[name]):
    seed=int(self.orders[name][self.positions[name]]);self.positions[name]+=1
    if self.seen[seed] or not self.allowed[seed] or self.blocked[seed] or seed in self.protected:continue
    self.seen[seed]=True;return seed
 def restore_cursor(self,positions,seen,hashes):
  assert hashes==self.order_hashes and set(positions)==set(self.positions)
  assert seen.dtype==np.bool_ and seen.shape==self.seen.shape
  assert all(type(p) is int and 0<=p<=len(self.orders[k]) for k,p in positions.items())
  assert int(seen.sum())<=sum(positions.values())
  self.positions=dict(positions);self.seen=seen.copy()

def save(root,context,cursor,state):
 root=Path(root);root.mkdir(mode=0o700,exist_ok=True);assert not root.is_symlink() and root.stat().st_uid==os.getuid()
 stars=state['selected'];assert stars;offsets=np.r_[0,np.cumsum([len(x['source_cell_indices']) for x in stars])].astype('<i8');parents=np.array(state['removed'],dtype='<i8');assert offsets[-1]==len(parents) and np.array_equal(parents,np.concatenate([np.asarray(x['source_cell_indices'],dtype='<i8') for x in stars]));assert len(np.unique(parents))==len(parents);assert np.array_equal(np.flatnonzero(state['blocked']),np.sort(parents))
 arrays=dict(edges=np.asarray([x['edge'] for x in stars],dtype='<i8'),parent_offsets=offsets,parent_cells=parents,maximum_conditions=np.asarray([x['maximum_child_edge_matrix_condition'] for x in stars],dtype='<f8'),midpoints=np.asarray(state['midpoints'],dtype='<f8'),serialized_midpoints=np.asarray(state['solver_midpoints'],dtype='<f8'),children=np.vstack(state['children']).astype('<i8',copy=False),attempted=np.asarray(sorted(state['attempted']),dtype='<i8'),seen=cursor.seen)
 size=sum(a.nbytes for a in arrays.values());assert size<=LIMIT and arrays['children'].shape==(2*len(parents),4)
 numbers=[int(p.stem.split('-')[-1]) for p in root.glob('selection-*.npz') if re.fullmatch(r'selection-[0-9]{6}\.npz',p.name)];generation=max(numbers,default=0)+1;name=f'selection-{generation:06d}';archive=root/(name+'.npz');assert not archive.exists()
 with archive.open('xb') as f:np.savez_compressed(f,**arrays);f.flush();os.fsync(f.fileno())
 assert archive.stat().st_size<=LIMIT+65536
 record=dict(schema=1,context=context,npz=name+'.npz',npz_sha256=sha(archive),expanded_array_bytes=size,positions=cursor.positions,order_hashes=cursor.order_hashes,covered=state['covered'],case_covered=state['case_covered'],refused=dict(state['refused']),last_note=state['last_note'],source_cells=len(state['blocked']),selected_edges=len(stars),split_source_cells=len(parents),proposal_or_geometry_admitted=False)
 metadata=root/(name+'.json')
 with metadata.open('x') as f:json.dump(record,f,sort_keys=True);f.flush();os.fsync(f.fileno())
 latest=dict(record=metadata.name,record_sha256=sha(metadata));temporary=root/(name+'.latest.tmp')
 with temporary.open('x') as f:json.dump(latest,f);f.flush();os.fsync(f.fileno())
 os.replace(temporary,root/'latest.json');return dict(generation=generation,metadata=str(metadata),archive_sha256=record['npz_sha256'],bytes=archive.stat().st_size,selected_edges=len(stars))

def load(root,context):
 root=Path(root);latest=json.loads((root/'latest.json').read_text());assert re.fullmatch(r'selection-[0-9]{6}\.json',latest['record']);metadata=root/latest['record'];assert not metadata.is_symlink() and sha(metadata)==latest['record_sha256'];record=json.loads(metadata.read_text());assert record['schema']==1 and record['context']==context and record['proposal_or_geometry_admitted'] is False;assert re.fullmatch(r'selection-[0-9]{6}\.npz',record['npz']);archive=root/record['npz'];assert not archive.is_symlink() and sha(archive)==record['npz_sha256'];assert record['expanded_array_bytes']<=LIMIT
 with zipfile.ZipFile(archive) as z:assert sum(x.file_size for x in z.infolist())<=LIMIT+65536
 with np.load(archive,allow_pickle=False) as z:a={k:z[k] for k in z.files}
 assert sum(x.nbytes for x in a.values())==record['expanded_array_bytes'];n=record['selected_edges'];p=record['split_source_cells'];offsets=a['parent_offsets'];parents=a['parent_cells'];assert offsets.shape==(n+1,) and offsets[0]==0 and offsets[-1]==p and np.all(np.diff(offsets)>0);assert parents.shape==(p,) and len(np.unique(parents))==p and parents.min()>=0 and parents.max()<record['source_cells'];assert a['children'].shape==(2*p,4) and a['edges'].shape==(n,2) and a['midpoints'].shape==a['serialized_midpoints'].shape==(n,3) and a['maximum_conditions'].shape==(n,);assert np.isfinite(a['midpoints']).all() and np.isfinite(a['serialized_midpoints']).all() and np.isfinite(a['maximum_conditions']).all() and np.all(a['maximum_conditions']<=1e6)
 selected=[dict(edge=a['edges'][i].tolist(),source_cell_indices=parents[offsets[i]:offsets[i+1]].tolist(),maximum_child_edge_matrix_condition=float(a['maximum_conditions'][i])) for i in range(n)];blocked=np.zeros(record['source_cells'],dtype=bool);blocked[parents]=True
 state=dict(selected=selected,midpoints=list(a['midpoints']),solver_midpoints=list(a['serialized_midpoints']),children=[a['children'][2*offsets[i]:2*offsets[i+1]] for i in range(n)],removed=parents.tolist(),blocked=blocked,attempted=set(map(int,a['attempted'])),covered=record['covered'],case_covered=record['case_covered'],refused=Counter(record['refused']),last_note=record['last_note'])
 return state,dict(positions=record['positions'],seen=a['seen'],hashes=record['order_hashes'])
