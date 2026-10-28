"""Exact arithmetic on the serialized native B-spline, without sampled bounds."""
from fractions import Fraction as F


def add(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else F(0)) +
            (b[i] if i < len(b) else F(0)) for i in range(n)]


def multiply(a, b):
    result = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] += x * y
    return result


def pieces(curve):
    """De Boor polynomial pieces in each span's local t in [0,1]."""
    degree = curve['degree']
    poles = [F(x) for x in curve['poles']]
    knots = [F(x) for x, m in zip(curve['knots_mm'],
                                  curve['multiplicities']) for _ in range(m)]
    if curve['rational'] or curve['periodic']:
        raise ValueError('Only a nonrational, nonperiodic law is supported')
    if len(knots) != len(poles) + degree + 1:
        raise ValueError('Invalid B-spline dimensions')
    result = []
    for k in range(degree, len(poles)):
        first, last = knots[k:k + 2]
        if first == last:
            continue
        d = [[poles[k - degree + j]] for j in range(degree + 1)]
        for r in range(1, degree + 1):
            for j in range(degree, r - 1, -1):
                i = k - degree + j
                denominator = knots[i + degree - r + 1] - knots[i]
                if denominator == 0:
                    raise ValueError('Unresolved zero De Boor denominator')
                alpha = [(first - knots[i]) / denominator,
                         (last - first) / denominator]
                d[j] = add(multiply([1 - alpha[0], -alpha[1]], d[j - 1]),
                           multiply(alpha, d[j]))
        result.append((first, last, d[degree]))
    return result


def certify(curve):
    """Certify the declared zero-endpoint R1 clamped two-span cubic design."""
    spans = pieces(curve)
    records, valid = [], curve['degree'] == 3 and len(spans) == 2
    for index, (first, last, coefficients) in enumerate(spans):
        c = coefficients + [F(0)] * (4 - len(coefficients))
        if len(c) != 4:
            valid = False
            continue
        derivative = [c[1], 2 * c[2], 3 * c[3]]
        bernstein = [derivative[0], derivative[0] + derivative[1] / 2,
                     sum(derivative)]
        start, end = c[0], sum(c)
        monotone = (all(x >= 0 for x in bernstein) if index == 0
                    else all(x <= 0 for x in bernstein))
        expected = (F(0), F(1)) if index == 0 else (F(1), F(0))
        passed = (start, end) == expected and monotone
        valid = valid and passed
        records.append(dict(domain_mm=[str(first), str(last)],
                            local_power_coefficients=[str(x) for x in c],
                            derivative_Bernstein=[str(x) for x in bernstein],
                            start=str(start), end=str(end), monotone=monotone,
                            passed=passed))
    if len(spans) == 2:
        a, b = spans
        ca, cb = a[2], b[2]
        endpoint_C1 = ca[1] == sum(i * ca[i] for i in range(1, len(ca))) == \
            cb[1] == sum(i * cb[i] for i in range(1, len(cb))) == 0
        domains_join = a[1] == b[0] and a[0] == 0 and b[1] > 0
        valid = valid and endpoint_C1 and domains_join
    else:
        endpoint_C1 = domains_join = False
    return dict(passed=bool(valid), exact_serialized_binary64_arithmetic=True,
                radius_range_mm=[0, 1] if valid else None,
                zero_endpoint_and_join_derivatives=endpoint_C1,
                domains_join=domains_join, pieces=records,
                scope='Standalone interpolant only; not the law consumed by Compute')
