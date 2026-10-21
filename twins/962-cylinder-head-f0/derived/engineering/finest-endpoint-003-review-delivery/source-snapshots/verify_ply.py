"""Independent stdlib full PLY readback against the original 962SURF1 bytes."""
from pathlib import Path
import hashlib
import json
import math
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/"work/962-engineering/finest-endpoint-003-head-001/head-endpoint003/quality-candidate.bin"
PLY=OUT/"head-endpoint003-exact.ply"
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
export=json.loads((OUT/"PLY-export.json").read_text())
if sha(SOURCE)!=export["source_sha256"] or sha(PLY)!=export["PLY_sha256"]:
    raise ValueError("Bound completed format export required")
if (OUT/"PLY-independent-readback.json").exists():
    raise ValueError("Existing readback retained")
started=time.monotonic();source_lo=[math.inf]*3;source_hi=[-math.inf]*3
ply_lo=[math.inf]*3;ply_hi=[-math.inf]*3;count=0;face_count=0
with SOURCE.open("rb") as reference,PLY.open("rb") as candidate:
    fixed=reference.read(24);assert fixed[:8]==b"962SURF1"
    nv,nf=struct.unpack_from("<QQ",fixed,8)
    lines=[]
    while True:
        line=candidate.readline(4096)
        if not line or len(line)>=4096:raise ValueError("Bounded complete ASCII PLY header required")
        lines.append(line.decode("ascii").rstrip("\n"))
        if line==b"end_header\n":break
    if [line for line in lines if not line.startswith("comment ")] != [
        "ply","format binary_little_endian 1.0",f"element vertex {nv}",
        "property double x","property double y","property double z",f"element face {nf}",
        "property list uchar uint vertex_indices","end_header"]:
        raise ValueError("Exact standard little-endian double/uchar/uint layout required")
    for start in range(0,nv,32768):
        n=min(32768,nv-start);a=reference.read(24*n);b=candidate.read(24*n)
        if len(a)!=24*n or a!=b:raise ValueError("Full coordinate BYTES differ")
        for source_xyz,ply_xyz in zip(struct.iter_unpack("<ddd",a),struct.iter_unpack("<ddd",b)):
            for axis in range(3):
                if not math.isfinite(source_xyz[axis]) or not math.isfinite(ply_xyz[axis]):
                    raise ValueError("Nonfinite vertex")
                source_lo[axis]=min(source_lo[axis],source_xyz[axis]);source_hi[axis]=max(source_hi[axis],source_xyz[axis])
                ply_lo[axis]=min(ply_lo[axis],ply_xyz[axis]);ply_hi[axis]=max(ply_hi[axis],ply_xyz[axis])
            count+=1
    for start in range(0,nf,32768):
        n=min(32768,nf-start);a=reference.read(24*n);b=candidate.read(13*n)
        if len(a)!=24*n or len(b)!=13*n:raise ValueError("Complete oriented face payload required")
        for source_face,ply_face in zip(struct.iter_unpack("<QQQ",a),struct.iter_unpack("<BIII",b)):
            if ply_face[0]!=3 or tuple(ply_face[1:])!=source_face or max(source_face)>=nv:
                raise ValueError("Exact face orientation/index mismatch")
            face_count+=1
    if reference.read(1) or candidate.read(1):raise ValueError("Unexpected trailing payload")
if count!=nv or face_count!=nf or [source_lo,source_hi]!=[ply_lo,ply_hi]:
    raise ValueError("Complete counts/bounds mismatch")
if sha(SOURCE)!=export["source_sha256"] or sha(PLY)!=export["PLY_sha256"]:
    raise ValueError("Input changed during independent readback")
report=dict(schema="962-exact-PLY-independent-readback/v1",status="all_coordinate_bytes_and_oriented_faces_equal",
    source_sha256=export["source_sha256"],PLY_sha256=export["PLY_sha256"],
    verified_vertices=count,verified_oriented_faces=face_count,
    every_coordinate_byte_exact=True,coordinate_bytes_compared=24*nv,
    every_face_index_and_orientation_exact=True,all_list_counts_equal_3=True,
    source_bounds_mm=[source_lo,source_hi],PLY_bounds_mm=[ply_lo,ply_hi],
    bounds_exact=True,source_and_PLY_unchanged=True,
    verifier_implementation="Independent stdlib ASCII-header/struct parsing, no NumPy structured-face writer reused.",
    verifier_source_sha256=sha(Path(__file__)),writer_source_sha256=export["writer_source_sha256"],
    original_export_receipt_sha256=sha(OUT/"PLY-export.json"),python=sys.version,
    wall_seconds=time.monotonic()-started,geometry_sampling_used=False,
    viewer_or_renderer_executed=False,native_physics_executed=False,manufacturing_authorized=False)
with (OUT/"PLY-independent-readback.json").open("x") as stream:json.dump(report,stream,indent=2);stream.write("\n")
print(json.dumps(report,indent=2))
