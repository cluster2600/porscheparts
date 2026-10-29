"""Build experimental G1 networks; independent embedding and distance checks remain required."""
import argparse, hashlib, json, signal, time
from pathlib import Path
import numpy as np
import manifold3d as mf
from reconstruct_core_envelopes import canonical_surface

def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--envelope-directory', type=Path, required=True)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir()
    signal.alarm(180)
    start = time.monotonic()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_sha = sha(Path(__file__))
    plan = json.loads(a.plan.read_text())
    r = json.loads((a.directory / 'assessment.json').read_text())
    er = json.loads((a.envelope_directory / 'assessment.json').read_text())
    z = np.load(a.envelope_directory / 'envelopes.npz')
    assert sha(a.envelope_directory / 'envelopes.npz') == er['output_sha256']['envelopes.npz']
    assert r['status'] in ['dominant_void_network_per_analytic_sign_retained', 'internal_void_repair_candidate_generated'] and (not r['manufacturing_authorized'])
    assert sorted((c['branch'] for c in r['selected'])) == [-1, 1]
    assert r['pitch_mm'] == plan['finite_pitch_mm'] and r['size_mm'] in plan['finite_sizes_mm']
    assert [plan['smoothing'][k] for k in ['min_sharp_angle_degrees', 'min_smoothness', 'refinement_tolerance_mm', 'geometry_cleanup_tolerance_mm', 'binary_grid_mm', 'seed_cleanup_tolerance_mm']] == [52.5, 0, 0.01, 0.001, 2 ** (-20), 0.001]
    assert plan['envelope_source_sha256'] == sha(a.envelope_directory / 'envelopes.npz')
    rank = r['rank']
    vs = sum((c['vertices'] for c in er['components'][:rank]))
    fs = sum((c['triangles'] for c in er['components'][:rank]))
    c = er['components'][rank]
    core = mf.Manifold(mf.Mesh64(np.array(z['vertices'][vs:vs + c['vertices']]), np.array(z['triangles'][fs:fs + c['triangles']] - vs, dtype=np.uint64)))
    (a.output / 'contract.json').write_text(json.dumps(dict(parameters=plan['smoothing'], input_sha256={str(p): sha(p) for p in [a.plan, a.envelope_directory / 'envelopes.npz', a.envelope_directory / 'assessment.json']}, source_sha256=source_sha, seed_assessment_sha256=sha(a.directory / 'assessment.json'), maximum_seconds=180, core_containment_must_be_empty=True, exact_oriented_triangle_roundtrip_required=True, manufacturing_authorized=False), indent=2) + '\n')
    rows = []
    for selected in r['selected']:
        path = a.directory / selected['file']
        assert sha(path) == selected['sha256']
        n = np.load(path)
        seed = mf.Manifold(mf.Mesh64(np.array(n['vertices']), np.array(n['triangles'], dtype=np.uint64)))
        s = plan['smoothing']
        seed_before_cleanup = seed.volume()
        seed = seed.as_original().simplify(s['seed_cleanup_tolerance_mm'])
        assert seed.status() == mf.Error.NoError
        candidate = seed.smooth_out(s['min_sharp_angle_degrees'], s['min_smoothness']).refine_to_tolerance(s['refinement_tolerance_mm'])
        assert candidate.status() == mf.Error.NoError
        rounded_volume = candidate.volume()
        candidate = candidate.simplify(s['geometry_cleanup_tolerance_mm'])
        cleaned_volume = candidate.volume()
        clean = candidate.to_mesh64()
        unquantized = np.array(clean.vert_properties)[:, :3]
        grid = s['binary_grid_mm']
        quantized = np.rint(unquantized / grid) * grid
        movement = float(abs(quantized - unquantized).max())
        assert movement <= grid / 2
        candidate = mf.Manifold(mf.Mesh64(quantized, np.array(clean.tri_verts, dtype=np.uint64)))
        assert candidate.status() == mf.Error.NoError
        parts = candidate.decompose()
        assert parts and all((part.volume() > 0 for part in parts))
        removed_pockets = len(parts) - 1
        before_filter = candidate.volume()
        candidate = max(parts, key=lambda part: part.volume()) if removed_pockets else candidate
        filled_volume = before_filter - candidate.volume()
        outside = candidate - core
        row = dict(post_rounding_pockets_filled=removed_pockets, post_rounding_filled_volume_mm3=filled_volume, branch=selected['branch'], seed_volume_mm3=seed_before_cleanup, seed_cleaned_volume_mm3=seed.volume(), seed_cleanup_tolerance_mm=s['seed_cleanup_tolerance_mm'], binary_grid_mm=grid, maximum_coordinate_regularization_mm=movement, raw_rounded_volume_mm3=rounded_volume, intentionally_cleaned_volume_mm3=cleaned_volume, smoothed_volume_mm3=candidate.volume(), outside_status=str(outside.status()), outside_is_empty=outside.is_empty(), outside_volume_mm3=outside.volume(), outside_triangles=outside.num_tri())
        (a.output / ('containment-' + selected['file'] + '.json')).write_text(json.dumps(row, indent=2) + '\n')
        assert outside.is_empty()
        mesh = candidate.to_mesh64()
        v = np.array(mesh.vert_properties)[:, :3]
        f = np.array(mesh.tri_verts, dtype=np.uint64)
        back = mf.Manifold(mf.Mesh64(v, f))
        b = back.to_mesh64()
        assert abs(back.volume() - candidate.volume()) / candidate.volume() <= 1e-10
        assert back.status() == mf.Error.NoError and all((np.array_equal(x, y) for (x, y) in zip(canonical_surface(v, f), canonical_surface(np.array(b.vert_properties)[:, :3], np.array(b.tri_verts, dtype=np.uint64)))))
        parts = candidate.decompose()
        assert len(parts) == 1 and parts[0].volume() > 0
        np.savez_compressed(a.output / selected['file'], vertices=v, triangles=f)
        row.update(volume_mm3=candidate.volume(), vertices=len(v), triangles=len(f), sha256=sha(a.output / selected['file']), file=selected['file'], exact_oriented_triangle_roundtrip=True)
        rows.append(row)
    report = dict(status='native_G1_smoothed_voids_transfer_and_containment_checked', rank=rank, pitch_mm=r['pitch_mm'], size_mm=r['size_mm'], core_volume_mm3=core.volume(), retained_void_volume_mm3=sum((c['volume_mm3'] for c in rows)), finite_retained_solid_fraction=1 - sum((c['volume_mm3'] for c in rows)) / core.volume(), discarded_void_pockets=r['discarded_void_pockets'], selected=rows, source_sha256=source_sha, elapsed_seconds=time.monotonic() - start, opposite_network_separation_certified=False, self_intersections_checked=False, powder_escape_demonstrated=False, manufacturing_authorized=False)
    (a.output / 'assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    signal.alarm(0)
    print(json.dumps(report))
if __name__ == '__main__':
    main()
