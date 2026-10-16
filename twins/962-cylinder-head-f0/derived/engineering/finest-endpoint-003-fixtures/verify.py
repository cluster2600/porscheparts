"""Verify sealed payloads and saved synthetic references; no native execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def load_pure(name, filename):
    path = BASE / 'source-snapshots/twins/962-cylinder-head-f0/source' / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify():
    receipt = json.loads((BASE / 'receipt.json').read_text())
    paths = list(BASE.rglob('*'))
    expected = receipt['payload_sha256']
    if any(p.is_symlink() for p in paths):
        raise ValueError('Symlink payload refused')
    files = {str(p.relative_to(BASE)): p for p in paths if p.is_file()}
    if set(files) != set(expected) | {'receipt.json'}:
        raise ValueError('Exact sealed payload inventory required')
    if len(expected) != receipt['payload_files'] or sum(files[n].stat().st_size for n in expected) != receipt['payload_bytes']:
        raise ValueError('Sealed payload count or byte total differs')
    for name, digest in expected.items():
        if hashlib.sha256(files[name].read_bytes()).hexdigest() != digest:
            raise ValueError('Sealed payload changed: ' + name)
    oracle = load_pure('sealed_endpoint_fixture_oracle', 'check_finest_endpoint_fixtures.py')
    ids = load_pure('sealed_endpoint003_ID_oracle', 'check_finest_endpoint_003.py')
    recorded = json.loads((BASE / 'fixture-independent-review.json').read_text())
    cases = [('common-neighbor-source001', False, False),
             ('common-neighbor-source003', False, True), ('all-fixed-source003', True, False)]
    stages = ['original_import_begin', 'original_import_complete', 'candidate_copy_begin',
              'candidate_copy_complete', 'original_quality_scan_begin', 'original_quality_scan_complete',
              'patch_reference_exported', 'patch_envelope_build_begin', 'patch_envelope_build_complete',
              'SMS_begin', 'SMS_returned', 'result_export_begin', 'result_export_complete']
    for label, rotated, improves in cases:
        directory = BASE / 'data' / label
        input_name = 'all-fixed-rotated' if rotated else 'common-fixed-neighbor'
        source = oracle.read(BASE / 'inputs' / (input_name + '.bin'))
        target = oracle.read(BASE / 'inputs' / ('known-centered-cube.bin' if improves else input_name + '.bin'))
        if source != oracle.fixture(rotated=rotated) or target != oracle.fixture(rotated=rotated, split=not improves):
            raise ValueError('Original literal synthetic input/reference changed')
        checked = oracle.assess_arrays(source, oracle.read(directory / 'proposed-surface.bin'),
                                       target, (directory / 'vertex-coordinate-origins.u64').read_bytes())
        native = json.loads((directory / 'report.json').read_text())
        oracle.require_native_flags(native, checked, improves)
        result = recorded['complete_array_and_original_ID_checks'][label]
        if checked != result['actual_complete_geometry']:
            raise ValueError('Complete saved-array assessment differs: ' + label)
        candidate = directory / 'quality-candidate.bin'
        if candidate.exists() is not improves or (improves and candidate.read_bytes() != (directory / 'proposed-surface.bin').read_bytes()):
            raise ValueError('Declared candidate/stagnation output differs')
        logs = [json.loads(line) for line in (directory / 'native.log').read_text().splitlines()]
        if logs[-1] != native:
            raise ValueError('Final native log record differs from the retained report')
        if label.endswith('003'):
            points, faces = source
            bad = [i for i, face in enumerate(faces) if oracle.qualities(points, [face])['below_necessary_bound']]
            face_ids, vertex_ids = ids.patch_reference_ids(faces, bad, len(points))
            exports = ids.verify_reference_exports(directory, face_ids, vertex_ids)
            if exports != result['reference_exports']:
                raise ValueError('Original ordered reference IDs differ')
            ids.verify_reference_exports(BASE / 'expected-reference' / label, face_ids, vertex_ids)
            if [row.get('stage') for row in logs[:-1]] != stages:
                raise ValueError('Flushed scalar progress order differs')
            if native['envelope_reference_kind'] != 'immutable_original_patch_faces' or native['head_physics_executed'] is not False:
                raise ValueError('Immutable original reference and no-physics scope required')
        elif len(logs) != 1:
            raise ValueError('Preserved source001 log changed')
    witness = json.loads((BASE / 'data/subset-envelope-witness003/native.log').read_text())
    literal = dict(schema='962-endpoint003-subset-envelope-witness/v1', epsilon_mm=0.0625,
        reference_triangles=2, subset_triangles=1, included_point_accepted=True,
        complete_included_triangle_accepted=True, small_offset_point_accepted=True,
        omitted_point_full_accepts_subset_rejects=True,
        complete_omitted_triangle_full_accepts_subset_rejects=True,
        outside_point_rejected_by_both=True, passed=True, head_input_used=False,
        solver_admission_established=False, manufacturing_authorized=False)
    if witness != literal or witness != recorded['direct_subset_witness']:
        raise ValueError('Six literal subset-envelope witness outcomes differ')
    if (receipt['synthetic_fixture_checks_passed'] is not True
            or any(receipt[k] is not False for k in ['head_execution_credited', 'head_surface_admitted',
                'solver_admission_established', 'head_physics_executed', 'manufacturing_authorized'])):
        raise ValueError('Synthetic fixture-only scope required')
    return 'Sealed hashes, all three complete saved-array references, ordered patch IDs and six subset expectations pass; no native execution.'


if __name__ == '__main__':
    print(verify())
