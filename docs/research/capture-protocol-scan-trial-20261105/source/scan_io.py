"""Load the 935 scan OBJ after checking its SHA-256, with a local array cache.

The OBJ stays outside Git. The cache is written next to the OBJ, never in the
repository.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

EXPECTED_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> tuple[np.ndarray, np.ndarray, str]:
    digest = sha256(path)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"refused: {path} has SHA-256 {digest}, expected {EXPECTED_SHA256}")
    cache = path.with_suffix(".arrays.npz")
    if cache.exists():
        data = np.load(cache)
        if str(data["sha256"]) == digest:
            return data["v"], data["f"], digest
    verts: list[list[float]] = []
    faces: list[list[int]] = []
    with path.open() as f:
        for line in f:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                faces.append([int(tok.split("/")[0]) - 1 for tok in line.split()[1:4]])
    v = np.asarray(verts, dtype=np.float64)
    fa = np.asarray(faces, dtype=np.int64)
    np.savez(cache, v=v, f=fa, sha256=np.array(digest))
    return v, fa, digest
