"""Closed encoded-point coverage for cuts with already verified owner bindings."""
from fractions import Fraction as Q
import hashlib
import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTHORITIES = {
    'reference/rounding_cell_diagnostic.py':
        '807a054749ae1f48dc0d375d67368b884195367c3473592c6f1c29b26a19e385',
    'reference/audit_support_scanpaths.py':
        '4ace9f24b61fa8f2d514f18d2e3eb6e9794983d6dee41fad4a8f44dc1f4c53ef',
}
for name, expected in AUTHORITIES.items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
        raise ValueError('Frozen encoded-point authority differs: '+name)
diagnostic, audit = [ROOT/name for name in AUTHORITIES]
spec = importlib.util.spec_from_file_location('_closed_point_807a', diagnostic)
_proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_proof)
_exact = dict(Q=Q)
_proof.extract(audit, ['canonical', 'encode', 'orient', 'contains_point'], _exact)
cell_proof = _proof.cell_proof


def encode_from_owned_cuts(owned_cuts):
    """Keep every Q cut; omit an encoded point only with an owned vector witness.

    Each record has npz_sha256/source_index/region/owner/layer/face/cut. The caller
    verifies NPZ bytes, partition, attributes and schedule before supplying it.
    region is the local surface-list position, not necessarily source_index.
    The encoded provenance contains ONLY faces whose own encoding is nonzero.
    """
    sections, encodings, encoded_sections, witnesses, points = {}, {}, {}, {}, []
    for row in owned_cuts:
        cut = tuple(tuple(point) for point in row['cut'])
        if (len(cut) != 2 or any(len(point) != 2 for point in cut) or
                any(type(c) is not Q for point in cut for c in point) or cut[0] == cut[1]):
            raise ValueError('A cut must contain two distinct exact Fraction XY points')
        cut = _exact['canonical'](cut)
        scope = tuple(row[key] for key in ('npz_sha256', 'source_index', 'region', 'owner', 'layer'))
        provenance = (row['region'], row['face'])
        sections.setdefault(cut, []).append(provenance)
        encoded = _exact['encode'](cut)
        if not all(math.isfinite(c) for point in encoded for c in point):
            raise ValueError('Nonfinite encoded coordinate')
        encoded_q = tuple(tuple(Q(c) for c in point) for point in encoded)
        if encoded[0] == encoded[1]:
            points.append((scope, provenance, cut, cell_proof(cut)))
            continue
        encodings.setdefault(encoded, set()).add(cut)
        encoded_sections.setdefault(encoded_q, []).append(provenance)
        witnesses.setdefault(scope, []).append((row['face'], encoded_q))
    covered_points = []
    for scope, provenance, cut, proof in points:
        point = tuple(Q(c) for c in proof['point'])
        covering = [face for face, vector in witnesses.get(scope, ())
                    if _exact['contains_point'](vector, point)]
        if not covering:
            raise ValueError('Encoded point lacks a nonzero vector in the same NPZ/source/region/owner/layer')
        covered_points.append(dict(scope=scope, provenance=provenance, rational_cut=cut,
                                   rounding_cell=proof, covering_face_ids=covering))
    return dict(sections=sections, encodings=encodings, encoded_sections=encoded_sections,
                covered_points=covered_points)
