from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0,str(SOURCE))
try:
    import numpy as np
    spec=importlib.util.spec_from_file_location('exact_boundary_cross',SOURCE/'surface-facet-repair-20261022/diagnose-added-boundary-point-002.py')
    exact=importlib.util.module_from_spec(spec);spec.loader.exec_module(exact)
    spec=importlib.util.spec_from_file_location('dual_cube_readback',SOURCE/'surface-facet-repair-20261022/check_cube_dual_002.py')
    cube=importlib.util.module_from_spec(spec);spec.loader.exec_module(cube)
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Requires NumPy')
class ExactBoundaryCrossTests(unittest.TestCase):
    def test_cross_product_does_not_wrap_at_64_bits(self):
        cross,scale=exact.exact_cross(np.array([[0.,0,0],[2.**40,0,0],[0,2.**40,0]]))
        self.assertEqual(cross,[0,0,2**80])
        self.assertEqual(scale,1)

    def test_translated_dyadic_collinear_points_are_exactly_collinear(self):
        origin=np.array([.125,.25,.375])
        cross,_=exact.exact_cross(np.array([origin,origin+[1,2,4],origin+[.5,1,2]]))
        self.assertEqual(cross,[0,0,0])

    def test_binary_fraction_cross_product_retains_its_scale(self):
        cross,scale=exact.exact_cross(np.array([[0.,0,0],[.5,0,0],[0,.25,0]]))
        self.assertEqual(Fraction(cross[2],scale**2),Fraction(1,8))

    def test_nonfinite_points_cannot_produce_a_collinearity_result(self):
        for value in [float('nan'),float('inf')]:
            with self.assertRaises((ValueError,OverflowError)):
                exact.exact_cross(np.array([[0.,0,0],[1,0,0],[0,value,0]]))


@unittest.skipUnless(AVAILABLE,'Requires NumPy')
class CubeBoundaryReadbackTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.case=Path(self.directory.name)
        self.parser=SOURCE/'fluid-mesh-study-20261022/export-fluid-plc-005.py'
        mesh=self.case/'constant/polyMesh';mesh.mkdir(parents=True)
        points=[(x,y,z) for z in [-.5,0.,.5] for x,y in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]]
        faces=[[4,5,6,7],[8,9,10,11],[3,2,1,0],[0,4,7,3],[4,8,11,7],[0,1,5,4],[4,5,9,8],[2,3,7,6],[6,7,11,10],[1,2,6,5],[5,6,10,9]]
        values={'points':['('+' '.join(map(str,p))+')' for p in points],
                'faces':[str(len(f))+'('+' '.join(map(str,f))+')' for f in faces],
                'owner':list(map(str,[0,1,0,0,1,0,1,0,1,0,1])), 'neighbour':['1'],
                'boundary':['%s { nFaces %d; startFace %d; }'%row for row in [('inlet',1,1),('outlet',1,2),('duct',6,3),('rotor',2,9)]]}
        for name,rows in values.items():
            (mesh/name).write_text('FoamFile { format ascii; }\n%d\n(\n%s\n)\n'%(len(rows),'\n'.join(rows)))
        (self.case/'log.checkMesh.allGeometry').write_text('cells: 2\nfaces: 11\nTotal volume = 1.\nMesh OK.\n')

    def test_two_cell_unit_cube_has_exact_boundary_volume(self):
        result=cube.check(self.case,self.parser)
        self.assertEqual(Fraction(result['exact_serialized_boundary_volume_m3']),1)
        self.assertEqual((result['cells'],result['Euler_characteristic']),(2,2))

    def test_actual_zero_time_mesh_is_read_instead_of_constant_mesh(self):
        shutil.copytree(self.case/'constant/polyMesh',self.case/'0/polyMesh')
        (self.case/'constant/polyMesh/points').write_text('Deliberately unreadable inactive mesh')
        result=cube.check(self.case,self.parser)
        self.assertEqual(result['mesh_instance'],'0')

    def test_warped_boundary_is_refused(self):
        path=self.case/'constant/polyMesh/points'
        path.write_text(path.read_text().replace('(-0.5 -0.5 -0.5)','(-0.6 -0.5 -0.5)'))
        with self.assertRaises(AssertionError):cube.check(self.case,self.parser)
        self.assertFalse((self.case/'geometry-readback.json').exists())

    def test_native_quality_failure_cannot_publish_geometry_receipt(self):
        (self.case/'log.checkMesh.allGeometry').write_text('cells: 2\nfaces: 11\nTotal volume = 1.\nFailed 1 mesh checks.\n')
        with self.assertRaises(AssertionError):cube.check(self.case,self.parser)
        self.assertFalse((self.case/'geometry-readback.json').exists())

    def test_native_cell_count_must_match_serialized_addressing(self):
        path=self.case/'log.checkMesh.allGeometry'
        path.write_text(path.read_text().replace('cells: 2','cells: 3'))
        with self.assertRaises(AssertionError):cube.check(self.case,self.parser)
        self.assertFalse((self.case/'geometry-readback.json').exists())


class SurfaceRepairCheckpointTests(unittest.TestCase):
    def test_executed_sources_remain_byte_identical(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/surface-facet-repair-20261022.json').read_text())
        for path,expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)

    def test_accepted_surface_and_cube_do_not_admit_refused_real_meshes(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/surface-facet-repair-20261022.json').read_text())
        self.assertTrue(record['surface']['complete_original_and_reference_bounds_passed'])
        self.assertEqual(record['surface']['poor_triangles_after'],46)
        self.assertEqual(record['volume']['tetrahedra'],3668295)
        self.assertTrue(record['volume']['exact_PLC_volume_equal'])
        self.assertEqual(record['native_tetrahedral']['failed_quality_checks'],7)
        self.assertTrue(record['polyhedral']['synthetic_cube']['native_full_quality_passed'])
        self.assertEqual(record['polyhedral']['real_rotor']['failed_quality_checks'],11)
        self.assertEqual(record['polyhedral']['real_rotor']['negative_volume_cells'],11)
        for key in ['full_system_goal_complete','scale_verified','current_geometry_CFD_accepted','manufacturing_authorized','physical_validation']:
            self.assertFalse(record['scope'][key])
        for item in [record['native_tetrahedral'],record['polyhedral']['real_rotor']]:
            self.assertFalse(item['full_quality_passed'])
            self.assertFalse(item['CFD_executed'])


if __name__=='__main__':
    unittest.main()
