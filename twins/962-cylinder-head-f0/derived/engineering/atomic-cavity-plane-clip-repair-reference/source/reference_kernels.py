"""Exact shortest-edge observations and necessary-only keeper eligibility."""
from fractions import Fraction
import math


def shortest_proposals(points, faces):
    rational = {}
    for vertex, point in points.items():
        if type(vertex) is not int or vertex < 0 or len(point) != 3:
            raise ValueError('Nonnegative integer point IDs and triples required')
        if any(type(x) is not float or not math.isfinite(x) for x in point):
            raise ValueError('Finite binary64 coordinates required')
        rational[vertex] = tuple(Fraction.from_float(x) for x in point)
    rows = []; all_minima = set(); lex_first = set()
    for fid, triangle in sorted(faces.items()):
        if (type(fid) is not int or fid < 0 or len(triangle) != 3
                or any(type(v) is not int or v not in rational for v in triangle)
                or len(set(triangle)) != 3):
            raise ValueError('Distinct bound triangle IDs required')
        costs = []
        for i in range(3):
            a,b = sorted((triangle[i], triangle[(i+1)%3]))
            squared = sum((x-y)**2 for x,y in zip(rational[a], rational[b]))
            costs.append((squared, (a,b)))
        costs.sort(); minimum = costs[0][0]
        ties = sorted(edge for value,edge in costs if value == minimum)
        all_minima.update(ties); lex_first.add(ties[0])
        rows.append(dict(face_id=fid, exact_squared_lengths_in_ascending_order=[
            dict(edge=list(edge), numerator=str(value.numerator), denominator=str(value.denominator))
            for value,edge in costs], minimum_edges=[list(edge) for edge in ties],
            exploratory_lex_first_edge=list(ties[0])))
    return rows, sorted(all_minima), sorted(lex_first)


def cap_winding(points, faces):
    result = {'negative_z_face_ids':[], 'positive_z_face_ids':[], 'zero_face_ids':[]}
    for fid,t in sorted(faces.items()):
        if any(points[v][2] != 0.0 for v in t):
            raise ValueError('Cap winding requires exact z0')
        a,b,c = [tuple(Fraction.from_float(x) for x in points[v][:2]) for v in t]
        signed = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        key = 'negative_z_face_ids' if signed < 0 else 'positive_z_face_ids' if signed > 0 else 'zero_face_ids'
        result[key].append(fid)
    return result


def component_eligibility(edges, fixed, cap_vertices, z_by_vertex):
    parent = {}
    def find(v):
        parent.setdefault(v,v)
        while parent[v] != v:
            parent[v] = parent[parent[v]]; v = parent[v]
        return v
    for a,b in edges:
        if type(a) is not int or type(b) is not int or not 0 <= a < b or a not in z_by_vertex or b not in z_by_vertex:
            raise ValueError('Ordered distinct bound edge IDs required')
        x,y = find(a),find(b)
        if x != y:
            parent[max(x,y)] = min(x,y)
    groups = {}
    for v in sorted(parent):
        groups.setdefault(find(v),[]).append(v)
    result = []
    for first,members in sorted(groups.items()):
        if any(type(z_by_vertex[v]) is not float or not math.isfinite(z_by_vertex[v]) for v in members):
            raise ValueError('Finite binary64 z required')
        conflicts = sorted(set(members) & fixed); cap = sorted(set(members) & cap_vertices)
        eligible = [] if conflicts else [v for v in members if not cap or z_by_vertex[v] == 0.0]
        result.append(dict(component_minimum=first, vertex_ids=members, fixed_conflict_ids=conflicts,
            cap_complex_member_ids=cap, keeper_candidates_satisfying_only_fixed_and_plane=eligible,
            selected_keeper=None, geometric_or_topological_keeper_admissibility_checked=False))
    return result
