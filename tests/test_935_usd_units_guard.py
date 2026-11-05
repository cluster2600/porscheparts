"""Regression for explicit 935 stage units, not scan calibration."""
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
          'assembly-placement/check_usd_units.py')
spec = importlib.util.spec_from_file_location('units_guard', SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@unittest.skipUnless(Usd is not None, 'usd-core is optional')
class UnitsCompositionTests(unittest.TestCase):
    def test_root_must_author_one_metre_per_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = Usd.Stage.CreateNew(str(root / 'base.usda'))
            UsdGeom.SetStageMetersPerUnit(base, 1.0)
            base.GetRootLayer().Save()
            stage = Usd.Stage.CreateNew(str(root / 'layer.usda'))
            stage.GetRootLayer().subLayerPaths = ['./base.usda']
            stage.GetRootLayer().Save()
            # Sublayer metadata does not author the root stage metadata.
            with self.assertRaisesRegex(ValueError, 'explicitly author'):
                guard.validate(stage)
            UsdGeom.SetStageMetersPerUnit(stage, 0.01)
            with self.assertRaisesRegex(ValueError, 'Expected one metre'):
                guard.validate(stage)
            UsdGeom.SetStageMetersPerUnit(stage, 1.0)
            self.assertEqual(guard.validate(stage), {
                'meters_per_unit': 1.0, 'source_scale_verified': False})

    def test_unopened_stage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'did not open'):
            guard.validate(None)
