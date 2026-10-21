"""Remove only triangles whose IEEE coordinates have exactly zero rational area."""
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import numpy as np


def retained_faces(vertices,faces,component_ranges=None):
    vertices=np.asarray(vertices);faces=np.asarray(faces);triangles=vertices[faces]
    magnitude=np.max(abs(triangles),axis=(1,2))
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    safe=(magnitude>=2.**-400)&(magnitude<=2.**400)&(np.max(abs(normals),axis=1)>32*np.finfo(float).eps*magnitude*magnitude)
    removed=[]
    for index in np.flatnonzero(~safe):
        a,b,c=[[Q(float(value)) for value in point] for point in triangles[index]]
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        if not any(cross):removed.append(int(index))
    keep=np.ones(len(faces),dtype=bool);keep[removed]=False
    if not np.any(keep):raise ValueError('An entire material component collapses to exact zero-area triangles')
    coverage=None
    if removed:
        path=Path(__file__).resolve().parent/'exact_zero_face_coverage.py'
        if not path.is_file():path=Path(__file__).resolve().parent.parent/'process-scanpath-audit-20261016/exact_zero_face_coverage.py'
        spec=importlib.util.spec_from_file_location('carrier_zero_area_coverage',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        ranges=component_ranges or [(0,len(faces))]
        cursor=0;rows=[]
        for component_index,(begin,end) in enumerate(ranges):
            if begin!=cursor or not begin<end<=len(faces):raise ValueError('Zero-face coverage ranges must partition material components')
            cursor=end;local=[i-begin for i in removed if begin<=i<end]
            if local:
                row=module.certify_zero_face_coverage(vertices,faces[begin:end],local)
                if row['status']!='passed':raise ValueError('An exact zero-area triangle has geometry not covered by positive-area faces of its own component')
                rows.append(dict(component_index=component_index,face_range=[begin,end],receipt=row))
        if cursor!=len(faces):raise ValueError('Zero-face coverage omitted material faces')
        coverage=dict(status='passed',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),components=rows)
    return keep,dict(method='exact rational cross product of original IEEE vertices; nonzero triangles retained',
        input_faces=len(faces),output_faces=int(keep.sum()),exact_zero_area_removed_faces=removed,
        positive_area_triangles_removed=0,coordinate_displacement_mm=0.,same_component_coverage=coverage)
