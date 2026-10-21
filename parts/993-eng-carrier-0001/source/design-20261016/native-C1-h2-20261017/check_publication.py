"""Check this fixed durable publication; no ZIP extraction or numerical imports."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat

HERE = Path(__file__).resolve().parent
MANIFEST = '3e61c6a688a80e8bf7062a7e2d6090921fdc87007d7e8865799951494b97f5d6'
VERIFY_ROOT = 'fd9db80722820b8f5c8be7294c2fbf33d7be937d767d90b6370611c936038815'
REPLAY_ROOT = '3cd27111adb36277638a3860e5f0ff01c3ef3126665573576d8799be6a0fafa9'
REPORTS = {
    'rigid-energy.json': 'bd3cff7793dc441a5912c6ad0f1d9602d8959b75e790e3944d1883f1184999a4',
    'rigid-peak.json': '9bd4eb4de62d4f94f91eaa18b4e3c79223a396b4aacb72e580210e28a247b666',
    'spring-energy.json': '1845d80d6ea14bc4faf2db0c2e593350c18710f78ad59957051e4f8500c3bae5',
    'spring-peak.json': '32e725f521d076e2800e585cada2f5c162a14cc21598262df31bca541c60ebc5',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    require(path.stat().st_size < 2_000_000, 'Only small JSON proofs may be parsed')
    return json.loads(path.read_text())


def inventory(folder):
    rows = read(folder / 'archive.json')['files_sha256']
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() or p.is_symlink()}
    require(actual == set(rows) | {'archive.json'}, 'Complete publication inventory differs')
    for name, expected in rows.items():
        relative = PurePosixPath(name)
        require(relative.as_posix() == name and not relative.is_absolute()
                and not any(p in {'.', '..'} for p in relative.parts), 'Noncanonical publication path')
        path = folder / name
        require(not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), 'Regular nonsymlink files required')
        require(sha(path) == expected, 'Whole publication file SHA differs')
    return rows


def link(record, key, target):
    require(record[key] == sha(target), 'Closed receipt cross-link differs')


def closed(supervision):
    require(supervision['status'] == 'executed' and supervision['actual_returncode'] == 0
            and supervision['direct_child_reaped'] and supervision['no_non_zombie_group_members']
            and supervision['final_group_members'] == [] and not supervision['timeout']
            and not supervision['interrupted'] and supervision['failure'] is None
            and supervision['cleanup_error'] is None and supervision['sources_and_plan_unchanged'],
            'Actual closed owned RC0 required')


def reports(folder):
    for name, expected in REPORTS.items():
        require(sha(folder / name) == expected, 'Complete replayed report bytes differ')
        report = read(folder / name)
        if 'energy' in name:
            require(report['energy_closure_pass'] and report['tolerance'] == 1e-4, 'Original energy gate differs')
        else:
            require(report['maximum_ties'] == 1
                    and report['all_global_maximum_ties'][0]['element_id'] == 90371
                    and report['all_global_maximum_ties'][0]['IP_one_based'] == 2,
                    'Complete H2 peak identity differs')


def check(folder=HERE):
    rows = inventory(folder)
    require(sha(folder / 'manifest.json') == MANIFEST, 'Frozen assembled manifest differs')
    manifest = read(folder / 'manifest.json')
    frozen = set(manifest['files_sha256']) | set(manifest['archives']) | {'manifest.json'}
    require(len(frozen) == 13 and frozen <= set(rows), 'All 13 original capsule files required')
    require(all(rows[n] == h for n, h in manifest['files_sha256'].items()), 'Frozen utility identity differs')
    require(all(rows[n] == r['sha256'] and (folder / n).stat().st_size == r['bytes'] < 100_000_000
                for n, r in manifest['archives'].items()), 'Frozen three ZIP identities or bounds differ')
    inherited = manifest['dependency']
    base = folder.parent / 'native-C1-20261017'
    require(sha(base / 'manifest.json') == inherited['manifest_sha256']
            == 'faa9069cc12e4ac69c784ab4af50e74de65c0c26403172721c500b8d5641e1d1'
            and sha(base / 'archive.json') == inherited['inventory_sha256']
            == '8628adb34a0ff61fe6ad6790400179a7a6932caf3568ca2328adb002209bd9f8',
            'Closed C1 dependency metadata differs')
    require(len(inherited['members']) == 186
            and sum(len(r['members']) for r in manifest['archives'].values()) == 234,
            'Exact inherited and new member counts required')
    for stage, root_sha in [('verify', VERIFY_ROOT), ('replay', REPLAY_ROOT)]:
        evidence = folder / 'evidence' / stage
        root_path = folder / 'evidence/root-review' / ('root-' + stage + '-terminal-review-001.json')
        require(sha(root_path) == root_sha, 'Actual root closeout differs')
        root = read(root_path); terminal = read(evidence / 'terminal-collection.json')
        supervision = read(evidence / 'execution-receipt.json')
        closed(supervision)
        link(root, 'terminal_sha256', evidence / 'terminal-collection.json')
        link(root, 'supervision_sha256', evidence / 'execution-receipt.json')
        link(terminal, 'supervision_sha256', evidence / 'execution-receipt.json')
        link(supervision, 'plan_sha256', evidence / 'launch-plan.json')
        require(terminal['actual_tool_returncode'] == terminal['actual_child_returncode'] == 0,
                'Actual collected tool and child RC0 required')
        for name, expected in supervision['logs_sha256'].items():
            require(sha(evidence / name) == expected, 'Closed log SHA differs')
    replay = folder / 'evidence/replay'
    receipt = read(replay / 'reanalysis-receipt.json')
    root = read(folder / 'evidence/root-review/root-replay-terminal-review-001.json')
    terminal = read(replay / 'terminal-collection.json')
    link(root, 'reanalysis_receipt_sha256', replay / 'reanalysis-receipt.json')
    link(terminal, 'reanalysis_receipt_sha256', replay / 'reanalysis-receipt.json')
    link(terminal, 'extra_collector_refusal_retained_sha256', replay / 'terminal-collection-refusal-001.json')
    require(receipt['actual_returncode'] == 0 and receipt['runtime_unchanged']
            and receipt['restored_inputs_unchanged'] and receipt['runtime_files'] == 500
            and receipt['cwd'] == '/' and receipt['actual_workers'] == 0
            and receipt['new_solver_run'] is False and receipt['new_mesh'] is False,
            'Actual portable replay contract differs')
    reports(replay)
    return dict(status='durable_C1_h2_publication_whole_files_and_closed_proof_links_PASS',
                files=len(rows) + 1, manifest_sha256=MANIFEST, inherited_members=186, new_members=234,
                four_reports_BYTE_equal=True, archive_decompression=False, numerical_replay=False,
                native_CAD_mesher_solver_run=False)


if __name__ == '__main__':
    print(json.dumps(check()))
