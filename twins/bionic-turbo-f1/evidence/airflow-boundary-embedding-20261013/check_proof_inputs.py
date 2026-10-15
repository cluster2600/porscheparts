"""Bind established receipts to the written proof; not a theorem prover."""
import hashlib
import json
from pathlib import Path

W = Path('work/bionic-boundary-embedding-20261013')
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
paths = [W / n for n in ('preflight.md', 'proof.md', 'source-references.json',
    'readback.json', 'independent-readback.json', 'gluing-readback.json', 'dependencies.json')]
paths += [Path('work/bionic-parametric-boundary-20261013') / n
          for n in ('proof.md', 'readback.json', 'independent-readback-v2.json')]
paths += [Path('work/bionic-volume-representation-20261013') / n
          for n in ('readback.json', 'independent-readback.json')]
read = lambda p: json.loads(p.read_text())
a, b, g = [read(W / n) for n in ('readback.json', 'independent-readback.json', 'gluing-readback.json')]
c = read(paths[-4]); ci = read(paths[-3]); v = read(paths[-2]); vi = read(paths[-1])
assert all(r['domain_v'] == a['domain_v'] for r in (b, g, c, ci, v, vi))
assert sha(W/'check_embedding.py') == a['source_sha256']
assert sha(W/'verify_embedding.py') == b['source_sha256']
assert sha(W/'verify_gluing.py') == g['source_sha256']
assert b['primary_readback_sha256'] == g['primary_readback_sha256'] == sha(W/'readback.json')
assert g['independent_readback_sha256'] == sha(W/'independent-readback.json')
assert ci['primary_readback_sha256'] == sha(paths[-4])
assert c['proof_sha256'] == sha(paths[-5])
assert g['inherited_verification_sha256'] == sha(paths[-1])
assert a['exact_pairs_checked'] + a['strict_bbox_separations'] == a['total_pairs']
assert b['exact_candidates_verified'] == a['exact_pairs_checked'] == 59462
assert b['all_intersections_equal_common_simplex'] and b['cap_contacts_verified']
assert a['boundary_connected'] and b['closed_connected_oriented_boundary_links_verified'] == 8960
assert c['cap_triangle_coverage_proved'] and ci['cap_coverage_hypotheses_verified']
assert g['lateral_links_are_paths_or_cycles']
assert g['tetrahedron_boundary_equals_global_fan_chain']
assert g['tetrahedra_positive_bounds_inherited'] == 119808
assert g['external_triangles'] == a['boundary_triangles'] == 17920
out = {'source_sha256': sha(Path(__file__)), 'inputs': {str(p): sha(p) for p in paths},
       'domain_v': a['domain_v'], 'input_consistency_passed': True,
       'role': 'structural binding of verified hypotheses to proof.md; not another geometric reconstruction or automated theorem proof',
       'proof_conclusion': 'boundary index one and closed coverage with disjoint tetrahedron/cell interiors in the prescribed fan representation',
       'all_internal_lower_dimensional_contacts_classified': False,
       'native_admission': False, 'new_ratio_point': False}
(W/'proof-input-readback.json').write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps(out))
