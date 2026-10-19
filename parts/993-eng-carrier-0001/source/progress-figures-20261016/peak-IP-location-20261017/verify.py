"""Verify the portable retained figure without a scientific import or solve."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    load = lambda name: json.loads((HERE / name).read_text())
    manifest = load('manifest.json')
    files = manifest['files']
    actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file()}
    require(actual == set(files) | {'manifest.json', 'publication-validation.json'},
            'The complete capsule file list differs')
    for name, row in files.items():
        path = HERE / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,
                'A manifest path escapes the capsule')
        require(not any(p.is_symlink() for p in [path, *path.parents]),
                'A capsule payload is reached through a symlink')
        require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],
                'A retained capsule payload changed: ' + name)
    require(sum(row['bytes'] for row in files.values()) == manifest['payload_bytes']
            and len(files) == manifest['payload_count'], 'Payload totals differ')
    publication = load('publication-validation.json')
    require(publication['manifest_sha256'] == sha(HERE / 'manifest.json'),
            'The publication binding differs')
    origins = load('copy-origins.json')['files']
    for name, row in origins.items():
        require(files[name]['sha256'] == row['sha256'] and files[name]['bytes'] == row['bytes'],
                'A copy differs from its retained original identity')
    terminal = load('evidence/render-root-terminal.json')
    require(terminal['actual_tool_returncode'] == 0 and terminal['direct_child_reaped']
            and terminal['group_reaped_and_empty_no_signals'] and not terminal['timeout'],
            'The original render was not closed successfully')
    require(terminal['assessment_sha256'] == sha(HERE / 'render-001/render-receipt.json')
            and terminal['supervision_sha256'] == sha(HERE / 'evidence/render-supervision.json')
            and terminal['launch_sha256'] == sha(HERE / 'evidence/original-launch-plan.json'),
            'An actual render receipt binding differs')
    for name, row in terminal['outputs'].items():
        require(files['render-001/' + name] == row, 'An original output differs')
    receipt = load('render-001/render-receipt.json')
    require(receipt['all_faces_per_panel'] == dict(XY=45654, XZ=45654, roots=45654, eye=45654)
            and receipt['all_four_maxima_preserved'] and not receipt['FEA_started']
            and not receipt['global_admission'], 'The retained display scope differs')
    original = load('evidence/original-render-plan.json')
    require(receipt['plan_sha256'] == sha(HERE / 'evidence/original-render-plan.json'),
            'The historical plan binding differs')
    for name, digest in original['files_sha256'].items():
        path = HERE / ('evidence/original-preparation-README.md' if name == 'README.md' else name)
        require(sha(path) == digest, 'A historical render source differs')
    spec = importlib.util.spec_from_file_location('_retained_peak_figure', HERE / 'render.py')
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    renderer.verify(load('render-plan.json'))
    require(receipt['exact_source_peak_cases'] == load('data/figure-data.json')['cases'],
            'The four retained cases differ from the rendered cases')
    print(json.dumps(dict(status='retained_actual_figure_copies_verified',
        payload_files=len(files), payload_bytes=manifest['payload_bytes'],
        byte_identical_copies=len(origins), original_render_actual_RC=0,
        portable_replay_executed=publication['portable_replay_executed'],
        new_FEA=False, global_admission=False)))


if __name__ == '__main__':
    main()
