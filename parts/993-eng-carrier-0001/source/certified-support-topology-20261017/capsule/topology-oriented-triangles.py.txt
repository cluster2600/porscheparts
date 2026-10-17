"""Pure original-ID normalization: face permutation and cyclic rotations only."""
import copy


def normalise_oriented_triangles(triangles):
    """Return a canonical two-face tuple without permitting orientation reversal.

    Inputs are plain JSON-style integer IDs. No coordinate, tolerance, geometry
    edit, mesh library or cyclic permutation of the four-vertex boundary occurs.
    """
    if not isinstance(triangles, (list, tuple)) or len(triangles) != 2:
        raise ValueError('Exactly two triangles required')
    result = []
    for triangle in triangles:
        if not isinstance(triangle, (list, tuple)) or len(triangle) != 3:
            raise ValueError('Exactly three original integer IDs per triangle required')
        if any(type(v) is not int for v in triangle) or len(set(triangle)) != 3:
            raise ValueError('Distinct plain integer vertex IDs required')
        t = tuple(triangle)
        result.append(min(t, t[1:] + t[:1], t[2:] + t[:2]))
    if result[0] == result[1]:
        raise ValueError('Duplicate oriented face is not a two-face patch')
    return tuple(sorted(result))


def bind_operations(packet, native_lines):
    """Return a deep copy whose step triangles come from native rows in PLAN order.

    ``native_lines`` is the already parsed ordered list of JSONL dictionaries.
    The caller must separately verify native execution, exact coordinates and
    provenance. This pure function checks only names and oriented topology.
    The existing face_pair and row-to-face assignment are never reordered.
    """
    result = copy.deepcopy(packet)
    steps = [(operation['name'], index, step) for operation in result['operations']
             for index, step in enumerate(operation['steps'])]
    names = [name + '-step-' + str(index) for name, index, _ in steps]
    if not steps or len(set(names)) != len(names) or len(native_lines) != len(steps):
        raise ValueError('One unique native case per finite operation step required')
    if [row['case'] for row in native_lines] != names:
        raise ValueError('Native case order or step identity differs')
    bindings = []
    for row, (name, index, step) in zip(native_lines, steps):
        native = row['triangles_original_vertex_ids']
        target = step['new_triangles']
        canonical = normalise_oriented_triangles(native)
        if canonical != normalise_oriented_triangles(target):
            raise ValueError('Native oriented topology differs from operation step')
        aligned, mapping = [None, None], []
        for native_face, triangle in enumerate(native):
            t = list(triangle)
            rotations = [t, t[1:] + t[:1], t[2:] + t[:2]]
            matches = [(face, rotation, candidate) for face, planned in enumerate(target)
                       for rotation, candidate in enumerate(rotations) if candidate == list(planned)]
            if len(matches) != 1:
                raise ValueError('Unique orientation-preserving native face match required')
            face, rotation, candidate = matches[0]
            if aligned[face] is not None:
                raise ValueError('Two native faces map to the same planned face')
            aligned[face] = candidate[:]
            mapping.append({'native_face': native_face, 'plan_face': face,
                            'cyclic_left_rotation': rotation})
        if any(face is None for face in aligned):
            raise ValueError('A planned face has no native match')
        step['new_triangles'] = aligned
        bindings.append({'case': row['case'], 'operation': name, 'step': index,
                         'face_pair': copy.deepcopy(step['face_pair']),
                         'native_to_plan_faces': mapping,
                         'native_triangles_in_plan_face_order': aligned,
                         'canonical_oriented_triangles': canonical,
                         'oriented_triangles_equal': True})
    return result, {'cases_verified': len(steps), 'operation_count': len(result['operations']),
                    'normalized_rows_used': True, 'plan_face_assignment_preserved': True,
                    'orientation_reversal_permitted': False, 'bindings': bindings,
                    'mesh_applied_or_written': False, 'global_admission': False}
