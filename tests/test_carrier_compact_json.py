"""A local serialization hook preserves values and refuses nonfinite numbers."""
from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import unittest
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016/compact_json.py'
spec=importlib.util.spec_from_file_location('carrier_compact_json_test',SOURCE)
compact=importlib.util.module_from_spec(spec);spec.loader.exec_module(compact)

class CompactJson(unittest.TestCase):
 def test_local_core_proxy_preserves_objects_kwargs_and_global_module(self):
  original=json.dumps;core=SimpleNamespace(json=json);compact.install(core)
  obj=dict(z=[.06,-0.,1e-300,10**40],a={'côté':'preuve','bytes':b'known'})
  kwargs=dict(indent=8,sort_keys=True,ensure_ascii=False,default=lambda value:value.decode())
  result=core.json.dumps(obj,**kwargs)
  self.assertEqual(json.loads(result),json.loads(original(obj,**kwargs)))
  self.assertTrue(result.startswith('{"a":'));self.assertIn('côté',result)
  self.assertNotIn('\n',result);self.assertIs(json.dumps,original);self.assertIs(core.json.loads,json.loads)
  self.assertIn('\n',json.dumps({'x':1},indent=2))
 def test_nonfinite_values_are_refused_even_if_caller_allows_them(self):
  for value in [float('nan'),float('inf'),float('-inf')]:
   with self.subTest(value=value),self.assertRaises(ValueError):compact.dumps(dict(value=value),allow_nan=True)
