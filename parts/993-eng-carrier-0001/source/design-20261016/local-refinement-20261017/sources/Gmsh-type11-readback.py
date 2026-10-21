"""Load original serialized mesh7 as a discrete Gmsh model; no CAD or remesh."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def type11_permutation(properties):
    """Return native-position -> CCX-position from actual reference nodes."""
    name, dim, order, count, local, primary = properties
    if (dim, order, count, primary) != (3, 2, 10, 4) or len(local) != 30:
        raise ValueError('Expected native affine ten-node tetrahedron properties')
    actual = [tuple(float(v) for v in local[i:i+3]) for i in range(0, 30, 3)]
    if not all(math.isfinite(v) for p in actual for v in p) or len(set(actual[:4])) != 4:
        raise ValueError('Invalid native reference corners')
    expected = actual[:4] + [tuple((actual[i][d]+actual[j][d])/2 for d in range(3))
                            for i, j in ((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))]
    if len(set(actual)) != 10 or set(actual) != set(expected):
        raise ValueError('Native type11 nodes do not match CCX edge midpoints')
    return [expected.index(point) for point in actual]


def run(expected):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (40, 41))
    def expired(*_):
        raise TimeoutError('The fixed 45s read-only Gmsh alarm expired')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 45)
    plan_path = HERE/'plan.json'; plan_sha = sha(plan_path)
    assert len(sys.argv) == 2 and expected == plan_sha
    plan = json.loads(plan_path.read_text()); files = plan['files_sha256']
    assert os.getpriority(os.PRIO_PROCESS, 0) == 10
    assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'))
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts and
               not any(p.is_symlink() for p in [ROOT/n, *(ROOT/n).parents]) for n in files)
    before = {n: sha(ROOT/n) for n in files}; assert before == files
    assert sha(sys.executable) == plan['python_executable_sha256']
    out = HERE/'output-001'; assert not out.exists(); out.mkdir()
    report = dict(status='incomplete_readback_no_admission', plan_sha256=plan_sha,
                  files_sha256_before=before, no_CAD_import=True, mesh_generated=False, FEA_started=False)
    gmsh = None; initialized = False; code = 1
    try:
        import gmsh
        import numpy as np
        reader_path = ROOT/plan['energy_reader']
        spec = importlib.util.spec_from_file_location('_original_mesh7_readonly_energy', reader_path)
        energy = importlib.util.module_from_spec(spec); spec.loader.exec_module(energy)
        assert gmsh.__version__ == '4.15.2' and Path(gmsh.__file__).resolve() == (ROOT/plan['gmsh_module']).resolve()
        gmsh.initialize(); initialized = True
        gmsh.option.setNumber('General.Terminal', 0); gmsh.option.setNumber('General.NumThreads', 1)
        mesh = ROOT/plan['mesh_inp']
        tags, xyz, eids, conn = energy.read_mesh(mesh)
        properties = gmsh.model.mesh.getElementProperties(11)
        permutation = type11_permutation(properties)
        inverse = [permutation.index(i) for i in range(10)]
        entity = gmsh.model.addDiscreteEntity(3)
        gmsh.model.mesh.addNodes(3, entity, tags, xyz.reshape(-1))
        gmsh.model.mesh.addElementsByType(entity, 11, eids, tags[conn[:, permutation]].reshape(-1))
        actual_tags, actual_xyz, _ = gmsh.model.mesh.getNodes()
        node_order = np.argsort(actual_tags)
        assert np.array_equal(actual_tags[node_order], tags)
        returned_xyz = np.ascontiguousarray(np.asarray(actual_xyz).reshape(-1, 3)[node_order])
        assert returned_xyz.tobytes() == np.ascontiguousarray(xyz).tobytes()
        types, elements, connectivity = gmsh.model.mesh.getElements(3)
        element_order = np.argsort(elements[0]); expected_order = np.argsort(eids)
        assert np.array_equal(elements[0][element_order], eids[expected_order])
        restored = np.asarray(connectivity[0]).reshape(-1, 10)[:, inverse]
        assert np.array_equal(restored[element_order], tags[conn][expected_order])
        report.update(serialized_node_tags_equal_XYZ_bit_equal=True, serialized_CCX_connectivity_inverse_equal=True,
            CCX_positions_for_native_type11=permutation, native_element_type_name=properties[0],
            node_count=len(tags), native_read_method='original_energy_read_mesh_then_Gmsh_discrete_entity')
        assert list(types) == [11] and len(elements[0]) == 85315
        jac = gmsh.model.mesh.getElementQualities(elements[0], 'minDetJac')
        quality = {'minimum_Jacobian': float(min(jac)),
                   'nonpositive_elements': int(np.count_nonzero(jac <= 0)),
                   'finite': bool(np.isfinite(jac).all()), 'elements': len(jac)}
        report['serialized_quality'] = quality
        assert np.isfinite(jac).all() and min(jac) > 0
        mesh_volume = float(gmsh.model.mesh.getElementQualities(elements[0], 'volume').sum())
        cad_volume = json.loads((mesh.parent.parent/'geometry.json').read_text())['volume_mm3']
        metadata = json.loads((mesh.parent/'mesh.json').read_text())
        assert cad_volume == 285568.46624126856 and metadata['volume_relative_error'] == -0.00020481102174940702
        assert math.isfinite(mesh_volume) and mesh_volume > 0
        relative = mesh_volume/cad_volume-1
        report.update(status='original_serialized_mesh7_volume_readback_complete', elements=85315,
            serialized_mesh_volume_mm3=mesh_volume, CAD_volume_mm3=cad_volume,
            serialized_volume_relative_error=relative, historical_minimum_Jacobian=metadata['minimum_sampled_Jacobian'],
            historical_mesh_volume_mm3=metadata['mesh_volume_mm3'],
            historical_volume_relative_error=metadata['volume_relative_error'],
            volume_difference_mm3=mesh_volume-metadata['mesh_volume_mm3'],
            relative_error_difference=relative-metadata['volume_relative_error'],
            exact_float_volume_equal=mesh_volume == metadata['mesh_volume_mm3'],
            historical_nonregression_comparison=abs(relative) <= abs(metadata['volume_relative_error']),
            comparison_scope='Measured serialization readback only; no admission threshold or historical metadata changed')
        code = 0
    except BaseException as error:
        report['error'] = dict(type=type(error).__name__, message=str(error))
    finally:
        if initialized:
            try: gmsh.finalize()
            except BaseException as error:
                report['finalize_error'] = dict(type=type(error).__name__, message=str(error)); code = 1
        signal.setitimer(signal.ITIMER_REAL, 0)
        after = {n: sha(ROOT/n) for n in files}
        unchanged = before == after and sha(plan_path) == plan_sha and sha(sys.executable) == plan['python_executable_sha256']
        if not unchanged: code = 1
        report.update(files_sha256_after=after, sources_and_plan_unchanged=unchanged,
            returncode=code, elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, actual_workers=0,
            global_admission=False)
        write(out/'assessment.json', report)
    return code


if __name__ == '__main__':
    raise SystemExit(run(sys.argv[1]))
