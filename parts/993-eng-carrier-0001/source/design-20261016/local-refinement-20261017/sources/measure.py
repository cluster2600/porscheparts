"""Measure actual T10 edge lengths in the two frozen peak boxes; no field selection."""
import math


def require(condition, message):
    if not condition:
        raise ValueError(message)


def region_edges(points, elements, region):
    """Whole edges of centroid-selected tetrahedra; lengths are never clipped."""
    lo, hi = region['bounds_mm']; target = region['target_h_mm']
    require(len(lo) == len(hi) == 3 and all(math.isfinite(x) for x in lo + hi), 'Invalid box')
    require(all(a < b for a, b in zip(lo, hi)) and math.isfinite(target) and target > 0, 'Invalid box/target')
    lengths = []; inside_edges = []; included = []
    for element, ids in elements:
        corners = [points[node] for node in ids[:4]]
        require(len(corners) == 4 and all(len(p) == 3 and all(math.isfinite(x) for x in p) for p in corners), 'Invalid tetrahedron')
        centre = [sum(p[d] for p in corners) / 4 for d in range(3)]
        inside = lambda p: all(a <= v <= b for v, a, b in zip(p, lo, hi))
        if inside(centre):
            included.append(element)
            lengths.extend(math.dist(corners[i], corners[j]) for i in range(4) for j in range(i))
        for i in range(4):
            for j in range(i):
                if inside(corners[i]) and inside(corners[j]):
                    inside_edges.append(math.dist(corners[i], corners[j]))
    require(included and lengths and inside_edges, 'No actual tetrahedra/whole edges in the requested box')
    require(min(lengths) > 0 and min(inside_edges) > 0, 'Degenerate corner edge')
    maximum = max(max(lengths), max(inside_edges))
    return dict(region_id=region['id'], bounds_mm=region['bounds_mm'], target_h_mm=target,
        source_measured_h_mm=region['measured_reference_h_mm'],
        centroid_selected_element_count=len(included), centroid_selected_element_ids=included,
        centroid_selected_six_edges_min_max_mm=[min(lengths), max(lengths)],
        all_mesh_whole_edge_incidences_with_both_endpoints_in_box_count=len(inside_edges),
        all_mesh_whole_edges_with_both_endpoints_in_box_min_max_mm=[min(inside_edges), max(inside_edges)],
        measured_h_mm=maximum, measured_to_target_ratio=maximum / target,
        measured_to_reference_ratio=maximum / region['measured_reference_h_mm'],
        target_attained=maximum <= target,
        measurement='Maximum whole corner-edge length across centroid-selected T10 elements and all whole edges fully inside the box; no edge clipping, no distance-based peak omission',
        qualification='measured_local_h_at_most_half_reference' if maximum <= target else 'target_not_attained_no_h2_claim')
