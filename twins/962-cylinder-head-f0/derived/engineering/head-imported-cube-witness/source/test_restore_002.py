"""Prepared unrun pure-byte literal tests; no Gmsh or solver calls."""
import json
from pathlib import Path
import unittest
import restore_tags as M

ROOT=Path(__file__).resolve().parents[3]
REFERENCE=ROOT/'work/962-engineering/head-imported-cube-witness-prep-001/cube-reference.json'


class IntegerTags(unittest.TestCase):
    def literal(self):
        r=json.loads(REFERENCE.read_text());index={tag:i+1 for i,tag in enumerate(r['node_tags'])}
        lines=['$MeshFormat','2.2 0 8','$EndMeshFormat','$PhysicalNames','2','2 11 "all_boundary"','3 21 "solid"','$EndPhysicalNames','$Nodes','9']
        lines += [' '.join([str(i+1)]+list(map(str,p))) for i,p in enumerate(r['coordinates_mm'])]
        lines += ['$EndNodes','$Elements','24']
        for i,row in enumerate(r['outward_triangles_node_tags']):lines.append(' '.join(map(str,[i+1,2,2,11,1]+[index[v] for v in row])))
        for i,row in enumerate(r['positive_tetrahedra_node_tags']):lines.append(' '.join(map(str,[i+13,4,2,21,1]+[index[v] for v in row])))
        lines.append('$EndElements')
        return '\n'.join(lines)+'\n',r

    def test_exact_all_integer_tags_and_coordinate_words(self):
        source,r=self.literal();result,nodes,elements=M.restore(source,r)
        self.assertTrue(M.verify(source,result,nodes,elements,r))
        self.assertEqual(nodes,dict(zip(range(1,10),r['node_tags'])))
        self.assertEqual(elements,dict(zip(range(1,25),r['triangle_tags']+r['tetrahedron_tags'])))
        self.assertIn('201 0 0 0\n',result);self.assertIn('2001 4 2 21 1 201 101 103 102\n',result)
        with self.assertRaisesRegex(ValueError,'Coordinate words'):M.verify(source,result.replace('201 0 0 0','201 0.0 0 0'),nodes,elements,r)

    def test_duplicate_coordinate_reversed_tetra_and_wrong_physical_refused(self):
        source,r=self.literal()
        for text in [source.replace('2 1 -1 -1','2 -1 -1 -1'),source.replace('13 4 2 21 1 9 1 3 2','13 4 2 21 1 9 3 1 2'),source.replace('2 11 "all_boundary"','2 12 "all_boundary"')]:
            with self.assertRaises(ValueError):M.restore(text,r)


if __name__=='__main__':unittest.main()
