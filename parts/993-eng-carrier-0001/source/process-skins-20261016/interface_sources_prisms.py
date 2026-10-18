"""Decode every retained parent of positive closed prisms before classifying contacts.

This separate adapter does not admit the experimental Boolean result. Callers
must supply its native, snap, topology and distance proofs independently.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from interface_sources import signs_xy


ROLES=['positive_roof_prisms','mask','part','clip_bbox']
LOCAL_FACES=[[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]]
LOCAL_ROLES=['bottom','top','side_pq','side_pq','side_qr','side_qr','side_rp','side_rp']
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integers(value,name):
    value=np.asarray(value)
    if value.ndim!=1 or not np.isfinite(value).all() or not np.array_equal(value,value.astype(np.int64)):
        raise ValueError('Nonintegral or malformed '+name)
    return value.astype(np.int64)


def attach(volume,arrays,raw_arrays,audit,roofs_path,mask_path,part_path,schema_path):
    """Bind snap children through raw CSR parents to documented original leaves."""
    paths=[Path(p) for p in [roofs_path,mask_path,part_path]]
    schema_path=Path(schema_path);schema=json.loads(schema_path.read_text())
    if (schema.get('common_floor_z_mm')!=0 or schema.get('local_faces')!=LOCAL_FACES or
            schema.get('local_face_roles')!=LOCAL_ROLES or schema.get('leaf_role_order')!=ROLES):
        raise ValueError('Positive-prism face schema differs from the documented topology')
    if audit.get('leaf_role_order')!=ROLES or audit.get('input_sha256')!=[sha(p) for p in paths]:
        raise ValueError('Native prism leaf identity/order differs')
    leaves=[np.load(path,allow_pickle=False) for path in paths]
    roofs,mask,part=leaves;counts=[8*len(roofs['faces']),len(mask['faces']),len(part['faces']),12]
    if audit.get('leaf_face_counts')!=counts:raise ValueError('Native prism leaf face counts differ')
    offsets=np.r_[0,np.cumsum(counts)]
    raw_faces=np.asarray(raw_arrays['faces'])
    csr=integers(raw_arrays['all_parent_offsets'],'parent offsets')
    parents=integers(raw_arrays['all_parent_faces'],'parent faces')
    if (len(csr)!=len(raw_faces)+1 or not len(csr) or csr[0]!=0 or csr[-1]!=len(parents) or
            np.any(np.diff(csr)<=0) or np.any(parents<0) or np.any(parents>=offsets[-1])):
        raise ValueError('Every raw Boolean face must have valid complete parents')
    child=integers(arrays['autorefine_input_face'],'snap input face')
    if len(child)!=len(volume.faces) or np.any(child<0) or np.any(child>=len(raw_faces)):
        raise ValueError('Snap face lineage does not address the raw Boolean faces')
    for name in ['source_face','source']:
        final=integers(arrays[name],'final '+name);raw=integers(raw_arrays[name],'raw '+name)
        if len(raw)!=len(raw_faces) or not np.array_equal(final,raw[child]):
            raise ValueError('Snap primary ancestry differs from its raw input face')
    primary=integers(raw_arrays['source_face'],'primary parent')
    source=integers(raw_arrays['source'],'primary role')
    if not np.array_equal(source,np.searchsorted(offsets[1:],primary,side='right')):
        raise ValueError('Primary role and global parent index disagree')
    roof_ids=integers(roofs['source_face_ids'],'roof source IDs') if 'source_face_ids' in roofs else np.arange(len(roofs['faces']))
    if len(roof_ids)!=len(roofs['faces']) or len(np.unique(roof_ids))!=len(roof_ids):
        raise ValueError('Original roof IDs must be unique and complete')
    triangles=np.asarray(roofs['vertices'])[np.asarray(roofs['faces'])]
    if not np.isfinite(triangles).all() or np.any(triangles[:,:,2]<0) or np.any(signs_xy(triangles)==0):
        raise ValueError('Positive prisms require nondegenerate XY roofs above the common floor')
    part_signs=signs_xy(np.asarray(part['vertices'])[np.asarray(part['faces'])])
    # One classification per raw face, then the documented snap parent mapping.
    raw_kind=np.zeros(len(raw_faces),dtype=np.int8);raw_bottom=np.zeros(len(raw_faces),dtype=bool);ambiguous=0
    for face in range(len(raw_faces)):
        retained=parents[csr[face]:csr[face+1]]
        if len(np.unique(retained))!=len(retained) or primary[face]!=retained.min():
            raise ValueError('Raw complete parent list is duplicated or lacks its minimum primary')
        classifications=set()
        for parent in retained:
            role=int(np.searchsorted(offsets[1:],parent,side='right'));local=int(parent-offsets[role])
            if role==3:raise ValueError('An artificial clipping-box parent cannot define a support interface')
            if role==0:
                which=local%8
                value=-1 if which==0 else 1 if which==1 else 0
                raw_bottom[face]|=which==0
            elif role==2:value=-int(part_signs[local])
            else:value=0  # The XY mask is an artificial boundary.
            if value:classifications.add(value)
        if len(classifications)>1:raise ValueError('Complete Boolean parents disagree on upper/lower interface identity')
        raw_kind[face]=next(iter(classifications),0);ambiguous+=len(retained)>1
    kind=raw_kind[child]
    floor=np.all(volume.triangles[:,:,2]==0.,axis=1)
    if np.any(floor&(kind>0)):raise ValueError('An upper interface contradicts the actual plate plane')
    if np.any(raw_bottom[child]&~floor):
        raise ValueError('A positive-prism bottom was classified away from the common floor')
    kind[floor]=-1;volume.face_attributes['interface_kind']=kind
    for data in leaves:data.close()
    return dict(algorithm='all retained whole-triangle positive-prism CSR witnesses through snap input-face lineage',
        classification_scope='Positive whole-child containment witnesses only; absence of a role does not exclude partial contact with that leaf',
        leaf_role_order=ROLES,leaf_face_counts=counts,face_schema_sha256=sha(schema_path),
        source_meshes={name:dict(path=str(path),sha256=sha(path)) for name,path in zip(['roofs','mask','part'],paths)},
        ambiguous_raw_faces_with_all_parents_checked=int(ambiguous),contradictory_parents=0,clip_bbox_parents=0,
        final_face_classification_sha256=hashlib.sha256(kind.tobytes()).hexdigest(),
        upper_faces=int(np.sum(kind>0)),lower_faces=int(np.sum(kind<0)),faces_without_whole_parent_contact_witness=int(np.sum(kind==0)),
        plate_Z0_faces=int(floor.sum()))
