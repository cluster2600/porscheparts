#!/usr/bin/env python3
"""Run tip recovery only when every observed cut edge is accounted for."""
import argparse
from collections import Counter
from pathlib import Path

import numpy as np

import recover_tip_sections
from audit_cut_coverage import audit, edge
from run_reconstruction import ordered_contours


def guarded_contours(segments, maximum_gap):
    contours = ordered_contours(segments, maximum_gap)
    if len(contours) != 1:
        raise ValueError('Cut must have exactly one complete accounted contour')
    points, repairs = contours[0]
    coverage = audit(segments, points)
    if not coverage['all_observed_segments_retained']:
        raise ValueError('Cut contour omits observed scan segments')
    observed = Counter(edge(a, b) for a, b in np.round(segments, 6))
    rounded = np.round(points, 6)
    contour = Counter(edge(a, b) for a, b in zip(rounded, np.roll(rounded, -1, axis=0)))
    added = contour - observed
    declared = Counter(edge(*np.round([r['a'], r['b']], 6)) for r in repairs)
    if added != declared:
        raise ValueError('Cut contains undeclared or unused repair edges')
    return contours


def prepare(case, output):
    # The historical module is hash-pinned by previous receipts; scope the guard
    # to this call and restore the original function even when recovery fails.
    original = recover_tip_sections.ordered_contours
    recover_tip_sections.ordered_contours = guarded_contours
    try:
        return recover_tip_sections.prepare(case, output)
    finally:
        recover_tip_sections.ordered_contours = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('new_output', type=Path)
    args = parser.parse_args()
    print(prepare(args.case, args.new_output))


if __name__ == '__main__':
    main()
