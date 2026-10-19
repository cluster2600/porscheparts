"""One bounded, opt-in OCP reference tessellation; no CAD imports at module load."""
import argparse
import ast
from collections import defaultdict, deque
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def sha(path, deadline=None):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError('Integrity verification exceeded the global deadline')
            h.update(block)
    return h.hexdigest()


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def verify(plan, deadline=None):
    for name, digest in plan['files_sha256'].items():
        if sha(name, deadline) != digest:
            raise ValueError('Pinned input or runtime changed: ' + name)
    if plan['parameters'] != dict(linear_deflection_mm=.01, is_relative=False,
                                 angular_deflection_rad=.10, in_parallel=False):
        raise ValueError('Unexpected meshing parameters')
    criterion = plan['criterion']
    actual = json.loads(Path(criterion['path']).read_text())
    if actual[criterion['field']] != .01:
        raise ValueError('The declared interface criterion differs')
    tree = ast.parse(Path(plan['angular_setting_source']).read_text())
    settings = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == 'export_stl']
    if len(settings) != 1 or {kw.arg: ast.literal_eval(kw.value) for kw in settings[0].keywords}.get('angular_tolerance') != .10:
        raise ValueError('The inherited CAD angular setting differs')
    if plan['resources'] != dict(global_wall_seconds=300, child_wall_seconds_max=260,
                                child_CPU_seconds=260, cleanup_reserve_seconds=30,
                                threads=1, nice=10):
        raise ValueError('Unexpected bounded execution resources')


def add_face(nodes, triangles, reversed_face, vertices, faces, lookup):
    """Copy binary64 coordinates; identify only bit-identical existing XYZ."""
    if type(reversed_face) is not bool or not nodes or not triangles:
        raise ValueError('Every CAD face needs nodes, triangles and a known orientation')
    ids = []
    for point in nodes:
        if len(point) != 3 or any(type(c) is not float or not math.isfinite(c) for c in point):
            raise ValueError('Finite binary64 XYZ nodes required')
        key = struct.pack('<ddd', *point)
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(tuple(point))
        ids.append(lookup[key])
    for row in triangles:
        if len(row) != 3 or any(type(i) is not int or not 1 <= i <= len(nodes) for i in row):
            raise ValueError('Invalid one-based OCP triangle')
        a, b, c = (ids[i - 1] for i in row)
        faces.append((a, c, b) if reversed_face else (a, b, c))


def validate_surface(vertices, faces):
    """Exact dyadic zero-area/volume and indexed closed oriented surface checks."""
    if not vertices or not faces:
        raise ValueError('An empty reference is not permitted')
    ratios = [[c.as_integer_ratio() for c in p] for p in vertices]
    denominator = max(d for row in ratios for _, d in row)
    xyz = [tuple(n * (denominator // d) for n, d in row) for row in ratios]
    edges, adjacent, used = defaultdict(list), [set() for _ in faces], set()
    volume6 = 0
    for fid, row in enumerate(faces):
        if (len(row) != 3 or any(type(i) is not int or not 0 <= i < len(xyz) for i in row)
                or len(set(row)) != 3):
            raise ValueError('Invalid or repeated triangle vertex index')
        a, b, c = (xyz[i] for i in row)
        u = tuple(b[i] - a[i] for i in range(3))
        v = tuple(c[i] - a[i] for i in range(3))
        cross = (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
        if cross == (0, 0, 0):
            raise ValueError('An exactly zero-area triangle is not permitted')
        volume6 += (a[0]*(b[1]*c[2]-b[2]*c[1]) +
                    a[1]*(b[2]*c[0]-b[0]*c[2]) + a[2]*(b[0]*c[1]-b[1]*c[0]))
        used.update(row)
        for x, y in zip(row, row[1:] + row[:1]):
            edges[min(x, y), max(x, y)].append((fid, 1 if x < y else -1))
    boundary = sum(len(e) == 1 for e in edges.values())
    nonmanifold = sum(len(e) > 2 for e in edges.values())
    inconsistent = sum(len(e) == 2 and e[0][1] == e[1][1] for e in edges.values())
    if boundary or nonmanifold or inconsistent:
        raise ValueError('Exact XYZ indexing is not closed/manifold/oriented: ' +
                         str(dict(boundary=boundary, nonmanifold=nonmanifold, inconsistent=inconsistent)))
    for entries in edges.values():
        a, b = entries[0][0], entries[1][0]
        adjacent[a].add(b)
        adjacent[b].add(a)
    visited, todo = {0}, deque([0])
    while todo:
        for fid in adjacent[todo.popleft()]:
            if fid not in visited:
                visited.add(fid)
                todo.append(fid)
    if len(visited) != len(faces) or len(used) != len(vertices) or volume6 <= 0:
        raise ValueError('One complete outward oriented positive-volume surface is required')
    return dict(vertices=len(vertices), triangles=len(faces), boundary_edges=boundary,
                nonmanifold_edges=nonmanifold, inconsistent_orientation_edges=inconsistent,
                zero_area_triangles=0, face_connected_components=1,
                exact_signed_volume_mm3=str(Fraction(volume6, 6*denominator**3)),
                exact_coordinate_identification='IEEE binary64 bits; no tolerance weld',
                self_intersections_checked=False)


def worker(plan, output):
    # These are the only CAD/native imports; selfchecks never call this function.
    import numpy as np
    from OCP.BRep import BRep_Tool
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_FACE, TopAbs_FORWARD, TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    reader = STEPControl_Reader()
    if reader.ReadFile(plan['STEP']) != IFSelect_RetDone:
        raise ValueError('The retained STEP could not be read')
    reader.SetSystemLengthUnit(1.0)  # OCCT length scale is millimetres.
    if reader.SystemLengthUnit() != 1.0 or reader.TransferRoots() != reader.NbRootsForTransfer():
        raise ValueError('Incomplete STEP transfer or an unexpected system length unit')
    shape = reader.OneShape()
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError('One valid retained CAD shape is required')
    def shapes(kind):
        exp, result = TopExp_Explorer(shape, kind), []
        while exp.More():
            result.append(exp.Current())
            exp.Next()
        return result
    if len(shapes(TopAbs_SOLID)) != 1 or len(shapes(TopAbs_SHELL)) != 1:
        raise ValueError('The retained STEP must contain exactly one solid and shell')
    if not BRep_Tool.IsClosed_s(shapes(TopAbs_SHELL)[0]):
        raise ValueError('The retained CAD shell is not closed')
    mesher = BRepMesh_IncrementalMesh(shape, .01, False, .10, False)
    if not mesher.IsDone() or mesher.GetStatusFlags() != 0:
        raise ValueError('OCP meshing is incomplete or has status flags')
    vertices, faces, lookup, rows, cad_ids = [], [], {}, [], []
    for fid, item in enumerate(shapes(TopAbs_FACE)):
        face, location = TopoDS.Face_s(item), TopLoc_Location()
        orientation = face.Orientation()
        if orientation not in (TopAbs_FORWARD, TopAbs_REVERSED):
            raise ValueError('Unsupported CAD face orientation')
        poly = BRep_Tool.Triangulation_s(face, location)
        if poly is None or not poly.HasGeometry() or not poly.IsDoublePrecision():
            raise ValueError('Every CAD face must have a binary64 triangulation')
        nodes = [tuple(float(c) for c in poly.Node(i).Transformed(location.Transformation()).Coord())
                 for i in range(1, poly.NbNodes() + 1)]
        triangles = [tuple(int(poly.Triangle(i).Value(j)) for j in (1, 2, 3))
                     for i in range(1, poly.NbTriangles() + 1)]
        lo = len(faces)
        add_face(nodes, triangles, orientation == TopAbs_REVERSED, vertices, faces, lookup)
        rows.append(dict(CAD_face_id=fid, nodes=len(nodes), triangles=len(triangles),
                         output_face_range=[lo, len(faces)], reversed=orientation == TopAbs_REVERSED,
                         OCP_deflection_diagnostic_mm=float(poly.Deflection())))
        cad_ids.extend([fid] * len(triangles))
    if not rows or sum(r['triangles'] for r in rows) != len(faces):
        raise ValueError('Incomplete CAD face extraction')
    report = validate_surface(vertices, faces)
    arrays = dict(vertices=np.asarray(vertices, dtype='<f8'), faces=np.asarray(faces, dtype='<i8'),
                  CAD_face_ids=np.asarray(cad_ids, dtype='<i8'))
    target = output / 'reference-mesh.npz'
    with target.open('xb') as stream:
        np.savez(stream, **arrays)
    with np.load(target, allow_pickle=False) as data:
        if set(data.files) != set(arrays) or any(data[n].dtype != a.dtype or
                data[n].shape != a.shape or data[n].tobytes() != a.tobytes() for n, a in arrays.items()):
            raise ValueError('NPZ roundtrip changed the actual binary64 coordinates or indices')
    report.update(schema='OCP-absolute-reference-tessellation-1', status='reference_mesh_checks_pass',
                  STEP_sha256=sha(plan['STEP']), parameters=plan['parameters'], CAD_faces=rows,
                  complete_CAD_faces=len(rows), output_sha256=sha(target), output=str(target),
                  no_STL_float32_roundtrip=True, BREP_global_error_bound_mm=None,
                  requested_deflection_is_not_a_BREP_bound=True, global_admission=False)
    write_new(output / 'mesh-assessment.json', report)


def run(plan_path):
    start, child, report = time.monotonic(), None, dict(status='refused_before_start')
    deadline = start + 300
    plan_hash = sha(plan_path)
    plan = json.loads(plan_path.read_text())
    output = Path(plan['output'])
    if output.exists() or output.is_symlink():
        raise ValueError('Fresh execution output is required')
    output.mkdir()
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Execution interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        verify(plan, deadline - 30)
        env = os.environ.copy()
        env.update({n: '1' for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                    'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')})
        def limits():
            os.nice(10)
            resource.setrlimit(resource.RLIMIT_CPU, (260, 260))
        command = [plan['python'], '-I', '-B', str(Path(__file__).resolve()), '--worker', str(plan_path)]
        with (output / 'stdout.log').open('xb') as stdout, (output / 'stderr.log').open('xb') as stderr:
            child_start = time.monotonic()
            child = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr,
                                     start_new_session=True, preexec_fn=limits)
            report.update(status='child_running', child_pid=child.pid, command=command)
            child.wait(timeout=min(260, deadline - 30 - time.monotonic()))
            report.update(child_exit_code=child.returncode, child_wall_seconds=time.monotonic() - child_start)
        if child.returncode != 0:
            raise ValueError('The actual CAD child did not return zero')
        assessment = json.loads((output / 'mesh-assessment.json').read_text())
        if (assessment['status'] != 'reference_mesh_checks_pass' or
                sha(output / 'reference-mesh.npz', deadline) != assessment['output_sha256']):
            raise ValueError('The actual complete reference receipt or output differs')
        report['status'] = 'completed_reference_mesh_only'
    except BaseException as error:
        report.update(status='refused_or_interrupted', error=type(error).__name__ + ': ' + str(error))
    finally:
        if child is not None and child.poll() is None:
            try:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=min(5, max(.001, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=min(5, max(.001, deadline - time.monotonic())))
            except BaseException as error:
                report.update(status='refused_child_cleanup', cleanup_error=str(error))
        try:
            verify(plan, deadline)
            if sha(plan_path, deadline) != plan_hash:
                raise ValueError('The plan changed')
            report['inputs_and_runtime_unchanged'] = True
        except BaseException as error:
            report.update(status='refused_integrity_or_deadline', integrity_error=str(error))
        if time.monotonic() > deadline or child is not None and child.poll() is None:
            report['status'] = 'refused_deadline_or_live_child'
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        report.update(plan_sha256=plan_hash, actual_child_exit_code=None if child is None else child.returncode,
                      child_terminal=child is None or child.poll() is not None,
                      wall_seconds=time.monotonic() - start,
                      child_usage=dict(CPU_user_seconds=usage.ru_utime, CPU_system_seconds=usage.ru_stime,
                                       max_RSS_bytes=usage.ru_maxrss),
                      global_admission=False, BREP_global_error_bound_mm=None)
        write_new(output / 'execution-receipt.json', report)
    return 0 if report['status'] == 'completed_reference_mesh_only' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        worker(json.loads(args.worker.read_text()), Path(json.loads(args.worker.read_text())['output']))
    else:
        raise SystemExit(run(HERE / 'plan.json'))
