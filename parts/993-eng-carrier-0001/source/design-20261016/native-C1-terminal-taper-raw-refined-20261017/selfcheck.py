"""Tiny synthetic ZIP/JSON tests only; never real archive extraction or numerical replay."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

HERE=Path(__file__).resolve().parent
if '--base-capsule' in sys.argv:
    index=sys.argv.index('--base-capsule');BASE=Path(sys.argv[index+1]).absolute();del sys.argv[index:index+2]
else:BASE=HERE.parent/'native-C1-terminal-taper-20261017'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def archive(path,members):
    rows={}
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data);rows[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    return dict(bytes=path.stat().st_size,sha256=sha(path),members=rows)

def fixture(root):
    base=root/'base';base.mkdir();cap=root/'delta';cap.mkdir()
    shutil.copyfile(BASE/'restore.py',base/'restore.py');shutil.copyfile(HERE/'restore.py',cap/'restore.py')
    inherited={};basearchives={}
    for i,name in enumerate(('taper-common.zip','taper-rigid.zip','taper-spring.zip')):
        data={f'old/{i}-{j:03}.txt':bytes([65+i]) for j in range(165)}
        row=archive(base/name,data);basearchives[name]=row;inherited.update(row['members'])
    bm=dict(schema='actual-preserved-taper-native-capsule-1',archives=basearchives,files_sha256={'restore.py':sha(base/'restore.py')})
    (base/'manifest.json').write_text(json.dumps(bm))
    inventory={p.name:sha(p) for p in base.iterdir() if p.is_file()}
    (base/'archive.json').write_text(json.dumps({'files_sha256':inventory}))
    new={name:archive(cap/name,{f'new/{i}.json':json.dumps({'float':1.25,'Unicode':'µ','unused':None}).encode()})
         for i,name in enumerate(('taper-raw-refined-common.zip','taper-raw-refined-rigid.zip','taper-raw-refined-spring.zip'))}
    manifest=dict(schema='actual-taper-raw-refined-dependent-native-capsule-1',dependency=dict(manifest_sha256=sha(base/'manifest.json'),inventory_sha256=sha(base/'archive.json'),restore_source_sha256=sha(base/'restore.py'),members=inherited),archives=new,files_sha256={'restore.py':sha(cap/'restore.py')})
    (cap/'manifest.json').write_text(json.dumps(manifest));module=load('synthetic_delta',cap/'restore.py')
    return module,base,cap,manifest

class Checks(unittest.TestCase):
    def test_transfer_and_path_guards_reused_AST_exactly(self):
        funcs=lambda text:{n.name:ast.dump(n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        old=funcs((BASE/'restore.py').read_text());new=funcs((HERE/'restore.py').read_text())
        for name in ('require','sha','relative','transfer'):self.assertEqual(old[name],new[name])
    def test_unchanged_real_analysis_sources(self):
        for name,digest in {'audit_energy.py':'b71603069518e6aa8820a7c5fec02115ab82a585e6fe9c160452f1ca2025b186','locate.py':'962379625759f1e467da8eb904c3d25d7f7860443745cb37529dad5ea293dad7','cad_binding.py':'07addd2439be51920d393c8bee170611fea4774c3723906bf446387bbef382fb'}.items():self.assertEqual(sha(BASE/'sources'/name),digest)
    def test_exact_495_plus_three_and_whole_JSON_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);dest=root/'restored';r.restore(dest,sha(cap/'manifest.json'),base)
            members=r.all_members(m);self.assertEqual(len(members),498)
            self.assertTrue(all(sha(dest/p)==row['sha256'] for p,row in members.items()))
            self.assertEqual(json.loads((dest/'new/0.json').read_text()),{'float':1.25,'Unicode':'µ','unused':None})
            r.verify(sha(cap/'manifest.json'),base)
    def test_dependency_crossed_manifest_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);m['dependency']['manifest_sha256']='0'*64;(cap/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'dependency identity'):r.restore(root/'out',sha(cap/'manifest.json'),base)
            self.assertFalse((root/'out').exists())
    def test_collision_refuses_before_creating_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);path=next(iter(m['dependency']['members']));m['archives']['taper-raw-refined-common.zip']['members'][path]=m['dependency']['members'][path];(cap/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'overwrites'):r.restore(root/'out',sha(cap/'manifest.json'),base)
            self.assertFalse((root/'out').exists())
    def test_path_traversal_and_symlink_destination_refuse(self):
        r=load('path_only',HERE/'restore.py')
        for path in ('../bad','/bad','a/../b','./a','a//b'):
            with self.subTest(path=path),self.assertRaises(ValueError):r.relative(path)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);target=root/'target';target.mkdir();(root/'link').symlink_to(target,target_is_directory=True)
            with self.assertRaises(ValueError):r.restore(root/'link/out',sha(cap/'manifest.json'),base)
    def test_new_member_SHA_refuses_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);m['archives']['taper-raw-refined-common.zip']['members']['new/0.json']['sha256']='0'*64;(cap/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Decompressed original'):r.restore(root/'out',sha(cap/'manifest.json'),base)
            with self.assertRaisesRegex(ValueError,'fresh restoration'):r.restore(root/'out',sha(cap/'manifest.json'),base)
    def test_strict_archive_limit_and_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);m['archives']['taper-raw-refined-common.zip']['bytes']=100000000;(cap/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'strict size'):r.manifest(sha(cap/'manifest.json'),base)
    def test_insufficient_disk_refuses_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root)
            with patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=0)),self.assertRaisesRegex(ValueError,'free space'):r.restore(root/'out',sha(cap/'manifest.json'),base)
            self.assertFalse((root/'out').exists())
    def test_dependency_can_be_relocated_without_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r,base,cap,m=fixture(root);relocated=root/'different-base-name';base.rename(relocated)
            r.restore(root/'out',sha(cap/'manifest.json'),relocated);self.assertEqual(len(list((root/'out').rglob('*.txt'))),495)
    def test_four_replayed_reports_require_entire_equality_and_exact_bytes(self):
        text=(HERE/'replay_analysis.py').read_text();tree=ast.parse(text)
        self.assertIn('actual_energy == historical_energy',text);self.assertIn('actual_peak == historical_peak',text)
        self.assertIn("archive.sha(output / (case['key'] + '-' + label + '.json')) == archive.sha(retained_path)",text)
        self.assertIn('archive.all_members(report).items()',text)
        calls=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertFalse(set(calls)&{'solve','generate','refine'})
        self.assertNotEqual(hashlib.sha256(b'{"a": 1}\n').hexdigest(),hashlib.sha256(b'{\n  "a": 1\n}\n').hexdigest())

    def test_pack_storage_guard_refuses_before_directory_or_exec(self):
        path=HERE/'sources/package_owned.py' if (HERE/'sources/package_owned.py').is_file() else HERE.parent/'package_owned.py'
        wrapper=load('fixed_pack_space_fixture',path)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();plan=root/'plan.json'
            plan.write_text(json.dumps(dict(source_root=str(root),destination=str(root/'archives'),archives={n:{} for n in ('taper-raw-refined-common.zip','taper-raw-refined-rigid.zip','taper-raw-refined-spring.zip')})))
            with patch.object(wrapper,'HERE',root),patch.object(wrapper,'ROOT',root),patch.object(wrapper.shutil,'disk_usage',return_value=SimpleNamespace(free=0)),self.assertRaisesRegex(ValueError,'free space'):
                wrapper.run(plan,sha(plan))
            self.assertFalse((root/'archives').exists())

    def test_direct_unchanged_pack_entry_has_one_call_caps_and_no_nice_or_exec(self):
        wrapper=load('direct_fixed_pack_fixture',HERE.parent/'package_owned.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();plan=root/'plan.json';fake=root/'fake_package.py'
            fake.write_text("def pack(path,expected):\n    with path.with_name('called').open('x') as f:f.write(expected)\n")
            plan.write_text(json.dumps(dict(source_root=str(root),destination=str(root/'archives'),archives={n:{} for n in ('taper-raw-refined-common.zip','taper-raw-refined-rigid.zip','taper-raw-refined-spring.zip')})))
            with patch.object(wrapper,'HERE',root),patch.object(wrapper,'ROOT',root),patch.object(wrapper,'PACKER',fake),patch.object(wrapper,'PACKER_SHA',sha(fake)),patch.object(wrapper.shutil,'disk_usage',return_value=SimpleNamespace(free=10**9)),patch.object(wrapper.os,'getpriority',return_value=10),patch.object(wrapper.os,'nice',side_effect=AssertionError('No second nice')),patch.object(wrapper.os,'execv',side_effect=AssertionError('No CLI exec')),patch.object(wrapper.signal,'signal'),patch.object(wrapper.signal,'alarm')as alarm,patch.object(wrapper.resource,'setrlimit')as limits:
                wrapper.run(plan,sha(plan))
                self.assertEqual((root/'called').read_text(),sha(plan));self.assertEqual([c.args for c in alarm.call_args_list],[(180,),(0,)])
                limits.assert_called_once_with(wrapper.resource.RLIMIT_CPU,(150,151))

if __name__=='__main__':unittest.main()
