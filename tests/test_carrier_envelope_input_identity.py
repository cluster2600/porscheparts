"""A fresh meshing receipt binds the exact STL before any preparation output."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):raise unittest.SkipTest('Coverage runtime required')
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
from prepare_exact_envelopes_v2 import resolve_identity

class EnvelopeInputIdentity(unittest.TestCase):
 def test_fresh_identity_is_exact_and_malformed_or_changed_stl_is_refused(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);stl=d/'part.stl';stl.write_bytes(b'exact input');digest=hashlib.sha256(stl.read_bytes()).hexdigest()
   receipt=d/'meshing.json';receipt.write_text(json.dumps(dict(candidate_STL_sha256=digest)))
   self.assertEqual(resolve_identity(stl,identity_receipt=receipt),digest)
   self.assertEqual(resolve_identity(stl,expected_sha256=digest),digest)
   for value in [None,'invalid',42]:
    receipt.write_text(json.dumps(dict(candidate_STL_sha256=value)))
    with self.assertRaisesRegex(ValueError,'Malformed'):resolve_identity(stl,identity_receipt=receipt)
   receipt.write_text(json.dumps(dict(candidate_STL_sha256=digest)));stl.write_bytes(b'changed input')
   with self.assertRaisesRegex(ValueError,'mismatch'):resolve_identity(stl,identity_receipt=receipt)
   with self.assertRaisesRegex(ValueError,'exactly one'):resolve_identity(stl,digest,receipt)
