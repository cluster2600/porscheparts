"""Small stdlib contracts for the new restoration path; no scientific fixture."""
import gzip
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import shutil
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_portable_restore_test',HERE/'restore.py')
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.capsule=self.root/'capsule';self.capsule.mkdir()
        self.old=restore.HERE;restore.HERE=self.capsule;shutil.copyfile(HERE/'restore.py',self.capsule/'restore.py')
        self.data=b'original native output\n'*30;self.relative='work/fixed/prepared-001/field.dat'
        source=self.capsule/'payloads'/ (self.relative+'.gz');source.parent.mkdir(parents=True)
        with source.open('xb')as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0)as stream:stream.write(self.data)
        self.report=dict(schema='wholepart-native64-portable-capsule-1',status='fixture',utility_sha256={'restore.py':restore.sha(self.capsule/'restore.py')},
            payloads=[dict(stored='payloads/'+self.relative+'.gz',restored=self.relative,compression='gzip-mtime0',
                stored_sha256=restore.sha(source),stored_bytes=source.stat().st_size,original_sha256=hashlib.sha256(self.data).hexdigest(),original_bytes=len(self.data))])
        self.publish()

    def tearDown(self):restore.HERE=self.old;self.tmp.cleanup()

    def publish(self):
        (self.capsule/'manifest.json').write_text(json.dumps(self.report));self.digest=restore.sha(self.capsule/'manifest.json')

    def test_actual_stream_is_restored_exactly(self):
        destination=self.root/'restored';receipt=restore.restore(destination,self.digest)
        self.assertEqual((destination/self.relative).read_bytes(),self.data);self.assertFalse(receipt['new_solver_run'])

    def test_existing_and_dangling_outputs_refuse_before_verification(self):
        existing=self.root/'exists';existing.mkdir();dangling=self.root/'link';target=self.root/'absent';dangling.symlink_to(target,target_is_directory=True)
        for p in (existing,dangling):
            with self.assertRaises(FileExistsError):restore.restore(p,'invalid manifest')
        self.assertFalse(target.exists())

    def test_changed_payload_and_review_hash_refused(self):
        with self.assertRaises(ValueError):restore.verify('0'*64)
        (self.capsule/self.report['payloads'][0]['stored']).write_bytes(b'changed')
        with self.assertRaises(ValueError):restore.verify(self.digest)

    def test_xz_stream_is_restored_exactly(self):
        row=self.report['payloads'][0];path=self.capsule/(row['stored'][:-3]+'.xz')
        with lzma.open(path,'wb')as stream:stream.write(self.data)
        row.update(stored=path.relative_to(self.capsule).as_posix(),compression='xz-no-timestamp',stored_sha256=restore.sha(path),stored_bytes=path.stat().st_size)
        self.publish();destination=self.root/'restored-xz';restore.restore(destination,self.digest)
        self.assertEqual((destination/self.relative).read_bytes(),self.data)

    def test_wrong_original_digest_refuses_before_destination_created(self):
        self.report['payloads'][0]['original_sha256']='0'*64;self.publish();destination=self.root/'no-output'
        with self.assertRaises(ValueError):restore.restore(destination,self.digest)
        self.assertFalse(destination.exists())

    def test_relative_path_escape_refused(self):
        for p in ('.','../x','/tmp/x','a/../x','a//x','a/./x'):
            with self.assertRaises(ValueError):restore.relative(p)


if __name__=='__main__':unittest.main()
