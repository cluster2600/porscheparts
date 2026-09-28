#!/usr/bin/env python3
"""Native section curves through the two corrected exhaust support sectors."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

from render_v5_v2 import save, sha
from spring_packaging import section_curves

BODY_PINS = {'before':'2969035f9a802d08652c295e310591788f851d2ace2935c484c0e90c36c9a9af',
             'after':'111342292d92b7303072ecc5be606047ac810df25ee4fa5c112f992404224c60'}
REPORT_SHA = 'da3dd990f8ef802459cdedb8efd0600aa9274632303b11dd978cdf761d17272a'
HELPER_SHA = '04836203e87bd0538179906cf487b73aebb16d121d3ef7602e31a67858facc8b'


def render(pockets, pads, output):
    import OCP
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    helper = Path(__file__).with_name('spring_packaging.py')
    if OCP.__version__ != '7.9.3.1' or sha(helper) != HELPER_SHA or sha(pads/'report.json') != REPORT_SHA:
        raise ValueError('exact_saved_pad_prototype_required')
    paths = {'before':pockets/'candidate.binbrep','after':pads/'candidate.binbrep'}
    if any(p.is_symlink() or sha(p) != BODY_PINS[n] for n,p in paths.items()):
        raise ValueError('saved_body_hash_mismatch')
    source_sha = sha(__file__); cad = design.CAD(); sections = []
    for name,path in paths.items():
        body = TopoDS_Shape()
        if not BinTools.Read_s(body,str(path)) or not cad.valid(body) or cad.indexed(body,cad.TopAbs_SOLID).Extent() != 1:
            raise ValueError('one_valid_body_required')
        for x in (-34.,34.):
            curves = section_curves(cad,body,x)
            if not curves:
                raise ValueError('empty_native_section')
            sections.append({'name':name,'x':x,'curves':curves})
    os.umask(0o077); output.mkdir(mode=0o700,parents=True,exist_ok=False)
    save(output/'section-curves.json',sections)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1030" viewBox="0 0 1600 1030">',
           '<rect width="1600" height="1030" fill="#14212b"/>',
           '<g font-family="sans-serif" fill="#edf3f8">',
           '<text x="35" y="45" font-size="27">Exhaust spring-seat support — actual native body sections</text>',
           '<text x="35" y="78" font-size="18">Local fin-contour correction; before / after at the same position and scale</text>']
    for row,x in enumerate((-34.,34.)):
        for col,name in enumerate(('before','after')):
            left,top = 50+col*780,150+row*360
            color = '#b9c5cd' if name == 'before' else '#61d8bd'
            svg += [f'<text x="{left}" y="{top-25}" font-size="20" fill="{color}">{name.upper()} — exhaust {row+1}, X={x:+g}</text>',
                    f'<defs><clipPath id="clip-{row}-{col}"><rect x="{left}" y="{top}" width="690" height="285"/></clipPath></defs>',
                    f'<rect x="{left}" y="{top}" width="690" height="285" fill="#1b2b36" stroke="#405260"/>']
            for z in (54,58,62,66):
                py=top+(66-z)*20
                svg.append(f'<line x1="{left}" y1="{py}" x2="{left+690}" y2="{py}" stroke="#2b3f4c"/>')
                svg.append(f'<text x="{left+5}" y="{py+17}" font-size="13" fill="#879aa8">Z {z}</text>')
            svg.append(f'<g clip-path="url(#clip-{row}-{col})">')
            section=next(s for s in sections if s['name']==name and s['x']==x)
            for curve in section['curves']:
                points=' '.join(f'{left+(y+53)*20:.3f},{top+(66-z)*20:.3f}' for y,z in curve)
                svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
            svg.append('</g>')
    svg += ['<text x="35" y="900" font-size="20">Two annular pads: axial 55.1–58.1; radii 7–16. Added material ≈135.07 scan-unit³.</text>',
            '<text x="35" y="935" font-size="18">Four complete native washer footprints after saved-file reread. Overall bounding box unchanged; local skin is changed.</text>',
            '<text x="35" y="970" font-size="17" fill="#ffbcaa">Not a structural, cooling, hot-fit or manufacturing approval. Springs, retainers, locks and actuation are not shown.</text>',
            '<text x="35" y="1005" font-size="16">Uncalibrated scan units. Curves sampled at 41 points for display only; no smoothing, repair or generative image.</text>',
            '</g></svg>']
    target=output/'spring-seat-pads-before-after.svg'
    with target.open('x') as out:out.write('\n'.join(svg)+'\n')
    if any(sha(p)!=BODY_PINS[n] for n,p in paths.items()) or sha(__file__)!=source_sha or sha(helper)!=HELPER_SHA:
        raise ValueError('inputs_or_source_changed')
    save(output/'render-receipt.json',{'source_sha256':source_sha,'section_helper_sha256':HELPER_SHA,
         'candidate_report_sha256':REPORT_SHA,'body_hashes':BODY_PINS,'SVG_sha256':sha(target),
         'curves_json_sha256':sha(output/'section-curves.json'),'planes_X':[-34.,34.],
         'display_sampling':'41_points_per_native_curve_not_metrology','equal_axis_scale':True,
         'raw_geometry_or_master_modified':False,'inputs_unchanged':True,'manufacturing_authorized':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pockets','pads','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();signal.alarm(300);render(args.pockets,args.pads,args.output)
