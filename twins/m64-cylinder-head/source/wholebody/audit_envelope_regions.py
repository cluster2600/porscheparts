#!/usr/bin/env python3
"""Independent region and boundary-edge audit of a completed private trial."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from trial_meshers_2026 import boundary,normalize_convention,native


def audit(points,cells):
    cells,reversed_convention=normalize_convention(points,cells)
    if reversed_convention or len(cells)>3000000:raise ValueError('bounded_positive_mesh_required')
    count=len(cells)
    faces=np.concatenate([np.sort(cells[:,ids],axis=1) for ids in ((1,2,3),(0,3,2),(0,1,3),(0,2,1))])
    owners=np.tile(np.arange(count),4);order=np.lexsort(faces.T[::-1])
    faces,owners=faces[order],owners[order]
    same=np.all(faces[1:]==faces[:-1],axis=1)
    left,right=owners[:-1][same],owners[1:][same]
    graph=coo_matrix((np.ones(len(left),dtype=np.uint8),(left,right)),shape=(count,count)).tocsr()
    nregions,labels=connected_components(graph,directed=False)
    triangles=boundary(cells)
    edges=np.concatenate([triangles[:,ids] for ids in ((0,1),(1,2),(2,0))])
    _,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    signs=np.where(edges[:,0]<edges[:,1],1,-1)
    balances=np.bincount(inverse,weights=signs)
    volumes=np.linalg.det(points[cells][:,1:]-points[cells][:,[0]])/6
    used=np.unique(cells)
    return dict(regions=[dict(label=i,tetrahedra=int((labels==i).sum()),
        volume=math.fsum(map(float,volumes[labels==i]))) for i in range(nregions)],
        tetra_components=int(nregions),boundary_triangles=len(triangles),
        boundary_edges=len(counts),boundary_edges_not_incident_twice=int((counts!=2).sum()),
        boundary_edges_with_unbalanced_orientation=int((balances!=0).sum()),
        duplicate_coordinate_vertices=len(used)-len(np.unique(points[used],axis=0)),
        vertex_link_manifoldness_checked=False,geometric_self_intersections_checked=False),labels


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();mesh=args.trial/'output-private.npz';receipt=args.trial/'report.json'
    if args.output.exists() or mesh.is_symlink() or receipt.is_symlink():raise ValueError('fresh_private_output_required')
    pins={p:native.sha256(p) for p in (mesh,receipt,Path(__file__))}
    producer=json.loads(receipt.read_text())
    if producer.get('status')!='completed_diagnostic_only' or producer.get('inputs_and_sources_unchanged') is not True:
        raise ValueError('completed_unchanged_trial_required')
    with np.load(mesh,allow_pickle=False) as data:points,cells=data['points'],data['cells']
    result,labels=audit(points,cells)
    args.output.mkdir(mode=0o700,parents=True)
    for row in result['regions']:
        if row['tetrahedra']<=100:
            selected=cells[labels==row['label']];used=np.unique(selected)
            np.savez_compressed(args.output/f"component-{row['label']}-private.npz",
                points=points[used],cells=np.searchsorted(used,selected))
    result.update(schema='m64-envelope-region-audit/v1',input_sha256=pins[mesh],
        producer_receipt_sha256=pins[receipt],source_sha256=pins[Path(__file__)],
        inputs_unchanged=all(native.sha256(p)==s for p,s in pins.items()),
        removed_elements=0,native_CAD_conformance_certified=False,manufacturing_authorized=False)
    native.save(args.output/'report.json',result);print(json.dumps(result))
