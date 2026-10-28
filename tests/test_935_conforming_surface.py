import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

try:import numpy as np
except ImportError:np=None
SOURCE=Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('conforming_surface',SOURCE/'prepare_conforming_surface.py')
module=importlib.util.module_from_spec(spec)
if np is not None:spec.loader.exec_module(module)


@unittest.skipIf(np is None,'NumPy unavailable')
class ConformingSurfaceTests(unittest.TestCase):
    def fixture(self,folder):
        v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype=np.float32)
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=np.int32)
        records=np.zeros(4,dtype=module.DTYPE);records['vertices']=v[f]
        stl=folder/'mesh.stl';stl.write_bytes(b' '*80+(4).to_bytes(4,'little')+records.tobytes())
        bundle=folder/'boundary.npz';np.savez(bundle,vertices=v,faces=f)
        return v,f,stl,bundle

    def test_native_coordinates_and_smesh_roundtrip_are_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);v,f,stl,bundle=self.fixture(root)
            a,b=module.load_surface(bundle,module.sha(bundle),stl,module.sha(stl))
            np.testing.assert_array_equal(a,v);np.testing.assert_array_equal(b,f)
            path=root/'mesh.smesh';module.write_smesh(path,a,b)
            lines=path.read_text().splitlines();self.assertEqual(lines[0],'4 3 0 0')
            np.testing.assert_array_equal(np.loadtxt(lines[1:5])[:,1:],v)
            np.testing.assert_array_equal(np.loadtxt(lines[6:10],dtype=int)[:,1:],f)
            self.assertEqual(lines[-2:],['0','0'])
            with self.assertRaises(FileExistsError):module.write_smesh(path,a,b)

    def test_changed_coordinate_or_triangle_order_cannot_borrow_native_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);v,f,stl,bundle=self.fixture(root)
            for changed in (v+np.array([0,0,.125],dtype=np.float32),v):
                faces=f if changed is not v else f[::-1]
                np.savez(bundle,vertices=changed,faces=faces)
                with self.assertRaisesRegex(ValueError,'coordinates or order'):
                    module.load_surface(bundle,module.sha(bundle),stl,module.sha(stl))
