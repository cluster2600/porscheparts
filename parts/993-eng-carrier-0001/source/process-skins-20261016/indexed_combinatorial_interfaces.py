"""Exact source-line index for the unchanged combinatorial construction.

The private constructor is pinned. Its only substituted operation returns the
same attestation intervals, in the same original path/segment order. A line key
is a normalized rational equation; no spatial tolerance or rounded bin is used.
"""
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
from threading import RLock

CONSTRUCTION_SHA256 = '94393c465fb15c1c3129ad8e482ea19cd597d3e716714e069b4eaee38b80e2fa'
_PATH = Path(__file__).with_name('combinatorial_interfaces.py')
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != CONSTRUCTION_SHA256:
    raise ValueError('The indexed constructor source changed')
_SPEC = importlib.util.spec_from_file_location('_private_indexed_combinatorial_constructor', _PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)
_LOCK = RLock()
_ORIGINAL_COVERAGE = _BASE._coverage


def _line(a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    if not dx and not dy:
        raise ValueError('Zero attested source segment')
    coefficients = (dy, -dx, dx*a[1]-dy*a[0])
    scale = next(c for c in coefficients if c)
    return tuple(c/scale for c in coefficients)


class InterfaceIndex:
    def __init__(self, paths):
        self.lines = {}
        for path_index, path in enumerate(paths):
            points = [_BASE._EXACT.point(p) for p in path]
            for segment_index, (c, d) in enumerate(zip(points[:-1], points[1:])):
                self.lines.setdefault(_line(c, d), []).append((path_index, segment_index, c, d))

    def coverage(self, a, b):
        delta = _BASE._EXACT.difference(b, a)
        axis = 0 if delta[0] else 1
        intervals = []
        for path_index, segment_index, c, d in self.lines.get(_line(a, b), []):
            first, last = sorted(((p[axis]-a[axis])/delta[axis] for p in (c, d)))
            first, last = max(Q(0), first), min(Q(1), last)
            if first < last:
                intervals.append((first, last, path_index, segment_index))
        end = Q(0)
        for first, last, _, _ in sorted(intervals):
            if first > end:
                break
            end = max(end, last)
        return end == 1, intervals


def construct(domain, interfaces, penetration):
    if set(interfaces) != {'upper', 'lower'}:
        raise ValueError('Attested upper and lower interfaces are required')
    indices = {name: InterfaceIndex(paths) for name, paths in interfaces.items()}
    def indexed(a, b, paths):
        for name in ['upper', 'lower']:
            if paths is interfaces[name]:
                return indices[name].coverage(a, b)
        raise ValueError('The constructor requested an unbound source interface list')
    with _LOCK:
        if _BASE._coverage is not _ORIGINAL_COVERAGE:
            raise ValueError('The indexed constructor does not permit reentrant calls')
        _BASE._coverage = indexed
        try:
            return _BASE.construct(domain, interfaces, penetration)
        finally:
            _BASE._coverage = _ORIGINAL_COVERAGE
