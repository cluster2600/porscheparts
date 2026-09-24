#!/usr/bin/env python3
"""Rejoue le défaut de volume G2 et publie le résultat du calcul corrigé, sans modifier la CAO.

Usage : audit_compression.py PARAMETERS_RESOLVED.json NEW_OUTPUT_DIRECTORY
La formule historique sert uniquement à démontrer sa dépendance à la fenêtre de mesure.
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import assembly
import cadquery as cq
import components as comp
import kinematics as kin
import numpy as np


def audit(parameters, out):
    out.mkdir(parents=True, exist_ok=False)
    p = {k: row['value'] for k, row in json.loads(parameters.read_text()).items()}
    head = comp.head(p)
    solids = [head, comp.piston(p, 0)]
    for side, sy in (('intake', 1), ('intake', -1), ('exhaust', 1), ('exhaust', -1)):
        solids.extend([comp.valve(p, side, sy), comp.seat_insert(p, side, sy)])
    crown = float(kin.piston_crown_z(p, np.array([0]))[0])
    R = p['bore_diameter'] / 2
    rows = []
    for margin in (2.0, 5.0, 10.0):
        z0, z1 = crown - p['piston_bowl_depth'], p['roof_ridge_height'] + margin
        probe = cq.Solid.makeCylinder(R, z1 - z0, cq.Vector(0, 0, z0))
        legacy = probe.Volume() - sum(probe.intersect(s).Volume() for s in solids)
        void = probe.cut(*solids)
        selected = [s for s in void.Solids() if s.isInside(cq.Vector(0, 0, crown + 0.5), 1e-7)]
        row = {'top_margin_mm': margin, 'legacy_all_voids_cc': legacy / 1000,
               'legacy_ratio_not_accepted': 1 + np.pi * R**2 * p['crank_stroke'] / legacy,
               'boolean_void_cc': void.Volume() / 1000, 'boolean_valid': assembly.brep_valid(void),
               'void_components': len(void.Solids()),
               'connected_chamber_cc_diagnostic_only': selected[0].Volume() / 1000 if len(selected) == 1 else None}
        rows.append(row)
        print(json.dumps(row), flush=True)
    corrected = assembly.compression_ratio(p)
    # Coupe produite par le noyau CAO, pas une image générative.
    half = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, 0, -500))
    section = out / 'head-section.svg'
    cq.exporters.export(cq.Workplane().add(head.cut(half)), str(section),
                        opt={'projectionDir': (0, 1, 0), 'showHidden': False})
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {'artifact': 'm64_g2_compression_audit', 'manufacturing_authorized': False,
              'geometry_modified': False, 'head_valid': assembly.brep_valid(head),
              'head_solids': len(head.Solids()), 'head_faces': len(head.Faces()),
              'legacy_measurement_sensitivity': rows, 'corrected_measurement': corrected,
              'parameters_sha256': digest(parameters),
              'source_sha256': {str(f.relative_to(HERE)): digest(f) for f in
                               sorted(list(HERE.glob('*.py')) + list((HERE / 'cad').glob('*.py')))},
              'section_sha256': digest(section),
              'environment': {'python': platform.python_version(), 'cadquery': cq.__version__,
                              'numpy': np.__version__}}
    (out / 'audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(corrected), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('parameters', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    audit(args.parameters, args.output)
