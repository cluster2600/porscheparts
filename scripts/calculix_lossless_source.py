"""A lossless DAT stream view; raw bytes are verified without a disk-sized duplicate."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,lzma

class CountSink:
 def __init__(self):self.bytes=0
 def write(self,data):self.bytes+=len(data);return len(data)

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

class VerifiedXZSource:
 def __init__(self,path,compressed_sha256,raw_bytes,raw_sha256,decoder,maximum_raw_bytes=2750000000):
  self.path=Path(path);self.compressed_sha256=compressed_sha256;self.raw_bytes=raw_bytes;self.raw_sha256=raw_sha256;self.decoder=decoder;self.maximum_raw_bytes=maximum_raw_bytes;self.verified=None
 def verify(self):
  assert sha(self.path)==self.compressed_sha256
  sink=CountSink()
  with self.path.open('rb') as src:r=self.decoder(src,sink,self.raw_bytes,self.raw_sha256,maximum_raw_bytes=self.maximum_raw_bytes)
  assert sink.bytes==self.raw_bytes and r['complete_source_SHA256_verified'];assert sha(self.path)==self.compressed_sha256;self.verified=r;return r
 @contextmanager
 def open(self,mode='r'):
  assert mode in ['r','rt','rb']
  if self.verified is None:self.verify()
  assert sha(self.path)==self.compressed_sha256
  with lzma.open(self.path,'rb' if mode=='rb' else 'rt') as stream:yield stream
  assert sha(self.path)==self.compressed_sha256,'Scientific archive changed during read'
