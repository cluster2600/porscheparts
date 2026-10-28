"""Strict per-region profiles and relocatable, lossless input identities."""
import hashlib
import json
from pathlib import Path

import numpy as np

PROFILES = {
    0: dict(backend='cgal-positive-roof-prisms-v4', order='mask-first', csg_seconds=1200),
    2: dict(backend='cgal-positive-roof-prisms-v4', order='mask-first-explicit-local-repair', csg_seconds=600),
    8: dict(backend='pymesh-csgtree-explicit-order', order='mask-first', csg_seconds=600),
    **{i: dict(backend='pymesh-csgtree-explicit-order', order='difference-first', csg_seconds=600)
       for i in (1, 3, 9, 10)},
}
RUNTIME_KEYS = {'schema', 'host', 'remote_parent', 'python', 'audit_python',
                'pymesh_orders', 'prism_csg', 'snap', 'distance'}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def runtime_config(path):
    value = json.loads(Path(path).read_text())
    if set(value) != RUNTIME_KEYS or value['schema'] != 'carrier-native-case-runtime-v2':
        raise ValueError('Runtime must contain exactly the documented nonsecret fields')
    if not isinstance(value['host'], str) or not value['host'] or value['host'].startswith('-') or any(c.isspace() for c in value['host']):
        raise ValueError('Invalid explicit SSH host')
    for name in RUNTIME_KEYS-{'schema', 'host'}:
        text = value[name]
        if not isinstance(text, str) or not text.startswith('/') or '..' in Path(text).parts:
            raise ValueError('Native runtime paths must be explicit absolute paths')
    return value


def selected_inputs(path, source_index):
    """Never infer a backend from geometry or silently choose another polygon."""
    path = Path(path).resolve()
    manifest = json.loads(path.read_text())
    if source_index not in PROFILES:
        raise ValueError('Unsupported native region')
    if not manifest.get('sources_and_input_unchanged') or manifest['expected_regions'] != len(manifest['regions']):
        raise ValueError('Input preparation is incomplete')
    matches = [row for row in manifest['regions'] if row['source_index'] == source_index]
    if len(matches) != 1:
        raise ValueError('Exactly one declared polygon is required for this source')
    row = matches[0]
    roles = ('roofs', 'mask') if source_index in (0, 2) else ('chain', 'mask')
    files = {}
    for role in (*roles, 'part'):
        holder = manifest if role == 'part' else row
        name, expected = holder[role], holder[role+'_sha256']
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError('Prepared input paths must be local basenames')
        actual = path.parent/name
        if actual.is_symlink() or not actual.is_file() or sha(actual) != expected:
            raise ValueError('Prepared '+role+' identity mismatch')
        files[role] = dict(path=str(actual), sha256=expected)
    return manifest, row, files


def arrays_identity(path):
    """All arrays, names, dtypes, shapes and C-order bytes; independent of ZIP order."""
    digest = hashlib.sha256()
    with np.load(path, allow_pickle=False) as archive:
        for name in sorted(archive.files):
            array = archive[name]
            if array.dtype.hasobject:
                raise ValueError('Object arrays are forbidden')
            header = json.dumps([name, array.dtype.str, list(array.shape)], separators=(',', ':')).encode()
            payload = np.ascontiguousarray(array).tobytes()
            digest.update(len(header).to_bytes(8, 'big')); digest.update(header)
            digest.update(len(payload).to_bytes(8, 'big')); digest.update(payload)
    return digest.hexdigest()


def bind_repair(template_path, first_snap, original_raw, output):
    """Rebind file packaging only after exact identity of every array is established."""
    template = json.loads(Path(template_path).read_text())
    for role, path in [('first_snap', first_snap), ('original_raw', original_raw)]:
        if arrays_identity(path) != template['canonical_arrays_sha256'][role]:
            raise ValueError('Frozen left '+role+' arrays differ; explicit repair cannot be reused')
    plan = template['plan'].copy()
    plan.update(input_sha256=sha(first_snap), original_float_sha256=sha(original_raw),
                identity_rebinding=dict(template_sha256=sha(template_path),
                    canonical_arrays_sha256=template['canonical_arrays_sha256'],
                    scope='Only NPZ packaging/path identities rebound after all arrays match exactly; no reindexing, matching or coordinate change.'))
    write(output, plan)
    return plan


def validate_terminal(terminal, plan, runtime_sha256, root):
    """Bind the terminal object to this invocation and stable collected paths."""
    source = plan['source_index']; root = Path(root)
    expected = dict(schema='native-envelope-case-v2',status='executed',source_index=source,
        backend=plan['profile']['backend'],profile=plan['profile'],
        input_manifest_sha256=plan['input_manifest_sha256'],runtime_sha256=runtime_sha256,
        source_snapshot_sha256=plan['sources_sha256'],all_owned_scopes_inactive=True)
    if any(terminal.get(key) != value for key,value in expected.items()):
        raise ValueError('Terminal receipt is not bound to this plan/runtime/source snapshot')
    files = terminal['files_sha256']
    if not isinstance(files,dict) or not files:
        raise ValueError('Missing terminal payload identities')
    for name, digest in files.items():
        path = root/name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or sha(path) != digest:
            raise ValueError('Collected terminal payload identity/path mismatch')
    if source in (0,2):
        ref = terminal['native_audit']; name = 'sealed/native_audit.json'
        if ref != dict(path=name,sha256=files.get(name)) or sha(root/name) != ref['sha256']:
            raise ValueError('Native audit path/SHA is not the stable bound payload')
    else:
        if terminal['legacy_case_directory'] != dict(path='legacy'):
            raise ValueError('Legacy case path differs from the stable contract')
        for name in ['legacy/snap/result.npz','legacy/csg/receipt.json']:
            if name not in files:
                raise ValueError('Legacy case is missing its bound mesh/receipt')
