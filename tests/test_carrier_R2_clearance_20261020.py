"""Independent replay of the R2 edit chain and dual geometric separators."""
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/picogk-R2-study'
REPORT=ROOT/'docs/reports/carrier-resume-20261020/evidence'


class R2ClearanceTests(unittest.TestCase):
    def test_unchanged_face_roster_and_both_exact_vertex_edit_chains(self):
        pad=json.loads((REPORT/'picogk-R2-pad-restoration-001/assessment.json').read_text())
        cap=json.loads((REPORT/'picogk-R2-tool-facet-cap-001/assessment.json').read_text())
        def ledger(name):
            with gzip.open(SOURCE/name,'rt')as stream:rows=json.load(stream)
            result={r['vertex']:r for r in rows};self.assertEqual(len(result),len(rows));return result
        pads=ledger('pad-changed-vertices.json.gz');caps=ledger('cap-changed-vertices.json.gz')
        before_pad=hashlib.sha256();before_cap=hashlib.sha256();after=hashlib.sha256();maximum_pad=Q(0);maximum_cap=Q(0)
        def line(values):return(' '.join(format(x,'.17g')for x in values)+'\n').encode()
        with gzip.open(SOURCE/'surface.mesh64.gz','rb')as stream:
            header=stream.readline();nv,nf=map(int,header.split())
            for h in [before_pad,before_cap,after]:h.update(header)
            for index in range(nv):
                raw=stream.readline();after.update(raw);original=raw;values=None
                if index in caps:
                    row=caps[index];values=list(map(float,raw.split()));self.assertEqual(values[2],4.);self.assertEqual(row['after_Z_mm'],4.)
                    cost=Q(row['before_Z_mm'])-4;self.assertGreater(cost,0);self.assertEqual(cost,Q(row['exact_L1_mm']));maximum_cap=max(maximum_cap,cost)
                    values[2]=row['before_Z_mm'];original=line(values)
                before_cap.update(original)
                if index in pads:
                    row=pads[index];values=list(map(float,original.split()));self.assertEqual(values[2],row['after_Z_mm'])
                    cost=abs(Q(values[2])-Q(row['before_Z_mm']));self.assertEqual(cost,Q(row['exact_L1_mm']));maximum_pad=max(maximum_pad,cost)
                    values[2]=row['before_Z_mm'];original=line(values)
                before_pad.update(original)
            count=0
            for raw in stream:
                count+=1
                for h in [before_pad,before_cap,after]:h.update(raw)
        self.assertEqual(count,nf)
        self.assertEqual(after.hexdigest(),cap['output_sha256'])
        self.assertEqual(before_cap.hexdigest(),cap['source_mesh_sha256'])
        self.assertEqual(before_cap.hexdigest(),pad['output_sha256'])
        self.assertEqual(before_pad.hexdigest(),pad['source_sha256'])
        self.assertEqual(maximum_pad,Q(pad['exact_complete_edit_L1_bound_mm']))
        self.assertEqual(maximum_cap,Q(cap['maximum_exact_design_edit_L1_mm']))
        self.assertFalse(cap['tessellation_error_budget_changed'])

    def test_complete_facets_have_exact_dual_circle_separators(self):
        proof=json.loads((REPORT/'picogk-R2-capped-open-tool-certificate-001/assessment.json').read_text())
        tables=[{row['triangle']:row for row in col['facets']}for col in proof['columns']];seen=[set()for _ in tables]
        radius2=Q(625,4)
        with gzip.open(SOURCE/'surface.mesh64.gz','rt')as stream:
            nv,nf=map(int,stream.readline().split());vertices=[tuple(map(float,stream.readline().split()))for _ in range(nv)]
            self.assertLess(max(p[2]for p in vertices),40)
            count=0
            for index,raw in enumerate(stream):
                count+=1;tri=[vertices[int(i)]for i in raw.split()]
                if all(p[2]<=4 for p in tri):continue
                for k,(cx,cy)in enumerate([(-50,-20),(-50,20),(50,-20),(50,20)]):
                    if any(all(p[axis]<=c-12.5 for p in tri)or all(p[axis]>=c+12.5 for p in tri)for axis,c in [(0,cx),(1,cy)]):continue
                    seen[k].add(index);row=tables[k][index];points=[tuple(Q(x)for x in p)for p in row['clipped_polygon_xyz_Q']]
                    source=[tuple(Q(x)for x in p)for p in tri];expected={p for p in source if p[2]>=4}
                    for i,j in [(0,1),(1,2),(2,0)]:
                        p,q=source[i],source[j]
                        if (p[2]-4)*(q[2]-4)<0:
                            expected.add(tuple(((q[2]-4)*p[d]-(p[2]-4)*q[d])/(q[2]-p[2])for d in range(3)))
                    self.assertEqual(set(points),expected)
                    polygon=[(p[0]-cx,p[1]-cy)for p in points];normals=list(polygon)
                    # A feasible dual half-plane proves separation of the whole
                    # convex polygon. No sampled point or declared primal minimum is trusted.
                    for i,p in enumerate(polygon):
                        for q in polygon[i+1:]:
                            u=[q[d]-p[d]for d in range(2)];norm=sum(x*x for x in u)
                            if norm:
                                t=max(Q(0),min(Q(1),-sum(p[d]*u[d]for d in range(2))/norm));normals.append(tuple(p[d]+t*u[d]for d in range(2)))
                    def separates(n):
                        norm=sum(x*x for x in n)
                        if not norm:return False
                        minimum=min(sum(n[d]*p[d]for d in range(2))for p in polygon)
                        return minimum>=0 and minimum*minimum>=radius2*norm
                    self.assertTrue(any(separates(n)for n in normals))
        self.assertEqual(count,nf)
        self.assertEqual(seen,[set(table)for table in tables])
        self.assertEqual(proof['status'],'complete_open_tool_column_exclusion_passed')

    def test_independent_exact_surface_and_cell_volume_sums_agree(self):
        surface=json.loads((REPORT/'picogk-R2-exact-mass-001/assessment.json').read_text())
        volume=json.loads((REPORT/'picogk-R2-exact-volume-audit-001/assessment.json').read_text())
        identity=json.loads((REPORT/'picogk-R2-tetgen-outward-001/assessment.json').read_text())
        audit=json.loads((REPORT/'picogk-R2-capped-surface-audit-001/assessment.json').read_text())
        self.assertEqual(surface['source_mesh_sha256'],audit['source_mesh_sha256'])
        self.assertEqual(volume['status'],'full_exact_orientation_and_indexed_volume_screens_passed')
        self.assertEqual(identity['status'],'exact_boundary_bijection_and_outward_winding_passed')
        self.assertTrue(identity['volume_arrays_byte_identical'])
        self.assertEqual(identity['output_sha256']['boundary.mesh64'],surface['source_mesh_sha256'])
        self.assertEqual(volume['source_sha256']['work/carrier-resume-20261020/picogk-R2-tetgen-quality-001/output/volume.npz'],identity['source_sha256']['work/carrier-resume-20261020/picogk-R2-tetgen-quality-001/output/volume.npz'])
        # Integer surface determinants and per-cell Fraction determinants are
        # independent accumulations on different representations of this body.
        exact=Q(surface['exact_volume_mm3'])
        self.assertEqual(exact,Q(volume['exact_orientation']['total_signed_volume_mm3']))
        self.assertEqual(volume['exact_orientation']['negative'],0)
        self.assertEqual(volume['exact_orientation']['zero'],0)
        mass=exact*Q(4420,10**9)
        self.assertEqual(mass,Q(surface['exact_nominal_dense_mass_kg']))
        self.assertLessEqual(mass,Q(13,10))


if __name__=='__main__':unittest.main()
