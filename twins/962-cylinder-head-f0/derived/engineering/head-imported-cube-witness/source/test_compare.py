"""Prepared unrun stdlib comparator tests; no SciPy/Exodus/native invocation."""
import json
from pathlib import Path
import unittest
import compare_cube as check

ROOT=Path(__file__).resolve().parents[3]
REFERENCE=ROOT/'work/962-engineering/head-imported-cube-witness-prep-001/cube-reference.json'
PRIMARY=ROOT/'work/962-engineering/head-imported-cube-exodus-primary-source-001/ex_get_side_set_node_list.c'
PRIMARY_SHA='9cedc3c636874dddd4c750ce2a4acd0250eb9b981c5c471630944803a5549047'


class CubeReadback(unittest.TestCase):
    def literal(self):
        r=json.loads(REFERENCE.read_text());table=check.side_table_from_primary(PRIMARY,PRIMARY_SHA)
        order=list(range(3,9))+list(range(3));coords=[r['coordinates_mm'][i] for i in order]
        index={tuple(p):i+1 for i,p in enumerate(coords)};by_tag=dict(zip(r['node_tags'],map(tuple,r['coordinates_mm'])))
        cells=[[index[by_tag[v]] for v in row] for row in r['positive_tetrahedra_node_tags']]
        boundary_side=next(k for k,row in table.items() if check.oriented(row)==check.oriented([1,2,3]))
        w=[.25 if p==[0,0,0] else 0. for p in coords]
        rows=[dict(id=str(77+5*i),x=str(p[0]),y=str(p[1]),z=str(p[2]),w=str(w[i])) for i,p in enumerate(coords)]
        return r,table,coords,cells,list(range(1,13)),[boundary_side]*12,w,list(reversed(rows))

    def test_complete_reindexed_cells_boundary_and_field(self):
        r,t,p,e,se,ss,w,rows=self.literal();result=check.compare(p,e,se,ss,t,w,rows,r)
        self.assertEqual(result['count_one_boundary_faces'],12);self.assertEqual(result['total_tetrahedral_volume_mm3'],8)
        self.assertTrue(result['sideset11_complete']);self.assertFalse(result['row_equals_original_Gmsh_or_PETSc_ID_assumed'])

    def test_reversed_duplicate_and_incomplete_sideset_refused(self):
        r,t,p,e,se,ss,w,rows=self.literal()
        reversed_cells=[v.copy() for v in e];reversed_cells[0][0],reversed_cells[0][1]=reversed_cells[0][1],reversed_cells[0][0]
        with self.assertRaisesRegex(ValueError,'Jacobians'):check.compare(p,reversed_cells,se,ss,t,w,rows,r)
        duplicate=[v.copy() for v in e];duplicate[-1]=duplicate[0].copy()
        with self.assertRaisesRegex(ValueError,'duplicates'):check.compare(p,duplicate,se,ss,t,w,rows,r)
        bad=ss.copy();bad[0]=next(v for v in t if v!=ss[0])
        with self.assertRaisesRegex(ValueError,'Sideset'):check.compare(p,e,se,bad,t,w,rows,r)
        with self.assertRaises(ValueError):check.compare(p,e,se[:-1],ss[:-1],t,w,rows,r)

    def test_bad_primary_and_missing_or_nonfinite_field_refused(self):
        r,t,p,e,se,ss,w,rows=self.literal()
        with self.assertRaisesRegex(ValueError,'primary source'):check.side_table_from_primary(PRIMARY,'0'*64)
        with self.assertRaisesRegex(ValueError,'nine-node'):check.compare(p,e,se,ss,t,w,rows[:-1],r)
        bad=w.copy();bad[0]=float('nan')
        with self.assertRaisesRegex(ValueError,'Finite'):check.compare(p,e,se,ss,t,bad,rows,r)
        with self.assertRaisesRegex(ValueError,'side map'):check.compare(p,e,se,ss,{},w,rows,r)


if __name__=='__main__':unittest.main()
