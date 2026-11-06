"""Memory-backed field storage; all numerical readers and assessors remain unchanged."""
from pathlib import Path
import numpy as np
class FieldArray(np.ndarray):
 def flush(self):pass
class Fields:
 def __init__(self,root,limit=2*1024**3):self.root=Path(root);self.limit=limit;self.arrays={};self.allocated=0
 def create(self,path,mode='w+',dtype=None,shape=None,**kwargs):
  p=Path(path);assert p.parent==self.root and p.suffix=='.npy' and not kwargs;assert mode=='w+' and np.dtype(dtype)==np.dtype('<f8');assert p.name not in self.arrays and not p.exists();assert all(type(n) is int and n>0 for n in shape)
  count=int(np.prod(shape));size=count*8;assert self.allocated+size<=self.limit;out=np.zeros(shape,dtype='<f8').view(FieldArray);self.arrays[p.name]=out;self.allocated+=size;return out
def reuse_decode(mesh,output,contract,deck,source):
 """Reuse the previously independently decoded exact mesh, after full byte checks."""
 import hashlib,json,os
 from pathlib import Path
 def sha(p):
  with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
 def digest(a):
  h=hashlib.sha256()
  for begin in range(0,len(a),65536):h.update(np.ascontiguousarray(a[begin:begin+65536]).tobytes())
  return h.hexdigest()
 mesh=Path(mesh);output=Path(output);source=Path(source);assert not output.exists() and sha(mesh)==deck['mesh_sha256'];v=np.load(source/'vertices.npy',mmap_mode='r');c=np.load(source/'cells.npy',mmap_mode='r');assert v.shape==(contract['vertex_count'],3) and c.shape==(contract['element_count'],4) and v.dtype==np.dtype('<f8') and c.dtype==np.dtype('<i8');assert np.isfinite(v).all() and c.min()>=0 and c.max()<len(v);assert digest(v)==contract['serialized_vertex_bytes_sha256'] and digest(c)==contract['connectivity_i8_bytes_sha256'];output.mkdir()
 for name in ['vertices.npy','cells.npy','decoding.json']:
  p=source/name;assert p.is_file() and not p.is_symlink() and p.stat().st_dev==output.stat().st_dev;os.link(p,output/name)
 return v,c
