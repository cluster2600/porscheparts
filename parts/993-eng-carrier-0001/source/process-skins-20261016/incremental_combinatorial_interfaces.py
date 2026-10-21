"""Incremental replay of the pinned constructor's exact assembly operation.

Every line retains ALL endpoints and signed events from accepted triangles,
including endpoints of edges that cancel. A trial only changes its own lines.
The materialized boundary therefore equals a fresh _atomic_chain of the complete
triangle list. Rejected trials never commit endpoints, events or area.
"""
from fractions import Fraction as Q
import hashlib
import importlib.util
import math
from pathlib import Path
from threading import RLock

INDEX_SHA256 = '0302ac46796b2dab08484873370ab1f4d5eff6319c752f966641825a34aba2bd'
_PATH = Path(__file__).with_name('indexed_combinatorial_interfaces.py')
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != INDEX_SHA256:
    raise ValueError('The indexed constructor source changed')
_SPEC = importlib.util.spec_from_file_location('_private_incremental_indexed_constructor', _PATH)
_INDEX = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_INDEX)
_BASE = _INDEX._BASE
_ORIGINAL_ASSEMBLE = _BASE._assemble
_LOCK = RLock()


def exact_area(points):
    """Integer shoelace with common positive denominators, no rounded sum."""
    if not points:
        return Q(0)
    sx = math.lcm(*(p[0].denominator for p in points))
    sy = math.lcm(*(p[1].denominator for p in points))
    integers = [(p[0].numerator*(sx//p[0].denominator),
                 p[1].numerator*(sy//p[1].denominator)) for p in points]
    numerator = sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(integers,integers[1:]+integers[:1]))
    return Q(numerator, 2*sx*sy)


class _Line:
    def __init__(self, axis):
        self.axis, self.points, self.events, self.atoms = axis, {}, {}, {}

    def copy(self):
        other = _Line(self.axis)
        other.points, other.events = self.points.copy(), self.events.copy()
        return other

    def add(self, a, b):
        self.points[a[self.axis]], self.points[b[self.axis]] = a, b
        low, high = sorted((a[self.axis],b[self.axis]))
        sign = 1 if b[self.axis]>a[self.axis] else -1
        self.events[low] = self.events.get(low,0)+sign
        self.events[high] = self.events.get(high,0)-sign

    def materialize(self):
        ordered, multiplicity, result = sorted(self.points), 0, {}
        for low,high in zip(ordered[:-1],ordered[1:]):
            multiplicity += self.events.get(low,0)
            if multiplicity:
                a,b = self.points[low],self.points[high]
                count = multiplicity
                if a>b:
                    a,b,count = b,a,-multiplicity
                result[(a,b)] = count
        self.atoms = result


def _edges(triangles):
    for triangle in triangles:
        for a,b in zip(triangle,triangle[1:]+triangle[:1]):
            if a!=b:
                yield _INDEX._line(a,b),a,b


class _Assembly:
    def __init__(self, initial):
        self.initial, self.prefix, self.lines = initial, None, {}
        self.statistics = dict(calls=0, full_recompute_fallbacks=0, changed_line_updates=0,
                               accepted_trials=0, rejected_trials=0)

    def initialize(self, triangles):
        source = triangles[:len(self.initial)]
        if source!=self.initial:
            return False
        self.result,self.area = _ORIGINAL_ASSEMBLE(source)
        for key,a,b in _edges(source):
            if key not in self.lines:
                self.lines[key] = _Line(0 if a[0]!=b[0] else 1)
            self.lines[key].add(a,b)
        for line in self.lines.values():
            line.materialize()
        self.prefix = list(source)
        return True

    def __call__(self, triangles):
        self.statistics['calls'] += 1
        if self.prefix is None and not self.initialize(triangles):
            self.statistics['full_recompute_fallbacks'] += 1
            return _ORIGINAL_ASSEMBLE(triangles)
        if (len(triangles)<len(self.prefix) or len(triangles)>len(self.prefix)+2 or
                any(a is not b for a,b in zip(triangles,self.prefix))):
            self.statistics['full_recompute_fallbacks'] += 1
            return _ORIGINAL_ASSEMBLE(triangles)
        if len(triangles)==len(self.prefix):
            return self.result,self.area
        additions = triangles[len(self.prefix):]
        if any(exact_area(triangle)<=0 for triangle in additions):
            self.statistics['full_recompute_fallbacks'] += 1
            return _ORIGINAL_ASSEMBLE(triangles)
        updates = {}
        for key,a,b in _edges(additions):
            if key not in updates:
                updates[key] = self.lines[key].copy() if key in self.lines else _Line(0 if a[0]!=b[0] else 1)
            updates[key].add(a,b)
        for line in updates.values():
            line.materialize()
        candidate_lines = self.lines | updates
        # Dict union preserves the first appearance of every line, exactly as
        # the pinned constructor's full triangle scan does.
        boundary = {edge:count for line in candidate_lines.values() for edge,count in line.atoms.items()}
        self.statistics['changed_line_updates'] += len(updates)
        try:
            generated = _BASE._cycles(boundary)
            areas = [exact_area(ring) for ring in generated]
            outers = [ring for ring,area in zip(generated,areas) if area>0]
            holes = [ring for ring,area in zip(generated,areas) if area<0]
            if len(outers)!=1 or len(outers)+len(holes)!=len(generated):
                raise ValueError('The boundary does not describe one positive sheet')
            generated = [outers[0],*holes]
            result = _BASE.Polygon([[float(c) for c in p] for p in generated[0]],
                [[[float(c) for c in p] for p in ring] for ring in generated[1:]])
            # Every cycle edge is one already-atomic boundary edge. All its
            # endpoints came from the complete line event store, so another
            # atomization cannot introduce an interior endpoint.
            chain_equal = boundary==_BASE._BAND._chain(generated)
            area = self.area+sum(exact_area(triangle) for triangle in additions)
            ring_area = sum(exact_area(ring) for ring in generated)
            below = any(p[1]<0 for ring in generated for p in ring)
            if not result.is_valid or result.is_empty or not chain_equal or area!=ring_area or below:
                error = ValueError('The assembled positive triangle chain is not one valid sheet')
                error.receipt = _BASE._BAND._COVERAGE._encoded(dict(valid=result.is_valid,
                    explain_validity=_BASE.shapely.is_valid_reason(result),chain_equal=chain_equal,
                    area_equal=area==ring_area,below_plate=below,result_wkb_hex=result.wkb_hex))
                raise error
        except ValueError:
            self.statistics['rejected_trials'] += 1
            raise
        self.prefix = list(triangles)
        self.lines,self.result,self.area = candidate_lines,result,area
        self.statistics['accepted_trials'] += 1
        return result,area


def construct_with_statistics(domain,interfaces,penetration):
    initial,_ = _BASE._BAND._triangulation(domain)
    state = _Assembly(initial)
    with _LOCK:
        if _BASE._assemble is not _ORIGINAL_ASSEMBLE:
            raise ValueError('The incremental constructor does not permit reentrant calls')
        _BASE._assemble = state
        try:
            result,receipt = _INDEX.construct(domain,interfaces,penetration)
        finally:
            _BASE._assemble = _ORIGINAL_ASSEMBLE
    return result,receipt,state.statistics


def construct(domain,interfaces,penetration):
    result,receipt,_ = construct_with_statistics(domain,interfaces,penetration)
    return result,receipt
