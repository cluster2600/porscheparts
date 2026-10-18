"""A different CORE or prepared-region receipt must fail before any geometry run."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):raise unittest.SkipTest('Coverage runtime required')
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE));import build_cached

class BuildReuseGuards(unittest.TestCase):
 def test_unknown_core_is_refused_before_executing_its_code(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);input_path=d/'input.stl';input_path.write_bytes(b'frozen identity')
   wrong=d/'unknown-core.py';wrong.write_text("raise RuntimeError('must never execute')")
   with patch.object(build_cached,'CORE',wrong),self.assertRaisesRegex(ValueError,'CORE identity'):
    build_cached.build(input_path,d/'output',d/'store',d/'cache',expected_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest())
 def test_reuse_cannot_borrow_another_prepared_region_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);input_path=d/'input.stl';input_path.write_bytes(b'frozen identity');stage=d/'stage';stage.mkdir()
   (stage/'support-stage.json').write_text(json.dumps(dict(admission={},prepared_regions_manifest_sha256='other')))
   manifest=d/'prepared-regions.json';manifest.write_text('{}')
   store=SimpleNamespace(report=dict(regions=[dict(source_index=0)]),files={},manifest_sha256='store',identify=lambda *args:None)
   prepared=SimpleNamespace(manifest_sha256='requested',files={})
   with patch.object(build_cached,'EnvelopeStore',return_value=store),patch.object(build_cached,'PreparedRegions',return_value=prepared),patch.object(build_cached,'CachedLayers',return_value=object()):
    with self.assertRaisesRegex(ValueError,'another prepared-region manifest'):
     build_cached.build(input_path,d/'output',d/'store',d/'cache',
      expected_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),solid_sheets=True,continuous_interfaces=True,
      region_checkpoints=manifest,reuse_support_stage=stage)
