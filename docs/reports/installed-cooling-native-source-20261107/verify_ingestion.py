from pathlib import Path
import numpy as np,json,struct,hashlib,ast
r=Path(__file__).parent;raw=(r/'native-ingested-source.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()=='80daaea26b32bc5a39579128f73a40e463a72624aff51ebbe1908db5ef6c19ca';nv,nf=struct.unpack_from('<QQ',raw,8);assert raw[:8]==b'M64TRI1\0' and (nv,nf)==(459068,918136) and len(raw)==24+24*(nv+nf);v=np.frombuffer(raw,dtype='<f8',count=nv*3,offset=24).reshape(-1,3);f=np.frombuffer(raw,dtype='<u8',offset=24+nv*24).reshape(-1,3)
original=(r.parent/'installed-cooling-native-source-20261107/duct.bin').read_bytes();assert hashlib.sha256(original).hexdigest()=='7dd050d458585f0272058ffa01b74ba3c638071b755492540b463342a7ec4c2b';mm=np.frombuffer(original,dtype='<f8',count=nv*3,offset=24).reshape(-1,3)
path=Path('twins/993-installed-cooling-f1/source/prepare_duct_cfd.py');assert hashlib.sha256(path.read_bytes()).hexdigest()=='591d901a9ffec1cca46d297a81964bf018c00767ca99fd8b724c0a31846198ff';assert hashlib.sha256(Path('twins/993-installed-cooling-f1/study.json').read_bytes()).hexdigest()=='cc79c29e97717e57f20593082f1ff2154fd263681fe214d43abcd123a2aa4fa3';fn=[x for x in ast.parse(path.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='port_labels'];assert len(fn)==1;ns={'np':np};exec(compile(ast.Module(body=fn,type_ignores=[]),str(path),'exec'),ns);labels=ns['port_labels'](mm[f].mean(axis=1),json.loads(Path('twins/993-installed-cooling-f1/study.json').read_text()))
points=[];faces=[];groups=[];group=None
with (r/'native17.obj').open() as stream:
 for line in stream:
  tokens=line.split()
  if not tokens or tokens[0].startswith('#'):continue
  if tokens[0]=='v':assert len(tokens)==4;points.append(tuple(map(float,tokens[1:])))
  elif tokens[0]=='g':assert len(tokens)==2;group=tokens[1]
  elif tokens[0]=='f':assert len(tokens)==4 and group is not None and all(1<=int(x)<=nv for x in tokens[1:]);faces.append([int(x)-1 for x in tokens[1:]]);groups.append(group)
  else:assert tokens[0]=='o',tokens[0]
assert len(points)==nv and len(faces)==nf
lookup={tuple(p):i for i,p in enumerate(v)};assert len(lookup)==nv
mapped=np.array([lookup[p] for p in points],dtype=np.int64);assert len(set(mapped.tolist()))==nv
current=mapped[np.array(faces)];groups=np.array(groups)
def canonical(a):
 a=a[np.arange(len(a))[:,None],(a.argmin(axis=1)[:,None]+np.arange(3))%3]
 return a[np.lexsort(a.T[::-1])]
checks={}
for name in sorted(set(labels)):
 checks[name]=bool(np.array_equal(canonical(f[labels==name]),canonical(current[groups==name])))
assert all(checks.values()) and set(groups)==set(labels)
result={'native_obj_sha256':hashlib.sha256((r/'native17.obj').read_bytes()).hexdigest(),'expected_ingested_binary_sha256':hashlib.sha256(raw).hexdigest(),'all_459068_points_match_binary32_rounding_exactly':True,'all_918136_oriented_triangles_and_patch_labels_preserved':True,'patch_checks':checks,'mesh_admitted':False}
(r/'ingestion-verification-v2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
