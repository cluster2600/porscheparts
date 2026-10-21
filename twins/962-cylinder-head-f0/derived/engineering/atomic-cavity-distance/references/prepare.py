"""Prepare unequal-count source partitions; never launch CUB or change a mesh."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'work/962-engineering'
OUT = Path(__file__).parent
SOURCE = ROOT / 'twins/962-cylinder-head-f0/source'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rel = lambda p: p.relative_to(ROOT).as_posix()


def canonical_keys(faces):
    first = np.argmin(faces, axis=1)
    order = (first[:, None] + np.arange(3)[None, :]) % 3
    return np.ascontiguousarray(np.take_along_axis(faces, order, axis=1), dtype='<u8').view('V24').reshape(-1)


def masks(original_faces, candidate_original_ids, patch_ids):
    original_shared = np.ones(len(original_faces), dtype=bool)
    original_shared[patch_ids] = False
    exterior = canonical_keys(original_faces[original_shared])
    candidate_keys = canonical_keys(candidate_original_ids)
    candidate_shared = np.isin(candidate_keys, exterior)
    assert len(np.unique(exterior)) == len(exterior)
    assert np.array_equal(np.sort(candidate_keys[candidate_shared]), np.sort(exterior))
    return original_shared, candidate_shared


def put(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def run():
    # Different source counts and cyclic corner starts must work; reversal must fail.
    a = np.array([[0, 1, 2], [3, 4, 5], [5, 4, 6]], dtype='<u8')
    b = np.array([[1, 2, 0], [3, 4, 6]], dtype='<u8')
    ma, mb = masks(a, b, np.array([1, 2]))
    assert ma.tolist() == [True, False, False] and mb.tolist() == [True, False]
    try:
        masks(a, b[:, ::-1], np.array([1, 2]))
    except AssertionError:
        pass
    else:
        raise AssertionError('Reversed shared exterior must be refused')
    original = WORK / 'analysis-envelope-025-003/exact-input.bin'
    candidate = WORK / 'atomic-cavity-head-001/head-atomic002/candidate.bin'
    origins_path = candidate.with_name('vertex-coordinate-origins.u64')
    patch_path = WORK / 'finest-endpoint-003-head-001/head-endpoint003/patch-reference-face-ids.u64'
    fixed = {
        original: '894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95',
        candidate: '1f9dbd4cda61c7b58084479ebb165fb01280fa831752dc0da18517e548131b1a',
        origins_path: '22d9303503c98a7c4b0f08bfe20df3dddce51b7a86a96f4fcbc503f0cb163e47',
        patch_path: 'c93dcc98059fed493f2d50d64cbdd4a6ca4b3d79199af390442cea4506175763',
        SOURCE / 'audit_quality_head.py': 'a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991',
        SOURCE / 'run_quality_distance_002.py': '6aeb8be558054b6cb4e8d1b7904adfe17d57b0c11d17a134cbe574a8cafa085c',
        WORK / 'atomic-cavity-head-root-result-001/review.json': '4c6699f8f63b18e3e819f10bcaf09693f43381bc0e01f45f85cb4bf43116c081',
        WORK / 'atomic-cavity-head-peer-readback-001/review.json': '61e0802328ddbf8e38658b980fbc43c617cab00248304717dde4492f7b2ff047',
    }
    assert all(sha(p) == value for p, value in fixed.items())
    sys.path.insert(0, str(SOURCE))
    from audit_quality_head import read
    p, f = read(original)
    q, g = read(candidate)
    origins = np.fromfile(origins_path, dtype='<u8')
    patch = np.fromfile(patch_path, dtype='<u8')
    assert (len(p), len(f), len(q), len(g)) == (902145, 1804706, 901727, 1803870)
    assert len(origins) == len(q) and len(np.unique(origins)) == len(q)
    assert origins.max() < len(p) and q.tobytes() == p[origins].tobytes()
    assert len(patch) == 4704 and np.array_equal(patch, np.unique(patch)) and patch.max() < len(f)
    original_mask, candidate_mask = masks(f, origins[g], patch)
    assert int(original_mask.sum()) == int(candidate_mask.sum()) == 1800002
    assert len(f) - original_mask.sum() == 4704 and len(g) - candidate_mask.sum() == 3868
    partitions = []
    for name, mask in [('original', original_mask), ('candidate', candidate_mask)]:
        path = OUT / (name + '-partition.npz')
        with path.open('xb') as stream:
            np.savez(stream, shared_face_mask=mask, changed_face_indices=np.flatnonzero(~mask).astype('<u8'))
        partitions.append(path)
    assert all(sha(p) == value for p, value in fixed.items())
    put('reduction-proof.json', dict(
        schema='962-atomic-unequal-count-shared-exterior-reduction/v1',
        preparation_sha256=sha(Path(__file__)),
        input_sha256={rel(p): value for p, value in fixed.items()},
        original_faces=len(f), candidate_faces=len(g), shared_oriented_faces=1800002,
        original_query_faces=4704, candidate_query_faces=3868,
        partitions={rel(p): sha(p) for p in partitions},
        complete_ordered_candidate_points_original_byte_exact=True,
        complete_oriented_exterior_multisets_equal=True,
        proof='A=S union A_patch; B=S union B_patch. Every face in S is present exactly once in both complete targets with the same original IDs, coordinate bytes and winding. Therefore h(A,B)=max(0,h(A_patch,B)); reverse analogously. Patch faces may still be shared; leaving them in the source is conservative.',
        source_partitions_have_distinct_lengths=True, complete_opposite_targets_required=True,
        coordinate_tolerance_or_rounding_used=False, native_CUB_calls=0,
        unequal_count_and_reversed_winding_selfchecks_passed=True,
        distance_gate_passed=False, head_or_solver_admitted=False, manufacturing_authorized=False))
    print(json.dumps(dict(status='source_partitions_prepared_no_native_query', proof_sha256=sha(OUT/'reduction-proof.json'))))


if __name__ == '__main__':
    run()
