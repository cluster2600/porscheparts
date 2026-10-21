"""Replay the saved contraction proof against every actual source/output facet."""
from fractions import Fraction as F
import hashlib
import gzip
import json
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'
REPORT=ROOT/'docs/reports/carrier-resume-20261020'


def triangles(path):
    raw=path.read_bytes();n=struct.unpack_from('<I',raw,80)[0]
    if len(raw)!=84+50*n:raise ValueError('Binary STL length differs')
    return [tuple(tuple(struct.unpack_from('<3f',raw,84+50*i+12+12*j))for j in range(3))for i in range(n)]


class CertifiedPatchReplayTests(unittest.TestCase):
    def test_every_contraction_cost_and_final_triangle_image_replays_exactly(self):
        proof=json.loads((REPORT/'evidence/certified-collapse-001/assessment.json').read_text())
        original=json.loads((REPORT/'evidence/bounded-tessellation-001/assessment.json').read_text())
        for i,row in enumerate(proof['patches']):
            old=SOURCE/f'inputs/bounded-patch-{i}.stl';new=SOURCE/f'inputs/certified-patch-{i}.stl'
            self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),original['patches'][i]['STL_sha256'])
            tri=triangles(old);vertices=sorted({v for t in tri for v in t});index={v:k for k,v in enumerate(vertices)}
            faces=[tuple(index[v]for v in t)for t in tri];spent=F(0)
            for step in row['steps']:
                a,b=step['retained_vertex'],step['removed_vertex'];cost=sum(abs(F(x)-F(y))for x,y in zip(vertices[a],vertices[b]));spent+=cost
                self.assertEqual(cost,F(step['L1_displacement_mm']));self.assertEqual(spent,F(step['accumulated_L1_bound_mm']))
                faces=[tuple(a if v==b else v for v in t)for t in faces]
                degenerate=[k for k,t in enumerate(faces)if len(set(t))<3]
                self.assertEqual(degenerate,step['redundant_image_coverage']['removed_source_triangle_indices'])
                kept=[t for t in faces if len(set(t))==3];edges={tuple(sorted((t[j],t[(j+1)%3])))for t in kept for j in range(3)}
                for k in degenerate:
                    for x in faces[k]:
                        for y in faces[k]:
                            if x!=y:self.assertIn(tuple(sorted((x,y))),edges)
                faces=kept
            self.assertEqual([tuple(vertices[v]for v in t)for t in faces],triangles(new))
            self.assertEqual(hashlib.sha256(new.read_bytes()).hexdigest(),row['STL_sha256'])
            total=F(original['patches'][i]['maximum_complete_cell_L1_bound_mm'])+spent
            self.assertEqual(total,F(row['complete_source_to_output_L1_bound_mm']));self.assertLessEqual(total,F(.06))

    def test_every_source_cell_and_full_audit_agree_with_checkpoint(self):
        bound=json.loads((REPORT/'evidence/bounded-tessellation-001/assessment.json').read_text())
        for row in bound['patches']:
            maximum=max(F(cell['total_L1'])for cell in row['cells'])
            self.assertEqual(maximum,F(row['maximum_complete_cell_L1_bound_mm']));self.assertLessEqual(maximum,F(.06))
        audit=json.loads((REPORT/'evidence/component-libigl-certified-001/assessment.json').read_text());checkpoint=json.loads((REPORT/'checkpoint.json').read_text())
        self.assertEqual(audit['status'],'all_complete_component_surface_screens_passed')
        self.assertEqual(sum(r['topology']['triangles']for r in audit['components']),checkpoint['triangles'])
        self.assertTrue(all(not r['failures']and not r['self_intersection_pairs']for r in audit['components']))
        self.assertEqual(hashlib.sha256((SOURCE/'carrier-additive-assembly-study.3mf').read_bytes()).hexdigest(),audit['archive_sha256'])

    def test_published_native_tensor_readback_binds_exact_saved_solids(self):
        data=json.loads((REPORT/'evidence/native-tensor-readback-001/assessment.json').read_text())
        self.assertEqual(data['status'],'all_native_tensor_coefficients_exact')
        for i,row in enumerate(data['patches']):
            self.assertEqual(hashlib.sha256((SOURCE/f'inputs/patch-{i}.brep').read_bytes()).hexdigest(),row['BREP_sha256'])
            self.assertTrue(all(c['passed']for c in row['checks']))

    def test_copied_execution_evidence_has_no_byte_changes(self):
        data=json.loads((REPORT/'evidence-copy-manifest.json').read_text())
        for row in data['exact_copies']:
            with self.subTest(path=row['path']):
                raw=(ROOT/row['path']).read_bytes()
                if row.get('encoding')=='gzip':
                    self.assertEqual(hashlib.sha256(raw).hexdigest(),row['stored_sha256']);raw=gzip.decompress(raw)
                self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
