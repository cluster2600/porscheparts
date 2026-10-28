"""Stored pcurve normals on exact tangent cylinder/plane joins and sharp edges."""
import importlib.util
import math
from pathlib import Path
import unittest

try:
    import numpy as np
    from build123d import Axis,Box,fillet
    from OCP.BRepAdaptor import BRepAdaptor_Curve
except ImportError:
    np=None

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/check_root_blend.py'
spec=importlib.util.spec_from_file_location('carrier_root_blend',SOURCE)
blend=importlib.util.module_from_spec(spec);spec.loader.exec_module(blend)


@unittest.skipIf(np is None,'Optional native CAD runtime is unavailable')
class CarrierRootBlendTests(unittest.TestCase):
    def test_pcurve_normals_distinguish_tangent_join_and_sharp_box_edge(self):
        for body,tangent_count in ((Box(10,8,6),0),(fillet(Box(10,8,6).edges().filter_by(Axis.Z),1),8)):
            count=0;faces=list(body.faces())
            for edge in body.edges():
                adjacent=[face for face in faces if any(edge.wrapped.IsSame(e.wrapped) for e in face.edges())]
                self.assertEqual(len(adjacent),2)
                curve=BRepAdaptor_Curve(edge.wrapped)
                parameter=(curve.FirstParameter()+curve.LastParameter())/2
                results=[blend.boundary_normal(edge,face,parameter) for face in adjacent]
                normals=[r[0] for r in results]
                angle=math.degrees(math.atan2(np.linalg.norm(np.cross(*normals)),normals[0]@normals[1]))
                np.testing.assert_allclose(results[0][1]['support_point_mm'],results[1][1]['support_point_mm'],rtol=0,atol=1e-12)
                if angle<1e-5:count+=1
                else:self.assertAlmostEqual(angle,90,places=10)
            self.assertEqual(count,tangent_count)


if __name__=='__main__':unittest.main()
