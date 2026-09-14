import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/subdivide_low_degree_tetrahedra.py'
spec=importlib.util.spec_from_file_location('central_tet_subdivision',PATH)
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)


def fixture(neighbors=0,crlf=False):
    """Un tétraèdre central et jusqu'à quatre voisins, sans liste de défauts."""
    coordinates={1:(0,0,0),2:(1,0,0),3:(0,1,0),4:(0,0,1),
        5:(1,1,1),6:(-1,0,0),7:(0,-1,0),8:(0,0,-1)}
    cells=[(1,2,3,4)]
    for i in range(neighbors):
        cell=list(cells[0]);cell[i]=5+i
        if trial.determinant([coordinates[n] for n in cell])<0:cell[0],cell[1]=cell[1],cell[0]
        cells.append(tuple(cell))
    used={n for cell in cells for n in cell};surface={}
    for cell in cells:
        for face in trial.outward_faces(cell):
            key=tuple(sorted(face))
            if key in surface:del surface[key]
            else:surface[key]=face
    rows=[]
    for i,face in enumerate(surface.values(),10):rows.append(f'{i} 2 2 1 {i} '+' '.join(map(str,face)))
    for i,cell in enumerate(cells,100):rows.append(f'  {i}\t4 3  8  1 -2\t'+' '.join(map(str,cell)))
    nodes=[]
    for n in sorted(used):
        nodes.append('  1\t0.000000  0.0e+00\t0' if n==1 else f'{n} '+' '.join(map(str,coordinates[n])))
    text=('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n2\n2 1 "wall"\n3 8 "gas"\n$EndPhysicalNames\n'
        '$Nodes\n'+str(len(nodes))+'\n'+'\n'.join(nodes)+'\n$EndNodes\n'
        '$Elements\n'+str(len(rows))+'\n'+'\n'.join(rows)+'\n$EndElements\n'
        '$Comments\nFixture only; no manufacturing claim\n$EndComments\n')
    return text.replace('\n','\r\n').encode() if crlf else text.encode()


class TetrahedralStarSubdivisionTests(unittest.TestCase):
    def test_single_tetrahedron_has_four_positive_exact_quarter_children(self):
        source=fixture();candidate,report=trial.subdivide_mesh(source)
        self.assertEqual(report['selection']['selected_tetrahedra'],1)
        self.assertEqual(report['selection']['output_tetrahedra'],4)
        self.assertEqual(report['volume_proof']['verified_child_count'],4)
        self.assertTrue(all(report['gates'].values()))
        self.assertEqual(report['volume_proof']['binary64_input_volume'],report['volume_proof']['binary64_output_volume'])
        before=trial.read_mesh(source);after=trial.read_mesh(candidate);row=report['parent_children_private'][0]
        self.assertEqual(after['nodes'][row['centroid_node_id']].xyz,(.25,.25,.25))
        for node,value in before['nodes'].items():self.assertEqual(after['nodes'][node].raw,value.raw)

    def test_selection_uses_full_adjacency_degree_zero_through_four(self):
        for neighbors in range(5):
            with self.subTest(neighbors=neighbors):
                source=fixture(neighbors);candidate,report=trial.subdivide_mesh(source)
                selected={r['parent_element_id']:r['internal_face_count'] for r in report['parent_children_private']}
                self.assertEqual(100 in selected,neighbors<=2)
                if neighbors<=2:self.assertEqual(selected[100],neighbors)
                self.assertEqual(set(selected)-{100},set(range(101,101+neighbors)))
                self.assertTrue(all(v==1 for k,v in selected.items() if k!=100))
                if neighbors>=3:
                    self.assertEqual(trial.read_mesh(source)['elements'][100].raw,trial.read_mesh(candidate)['elements'][100].raw)
                self.assertTrue(report['gates']['oriented_exterior_boundary_exactly_preserved'])

    def test_existing_crlf_nodes_and_untargeted_sections_and_elements_byte_exact(self):
        source=fixture(4,crlf=True);candidate,report=trial.subdivide_mesh(source)
        before=trial.read_mesh(source);after=trial.read_mesh(candidate)
        selected={r['parent_element_id'] for r in report['parent_children_private']}
        for i,n in before['nodes'].items():self.assertEqual(after['nodes'][i].raw,n.raw)
        for i,e in before['elements'].items():
            if i not in selected:self.assertEqual(after['elements'][i].raw,e.raw)
        for name in (b'$MeshFormat',b'$PhysicalNames',b'$Comments'):
            a,b=before['sections'][name];c,d=after['sections'][name]
            self.assertEqual(before['lines'][a:b+1],after['lines'][c:d+1])

    def test_new_tags_unique_and_physical_entity_partition_tags_inherited(self):
        source=fixture(4);candidate,report=trial.subdivide_mesh(source)
        before=trial.read_mesh(source);after=trial.read_mesh(candidate)
        for row in report['parent_children_private']:
            parent=before['elements'][row['parent_element_id']]
            self.assertNotIn(parent.id,after['elements'])
            self.assertEqual(len(set(row['child_element_ids'])),4)
            self.assertNotIn(row['centroid_node_id'],before['nodes'])
            for cid in row['child_element_ids']:
                self.assertNotIn(cid,before['elements']);self.assertEqual(after['elements'][cid].tags,parent.tags)

    def test_exact_decimal_handles_exponents_without_binary64_rounding(self):
        for value in (Fraction('1e-20'),Fraction('-1234567.00001'),Fraction(1,8),Fraction(1,20),Fraction(0)):
            self.assertEqual(Fraction(trial.exact_decimal(value).decode()),value)
        with self.assertRaises(ValueError):trial.exact_decimal(Fraction(1,3))
        points=[tuple(Fraction(v) for v in p) for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1))]
        self.assertEqual(trial.quarter_children(points,(Fraction(1,4),)*3),1)
        with self.assertRaises(ValueError):trial.quarter_children(points,(Fraction(1,5),)*3)

    def test_negative_degenerate_nonmanifold_and_missing_boundary_rejected(self):
        source=fixture()
        bads=[source.replace(b'1 2 3 4\n',b'1 3 2 4\n'),
            source.replace(b'4 0 0 1\n',b'4 0 0 0\n'),
            source.replace(b'$Elements\n5\n',b'$Elements\n6\n').replace(b'$EndElements',b'101 4 2 8 1 1 2 3 4\n$EndElements'),
            source.replace(b'10 2 2 1 10 1 3 2\n',b'10 1 2 1 10 1 3\n')]
        for bad in bads:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):trial.subdivide_mesh(bad)

    def test_malformed_counts_nodes_and_semantic_data_sections_rejected(self):
        source=fixture()
        bads=[source.replace(b'$Nodes\n4\n',b'$Nodes\n5\n'),
            source.replace(b'4 0 0 1\n',b'4 nan 0 1\n'),
            source.replace(b'4 0 0 1\n',b'3 0 0 1\n'),
            source+b'$ElementData\n0\n$EndElementData\n',
            source+b'$Periodic\n0\n$EndPeriodic\n',
            source.replace(b'2.2 0 8',b'4.1 0 8')]
        for bad in bads:
            with self.assertRaises(ValueError):trial.subdivide_mesh(bad)

    def test_production_pin_and_fresh_private_output_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.msh';source.write_bytes(fixture())
            args=argparse.Namespace(source_mesh=source,output_mesh=root/'candidate.msh',report=root/'report.json')
            with self.assertRaisesRegex(ValueError,'exact_source_mesh_sha256'):trial.run(args)
            self.assertFalse(args.output_mesh.exists());self.assertFalse(args.report.exists())
            with patch.object(trial,'SOURCE_MESH_SHA256',trial.sha(source.read_bytes())):
                self.assertEqual(trial.run(args),0)
                receipt=json.loads(args.report.read_text())
                self.assertEqual(receipt['candidate_mesh_sha256'],trial.sha(args.output_mesh.read_bytes()))
                self.assertFalse(receipt['CFD_qualified']);self.assertFalse(receipt['OpenFOAM_checks_executed'])
                self.assertEqual(args.output_mesh.stat().st_mode&0o777,0o600)
                before=args.output_mesh.read_bytes()
                with self.assertRaisesRegex(ValueError,'new_distinct_output_files'):trial.run(args)
                self.assertEqual(before,args.output_mesh.read_bytes())


if __name__=='__main__':unittest.main()
