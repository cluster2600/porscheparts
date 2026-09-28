#!/usr/bin/env python3
"""Display native cross-sections of the exact saved 13-solid assembly."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

from render_v5_v2 import save, sha
from spring_packaging import section_curves

ASSEMBLY_SHA = '26e6108befb19fda527b1f6b0976bce98d625400dd0dca0abcca9472ad109f01'
REPORT_SHA = '4a70920663d43bea0546f21eb40a8d5253beeb5f8fe797ecc0baf90db426e1fa'
DEPENDENCIES = {'spring_packaging.py':'04836203e87bd0538179906cf487b73aebb16d121d3ef7602e31a67858facc8b',
                'render_v5_v2.py':'63ccd3df8f07997a1bbeb6d7ba1434732622c7fc41106483ace0155ff00c3947',
                'build_four_valve_distribution.py':'4604b5fbc74e02c7029481cdf269a3ee93d208229d87379bc6545db46bdb3d1c'}
COLORS = {'body':'#9daebc','valve':'#53e0dc','seat':'#ffd271','guide':'#c99aff'}


def render(assembly, output):
    import OCP
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import build_four_valve_distribution as design
    sources={Path(__file__).name:Path(__file__),
             **{n:Path(__file__).with_name(n) for n in DEPENDENCIES if n!='build_four_valve_distribution.py'},
             'build_four_valve_distribution.py':Path(design.__file__)}
    source_hashes={n:sha(p) for n,p in sources.items()}
    paths={assembly/'extended-valve-assembly.binbrep':ASSEMBLY_SHA,assembly/'report.json':REPORT_SHA}
    def gate():
        if OCP.__version__!='7.9.3.1' or any(source_hashes[n]!=h for n,h in DEPENDENCIES.items()):
            raise ValueError('exact_native_runtime_and_helpers_required')
        if any(p.is_symlink() or sha(p)!=h for p,h in paths.items()) or any(sha(p)!=source_hashes[n] for n,p in sources.items()):
            raise ValueError('source_or_input_hash_changed')
    gate();report=json.loads((assembly/'report.json').read_text());cad=design.CAD();shape=TopoDS_Shape()
    if not BinTools.Read_s(shape,str(assembly/'extended-valve-assembly.binbrep')) or not cad.valid(shape):
        raise ValueError('saved_assembly_native_invalid')
    solids=cad.indexed(shape,cad.TopAbs_SOLID)
    if solids.Extent()!=13 or report['assembly_sha256']!=ASSEMBLY_SHA or report['assembly_solids']!=13:
        raise ValueError('thirteen_bound_solids_required')
    parts=[{'name':'body','assembly_solid_id':1}]+report['parts']
    sections=[]
    for x in (-22.5,22.5):
        for part in parts:
            curves=section_curves(cad,solids.FindKey(part['assembly_solid_id']),x)
            if curves:sections.append({'x':x,'name':part['name'],'curves':curves})
    os.umask(0o077);output.mkdir(mode=0o700,parents=True,exist_ok=False)
    save(output/'section-curves.json',sections)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1030" viewBox="0 0 1600 1030">',
         '<rect width="1600" height="1030" fill="#14212b"/>','<g font-family="sans-serif" fill="#edf3f8">',
         '<text x="35" y="45" font-size="27">Padded head + four extended valves — actual saved native CAD</text>',
         '<text x="35" y="80" font-size="18">13-solid integration checkpoint: body, 4 valves, 4 seats, 4 guides. Closed position.</text>']
    for col,x in enumerate((-22.5,22.5)):
        left,top,scale=50+col*780,150,5.5
        svg += [f'<text x="{left}" y="{top-22}" font-size="20">Native cross-section X={x:+g}</text>',
                f'<defs><clipPath id="clip-{col}"><rect x="{left}" y="{top}" width="700" height="620"/></clipPath></defs>',
                f'<rect x="{left}" y="{top}" width="700" height="620" fill="#1b2b36" stroke="#405260"/>']
        for z in (0,20,40,60,80,100):
            py=top+(110-z)*scale
            svg += [f'<line x1="{left}" y1="{py}" x2="{left+700}" y2="{py}" stroke="#2b3f4c"/>',
                    f'<text x="{left+5}" y="{py-5}" font-size="13" fill="#879aa8">Z {z}</text>']
        svg.append(f'<g clip-path="url(#clip-{col})">')
        for section in (s for s in sections if s['x']==x):
            kind=section['name'].split('_')[-1]
            for curve in section['curves']:
                points=' '.join(f'{left+(y+64)*scale:.3f},{top+(110-z)*scale:.3f}' for y,z in curve)
                svg.append(f'<polyline points="{points}" fill="none" stroke="{COLORS[kind]}" stroke-width="{1.3 if kind=="body" else 2.5}"/>')
        svg.append('</g>')
    for col,(name,color) in enumerate(COLORS.items()):
        svg.append(f'<text x="{60+col*380}" y="825" font-size="21" fill="{color}">{name.upper()}</text>')
    svg += ['<text x="35" y="875" font-size="20">Exact retained radius-3 stems extended by 23 to axial tip 105; lower profiles retained.</text>',
            '<text x="35" y="912" font-size="17">Eight empty body/valve intersection screens: closed and full-lift endpoints only. No continuous-motion validation.</text>',
            '<text x="35" y="949" font-size="17" fill="#ffbcaa">Springs, retainers, locks, cams and other hardware are not integrated. Not a complete or physically qualified head.</text>',
            '<text x="35" y="986" font-size="16">Uncalibrated scan units. 41 samples per native section edge for display only; equal axis scales; no smoothing or repair.</text>',
            '</g></svg>']
    target=output/'extended-valve-assembly-sections.svg'
    with target.open('x') as out:out.write('\n'.join(svg)+'\n')
    gate();save(output/'render-receipt.json',{'source_sha256':source_hashes,'assembly_sha256':ASSEMBLY_SHA,
         'assembly_report_sha256':REPORT_SHA,'assembly_solids':13,'exact_BRepCheck_valid':True,
         'SVG_sha256':sha(target),'curves_sha256':sha(output/'section-curves.json'),
         'planes_X':[-22.5,22.5],'view':'native_planar_sections_closed_position',
         'curve_counts':[{'x':s['x'],'name':s['name'],'count':len(s['curves'])} for s in sections],
         'inputs_and_source_unchanged':True,'geometry_modified':False,'physical_or_motion_qualification':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('assembly','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();signal.alarm(300);render(args.assembly,args.output)
