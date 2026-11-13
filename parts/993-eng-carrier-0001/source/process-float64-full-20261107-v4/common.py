"""Explicit same-profile bindings for the separate current full-calendar replay."""
import ast
import gc
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
LAYER = HERE.parent / 'process-float64-20261107'
LAYER_MANIFEST = '3c36bdcea66b81c7aef9fc55ad2a18c6311f967bcd802ca90d8bbb14b553c25e'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def bindings(args):
    manifest = HERE / 'source-manifest.json'
    if sha(manifest) != args.source_manifest_sha256:
        raise ValueError('Full-calendar source manifest differs')
    expected = json.loads(manifest.read_text())
    repo = Path(args.repository_root).resolve(strict=True)
    for name, digest in expected['bundle_sources_sha256'].items():
        if Path(name).name != name or sha(HERE / name) != digest:
            raise ValueError('Full-calendar bundle source differs: ' + name)
    for name, digest in expected['repository_sources_sha256'].items():
        path = (repo / name).resolve(strict=True)
        if not path.is_relative_to(repo) or sha(path) != digest:
            raise ValueError('Full-calendar repository source differs: ' + name)
    verify_worker_files(expected['worker_native_images'])
    replay = module('unchanged_current_layer_replay', LAYER / 'run_layer.py')
    old_args = SimpleNamespace(repository_root=str(repo), input_manifest=args.input_manifest,
                              source_manifest_sha256=LAYER_MANIFEST)
    original, supplied, paths, profile, repo = replay.inputs(old_args)
    return expected, replay, old_args, original, paths, profile, repo


def load_current(args):
    """Execute the unchanged, pinned public layer worker setup up to its fixed-plane assignment."""
    expected, replay, old_args, original, paths, profile, repo = bindings(args)
    source = inspect.getsource(replay.worker)
    tree = ast.parse(source)
    worker = tree.body[0]
    stops = [i for i, node in enumerate(worker.body)
             if isinstance(node, ast.Assign) and len(node.targets) == 1
             and isinstance(node.targets[0], ast.Tuple)
             and [x.id for x in node.targets[0].elts] == ['index', 'z']]
    if len(stops) != 1 or stops[0] < 10:
        raise ValueError('Pinned public setup boundary differs')
    prefix = worker.body[:stops[0]]
    actual = hashlib.sha256(ast.dump(ast.Module(body=prefix, type_ignores=[]),
                                    include_attributes=False).encode()).hexdigest()
    if actual != expected['public_setup_ast_sha256']:
        raise ValueError('Unchanged public import/pose setup differs')
    worker.name = '_current_setup'
    worker.body = prefix + [ast.Return(value=ast.Call(func=ast.Name(id='locals', ctx=ast.Load()), args=[], keywords=[]))]
    namespace = dict(replay.__dict__)
    exec(compile(ast.fix_missing_locations(tree), str(LAYER / 'run_layer.py'), 'exec'), namespace)
    state = namespace['_current_setup'](old_args)
    import numpy as np
    import trimesh
    posed = state['posed']
    mesh = trimesh.Trimesh(vertices=np.array(posed.vertices, copy=True),
                           faces=np.array(posed.faces, copy=True), process=False, validate=False)
    for key in ('mesh', 'part', 'posed', 'unposed', 'vertices', 'faces'):
        state.pop(key, None)
    del posed, namespace
    gc.collect()
    if (state['digest'](mesh.vertices) != state['pose']['vertices_f64_sha256']
            or state['digest'](mesh.faces) != state['pose']['faces_i64_sha256']):
        raise ValueError('Released parent topology caches changed the posed mesh')
    state.update(mesh=mesh, full_expected=expected, replay=replay, old_args=old_args)
    return state


def verify_worker_files(identities):
    if len(identities) != 1:
        raise ValueError('Exactly the recorded spawn-worker extension is required')
    for name, identity in identities.items():
        path=Path(name)
        if not path.is_file() or path.stat().st_size!=identity['bytes'] or sha(path)!=identity['sha256']:
            raise ValueError('Recorded spawn-worker extension identity differs')


def check_images(images, baseline, worker_images):
    if (images['macOS_version'] != baseline['macOS_version']
            or images['kernel_release'] != baseline['kernel_release']):
        raise ValueError('Recorded macOS system profile differs')
    allowed=dict(baseline['images'])
    for name,identity in worker_images.items():
        if name in allowed and allowed[name]!=identity:
            raise ValueError('Worker image contradicts the unchanged direct baseline')
        allowed[name]=identity
    if any(allowed.get(name)!=identity for name,identity in images['images'].items()):
        raise ValueError('Unexpected or mismatched loaded native image')
    if any(images['images'].get(name)!=identity for name,identity in worker_images.items()):
        raise ValueError('Recorded spawn-worker extension was not observed')
    return True


def verify_runtime(state, args):
    replay = state['replay']
    images = replay.loaded_images()
    baseline = state['golden']['loaded_shared_images']
    check_images(images, baseline, state['full_expected']['worker_native_images'])
    replay.verify_profile(state['profile'])
    bindings(args)
    if (state['digest'](state['mesh'].vertices) != state['pose']['vertices_f64_sha256']
            or state['digest'](state['mesh'].faces) != state['pose']['faces_i64_sha256']):
        raise ValueError('Posed source changed during execution')
    return images
