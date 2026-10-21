"""One bounded native construction; retain raw law and geometry before verdicts."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

MASTER = '24af058467fd82a9f0c1d391bf947d427dffd311371cf8f73dafa492d204f4fd'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    require(not out.exists(), 'A fresh output directory is required')
    out.mkdir(parents=True)
    began = time.monotonic()
    report = dict(status='incomplete', Compute_call_count=0,
                  candidate_adopted=False, downstream_checks='pending',
                  declaration='One R1 point-radius construction with complete R0 terminal source edges')
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(
        TimeoutError('Original 150 second inner limit')))
    signal.alarm(150)
    resource.setrlimit(resource.RLIMIT_CPU, (140, 141))
    try:
        require(os.getpriority(os.PRIO_PROCESS, 0) == 10 and
                all(os.environ.get(k) == '1' for k in
                    ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']),
                'Original nice10 and one-thread limits are required')
        old = root / 'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-law-API-observer-preparation-001'
        p = json.loads((old / 'plan.json').read_text())
        master = root / p['master_BREP']
        require(sha(master) == MASTER, 'Current master identity differs')
        sys.path.insert(0, str(root / p['native_site']))
        observer = load('_resume_reference_reader', old / 'observe.py')
        fragment = load('_resume_point_radius_fragment', root /
                        'work/carrier-current24af-point-radius-construction-SOURCE-001/construction_fragment.py')
        maths = load('_resume_exact_law', Path(__file__).with_name('law_certificate.py'))
        from build123d import import_brep, export_brep, Solid
        from OCP.ChFi3d import ChFi3d_FilBuilder
        from OCP.OSD import OSD_ThreadPool
        from OCP.BRep import BRep_Tool
        OSD_ThreadPool.DefaultPool_s().Init(1)
        _, nearest = observer.closed_observation(p)
        prior = observer.closed_add_observer(p)
        body = import_brep(master)
        require(body.is_valid and len(body.solids()) == 1, 'Invalid baseline')
        faces, edges, graph = observer.SELECT.topology(body)
        write(out / 'baseline-topology.json', graph)
        selection = {}
        normals = load('_resume_original_normals', root / p['boundary_normal_source'])
        try:
            paths = observer.SELECT.select(body, faces, edges, graph, normals,
                                           selection, nearest, prior)
        finally:
            write(out / 'fresh-selection.json', selection)
        builder = ChFi3d_FilBuilder(body.solids()[0].wrapped)
        report['contours'] = []
        for path in paths:
            row = dict(source_selected_path=path)
            report['contours'].append(row)
            fragment.initialise_one_contour(builder, edges[path[1]].wrapped,
                                            path, edges, row)
            # Serialize the actual evaluator and coefficients before assertions.
            write(out / 'configured-contours.json', report['contours'])
            require('configuration_refusal' not in row, 'Contour/domain refused')
            raw = row['standalone_interpolation_before_any_assertion']
            require('unresolved' not in raw, 'Standalone law readback unresolved')
            row['exact_standalone_certificate'] = maths.certify(raw['curve'])
            write(out / 'configured-contours.json', report['contours'])
            require(row['exact_standalone_certificate']['passed'],
                    'Actual standalone coefficients do not prove the declared law')
        # Separate design: reserve the complete two terminal source edges at R0.
        # This changes the radius design, not the retained original trial verdict.
        report['zero_terminal_edges'] = []
        for ci, path in enumerate(paths, 1):
            spine = builder.Value(ci)
            for edge_index in (path[0], path[-1]):
                builder.SetRadius(0.0, ci, edges[edge_index].wrapped)
            row = dict(contour=ci, source_edges=[path[0], path[-1]],
                       standalone_whole_contour_certificate_superseded=True,
                       actual_constant_edges=[])
            report['zero_terminal_edges'].append(row)
            for j in range(1, spine.NbEdges() + 1):
                constant = bool(spine.IsConstant(j))
                row['actual_constant_edges'].append(dict(
                    edge=path[j - 1], constant=constant,
                    radius_mm=spine.Radius(j) if constant else None))
            write(out / 'zero-terminal-edges.json', report['zero_terminal_edges'])
            require(all(row['actual_constant_edges'][j]['constant'] and
                        row['actual_constant_edges'][j]['radius_mm'] == 0.0
                        for j in (0, -1)), 'Terminal edge R0 assignment differs')
        report['Compute_call_count'] = 1
        write(out / 'before-compute.json', report)
        try:
            builder.Compute()
        finally:
            report['native_state'] = dict(
                IsDone=bool(builder.IsDone()), HasResult=bool(builder.HasResult()),
                NbFaultyContours=builder.NbFaultyContours(),
                NbFaultyVertices=builder.NbFaultyVertices(),
                StripeStatus=[str(builder.StripeStatus(i))
                              for i in range(1, builder.NbElements() + 1)])
            report['fault_vertices'] = []
            for i in range(1, builder.NbFaultyVertices() + 1):
                row = dict(index=i)
                report['fault_vertices'].append(row)
                try:
                    row['xyz_mm'] = list(BRep_Tool.Pnt_s(builder.FaultyVertex(i)).Coord())
                except Exception as error:
                    row['unresolved'] = dict(type=type(error).__name__, message=str(error))
            report['consumed_laws'] = []
            for ci, path in enumerate(paths, 1):
                for ei in path:
                    row = dict(contour=ci, source_edge=ei)
                    report['consumed_laws'].append(row)
                    try:
                        law = builder.GetLaw(ci, edges[ei].wrapped)
                        row['raw'] = fragment.raw_law(law)
                        row['available_methods'] = [n for n in dir(law) if not n.startswith('_')]
                    except Exception as error:
                        row['unresolved'] = dict(type=type(error).__name__, message=str(error))
            write(out / 'after-compute.json', report)
        if builder.IsDone():
            candidate = Solid(builder.Shape())
            export_brep(candidate, out / 'unqualified-candidate.brep')
            box = candidate.bounding_box()
            report['candidate'] = dict(sha256=sha(out / 'unqualified-candidate.brep'),
                                     valid=candidate.is_valid,
                                     solid_count=len(candidate.solids()),
                                     volume_mm3=candidate.volume,
                                     mass_kg=candidate.volume * 4420e-9,
                                     bounds_mm=[list(box.min), list(box.max)])
            report['status'] = 'constructed_unqualified_candidate'
        else:
            if builder.HasResult():
                from build123d import Shape
                export_brep(Shape.cast(builder.BadShape()), out / 'raw-bad-shape.brep')
            report['status'] = 'native_construction_refused'
    except Exception as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error),
                                 traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        report['elapsed_seconds'] = time.monotonic() - began
        write(out / 'assessment.json', report)
    print(json.dumps(dict(status=report['status'],
                          Compute_call_count=report['Compute_call_count'],
                          assessment_sha256=sha(out / 'assessment.json'))))
    return 0 if report['status'] in ('constructed_unqualified_candidate',
                                    'native_construction_refused') else 1


if __name__ == '__main__':
    raise SystemExit(main())
