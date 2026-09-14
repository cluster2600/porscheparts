#!/usr/bin/env python3
"""Profileur borné du contrôle natif d'un candidat de congé M64.

Chaque phase du contrôle de ``build_local_port_junction_fillet.run`` est
rejouée seule dans un sous-processus avec délai externe et limite CPU, sans
réseau. Une phase qui dépasse son délai est notée ``timeout`` : le verdict
global devient alors ``incomplete`` (fail-closed), jamais ``pass``.

Aucune géométrie n'est modifiée ; le contour maître n'est ni lu ni écrit ici.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))

SCHEMA = 'm64-strict-check-profile/v1'
BOP_OPTIONS = ('SelfInterMode', 'SmallEdgeMode', 'RebuildFaceMode',
               'ContinuityMode', 'CurveOnSurfaceMode')
# Phases rejouant le contrôle actuel (ordre de run()) puis variantes mesurées.
PHASES = (
    'read', 'brepcheck_exact', 'brepcheck_default', 'tolerances',
    'bop_full', *('bop_only_' + o for o in BOP_OPTIONS), 'bop_none',
    'write_reread', 'bbox_optimal', 'volume_adaptive_1e-11',
    'volume_adaptive_1e-9', 'volume_gauss_default',
)
DEFAULT_TIMEOUT = 300.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_shape(path):
    path = Path(path)
    from OCP.TopoDS import TopoDS_Shape
    if path.suffix.lower() in ('.step', '.stp'):
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        reader = STEPControl_Reader()
        if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
            raise ValueError('STEP read failed')
        return reader.OneShape()
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
        raise ValueError('native BRep read failed')
    return shape


def indexed(shape, kind):
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    m = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(shape, kind, m); return m


def bop(shape, options):
    """Même analyseur que ports.bop_check, avec options explicites."""
    from collections import Counter
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    checker = BOPAlgo_ArgumentAnalyzer(); checker.SetShape1(shape)
    for name in BOP_OPTIONS:
        setattr(checker, name, name in options)
    checker.Perform()
    counts = Counter(str(r.GetCheckStatus()).split('.')[-1] for r in checker.GetCheckResult())
    return {'has_faulty': bool(checker.HasFaulty()), 'fault_counts': dict(counts),
            'options': sorted(options)}


def brepcheck(shape, exact):
    """exact=True reproduit design.CAD.valid (SetExactMethod(True))."""
    from OCP.BRepCheck import BRepCheck_Analyzer
    analyzer = BRepCheck_Analyzer(shape, True)
    analyzer.SetExactMethod(bool(exact))
    analyzer.Init(shape, True)
    return {'valid': bool(analyzer.IsValid()), 'exact_method': bool(exact)}


def volume(shape, eps):
    """Volume GProp total, puis par solide (signe = orientation)."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopoDS import TopoDS

    def one(s):
        props = GProp_GProps()
        if eps is None:
            BRepGProp.VolumeProperties_s(s, props, False, False, False)
            return props.Mass(), None
        err = BRepGProp.VolumeProperties_s(s, props, eps, True, False)
        return props.Mass(), err
    total, err = one(shape)
    solids = indexed(shape, TopAbs_SOLID)
    per = []
    for i in range(1, solids.Extent()+1):
        s = TopoDS.Solid_s(solids.FindKey(i)); v, e = one(s)
        per.append({'volume': v, 'error_estimate': e, 'orientation': str(s.Orientation()).split('.')[-1]})
    return {'volume': total, 'error_estimate': err, 'eps': eps, 'solids': per}


def tolerances(shape):
    from OCP.BRep import BRep_Tool
    from OCP.ShapeAnalysis import ShapeAnalysis_ShapeTolerance
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopoDS import TopoDS
    out = {'solids': indexed(shape, TopAbs_SOLID).Extent(), 'shells': indexed(shape, TopAbs_SHELL).Extent()}
    sat = ShapeAnalysis_ShapeTolerance()
    for name, kind, cast in (('faces', TopAbs_FACE, TopoDS.Face_s), ('edges', TopAbs_EDGE, TopoDS.Edge_s),
                             ('vertices', TopAbs_VERTEX, TopoDS.Vertex_s)):
        m = indexed(shape, kind)
        vals = [BRep_Tool.Tolerance_s(cast(m.FindKey(i))) for i in range(1, m.Extent()+1)]
        out[name] = {'count': len(vals), 'tolerance_min': min(vals) if vals else None,
                     'tolerance_max': max(vals) if vals else None,
                     'shape_analysis_max': sat.Tolerance(shape, 1, kind)}
    return out


def run_phase(phase, shape_path, scratch):
    """Exécute une phase dans le processus courant ; retourne un dict JSON."""
    t0 = time.monotonic(); shape = read_shape(shape_path); t_read = time.monotonic()-t0
    t1 = time.monotonic()
    if phase == 'read':
        result = {'null': shape.IsNull()}
    elif phase == 'brepcheck_exact':
        result = brepcheck(shape, True)
    elif phase == 'brepcheck_default':
        result = brepcheck(shape, False)
    elif phase == 'tolerances':
        result = tolerances(shape)
    elif phase == 'bop_full':
        result = bop(shape, set(BOP_OPTIONS))
    elif phase.startswith('bop_only_'):
        result = bop(shape, {phase[len('bop_only_'):]})
    elif phase == 'bop_none':
        result = bop(shape, set())
    elif phase == 'write_reread':
        from OCP.BRepTools import BRepTools
        target = Path(scratch)/('reread-' + str(os.getpid()) + '.brep')
        if not BRepTools.Write_s(shape, str(target)):
            raise ValueError('native BRep write failed')
        again = read_shape(target)
        result = {'reread_sha256': sha(target), 'reread_null': again.IsNull(),
                  'reread_volume_adaptive_1e-11': volume(again, 1e-11)['volume']}
        target.unlink()
    elif phase == 'bbox_optimal':
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib
        box = Bnd_Box(); BRepBndLib.AddOptimal_s(shape, box, False, False); result = {'bbox': list(box.Get())}
    elif phase == 'volume_adaptive_1e-11':
        result = volume(shape, 1e-11)
    elif phase == 'volume_adaptive_1e-9':
        result = volume(shape, 1e-9)
    elif phase == 'volume_gauss_default':
        result = volume(shape, None)
    else:
        raise ValueError('unknown phase')
    return {'read_seconds': t_read, 'phase_seconds': time.monotonic()-t1, 'result': result}


def supervise(shape_path, phases, timeout, scratch):
    """Chaque phase dans un sous-processus isolé ; délai externe par phase."""
    rows = {}
    for phase in phases:
        cmd = [sys.executable, str(Path(__file__).resolve()), '--worker', phase,
               '--shape', str(shape_path), '--scratch', str(scratch), '--cpu-limit', str(int(math.ceil(timeout))+5)]
        env = {k: v for k, v in os.environ.items() if not k.lower().endswith('_proxy')}
        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            rows[phase] = {'status': 'timeout', 'wall_seconds': time.monotonic()-t0, 'timeout_seconds': timeout}
            continue
        wall = time.monotonic()-t0
        if proc.returncode != 0:
            rows[phase] = {'status': 'error', 'returncode': proc.returncode, 'wall_seconds': wall,
                           'stderr_tail': proc.stderr[-800:]}
            continue
        row = json.loads(proc.stdout.strip().splitlines()[-1])
        row.update(status='done', wall_seconds=wall); rows[phase] = row
    return rows


def verdict(rows):
    """Verdict du contrôle actuel : exact BRepCheck + BOP complet + solide unique."""
    need = ('brepcheck_exact', 'bop_full', 'tolerances')
    if any(rows.get(p, {}).get('status') != 'done' for p in need):
        return 'incomplete'
    ok = (rows['brepcheck_exact']['result']['valid'] and not rows['bop_full']['result']['has_faulty']
          and rows['tolerances']['result']['solids'] == 1)
    return 'pass' if ok else 'fail'


def fast_verdict(rows, fast_brepcheck='brepcheck_default', fast_bop='bop_full'):
    need = (fast_brepcheck, fast_bop, 'tolerances')
    if any(rows.get(p, {}).get('status') != 'done' for p in need):
        return 'incomplete'
    ok = (rows[fast_brepcheck]['result']['valid'] and not rows[fast_bop]['result']['has_faulty']
          and rows['tolerances']['result']['solids'] == 1)
    return 'pass' if ok else 'fail'


def reconcile(labelled):
    """Réconciliation volumique entre profils (source, candidat, relu)."""
    out = {}
    for label, rows in labelled.items():
        vol = rows.get('volume_adaptive_1e-11', {})
        rr = rows.get('write_reread', {})
        out[label] = {
            'volume_adaptive_1e-11': vol.get('result', {}).get('volume'),
            'error_estimate': vol.get('result', {}).get('error_estimate'),
            'per_solid': vol.get('result', {}).get('solids'),
            'volume_gauss_default': rows.get('volume_gauss_default', {}).get('result', {}).get('volume'),
            'reread_volume_adaptive_1e-11': rr.get('result', {}).get('reread_volume_adaptive_1e-11'),
        }
        v, r = out[label]['volume_adaptive_1e-11'], out[label]['reread_volume_adaptive_1e-11']
        out[label]['reread_minus_in_memory'] = (r-v) if v is not None and r is not None else None
        solids = out[label]['per_solid'] or []
        out[label]['negative_solid_volumes'] = sum(1 for s in solids if s['volume'] < 0)
    if 'source' in out:
        base = out['source']['volume_adaptive_1e-11']
        for label, row in out.items():
            v = row['volume_adaptive_1e-11']
            row['minus_source'] = (v-base) if v is not None and base is not None else None
    return out


def synthetic_witness(scratch, radius, nurbs=False):
    """Témoin public du test existant : cylindre de branche fusionné au tronc.

    nurbs=True convertit la branche en B-spline avant fusion : le congé ne
    peut plus être analytique et les paramètres d'approximation stricts
    agissent réellement (le témoin analytique les rend sans effet).
    """
    import build_local_port_junction_fillet as local
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    cad = local.ports.design.CAD()
    branch = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, -10, 0), gp_Dir(0, 1, 0)), 5, 12).Shape()
    if nurbs:
        branch = BRepBuilderAPI_NurbsConvert(branch, True).Shape()
    trunk = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), 10, 10).Shape()
    source = BRepAlgoAPI_Fuse(branch, trunk).Shape()
    paths = {'source': Path(scratch)/'witness-source.brep'}
    BRepTools.Write_s(source, str(paths['source']))
    edges = [e for _, e, _ in local.branch_cap_edges(cad, source, {'center': [0, 0, 0], 'radius': 10})]
    builds = {}
    for mode in local.CONSTRUCTION_MODES:
        t0 = time.monotonic(); maker, build = local.build_fillet(source, edges, radius, mode)
        build['build_seconds'] = time.monotonic()-t0; builds[mode] = build
        if build['done']:
            p = Path(scratch)/('witness-' + mode + '.brep'); BRepTools.Write_s(maker.Shape(), str(p)); paths[mode] = p
    return paths, builds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=PHASES)
    parser.add_argument('--shape', type=Path, action='append', default=[],
                        help='label=chemin (.brep/.step) ; répéter. Libellés source/candidat pour la réconciliation')
    parser.add_argument('--synthetic-radius', type=float, help='génère le témoin synthétique (default + strict)')
    parser.add_argument('--synthetic-nurbs', action='store_true', help='branche du témoin convertie en B-spline')
    parser.add_argument('--phases', default=','.join(PHASES))
    parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument('--scratch', type=Path)
    parser.add_argument('--cpu-limit', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.worker:
        if args.cpu_limit:
            resource.setrlimit(resource.RLIMIT_CPU, (args.cpu_limit, args.cpu_limit+5))
        print(json.dumps(run_phase(args.worker, args.shape[0], args.scratch)), flush=True)
        return 0
    if args.scratch is None or args.output is None:
        parser.error('--scratch et --output requis')
    if args.output.exists():
        raise FileExistsError(args.output)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('délai positif fini requis')
    phases = [p for p in args.phases.split(',') if p]
    if any(p not in PHASES for p in phases):
        parser.error('phase inconnue')
    args.scratch.mkdir(parents=True, exist_ok=True)
    report = {'schema': SCHEMA, 'timeout_seconds_per_phase': args.timeout, 'phases': phases,
              'master_modified': False, 'promoted': False, 'network_used': False}
    shapes = {}
    for item in args.shape:
        label, _, path = str(item).partition('=')
        if not path:
            parser.error('--shape label=chemin requis')
        shapes[label] = Path(path)
    if args.synthetic_radius is not None:
        paths, builds = synthetic_witness(args.scratch, args.synthetic_radius, args.synthetic_nurbs)
        report['synthetic_builds'] = builds; shapes.update(paths)
    report['inputs_sha256'] = {k: sha(p) for k, p in shapes.items()}
    t0 = time.monotonic()
    report['profiles'] = {k: supervise(p, phases, args.timeout, args.scratch) for k, p in shapes.items()}
    report['verdicts'] = {k: {'current_exact': verdict(r), 'proposed_default_brepcheck': fast_verdict(r)}
                          for k, r in report['profiles'].items()}
    report['volume_reconciliation'] = reconcile(report['profiles'])
    report['wall_seconds'] = time.monotonic()-t0
    report['inputs_unchanged'] = all(sha(p) == report['inputs_sha256'][k] for k, p in shapes.items())
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True))
    slow = {k: max(((p, r.get('wall_seconds', 0)) for p, r in rows.items()), key=lambda x: x[1])
            for k, rows in report['profiles'].items()}
    print(json.dumps({'verdicts': report['verdicts'], 'slowest_phase': slow}), flush=True)
    return 0 if report['inputs_unchanged'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
