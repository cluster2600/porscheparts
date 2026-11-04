"""Independent normal/edge audit of the native explicit-constraint classification."""
import argparse
import json
from pathlib import Path
import numpy as np
from trial_planar_flips import sha, save_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','protected','native','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists(): raise SystemExit('Existing feasibility assessment refused.')
    with np.load(args.parent,allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
    protected=np.load(args.protected,allow_pickle=False)
    pm=np.zeros(len(f),bool);pm[protected]=True
    points=v[f];cross=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])
    norm=np.linalg.norm(cross,axis=1)
    if (norm<=0).any(): raise SystemExit('Degenerate parent faces.')
    normal=cross/norm[:,None]
    edges=np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]))
    edge_keys=edges.min(1)*len(v)+edges.max(1);order=np.argsort(edge_keys);ordered=edge_keys[order]
    if not np.all(ordered[::2]==ordered[1::2]) or np.any(ordered[1:-1:2]==ordered[2::2]):
        raise SystemExit('Expected exactly two faces per edge.')
    faces=np.tile(np.arange(len(f)),3)[order].reshape(-1,2)
    dot=np.einsum('ij,ij->i',normal[faces[:,0]],normal[faces[:,1]])
    locked=pm[faces].any(1)|(dot<np.cos(np.deg2rad(30)))
    face_locks=np.zeros(len(f),np.uint8);np.add.at(face_locks,faces[locked].reshape(-1),1)
    immutable=face_locks==3
    quality=2*np.sqrt(3)*norm/np.sum((points[:,1]-points[:,0])**2+(points[:,2]-points[:,0])**2+(points[:,2]-points[:,1])**2,axis=1)
    bad=quality<.01;locked_keys=ordered[::2][locked]
    locked_vertices=np.unique(np.concatenate((locked_keys//len(v),locked_keys%len(v))))
    native=json.loads(args.native.read_text())
    report={'locked_edges_independent':int(locked.sum()),'locked_vertices_independent':len(locked_vertices),
        'immutable_triangle_bound':int(immutable.sum()),'original_bad_triangles':int(bad.sum()),
        'bad_triangles_with_all_three_edges_locked':int((bad&immutable).sum()),
        'best_possible_bad_triangle_reduction_if_all_locked_edges_preserved':1-int((bad&immutable).sum())/int(bad.sum()),
        'native_counts_match':native['locked_edges']==int(locked.sum()) and native['locked_vertices']==len(locked_vertices),
        'input_hashes':{name:sha(getattr(args,name)) for name in ('parent','protected','native')},
        'scope':'Necessary quality-feasibility bound only; no full remesh or physical acceptance.'}
    save_json(args.output,report);print(json.dumps(report))
    if not report['native_counts_match']: raise SystemExit(1)


if __name__=='__main__':
    main()
