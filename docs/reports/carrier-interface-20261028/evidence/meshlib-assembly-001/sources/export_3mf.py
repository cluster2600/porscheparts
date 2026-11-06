"""Stream a single exact-coordinate study mesh into a 3MF package."""
from pathlib import Path
import sys,struct,zipfile,json,time,hashlib
import numpy as np
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
MODEL='3D/3dmodel.model'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as s:
  while b:=s.read(1048576):h.update(b)
 return h.hexdigest()
def arrays(path):
 with path.open('rb')as s:nv,nf=struct.unpack('<QQ',s.read(16))
 assert 3<=nv<2**31 and 4<=nf<2**31 and path.stat().st_size==16+24*(nv+nf)
 return np.memmap(path,dtype='<f8',mode='r',offset=16,shape=(nv,3)),np.memmap(path,dtype='<u8',mode='r',offset=16+24*nv,shape=(nf,3))
def info(name):
 i=zipfile.ZipInfo(name,(2026,10,29,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o600<<16;return i
def package(source,out):
 assert not out.exists();start=time.monotonic();v,f=arrays(source)
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True)as z:
  z.writestr(info('[Content_Types].xml'),'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
  z.writestr(info('_rels/.rels'),'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
  with z.open(info(MODEL),'w',force_zip64=True)as s:
   s.write(('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="'+NS+'"><metadata name="Title">993 carrier conditioned numerical study</metadata><metadata name="Description">Exact numerical geometry; mechanical convergence and machine build preparation pending.</metadata><resources><object id="1" type="model"><mesh><vertices>\n').encode())
   for begin in range(0,len(v),8192):
    batch=v[begin:begin+8192];assert np.isfinite(batch).all()
    s.write(''.join('<vertex x="%.17g" y="%.17g" z="%.17g"/>\n'%tuple(row)for row in batch).encode())
   s.write(b'</vertices><triangles>\n')
   for begin in range(0,len(f),8192):
    batch=f[begin:begin+8192];assert batch.max()<len(v)
    s.write(''.join('<triangle v1="%d" v2="%d" v3="%d"/>\n'%tuple(row)for row in batch).encode())
   s.write(b'</triangles></mesh></object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build></model>')
 report=dict(status='package_written_verification_pending',input_sha256=sha(source),output_sha256=sha(out),bytes=out.stat().st_size,vertices=len(v),triangles=len(f),elapsed_seconds=time.monotonic()-start,source_sha256=sha(Path(__file__)))
 out.with_suffix('.package.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(package(Path(sys.argv[1]),Path(sys.argv[2]))),flush=True)
