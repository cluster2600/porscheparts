#!/usr/bin/env python3
"""Two analytical solver checks; all inputs are synthetic, never head properties."""
import argparse
import json
from pathlib import Path
import re
import subprocess

BAR = '''*NODE
1,0,0,0
2,100,0,0
*ELEMENT,TYPE=T3D2,ELSET=BAR
1,1,2
*NSET,NSET=TIP
2
*MATERIAL,NAME=TEST
*ELASTIC
200000,0.3
*SOLID SECTION,ELSET=BAR,MATERIAL=TEST
10
*BOUNDARY
1,1,3
2,2,3
*STEP
*STATIC
*CLOAD
2,1,1000
*NODE PRINT,NSET=TIP
U
*END STEP
'''
HEAT = '''*NODE
1,0,0,0
2,1,0,0
3,1,1,0
4,0,1,0
5,0,0,1
6,1,0,1
7,1,1,1
8,0,1,1
*ELEMENT,TYPE=C3D8,ELSET=BLOCK
1,1,2,3,4,5,6,7,8
*MATERIAL,NAME=TEST
*CONDUCTIVITY
10
*SOLID SECTION,ELSET=BLOCK,MATERIAL=TEST
*STEP
*HEAT TRANSFER,STEADY STATE
*BOUNDARY
1,11,11,0
2,11,11,0
3,11,11,0
4,11,11,0
5,11,11,100
6,11,11,100
7,11,11,100
8,11,11,100
*EL PRINT,ELSET=BLOCK
HFL
*END STEP
'''


def main():
    p = argparse.ArgumentParser(); p.add_argument('output', type=Path); p.add_argument('--ccx', default='ccx')
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    results = {}
    for name, deck, width, expected in [('bar', BAR, 4, 0.05), ('heat', HEAT, 5, -1000.0)]:
        (a.output / f'{name}.inp').write_text(deck)
        with (a.output / f'{name}.log').open('w') as log:
            subprocess.run([a.ccx, '-i', name], cwd=a.output, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        rows = []
        for line in (a.output / f'{name}.dat').read_text().splitlines():
            words = line.split()
            if len(words) == width and re.fullmatch(r'\d+', words[0]):
                try: rows.append([float(v.replace('D', 'E')) for v in words])
                except ValueError: pass
        if not rows: raise ValueError(f'{name}: no solver result')
        observed = [row[1] if name == 'bar' else row[-1] for row in rows]
        error = max(abs(v - expected) / abs(expected) for v in observed)
        results[name] = {'expected': expected, 'observed': observed, 'relative_error': error, 'passed': error < 1e-5}
    passed = all(r['passed'] for r in results.values())
    (a.output / 'checks.json').write_text(json.dumps({'status': 'passed' if passed else 'failed',
        'synthetic_only': True, 'head_physics_validated': False, 'checks': results}, indent=2) + '\n')
    return 0 if passed else 1


if __name__ == '__main__': raise SystemExit(main())
