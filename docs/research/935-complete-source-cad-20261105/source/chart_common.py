"""Immutable source-CAD job loading; geometry and private parameters stay local."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2)+"\n")


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def job(path):
    value = json.loads(path.read_text()); root = path.parent.resolve()
    assert value["schema"] == "935-complete-source-chart-job-1"
    assert value["chunk_count"] == 83 and value["max_chunk_faces"] == 30000
    assert len({row["path"] for row in value["files"]}) == len(value["files"])
    assert value["source_arrays_sha256"] == "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    assert value["source_plan_sha256"] == "f26389c910ded839b94de910f495c0110a0fd103fc860af2b4a07e25139d5026"
    for row in value["files"]:
        p = root/row["path"]
        assert p.resolve().is_relative_to(root) and not p.is_symlink() and sha(p) == row["sha256"]
    assert sha(root/value["source_arrays"]) == value["source_arrays_sha256"]
    assert sha(root/value["source_plan"]) == value["source_plan_sha256"]
    return value, root


def selected(value, root, chunk):
    assert type(chunk) is int and 0 <= chunk < value["chunk_count"]
    with np.load(root/value["source_arrays"], allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    with np.load(root/value["source_plan"], allow_pickle=False) as data:
        owner = data["source_chunk_owner"]; reasons = data["source_quarantine_reason_bits"]
    assert len(owner) == len(reasons) == len(faces)
    ids = np.flatnonzero(owner == chunk)
    assert 0 < len(ids) <= value["max_chunk_faces"] == 30000 and not reasons[ids].any()
    return vertices, faces[ids], ids


def fixture(name):
    # Independently fixed analytic coordinates; no acquired data is used here.
    if name == "square":
        vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
        faces = [[0, 1, 2], [0, 2, 3]]
    elif name == "point-contact":
        vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]]
        faces = [[0, 1, 2], [0, 3, 4]]
    else:
        raise ValueError("Unknown independent synthetic source contract")
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64), np.arange(2, dtype=np.int64)
