"""Independent bounded-memory parsing of every coordinate and triangle in the export."""
from pathlib import Path
import sys,json,zipfile,struct,hashlib,time
import numpy as np
from lxml import etree
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
MODEL='3D/3dmodel.model'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as s:
  while b:=s.read(1048576):h.update(b)
 return h.hexdigest()
def verify(source,path):
 start=time.monotonic()
 with source.open('rb')as s:nv,nf=struct.unpack('<QQ',s.read(16))
 v=np.memmap(source,dtype='<f8',mode='r',offset=16,shape=(nv,3));f=np.memmap(source,dtype='<u8',mode='r',offset=16+24*nv,shape=(nf,3))
 vi=fi=0;vb=[];fb=[];objects=items=models=0;stack=[];containers={k:0 for k in ['resources','mesh','vertices','triangles','build']};root_order=[]
 with zipfile.ZipFile(path)as z:
  assert sorted(z.namelist())==sorted(['[Content_Types].xml','_rels/.rels',MODEL])
  types=etree.fromstring(z.read('[Content_Types].xml'));assert types.tag=='{http://schemas.openxmlformats.org/package/2006/content-types}Types'
  assert {e.get('Extension'):e.get('ContentType')for e in types}=={'rels':'application/vnd.openxmlformats-package.relationships+xml','model':'application/vnd.ms-package.3dmanufacturing-3dmodel+xml'}
  rels=etree.fromstring(z.read('_rels/.rels'));assert len(rels)==1 and rels[0].get('Target')=='/'+MODEL and rels[0].get('Type')=='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel'
  with z.open(MODEL)as stream:
   for event,e in etree.iterparse(stream,events=['start','end'],resolve_entities=False,no_network=True):
    q=etree.QName(e);tag=q.localname;assert q.namespace==NS
    if event=='start':
     parent=stack[-1]if stack else None;stack.append(tag)
     if parent=='model':root_order.append(tag)
     if tag in containers:
      containers[tag]+=1;assert parent=={'resources':'model','mesh':'object','vertices':'mesh','triangles':'mesh','build':'model'}[tag]
     if tag=='model':models+=1;assert parent is None and e.get('unit')=='millimeter' and e.get('requiredextensions')is None
     elif tag=='object':objects+=1;assert parent=='resources' and e.get('id')=='1' and e.get('type')=='model'
     elif tag=='item':items+=1;assert parent=='build' and e.get('objectid')=='1' and e.get('transform')=='1 0 0 0 1 0 0 0 1 0 0 0'
     elif tag=='vertex':assert parent=='vertices'
     elif tag=='triangle':assert parent=='triangles'
     else:assert tag in ['metadata','resources','mesh','vertices','triangles','build']
     continue
    if tag=='vertex':
     vb.append([float(e.get(k))for k in ['x','y','z']])
     if len(vb)==8192:
      a=np.asarray(vb,dtype='<f8');assert np.array_equal(a.view('<u8'),v[vi:vi+len(vb)].view('<u8'));vi+=len(vb);vb=[]
    elif tag=='triangle':
     fb.append([int(e.get(k))for k in ['v1','v2','v3']])
     if len(fb)==8192:assert np.array_equal(np.asarray(fb,dtype='<u8'),f[fi:fi+len(fb)]);fi+=len(fb);fb=[]
    assert stack.pop()==tag;e.clear()
    while e.getprevious()is not None:del e.getparent()[0]
   assert not stream.read(1)
  assert models==objects==items==1 and not stack and all(n==1 for n in containers.values())
  assert root_order==['metadata']*(len(root_order)-2)+['resources','build']
  assert np.array_equal(np.asarray(vb,dtype='<f8').reshape(-1,3).view('<u8'),v[vi:].view('<u8'));assert np.array_equal(np.asarray(fb,dtype='<u8').reshape(-1,3),f[fi:])
  vi+=len(vb);fi+=len(fb);assert vi==nv and fi==nf
 result=dict(status='complete_3mf_array_and_package_verification_passed',input_sha256=sha(source),package_sha256=sha(path),vertices_verified=vi,triangles_verified=fi,coordinate_bits_exact=True,index_order_exact=True,unit='millimeter',build_items=items,identity_placement=True,all_member_crc_verified=True,elapsed_seconds=time.monotonic()-start)
 return result
if __name__=='__main__':
 result=verify(Path(sys.argv[1]),Path(sys.argv[2]));Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
