"""Ideal elastic-perfectly-plastic load/unload sensitivity, not an AM material fit."""
import json
import sys
from pathlib import Path

import numpy as np

from print_simulation import frames
from simulate import execute, von_mises


def run(folder, support):
    fixture = f'spring-{support:g}' if support else 'rigid'
    original = folder/f'combined-{fixture}-nonlinear.inp'
    name = f'combined-{fixture}-ideal-plastic'
    assert not (folder/(name+'.inp')).exists()
    deck = original.read_text()
    assert '*PLASTIC' not in deck and deck.count('*END STEP') == 1
    deck = deck.replace('*DENSITY', '*PLASTIC\n955,0\n955,0.1\n*DENSITY')
    deck = deck.replace('*STEP,NLGEOM,INC=100', '*STEP,NLGEOM,INC=250')
    deck = deck.replace('0.1,1,0.001,0.2', '0.1,1,0.000001,0.1')
    deck = deck.replace('*NODE PRINT,NSET=ALLN', '*NODE PRINT,NSET=ALLN,FREQUENCY=999999')
    deck = deck.replace('*NODE PRINT,NSET=FIXED', '*NODE PRINT,NSET=FIXED,FREQUENCY=999999')
    deck = deck.replace('*EL PRINT,ELSET=BODY\nS', '*EL PRINT,ELSET=BODY,FREQUENCY=999999\nS,PEEQ')
    deck += ('*STEP,NLGEOM,INC=250\n*STATIC,SOLVER=SPOOLES\n0.1,1,0.000001,0.1\n'
             '*CLOAD,OP=NEW\n*NODE PRINT,NSET=ALLN,FREQUENCY=999999\nU\n'
             '*EL PRINT,ELSET=BODY,FREQUENCY=999999\nS,PEEQ\n*END STEP\n')
    (folder/(name+'.inp')).write_text(deck)
    seconds = execute(folder, name, timeout_seconds=1800)
    steps = frames(folder/(name+'.dat')); assert len(steps) == 2
    plastic = []; active = False
    for line in (folder/(name+'.dat')).read_text().splitlines():
        if 'equivalent plastic strain' in line.lower():
            plastic.append([]); active = True
        elif line.strip() and line.strip()[0].isalpha(): active = False
        fields = line.split()
        if active and len(fields) == 3 and fields[0].isdigit():
            plastic[-1].append([float(x.replace('D', 'E')) for x in fields])
    assert len(plastic) == 2 and all(plastic)
    result = {'name': name, 'seconds': seconds, 'reference_yield_MPa': 955,
              'hardening': 'ideal perfect plasticity; no measured stress-strain curve',
              'material_model_calibrated': False, 'stages': []}
    for label, row, pe in zip(('loaded', 'unloaded'), steps, plastic):
        u = row['displacements'][:, 1:]; s = row['stresses']; pe = np.asarray(pe)
        assert np.isfinite(u).all() and np.isfinite(s).all() and np.isfinite(pe).all()
        vm = von_mises(s[:, 2:])
        item = {'stage': label, 'U_max_mm': float(np.linalg.norm(u, axis=1).max()),
                'VM_max_MPa': float(vm.max()), 'PEEQ_max': float(pe[:, 2].max()),
                'integration_points_with_PEEQ_gt_1e_6': int(np.count_nonzero(pe[:, 2] > 1e-6))}
        result['stages'].append(item)
        np.savez_compressed(folder/(name+'-'+label+'.npz'), displacement=u,
                            element_ids=s[:, 0].astype(int), stress=s[:, 2:], VM=vm, PEEQ=pe)
    (folder/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    run(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else None)
