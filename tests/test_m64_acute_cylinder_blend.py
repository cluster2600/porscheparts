import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('numpy'),'optional numerical helper dependencies')
class AcuteBlendTest(unittest.TestCase):
    def test_local_candidate_admission_requires_every_guard(self):
        path=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/trial_acute_cylinder_blend.py'
        spec=importlib.util.spec_from_file_location('acute_blend',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        good=dict(native_valid=True,protected_unchanged=True,source_in_memory_unchanged=True,
                  tolerances_not_increased=True,solid_count=1)
        self.assertTrue(module.admitted(good,(141,142),{2,140,141,142},{2,140,141,142}))
        for key in good:
            bad=dict(good);bad.pop(key)
            self.assertFalse(module.admitted(bad,(141,142),{141,142},{141,142}))
        self.assertFalse(module.admitted({**good,'native_valid':1},(141,142),{141,142},{141,142}))
        self.assertFalse(module.admitted(good,(141,142),{141,142},{141,142,999}))
        self.assertFalse(module.admitted(good,(141,142),{141,142},{141}))
