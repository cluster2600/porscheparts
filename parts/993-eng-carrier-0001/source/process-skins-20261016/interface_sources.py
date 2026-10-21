"""Bind true support interfaces to retained native CSG face ancestry, never ring slope alone."""
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import numpy as np


def signs_xy(triangles):
    a,b,c=np.asarray(triangles).transpose(1,0,2)
    determinant=np.cross(b[:,:2]-a[:,:2],c[:,:2]-a[:,:2]);scale=np.max(abs(triangles),axis=(1,2))
    result=np.sign(determinant).astype(np.int8)
    uncertain=np.flatnonzero(abs(determinant)<=32*np.finfo(float).eps*scale*scale)
    for i in uncertain:
        p=[[Q(float(x)) for x in point[:2]] for point in triangles[i]]
        d=(p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0])
        result[i]=int(d>0)-int(d<0)
    return result


def attach(volume,arrays,receipt,leaves):
    roles=receipt.get('leaf_role_order')
    if roles is None and receipt['algorithm']=='difference(intersection(chain,mask),part) in one native CSGTree':
        roles=['chain','mask','part']
    if roles is None:raise ValueError('Native CSG leaf ancestry order is not documented')
    counts=receipt['leaf_face_counts'];offsets=np.r_[0,np.cumsum(counts)]
    original=np.asarray(arrays['source_face']);source=np.asarray(arrays['source'])
    if (len(original)!=len(volume.faces) or len(source)!=len(original) or not np.isfinite(original).all() or
            not np.array_equal(original,original.astype(np.int64)) or not np.array_equal(source,source.astype(np.int64))):
        raise ValueError('Native interface ancestry is missing or nonintegral')
    original=original.astype(np.int64);source=source.astype(np.int64);kind=np.zeros(len(source),dtype=np.int8)
    payload={}
    for i,role in enumerate(roles):
        selected=np.flatnonzero(source==i)
        if not len(selected):continue
        ids=original[selected]-offsets[i]
        if np.any(ids<0) or np.any(ids>=counts[i]):raise ValueError('Native interface ancestry index is outside its leaf')
        if role in ['mask','clip_bbox']:
            # Their side walls and artificial top are never a part anchor.
            continue
        path=Path(leaves[role]);data=np.load(path,allow_pickle=False)
        if len(data['faces'])!=counts[i]:raise ValueError('Native interface leaf face count differs')
        unique,inverse=np.unique(ids,return_inverse=True)
        triangle=data['vertices'][data['faces'][unique]];orientation=signs_xy(triangle)[inverse]
        if role=='part':kind[selected]=-orientation
        elif role=='chain':kind[selected]=np.maximum(orientation,0)
        else:raise ValueError('Unknown native CSG interface role')
        payload[role]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),faces=len(data['faces']))
    floor=np.all(volume.triangles[:,:,2]==0.,axis=1);kind[floor]=-1
    volume.face_attributes['interface_kind']=kind
    return dict(algorithm='native_CSG_source_face_ancestry; mask/bbox sides are not anchors; exact original XY orientation; actual Z0 is plate',
        leaf_role_order=roles,leaf_face_counts=counts,source_meshes=payload,
        final_face_classification_sha256=hashlib.sha256(kind.tobytes()).hexdigest(),
        upper_faces=int(np.sum(kind>0)),lower_faces=int(np.sum(kind<0)),unanchored_side_faces=int(np.sum(kind==0)),
        plate_Z0_faces=int(floor.sum()))


def fixture(volume):
    """Known standalone witnesses explicitly declare their own top/bottom faces."""
    volume.face_attributes['interface_kind']=signs_xy(volume.triangles)
    return dict(algorithm='declared_standalone_fixture_volume_exact_face_orientation')


def from_store(store,row,volume):
    audit=store._receipt(row['native_audit']);receipt=store._receipt(audit['csg_receipt'])
    arrays=np.load(store.path/row['envelope'],allow_pickle=False)
    leaves={role:store.path/('input-'+row[role]) for role in ['chain','mask']}
    leaves['part']=store.path/'input-part.npz'
    return attach(volume,arrays,receipt,leaves)
