"""Regression for USD layer time scaling in the 935 inspection scene."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    from pxr import Usd, UsdGeom
except ImportError:
    Usd = UsdGeom = None

SOURCE = (Path(__file__).resolve().parents[1] /
          'twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104' /
          'assembly-placement/check_rotor_timeline.py')
spec = importlib.util.spec_from_file_location('timeline_guard', SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@unittest.skipUnless(Usd is not None, 'usd-core is optional')
class TimelineCompositionTests(unittest.TestCase):
    def test_composed_timeline_and_time_scaling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = Usd.Stage.CreateNew(str(root / 'base.usda'))
            base.SetStartTimeCode(0)
            base.SetEndTimeCode(240)
            base.SetTimeCodesPerSecond(60)
            base.SetFramesPerSecond(60)
            rotor = UsdGeom.Xform.Define(base, '/World/rotor_candidate')
            spin = rotor.AddRotateZOp()
            for frame in range(241):
                spin.Set(1.5 * frame, frame)
            base.GetRootLayer().Save()
            base = None

            layer = Usd.Stage.CreateNew(str(root / 'layer.usda'))
            layer.GetRootLayer().subLayerPaths = ['./base.usda']
            layer.SetStartTimeCode(0)
            layer.SetEndTimeCode(240)
            layer.SetTimeCodesPerSecond(60)
            layer.SetFramesPerSecond(60)
            layer.GetRootLayer().Save()
            self.assertEqual(guard.validate(layer)['checked_frames'], 241)

            # A stronger layer using 24 time codes/s remaps the 60 Hz source.
            layer.SetTimeCodesPerSecond(24)
            layer.SetFramesPerSecond(24)
            layer.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError, 'timeline'):
                guard.validate(layer)

            # Metadata alone is insufficient: a changed animation must fail too.
            layer.SetTimeCodesPerSecond(60)
            layer.SetFramesPerSecond(60)
            rotor_override = layer.OverridePrim('/World/rotor_candidate')
            UsdGeom.Xformable(rotor_override).GetOrderedXformOps()[0].Set(17, 60)
            with self.assertRaisesRegex(ValueError, 'Unexpected rotor angle'):
                guard.validate(layer)
