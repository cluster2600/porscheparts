"""G1 4 soupapes / 2 bougies : provenance, itération, contrôles 720°, CAO et manifeste.

Usage : python run.py <out_dir> [--no-cad] [--external-dir DIR]
Jamais géométrie maître, jamais autorisation de fabrication.
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import numpy as np  # noqa: E402

import checks as chk  # noqa: E402
import iterate as it  # noqa: E402
import provenance as pv  # noqa: E402
from layout import DERIVED, derive  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolved_table(spec, base, traces, p, design, best_trial):
    rows = {}
    for name, item in spec['parameters'].items():
        row = {'value': round(float(p[name]), 4), 'unit': item.get('unit'), 'provenance': item['provenance']}
        if item['provenance'] == 'derived':
            row.update(formula=item['formula'], inputs=item['inputs'])
        else:
            row['trace'] = traces[name]
        if name in design:
            original = derive(base)[name]
            row = {'value': round(float(design[name]), 4), 'unit': item.get('unit'), 'provenance': 'derived_by_iteration',
                   'trial': best_trial, 'replaces_provenance': item['provenance'], 'start_value': round(float(original), 4)}
        rows[name] = row
    return rows


def run(out_dir, cad=True, external_dir=None, space=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    spec = pv.load_spec()
    space = space or pv.load_design_space()
    base, traces = pv.resolve_base(spec)
    search = it.Search(spec, space, base)
    best = search.run()
    design = it.mirror(best['design'], space)
    p = derive(base, design)
    step = space['budget']['final_sweep_step_deg']
    base_checks, base_summary = chk.evaluate(derive(base), step, force_cycle=True)
    final_checks, final_summary = chk.evaluate(p, step, force_cycle=True)
    table = resolved_table(spec, base, traces, p, design, best['trial'])
    counts = {k: 0 for k in pv.PROVENANCES}
    for row in table.values():
        counts[row['provenance']] += 1
    (out / 'parameters-resolved.json').write_text(json.dumps(table, ensure_ascii=False, indent=1) + '\n')
    (out / 'checks.json').write_text(json.dumps({
        'start_935': {'summary': base_summary, 'checks': base_checks},
        'best': {'trial': best['trial'], 'summary': final_summary, 'checks': final_checks},
    }, ensure_ascii=False, indent=1) + '\n')
    (out / 'iteration-history.json').write_text(json.dumps({
        'seed': space['seed'], 'budget': space['budget'], 'plug_mode': space['plug_mode'],
        'trials': search.history, 'front': it.pareto_front(search.history)}, ensure_ascii=False, separators=(',', ':')) + '\n')
    accepted = final_summary['accepted']
    cad_result = None
    if cad:
        import assembly
        cad_result = assembly.export_all(p, out, final_checks, 0.0, external_dir)
        brep_ok = cad_result['all_brep_valid'] and cad_result['head_solid_count'] == 1 and \
            all(r['passed'] for r in cad_result['brep_cross_check'])
        accepted = accepted and brep_ok
    inputs = sorted(Path(HERE / 'params').glob('*.json'))
    manifest = {
        'schema_version': 1,
        'artifact': 'm64_g1_four_valve_twin_plug_assembly',
        'master_geometry': False,
        'manufacturing_authorized': False,
        'geometry_origin': 'synthétique paramétrique ; aucun maillage de scan importé',
        'accepted': accepted,
        'provenance_counts': counts,
        'iteration': {'trials': len(search.history), 'accepted_trials': sum(r['accepted'] for r in search.history),
                      'best_trial': best['trial'], 'best_stage': best['stage'], 'design_variables': best['design'],
                      'sourced_values_modified': sorted(k for k in design if spec['parameters'][k]['provenance'] in pv.SOURCED
                                                        and spec['parameters'][k]['provenance'] != 'candidate_935_scan_C')},
        'bore': {'diameter': p['bore_diameter'], 'band': it.bore_band(p['bore_diameter'], space),
                 'displacement_cc_6_cyl': round(chk.displacement_cc(p['bore_diameter'], p['crank_stroke']), 1)},
        'start_935_summary': base_summary,
        'final_summary': final_summary,
        'cad': cad_result,
        'environment': {'python': platform.python_version(), 'numpy': np.__version__},
        'sha256': {
            'inputs': {str(f.relative_to(pv.REPO)): sha(f) for f in inputs},
            'sources': {k: sha(pv.REPO / v) for k, v in pv.SOURCES.items()},
            'generators': {f.name: sha(f) for f in sorted(list(HERE.glob('*.py')) + list((HERE / 'cad').glob('*.py')))},
            'outputs': {n: sha(out / n) for n in ('parameters-resolved.json', 'checks.json', 'iteration-history.json')},
        },
        'derived_parameters': list(DERIVED),
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n')
    return manifest


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out_dir')
    ap.add_argument('--no-cad', action='store_true')
    ap.add_argument('--external-dir')
    args = ap.parse_args()
    m = run(args.out_dir, cad=not args.no_cad, external_dir=args.external_dir)
    print(json.dumps({k: m[k] for k in ('accepted', 'provenance_counts', 'final_summary')}, ensure_ascii=False))
    sys.exit(0 if m['accepted'] else 2)
