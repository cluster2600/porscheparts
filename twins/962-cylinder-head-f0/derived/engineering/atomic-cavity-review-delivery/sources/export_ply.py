"""One lossless PLY format export of the fixed reviewed indexed surface."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT/"work/962-engineering/atomic-cavity-head-001/head-atomic002/candidate.bin"
TARGET = OUT/"head-atomic002-exact.ply"
EXPECTED = "1f9dbd4cda61c7b58084479ebb165fb01280fa831752dc0da18517e548131b1a"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
if TARGET.exists() or TARGET.is_symlink() or sha(SOURCE) != EXPECTED:
    raise ValueError("Fresh output and exact reviewed source required")
started = time.monotonic()
with SOURCE.open("rb") as stream:
    fixed = stream.read(24)
if fixed[:8] != b"962SURF1" or struct.unpack_from("<QQ",fixed,8) != (901727,1803870):
    raise ValueError("Exact indexed input header required")
nv,nf=struct.unpack_from("<QQ",fixed,8)
if SOURCE.stat().st_size != 24+24*(nv+nf):
    raise ValueError("Complete fixed indexed payload required")
header=("ply\nformat binary_little_endian 1.0\n"
        "comment Numerical local/global surface review only; no volume mesh or physics qualification\n"
        "comment Coordinates are millimetres; PLY has no standardized unit metadata\n"
        "comment source_962SURF1_sha256 "+EXPECTED+"\n"
        f"element vertex {nv}\nproperty double x\nproperty double y\nproperty double z\n"
        f"element face {nf}\nproperty list uchar uint vertex_indices\nend_header\n").encode("ascii")
points=np.memmap(SOURCE,mode="r",dtype="<f8",offset=24,shape=(nv,3))
faces=np.memmap(SOURCE,mode="r",dtype="<u8",offset=24+24*nv,shape=(nf,3))
if not np.isfinite(points).all() or faces.max() >= nv or nv>2**32:
    raise ValueError("Finite points and uint32-compatible valid indices required")
face_dtype=np.dtype([("count","u1"),("vertices","<u4",(3,))],align=False)
assert face_dtype.itemsize==13
with TARGET.open("xb") as output:
    output.write(header)
    with SOURCE.open("rb") as stream:
        stream.seek(24);remaining=nv*24
        while remaining:
            block=stream.read(min(1048576,remaining))
            if not block:raise ValueError("Truncated point payload")
            output.write(block);remaining-=len(block)
    for start in range(0,nf,65536):
        source=faces[start:start+65536];chunk=np.empty(len(source),dtype=face_dtype)
        chunk["count"]=3;chunk["vertices"]=source
        output.write(chunk.tobytes())
if sha(SOURCE)!=EXPECTED or TARGET.stat().st_size != len(header)+nv*24+nf*13:
    raise ValueError("Export source changed or output incomplete")
report=dict(schema="962-exact-binary-PLY-export/v1",status="format_export_complete_independent_readback_pending",
    source_sha256=EXPECTED,PLY_sha256=sha(TARGET),PLY_bytes=TARGET.stat().st_size,
    PLY_header_bytes=len(header),vertices=nv,oriented_triangles=nf,
    points_encoding="little-endian IEEE754 binary64 xyz, copied byte-for-byte",
    face_encoding="one uint8 list count3 followed by three little-endian uint32 indices",
    source_index_min=int(faces.min()),source_index_max=int(faces.max()),
    source_bounds_mm=[points.min(axis=0).tolist(),points.max(axis=0).tolist()],
    coordinates_transformed_or_rounded=False,geometry_regenerated=False,
    source_unchanged=True,writer_source_sha256=sha(Path(__file__)),
    python=sys.version,numpy=np.__version__,wall_seconds=time.monotonic()-started,
    viewer_or_renderer_executed=False,native_physics_executed=False,manufacturing_authorized=False)
with (OUT/"PLY-export.json").open("x") as stream:json.dump(report,stream,indent=2);stream.write("\n")
print(json.dumps(report,indent=2))
