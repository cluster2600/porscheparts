"""Offline guard checks only; no compiler, solver or external command."""
from pathlib import Path
import io
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import linux_job as job


class LinuxJob(unittest.TestCase):
    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive=root/'source.tar'
            with tarfile.open(archive,'w') as t:
                member=tarfile.TarInfo('../escape'); member.size=1
                t.addfile(member,io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError,'unsupported archive member'):
                job.extract(archive,root/'source')
            self.assertFalse((root/'escape').exists())

    def test_non_linux_never_starts_build(self):
        with tempfile.TemporaryDirectory() as d, patch.object(job,'inputs',return_value={}), \
                patch.object(job.sys,'platform','darwin'), patch.object(job.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'native Linux'):
                job.run(SimpleNamespace(repo=Path(d),output=Path(d)/'new',check=False))
            spawn.assert_not_called(); self.assertFalse((Path(d)/'new').exists())

    def test_exact_three_hash_products_and_refuse_changed_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'util.c'; old='loc  = (loc1*loc2) % hashtable->nlist ;'
            new='loc  = (int) (((long long) loc1*loc2) % hashtable->nlist) ;'
            p.write_text((old+'\n')*3)
            row=job.replace(p,old,new,3)
            self.assertEqual(row['replacements'],3); self.assertEqual(p.read_text().count(new),3)
            with self.assertRaisesRegex(ValueError,'unexpected source'): job.replace(p,old,new,3)


if __name__=='__main__': unittest.main()
