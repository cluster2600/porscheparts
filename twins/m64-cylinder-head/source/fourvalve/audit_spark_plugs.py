#!/usr/bin/env python3
"""Audit opt-in des bougies candidates sur la G2 figée ; aucune autorisation de fabrication.

Usage : audit_spark_plugs.py PARAMETERS_RESOLVED.json NEW_OUTPUT_DIRECTORY
Les STEP complets dépassant la limite du dépôt ne sont pas publiés ; le générateur reste la source.
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import assembly
import cadquery as cq
import checks
import components as comp
import layout
import numpy as np
import provenance


def audit(parameters, out):
    out.mkdir(parents=True, exist_ok=False)
    extra = HERE / 'params-plugs/spark_plug_envelope.json'
    p = {k: row['value'] for k, row in json.loads(parameters.read_text()).items()}
    candidate = json.loads(extra.read_text())
    for name, row in candidate['parameters'].items():
        provenance.verify_provenance(name, row, {})  # hypothèses, pas des cotes M64
        p[name] = row['value']
    head = comp.head(p)
    plugs = [comp.spark_plug(p, k) for k in layout.PLUGS]
    # Réutiliser les mêmes solides rend le balayage de fenêtre moins coûteux et déterministe.
    with patch.object(comp, 'head', return_value=head):
        measurements = [dict(top_margin_above_carrier_mm=m, **assembly.compression_ratio(p, m))
                        for m in (2.0, 5.0, 10.0)]
        real_plug = comp.spark_plug
        def missing_second(p, k):
            s = real_plug(p, k)
            return s.translate((200, 0, 0)) if k == 2 else s
        with patch.object(comp, 'spark_plug', side_effect=missing_second):
            missing = assembly.compression_ratio(p)
    final_checks, summary = checks.evaluate(p, 0.5, force_cycle=True)
    o, d = layout.plug_opening(p, 1)
    normal = cq.Vector(float(d[2]), 0, -float(d[0]))
    plane = cq.Plane(origin=cq.Vector(*o), normal=normal)
    half = cq.Workplane(plane).rect(1000, 1000).extrude(1000).val()
    sliced = [s.cut(half) for s in [head, comp.piston(p, 0), *plugs]]
    cq.exporters.export(cq.Workplane().add(cq.Compound.makeCompound(sliced)), str(out / 'plug-section.svg'),
                        opt={'projectionDir': normal.toTuple(), 'showHidden': False,
                             'width': 1100, 'height': 700, 'strokeWidth': 0.6})
    assembly._export(plugs, out / 'spark-plug-envelopes.step')
    raw_cc = checks.chamber_volume_mm3(p) / 1000
    volumes = [r['clearance_volume_cc'] for r in measurements]
    all_measured = all(v is not None for v in volumes)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {
        'artifact': 'm64_g2_spark_plug_packaging_audit', 'manufacturing_authorized': False,
        'status': 'candidate_packaging_only_not_released', 'outer_shape_changed': False,
        'geometry_changes': ['two_stepped_socket_wells', 'two_solid_spark_plug_envelopes'],
        'head_valid': assembly.brep_valid(head), 'head_solids': len(head.Solids()), 'head_faces': len(head.Faces()),
        'plugs_valid': [assembly.brep_valid(s) and len(s.Solids()) == 1 for s in plugs],
        'plug_head_intersection_mm3': [s.intersect(head).Volume() for s in plugs],
        'plug_piston_tdc_distance_mm': [assembly.brep_distance(s, comp.piston(p, 0)) for s in plugs],
        'compression_window_sweep': measurements, 'missing_second_plug_negative_control': missing,
        'window_spread_cc': max(volumes) - min(volumes) if all_measured else None,
        'uncalibrated_numpy_proxy_cc': raw_cc,
        'proxy_relative_difference_percent': 100 * (raw_cc / volumes[0] - 1) if all_measured else None,
        'hypothesis_band': [p['compression_ratio_min'], p['compression_ratio_max']],
        'geometry_checks': final_checks, 'geometry_summary': summary,
        'limitations': ['candidate dimensions not qualified for M64', 'ideal sealed threaded envelope',
                        'no thread or plug nose crevice volume', 'no ring-pack crevice volume',
                        'simplified intersecting valve and seat solids, not physical contact',
                        'no hot clearance, thermal, combustion, endurance or printing validation'],
        'parameters_sha256': digest(parameters), 'candidate_parameters_sha256': digest(extra),
        'source_sha256': {str(f.relative_to(HERE)): digest(f) for f in
                         sorted(list(HERE.glob('*.py')) + list((HERE / 'cad').glob('*.py')))},
        'files_sha256': {f.name: digest(f) for f in sorted(out.iterdir())},
        'environment': {'python': platform.python_version(), 'cadquery': cq.__version__, 'numpy': np.__version__},
    }
    (out / 'audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'measurements': measurements, 'geometry': summary, 'missing_plug': missing}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.parameters, args.output)
