"""Independent replay of the published complete edit and tool-column witness."""
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'
REPORT=ROOT/'docs/reports/carrier-resume-20261020/evidence'


class PublishedDatumTests(unittest.TestCase):
    def test_complete_vertex_map_reconstructs_both_hashed_surfaces(self):
        report=json.loads((REPORT/'picogk-pad-datum-restoration-002/assessment.json').read_text())
        with gzip.open(SOURCE/'picogk-restored-study/changed-vertices.json.gz','rt')as stream:rows=json.load(stream)
        self.assertEqual(len(rows),report['changed_vertices'])
        ledger={r['vertex']:r for r in rows}
        self.assertEqual(len(ledger),len(rows))
        before=hashlib.sha256();after=hashlib.sha256();maximum=Q(0)
        with gzip.open(SOURCE/'picogk-restored-study/surface.mesh64.gz','rb')as stream:
            header=stream.readline();before.update(header);after.update(header);nv,nf=map(int,header.split())
            for index in range(nv):
                line=stream.readline();after.update(line)
                if index in ledger:
                    row=ledger[index];values=list(map(float,line.split()))
                    self.assertEqual(values[2],row['after_Z_mm'])
                    cost=abs(Q(values[2])-Q(row['before_Z_mm']))
                    self.assertEqual(cost,Q(row['exact_L1_mm']));maximum=max(maximum,cost)
                    values[2]=row['before_Z_mm'];line=(' '.join(format(x,'.17g')for x in values)+'\n').encode()
                before.update(line)
            count=0
            for line in stream:count+=1;before.update(line);after.update(line)
        self.assertEqual(count,nf)
        self.assertEqual(before.hexdigest(),report['source_sha256'])
        self.assertEqual(after.hexdigest(),report['output_sha256'])
        self.assertEqual(maximum,Q(report['exact_complete_edit_L1_bound_mm']))
        self.assertLessEqual(maximum,Q(3,50))

    def test_every_above_plane_facet_is_separated_from_all_four_columns(self):
        proof=json.loads((REPORT/'picogk-open-tool-certificate-001/assessment.json').read_text())
        audit=json.loads((REPORT/'picogk-pad-datum-surface-audit-002/assessment.json').read_text())
        self.assertEqual(proof['source_mesh_sha256'],audit['source_mesh_sha256'])
        self.assertEqual(audit['status'],'complete_surface_screen_passed')
        self.assertEqual(proof['radius_mm'],12.5)
        self.assertEqual(proof['open_Z_interval_mm'],[4,40])
        with gzip.open(SOURCE/'picogk-restored-study/surface.mesh64.gz','rt')as stream:
            nv,nf=map(int,stream.readline().split());vertices=[tuple(map(float,stream.readline().split()))for _ in range(nv)]
            self.assertLess(max(v[2]for v in vertices),40)
            count=0
            for line in stream:
                count+=1;triangle=[vertices[int(i)]for i in line.split()]
                if all(p[2]<=4 for p in triangle):continue
                # Independently replay a stronger interval-separation witness.
                for cx,cy in [(-50,-20),(-50,20),(50,-20),(50,20)]:
                    separated=any(all(p[axis]<=centre-12.5 for p in triangle)or all(p[axis]>=centre+12.5 for p in triangle)for axis,centre in [(0,cx),(1,cy)])
                    self.assertTrue(separated)
        self.assertEqual(count,nf)
        self.assertEqual(proof['status'],'complete_open_tool_column_exclusion_passed')
        self.assertTrue(all(column['exactly_checked_facets']==0 for column in proof['columns']))
        self.assertFalse(proof['original_closed_set_empty_test_reclassified'])


if __name__=='__main__':unittest.main()
