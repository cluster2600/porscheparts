"""Read native legacy VTK traces and predict coupled linear interpolation."""
import re
import numpy as np


def vtk_field(path,name,count):
    data=path.read_bytes();lines=data.split(b'\n',4)
    if len(lines)<4 or lines[2] not in (b'ASCII',b'BINARY'):raise ValueError('Unsupported VTK encoding')
    m=re.search(rb'^'+re.escape(name.encode())+rb' ([1-3]) (\d+) (float|int)\r?\n',data,re.M)
    if not m or int(m[2])!=count:raise ValueError('Unexpected VTK field count')
    components=int(m[1]);size=count*components
    if lines[2]==b'BINARY':
        raw=data[m.end():m.end()+size*4]
        if len(raw)!=size*4:raise ValueError('Truncated VTK array')
        values=np.frombuffer(raw,dtype='>f4' if m[3]==b'float' else '>i4').astype(float)
    else:values=np.fromstring(data[m.end():].decode().split('\n\n')[0],sep=' ',count=size)
    if values.size!=size or not np.isfinite(values).all():raise ValueError('Invalid VTK array')
    return values.reshape(count,components)


def expected_trace(own_centres,neighbour_centres,face_centres,normals,own_values,neighbour_values,rotation):
    neighbour_centres=np.asarray(neighbour_centres)@np.asarray(rotation).T
    a=np.abs(np.einsum('ij,ij->i',face_centres-own_centres,normals));b=np.abs(np.einsum('ij,ij->i',face_centres-neighbour_centres,normals))
    if not np.isfinite(a+b).all() or np.any(a+b<=0):raise ValueError('Invalid interpolation distances')
    weight=b/(a+b)
    return weight[:,None]*own_values+(1-weight[:,None])*(neighbour_values@rotation.T),weight
