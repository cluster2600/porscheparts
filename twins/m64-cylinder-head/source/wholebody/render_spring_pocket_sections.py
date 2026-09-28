#!/usr/bin/env python3
"""Actual before/after body sections for the fixed, unreleased pocket prototype."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

from render_v5_v2 import PINS, preflight, save, sha
from spring_packaging import section_curves

REPORT_SHA = 'e1f56194ccb91fb0571cdc3531dabe8081effe8d9897882a5064c3acf851ae1a'
SECTION_HELPER_SHA = '04836203e87bd0538179906cf487b73aebb16d121d3ef7602e31a67858facc8b'


def render(root, run, output):
    import OCP
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    preflight(root)
    helper = Path(__file__).with_name('spring_packaging.py')
    report_path = run / 'report.json'
    if (OCP.__version__ != '7.9.3.1' or sha(report_path) != REPORT_SHA
            or sha(helper) != SECTION_HELPER_SHA):
        raise ValueError('exact_prototype_and_section_helper_required')
    report = json.loads(report_path.read_text())
    if (report['inputs_sha256'] != PINS or report['manufacturing_authorized']
            or report['longer_valves_modeled'] or report['status'] != 'native_prototype_gates_passed'):
        raise ValueError('unreleased_body_only_prototype_required')
    paths = {'before': root / 'candidate.binbrep', 'after': run / 'candidate.binbrep'}
    hashes = {'before': PINS['candidate.binbrep'], 'after': report['outputs_sha256']['candidate.binbrep']}
    if any(p.is_symlink() or sha(p) != hashes[k] for k, p in paths.items()):
        raise ValueError('body_hash_mismatch')
    source_sha = sha(__file__)
    cad = design.CAD()
    sections = {}
    for name, path in paths.items():
        shape = TopoDS_Shape()
        if not BinTools.Read_s(shape, str(path)) or not cad.valid(shape) or cad.indexed(shape, cad.TopAbs_SOLID).Extent() != 1:
            raise ValueError('one_valid_native_body_required')
        sections[name] = section_curves(cad, shape, 22.5)
        if not sections[name]:
            raise ValueError('empty_native_section')
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="750" viewBox="0 0 1600 750">',
           '<rect width="1600" height="750" fill="#14212b"/>', '<g font-family="sans-serif" fill="#edf3f8">',
           '<text x="40" y="48" font-size="29">Culasse — quatre logements de ressorts, prototype CAO</text>',
           '<text x="40" y="83" font-size="18">Même coupe native X = +22,5 : deux des quatre logements traversés par le plan</text>']
    for panel, (name, title, color) in enumerate((('before', 'AVANT — corps V5', '#bbc7cf'),
                                                ('after', 'APRÈS — logements relevés, corps candidat', '#62d5c6'))):
        svg.append(f'<text x="{40 + 780 * panel}" y="137" font-size="22" fill="{color}">{title}</text>')
        for curve in sections[name]:
            points = ' '.join(f'{65 + panel * 780 + (y + 90) * 3.25:.2f},{495 - z * 3.25:.2f}' for y, z in curve)
            svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5"/>')
    svg += ['<text x="40" y="560" font-size="20">1 solide conservé après découpe et relecture ; contrôle géométrique, pas validation moteur.</text>',
            '<text x="40" y="602" font-size="18">Enveloppes nominales des ressorts dégagées ; séparation minimale aux conduits : 4,01 unités du scan.</text>',
            '<text x="40" y="642" font-size="18" fill="#ffb7a4">À concevoir : tiges +23, coupelles/clavettes, commande et appuis de ressorts côté échappement.</text>',
            '<text x="40" y="685" font-size="17">Corps seulement. Échelle non calibrée ; 1 unité/mm supposé. Pas de qualification thermique, mécanique ou fabrication.</text>',
            '<text x="40" y="718" font-size="16">Courbes CAO échantillonnées pour affichage ; pas de lissage, aucune image générative, aucune modification du maître.</text>',
            '</g></svg>']
    target = output / 'spring-pockets-before-after.svg'
    with target.open('x') as stream:
        stream.write('\n'.join(svg) + '\n')
    if any(sha(p) != hashes[k] for k, p in paths.items()) or sha(__file__) != source_sha or sha(helper) != SECTION_HELPER_SHA:
        raise ValueError('input_or_source_changed')
    save(output / 'render-receipt.json', {'source_sha256': source_sha, 'section_helper_sha256': SECTION_HELPER_SHA,
         'prototype_report_sha256': REPORT_SHA, 'body_hashes': hashes, 'SVG_sha256': sha(target),
         'curves_per_body': {k: len(v) for k, v in sections.items()}, 'plane_X': 22.5,
         'display_sampling': '41_points_per_native_curve_not_metrology', 'inputs_unchanged': True,
         'manufacturing_authorized': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'run', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    signal.alarm(300)
    render(args.root, args.run, args.output)
