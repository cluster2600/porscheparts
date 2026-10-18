"""Held exact oriented-coordinate cancellation; no distance query or geometry export."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve()
PREP = HERE.parent
ORIGINAL = ROOT/'work/962-engineering/analysis-envelope-025-003/exact-input.bin'
CANDIDATE = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin'
OUTPUT = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-mask-001'
EXPECTED_COUNTS = dict(original_vertices=902145, original_faces=1804706,
                       candidate_vertices=871731, candidate_faces=1743878)
CHUNK = 65536
np = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"962SURF1":
        raise ValueError("Complete binary indexed surface required")
    nv, nf = struct.unpack_from("<QQ", header, 8)
    if not nv or not nf or path.stat().st_size != 24+24*(nv+nf):
        raise ValueError("Complete surface payload and counts required")
    p = np.memmap(path, mode="r", dtype="<f8", offset=24, shape=(nv, 3))
    f = np.memmap(path, mode="r", dtype="<u8", offset=24+24*nv, shape=(nf, 3))
    if not np.isfinite(p).all() or f.max() >= nv:
        raise ValueError("Finite valid coordinate/index arrays required")
    return p, f


def coordinate_faces(points, faces):
    """Exact finite binary64 coordinates, cyclic orientation, signed-zero neutral."""
    xyz = np.asarray(points[faces], dtype="<f8").copy()
    if (not np.isfinite(xyz).all() or
            not (np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0],
                                        xyz[:, 2]-xyz[:, 0]), axis=1) > 0).all()):
        raise ValueError("Finite nondegenerate triangles required")
    xyz[xyz == 0] = 0.0
    first = np.lexsort((xyz[:, :, 2], xyz[:, :, 1], xyz[:, :, 0]), axis=1)[:, 0]
    order = (first[:, None]+np.arange(3)[None, :]) % 3
    return np.take_along_axis(xyz, order[:, :, None], axis=1)


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def face_keys(points, faces):
    """All source rows, exact 72-byte cyclic coordinate keys in bounded chunks."""
    keys = np.empty(len(faces), dtype='V72')
    for start in range(0, len(faces), CHUNK):
        stop = min(start+CHUNK, len(faces))
        rows = coordinate_faces(points, faces[start:stop])
        keys[start:stop] = np.ascontiguousarray(rows, dtype='<f8').reshape(-1, 9).view('V72').ravel()
    return keys


def masks_from_keys(original, candidate):
    """Unique-or-fail complete intersection; each surface keeps its own source mask."""
    if (original.ndim != 1 or candidate.ndim != 1 or
            original.dtype != np.dtype('V72') or candidate.dtype != np.dtype('V72')):
        raise ValueError('Complete one-dimensional 72-byte key arrays required')
    if len(np.unique(original)) != len(original) or len(np.unique(candidate)) != len(candidate):
        raise ValueError('Duplicate oriented coordinate triangles refuse cancellation')
    common, original_ids, candidate_ids = np.intersect1d(
        original, candidate, assume_unique=True, return_indices=True)
    a = np.zeros(len(original), dtype=np.bool_)
    b = np.zeros(len(candidate), dtype=np.bool_)
    a[original_ids] = True; b[candidate_ids] = True
    if (not np.array_equal(original[original_ids], common) or
            not np.array_equal(candidate[candidate_ids], common) or
            int(a.sum()) != len(common) or int(b.sum()) != len(common)):
        raise ValueError('Complete shared-key association failed')
    return a, b, common


def validate(contract_path, expected):
    if digest(contract_path) != expected:
        raise ValueError('Exact frozen execution contract required')
    contract = json.loads(contract_path.read_text())
    if (contract.get('schema') != '962-exact-coordinate-unequal-partition-child/v1' or
            contract.get('root_authorized') is not True or
            contract.get('root_and_peer_review_complete') is not True):
        raise ValueError('HELD: separate reviewed root authorization required before inputs or NumPy')
    held_path = PREP/'held-contract.json'
    held = json.loads(held_path.read_text())
    if contract.get('preparation') != dict(path=str(held_path.relative_to(ROOT)), sha256=digest(held_path)):
        raise ValueError('Exact held preparation binding required')
    pins = dict(held['input_sha256']); pins[str(held_path.relative_to(ROOT))] = digest(held_path)
    for name, value in contract.get('execution_reviews', {}).items():
        if name in pins:
            raise ValueError('Execution review cannot replace a prepared pin')
        pins[name] = value
    if (contract.get('input_sha256') != pins or
            contract.get('original') != str(ORIGINAL.relative_to(ROOT)) or
            contract.get('candidate') != str(CANDIDATE.relative_to(ROOT)) or
            contract.get('output') != str(OUTPUT.relative_to(ROOT)) or
            contract.get('expected_counts') != EXPECTED_COUNTS or
            contract.get('chunk_faces') != CHUNK or
            contract.get('complete_opposite_targets_required') is not True or
            contract.get('automatic_retry') is not False or
            contract.get('envelope_limit_mm') != 0.0625 or
            contract.get('coordinate_tolerance_mm') != 0 or
            not contract.get('qualification') or any(v is not False for v in contract['qualification'].values()) or
            contract.get('qualification') != held['qualification']):
        raise ValueError('Only the fixed conservative partition is prepared')
    for name in pins:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not (ROOT/path).resolve().is_relative_to(ROOT):
            raise ValueError('Repository-relative source pins required')
    if (any(not (ROOT/name).is_file() or (ROOT/name).is_symlink() or digest(ROOT/name) != value
            for name, value in pins.items()) or
            digest(HERE) != pins.get(str(HERE.relative_to(ROOT))) or
            digest(Path(sys.executable).resolve()) != contract.get('python_executable_sha256')):
        raise ValueError('Prepared source/input/interpreter drift')
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError('Fresh fixed output required; prior partial output preserved')
    return contract, pins


def prepare(contract_path, expected):
    contract, pins = validate(contract_path, expected)
    global np
    import numpy as np
    if np.__version__ != contract.get('numpy_version'):
        raise ValueError('Reviewed NumPy runtime required')
    p, f = read(ORIGINAL); q, g = read(CANDIDATE)
    observed = dict(original_vertices=len(p), original_faces=len(f),
                    candidate_vertices=len(q), candidate_faces=len(g))
    if observed != EXPECTED_COUNTS:
        raise ValueError('Complete frozen source counts changed')
    a, b = face_keys(p, f), face_keys(q, g)
    original_mask, candidate_mask, common = masks_from_keys(a, b)
    OUTPUT.mkdir(exist_ok=False)
    partitions = {}
    for role, mask in [('original', original_mask), ('candidate', candidate_mask)]:
        path = OUTPUT/(role+'-partition.npz')
        changed = np.flatnonzero(~mask).astype('<u8')
        with path.open('xb') as stream:
            np.savez(stream, shared_face_mask=mask, changed_face_indices=changed)
        with np.load(path, allow_pickle=False) as saved:
            if (set(saved.files) != {'shared_face_mask', 'changed_face_indices'} or
                    saved['shared_face_mask'].dtype != np.dtype('bool') or
                    saved['changed_face_indices'].dtype != np.dtype('<u8') or
                    not np.array_equal(saved['shared_face_mask'], mask) or
                    not np.array_equal(saved['changed_face_indices'], changed)):
                raise ValueError('Saved complete mask/index readback failed')
        partitions[role] = dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
            source_faces=len(mask), shared_faces=int(mask.sum()), changed_faces=len(changed),
            shared_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
            changed_indices_sha256=hashlib.sha256(changed.tobytes()).hexdigest(),
            all_source_rows_partitioned_once=True)
    queries = {}
    for name, source, target, role in [
            ('original-changed-to-complete-assembled', ORIGINAL, CANDIDATE, 'original'),
            ('assembled-changed-to-complete-original', CANDIDATE, ORIGINAL, 'candidate')]:
        config = dict(id=name, source=str(source.relative_to(ROOT)),
            target=str(target.relative_to(ROOT)), partition=partitions[role]['path'])
        path = OUTPUT/(name+'.json'); save(path, config)
        queries[str(path.relative_to(ROOT))] = digest(path)
    unchanged = (digest(contract_path) == expected and all(digest(ROOT/name) == value
                 for name, value in pins.items()))
    if not unchanged:
        raise ValueError('Input drift; partial outputs preserved without completion proof')
    report = dict(schema='962-exact-coordinate-unequal-partition-proof/v1',
        status='complete_exact_source_masks_only_no_distance_query',
        contract_sha256=expected, source_sha256=digest(HERE), input_sha256=pins,
        complete_source_counts=observed, partitions=partitions,
        shared_faces=len(common), sorted_shared_oriented_coordinate_keys_sha256=hashlib.sha256(common.tobytes()).hexdigest(),
        each_shared_key_occurs_once_in_each_complete_surface=True,
        complete_opposite_targets_required=True, only_query_source_faces_restricted=True,
        orientation_preserved=True, signed_zero_geometric_equivalence=True,
        coordinate_tolerance_mm=0, chunk_faces=CHUNK,
        original_key_array_sha256=hashlib.sha256(a.tobytes()).hexdigest(),
        candidate_key_array_sha256=hashlib.sha256(b.tobytes()).hexdigest(),
        query_config_sha256=queries, all_bound_inputs_unchanged=unchanged,
        proof='A=S union A_changed and B=S union B_changed. Every cancelled source triangle has the identical cyclic oriented coordinate triangle in the COMPLETE opposite target. Each directed supremum equals max(0, its own changed-source-to-complete-opposite-target supremum). Duplicate keys refuse; no origins or UINT64_MAX indices are used.',
        distance_queries_executed=0, geometry_exports=0,
        qualification=contract['qualification'])
    save(OUTPUT/'reduction-proof.json', report)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    args = parser.parse_args()
    raise SystemExit(prepare(args.contract.resolve(), args.contract_sha256))
