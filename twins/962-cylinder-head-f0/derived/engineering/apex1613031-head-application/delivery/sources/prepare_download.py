"""One deterministic byte-only gzip derivative; no mesh or scientific decoding."""
from pathlib import Path
import gzip,hashlib,json,os,stat
ROOT=Path('project-role://engineering-checkout')
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'work/962-engineering/apex1613031-head-application-001/head-volume.msh'
EXPECTED='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08'
SIZE=235786462
def identity(p):
 raw=p.read_bytes();return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def stamp(p):
 s=p.stat();return dict(bytes=s.st_size,mtime_ns=s.st_mtime_ns,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)))
def main():
 auth=json.loads((HERE/'authorization.json').read_text())
 assert identity(Path(__file__).resolve())==auth['source']
 accepted=ROOT/auth['accepted_result']['path']
 assert identity(accepted)==auth['accepted_result']
 a=json.loads(accepted.read_text())
 assert a['procedural_partial_repair_accepted'] and not a['whole_head_quality_accepted']
 assert a['mesh']['sha256']==EXPECTED and a['mesh']['bytes']==SIZE
 assert SOURCE.is_file() and not SOURCE.is_symlink()
 before=stamp(SOURCE);assert before['bytes']==SIZE and before['mode']=='0o444'
 output=HERE/'head-volume.msh.gz';receipt=HERE/'receipt.json'
 assert not output.exists() and not output.is_symlink() and not receipt.exists()
 markers=[bytes.fromhex('2f55736572732f'),bytes.fromhex('2f686f6d652f'),bytes.fromhex('2f707269766174652f'),bytes.fromhex('3139322e3136382e'),bytes.fromhex('66696c653a2f2f')]
 raw_hash=hashlib.sha256();n=0;tail=b'';hits=[]
 with SOURCE.open('rb') as inp,output.open('xb') as stream:
  with gzip.GzipFile(filename='',mode='wb',fileobj=stream,compresslevel=9,mtime=0) as zipped:
   while True:
    chunk=inp.read(1024*1024)
    if not chunk:break
    n+=len(chunk);assert n<=SIZE;raw_hash.update(chunk)
    window=tail+chunk
    hits.extend(m.decode() for m in markers if m in window)
    tail=window[-16:];zipped.write(chunk)
 assert n==SIZE and raw_hash.hexdigest()==EXPECTED and hits==[]
 after=stamp(SOURCE);assert before==after
 assert output.stat().st_size<100000000
 digest=hashlib.sha256();decoded=0
 with gzip.open(output,'rb') as inp:
  while True:
   chunk=inp.read(1024*1024)
   if not chunk:break
   decoded+=len(chunk);assert decoded<=SIZE;digest.update(chunk)
 assert decoded==SIZE and digest.hexdigest()==EXPECTED
 r=dict(schema='962-generated-head-lossless-gzip-review-derivative/v2',original_path=str(SOURCE.relative_to(ROOT)),original_sha256=EXPECTED,original_bytes=SIZE,selected=identity(output),gzip_filename='',gzip_mtime=0,compresslevel=9,compressed_bytes_below_GitHub100MB=True,full_decompressed_sha256=digest.hexdigest(),full_decompressed_bytes=decoded,full_decompressed_hash_and_size_match_original=True,original_stat_before=before,original_stat_after=after,original_unchanged=True,private_path_byte_markers_absent=True,private_marker_scan_scope='Entire raw byte stream including chunk-boundary overlap; no redaction.',accepted_result=auth['accepted_result'],source=auth['source'],authorization=identity(HERE/'authorization.json'),poor_cells_below_SICN_0_1=126,minimum_SICN=.039074265058645995,whole_head_mesh_admitted=False,head_physics_assessed=False,manufacturing_authorized=False,scope='Lossless review download of generated partial research mesh; not an OEM scan or manufacturing release.',no_native_or_mesh_decode=True,automatic_retry=False)
 with receipt.open('x') as f:json.dump(r,f,indent=2,allow_nan=False);print(file=f)
 output.chmod(0o444);receipt.chmod(0o444)
 print(json.dumps(dict(receipt=identity(receipt),selected=r['selected'],original_sha256=EXPECTED,decoded_bytes=decoded),indent=2))
if __name__=='__main__':main()
