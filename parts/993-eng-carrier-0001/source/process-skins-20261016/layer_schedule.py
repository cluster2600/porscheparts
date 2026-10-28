"""Exact proof that an original vertical chart exposes no segment on a frozen schedule."""
from fractions import Fraction as Q
import hashlib
import numpy as np


def calendar(height,layer_height):
    import math
    return np.asarray([(i+.5)*layer_height for i in range(math.ceil(height/layer_height))],dtype=np.float64)


def no_exposure(mesh,face_ids,planes):
    planes=np.asarray(planes,dtype=np.float64)
    if planes.ndim!=1 or not len(planes) or not np.isfinite(planes).all() or np.any(np.diff(planes)<=0):
        raise ValueError('Exposure planes must be finite and strictly increasing')
    ids=np.asarray(face_ids);triangles=np.asarray(mesh.vertices)[mesh.faces[ids]]
    bounds=np.stack([triangles.min(axis=(0,1)),triangles.max(axis=(0,1))])
    selected=np.flatnonzero((planes>=bounds[0,2])&(planes<=bounds[1,2]))
    checks=[]
    for index in selected:
        z=Q(float(planes[index]));positive=0
        for triangle in triangles:
            if planes[index]<triangle[:,2].min() or planes[index]>triangle[:,2].max():continue
            p=[tuple(Q(float(c)) for c in point) for point in triangle];points=set()
            for a,b in zip(p,p[1:]+p[:1]):
                if a[2]==z:points.add(a)
                if (a[2]<z<b[2]) or (b[2]<z<a[2]):
                    t=(z-a[2])/(b[2]-a[2]);points.add(tuple(a[k]+t*(b[k]-a[k]) for k in range(3)))
            if len(points)>1:return None
        checks.append(dict(layer=int(index),z_mm=float(planes[index]),positive_exact_triangle_sections=positive))
        if positive:return None
    preceding=np.flatnonzero(planes<bounds[0,2]);following=np.flatnonzero(planes>bounds[1,2])
    neighbor=lambda a:None if not len(a) else dict(layer=int(a[0]),z_mm=float(planes[a[0]]))
    return dict(status='excluded_no_positive_section_on_actual_schedule',source_face_indices=ids.tolist(),
        source_area_mm2=float(mesh.area_faces[ids].sum()),bounds_mm=bounds.tolist(),
        calendar_sha256=hashlib.sha256(planes.tobytes()).hexdigest(),n_calendar_planes=len(planes),
        first_plane_z_mm=float(planes[0]),last_plane_z_mm=float(planes[-1]),
        concerned_planes=checks,preceding_plane=neighbor(preceding[-1:]),following_plane=neighbor(following[:1]),
        proof='Exact rational intersections of original IEEE triangle edges on every potentially intersecting IEEE layer plane; all other planes strictly outside source Z bounds.',
        original_envelope_unchanged=True)
