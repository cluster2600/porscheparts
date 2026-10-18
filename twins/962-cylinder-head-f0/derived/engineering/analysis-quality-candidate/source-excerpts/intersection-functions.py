def intersection_fixtures(cgal):
    base = [[0., 0, 0], [1., 0, 0], [0., 1, 0]]
    two = [[0, 1, 2], [3, 4, 5]]
    fixtures = [
        ("separate", base+[[0, 0, 1], [1, 0, 1], [0, 1, 1]], two, 0),
        ("crossing", base+[[.25, .25, -1], [.25, .25, 1], [.75, .25, 0]], two, 1),
        ("coplanar_contained", base+[[.1, .1, 0], [.2, .1, 0], [.1, .2, 0]], two, 1),
        ("coplanar_shared_vertex_overlap", base+[[.1, .1, 0], [.2, .1, 0]], [[0, 1, 2], [0, 3, 4]], 1),
        ("manifold_tetrahedron", base+[[0, 0, 1]], [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], 0)]
    rows = []
    for name, xyz, faces, expected in fixtures:
        p, f = np.array(xyz, dtype=np.float64), np.array(faces, dtype=np.int64)
        old_p, old_f = p.copy(), f.copy()
        result = cgal.remesh_self_intersections(p, f, detect_only=True, first_only=False,
            stitch_all=False, cutoff=100001)
        unchanged = np.array_equal(p, old_p) and np.array_equal(f, old_f)
        rows.append(dict(name=name, expected_pairs=expected, observed_pairs=len(result[2]),
            input_arrays_unchanged=unchanged))
        if len(result[2]) != expected or not unchanged:
            raise ValueError("Global intersection known-result fixture failed: " + name)
    return rows


def audit_intersections(report, p, f):
    import igl
    import igl.copyleft.cgal as cgal
    if importlib.metadata.version("libigl") != "2.6.3":
        raise ValueError("Observed pinned libigl 2.6.3 runtime required")
    report["runtime"]["libigl_version"] = importlib.metadata.version("libigl")
    report["runtime"]["cgal_wrapper_sha256"] = sha(Path(cgal.__file__))
    report["runtime"]["igl_binary_modules"] = {str(q.relative_to(Path(igl.__file__).parent)): sha(q)
        for q in Path(igl.__file__).parent.rglob("*.so")}
    report["known_result_fixtures"] = intersection_fixtures(cgal)
    vertex_manifold = np.asarray(igl.is_vertex_manifold(f), dtype=bool)
    report["nonmanifold_vertex_count"] = int(np.sum(~vertex_manifold))
    cap = 100001
    result = cgal.remesh_self_intersections(p, f, detect_only=True, first_only=False,
        stitch_all=False, cutoff=cap)
    pairs = np.asarray(result[2], dtype=np.int64).reshape(-1, 2)
    report["intersections"] = dict(pair_count=len(pairs), pair_cap=cap, complete=len(pairs) < cap,
        detect_only=True, first_only=False, stitch_all=False, pairs=pairs.tolist())
    report["gate_passed"] = len(pairs) == 0 and len(pairs) < cap and report["nonmanifold_vertex_count"] == 0
