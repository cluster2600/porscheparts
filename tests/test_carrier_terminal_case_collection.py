"""A new native terminal must bind its own relative proof payload."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional coverage runtime required')
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
from seal_envelopes_v2 import case_records


class TerminalCollection(unittest.TestCase):
 def test_relative_bound_native_proof_and_rejections(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);case=root/'source-000';proof=case/'result/sealed/native_audit.json';proof.parent.mkdir(parents=True)
   proof.write_bytes(b'identity fixture; not a native audit')
   digest=hashlib.sha256(proof.read_bytes()).hexdigest();name='result/sealed/native_audit.json'
   record=dict(schema='native-envelope-case-v2',status='executed',source_index=0,input_manifest_sha256='input',
    backend='cgal-positive-roof-prisms-v4',files_sha256={name:digest},native_audit=dict(path=name,sha256=digest))
   def write(value):(case/'case.json').write_text(json.dumps(value))
   write(record);inputs=dict(regions=[dict(source_index=0)])
   prisms,legacy,receipts=case_records(root,inputs,'input')
   self.assertEqual(prisms,{'0':str(proof.resolve())});self.assertFalse(legacy)
   self.assertEqual(receipts,[(case/'case.json').resolve()])
   for changes,pattern in [({'status':'rejected'},'rejected'),({'files_sha256':{}},'no bound payload'),
     ({'input_manifest_sha256':'other'},'another prepared input'),
     ({'files_sha256':{'../escape':digest}},'inside their case'),
     ({'native_audit':dict(path=name,sha256='wrong')},'audit identity')]:
    write(dict(record,**changes))
    with self.subTest(changes=changes),self.assertRaisesRegex(ValueError,pattern):case_records(root,inputs,'input')
   write(record);proof.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'output changed'):case_records(root,inputs,'input')
