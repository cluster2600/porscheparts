"""Measure acquired vertices against the actual reopened native STEP faces."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from inspect_wall_step import load


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('step','arrays','reference','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing exact-distance report refused.')
    input_hashes={name:sha(getattr(args,name)) for name in ('step','arrays','reference')}
    shape=load(args.step)
    with np.load(args.arrays,allow_pickle=False) as a:vertices=a['vertices']
    with np.load(args.reference,allow_pickle=False) as a:ids=a['source_vertex_ids']
    distances=[]
    for point in vertices[ids]:
        vertex=BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex()
        distance=BRepExtrema_DistShapeShape(vertex,shape);distance.Perform()
        if not distance.IsDone() or distance.NbSolution()<1:raise ValueError('Native distance failed')
        distances.append(distance.Value())
    d=np.asarray(distances);report={'source_vertices':len(ids),'p95_mm':float(np.quantile(d,.95)),
        'max_mm':float(d.max()),'all_vertices_within_exploratory_0p4mm':bool((d<=.4).all()),
        'input_sha256':input_hashes,'method':'OCCT native point-to-trimmed-face distance after STEP reload; no tessellation proxy',
        'physical_metrology':False}
    for name,digest in input_hashes.items():
        if sha(getattr(args,name))!=digest:raise SystemExit('Input changed during native distance assessment.')
    with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
