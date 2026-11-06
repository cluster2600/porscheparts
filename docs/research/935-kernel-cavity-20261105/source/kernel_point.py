"""Propose a cavity kernel point; exact inequalities/dual bounds remain authoritative."""
from fractions import Fraction as Q
import math


def solve_columns(columns, rhs):
    """Solve an overdetermined full-column-rank rational system exactly."""
    width = len(columns)
    assert 0 < width <= len(rhs)
    rows = [[Q(column[i]) for column in columns]+[Q(rhs[i])] for i in range(len(rhs))]
    rank = 0; pivots = []
    for column in range(width):
        pivot = next((i for i in range(rank, len(rows)) if rows[i][column]), None)
        assert pivot is not None, "Dependent proposed dual support"
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        factor = rows[rank][column]; rows[rank] = [x/factor for x in rows[rank]]
        for i in range(len(rows)):
            if i != rank:
                factor = rows[i][column]
                rows[i] = [a-factor*b for a, b in zip(rows[i], rows[rank])]
        pivots.append((rank, column)); rank += 1
    assert all(any(row[:width]) or row[-1] == 0 for row in rows), "Inconsistent exact dual support"
    return [rows[r][-1] for r, _ in pivots]


def inequalities(nodes, faces, geometry):
    ids = sorted({int(i) for face in faces for i in face})
    points, denominator = geometry.exact_points(nodes, ids)
    origin = points[ids[0]]
    extent = max(abs(p[a]-origin[a]) for p in points.values() for a in range(3))
    assert extent > 0
    span = 1 << (extent-1).bit_length()
    rows = []; bounds = []
    for face in faces:
        a, b, c = [points[int(i)] for i in face]
        normal = geometry.cross(geometry.sub(b, a), geometry.sub(c, a))
        norm = sum(abs(v) for v in normal); assert norm > 0
        rows.append(tuple(Q(n, norm) for n in normal)+(Q(1),))
        bounds.append(Q(geometry.dot(normal, geometry.sub(a, origin)), span*norm))
    return rows, bounds, origin, span, denominator


def exact_dual(rows, bounds, support):
    assert len(support) == len(set(support)) and all(0 <= i < len(rows) for i in support)
    weights = solve_columns([rows[i] for i in support], [0, 0, 0, 1])
    assert min(weights) >= 0
    assert all(sum(w*rows[i][a] for i, w in zip(support, weights)) == (a == 3) for a in range(4))
    upper = sum(w*bounds[i] for i, w in zip(support, weights))
    return weights, upper


def linear_proposal(rows, bounds):
    import numpy as np
    from scipy.optimize import linprog
    result = linprog([0., 0., 0., -1.], A_ub=np.asarray(rows, dtype=float), b_ub=np.asarray(bounds, dtype=float),
                     bounds=[(None, None)]*4, method="highs-ds", options={"time_limit": 10., "maxiter": 10000})
    assert result.status == 0 and result.success and np.isfinite(result.x).all(), "LP did not return a finite successful proposal"
    support = [int(i) for i in np.flatnonzero(result.ineqlin.marginals < 0)]
    dual = None
    try:
        weights, upper = exact_dual(rows, bounds, support)
        dual = {"support": support, "weights": [[str(w.numerator), str(w.denominator)] for w in weights],
                "normalized_margin_upper_bound": [str(upper.numerator), str(upper.denominator)],
                "no_strict_kernel_proved": upper <= 0}
    except AssertionError:
        pass
    return {"coordinates": [float(x) for x in result.x[:3]], "proposed_normalized_radius": float(result.x[3]),
            "solver_status": int(result.status), "iterations": int(result.nit), "exact_dual": dual,
            "floating_lp_success_is_not_an_admission": True}


def propose(nodes, faces, geometry):
    rows, bounds, origin, span, denominator = inequalities(nodes, faces, geometry)
    result = linear_proposal(rows, bounds)
    exact_point = [(Q(origin[a])+span*Q.from_float(result["coordinates"][a]))/denominator for a in range(3)]
    point = [float(x) for x in exact_point]
    assert all(math.isfinite(x) for x in point)
    # Recompute every inequality from the once-rounded stored world point.
    local = [(denominator*Q.from_float(point[a])-origin[a])/span for a in range(3)]
    margin = min(b-sum(row[a]*local[a] for a in range(3)) for row, b in zip(rows, bounds))
    result.update(point_hex=[x.hex() for x in point],
                  exact_stored_normalized_margin=[str(margin.numerator), str(margin.denominator)],
                  strict_kernel_for_stored_point=margin > 0,
                  exact_affine_frame={"origin": list(origin), "span": span, "denominator": denominator})
    return result
