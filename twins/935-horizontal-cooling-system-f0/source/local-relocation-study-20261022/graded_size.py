"""Nodal isotropic size field; nearest-vertex distance is not a wall-distance certificate."""
import numpy as np
from scipy.spatial import cKDTree


def nodal_sizes(vertices,faces,markers,near=.001,far=.015,growth=.2):
    v=np.asarray(vertices);f=np.asarray(faces);tags=np.asarray(markers)
    if (v.ndim!=2 or v.shape[1]!=3 or not len(v) or not np.isfinite(v).all()
            or f.ndim!=2 or f.shape[1]!=3 or not len(f) or not np.issubdtype(f.dtype,np.integer)
            or f.min()<0 or f.max()>=len(v) or tags.shape!=(len(f),)
            or not np.isin(tags,[1,2,3,4]).all() or not np.any(tags==4)
            or not np.isfinite([near,far,growth]).all() or not 0<near<=far or growth<=0):
        raise ValueError('Finite marked geometry and positive size parameters required')
    rotor=np.unique(f[tags==4]);distance=cKDTree(v[rotor]).query(v,workers=1)[0]
    sizes=np.clip(near+growth*distance,near,far)
    assert np.all(sizes[rotor]==near) and np.isfinite(sizes).all()
    return sizes
