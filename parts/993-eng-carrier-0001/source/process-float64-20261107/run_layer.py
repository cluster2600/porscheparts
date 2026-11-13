"""Same-profile current-carrier float64 layer replay; explicit private inputs only.

Draft: execute only after the preparation has been reviewed. This entrypoint
uses the repository's existing native slicing, serialization and audit helpers.
It neither installs packages nor substitutes another input or runtime profile.
"""
import argparse
import ctypes
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def inputs(args):
    manifest_path = HERE / 'source-manifest.json'
    if sha(manifest_path) != args.source_manifest_sha256:
        raise ValueError('Source manifest identity differs')
    expected = read_json(manifest_path)
    supplied = read_json(args.input_manifest)
    if supplied.get('schema') != 'carrier-float64-layer-private-input@1':
        raise ValueError('Explicit private input schema differs')
    repo = Path(args.repository_root).resolve(strict=True)
    for name, digest in expected['repository_sources_sha256'].items():
        path = (repo / name).resolve(strict=True)
        if not path.is_relative_to(repo) or sha(path) != digest:
            raise ValueError('Repository source differs: ' + name)
    for name, digest in expected['bundle_sources_sha256'].items():
        if Path(name).name != name or sha(HERE / name) != digest:
            raise ValueError('Replay source differs: ' + name)
    if (sys.version_info[:3] != (3, 11, 18) or not sys.flags.isolated
            or not sys.flags.dont_write_bytecode or not sys.flags.no_site
            or sha(sys.executable) != expected['python_sha256']):
        raise ValueError('Recorded isolated CPython 3.11.18 is required')
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Only the recorded macOS arm64 profile is admitted')
    paths = {key: Path(value).resolve(strict=True) for key, value in supplied['paths'].items()}
    for key, digest in expected['private_inputs_sha256'].items():
        if key not in paths or not paths[key].is_file() or sha(paths[key]) != digest:
            raise ValueError('Private input identity differs: ' + key)
    if supplied['source_id'] != expected['source_id'] or supplied['layer'] != 517:
        raise ValueError('Only the admitted current source and layer 517 are supported')
    profile = read_json(paths['runtime_profile'])
    if (paths['site_packages'] != Path(profile['site_packages']).resolve()
            or profile['python_sha256'] != expected['python_sha256']
            or profile['python_version'] != '3.11.18' or profile['architecture'] != 'arm64'):
        raise ValueError('Supplied package tree differs from the recorded runtime')
    with paths['mesh'].open('rb') as stream:
        counts = struct.unpack('<QQ', stream.read(16))
    if (list(counts) != expected['source_counts']
            or paths['mesh'].stat().st_size != 16 + 24 * sum(counts)):
        raise ValueError('Float64 mesh header, counts or exact byte size differs')
    return expected, supplied, paths, profile, repo


def verify_profile(profile):
    for name, row in profile['source_and_native_files'].items():
        path = Path(name)
        if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError('Recorded runtime file differs')
    for name, version in profile['packages'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError('Recorded runtime package version differs: ' + name)


def loaded_images():
    library = ctypes.CDLL(None)
    library._dyld_image_count.restype = ctypes.c_uint32
    library._dyld_get_image_name.argtypes = [ctypes.c_uint32]
    library._dyld_get_image_name.restype = ctypes.c_char_p
    images = {}
    for i in range(library._dyld_image_count()):
        path = Path(library._dyld_get_image_name(i).decode())
        images[str(path)] = ({'sha256': sha(path), 'bytes': path.stat().st_size}
                             if path.is_file() else
                             {'system_shared_cache_image': True, 'filesystem_hash_unavailable': True})
    return dict(macOS_version=platform.mac_ver()[0], kernel_release=platform.release(), images=images)


def worker(args):
    started = time.monotonic()
    expected, supplied, paths, profile, repo = inputs(args)
    sys.path.insert(0, str(paths['site_packages']))
    import numpy as np
    import pyslm
    import trimesh
    verify_profile(profile)
    base = repo / 'parts/993-eng-carrier-0001/source'
    layers = module('replay_native_layers', base / 'process-slicing-20261016/layers.py')
    core = module('replay_native_core', base / 'process-coverage-20261016/build_pyslm.py')
    audit = module('replay_native_audit', base / 'process-slicing-20261016/audit_scanpaths.py')
    # part_cache imports its neighbouring layer helpers; its full-cache builder is never called.
    sys.path.insert(0, str(base / 'process-slicing-20261016'))
    cache = module('replay_native_cache', base / 'process-cache-20261016/part_cache.py')
    oracle = module('replay_strict_oracle', HERE / 'strict_plane_oracle.py')
    outward = module('replay_outward_bounds', HERE / 'outward_bounds.py')
    admission = read_json(paths['admission'])
    golden = read_json(paths['golden_receipt'])
    if admission['status'] != 'current_float64_surface_runtime_and_pose_admitted_for_one_layer':
        raise ValueError('Current source admission status differs')
    nv, nf = expected['source_counts']
    vertices = np.memmap(paths['mesh'], dtype='<f8', mode='r', offset=16, shape=(nv, 3))
    faces = np.memmap(paths['mesh'], dtype='<u8', mode='r', offset=16 + 24 * nv, shape=(nf, 3))

    def digest(array):
        h = hashlib.sha256()
        for begin in range(0, len(array), 65536):
            h.update(np.ascontiguousarray(array[begin:begin + 65536]).tobytes())
        return h.hexdigest()

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces.astype('<i8'), process=False, validate=False)
    if (digest(mesh.vertices) != expected['vertex_bytes_sha256']
            or digest(mesh.faces) != expected['face_bytes_sha256']):
        raise ValueError('Float64 coordinate bits or ordered faces changed during import')
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
            and np.isfinite(mesh.vertices).all() and np.all(mesh.area_faces > 0)):
        raise ValueError('Current mesh topology, orientation or face area refused')
    part = pyslm.Part('current-carrier-float64-replay')
    part.setGeometry(mesh, fixGeometry=False, mergeVertices=False)
    unposed = part.geometry
    if digest(unposed.vertices) != expected['vertex_bytes_sha256'] or digest(unposed.faces) != expected['face_bytes_sha256']:
        raise ValueError('Identity PySLM import changed the source arrays')
    del unposed
    gc.collect()
    parameters = json.loads(json.dumps(core.PARAMETERS))
    if parameters != admission['parameters']:
        raise ValueError('Native process parameters differ from the admitted reference')
    part.rotation = parameters['rotation_degrees_xyz']
    part.dropToPlatform(parameters['support_gap_mm'])
    posed = part.geometry
    pose = admission['pose']
    if (digest(posed.vertices) != pose['vertices_f64_sha256']
            or digest(posed.faces) != pose['faces_i64_sha256']
            or not np.array_equal(part.origin, pose['origin_mm'])
            or not np.array_equal(part.rotation, pose['rotation_degrees_xyz'])
            or not np.array_equal(part.scaleFactor, pose['scale_factor'])):
        raise ValueError('Exact current pose identity differs')
    index, z = 517, (517 + .5) * parameters['layer_height_mm']
    if z != admission['calendar']['representative_z_mm'] or index != admission['calendar']['representative_layer_index']:
        raise ValueError('Current representative plane differs')
    cut = oracle.slice_rings(posed.vertices, posed.faces, z)
    interval = outward.section_area_bounds(posed.vertices, cut['ring_source_edges'], z, cut['signed_area_mm2'])
    native = layers.layer_geometry(part, z, parameters, layers.face_z_bounds(posed))
    output = Path(args.output).resolve()
    scientific = output / 'scientific'
    scientific.mkdir(mode=0o700, exist_ok=False)
    (scientific / 'layers').mkdir()
    row = cache.write_layer(scientific, index, z, native)
    raw = scientific / 'layers/layer-00517.npz'
    domain = audit.section_domain(cut['rings'])
    with np.load(raw, allow_pickle=False) as data, np.load(paths['golden_arrays'], allow_pickle=False) as reference:
        if set(data.files) != set(reference.files):
            raise ValueError('Reference array fields differ')
        for key in data.files:
            if (data[key].dtype != reference[key].dtype or data[key].shape != reference[key].shape
                    or data[key].tobytes() != reference[key].tobytes()):
                raise ValueError('Direct layer 517 array-byte parity failed: ' + key)
        native_audit = audit.layer_check(data, row['part_area_mm2'])
        hatch_audit = audit.segments_check(data['part_hatch_segments_mm'], domain)
        contours = audit.paths(data['part_scan_contour_points_mm'], data['part_scan_contour_offsets'])
        pieces = [np.stack((p[:-1], p[1:]), axis=1) for p in contours]
        contour_audit = audit.segments_check(np.concatenate(pieces) if pieces else np.empty((0, 2, 2)), domain)
    area_ok = abs(row['part_area_mm2'] - cut['signed_area_mm2']) <= audit.AREA_RELATIVE_TOLERANCE * max(1., abs(cut['signed_area_mm2']))
    if not (native_audit['passed'] and hatch_audit['passed'] and contour_audit['passed'] and area_ok):
        raise ValueError('Unchanged native and independent domain checks refused the layer')
    images = loaded_images()
    baseline = golden['loaded_shared_images']
    if images['macOS_version'] != baseline['macOS_version'] or images['kernel_release'] != baseline['kernel_release']:
        raise ValueError('Recorded macOS system profile changed')
    for name, identity in images['images'].items():
        if baseline['images'].get(name) != identity:
            raise ValueError('Loaded native image is not in the recorded profile')
    verify_profile(profile)
    inputs(args)
    if digest(mesh.vertices) != expected['vertex_bytes_sha256'] or digest(posed.vertices) != pose['vertices_f64_sha256']:
        raise ValueError('Source or posed coordinates changed during slicing')
    report = dict(status='same_profile_current_float64_layer_517_replayed', source_id=expected['source_id'],
                  source_manifest_sha256=args.source_manifest_sha256, input_manifest_sha256=sha(args.input_manifest),
                  source_sha256=sha(paths['mesh']), runtime_profile_sha256=sha(paths['runtime_profile']),
                  pose=pose, parameters=parameters, layer=row, source_coordinate_bits_preserved=True,
                  direct_reference_arrays_bitwise_equal=True, raw_arrays_sha256=sha(raw),
                  native_audit=native_audit, independent_hatch_audit=hatch_audit,
                  independent_contour_audit=contour_audit, independent_area_bounds=interval,
                  loaded_shared_images=images, complete_build_audited=False,
                  supports_generated=False, machine_job_generated=False,
                  elapsed_seconds=time.monotonic() - started)
    write_json(output / 'result.json', report)


def guarded(args):
    expected, _, _, _, _ = inputs(args)
    output = Path(args.output).resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError('An existing parent and a fresh exclusive output directory are required')
    if shutil.disk_usage(output.parent).free < 8 * 1024**3:
        raise ValueError('At least 8 GiB free storage is required')
    output.mkdir(mode=0o700)
    cleanup_module = module('replay_owned_group', HERE / 'owned_process_group.py')
    command = [sys.executable, '-I', '-B', '-S', str(Path(__file__).resolve()),
               '--input-manifest', str(Path(args.input_manifest).resolve()),
               '--repository-root', str(Path(args.repository_root).resolve()),
               '--source-manifest-sha256', args.source_manifest_sha256,
               '--output', str(output), '--worker']
    write_json(output / 'start-intent.json', dict(command=command, wall_seconds=300, aggregate_RSS_bytes=8*1024**3))
    child, cleanup, reason, error, peak = None, None, 'complete', None, 0
    started = time.monotonic()
    try:
        with (output / 'stdout.log').open('x') as stdout, (output / 'stderr.log').open('x') as stderr:
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', LC_ALL='C', OPENBLAS_NUM_THREADS='1',
                       OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
            child = subprocess.Popen(command, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                     start_new_session=True, env=env)
            while child.poll() is None:
                state = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid=,rss='], capture_output=True,
                                       text=True, check=True, timeout=5)
                rss = sum(int(row.split()[2])*1024 for row in state.stdout.splitlines()
                          if len(row.split()) == 3 and int(row.split()[1]) == child.pid)
                peak = max(peak, rss)
                if time.monotonic()-started > 300 or rss > 8*1024**3 or shutil.disk_usage(output.parent).free < 8*1024**3:
                    reason = 'finite_resource_guard'; break
                time.sleep(1)
    except BaseException as exc:
        reason, error = 'observer_error', repr(exc)
    finally:
        if child is not None:
            try:
                cleanup = cleanup_module.cleanup_owned_group(child, child.pid)
            except BaseException as exc:
                reason, error = 'owned_group_cleanup_failed', repr(exc)
        if child is None or child.returncode != 0:
            reason = 'worker_failed' if reason == 'complete' else reason
        try:
            inputs(args)
            unchanged = True
        except BaseException as exc:
            unchanged, reason, error = False, 'source_or_input_changed', repr(exc)
        write_json(output / 'terminal.json', dict(reason=reason, actual_returncode=None if child is None else child.returncode,
                   peak_group_RSS_bytes=peak, owned_group_cleanup=cleanup, error=error,
                   source_and_input_identities_unchanged=unchanged,
                   elapsed_seconds=time.monotonic()-started))
    if reason != 'complete' or not cleanup or not cleanup['group_absent'] or not cleanup['direct_child_reaped']:
        raise RuntimeError('Bounded layer replay did not complete; inspect retained logs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', required=True)
    parser.add_argument('--input-manifest', required=True)
    parser.add_argument('--source-manifest-sha256', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    worker(args) if args.worker else guarded(args)
