import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow/merge_flagged_cells.py'
spec=importlib.util.spec_from_file_location('merge_flagged',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class FlaggedMergeTests(unittest.TestCase):
    def test_internal_merge_keeps_boundary_and_refuses_boundary_removal(self):
        faces=['3(0 1 2)','3(0 3 1)','3(0 2 3)','3(1 3 2)',
               '3(0 1 4)','3(0 4 2)','3(1 2 4)']
        owners=[0,0,0,0,1,1,1]
        result=module.merged_connectivity(faces,owners,[1],{0})
        self.assertEqual(result,(faces[1:],[0]*6,[],1))
        with self.assertRaises(ValueError):module.merged_connectivity(faces,owners,[1],{1})

    def test_relabel_reverses_internal_face_and_orders_owners(self):
        faces=['3(0 1 2)','3(1 2 3)','3(2 3 4)']
        new,owners,neighbours,count=module.merged_connectivity(faces,[0,1,2],[3,2,3],{0})
        self.assertEqual((owners,neighbours,count),([0,1],[2,2],3))
        self.assertEqual(new,['3(4 3 2)','3(1 2 3)'])

    def test_ascii_reader_rejects_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'owner'
            path.write_text('FoamFile {format ascii;}\n2\n(\n0\n)\n')
            with self.assertRaises(ValueError):module.read_list(path)
            path.write_text('FoamFile {format ascii;}\n1\n(\n0\n)\n')
            self.assertEqual(module.read_list(path),['0'])


if __name__=='__main__':unittest.main()
