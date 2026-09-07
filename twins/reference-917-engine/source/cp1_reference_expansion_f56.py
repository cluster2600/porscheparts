#!/usr/bin/env python3
"""Conditional reference strain from published interval-mean CP1 expansion."""
import argparse
import json
import math
from pathlib import Path


def reference_strain(card, temperature_c):
    if not math.isfinite(temperature_c):
        raise ValueError('finite temperature required')
    expansion = card['thermal_expansion_reference']
    ref = expansion['reference_temperature_c']
    nodes = [(ref, 0.)]
    for item in expansion['published_intervals']:
        if item['lower_c'] != ref:
            raise ValueError('inconsistent expansion reference temperature')
        nodes.append((item['upper_c'], item['coefficient_per_k'] * (item['upper_c'] - ref)))
    if any(b[0] <= a[0] for a, b in zip(nodes, nodes[1:])):
        raise ValueError('temperature nodes must strictly increase')
    if not nodes[0][0] <= temperature_c <= nodes[-1][0]:
        raise ValueError('extrapolation outside published temperature intervals forbidden')
    for (ta, ea), (tb, eb) in zip(nodes, nodes[1:]):
        if temperature_c <= tb:
            return ea + (eb-ea)*(temperature_c-ta)/(tb-ta)
    raise AssertionError('unreachable interpolation interval')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--card', type=Path, required=True)
    p.add_argument('--temperature-c', type=float, required=True)
    a = p.parse_args()
    card = json.loads(a.card.read_text())
    print(json.dumps({'temperature_c': a.temperature_c,
                      'conditional_reference_strain': reference_strain(card, a.temperature_c),
                      'supplier_interpretation_confirmed': False,
                      'part_distortion_computed': False,
                      'manufacturing_authorized': False}))


if __name__ == '__main__':
    main()
