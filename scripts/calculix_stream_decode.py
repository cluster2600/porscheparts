"""Decode exact scientific bytes with bounded chunks and 64-bit-sized counts."""
import hashlib,lzma
CHUNK=1024**2
def decode(source,destination,expected_bytes,expected_sha256,maximum_raw_bytes=2_500_000_000):
 assert type(expected_bytes) is int and type(maximum_raw_bytes) is int and 0<expected_bytes<=maximum_raw_bytes
 decoder=lzma.LZMADecompressor(format=lzma.FORMAT_XZ,memlimit=256*1024**2);count=0;largest=0;digest=hashlib.sha256()
 while True:
  compressed=source.read(CHUNK)
  if not compressed:break
  assert not decoder.eof,'Trailing or concatenated compressed stream'
  block=decoder.decompress(compressed,max_length=CHUNK)
  while True:
   if block:
    count+=len(block);largest=max(largest,len(block));assert count<=expected_bytes,'Decoded scientific size exceeds admitted source'
    digest.update(block);destination.write(block)
   if decoder.eof:assert not decoder.unused_data,'Trailing compressed bytes';break
   if decoder.needs_input:break
   block=decoder.decompress(b'',max_length=CHUNK)
 assert decoder.eof and count==expected_bytes and digest.hexdigest()==expected_sha256,'Incomplete or changed complete scientific field'
 return dict(raw_bytes=count,raw_sha256=digest.hexdigest(),maximum_decoded_chunk_bytes=largest,complete_source_SHA256_verified=True)
