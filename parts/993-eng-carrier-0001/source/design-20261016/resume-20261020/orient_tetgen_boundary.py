"""Normalize the TetGen skin winding against the already audited input PLC.

Require an exact triangle/coordinate bijection before changing any winding.
Volume vertices and tetrahedron arrays remain byte-for-byte identical. The
original mesher files and its inward-skin audit remain immutable evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def cyclic(face):
    a,b,c=map(int,face)
    return min((a,b,c),(b,c,a),(c,a,b))


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--volume',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    with np.load(a.volume,allow_pickle=False) as data:
        vertices=data['vertices'].copy();cells=data['tetrahedra'].copy();raw=data['boundary'].copy()
    with a.reference.open() as stream:
        nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    lookup={tuple(row):i for i,row in enumerate(vertices)}
    if len(lookup)!=len(vertices):raise ValueError('Coincident indexed vertices')
    mapping=np.array([lookup[tuple(row)]for row in v],dtype=np.int64)
    outward=mapping[f]
    source={tuple(sorted(row)):cyclic(row)for row in outward}
    if len(source)!=nf or len(raw)!=nf:raise ValueError('Triangle count or uniqueness differs')
    same=reversed_count=0
    seen=set()
    for row in raw:
        key=tuple(sorted(row))
        if key in seen or key not in source:raise ValueError('Boundary triangle bijection failed')
        seen.add(key)
        if cyclic(row)==source[key]:same+=1
        elif cyclic(row[::-1])==source[key]:reversed_count+=1
        else:raise ValueError('Boundary permutation differs')
    if same and reversed_count:raise ValueError('Mixed raw winding; refuse normalization')
    np.savez_compressed(a.output/'volume.npz',vertices=vertices,tetrahedra=cells,boundary=outward)
    shutil.copyfile(a.reference,a.output/'boundary.mesh64')
    with np.load(a.output/'volume.npz',allow_pickle=False) as data:
        unchanged=all(data[k].dtype==array.dtype and data[k].shape==array.shape and data[k].tobytes()==array.tobytes() for k,array in [('vertices',vertices),('tetrahedra',cells)])
        if not unchanged:raise ValueError('Volume arrays changed')
    report=dict(status='exact_boundary_bijection_and_outward_winding_passed',raw_same_winding_faces=same,
        raw_reversed_winding_faces=reversed_count,boundary_faces=nf,volume_arrays_byte_identical=unchanged,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.volume,a.reference,Path(__file__)]},
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.output/'volume.npz',a.output/'boundary.mesh64']},
        mechanical_mesh_admitted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','raw_same_winding_faces','raw_reversed_winding_faces','volume_arrays_byte_identical']}))

if __name__=='__main__':main()
