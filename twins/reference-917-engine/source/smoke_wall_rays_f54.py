#!/usr/bin/env python3
"""Exercise the CAD-ray checker on an exact unit-thickness synthetic box."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--helpers', type=Path, required=True)
    p.add_argument('--checker', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from repair_topology_f42_1 import write_step
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    step, probes, report = (a.output / name for name in ('box.step', 'probes.npz', 'report.json'))
    write_step(BRepPrimAPI_MakeBox(1., 10., 10.).Shape(), step)
    np.savez_compressed(probes, points=np.array([[0.,5.,5.], [0.,5.,5.]]),
                        normals=np.array([[-1.,0.,0.], [1.,0.,0.]]),
                        ray=np.array([1.,1.]), max_sphere=np.array([1.,1.]))
    subprocess.run([sys.executable, str(a.checker), '--helpers', str(a.helpers),
                    '--step', str(step), '--step-sha256', digest(step),
                    '--probes', str(probes), '--probes-sha256', digest(probes),
                    '--output', str(report)], check=True)
    data = json.loads(report.read_text())
    first, second = data['records_private']
    if first['status'] != 'resolved_inside' or abs(first['cad_ray_scan_units']-1.) > 1e-8:
        raise AssertionError('unit wall not recovered')
    if first['faces_share_edge']:
        raise AssertionError('opposing box faces incorrectly adjacent')
    if second['status'] == 'resolved_inside':
        raise AssertionError('outward ray incorrectly accepted')
    print('PASS: exact unit wall, opposing faces, outward-ray rejection')


if __name__ == '__main__':
    main()
