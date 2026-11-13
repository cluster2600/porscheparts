"""Shared helpers for the top-down 935 horizontal-fan CAD twin.

Units: the scan's source unit is 1 mm, as declared by the project owner on
2026-11-06 (owner declaration, not an instrument calibration).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROTOR_SCAN_SHA256 = "244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba"
DRIVE_SCAN_SHA256 = "6c0b12d4dd782fd4ecf4a5527d9b716ea5861abe1d7c369b3005910fa9ddb2f3"
SCALE_MM_PER_UNIT = 1.0
SCALE_BASIS = "owner_declared_2026-11-06"
BLADE_COUNT = 9
PARAMS = Path(__file__).resolve().parents[1] / "params"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_obj(path: Path, expected_sha: str, cache_dir: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Read vertices and triangles of an OBJ after checking its digest.

    Vertex order and indices are kept; nothing is welded or repaired.
    """
    path = Path(path)
    if cache_dir is not None:
        cache = Path(cache_dir) / f"{expected_sha[:16]}.npz"
        if cache.exists():
            z = np.load(cache)
            return z["v"], z["f"]
    got = sha256(path)
    if got != expected_sha:
        raise SystemExit(f"refusing {path}: sha256 {got} != pinned {expected_sha}")
    v, f = [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                v.append(line.split()[1:4])
            elif line.startswith("f "):
                f.append([int(t.split("/")[0]) for t in line.split()[1:4]])
    v = np.asarray(v, dtype=float) * SCALE_MM_PER_UNIT
    f = np.asarray(f, dtype=np.int64) - 1
    if cache_dir is not None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        np.savez(Path(cache_dir) / f"{expected_sha[:16]}.npz", v=v, f=f)
    return v, f


def tri_centroids_areas(v: np.ndarray, f: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = v[f]
    cr = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    a = 0.5 * np.linalg.norm(cr, axis=1)
    n = cr / np.maximum(2 * a, 1e-30)[:, None]
    return t.mean(axis=1), a, n


def load_frame(path: Path | None = None) -> dict:
    return json.loads(Path(path or PARAMS / "frame.json").read_text())


def to_fan(points: np.ndarray, frame: dict) -> np.ndarray:
    r = np.asarray(frame["rotation"])
    t = np.asarray(frame["translation_mm"])
    return points @ r.T + t


def cylindrical(p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.hypot(p[:, 0], p[:, 1]), np.arctan2(p[:, 1], p[:, 0]), p[:, 2]


def write_json(path: Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=False) + "\n")
