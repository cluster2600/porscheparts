import sys,tempfile,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from cyclic_vector_trace import vtk_field,expected_trace


class CyclicVectorTest(unittest.TestCase):
    def test_binary_and_ascii_and_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'trace.vtk';values=np.array([[1.25,-2,3],[4,5,6]])
            for binary in (False,True):
                payload=values.astype('>f4').tobytes() if binary else b'1.25 -2 3 4 5 6\n'
                p.write_bytes(b'# vtk\ntrace\n'+(b'BINARY' if binary else b'ASCII')+b'\nDATASET POLYDATA\nV 3 2 float\n'+payload)
                np.testing.assert_array_equal(vtk_field(p,'V',2),values)
            p.write_bytes(p.read_bytes()[:-4])
            with self.assertRaises(ValueError):vtk_field(p,'V',2)

    def test_rotated_trace_not_identity_or_inverse(self):
        r=np.array([[0.,-1,0],[1,0,0],[0,0,1]])
        value,w=expected_trace(np.array([[0.,-1,0]]),np.array([[1.,0,0]]),np.zeros((1,3)),np.array([[0.,1,0]]),np.array([[1.,2,3]]),np.array([[4.,5,6]]),r)
        np.testing.assert_allclose(w,[.5]);np.testing.assert_allclose(value,[[-2,3,4.5]])

if __name__=='__main__':unittest.main()
