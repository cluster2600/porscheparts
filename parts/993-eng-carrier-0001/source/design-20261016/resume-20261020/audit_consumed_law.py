"""Audit saved GetLaw coefficients at the physical contour endpoints."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'carrier_radius_pieces', Path(__file__).with_name('law_certificate.py'))
MATHS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATHS)


def at_parameter(curve, parameter):
    """Return both incident polynomial evaluations at a knot, without averaging."""
    s = F(parameter)
    result = []
    for first, last, coefficients in MATHS.pieces(curve):
        if first <= s <= last:
            t = (s - first) / (last - first)
            value = sum(c * t ** i for i, c in enumerate(coefficients))
            slope = sum(i * coefficients[i] * t ** (i - 1)
                        for i in range(1, len(coefficients))) / (last - first)
            result.append(dict(span_mm=[str(first), str(last)],
                               parameter_mm=str(s), value_mm=str(value),
                               slope=str(slope), slope_float=float(slope),
                               value_exactly_zero=value == 0,
                               slope_exactly_zero=slope == 0))
    if not result:
        raise ValueError('Physical endpoint is outside the saved generated law')
    return result


def audit(assessment):
    rows = []
    for saved in assessment.get('consumed_laws', []):
        row = dict(contour=saved['contour'], source_edge=saved['source_edge'])
        rows.append(row)
        try:
            contour = assessment['contours'][saved['contour'] - 1]
            curve = saved['raw']['curve']
            standalone = contour['standalone_interpolation_before_any_assertion']['curve']
            row['generated_curve_equals_standalone'] = curve == standalone
            row['physical_domain_mm'] = contour['actual_domain_mm']
            row['physical_endpoints'] = [at_parameter(curve, s)
                                         for s in contour['actual_domain_mm']]
        except (KeyError, ValueError) as error:
            row['unresolved'] = str(error)
    complete = len(rows) == 8 and all('unresolved' not in r for r in rows)
    return dict(schema='carrier-saved-consumed-law-audit-1',
                source_edge_count=len(rows), complete=complete,
                all_physical_endpoint_slopes_exactly_zero=(
                    all(e['slope_exactly_zero'] for r in rows
                        for endpoint in r['physical_endpoints'] for e in endpoint)
                    if complete else None),
                rows=rows,
                scope='Exact arithmetic on saved binary64 coefficients; no new native run')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('assessment', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve the existing audit; choose a fresh output')
    raw = args.assessment.read_bytes()
    result = audit(json.loads(raw))
    result['assessment_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in
                      ['complete', 'source_edge_count',
                       'all_physical_endpoint_slopes_exactly_zero']}))


if __name__ == '__main__':
    main()
