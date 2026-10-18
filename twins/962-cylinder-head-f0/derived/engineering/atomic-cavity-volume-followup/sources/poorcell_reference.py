"""Small stdlib oracle for proposed participation counts; no geometry/runtime imports."""
import math


def classify(values, tetra_tags, node_rows, boundary_count):
    if type(boundary_count) is not int or boundary_count <= 0:
        raise ValueError("Positive original boundary count required")
    if not len(values) == len(tetra_tags) == len(node_rows):
        raise ValueError("Complete aligned cell rows required")
    if (any(type(tag) is not int or tag <= 0 for tag in tetra_tags)
            or len(set(tetra_tags)) != len(tetra_tags)):
        raise ValueError("Distinct positive tetrahedron tags required")
    counts = {str(k): 0 for k in range(5)}
    representatives = {}
    for index, (value, tag, nodes) in enumerate(zip(values, tetra_tags, node_rows)):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Finite SICN values required")
        if len(nodes) != 4 or any(type(n) is not int or n <= 0 for n in nodes):
            raise ValueError("Four positive node tags required")
        if not 0 < value < .1:
            continue
        key = str(sum(1 <= n <= boundary_count for n in nodes))
        counts[key] += 1
        if (key not in representatives
                or (value, tag) < (values[representatives[key]], tetra_tags[representatives[key]])):
            representatives[key] = index
    return counts, representatives
