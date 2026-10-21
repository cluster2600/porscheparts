"""Verify the complete portable STL picture capsule without scientific imports."""
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / 'manifest.json').read_text())
    files = manifest['files_sha256']
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p != HERE / 'manifest.json'}
    if actual != set(files) or any((HERE / name).is_symlink() or sha(HERE / name) != digest for name, digest in files.items()):
        raise ValueError('Capsule file set or complete SHA differs')
    provenance = json.loads((HERE / 'source-provenance.json').read_text())
    if any(files[name] != row['copied_sha256'] or row['source_sha256'] != row['copied_sha256'] for name, row in provenance.items()):
        raise ValueError('An original byte-identical copy differs')
    render = json.loads((HERE / 'render-001/receipt.json').read_text())
    if render['needle_counts'] != [463, 0] or render['complete_triangle_counts'] != [44172, 638174] or render['geometry_modified'] or render['new_topology_or_fidelity_admission']:
        raise ValueError('Actual picture scope differs')
    for name, expected in zip(('native.stl', 'remeshed.stl'), render['complete_triangle_counts']):
        path = HERE / 'inputs' / name
        with path.open('rb') as stream:
            header = stream.read(84)
        if len(header) != 84 or struct.unpack('<I', header[80:84])[0] != expected or path.stat().st_size != 84 + 50 * expected:
            raise ValueError('Actual complete binary STL length or count differs')
    for name, digest in render['input_sha256'].items():
        if files[name] != digest:
            raise ValueError('An executed renderer input differs')
    for name, digest in render['exports_sha256'].items():
        if files['render-001/' + name] != digest:
            raise ValueError('An actual export differs')
    execution = json.loads((HERE / 'evidence/render-execution/execution-receipt.json').read_text())
    if not (execution['actual_returncode'] == 0 and execution['direct_child_reaped'] and execution['no_non_zombie_group_members'] and execution['sources_and_plan_unchanged'] and not execution['timeout'] and not execution['interrupted'] and not execution['signals_to_owned_group_only']):
        raise ValueError('Actual render execution was not successfully closed')
    print(json.dumps(dict(status='portable_actual_surface_picture_verified', payloads=len(files), actual_triangle_counts=render['complete_triangle_counts'], actual_needle_counts=render['needle_counts'], no_geometry_edit=True, no_global_admission=True)))


if __name__ == '__main__':
    main()
