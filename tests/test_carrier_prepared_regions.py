"""Region-manifest paths follow their own root and the exact envelope identity."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):raise unittest.SkipTest('Coverage runtime required')
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE));from prepared_regions import PreparedRegions

class PreparedRegionManifest(unittest.TestCase):
 def test_paths_are_based_on_manifest_not_working_directory_and_store_is_bound(self):
  with tempfile.TemporaryDirectory() as directory:
   directory=Path(directory);region=directory/'source-000';region.mkdir();files={}
   for name in ['support.npz','geometry-assessment.json','material-connections.json']:
    p=region/name;p.write_bytes(b'identity-only fixture; geometry not admitted');files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
   helper=SOURCE.parent/'process-scanpath-audit-20261016/exact_band_union.py'
   receipt=region/'region-checkpoint.json';receipt.write_text(json.dumps(dict(status='region_geometry_completed_no_global_admission',source_index=0,files_sha256=files,
    additional_source_sha256={helper.name:hashlib.sha256(helper.read_bytes()).hexdigest()})))
   manifest=directory/'regions.json';manifest.write_text(json.dumps(dict(schema='prepared-support-regions-1',envelope_store_sha256='expected-store',
    regions=[dict(source_index=0,checkpoint='source-000/region-checkpoint.json',checkpoint_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())])))
   prior=Path.cwd()
   try:
    os.chdir('/');loader=PreparedRegions(manifest,[0],'expected-store');loader.verify()
    self.assertEqual(loader.rows[0]['_directory'],region.resolve())
    self.assertIn(helper,loader.files)
    with self.assertRaisesRegex(ValueError,'another envelope store'):PreparedRegions(manifest,[0],'other-store')
    with self.assertRaisesRegex(ValueError,'omit or reorder'):PreparedRegions(manifest,[1],'expected-store')
   finally:os.chdir(prior)
   # Only manifest identity is tested above. No geometry() call or global
   # admission is claimed for the deliberately non-geometric fixture files.
