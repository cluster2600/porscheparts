import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location('area_precision', HERE/'audit_area_precision.py')
audit = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(audit)


class AreaPrecisionTests(unittest.TestCase):
    def test_decimal_independent_formulas(self):
        from decimal import Decimal
        for height in (1., 2.**-30):
            vertices = [[0.,0.,0.],[1.,0.,0.],[1.,height,0.]]
            for precision in (80,120):
                cross, gram = audit.decimal_areas(vertices,precision)
                self.assertEqual(cross,Decimal.from_float(height)/2)
                self.assertEqual(cross,gram)

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'Torch is optional')
    def test_thin_triangle_cancellation_and_narrow_adapter(self):
        import torch
        vectors = torch.tensor([[[1.,0.,0.],[1.,2.**-30,0.]]],dtype=torch.float64)
        u,v = vectors[:,0],vectors[:,1]
        gram = ((u*u).sum(-1)*(v*v).sum(-1)-(u*v).sum(-1)**2).clamp(min=0).sqrt()/2
        self.assertEqual(gram.item(),0.)
        self.assertEqual(audit.stable_3d_areas(vectors).item(),2.**-31)
        for invalid in (vectors.float(), vectors[:,:,:2], torch.zeros_like(vectors), vectors*float('nan')):
            with self.assertRaises(ValueError):audit.stable_3d_areas(invalid)


if __name__ == '__main__':unittest.main()
