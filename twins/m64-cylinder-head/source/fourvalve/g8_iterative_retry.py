#!/usr/bin/env python3
"""Retry existing G8 x decks with native incomplete Cholesky, without remeshing."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import numpy as np
import g8_pilot as g8


def deck_data(text):
    points, loads, mode = {}, {}, ''
    for line in text.splitlines():
        if line.startswith('*'):
            mode = line
        elif mode == '*NODE':
            fields = line.split(',')
            points[int(fields[0])] = np.array(list(map(float,fields[1:])))
        elif mode == '*CLOAD':
            n, d, value = line.split(',')
            if int(d) != 1 or int(n) in loads or not float(value) > 0:
                raise ValueError('retry expects positive x-only G8 loads')
            loads[int(n)] = float(value)
    if not points or not loads or text.count('\n*STATIC\n') != 1:
        raise ValueError('expected one G8 static deck')
    return points, loads


def run(root):
    rows = []
    start = time.monotonic()
    for size in (3.,2.):
        case = root/('carrier_base_p-'+str(size))
        source = case/'x.inp'
        text = source.read_text()
        points, loads = deck_data(text)
        target = case/'iterative-x.inp'
        with target.open('x') as f:
            f.write(text.replace('\n*STATIC\n','\n*STATIC,SOLVER=ITERATIVE CHOLESKY\n'))
        t = time.monotonic()
        with (case/'iterative-x.log').open('x') as log:
            done = subprocess.run(['ccx','iterative-x'],cwd=case,stdout=log,stderr=subprocess.STDOUT,
                                  timeout=600,env=dict(os.environ,OMP_NUM_THREADS='4',CCX_NPROC_STIFFNESS='4'))
        if done.returncode or '*ERROR' in (case/'iterative-x.log').read_text():
            raise ValueError('iterative solve failed: '+str(done.returncode))
        dat = case/'iterative-x.dat'
        u, rf = g8.vectors(dat,'displacements ('), g8.vectors(dat,'forces (')
        stress, displacement = g8.parse_dat(dat)
        if set(u) != set(points) or set(rf).intersection(loads):
            raise ValueError('incomplete result or loads on fixed nodes')
        total = sum(loads.values())
        residual = np.linalg.norm(np.sum(list(rf.values()),axis=0)+[total,0,0])/total
        moment = sum((np.cross(points[n],[f,0,0]) for n,f in loads.items()),np.zeros(3))
        rm = sum((np.cross(points[n],f) for n,f in rf.items()),np.zeros(3))
        moment_error = np.linalg.norm(moment+rm)/(total*100)
        equilibrium_ok = bool(np.isfinite(stress+displacement).all() and residual < 1e-4 and moment_error < 1e-4)
        row = {'size_mm':size,'seconds':time.monotonic()-t,'nodes':len(points),
               'source_deck_sha256':g8.sha256(source),'iterative_deck_sha256':g8.sha256(target),
               'dat_sha256':g8.sha256(dat),'log_sha256':g8.sha256(case/'iterative-x.log'),
               'force_balance_relative_error':float(residual),'moment_balance_F_times_100mm_error':float(moment_error),
               'equilibrium_passed':equilibrium_ok,
               'maximum_displacement_mm':max(displacement),'von_Mises_p95_MPa':g8.percentile(stress,.95),
               'von_Mises_max_MPa':max(stress),'journal_weighted_displacement_mm':{}}
        for side, sign in (('intake',-1),('exhaust',1)):
            selected = {n:f for n,f in loads.items() if points[n][0]*sign > 0}
            if not selected:raise ValueError('missing G8 journal load')
            row['journal_weighted_displacement_mm'][side] = (sum((f*np.array(u[n]) for n,f in selected.items()),np.zeros(3))/sum(selected.values())).tolist()
        if size == 3.:
            ref = g8.vectors(case/'x.dat','displacements (')
            if set(ref) != set(u):raise ValueError('direct reference node mismatch')
            row['direct_reference_dat_sha256'] = g8.sha256(case/'x.dat')
            error = max(np.linalg.norm(np.array(u[n])-ref[n]) for n in u)/max(np.linalg.norm(q) for q in ref.values())
            row['direct_solver_max_nodal_difference_over_max_U'] = float(error)
            row['direct_reference_agreement_passed'] = bool(error <= 1e-4)
        rows.append(row)
        print(json.dumps(row),flush=True)
        if not equilibrium_ok or not row.get('direct_reference_agreement_passed',True):
            break  # Fail closed, preserve the rejected result, do not attempt the larger deck.
    result = {'classification':'G8_existing_x_decks_iterative_resource_retry_not_full_campaign',
              'manufacturing_authorized':False,'engine_start_authorized':False,
              'full_three_mesh_two_direction_campaign_complete':False,
              'retry_accepted':len(rows)==2 and all(r['equilibrium_passed'] for r in rows),
              'source_sha256':g8.sha256(Path(__file__)),'pilot_source_sha256':g8.sha256(Path(g8.__file__)),
              'partial_direct_report_sha256':g8.sha256(root/'report.partial.json'),
              'rows':rows,'wall_seconds':time.monotonic()-start,
              'maximum_child_RSS_MiB_not_sum':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024,
              'container_memory_peak_bytes':int(Path('/sys/fs/cgroup/memory.peak').read_text()),
              'memory_events':Path('/sys/fs/cgroup/memory.events').read_text()}
    with (root/'iterative-retry.json').open('x') as f:
        f.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return 0 if result['retry_accepted'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    raise SystemExit(run(parser.parse_args().root))
