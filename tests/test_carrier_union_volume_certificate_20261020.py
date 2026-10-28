"""Replay actual coordinate edits and bind the published volume checkpoint."""
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'
REPORT=ROOT/'docs/reports/carrier-resume-20261020/evidence'


def read(case):
    return json.loads((REPORT/case/'assessment.json').read_text())


class UnionVolumeCertificateTests(unittest.TestCase):
    def test_vertex_moves_reconstruct_the_actual_prior_mesh_and_bound(self):
        proof=read('union-bounded-vertex-quality-001')
        raw=gzip.decompress((SOURCE/'carrier-union-bounded.mesh64.gz').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),proof['output_sha256'])
        lines=raw.splitlines(keepends=True)
        maximum=F(0)
        for step in reversed(proof['steps']):
            i=step['vertex']+1
            self.assertEqual(tuple(map(float,lines[i].split())),tuple(step['new_point_mm']))
            maximum=max(maximum,sum(abs(F(x)-F(y))for x,y in zip(step['new_point_mm'],step['old_point_mm'])))
            lines[i]=(' '.join(format(x,'.17g')for x in step['old_point_mm'])+'\n').encode()
        self.assertEqual(hashlib.sha256(b''.join(lines)).hexdigest(),proof['source_mesh_sha256'])
        self.assertEqual(maximum,F(proof['maximum_vertex_L1_displacement_mm']))
        total=F(proof['prior_bound_mm'])+maximum
        self.assertEqual(total,F(proof['complete_exact_master_L1_bound_mm']))
        self.assertLessEqual(total,F(.06))

    def test_complete_surface_audit_is_bound_to_published_geometry(self):
        proof=read('union-bounded-vertex-quality-001')
        audit=read('union-bounded-quality-surface-audit-001')
        self.assertEqual(audit['source_mesh_sha256'],proof['output_sha256'])
        self.assertEqual(audit['status'],'complete_surface_screen_passed')
        self.assertEqual(audit['retained_needle_ratio_threshold'],.001)
        self.assertEqual(audit['self_intersection_pairs'],0)
        self.assertEqual(audit['topology']['triangles'],603152)
        self.assertTrue(all(audit['topology'][k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_orientation_edges','degenerate_triangles','needle_triangles']))

    def test_tetgen_volume_and_exact_audit_are_bound_through_winding_only(self):
        mesh=read('tetgen-preserved-boundary-001')
        oriented=read('tetgen-outward-boundary-001')
        exact=read('tetgen-exact-volume-audit-001')
        self.assertTrue(mesh['exact_input_boundary_identity'])
        self.assertEqual(mesh['source_sha256'],read('union-bounded-vertex-quality-001')['output_sha256'])
        self.assertIn(mesh['output_sha256']['volume.npz'],oriented['source_sha256'].values())
        self.assertIn(mesh['output_sha256']['volume.npz'],exact['source_sha256'].values())
        self.assertTrue(oriented['volume_arrays_byte_identical'])
        self.assertEqual(oriented['raw_reversed_winding_faces'],603152)
        self.assertEqual(hashlib.sha256((SOURCE/'tetgen-volume-outward.npz').read_bytes()).hexdigest(),oriented['output_sha256']['volume.npz'])
        self.assertEqual(oriented['output_sha256']['boundary.mesh64'],mesh['source_sha256'])
        self.assertEqual(exact['exact_orientation']['tetrahedra'],927734)
        self.assertEqual(exact['exact_orientation']['negative'],0)
        self.assertEqual(exact['exact_orientation']['zero'],0)
        self.assertTrue(exact['indexed_connectivity']['boundary_matches'])
        self.assertFalse(mesh['mechanical_mesh_admitted'])

    def test_refined_volume_keeps_the_same_audited_skin_and_exact_positive_cells(self):
        mesh=read('tetgen-boundary-quality-001')
        oriented=read('tetgen-refined-outward-boundary-001')
        exact=read('tetgen-refined-exact-volume-audit-001')
        self.assertTrue(mesh['exact_input_boundary_identity'])
        self.assertEqual(oriented['output_sha256']['boundary.mesh64'],read('union-bounded-vertex-quality-001')['output_sha256'])
        self.assertIn(mesh['output_sha256']['volume.npz'],oriented['source_sha256'].values())
        self.assertIn(mesh['output_sha256']['volume.npz'],exact['source_sha256'].values())
        self.assertTrue(oriented['volume_arrays_byte_identical'])
        self.assertEqual(hashlib.sha256((SOURCE/'tetgen-volume-refined-outward.npz').read_bytes()).hexdigest(),oriented['output_sha256']['volume.npz'])
        self.assertEqual(exact['exact_orientation']['tetrahedra'],1163760)
        self.assertEqual(exact['exact_orientation']['negative'],0)
        self.assertEqual(exact['exact_orientation']['zero'],0)
        self.assertTrue(exact['indexed_connectivity']['boundary_matches'])
