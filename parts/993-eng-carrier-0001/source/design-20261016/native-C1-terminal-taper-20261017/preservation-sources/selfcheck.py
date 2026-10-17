"""Tiny stdlib trust fixtures only; no actual 495-member packaging or replay."""
import ast,hashlib,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load('_taper_pack_tests',H/'pack_owned.py');A=load('_taper_restore_tests',H/'restore.py');B=load('_taper_analysis_tests',H/'replay_analysis.py')
class Tests(unittest.TestCase):
 def test_01_fixed_inventory(self):
  v=json.loads((H.with_name('carrier-C1-terminal-taper-delivery-preparation-001')/'inventory-proposal.json').read_text());rows=P.inventory_archives(v);self.assertEqual([len(rows[n])for n in P.ARCHIVES],[433,31,31]);self.assertEqual(sum(x['bytes']for a in rows.values()for x in a.values()),598766939)
 def test_02_paths(self):
  for s in ['', '.', '../x','/absolute','a//b','a/../b','a/']:
   with self.assertRaises(ValueError):P.relative(s)
  self.assertEqual(P.relative('work/a.json'),Path('work/a.json'))
 def test_03_symlink_refused(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d).resolve();(r/'real').write_bytes(b'good');(r/'alias').symlink_to(r/'real')
   with self.assertRaises(ValueError):P.regular(r/'alias')
 def test_04_small_control_cap(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d).resolve()/'big';p.touch()
   with p.open('r+b')as f:f.truncate(8*1024**2)
   with self.assertRaises(ValueError):P.small(p)
 def test_05_changed_group_count(self):
  v=json.loads((H.with_name('carrier-C1-terminal-taper-delivery-preparation-001')/'inventory-proposal.json').read_text());v['archives']['taper-common.zip']['member_count']-=1
  with self.assertRaises(ValueError):P.inventory_archives(v)
 def test_06_runtime_forbidden(self):
  v=json.loads((H.with_name('carrier-C1-terminal-taper-delivery-preparation-001')/'inventory-proposal.json').read_text());row=v['members'].pop(next(iter(v['members'])));v['members']['work/runtimes/forbidden.py']=row
  with self.assertRaises(ValueError):P.inventory_archives(v)
 def test_07_unknown_archive_refused(self):
  v=json.loads((H.with_name('carrier-C1-terminal-taper-delivery-preparation-001')/'inventory-proposal.json').read_text());next(iter(v['members'].values()))['archive_slot']='other.zip'
  with self.assertRaises(ValueError):P.inventory_archives(v)
 def test_08_unchanged_package(self):self.assertEqual(P.sha(H/'package.py'),'697277ea5c4ccc10cec323f6815409e4d948726f55b52045c17d1be99bfa1a9a')
 def test_09_whole_utility_inverses(self):
  d=json.loads((H/'source-derivation.json').read_text())
  for label in ['restore.py','replay_analysis.py']:
   row=d[label];s=(H/label).read_text()
   for change in reversed(row['replacements']):
    old,new=change['before'],change['after'];self.assertEqual(s.count(new),1);s=s.replace(new,old)
   self.assertEqual(hashlib.sha256(s.encode()).hexdigest(),row['reference_sha256'])
 def test_10_unchanged_math_sources(self):
  for name,digest in [('audit_energy.py','b71603069518e6aa8820a7c5fec02115ab82a585e6fe9c160452f1ca2025b186'),('locate.py','962379625759f1e467da8eb904c3d25d7f7860443745cb37529dad5ea293dad7'),('cad_binding.py','07addd2439be51920d393c8bee170611fea4774c3723906bf446387bbef382fb'),('simulate.py','87be70c955e2532255fdee37cf3a686d970cb421bc9bf6094ca867f1f3098e77')]:self.assertEqual(P.sha(H/'sources'/name),digest)
 def test_11_case_mesh_guard(self):
  case=dict(name='actual');B.checked_case(case,dict(name='actual',procedure='static',mesh_sha256='right'),'right')
  with self.assertRaises(ValueError):B.checked_case(case,dict(name='actual',procedure='static',mesh_sha256='wrong'),'right')
 def test_12_new_peaks_bound(self):
  v=json.loads((H/'manifest-template.json').read_text());self.assertEqual([(c['key'],c['expected_element_id'],c['expected_IP_one_based'])for c in v['cases']],[('rigid',84327,1),('spring',54403,3)]);self.assertIsNone(v['archives']);self.assertIsNone(v['files_sha256']);self.assertFalse(v['candidate_qualified'])
 def test_13_foreign_FEA_terminal_join(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d).resolve();t=r/'terminal.json';root=r/'ROOT.json';t.write_text(json.dumps(dict(cases={})));root.write_text(json.dumps(dict(actual_tool_RC=0,terminal_sha256='foreign')));v=dict(stages=[],FEA_ROOT=dict(path=root.name,sha256=P.sha(root),owner_terminal=t.name,owner_terminal_sha256=P.sha(t)));saved=P.ROOT
   try:
    P.ROOT=r
    with self.assertRaisesRegex(ValueError,'Closed FEA join differs'):P.authorities(v,{})
   finally:P.ROOT=saved
 def fixture(self,r):
  data=b'{"complete":[1,2,3]}\n';info=zipfile.ZipInfo('work/a.json',date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
  with zipfile.ZipFile(r/'tiny.zip','x')as z:z.writestr(info,data)
  return dict(members={'work/a.json':dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())})
 def test_14_tiny_full_byte_roundtrip(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d).resolve();row=self.fixture(r);out=r/'restored';out.mkdir();saved=A.HERE
   try:A.HERE=r;A.transfer('tiny.zip',row,out);self.assertEqual(P.sha(out/'work/a.json'),row['members']['work/a.json']['sha256'])
   finally:A.HERE=saved
 def test_15_tiny_member_digest_refused(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d).resolve();row=self.fixture(r);row['members']['work/a.json']['sha256']='0'*64;saved=A.HERE
   try:
    A.HERE=r
    with self.assertRaises(ValueError):A.transfer('tiny.zip',row)
   finally:A.HERE=saved
 def test_16_tiny_member_size_refused(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d).resolve();row=self.fixture(r);row['members']['work/a.json']['bytes']+=1;saved=A.HERE
   try:
    A.HERE=r
    with self.assertRaises(ValueError):A.transfer('tiny.zip',row)
   finally:A.HERE=saved
 def test_17_manifest_wrong_identity_refused(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d).resolve();(r/'manifest.json').write_text('{}');saved=A.HERE
   try:
    A.HERE=r
    with self.assertRaises(ValueError):A.manifest('0'*64)
   finally:A.HERE=saved
 def test_18_no_native_import_in_utilities(self):
  for p in [H/'pack_owned.py',H/'restore.py',H/'package.py']:
   tree=ast.parse(p.read_text());modules={n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)}|{a.name for n in ast.walk(tree)if isinstance(n,ast.Import)for a in n.names};self.assertTrue(modules.isdisjoint({'numpy','gmsh','OCP','docker','trimesh'}))
if __name__=='__main__':unittest.main()
