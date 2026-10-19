"""Keep repaired faces unknown while classifying verified original prism parents."""
import hashlib
from pathlib import Path

import numpy as np
import trimesh
from interface_sources_prisms import attach as original_attach

SOURCE=Path(__file__).resolve().parent


def attach(volume,final_arrays,raw_arrays,audit,roofs_path,mask_path,part_path,schema_path,final_to_original_raw_face):
    mapping=np.asarray(final_to_original_raw_face)
    if (mapping.ndim!=1 or len(mapping)!=len(volume.faces) or mapping.dtype.kind not in 'iu' or
        np.any(mapping < -1) or np.any(mapping>=len(raw_arrays['faces']))):
        raise ValueError('Final-to-original raw face map is invalid')
    known=np.flatnonzero(mapping>=0);unknown=np.flatnonzero(mapping==-1)
    kind=np.zeros(len(mapping),dtype=np.int8)
    subset=trimesh.Trimesh(volume.vertices,volume.faces[known],process=False)
    arrays={name:np.asarray(final_arrays[name])[known] for name in ['source_face','source']}
    arrays['autorefine_input_face']=mapping[known].astype(np.int64)
    if len(known):
        receipt=original_attach(subset,arrays,raw_arrays,audit,roofs_path,mask_path,part_path,schema_path)
        kind[known]=subset.face_attributes['interface_kind']
    else:raise ValueError('A prism envelope has no original contact witnesses')
    # The sentinel is never used to index a parent array. Even a Z0 unknown
    # face receives no historical or implicit floor anchor in this adapter.
    volume.face_attributes['interface_kind']=kind
    receipt.update(algorithm='verified known original-prism parents; explicitly repaired final faces remain unknown',
        unknown_final_face_ids=unknown.tolist(),unknown_final_faces=len(unknown),
        unknown_faces_receive_no_part_or_plate_anchor=True,
        interface_adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_adapter_sha256=hashlib.sha256((SOURCE/'interface_sources_prisms.py').read_bytes()).hexdigest(),
        final_face_classification_sha256=hashlib.sha256(kind.tobytes()).hexdigest(),
        upper_faces=int(np.sum(kind>0)),lower_faces=int(np.sum(kind<0)),
        faces_without_whole_parent_contact_witness=int(np.sum(kind==0)))
    return receipt
