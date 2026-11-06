"""Replay the frozen two-face authoring plan into a fresh private directory."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

p=argparse.ArgumentParser(__doc__)
p.add_argument("source",type=Path);p.add_argument("plan",type=Path);p.add_argument("output",type=Path)
args=p.parse_args()
plan=json.loads(args.plan.read_text())
if args.output.exists() or hashlib.sha256(args.source.read_bytes()).hexdigest()!=plan["parent_sha256"]:
    raise ValueError("Frozen source and fresh output required")
with np.load(args.source,allow_pickle=False) as z:
    v,f=z["vertices"],z["triangles"]
if not np.array_equal(f[plan["changed_face_ids"]],plan["old_faces"]):
    raise ValueError("Old patch differs from the frozen authoring plan")
f[plan["changed_face_ids"]]=plan["new_faces"]
args.output.mkdir()
np.savez(args.output/"candidate.npz",vertices=v,triangles=f)
with (args.output/"candidate.meshbin").open("wb")as stream:
    stream.write(struct.pack("<QQ",len(v),len(f)))
    v.astype("<f8").tofile(stream);f.astype("<u8").tofile(stream)
print(json.dumps(dict(meshbin_sha256=hashlib.sha256((args.output/"candidate.meshbin").read_bytes()).hexdigest(),status="authored_independent_checks_required")))
