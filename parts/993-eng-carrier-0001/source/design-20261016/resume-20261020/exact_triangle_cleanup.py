"""Remove only repeated-index facets whose entire point set is already retained."""


def cleanup_certificate(faces):
    removed=[i for i,face in enumerate(faces) if len({int(v) for v in face})<3]
    certificate=dict(removed_source_triangle_indices=removed,
                     removed_count=len(removed),coordinate_changes=False,
                     welding_tolerance_used=False)
    if not removed:
        certificate.update(all_removed_vertices_covered=True,all_removed_segments_covered=True)
        return None,certificate
    excluded=set(removed);kept=[i for i in range(len(faces)) if i not in excluded]
    vertices=set();edges=set()
    for i in kept:
        a,b,c=map(int,faces[i]);vertices.update((a,b,c))
        edges.update((tuple(sorted((a,b))),tuple(sorted((b,c))),tuple(sorted((c,a)))))
    vertices_covered=all(int(v) in vertices for i in removed for v in faces[i])
    segments_covered=all(tuple(sorted((int(a),int(b)))) in edges
                         for i in removed for a in faces[i] for b in faces[i] if a!=b)
    certificate.update(all_removed_vertices_covered=vertices_covered,
                       all_removed_segments_covered=segments_covered)
    if not vertices_covered or not segments_covered:
        raise ValueError('Degenerate facet carries an uncovered point or segment: '+str(certificate))
    return kept,certificate
