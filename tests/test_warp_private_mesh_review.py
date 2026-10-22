import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
try:
    import numpy as np
except ImportError:
    np = None

SOURCE=Path(__file__).resolve().parents[1]/'benchmarks/warp-geometry'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('private_mesh_review',SOURCE/'mesh_review.py')
module=importlib.util.module_from_spec(spec)
if np is not None:spec.loader.exec_module(module)


@unittest.skipIf(np is None,'NumPy unavailable')
class MeshBundleTests(unittest.TestCase):
    def test_reference_from_a_cropped_patch_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            case=Path(d)/'case.json';case.write_text(json.dumps({'scale_verified':False,
                'native_unit':'uncalibrated_scan_unit','reference_scope':'cropped_local_patch',
                'reference_method':'independent_trimesh_point_to_triangle'}))
            with self.assertRaisesRegex(ValueError,'independent reference'):
                module.run(case,'cpu',1,Path(d)/'report.json')

    def test_valid_arrays_and_hash_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'mesh.npz'
            np.savez(p,vertices=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype=np.float32),faces=np.array([[0,1,2]],dtype=np.int32),
                     probes=np.array([[.2,.2,1]],dtype=np.float32),reference_distances=np.array([1.],dtype=np.float64))
            arrays=module.load_bundle(p,module.sha(p));self.assertEqual(len(arrays[2]),1)
            with self.assertRaises(ValueError):module.load_bundle(p,'0'*64)

    def test_invalid_indices_nonfinite_and_query_domain_fail(self):
        for field,value in [('faces',np.array([[0,1,3]],dtype=np.int32)),('vertices',np.array([[0,0,0],[1,0,0],[0,float('nan'),0]],dtype=np.float32)),
                            ('probes',np.array([[501,0,0]],dtype=np.float32)),('reference_distances',np.array([-1.],dtype=np.float64))]:
            with tempfile.TemporaryDirectory() as d:
                arrays=dict(vertices=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype=np.float32),faces=np.array([[0,1,2]],dtype=np.int32),
                    probes=np.array([[.2,.2,1]],dtype=np.float32),reference_distances=np.array([1.],dtype=np.float64))
                arrays[field]=value;p=Path(d)/'mesh.npz';np.savez(p,**arrays)
                with self.assertRaises(ValueError):module.load_bundle(p,module.sha(p))
