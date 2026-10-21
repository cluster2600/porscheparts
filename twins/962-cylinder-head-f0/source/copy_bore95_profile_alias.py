"""One separately authorized byte copy; no USD import or content authoring."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import signal
import time

DIGEST = 'b5cbcc23c6d59762c4a0e876691b2815ef402fc906be53aac069e46935d6850f'
BYTES = 39026927


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def copy_identity(source, directory, expected, size):
    if source.is_symlink() or not source.is_file() or source.stat().st_size != size or sha(source) != expected:
        raise ValueError('Exact unchanged source bytes required')
    if directory.exists() or directory.is_symlink():
        raise FileExistsError('Fresh alias directory required')
    directory.mkdir()
    target = directory / 'solid-face-normals.usd'
    with source.open('rb') as left, target.open('xb') as right:
        shutil.copyfileobj(left, right, length=1024 * 1024)
    after, copied = sha(source), sha(target)
    if after != expected or copied != expected or target.stat().st_size != size:
        raise ValueError('Alias/source byte identity failed; partial evidence preserved')
    return dict(source_before_sha256=expected, source_after_sha256=after,
                alias_sha256=copied, bytes=size, byte_identical=True)


def execute(recipe, expected):
    if sha(recipe) != expected:
        raise ValueError('Exact reviewed copy-child hash required')
    d = json.loads(recipe.read_text())
    if (any(d.get(k) is not True for k in ('root_reviewed', 'peer_reviewed', 'execution_authorized'))
            or type(d['not_after_epoch']) not in (int, float)
            or not math.isfinite(d['not_after_epoch']) or time.time() > d['not_after_epoch']):
        raise ValueError('Current root and peer copy authority required')
    owned = Path(d['owned_root']); source = Path(d['source']); directory = Path(d['alias_dir'])
    if (owned.is_symlink() or not owned.is_dir() or owned.resolve() != owned
            or source != owned / 'bore95-author001/solid-face-normals.usdc'
            or directory != owned / 'bore95-profile-alias001'
            or source.parent.resolve() != source.parent
            or d['source_sha256'] != DIGEST or d['source_bytes'] != BYTES
            or d['alias_name'] != 'solid-face-normals.usd'):
        raise ValueError('Exact owned source and fresh alias association required')
    required = [str(Path(__file__).resolve()), str(source)]
    if any(p not in d['input_sha256'] for p in required):
        raise ValueError('Copy source and executed script must both be hash-bound')
    for name, digest in d['input_sha256'].items():
        path = Path(name)
        if not path.is_absolute() or path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise ValueError('Copy input drift')
    result = copy_identity(source, directory, DIGEST, BYTES)
    if sha(recipe) != expected or any(sha(Path(p)) != h for p, h in d['input_sha256'].items()):
        raise ValueError('Child or source changed during copy; evidence preserved')
    with (directory / 'frozen-copy-child.json').open('x') as stream:
        stream.write(recipe.read_text())
    if sha(directory / 'frozen-copy-child.json') != expected:
        raise ValueError('Frozen copy-child snapshot changed')
    result.update(schema='962-bore95-profile-suffix-alias/v1', status='byte_identical_suffix_alias_created',
                  source='bore95-author001/solid-face-normals.usdc',
                  alias='bore95-profile-alias001/solid-face-normals.usd',
                  copy_child_sha256=expected, copy_script_sha256=sha(__file__),
                  serialization_or_geometry_edit=False, USD_imported=False,
                  stamp_fix_or_write_metadata=False, material_or_physics_assignment=False,
                  computed_fields=False, validator_executed=False, manufacturing_authorized=False)
    with (directory / 'alias-receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=Path); parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    def expired(signum, frame):
        raise TimeoutError('Byte-copy step exceeded 30 seconds; preserve partial evidence')
    signal.signal(signal.SIGALRM, expired); signal.alarm(30)
    try:
        print(json.dumps(execute(args.recipe, args.sha256), allow_nan=False))
    finally:
        signal.alarm(0)
