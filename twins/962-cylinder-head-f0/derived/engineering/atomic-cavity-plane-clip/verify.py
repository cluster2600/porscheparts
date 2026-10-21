"""Check sealed bytes and retained scalar bindings; no scientific source import."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent
read = lambda n: json.loads((BASE/n).read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
r = read('receipt.json')
payloads = r['payloads']
for name, pin in payloads.items():
    relative = PurePosixPath(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    path = BASE/name
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(BASE)
    assert path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], name
assert not any(p.is_symlink() for p in BASE.rglob('*'))
assert {str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file()} == set(payloads)|{'receipt.json'}
assert len(payloads) == r['payload_count'] and sum(p['bytes'] for p in payloads.values()) == r['payload_bytes']
original = read('original-records.json')
for name, pin in original['exact_copy_payloads'].items():
    assert payloads[name]['sha256'] == pin['original_sha256'] and payloads[name]['bytes'] == pin['bytes']
assert len(original['exact_copy_payloads']) == r['exact_copy_count']
projections = read('projections.json')['projections']
expected = {'epick_compile001':(32,[0]), 'epick_fixture001':(38,[2]),
            'exact_compile002':(41,[0]), 'exact_fixtures002':(47,[0,0,0,3]),
            'head_plane0':(78,[0])}
for name, (count, codes) in expected.items():
    phase = original['phase_records'][name]
    projected = projections[name]
    assert len(phase['input_sha256']) == count and phase['all_inputs_unchanged']
    assert projected['original_summary_sha256'] == phase['original_summary_sha256']
    assert [job['native_returncode'] for job in projected['jobs']] == codes
    for job in projected['jobs']:
        assert job['attach_reaped'] and job['owned_container_removed'] and not job['cleanup_errors'] and job['error'] is None
        assert not job['terminal_state']['Running'] and not job['terminal_state']['OOMKilled']
        assert job['terminal_state']['ExitCode'] == job['native_returncode']
        assert job['image_id'] == 'sha256:57c6b17ed0bd093a61a3d3cecb7563e912caeb3832fd59e8cec2d4d9d4d1e2f8'
        assert job['controls']['NetworkMode'] == 'none' and job['controls']['ReadonlyRootfs'] is True
        assert job['controls']['MemorySwap'] == job['controls']['Memory']
        assert math.isfinite(job['wall_seconds']) and 0 < job['wall_seconds'] <= (300 if 'compile' in name or name=='head_plane0' else 60)
first = read('reviews/first-failure-root.json')
assert first['actual_returncode'] == 2 and first['candidate_and_identity_outputs_absent']
assert first['diagnostic_does_not_disambiguate_nonfinite_from_below_plane']
assert first['unrun_cases'] == ['through-hole','above-noop','empty-refusal']
fixtures = read('assessments/epeck002/summary.json')
assert fixtures['all_four_literal_checks_passed'] and fixtures['assessor_sha256'] == r['paired_assessor_sha256']
for case, volume, cap, vertices, faces in [('cube-cut','1755904','23104',13,22),('through-hole','12','12',24,48),('above-noop','3511808','0',9,14)]:
    a = read('assessments/epeck002/'+case+'.json')
    assert (a['exact_signed_volume_mm3'],a['exact_cap_area_mm2'],a['vertices'],a['faces']) == (volume,cap,vertices,faces)
    assert a['literal_software_geometry_only'] and a['head_or_physical_admission'] is False
    assert a['complete_output_sha256'] == {n:payloads['results/epeck002/'+case+'/'+n]['sha256'] for n in ('candidate.bin','input-point-ids.u64','report.json')}
assert read('assessments/epeck002/empty-refusal.json')['report_only_empty_refusal']
head = read('results/head-plane0/report.json')
assert head == read('reviews/head-root.json')['native_surface_report']
assert (head['output_vertices'],head['output_faces'],head['constructed_on_plane_coordinates']) == (869355,1739126,3508)
assert head['surface_faces_below_2_over_29'] == 3112 and 0 < head['minimum_surface_quality'] < 2/29
assert head['surface_quality_screen_passed'] is head['head_surface_admitted'] is head['volume_mesh_admitted'] is False
assert head['exact_construction_clip'] is True and head['final_binary64_embedding_exact'] is False
assert read('reviews/head-root.json')['independent_complete_head_array_topology_intersection_feature_distance_checks_completed'] is False
assert read('reviews/head-root.json')['HXT_or_head_PDE_invocations'] == 0
assert not any(n.startswith('results/head-plane0/') and n != 'results/head-plane0/report.json' for n in payloads)
assert r['head_surface_admitted'] is r['volume_mesh_admitted'] is r['physics_validated'] is r['manufacturing_authorized'] is False
print(json.dumps(dict(status='sealed_bytes_and_retained_scalar_checks_passed',payloads=len(payloads),scientific_queries=0,head_admitted=False)))
