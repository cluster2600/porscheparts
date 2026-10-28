"""Use lossless point IDs for the pinned incremental boundary graph.

Coordinates remain Fractions. The IEEE pair used as an identity/order key is
accepted only after Q(float(c)) == c for both coordinates. Hence these keys have
exactly the same equality and lexicographic order as the original coordinates.
No coordinate arithmetic is performed on those keys.
"""
import hashlib
import importlib.util
import math
from pathlib import Path

ASSEMBLY_SHA256 = '69b32aee03445071f9d6d1705d1e153baf16d82f85a9ea7f25cb6532dfb99ad8'
_PATH = Path(__file__).with_name('incremental_combinatorial_interfaces.py')
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != ASSEMBLY_SHA256:
    raise ValueError('The incremental assembly source changed')
_SPEC = importlib.util.spec_from_file_location('_private_point_id_incremental_constructor',_PATH)
_OLD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_OLD)
_BASE = _OLD._BASE
_OriginalAssembly = _OLD._Assembly


class _Points:
    def __init__(self):
        self.coordinates,self.keys,self.index = [],[],{}

    def identity(self,point):
        if len(point)!=2 or any(not isinstance(c,_OLD.Q) for c in point):
            raise ValueError('A point ID requires exactly two Fraction coordinates')
        try:key=tuple(float(c) for c in point)
        except OverflowError:raise ValueError('A point ID requires finite IEEE coordinates') from None
        if not all(math.isfinite(c) for c in key) or any(_OLD.Q(c)!=q for c,q in zip(key,point)):
            raise ValueError('A point ID requires exactly representable IEEE coordinates')
        if key not in self.index:
            self.index[key]=len(self.coordinates)
            self.coordinates.append(point);self.keys.append(key)
        identity=self.index[key]
        if self.coordinates[identity]!=point:
            raise ValueError('Two unequal rational points received the same identity')
        return identity


class _Line:
    def __init__(self,axis,points):
        self.axis,self.registry,self.points,self.events,self.atoms=axis,points,{},{},{}

    def copy(self):
        result=_Line(self.axis,self.registry)
        result.points,result.events=self.points.copy(),self.events.copy()
        return result

    def add(self,a,b):
        ia,ib=self.registry.identity(a),self.registry.identity(b)
        aa,bb=self.registry.keys[ia][self.axis],self.registry.keys[ib][self.axis]
        self.points[aa],self.points[bb]=ia,ib
        low,high=sorted((aa,bb));sign=1 if bb>aa else -1
        self.events[low]=self.events.get(low,0)+sign
        self.events[high]=self.events.get(high,0)-sign

    def materialize(self):
        ordered,multiplicity,result=sorted(self.points),0,{}
        for low,high in zip(ordered[:-1],ordered[1:]):
            multiplicity+=self.events.get(low,0)
            if multiplicity:
                a,b=self.points[low],self.points[high];count=multiplicity
                if self.registry.keys[a]>self.registry.keys[b]:
                    a,b,count=b,a,-multiplicity
                result[(a,b)]=count
        self.atoms=result


def _cycles(boundary,points):
    outgoing,incoming={},{}
    for (a,b),count in boundary.items():
        if abs(count)!=1:raise ValueError('The boundary has repeated positive multiplicity')
        if count<0:a,b=b,a
        if a in outgoing or b in incoming:raise ValueError('The boundary has a branch or a point contact')
        outgoing[a],incoming[b]=b,a
    if set(outgoing)!=set(incoming):raise ValueError('The boundary has an open endpoint')
    unused=set(outgoing);result=[]
    while unused:
        first=min(unused,key=lambda i:points.keys[i]);ring,current=[],first
        while current in unused:
            ring.append(current);unused.remove(current);current=outgoing[current]
        if current!=first:raise ValueError('Boundary cycles unexpectedly meet')
        result.append(ring)
    return result


def _chain(rings,points):
    result={}
    for ring in rings:
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if a==b:continue
            edge=(a,b) if points.keys[a]<points.keys[b] else (b,a)
            result[edge]=result.get(edge,0)+(1 if edge==(a,b) else -1)
    return {edge:count for edge,count in result.items() if count}


class _Assembly(_OriginalAssembly):
    def __init__(self,initial):
        super().__init__(initial);self.registry=_Points()

    def initialize(self,triangles):
        source=triangles[:len(self.initial)]
        if source!=self.initial:return False
        self.result,self.area=_OLD._ORIGINAL_ASSEMBLE(source)
        for key,a,b in _OLD._edges(source):
            if key not in self.lines:self.lines[key]=_Line(0 if a[0]!=b[0] else 1,self.registry)
            self.lines[key].add(a,b)
        for line in self.lines.values():line.materialize()
        self.prefix=list(source);return True

    def __call__(self,triangles):
        self.statistics['calls']+=1
        if self.prefix is None and not self.initialize(triangles):
            self.statistics['full_recompute_fallbacks']+=1
            return _OLD._ORIGINAL_ASSEMBLE(triangles)
        if (len(triangles)<len(self.prefix) or len(triangles)>len(self.prefix)+2 or
                any(a is not b for a,b in zip(triangles,self.prefix))):
            self.statistics['full_recompute_fallbacks']+=1
            return _OLD._ORIGINAL_ASSEMBLE(triangles)
        if len(triangles)==len(self.prefix):return self.result,self.area
        additions=triangles[len(self.prefix):]
        if any(_OLD.exact_area(t)<=0 for t in additions):
            self.statistics['full_recompute_fallbacks']+=1
            return _OLD._ORIGINAL_ASSEMBLE(triangles)
        updates={}
        for key,a,b in _OLD._edges(additions):
            if key not in updates:updates[key]=self.lines[key].copy() if key in self.lines else _Line(0 if a[0]!=b[0] else 1,self.registry)
            updates[key].add(a,b)
        for line in updates.values():line.materialize()
        candidate_lines=self.lines|updates
        boundary={edge:count for line in candidate_lines.values() for edge,count in line.atoms.items()}
        self.statistics['changed_line_updates']+=len(updates)
        try:
            cycles=_cycles(boundary,self.registry)
            generated=[[self.registry.coordinates[i] for i in ring] for ring in cycles]
            areas=[_OLD.exact_area(ring) for ring in generated]
            outer_ids=[i for i,area in enumerate(areas) if area>0]
            hole_ids=[i for i,area in enumerate(areas) if area<0]
            if len(outer_ids)!=1 or len(outer_ids)+len(hole_ids)!=len(cycles):raise ValueError('The boundary does not describe one positive sheet')
            order=outer_ids+hole_ids;cycles=[cycles[i] for i in order];generated=[generated[i] for i in order]
            result=_BASE.Polygon([self.registry.keys[i] for i in cycles[0]],
                [[self.registry.keys[i] for i in ring] for ring in cycles[1:]])
            chain_equal=boundary==_chain(cycles,self.registry)
            area=self.area+sum(_OLD.exact_area(t) for t in additions)
            ring_area=sum(_OLD.exact_area(ring) for ring in generated)
            below=any(p[1]<0 for ring in generated for p in ring)
            if not result.is_valid or result.is_empty or not chain_equal or area!=ring_area or below:
                error=ValueError('The assembled positive triangle chain is not one valid sheet')
                error.receipt=_BASE._BAND._COVERAGE._encoded(dict(valid=result.is_valid,
                    explain_validity=_BASE.shapely.is_valid_reason(result),chain_equal=chain_equal,
                    area_equal=area==ring_area,below_plate=below,result_wkb_hex=result.wkb_hex))
                raise error
        except ValueError:
            self.statistics['rejected_trials']+=1;raise
        self.prefix=list(triangles);self.lines,self.result,self.area=candidate_lines,result,area
        self.statistics['accepted_trials']+=1
        return result,area


_OLD._Assembly=_Assembly
construct_with_statistics=_OLD.construct_with_statistics
construct=_OLD.construct
