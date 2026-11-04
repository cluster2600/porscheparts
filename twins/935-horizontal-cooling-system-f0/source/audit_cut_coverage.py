#!/usr/bin/env python3
"""Fail closed if a selected cut contour omits observed scan segments."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np


def edge(a, b):
    """Return an unoriented edge using the reconstruction's endpoint precision."""
    a, b = tuple(a), tuple(b)
    return (a, b) if a <= b else (b, a)


def audit(segments, contour):
    segments = np.asarray(segments, dtype=float)
    contour = np.asarray(contour, dtype=float)
    if (segments.ndim != 3 or segments.shape[1:] != (2, 3) or not len(segments)
            or contour.ndim != 2 or contour.shape[1:] != (3,) or len(contour) < 3
            or not np.isfinite(segments).all() or not np.isfinite(contour).all()):
        raise ValueError('Finite nonempty segments and a contour with at least three points required')
    observed = np.round(segments, 6)
    selected = np.round(contour, 6)
    observed_edges = Counter(edge(a, b) for a, b in observed)
    contour_edges = Counter(edge(a, b) for a, b in zip(selected, np.roll(selected, -1, axis=0)))
    unmatched = observed_edges - contour_edges
    added = contour_edges - observed_edges
    return {
        'observed_segments': len(segments),
        'observed_segments_not_in_selected_contour': sum(unmatched.values()),
        'contour_edges_not_in_observed_segments': sum(added.values()),
        'all_observed_segments_retained': not unmatched,
        'rounding_decimal_places': 6,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_npz', type=Path, help='Private NPZ with segments and contour arrays')
    parser.add_argument('output_json', type=Path, help='New private report path')
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error('Output must be new')
    with np.load(args.input_npz, allow_pickle=False) as data:
        result = audit(data['segments'], data['contour'])
    result.update(input_sha256=hashlib.sha256(args.input_npz.read_bytes()).hexdigest(),
                  status='coverage_screen_not_a_physical_validation')
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if (result['all_observed_segments_retained']
                 and result['contour_edges_not_in_observed_segments'] == 0) else 1


if __name__ == '__main__':
    raise SystemExit(main())
