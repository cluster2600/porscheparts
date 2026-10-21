"""Pure original-index reference selection and saved ID-export verification."""
import hashlib
from pathlib import Path
import struct


def patch_reference_ids(faces, bad_face_ids, vertex_count):
    """Bad faces are independently classified beforehand; no geometric tolerance."""
    if type(vertex_count) is not int or vertex_count <= 0:
        raise ValueError("A positive original vertex count is required")
    for face in faces:
        if (len(face) != 3 or len(set(face)) != 3
                or any(type(i) is not int or not 0 <= i < vertex_count for i in face)):
            raise ValueError("Original ordered nondegenerate index triples required")
    if (len(set(bad_face_ids)) != len(bad_face_ids)
            or any(type(i) is not int or not 0 <= i < len(faces) for i in bad_face_ids)):
        raise ValueError("Unique original bad-face indices required")
    seeds = {i for face in bad_face_ids for i in faces[face]}
    selected = [i for i, face in enumerate(faces) if seeds.intersection(face)]
    vertices = sorted({v for i in selected for v in faces[i]})
    return selected, vertices


def id_bytes(ids):
    previous = -1
    for value in ids:
        if type(value) is not int or not previous < value < 2**64:
            raise ValueError("Strictly increasing uint64 original IDs required")
        previous = value
    return b"".join(struct.pack("<Q", value) for value in ids)


def verify_reference_exports(directory, face_ids, vertex_ids):
    result = {}
    for kind, ids in [("face", face_ids), ("vertex", vertex_ids)]:
        name = "patch-reference-" + kind + "-ids.u64"
        path = Path(directory) / name
        expected = id_bytes(ids)
        if not path.is_file() or path.is_symlink() or path.read_bytes() != expected:
            raise ValueError("Exact ordered original-reference export required: " + name)
        result[name] = dict(count=len(ids), bytes=len(expected),
                           sha256=hashlib.sha256(expected).hexdigest())
    return result
