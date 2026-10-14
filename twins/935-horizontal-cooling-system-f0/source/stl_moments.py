#!/usr/bin/env python3
"""Bounded-memory tetrahedral moments of an already-audited binary STL in mm."""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

DTYPE = np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])


def remove_declared_voxel_specks(source, output, regions):
    """Remove explicitly classified 12-face voxel specks; preserve all other bytes."""
    bounds = []
    for region in regions:
        box = np.asarray(region['bounds_mm'],dtype=float)
        if region['classification'] != 'generated_voxel_speck' or region['triangles'] != 12 or box.shape != (2,3) or not np.isfinite(box).all() or np.any(box[1] <= box[0]) or np.max(box[1]-box[0]) > 1:
            raise ValueError('Explicit finite generated-voxel cube regions required')
        bounds.append(box)
    if not bounds:
        raise ValueError('Explicit regions required')
    removed = np.zeros(len(bounds),dtype=int)
    with Path(source).open('rb') as stream, Path(output).open('xb') as target:
        header=stream.read(84)
        if len(header)!=84:raise ValueError('Binary STL required')
        count=struct.unpack('<I',header[80:84])[0]
        if Path(source).stat().st_size != 84+count*50:raise ValueError('STL length mismatch')
        target.write(header)
        while True:
            records=np.fromfile(stream,dtype=DTYPE,count=100000)
            if not len(records):break
            keep=np.ones(len(records),dtype=bool)
            for i,box in enumerate(bounds):
                # The bounds come from independent topology zoning; tolerance only
                # accounts for its text export, never changes retained vertices.
                selected=np.all(records['vertices'] >= box[0]-.001,axis=(1,2)) & np.all(records['vertices'] <= box[1]+.001,axis=(1,2))
                if np.any(selected & ~keep):raise ValueError('Overlapping declared regions')
                removed[i]+=int(selected.sum());keep &= ~selected
            target.write(records[keep].tobytes())
        if not np.all(removed==12):raise ValueError('Region counts disagree; rejected output retained')
        target.seek(80);target.write(struct.pack('<I',count-int(removed.sum())))
    return {'triangles_removed_per_region':removed.tolist(),'retained_coordinates_unchanged':True}


def moments(path):
    volume, first, second = 0., np.zeros(3), np.zeros((3,3))
    path = Path(path)
    with path.open('rb') as stream:
        header = stream.read(84)
        if len(header) != 84:
            raise ValueError('Binary STL header required')
        count = struct.unpack('<I',header[80:84])[0]
        if not count or path.stat().st_size != 84 + count * 50:
            raise ValueError('Binary STL length/triangle-count mismatch')
        remaining = count
        while remaining:
            records = np.fromfile(stream,dtype=DTYPE,count=min(remaining,100000))
            if not len(records):
                raise ValueError('Truncated STL')
            p = records['vertices'].astype(float)
            if not np.isfinite(p).all():
                raise ValueError('Finite STL coordinates required')
            signed = np.einsum('ij,ij->i',p[:,0],np.cross(p[:,1],p[:,2])) / 6
            sums = p.sum(axis=1)
            volume += signed.sum()
            first += np.einsum('n,ni->i',signed,sums) / 4
            second += (np.einsum('n,ni,nj->ij',signed,sums,sums) +
                       np.einsum('n,nki,nkj->ij',signed,p,p)) / 20
            remaining -= len(records)
    inertia = np.trace(second) * np.eye(3) - second
    eigenvalues = np.linalg.eigvalsh(inertia)
    if not np.isfinite(volume) or volume <= 0 or not np.isfinite(inertia).all() or eigenvalues.min() <= 0:
        raise ValueError('Positive finite volume and inertia required')
    return {'conditional_volume_mm3':float(volume), 'centroid_mm':(first/volume).tolist(),
        'volume_inertia_about_origin_mm5':inertia.tolist(), 'principal_volume_inertias_mm5':eigenvalues.tolist(),
        'triangles':count, 'topology_checked_by_this_function':False}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mesh',type=Path)
    print(json.dumps(moments(parser.parse_args().mesh),indent=2,allow_nan=False))
