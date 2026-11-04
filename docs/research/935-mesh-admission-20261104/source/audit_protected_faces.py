"""Independently distinguish roundoff from changes in protected mesh regions."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from trial_planar_flips import sha, save_json


def keys(f):
    first = f.argmin(axis=1)
    cyclic = np.take_along_axis(f, (first[:,None]+np.arange(3)) % 3, axis=1)
    return np.ascontiguousarray(cyclic, dtype=np.int64).view('V24').reshape(-1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'candidate', 'protected', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Existing diagnostic refused.')
    with np.load(args.parent, allow_pickle=False) as a: v,f=a['vertices'],a['triangles']
    with np.load(args.candidate, allow_pickle=False) as a: v2,f2=a['vertices'],a['triangles']
    protected=np.load(args.protected, allow_pickle=False)
    unique=np.unique(f[protected]); d,idx=cKDTree(v2).query(v[unique])
    mapped=np.full(len(v),-1,dtype=np.int64);mapped[unique]=idx
    matched=np.isin(keys(mapped[f[protected]]),keys(f2))
    close=np.zeros(len(v),bool);close[unique]=d<=1e-10
    allclose=close[f[protected]].all(axis=1)
    result={'tolerance_mm':1e-10,'protected_faces':len(protected),'protected_vertices':len(unique),
        'protected_vertices_displaced_above_tolerance':int((d>1e-10).sum()),
        'max_protected_vertex_nearest_distance_mm':float(d.max()),
        'protected_faces_without_same_oriented_connectivity_and_close_vertices':int((~(matched&allclose)).sum()),
        'protected_faces_with_all_original_vertices_close_but_connectivity_changed':int((~matched&allclose).sum()),
        'input_sha256':{name:sha(getattr(args,name)) for name in ('parent','candidate','protected')},
        'scope':'Independent nearest-coordinate/index diagnostic; the original exact-preservation gate is unchanged.'}
    save_json(args.output,result);print(json.dumps(result))


if __name__ == '__main__':
    main()
