"""Exact native binary exchange without STL quantization or tolerance welding."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source"))
from run_head_envelope import read_surface,write_surface,latest_complete_checkpoint


class ExactSurfaceExchangeTests(unittest.TestCase):
    def test_binary64_near_distinct_points_and_orientation_survive(self):
        p=np.array([[0.,0,0],[1e-12,0,0],[0,1.,0],[0,0,1.]])
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"surface.bin";write_surface(path,p,f);q,g=read_surface(path)
            self.assertTrue(np.array_equal(p,q));self.assertTrue(np.array_equal(f,g))
            with self.assertRaises(FileExistsError):write_surface(path,p,f)

    def test_partial_or_invalid_indexed_payload_is_rejected(self):
        p=np.array([[0.,0,0],[1,0,0],[0,1.,0]])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"surface.bin";write_surface(path,p,np.array([[0,1,3]]))
            with self.assertRaises(ValueError):read_surface(path)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaises(ValueError):read_surface(path)

    def test_newest_torn_checkpoint_is_preserved_while_previous_complete_is_selected(self):
        p=np.array([[0.,0,0],[1,0,0],[0,1.,0]])
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);good=directory/"checkpoint-1.bin";bad=directory/"checkpoint-2.bin"
            write_surface(good,p,np.array([[0,1,2]]));bad.write_bytes(b"")
            selected,rejected=latest_complete_checkpoint(directory)
            self.assertEqual(selected,good);self.assertEqual(rejected[0]["file"],bad.name)
            self.assertEqual(bad.read_bytes(),b"")

    def test_complete_but_invalid_geometry_is_not_hidden_by_older_checkpoint(self):
        p=np.array([[0.,0,0],[1,0,0],[0,1.,0]])
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);good=directory/"checkpoint-1.bin";bad=directory/"checkpoint-2.bin"
            write_surface(good,p,np.array([[0,1,2]]));write_surface(bad,p*np.nan,np.array([[0,1,2]]))
            selected,rejected=latest_complete_checkpoint(directory)
            self.assertEqual(selected,bad);self.assertEqual(rejected,[])
            with self.assertRaises(ValueError):read_surface(selected)


if __name__=="__main__":unittest.main()
