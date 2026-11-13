"""Exact-byte private output cap with unchanged qualified numerical function code."""
from pathlib import Path
import hashlib,io,json,re,types
import numpy as np

class CappedBuffer(io.BytesIO):
 def __init__(self,maximum):super().__init__();self.maximum=maximum
 def write(self,data):
  if self.tell()+len(data)>self.maximum:raise ValueError('Scientific output cap would be exceeded')
  return super().write(data)

class OutputBudget:
 def __init__(self,root,limit,indices):
  self.root=Path(root).absolute();self.limit=int(limit);self.indices=frozenset(indices);self.used=0;self.files={}
  if self.limit<=0 or not self.indices:raise ValueError('Positive output budget and explicit indices required')
  if self.root.exists():
   if self.root.is_symlink():raise ValueError('Symlink output root refused')
   for path in self.root.rglob('*'):
    if path.is_symlink():raise ValueError('Symlink output entry refused')
    if path.is_file():
     if path.relative_to(self.root).as_posix()=='.DS_Store':continue
     self._path(path);size=path.stat().st_size;self.files[path]=size;self.used+=size
  if self.used>self.limit:raise ValueError('Existing scientific output exceeds cap')
 def _path(self,path):
  path=Path(path).absolute()
  try:relative=path.relative_to(self.root).as_posix()
  except ValueError:raise ValueError('Output path outside owned root')
  if any(p.is_symlink() for p in [path,*path.parents] if p==self.root or self.root in p.parents):raise ValueError('Symlink output refused')
  fixed={'context.json','mesh-bounds.json','full-result.json','scientific-manifest.json'}
  if relative not in fixed:
   match=re.fullmatch(r'(?:checkpoint-(\d{5})\.json|layer-(\d{5})\.receipt\.json|layers/layer-(\d{5})\.npz|oracle/(?:layer|source-edges)-(\d{5})\.npz|bounds/layer-(\d{5})\.json)',relative)
   if not match:raise ValueError('Unlisted scientific output path')
   groups=match.groups();number=int(next(x for x in groups if x is not None))
   if groups[0] is not None:
    if not 0<=number<=len(self.indices):raise ValueError('Checkpoint outside declared domain')
   elif number not in self.indices:raise ValueError('Layer outside declared domain')
  return path
 def _write(self,target,data):
  stream=hasattr(target,'write');path=self._path(target.name if stream else target)
  if path in self.files:raise ValueError('Existing scientific output must not be overwritten')
  if len(data)>self.limit-self.used:raise ValueError('Scientific output cap would be exceeded')
  if stream:
   if target.closed or target.tell()!=0 or path.stat().st_size!=0:raise ValueError('Only a freshly opened empty output is accepted')
   target.write(data);target.flush()
  else:
   with path.open('xb') as f:f.write(data)
  if path.stat().st_size!=len(data):raise ValueError('Scientific output write was incomplete')
  self.files[path]=len(data);self.used+=len(data)
 def write_json(self,path,data):self._write(path,(json.dumps(data,indent=2,allow_nan=False)+'\n').encode())
 def save_npz(self,target,*args,**arrays):
  if args:raise ValueError('Only explicitly named numerical arrays are accepted')
  path=self._path(target.name if hasattr(target,'write') else target)
  if path in self.files:raise ValueError('Existing scientific output must not be overwritten')
  data=CappedBuffer(self.limit-self.used)
  np.savez_compressed(data,**arrays)
  self._write(target,data.getvalue())
 def verify(self):
  actual={}
  for path in self.root.rglob('*'):
   if path.is_symlink():raise ValueError('Symlink output entry refused')
   if path.is_file():
    if path.relative_to(self.root).as_posix()=='.DS_Store':continue
    self._path(path);actual[path]=path.stat().st_size
  if actual!=self.files or sum(actual.values())!=self.used or self.used>self.limit:raise ValueError('Scientific file set or byte count differs from owned writes')
  return {'scientific_bytes':self.used,'scientific_files':len(actual),'cap_bytes':self.limit}

class NumpyOutputAdapter:
 def __init__(self,budget):self.budget=budget
 def __getattr__(self,name):return self.budget.save_npz if name=='savez_compressed' else getattr(np,name)

def bind_storage(cache,storage,budget):
 """Clone function globals only; original function bytecode and numerical helpers remain unchanged."""
 cache_globals=dict(cache.write_layer.__globals__);cache_globals['np']=NumpyOutputAdapter(budget)
 writer=types.FunctionType(cache.write_layer.__code__,cache_globals,cache.write_layer.__name__,cache.write_layer.__defaults__,cache.write_layer.__closure__)
 globals_copy=dict(storage.__dict__);globals_copy['np']=NumpyOutputAdapter(budget)
 names=[name for name,value in storage.__dict__.items() if isinstance(value,types.FunctionType) and value.__module__==storage.__name__]
 for name in names:
  original=getattr(storage,name);globals_copy[name]=types.FunctionType(original.__code__,globals_copy,name,original.__defaults__,original.__closure__)
 globals_copy['write_json']=budget.write_json
 return types.SimpleNamespace(write_layer=writer),types.SimpleNamespace(**{name:globals_copy[name] for name in names})
